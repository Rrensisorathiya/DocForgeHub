# rag/chain.py
import os, hashlib
from typing import Optional
from utils.logger import setup_logger

logger = setup_logger(__name__)

AZURE_ENDPOINT    = os.getenv("AZURE_LLM_ENDPOINT", "")
AZURE_API_KEY     = os.getenv("AZURE_OPENAI_LLM_KEY", "")
AZURE_API_VERSION = os.getenv("AZURE_LLM_API_VERSION", "2024-02-15-preview")
AZURE_CHAT_DEPLOY = os.getenv("AZURE_LLM_DEPLOYMENT_41_MINI", "")

_llm = None

def _get_llm():
    global _llm
    if _llm is None:
        from langchain_openai import AzureChatOpenAI
        _llm = AzureChatOpenAI(
            azure_endpoint   = AZURE_ENDPOINT,
            api_key          = AZURE_API_KEY,
            api_version      = AZURE_API_VERSION,
            azure_deployment = AZURE_CHAT_DEPLOY,
            temperature      = 0.1,
            max_tokens       = 2000,
        )
    return _llm


# ── session helpers ──────────────────────────────────────────────────────

def get_session_history(session_id: str) -> list:
    from cache.redis_service import redis_client
    data = redis_client.get(f"session:{session_id}")
    return data if isinstance(data, list) else []


def _save_session(session_id: str, history: list):
    from cache.redis_service import redis_client
    redis_client.set(f"session:{session_id}", history[-10:], ttl=3600)


def clear_session(session_id: str):
    from cache.redis_service import redis_client
    redis_client.delete(f"session:{session_id}")


# ── answer prompt ─────────────────────────────────────────────────────────

ANSWER_PROMPT = """\
You are a precise enterprise document assistant for DocForgeHub.
Answer ONLY using the provided context. If the answer is not in the context,
say exactly: "The information is not available in the retrieved documents."

NEVER fabricate facts, clauses, numbers, or dates not present in the context.

Context:
{context}

{history_block}Question: {question}

Instructions:
- Be specific and reference the source sections where relevant
- Use clear, professional language
- If multiple sources say different things, note the discrepancy
- End with ONE sentence rationale about your confidence level

Answer:"""


# ── core ask ─────────────────────────────────────────────────────────────

def ask(question: str, session_id: str = "default", filters: dict = None,
        use_refine: bool = True, top_k: int = 5) -> dict:
    from rag.tools import search_docs, refine_query
    from cache.redis_service import redis_client

    filters = filters or {}

    # 1. refine
    refined_query = question
    keywords      = []
    if use_refine:
        refine_result = refine_query(question)
        refined_query = refine_result.get("refined", question)
        keywords      = refine_result.get("keywords", [])

    # 2. cache check
    cache_key = hashlib.md5(
        (refined_query + str(filters) + str(top_k)).encode()
    ).hexdigest()
    cached = redis_client.get(f"answer:{cache_key}")
    if cached:
        cached["cached"]     = True
        cached["session_id"] = session_id
        return cached

    # 3. retrieve
    search_result = search_docs(
        query      = refined_query,
        doc_type   = filters.get("doc_type"),
        department = filters.get("department"),
        industry   = filters.get("industry"),
        top_k      = top_k,
    )
    chunks = search_result.get("chunks", [])

    # 4. no chunks
    if not chunks:
        return {
            "question":      question,
            "answer":        "The information is not available in the retrieved documents. "
                             "Ensure Notion documents are ingested via POST /rag/ingest.",
            "citations":     [],
            "chunks":        [],
            "refined_query": refined_query,
            "keywords":      keywords,
            "cached":        False,
            "session_id":    session_id,
        }

    # 5. build context
    context_parts = []
    for i, c in enumerate(chunks, 1):
        context_parts.append(
            f"[Source {i}: {c['doc_title']} › {c.get('section', 'General')}]\n{c['text']}"
        )
    context_text = "\n\n---\n\n".join(context_parts)

    # 6. session history
    history       = get_session_history(session_id)
    history_block = ""
    if history:
        lines = []
        for h in history[-4:]:
            role = "User" if h["role"] == "user" else "Assistant"
            lines.append(f"{role}: {h['content'][:200]}")
        history_block = "Conversation history:\n" + "\n".join(lines) + "\n\n"

    # 7. generate
    prompt_text = ANSWER_PROMPT.format(
        context       = context_text,
        history_block = history_block,
        question      = question,
    )
    try:
        answer = _get_llm().invoke(prompt_text).content.strip()
    except Exception as e:
        logger.error(f"LLM error: {e}")
        answer = f"LLM error: {str(e)}"

    # 8. citations — CLEAN STRING FORMAT for UI display
    # Format: "Doc Title › Section"  (user-friendly, not raw dict)
    citations = [
        f"{c['doc_title']} › {c.get('section', 'General') or 'General'}"
        for c in chunks
    ]

    # 9. save session + cache
    history.append({"role": "user",      "content": question})
    history.append({"role": "assistant", "content": answer})
    _save_session(session_id, history)

    result = {
        "question":      question,
        "answer":        answer,
        "citations":     citations,        # list of clean strings
        "chunks":        chunks,
        "refined_query": refined_query,
        "keywords":      keywords,
        "cached":        False,
        "session_id":    session_id,
    }
    redis_client.set(f"answer:{cache_key}", result, ttl=300)
    return result


