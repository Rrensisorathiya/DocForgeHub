# assistant/nodes.py
# ── NOTE ──────────────────────────────────────────────────────────────────
# This file REUSES Project 2's RAG pipeline:
#   from rag.tools import search_docs, refine_query   ← Project 2
#   from rag.chain import ask                          ← Project 2
# No RAG logic is duplicated here.
# ─────────────────────────────────────────────────────────────────────────
import os, uuid
from utils.logger import setup_logger
from assistant.state import (
    AssistantState, EVIDENCE_THRESHOLD,
    get_priority, is_direct_ticket,
)

logger = setup_logger(__name__)

AZURE_ENDPOINT    = os.getenv("AZURE_LLM_ENDPOINT", "")
AZURE_API_KEY     = os.getenv("AZURE_OPENAI_LLM_KEY", "")
AZURE_API_VERSION = os.getenv("AZURE_LLM_API_VERSION", "2024-02-15-preview")
AZURE_DEPLOY      = os.getenv("AZURE_LLM_DEPLOYMENT_41_MINI", "")

_llm = None
def _get_llm():
    global _llm
    if _llm is None:
        from langchain_openai import AzureChatOpenAI
        _llm = AzureChatOpenAI(
            azure_endpoint   = AZURE_ENDPOINT,
            api_key          = AZURE_API_KEY,
            api_version      = AZURE_API_VERSION,
            azure_deployment = AZURE_DEPLOY,
            temperature      = 0.1,
            max_tokens       = 1000,
            timeout          = 30,
            max_retries      = 1,
        )
    return _llm


# ── NODE 1: context_loader ────────────────────────────────────────────────

def context_loader(state: AssistantState) -> AssistantState:
    from assistant.memory import (
        redis_load_messages, redis_load_context, db_load_messages
    )
    thread_id = state["thread_id"]
    trace_id  = state.get("trace_id") or str(uuid.uuid4())[:8]
    logger.info(f"[{trace_id}] context_loader thread={thread_id}")

    # Redis first (fast), fallback to PostgreSQL
    ctx      = redis_load_context(thread_id)
    messages = redis_load_messages(thread_id)
    if not messages:
        messages = db_load_messages(thread_id, limit=10)

    return {
        **state,
        "trace_id":   trace_id,
        "history":    messages,
        "industry":   ctx.get("industry")   or state.get("industry"),
        "department": ctx.get("department") or state.get("department"),
    }


# ── NODE 2: intent_classifier ─────────────────────────────────────────────

def intent_classifier(state: AssistantState) -> AssistantState:
    message  = state["message"]
    history  = state.get("history", [])
    industry = state.get("industry", "")
    dept     = state.get("department", "")
    trace_id = state.get("trace_id", "")
    logger.info(f"[{trace_id}] intent_classifier: '{message[:60]}'")

    # Rule-based shortcut
    if is_direct_ticket(message):
        return {**state, "intent": "ticket",
                "priority": get_priority(message), "next_action": "ticket"}

    # LLM classification
    hist_text = "\n".join(
        f"{m['role'].upper()}: {m['content'][:100]}"
        for m in history[-4:]
    )
    prompt = f"""You are classifying user intent for an enterprise document assistant.

Context: industry={industry or 'unknown'}, department={dept or 'unknown'}
History:
{hist_text or '(none)'}

Message: "{message}"

Classify as ONE of:
- retrieve → default for ANY document-related question (NDA, contracts, policies, HR, legal, compliance, etc.)
- ticket   → asks for live data, personal HR decisions, pricing, or real-time information
- clarify  → ONLY if message is completely unrelated gibberish with zero context

When in doubt, ALWAYS choose retrieve.
Reply with ONLY: clarify, retrieve, or ticket"""

    try:
        intent = _get_llm().invoke(prompt).content.strip().lower()
        intent = intent if intent in ("clarify", "retrieve", "ticket") else "retrieve"
    except Exception as e:
        logger.warning(f"[{trace_id}] Intent LLM error: {e}")
        intent = "retrieve"

    logger.info(f"[{trace_id}] intent={intent}")
    return {**state, "intent": intent,
            "priority": get_priority(message), "next_action": intent}


