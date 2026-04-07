# rag/tools.py
import hashlib, os, json, re
from typing import Optional
from utils.logger import setup_logger

logger = setup_logger(__name__)

AZURE_ENDPOINT    = os.getenv("AZURE_LLM_ENDPOINT", "")
AZURE_API_KEY     = os.getenv("AZURE_OPENAI_LLM_KEY", "")
AZURE_API_VERSION = os.getenv("AZURE_LLM_API_VERSION", "2024-02-15-preview")
AZURE_CHAT_DEPLOY = os.getenv("AZURE_LLM_DEPLOYMENT_41_MINI", "")


def _build_filter(doc_type=None, department=None,
                  industry=None, version=None) -> Optional[dict]:
    conditions = []
    if doc_type:   conditions.append({"doc_type":   {"$eq": doc_type}})
    if department: conditions.append({"department": {"$eq": department}})
    if industry:   conditions.append({"industry":   {"$eq": industry}})
    if version:    conditions.append({"version":    {"$eq": version}})
    if not conditions:
        return None
    return conditions[0] if len(conditions) == 1 else {"$and": conditions}


def _cache_key(*parts) -> str:
    return hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()


# ── search_docs ───────────────────────────────────────────────────────────

def search_docs(query: str, doc_type=None, department=None,
                industry=None, version=None, top_k: int = 5) -> dict:
    from cache.redis_service import redis_client
    from rag.vector_store import vector_store

    key    = _cache_key("search", query, doc_type, department, industry, version, top_k)
    cached = redis_client.get(key)
    if cached:
        cached["cached"] = True
        return cached

    where  = _build_filter(doc_type, department, industry, version)
    chunks = vector_store.similarity_search(query, k=top_k, where=where)

    result = {"chunks": chunks, "cached": False}
    redis_client.set(key, result, ttl=300)
    return result


# ── refine_query ──────────────────────────────────────────────────────────

def refine_query(query: str, context: str = "") -> dict:
    """
    Always returns dict with ALL 4 keys:
    { original, refined, keywords, suggestions }
    This prevents KeyError: 'original' in the UI.
    """
    from cache.redis_service import redis_client

    key    = _cache_key("refine", query, context[:50])
    cached = redis_client.get(key)
    if cached:
        cached.setdefault("original",    query)
        cached.setdefault("refined",     query)
        cached.setdefault("keywords",    [])
        cached.setdefault("suggestions", [])
        return cached

    # Safe default — used if LLM fails
    default = {
        "original":    query,
        "refined":     query,
        "keywords":    [w for w in query.split() if len(w) > 3][:3],
        "suggestions": [query],
    }

    try:
        from langchain_openai import AzureChatOpenAI
        llm = AzureChatOpenAI(
            azure_endpoint   = AZURE_ENDPOINT,
            api_key          = AZURE_API_KEY,
            api_version      = AZURE_API_VERSION,
            azure_deployment = AZURE_CHAT_DEPLOY,
            temperature      = 0,
            max_tokens       = 200,
        )

        prompt = f"""Rewrite this search query for better legal/business document retrieval.

Original query: {query}
Context: {context or 'none'}

Return ONLY valid JSON (no markdown, no explanation):
{{
  "original": "{query}",
  "refined": "<precise 5-15 word query>",
  "keywords": ["word1", "word2", "word3"],
  "suggestions": ["alt query 1", "alt query 2"]
}}"""

        raw    = llm.invoke(prompt).content.strip()
        raw    = re.sub(r"```json|```", "", raw).strip()
        result = json.loads(raw)

        # Guarantee all 4 keys
        result["original"]    = query   # always use actual original
        result.setdefault("refined",     query)
        result.setdefault("keywords",    [])
        result.setdefault("suggestions", [])

    except Exception as e:
        logger.warning(f"refine_query LLM error: {e}")
        result = default

    redis_client.set(key, result, ttl=600)
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

{type_a} content:
{ctx_a[:1500]}

{type_b} content:
{ctx_b[:1500]}

Return a JSON object ONLY with this exact structure:
{{
  "doc_a_points": ["point 1 about {type_a}", "point 2", "point 3"],
  "doc_b_points": ["point 1 about {type_b}", "point 2", "point 3"],
  "similarities": ["similarity 1", "similarity 2"],
  "differences": ["difference 1", "difference 2"],
  "recommendation": "Which document is better for what use case"
}}

JSON only, no explanation, no markdown."""

        response = client.chat.completions.create(
            model=os.getenv("AZURE_LLM_DEPLOYMENT_41_MINI", "gpt-4.1-mini"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=800,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.warning(f"Comparison LLM failed: {e}")
        return '{}'
    