# ── compare ──────────────────────────────────────────────────────────────

COMPARE_PROMPT = """\
Compare these two answers about '{query}' from two different document types.

{doc_a} answer:
{answer_a}

{doc_b} answer:
{answer_b}

Write a concise 3-5 sentence comparison:
- Key similarities
- Key differences
- Which document is more comprehensive on this topic and why

Be specific about clauses, obligations, or missing information."""


def compare(query: str, doc_type_a: str, doc_type_b: str,
            department: Optional[str] = None, session_id: str = "default") -> dict:
    from rag.tools import search_docs, refine_query

    refined = refine_query(query).get("refined", query)

    result_a = search_docs(query=refined, doc_type=doc_type_a, department=department, top_k=5)
    result_b = search_docs(query=refined, doc_type=doc_type_b, department=department, top_k=5)

    chunks_a = result_a.get("chunks", [])
    chunks_b = result_b.get("chunks", [])

    def _build_answer(chunks, doc_type):
        if not chunks:
            return f"No documents of type '{doc_type}' found in the knowledge base."
        ctx = "\n\n---\n\n".join(
            f"[{c['doc_title']} › {c.get('section','')}]\n{c['text']}" for c in chunks
        )
        prompt = (
            f"Answer this question using ONLY the context below. Be concise.\n"
            f"Context: {ctx}\nQuestion: {query}\nAnswer:"
        )
        try:
            return _get_llm().invoke(prompt).content.strip()
        except Exception as e:
            return f"Error: {e}"

    answer_a = _build_answer(chunks_a, doc_type_a)
    answer_b = _build_answer(chunks_b, doc_type_b)

    try:
        comparison = _get_llm().invoke(
            COMPARE_PROMPT.format(
                query=query, doc_a=doc_type_a, doc_b=doc_type_b,
                answer_a=answer_a, answer_b=answer_b,
            )
        ).content.strip()
    except Exception as e:
        comparison = f"Comparison error: {e}"

    # Citations as clean strings
    citations_a = [
        f"{c['doc_title']} › {c.get('section','General') or 'General'}"
        for c in chunks_a
    ]
    citations_b = [
        f"{c['doc_title']} › {c.get('section','General') or 'General'}"
        for c in chunks_b
    ]

    return {
        "doc_a": {
            "type":      doc_type_a,
            "answer":    answer_a,
            "citations": citations_a,
            "chunks":    len(chunks_a),
        },
        "doc_b": {
            "type":      doc_type_b,
            "answer":    answer_b,
            "citations": citations_b,
            "chunks":    len(chunks_b),
        },
        "comparison": comparison,
    }
# # rag/chain.py
# import os, hashlib
# from typing import Optional
# from utils.logger import setup_logger

# logger = setup_logger(__name__)

# AZURE_ENDPOINT    = os.getenv("AZURE_LLM_ENDPOINT", "")
# AZURE_API_KEY     = os.getenv("AZURE_OPENAI_LLM_KEY", "")
# AZURE_API_VERSION = os.getenv("AZURE_LLM_API_VERSION", "2024-02-15-preview")
# AZURE_CHAT_DEPLOY = os.getenv("AZURE_LLM_DEPLOYMENT_41_MINI", "")


# # ── LLM singleton ────────────────────────────────────────────────────────
# _llm = None

# def _get_llm():
#     global _llm
#     if _llm is None:
#         from langchain_openai import AzureChatOpenAI
#         _llm = AzureChatOpenAI(
#             azure_endpoint   = AZURE_ENDPOINT,
#             api_key          = AZURE_API_KEY,
#             api_version      = AZURE_API_VERSION,
#             azure_deployment = AZURE_CHAT_DEPLOY,
#             temperature      = 0.1,
#             max_tokens       = 2000,
#         )
#     return _llm