# ── NODE 3: clarify_node ──────────────────────────────────────────────────

def clarify_node(state: AssistantState) -> AssistantState:
    trace_id = state.get("trace_id", "")
    logger.info(f"[{trace_id}] clarify_node")
    prompt = f"""User said: "{state['message']}"

Generate ONE short clarifying question to get the missing info needed.
Focus on: industry, document type, company size, use case.
Reply ONLY with the question."""
    try:
        q = _get_llm().invoke(prompt).content.strip()
    except Exception:
        q = "Could you provide more details about your industry and the specific document you need?"
    return {**state, "clarify_question": q, "answer": q, "next_action": "done"}


# ── NODE 4: rag_retrieval ─────────────────────────────────────────────────
# ← Uses Project 2's rag/tools.py directly

def rag_retrieval(state: AssistantState) -> AssistantState:
    from rag.tools import search_docs, refine_query   # ← PROJECT 2 reuse

    message  = state["message"]
    industry = state.get("industry")
    dept     = state.get("department")
    trace_id = state.get("trace_id", "")
    logger.info(f"[{trace_id}] rag_retrieval: '{message[:60]}'")

    # Refine query (Project 2)
    try:
        refined = refine_query(message).get("refined", message)
    except Exception:
        refined = message

    # Search ChromaDB (Project 2)
    try:
        result = search_docs(
            query      = refined,
            industry   = industry,
            department = dept,
            top_k      = 5,
        )
        chunks = result.get("chunks", [])
    except Exception as e:
        logger.error(f"[{trace_id}] search_docs error: {e}")
        chunks = []

    # Evidence score = avg of top-3 chunk scores
    evidence_score = (
        sum(c.get("score", 0) for c in chunks[:3]) / min(len(chunks), 3)
        if chunks else 0.0
    )

    next_action = "answer" if evidence_score >= EVIDENCE_THRESHOLD else "ticket"
    logger.info(f"[{trace_id}] chunks={len(chunks)} score={evidence_score:.3f} → {next_action}")
    return {
        **state,
        "retrieved_chunks": chunks,
        "evidence_score":   round(evidence_score, 4),
        "refined_query":    refined,
        "next_action":      next_action,
    }


# ── NODE 5: answer_node ───────────────────────────────────────────────────
# ← Uses Project 2's rag/chain.py answer generation

def answer_node(state: AssistantState) -> AssistantState:
    import os, httpx
    from openai import AzureOpenAI
    message   = state["message"]
    chunks    = state.get("retrieved_chunks", [])
    history   = state.get("history", [])
    thread_id = state["thread_id"]
    trace_id  = state.get("trace_id", "")
    logger.info(f"[{trace_id}] answer_node: {len(chunks)} chunks")
    if not chunks:
        return {**state, "answer": "I could not find relevant information in the knowledge base.", "citations": [], "next_action": "done"}
    context_parts = []
    citations = []
    for i, c in enumerate(chunks[:5]):
        text     = c.get("text", "")
        citation = c.get("citation", c.get("metadata", {}).get("title", "Unknown"))
        context_parts.append(f"[{i+1}] {citation}\n{text}")
        if citation not in citations:
            citations.append(citation)
    context = "\n\n---\n\n".join(context_parts)
    history_text = ""
    for h in history[-4:]:
        role = "User" if h.get("role") == "user" else "Assistant"
        history_text += f"{role}: {h.get('content', '')}\n"
    system_prompt = """You are an enterprise document assistant. Answer ONLY using the provided context chunks. If context is insufficient, say: I don't have sufficient information in the knowledge base. Be concise, professional, and accurate."""
    hist_section = ("Previous conversation:\n" + history_text) if history_text else ""
    user_prompt = f"Context:\n{context}\n\n{hist_section}\nQuestion: {message}\n\nProvide a clear grounded answer based only on the context above."
    try:
        client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_LLM_ENDPOINT","").rstrip("/"),
            api_key=os.getenv("AZURE_OPENAI_LLM_KEY") or os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_LLM_API_VERSION","2025-01-01-preview"),
            http_client=httpx.Client(),
        )
        response = client.chat.completions.create(
            model=os.getenv("AZURE_LLM_DEPLOYMENT_41_MINI","gpt-4.1-mini"),
            messages=[{"role":"system","content":system_prompt},{"role":"user","content":user_prompt}],
            temperature=0.2, max_tokens=800,
        )
        answer = response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"[{trace_id}] answer_node error: {e}")
        answer = f"Error: {e}"
    return {**state, "answer": answer, "citations": citations, "next_action": "done"}

