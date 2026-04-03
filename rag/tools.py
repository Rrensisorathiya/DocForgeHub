"""
RAG Tools — 3 tools for LangChain agent
1. search_docs    — vector search + metadata filters
2. refine_query   — rewrite query for better retrieval
3. compare_docs   — side-by-side comparison of 2 documents
"""

import os
import json
from dotenv import load_dotenv
from utils.logger import setup_logger
from rag.vector_store import vector_store
from cache.redis_service import redis_client

load_dotenv()
logger = setup_logger(__name__)


def search_docs(
    query: str,
    doc_type: str   = None,
    department: str = None,
    industry: str   = None,
    version: str    = None,
    top_k: int      = 5,
) -> dict:
    filters = {}
    if doc_type:   filters["doc_type"]   = doc_type
    if department: filters["department"] = department
    if industry:   filters["industry"]   = industry
    if version:    filters["version"]    = version

    cached = redis_client.get_retrieval(query, filters)
    if cached:
        logger.info(f"Cache HIT for query: {query[:40]}")
        return {"query": query, "chunks": cached, "cached": True, "filters": filters}

    chunks = vector_store.search(query, top_k=top_k, filters=filters or None)

    if not chunks:
        return {
            "query":   query,
            "chunks":  [],
            "cached":  False,
            "filters": filters,
            "message": "No relevant documents found. Try different keywords or remove filters.",
        }

    redis_client.set_retrieval(query, filters, chunks)
    logger.info(f"search_docs: '{query[:40]}' → {len(chunks)} chunks")
    return {"query": query, "chunks": chunks, "cached": False, "filters": filters}


def refine_query(original_query: str, context: str = "") -> dict:
    cache_key = f"refine:{hash(original_query)}"
    cached    = redis_client.get(cache_key)
    if cached:
        return cached

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

        prompt = f"""You are a search query optimizer for a legal/business document retrieval system.

User query: "{original_query}"
{f'Context: {context}' if context else ''}

Return a JSON object with:
1. "refined": A clearer, more specific version of the query
2. "keywords": List of 3-5 key terms for search
3. "suggestions": 2-3 alternative search queries

JSON only, no explanation."""

        response = client.chat.completions.create(
            model=os.getenv("AZURE_LLM_DEPLOYMENT_41_MINI", "gpt-4.1-mini"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300,
        )

        content = response.choices[0].message.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        parsed = json.loads(content)
        result = {
            "original":    original_query,
            "refined":     parsed.get("refined", original_query),
            "keywords":    parsed.get("keywords", []),
            "suggestions": parsed.get("suggestions", []),
        }

    except Exception as e:
        logger.warning(f"refine_query LLM failed: {e} — using original")
        result = {
            "original":    original_query,
            "refined":     original_query,
            "keywords":    original_query.split()[:5],
            "suggestions": [],
        }

    redis_client.set(cache_key, result, ttl=3600)
    logger.info(f"refine_query: '{original_query[:40]}' → '{result['refined'][:40]}'")
    return result


def compare_docs(query: str, doc_type_a: str, doc_type_b: str, department: str = None) -> dict:
    cache_key = f"compare:{hash(f'{query}|{doc_type_a}|{doc_type_b}')}"
    cached    = redis_client.get(cache_key)
    if cached:
        return cached

    filters_a = {"doc_type": doc_type_a}
    filters_b = {"doc_type": doc_type_b}
    if department:
        filters_a["department"] = department
        filters_b["department"] = department

    chunks_a = vector_store.search(query, top_k=3, filters=filters_a)
    chunks_b = vector_store.search(query, top_k=3, filters=filters_b)

    if not chunks_a and not chunks_b:
        return {
            "query":      query,
            "doc_a":      {"type": doc_type_a, "chunks": [], "citations": []},
            "doc_b":      {"type": doc_type_b, "chunks": [], "citations": []},
            "comparison": f"No content found for either {doc_type_a} or {doc_type_b}.",
        }

    ctx_a = "\n".join([c["text"] for c in chunks_a]) if chunks_a else "No content found."
    ctx_b = "\n".join([c["text"] for c in chunks_b]) if chunks_b else "No content found."

    comparison_text = _generate_comparison(query, doc_type_a, ctx_a, doc_type_b, ctx_b)

    result = {
        "query": query,
        "doc_a": {"type": doc_type_a, "chunks": chunks_a, "citations": [c["citation"] for c in chunks_a]},
        "doc_b": {"type": doc_type_b, "chunks": chunks_b, "citations": [c["citation"] for c in chunks_b]},
        "comparison": comparison_text,
    }

    redis_client.set(cache_key, result, ttl=1800)
    logger.info(f"compare_docs: {doc_type_a} vs {doc_type_b}")
    return result


def _generate_comparison(query: str, type_a: str, ctx_a: str, type_b: str, ctx_b: str) -> str:
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

        prompt = f"""Compare these two documents regarding: "{query}"

{type_a}:
{ctx_a[:1500]}

{type_b}:
{ctx_b[:1500]}

Provide a clear, structured comparison covering:
1. Key similarities
2. Key differences
3. Which is more suitable for specific use cases

Be concise and cite specific clauses where possible."""

        response = client.chat.completions.create(
            model=os.getenv("AZURE_LLM_DEPLOYMENT_41_MINI", "gpt-4.1-mini"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=600,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.warning(f"Comparison LLM failed: {e}")
        return f"Comparison generated from retrieved content. {type_a} and {type_b} differ in scope and application."