# # ── session helpers ──────────────────────────────────────────────────────

# def get_session_history(session_id: str) -> list:
#     from cache.redis_service import redis_client
#     data = redis_client.get(f"session:{session_id}")
#     return data if isinstance(data, list) else []


# def _save_session(session_id: str, history: list):
#     from cache.redis_service import redis_client
#     redis_client.set(f"session:{session_id}", history[-10:], ttl=3600)


# def clear_session(session_id: str):
#     from cache.redis_service import redis_client
#     redis_client.delete(f"session:{session_id}")


# # ── core: ask ────────────────────────────────────────────────────────────

# ANSWER_PROMPT = """\
# You are a precise enterprise document assistant for DocForgeHub.
# Answer ONLY using the provided context. If the answer is not in the context,
# say exactly: "The information is not available in the retrieved documents."

# NEVER fabricate facts, clauses, numbers, or dates not present in the context.

# Context:
# {context}

# {history_block}Question: {question}

# Instructions:
# - Be specific and reference the source sections where relevant
# - Use clear, professional language
# - If multiple sources say different things, note the discrepancy
# - End with ONE sentence rationale about your confidence level

# Answer:"""


# def ask(question: str, session_id: str = "default", filters: dict = None,
#         use_refine: bool = True, top_k: int = 5) -> dict:
#     """
#     Main RAG chain:
#     1. (optional) refine query
#     2. retrieve top-K chunks
#     3. generate grounded answer with citations
#     4. cache result + update session history
#     """
#     from rag.tools import search_docs, refine_query
#     from cache.redis_service import redis_client

#     filters = filters or {}

#     # ── 1. refine ────────────────────────────────────────────────────────
#     refined_query = question
#     keywords      = []
#     if use_refine:
#         refine_result = refine_query(question)
#         refined_query = refine_result.get("refined", question)
#         keywords      = refine_result.get("keywords", [])
#         logger.debug(f"Refined: '{question}' → '{refined_query}'")

#     # ── 2. cache check for full answer ───────────────────────────────────
#     cache_key = hashlib.md5(
#         (refined_query + str(filters) + str(top_k)).encode()
#     ).hexdigest()
#     ans_key   = f"answer:{cache_key}"
#     cached    = redis_client.get(ans_key)
#     if cached:
#         logger.debug("Cache HIT for answer")
#         cached["cached"]     = True
#         cached["session_id"] = session_id
#         return cached

#     # ── 3. retrieve ───────────────────────────────────────────────────────
#     search_result = search_docs(
#         query      = refined_query,
#         doc_type   = filters.get("doc_type"),
#         department = filters.get("department"),
#         industry   = filters.get("industry"),
#         top_k      = top_k,
#     )
#     chunks = search_result.get("chunks", [])

#     # ── 4. build context ─────────────────────────────────────────────────
#     if not chunks:
#         return {
#             "question":      question,
#             "answer":        "The information is not available in the retrieved documents. "
#                              "Ensure Notion documents are ingested via POST /rag/ingest.",
#             "citations":     [],
#             "chunks":        [],
#             "refined_query": refined_query,
#             "keywords":      keywords,
#             "cached":        False,
#             "session_id":    session_id,
#         }

#     context_parts = []
#     for i, c in enumerate(chunks, 1):
#         context_parts.append(
#             f"[Source {i}: {c['doc_title']} › {c.get('section', 'General')}]\n{c['text']}"
#         )
#     context_text = "\n\n---\n\n".join(context_parts)

#     # ── 5. session history ────────────────────────────────────────────────
#     history     = get_session_history(session_id)
#     history_block = ""
#     if history:
#         lines = []
#         for h in history[-4:]:
#             role  = "User" if h["role"] == "user" else "Assistant"
#             lines.append(f"{role}: {h['content'][:200]}")
#         history_block = "Conversation history:\n" + "\n".join(lines) + "\n\n"

#     # ── 6. generate ───────────────────────────────────────────────────────
#     prompt_text = ANSWER_PROMPT.format(
#         context      = context_text,
#         history_block= history_block,
#         question     = question,
#     )

#     try:
#         llm    = _get_llm()
#         answer = llm.invoke(prompt_text).content.strip()
#     except Exception as e:
#         logger.error(f"LLM invoke error: {e}")
#         answer = f"LLM error: {str(e)}"

#     # ── 7. build citations ────────────────────────────────────────────────
#     citations = [
#         {
#             "doc_title": c["doc_title"],
#             "section":   c.get("section", ""),
#             "score":     c["score"],
#             "page_id":   c.get("page_id", ""),
#         }
#         for c in chunks
#     ]