def ticket_node(state: AssistantState) -> AssistantState:
    from assistant.memory import redis_check_idempotency, redis_set_idempotency
    from assistant.ticket import create_notion_ticket

    thread_id = state["thread_id"]
    message   = state["message"]
    chunks    = state.get("retrieved_chunks", [])
    history   = state.get("history", [])
    dept      = state.get("department", "General")
    priority  = state.get("priority", "medium")
    trace_id  = state.get("trace_id", "")
    logger.info(f"[{trace_id}] ticket_node thread={thread_id}")

    # Idempotency — no duplicate tickets
    if redis_check_idempotency(thread_id):
        logger.info(f"[{trace_id}] Ticket already exists — skipping")
        return {**state,
                "answer": "A support ticket already exists for this conversation. Your team will respond shortly.",
                "next_action": "done"}

    # Build conversation summary
    summary = "\n".join(
        f"{h['role'].upper()}: {h['content'][:150]}"
        for h in history[-6:]
    ) or "No prior context."

    sources_tried = [
        f"{c.get('doc_title','?')} (score: {c.get('score',0):.2f})"
        for c in chunks[:3]
    ]

    owner_map = {
        "HR & People Operations":             "HR Head",
        "Legal & Compliance":                 "Legal Officer",
        "Finance & Operations":               "Finance Head",
        "Engineering & Operations":           "Engineering Lead",
        "Sales & Customer Facing":            "Sales Head",
        "Security & Information Assurance":   "Security Officer",
        "Data & Analytics":                   "Data Team Lead",
        "IT & Internal Systems":              "IT Head",
        "Platform & Infrastructure Operations": "Platform Head",
        "Product & Design":                   "Product Owner",
        "Marketing & Content":                "Marketing Head",
        "Partnership & Alliances":            "Partner Manager",
        "QA & Testing":                       "QA Lead",
    }
    owner = owner_map.get(dept, "Department Head")

    # Create Notion ticket
    notion_id, notion_url = None, None
    try:
        notion_id, notion_url = create_notion_ticket(
            question             = message,
            priority             = priority,
            department           = dept,
            owner                = owner,
            thread_id            = thread_id,
            evidence_score       = state.get("evidence_score", 0.0),
            sources_tried        = sources_tried,
            conversation_summary = summary,
        )
        redis_set_idempotency(thread_id)
        logger.info(f"[{trace_id}] Ticket created: {notion_id}")
    except Exception as e:
        logger.error(f"[{trace_id}] Ticket creation failed: {e}")

    answer = (
        f"I couldn't find sufficient information in our knowledge base to answer this.\n\n"
        f"**A support ticket has been created:**\n"
        f"- **Priority:** {priority.title()}\n"
        f"- **Assigned to:** {owner}\n"
        f"- **Department:** {dept}\n"
        + (f"- **[View ticket in Notion]({notion_url})**\n" if notion_url else "")
        + f"\nYour team will follow up shortly."
    )

    return {
        **state,
        "answer":          answer,
        "notion_ticket_id": notion_id,
        "notion_url":       notion_url,
        "ticket_status":    "open",
        "next_action":      "done",
    }


