"""
RAG Chain — LangChain pipeline
Combines search_docs + refine_query + compare_docs tools
with Azure OpenAI for grounded Q&A with citations.
Anti-hallucination: if info not found, says so clearly.
"""

import os
import json
from dotenv import load_dotenv
from utils.logger import setup_logger
from rag.tools import search_docs, refine_query, compare_docs
from cache.redis_service import redis_client

load_dotenv()
logger = setup_logger(__name__)

SYSTEM_PROMPT = """You are DocForge AI Assistant — an expert on business and legal documents.

You have access to a knowledge base of 129 professional documents including NDAs, SLAs, HR policies, compliance reports, and more.

RULES:
1. ALWAYS base your answer on the provided context chunks — never make up information.
2. If the context does not contain enough information, say: "I don't have enough information in the knowledge base to answer this accurately."
3. ALWAYS cite your sources using the format: [Doc Title → Section]
4. Be concise, professional, and accurate.
5. For legal/compliance questions, recommend consulting a professional.

CITATION FORMAT: At the end of your answer, list sources as:
**Sources:**
- [Document Title → Section Name]
"""


def ask(
    question: str,
    session_id: str  = "default",
    filters: dict    = None,
    use_refine: bool = True,
    top_k: int       = 5,
) -> dict:
    filters = filters or {}

    cache_key = f"answer:{hash(f'{question}|{json.dumps(filters, sort_keys=True)}')}"
    cached    = redis_client.get(cache_key)
    if cached:
        logger.info(f"Answer cache HIT: {question[:40]}")
        cached["cached"] = True
        return cached

    refined_query = question
    keywords      = []
    if use_refine:
        refined       = refine_query(question)
        refined_query = refined.get("refined", question)
        keywords      = refined.get("keywords", [])

    search_result = search_docs(
        refined_query,
        doc_type=filters.get("doc_type"),
        department=filters.get("department"),
        industry=filters.get("industry"),
        top_k=top_k,
    )
    chunks = search_result.get("chunks", [])

    if not chunks:
        answer = (
            "I don't have enough information in the knowledge base to answer this accurately. "
            "Try different keywords or remove filters."
        )
        result = {
            "question": question, "answer": answer,
            "chunks": [], "citations": [],
            "refined_query": refined_query,
            "cached": False, "session_id": session_id,
        }
        redis_client.append_session(session_id, "user",      question)
        redis_client.append_session(session_id, "assistant", answer)
        return result

    context_parts = []
    citations     = []
    for i, chunk in enumerate(chunks, 1):
        citation = chunk.get("citation", "Unknown")
        citations.append(citation)
        context_parts.append(f"[{i}] {citation}\n{chunk['text']}\n")
    context = "\n---\n".join(context_parts)

    history = redis_client.get_session(session_id)
    answer  = _generate_answer(question, context, history)

    redis_client.append_session(session_id, "user",      question)
    redis_client.append_session(session_id, "assistant", answer)

    result = {
        "question":      question,
        "answer":        answer,
        "chunks":        chunks,
        "citations":     list(dict.fromkeys(citations)),
        "refined_query": refined_query,
        "keywords":      keywords,
        "cached":        False,
        "session_id":    session_id,
        "filters":       filters,
    }

    redis_client.set(cache_key, result, ttl=1800)
    logger.info(f"Answer generated for: {question[:40]}")
    return result


def _generate_answer(question: str, context: str, history: list) -> str:
    try:
        from openai import AzureOpenAI
        import httpx

        client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_LLM_ENDPOINT", "").rstrip("/"),
            api_key=(
                os.getenv("AZURE_OPENAI_LLM_KEY")
                or os.getenv("AZURE_OPENAI_API_KEY")
            ),
            api_version=os.getenv("AZURE_LLM_API_VERSION", "2025-01-01-preview"),
            http_client=httpx.Client(),
        )

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in history[-4:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({
            "role": "user",
            "content": f"""Context from knowledge base:
{context[:4000]}

Question: {question}

Answer based ONLY on the context above. If information is missing, say so clearly."""
        })

        response = client.chat.completions.create(
            model=os.getenv("AZURE_LLM_DEPLOYMENT_41_MINI", "gpt-4.1-mini"),
            messages=messages,
            temperature=0.2,
            max_tokens=800,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"Answer generation failed: {e}")
        return (
            "I encountered an error generating the answer. "
            "Please check the retrieved chunks below for relevant information."
        )


def compare(query: str, doc_type_a: str, doc_type_b: str, department: str = None, session_id: str = "default") -> dict:
    result = compare_docs(query, doc_type_a, doc_type_b, department)
    redis_client.append_session(session_id, "user", f"Compare {doc_type_a} vs {doc_type_b}: {query}")
    redis_client.append_session(session_id, "assistant", result.get("comparison", ""))
    return result


def get_session_history(session_id: str) -> list:
    return redis_client.get_session(session_id)


def clear_session(session_id: str) -> None:
    redis_client.clear_session(session_id)
    logger.info(f"Session cleared: {session_id}")