#     # ── 8. save session + cache ───────────────────────────────────────────
#     history.append({"role": "user",      "content": question})
#     history.append({"role": "assistant", "content": answer})
#     _save_session(session_id, history)

#     result = {
#         "question":      question,
#         "answer":        answer,
#         "citations":     citations,
#         "chunks":        chunks,
#         "refined_query": refined_query,
#         "keywords":      keywords,
#         "cached":        False,
#         "session_id":    session_id,
#     }
#     redis_client.set(ans_key, result, ttl=300)
#     return result


# # ── core: compare ────────────────────────────────────────────────────────

# COMPARE_PROMPT = """\
# Compare these two answers about '{query}' from two different document types.

# {doc_a} answer:
# {answer_a}

# {doc_b} answer:
# {answer_b}

# Write a concise 3-5 sentence comparison:
# - Key similarities
# - Key differences
# - Which document is more comprehensive on this topic and why

# Be specific about clauses, obligations, or missing information."""


# def compare(query: str, doc_type_a: str, doc_type_b: str,
#             department: Optional[str] = None, session_id: str = "default") -> dict:
#     """
#     Run two parallel RAG retrievals and compare the answers side by side.
#     """
#     from rag.tools import search_docs, refine_query

#     refined = refine_query(query).get("refined", query)

#     result_a = search_docs(query=refined, doc_type=doc_type_a, department=department, top_k=5)
#     result_b = search_docs(query=refined, doc_type=doc_type_b, department=department, top_k=5)

#     chunks_a = result_a.get("chunks", [])
#     chunks_b = result_b.get("chunks", [])

#     # build individual answers
#     def _build_answer(chunks, doc_type):
#         if not chunks:
#             return f"No documents of type '{doc_type}' found in the knowledge base."
#         ctx = "\n\n---\n\n".join(
#             f"[{c['doc_title']} › {c.get('section','')}]\n{c['text']}" for c in chunks
#         )
#         prompt = f"""Answer this question using ONLY the context below. Be concise.
# Context: {ctx}
# Question: {query}
# Answer:"""
#         try:
#             return _get_llm().invoke(prompt).content.strip()
#         except Exception as e:
#             return f"Error: {e}"

#     answer_a = _build_answer(chunks_a, doc_type_a)
#     answer_b = _build_answer(chunks_b, doc_type_b)

#     # compare
#     try:
#         comparison = _get_llm().invoke(
#             COMPARE_PROMPT.format(
#                 query=query, doc_a=doc_type_a, doc_b=doc_type_b,
#                 answer_a=answer_a, answer_b=answer_b,
#             )
#         ).content.strip()
#     except Exception as e:
#         comparison = f"Comparison error: {e}"

#     citations_a = [{"doc_title": c["doc_title"], "section": c.get("section",""), "score": c["score"]} for c in chunks_a]
#     citations_b = [{"doc_title": c["doc_title"], "section": c.get("section",""), "score": c["score"]} for c in chunks_b]

#     return {
#         "doc_a": {"type": doc_type_a, "answer": answer_a, "citations": citations_a, "chunks": chunks_a},
#         "doc_b": {"type": doc_type_b, "answer": answer_b, "citations": citations_b, "chunks": chunks_b},
#         "comparison": comparison,
#     }
# """
# RAG Chain — LangChain pipeline
# Combines search_docs + refine_query + compare_docs tools
# with Azure OpenAI for grounded Q&A with citations.
# Anti-hallucination: if info not found, says so clearly.
# """

# import os
# import json
# from dotenv import load_dotenv
# from utils.logger import setup_logger
# from rag.tools import search_docs, refine_query, compare_docs
# from cache.redis_service import redis_client

# load_dotenv()
# logger = setup_logger(__name__)

# SYSTEM_PROMPT = """You are DocForge AI Assistant — an expert on business and legal documents.

# You have access to a knowledge base of 129 professional documents including NDAs, SLAs, HR policies, compliance reports, and more.

# RULES:
# 1. ALWAYS base your answer on the provided context chunks — never make up information.
# 2. If the context does not contain enough information, say: "I don't have enough information in the knowledge base to answer this accurately."
# 3. ALWAYS cite your sources using the format: [Doc Title → Section]
# 4. Be concise, professional, and accurate.
# 5. For legal/compliance questions, recommend consulting a professional.

# CITATION FORMAT: At the end of your answer, list sources as:
# **Sources:**
# - [Document Title → Section Name]
# """