# ── NODE 7: memory_save ───────────────────────────────────────────────────

def memory_save(state: AssistantState) -> AssistantState:
    from assistant.memory import (
        db_save_message, db_save_ticket,
        redis_save_messages, redis_save_context,
    )
    thread_id = state["thread_id"]
    trace_id  = state.get("trace_id", "")
    logger.info(f"[{trace_id}] memory_save thread={thread_id}")

    # Save to PostgreSQL
    db_save_message(
        thread_id=thread_id, role="user",
        content=state["message"], intent=state.get("intent"),
        trace_id=trace_id,
    )
    answer = state.get("answer", "")
    if answer:
        db_save_message(
            thread_id=thread_id, role="assistant",
            content=answer, intent=state.get("intent"),
            citations=state.get("citations", []),
            evidence_score=state.get("evidence_score"),
            trace_id=trace_id,
        )

    # Save ticket if created
    if state.get("notion_ticket_id"):
        db_save_ticket(
            thread_id            = thread_id,
            question             = state["message"],
            notion_ticket_id     = state.get("notion_ticket_id"),
            notion_url           = state.get("notion_url", ""),
            status               = "open",
            priority             = state.get("priority", "medium"),
            department           = state.get("department", ""),
            owner                = "",
            evidence_score       = state.get("evidence_score", 0.0),
            sources_tried        = [c.get("doc_title","") for c in state.get("retrieved_chunks",[])[:3]],
            conversation_summary = "",
        )

    # Update Redis
    history = list(state.get("history", []))
    history.append({"role": "user",      "content": state["message"]})
    history.append({"role": "assistant", "content": answer,
                    "citations": state.get("citations", []),
                    "ticket_url": state.get("notion_url")})
    redis_save_messages(thread_id, history)
    redis_save_context(
        thread_id  = thread_id,
        industry   = state.get("industry", ""),
        department = state.get("department", ""),
        user_id    = state.get("user_id", "anonymous"),
    )
    return {**state, "history": history}
# # assistant/nodes.py
# import os, uuid, json, re
# from utils.logger import setup_logger
# from assistant.state import (
#     AssistantState, EVIDENCE_THRESHOLD,
#     get_priority, is_direct_ticket
# )

# logger = setup_logger(__name__)

# AZURE_ENDPOINT    = os.getenv("AZURE_LLM_ENDPOINT", "")
# AZURE_API_KEY     = os.getenv("AZURE_OPENAI_LLM_KEY", "")
# AZURE_API_VERSION = os.getenv("AZURE_LLM_API_VERSION", "2024-02-15-preview")
# AZURE_DEPLOY      = os.getenv("AZURE_LLM_DEPLOYMENT_41_MINI", "")

# _llm = None
# def _get_llm():
#     global _llm
#     if _llm is None:
#         from langchain_openai import AzureChatOpenAI
#         _llm = AzureChatOpenAI(
#             azure_endpoint=AZURE_ENDPOINT, api_key=AZURE_API_KEY,
#             api_version=AZURE_API_VERSION, azure_deployment=AZURE_DEPLOY,
#             temperature=0.1, max_tokens=1000, timeout=30, max_retries=1,
#         )
#     return _llm


# # ── NODE 1: Context Loader ────────────────────────────────────────────────

# def context_loader(state: AssistantState) -> AssistantState:
#     """Load session context from Redis (fast) then PostgreSQL (durable)."""
#     from assistant.memory import (
#         load_messages_from_redis, load_context_from_redis,
#         load_messages_from_db
#     )
#     thread_id = state["thread_id"]
#     trace_id  = state.get("trace_id") or str(uuid.uuid4())[:8]
#     logger.info(f"[{trace_id}] context_loader: thread={thread_id}")

#     # Try Redis first
#     ctx      = load_context_from_redis(thread_id)
#     messages = load_messages_from_redis(thread_id)

#     # Fallback to PostgreSQL
#     if not messages:
#         messages = load_messages_from_db(thread_id, limit=10)

#     return {
#         **state,
#         "trace_id":   trace_id,
#         "history":    messages,
#         "industry":   ctx.get("industry")   or state.get("industry"),
#         "department": ctx.get("department") or state.get("department"),
#     }


# # ── NODE 2: Intent Classifier ─────────────────────────────────────────────

# def intent_classifier(state: AssistantState) -> AssistantState:
#     """Classify user message: clarify / retrieve / ticket."""
#     message   = state["message"]
#     trace_id  = state.get("trace_id", "")
#     history   = state.get("history", [])
#     industry  = state.get("industry", "")
#     dept      = state.get("department", "")

#     logger.info(f"[{trace_id}] intent_classifier: '{message[:60]}'")

#     # Rule-based shortcut — direct ticket keywords
#     if is_direct_ticket(message):
#         logger.info(f"[{trace_id}] Direct ticket triggered by keyword")
#         return {**state, "intent": "ticket",
#                 "priority": get_priority(message), "next_action": "ticket"}

#     # LLM-based classification
#     history_text = "\n".join(
#         f"{m['role'].upper()}: {m['content'][:100]}"
#         for m in history[-4:]
#     )
#     prompt = f"""You are an intent classifier for an enterprise document assistant.

# User context: industry={industry or 'unknown'}, department={dept or 'unknown'}
# Conversation history:
# {history_text or '(none)'}

# Current message: "{message}"

# Classify the intent as ONE of:
# - "clarify" — message is vague, missing key details (industry, doc type, use case)
# - "retrieve" — clear question that can be answered from enterprise documents
# - "ticket"   — asks for something not in docs (pricing, rate cards, live data, HR decisions)

# Reply with ONLY one word: clarify, retrieve, or ticket"""

#     try:
#         intent = _get_llm().invoke(prompt).content.strip().lower()
#         intent = intent if intent in ("clarify", "retrieve", "ticket") else "retrieve"
#     except Exception as e:
#         logger.warning(f"[{trace_id}] Intent LLM error: {e}")
#         intent = "retrieve"

#     logger.info(f"[{trace_id}] Intent: {intent}")
#     return {**state, "intent": intent,
#             "priority": get_priority(message), "next_action": intent}


# # ── NODE 3: Clarify Node ──────────────────────────────────────────────────

# def clarify_node(state: AssistantState) -> AssistantState:
#     """Generate a targeted clarifying question."""
#     message  = state["message"]
#     trace_id = state.get("trace_id", "")
#     logger.info(f"[{trace_id}] clarify_node")

#     prompt = f"""The user said: "{message}"

# Generate ONE short, specific clarifying question to get the missing information needed 
# to answer their request. Focus on: industry, document type, company size, or use case.
# Reply with ONLY the question, no preamble."""

#     try:
#         q = _get_llm().invoke(prompt).content.strip()
#     except Exception as e:
#         q = "Could you provide more details about your industry and the specific document you need?"

#     return {**state, "clarify_question": q,
#             "answer": q, "next_action": "clarify"}


# # ── NODE 4: RAG Retrieval ─────────────────────────────────────────────────

# def rag_retrieval(state: AssistantState) -> AssistantState:
#     """Retrieve chunks from ChromaDB using Project 2's tools."""
#     from rag.tools import search_docs, refine_query

#     message   = state["message"]
#     industry  = state.get("industry")
#     dept      = state.get("department")
#     trace_id  = state.get("trace_id", "")
#     logger.info(f"[{trace_id}] rag_retrieval: '{message[:60]}'")

#     # Refine query
#     try:
#         refined = refine_query(message).get("refined", message)
#     except Exception:
#         refined = message

#     # Build metadata filter
#     meta_filter = {}
#     if industry: meta_filter["industry"]   = industry
#     if dept:     meta_filter["department"] = dept