# def ask(
#     question: str,
#     session_id: str  = "default",
#     filters: dict    = None,
#     use_refine: bool = True,
#     top_k: int       = 5,
# ) -> dict:
#     filters = filters or {}

#     cache_key = f"answer:{hash(f'{question}|{json.dumps(filters, sort_keys=True)}')}"
#     cached    = redis_client.get(cache_key)
#     if cached:
#         logger.info(f"Answer cache HIT: {question[:40]}")
#         cached["cached"] = True
#         return cached

#     refined_query = question
#     keywords      = []
#     if use_refine:
#         refined       = refine_query(question)
#         refined_query = refined.get("refined", question)
#         keywords      = refined.get("keywords", [])

#     search_result = search_docs(
#         refined_query,
#         doc_type=filters.get("doc_type"),
#         department=filters.get("department"),
#         industry=filters.get("industry"),
#         top_k=top_k,
#     )
#     chunks = search_result.get("chunks", [])

#     if not chunks:
#         answer = (
#             "I don't have enough information in the knowledge base to answer this accurately. "
#             "Try different keywords or remove filters."
#         )
#         result = {
#             "question": question, "answer": answer,
#             "chunks": [], "citations": [],
#             "refined_query": refined_query,
#             "cached": False, "session_id": session_id,
#         }
#         redis_client.append_session(session_id, "user",      question)
#         redis_client.append_session(session_id, "assistant", answer)
#         return result

#     context_parts = []
#     citations     = []
#     for i, chunk in enumerate(chunks, 1):
#         citation = chunk.get("citation", "Unknown")
#         citations.append(citation)
#         context_parts.append(f"[{i}] {citation}\n{chunk['text']}\n")
#     context = "\n---\n".join(context_parts)

#     history = redis_client.get_session(session_id)
#     answer  = _generate_answer(question, context, history)

#     redis_client.append_session(session_id, "user",      question)
#     redis_client.append_session(session_id, "assistant", answer)

#     result = {
#         "question":      question,
#         "answer":        answer,
#         "chunks":        chunks,
#         "citations":     list(dict.fromkeys(citations)),
#         "refined_query": refined_query,
#         "keywords":      keywords,
#         "cached":        False,
#         "session_id":    session_id,
#         "filters":       filters,
#     }

#     redis_client.set(cache_key, result, ttl=1800)
#     logger.info(f"Answer generated for: {question[:40]}")
#     return result


# def _generate_answer(question: str, context: str, history: list) -> str:
#     try:
#         from openai import AzureOpenAI
#         import httpx

#         client = AzureOpenAI(
#             azure_endpoint=os.getenv("AZURE_LLM_ENDPOINT", "").rstrip("/"),
#             api_key=(
#                 os.getenv("AZURE_OPENAI_LLM_KEY")
#                 or os.getenv("AZURE_OPENAI_API_KEY")
#             ),
#             api_version=os.getenv("AZURE_LLM_API_VERSION", "2025-01-01-preview"),
#             http_client=httpx.Client(),
#         )

#         messages = [{"role": "system", "content": SYSTEM_PROMPT}]
#         for msg in history[-4:]:
#             messages.append({"role": msg["role"], "content": msg["content"]})

#         messages.append({
#             "role": "user",
#             "content": f"""Context from knowledge base:
# {context[:4000]}

# Question: {question}

# Answer based ONLY on the context above. If information is missing, say so clearly."""
#         })

#         response = client.chat.completions.create(
#             model=os.getenv("AZURE_LLM_DEPLOYMENT_41_MINI", "gpt-4.1-mini"),
#             messages=messages,
#             temperature=0.2,
#             max_tokens=800,
#         )
#         return response.choices[0].message.content.strip()

#     except Exception as e:
#         logger.error(f"Answer generation failed: {e}")
#         return (
#             "I encountered an error generating the answer. "
#             "Please check the retrieved chunks below for relevant information."
#         )


# def compare(query: str, doc_type_a: str, doc_type_b: str, department: str = None, session_id: str = "default") -> dict:
#     result = compare_docs(query, doc_type_a, doc_type_b, department)
#     redis_client.append_session(session_id, "user", f"Compare {doc_type_a} vs {doc_type_b}: {query}")
#     redis_client.append_session(session_id, "assistant", result.get("comparison", ""))
#     return result


# def get_session_history(session_id: str) -> list:
#     return redis_client.get_session(session_id)


# def clear_session(session_id: str) -> None:
#     redis_client.clear_session(session_id)
#     logger.info(f"Session cleared: {session_id}")