#     # Search
#     try:
#         result = search_docs(
#             query      = refined,
#             industry   = meta_filter.get("industry"),
#             department = meta_filter.get("department"),
#             top_k      = 5,
#         )
#         chunks = result.get("chunks", [])
#     except Exception as e:
#         logger.error(f"[{trace_id}] Retrieval error: {e}")
#         chunks = []

#     # Compute evidence score = average of top-3 chunk scores
#     if chunks:
#         top_scores    = [c.get("score", 0) for c in chunks[:3]]
#         evidence_score = sum(top_scores) / len(top_scores)
#     else:
#         evidence_score = 0.0

#     logger.info(f"[{trace_id}] Retrieved {len(chunks)} chunks, score={evidence_score:.3f}")

#     next_action = "answer" if evidence_score >= EVIDENCE_THRESHOLD else "ticket"
#     return {
#         **state,
#         "retrieved_chunks": chunks,
#         "evidence_score":   round(evidence_score, 4),
#         "refined_query":    refined,
#         "next_action":      next_action,
#     }


# # ── NODE 5: Answer Node ───────────────────────────────────────────────────

# def answer_node(state: AssistantState) -> AssistantState:
#     """Generate grounded answer from retrieved chunks."""
#     message   = state["message"]
#     chunks    = state.get("retrieved_chunks", [])
#     history   = state.get("history", [])
#     trace_id  = state.get("trace_id", "")
#     logger.info(f"[{trace_id}] answer_node: {len(chunks)} chunks")

#     # Build context
#     context = "\n\n---\n\n".join(
#         f"[Source {i+1}: {c['doc_title']} › {c.get('section','General')}]\n{c['text']}"
#         for i, c in enumerate(chunks)
#     )

#     # History block
#     history_block = ""
#     if history:
#         lines = [f"{h['role'].upper()}: {h['content'][:150]}" for h in history[-4:]]
#         history_block = "Conversation:\n" + "\n".join(lines) + "\n\n"

#     prompt = f"""{history_block}You are a precise enterprise document assistant.
# Answer ONLY using the provided context. If not in context, say so explicitly.

# Context:
# {context}

# Question: {message}

# Instructions:
# - Reference source sections where relevant
# - Be specific and professional
# - End with one sentence confidence rationale

# Answer:"""

#     try:
#         answer = _get_llm().invoke(prompt).content.strip()
#     except Exception as e:
#         answer = f"Error generating answer: {e}"

#     citations = [
#         f"{c['doc_title']} › {c.get('section','General') or 'General'}"
#         for c in chunks
#     ]

#     return {**state, "answer": answer, "citations": citations,
#             "next_action": "memory_save"}


# # ── NODE 6: Ticket Node ───────────────────────────────────────────────────

# def ticket_node(state: AssistantState) -> AssistantState:
#     """Create a Notion support ticket with full context."""
#     from assistant.memory import check_idempotency, set_idempotency
#     from assistant.ticket import create_notion_ticket

#     thread_id = state["thread_id"]
#     message   = state["message"]
#     trace_id  = state.get("trace_id", "")
#     chunks    = state.get("retrieved_chunks", [])
#     history   = state.get("history", [])
#     dept      = state.get("department", "General")
#     priority  = state.get("priority", "medium")

#     logger.info(f"[{trace_id}] ticket_node: thread={thread_id}")

#     # Idempotency check
#     if check_idempotency(thread_id):
#         logger.info(f"[{trace_id}] Ticket already exists for this thread — skipping")
#         return {
#             **state,
#             "answer": "A support ticket already exists for this conversation. Our team will respond shortly.",
#             "next_action": "memory_save",
#         }

#     # Build conversation summary
#     summary_lines = [f"{h['role'].upper()}: {h['content'][:200]}" for h in history[-6:]]
#     conv_summary  = "\n".join(summary_lines) if summary_lines else "No prior context."

#     # Sources tried
#     sources_tried = [
#         f"{c['doc_title']} (score: {c.get('score',0):.2f})"
#         for c in chunks[:3]
#     ]

#     # Determine owner by department
#     owner_map = {
#         "HR & People Operations":    "HR Head",
#         "Legal & Compliance":        "Legal Officer",
#         "Finance & Operations":      "Finance Head",
#         "Engineering & Operations":  "Engineering Lead",
#         "Sales & Customer Facing":   "Sales Head",
#         "Security & Information Assurance": "Security Officer",
#     }
#     owner = owner_map.get(dept, "Department Head")

#     # Create in Notion
#     try:
#         notion_id, notion_url = create_notion_ticket(
#             question          = message,
#             priority          = priority,
#             department        = dept,
#             owner             = owner,
#             thread_id         = thread_id,
#             evidence_score    = state.get("evidence_score", 0.0),
#             sources_tried     = sources_tried,
#             conversation_summary = conv_summary,
#         )
#         set_idempotency(thread_id)
#         logger.info(f"[{trace_id}] Ticket created: {notion_id}")
#     except Exception as e:
#         logger.error(f"[{trace_id}] Ticket creation error: {e}")
#         notion_id  = None
#         notion_url = None

#     answer = (
#         f"I wasn't able to find sufficient information in our documents to answer your question.\n\n"
#         f"I've created a support ticket for your team:\n"
#         f"- **Priority:** {priority.title()}\n"
#         f"- **Assigned to:** {owner}\n"
#         f"- **Department:** {dept}\n"
#         + (f"- **Notion ticket:** [View ticket]({notion_url})\n" if notion_url else "")
#         + f"\nYour team will respond shortly."
#     )

#     return {
#         **state,
#         "answer":           answer,
#         "notion_ticket_id": notion_id,
#         "notion_url":       notion_url,
#         "ticket_status":    "open",
#         "next_action":      "memory_save",
#     }


# # ── NODE 7: Memory Save ───────────────────────────────────────────────────

# def memory_save(state: AssistantState) -> AssistantState:
#     """Persist conversation to PostgreSQL + refresh Redis."""
#     from assistant.memory import (
#         save_message_to_db, save_messages_to_redis,
#         save_context_to_redis, save_ticket_to_db
#     )

#     thread_id = state["thread_id"]
#     trace_id  = state.get("trace_id", "")
#     logger.info(f"[{trace_id}] memory_save: thread={thread_id}")

#     # Save user message
#     save_message_to_db(
#         thread_id=thread_id, role="user",
#         content=state["message"], intent=state.get("intent"),
#         trace_id=trace_id,
#     )

#     # Save assistant response
#     answer = state.get("answer", "")
#     if answer:
#         save_message_to_db(
#             thread_id=thread_id, role="assistant",
#             content=answer, intent=state.get("intent"),
#             citations=state.get("citations", []),
#             evidence_score=state.get("evidence_score"),
#             trace_id=trace_id,
#         )

#     # Save ticket to DB if created
#     if state.get("notion_ticket_id"):
#         save_ticket_to_db(
#             thread_id         = thread_id,
#             question          = state["message"],
#             notion_ticket_id  = state.get("notion_ticket_id"),
#             notion_url        = state.get("notion_url", ""),
#             status            = "open",
#             priority          = state.get("priority", "medium"),
#             department        = state.get("department", ""),
#             owner             = "",
#             evidence_score    = state.get("evidence_score", 0.0),
#             sources_tried     = [c.get("doc_title","") for c in state.get("retrieved_chunks",[])[:3]],
#             conversation_summary = "",
#         )

#     # Update Redis
#     history = state.get("history", [])
#     history.append({"role": "user",      "content": state["message"]})
#     history.append({"role": "assistant", "content": answer})
#     save_messages_to_redis(thread_id, history)
#     save_context_to_redis(
#         thread_id  = thread_id,
#         industry   = state.get("industry", ""),
#         department = state.get("department", ""),
#         user_id    = state.get("user_id", "anonymous"),
#     )

#     return {**state, "history": history}