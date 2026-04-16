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


"""
Replace these 2 functions in rag/tools.py:
1. compare_docs()
2. _generate_comparison()
"""


def compare_docs(query: str, doc_type_a: str, doc_type_b: str, department: str = None) -> dict:
    """Compare two document types — no cache, fresh result every time."""
    import os
    from utils.logger import setup_logger
    from rag.vector_store import vector_store
    logger = setup_logger(__name__)

    filters_a = {"doc_type": doc_type_a}
    filters_b = {"doc_type": doc_type_b}
    if department:
        filters_a["department"] = department
        filters_b["department"] = department

    chunks_a = vector_store.similarity_search(query, k=4, where=filters_a)
    chunks_b = vector_store.similarity_search(query, k=4, where=filters_b)

    # Deduplicate citations
    cit_a = list(dict.fromkeys([c["citation"] for c in chunks_a])) if chunks_a else []
    cit_b = list(dict.fromkeys([c["citation"] for c in chunks_b])) if chunks_b else []

    if not chunks_a and not chunks_b:
        return {
            "query":   query,
            "doc_a":   {"type": doc_type_a, "chunks": [], "citations": []},
            "doc_b":   {"type": doc_type_b, "chunks": [], "citations": []},
            "comparison": "{}",
        }

    ctx_a = "\n\n".join([c["text"] for c in chunks_a]) if chunks_a else "No content found."
    ctx_b = "\n\n".join([c["text"] for c in chunks_b]) if chunks_b else "No content found."

    comparison_json = _generate_comparison(query, doc_type_a, ctx_a, doc_type_b, ctx_b)

    logger.info(f"compare_docs: {doc_type_a} vs {doc_type_b} | query: {query}")

    return {
        "query": query,
        "doc_a": {"type": doc_type_a, "chunks": chunks_a, "citations": cit_a},
        "doc_b": {"type": doc_type_b, "chunks": chunks_b, "citations": cit_b},
        "comparison": comparison_json,
    }


def _generate_comparison(query: str, type_a: str, ctx_a: str, type_b: str, ctx_b: str) -> str:
    """Generate structured JSON comparison using Azure OpenAI."""
    import os, json
    from utils.logger import setup_logger
    logger = setup_logger(__name__)

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

        prompt = f"""You are a document comparison expert. Compare these two documents on: "{query}"

=== {type_a} ===
{ctx_a[:2000]}

=== {type_b} ===
{ctx_b[:2000]}

Return ONLY a valid JSON object with this exact structure (no markdown, no explanation):
{{
  "doc_a_points": [
    "Specific point about {type_a} regarding {query}",
    "Another specific point about {type_a}",
    "Third point about {type_a}"
  ],
  "doc_b_points": [
    "Specific point about {type_b} regarding {query}",
    "Another specific point about {type_b}",
    "Third point about {type_b}"
  ],
  "similarities": [
    "First similarity between both documents",
    "Second similarity between both documents"
  ],
  "differences": [
    "Key difference 1: {type_a} does X while {type_b} does Y",
    "Key difference 2: contrast between the two"
  ],
  "recommendation": "Brief recommendation on when to use each document"
}}

IMPORTANT: 
- doc_a_points must ONLY be about {type_a}
- doc_b_points must ONLY be about {type_b}
- They must be DIFFERENT from each other
- Return ONLY the JSON, nothing else"""

        response = client.chat.completions.create(
            model=os.getenv("AZURE_LLM_DEPLOYMENT_41_MINI", "gpt-4.1-mini"),
            messages=[
                {"role": "system", "content": "You are a document comparison expert. Always return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1000,
        )

        content = response.choices[0].message.content.strip()

        # Clean JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        # Validate JSON
        parsed = json.loads(content)

        # Verify structure
        required = ["doc_a_points", "doc_b_points", "similarities", "differences", "recommendation"]
        for key in required:
            if key not in parsed:
                parsed[key] = []

        logger.info(f"Comparison generated: {len(parsed.get('doc_a_points',[]))} a-points, {len(parsed.get('doc_b_points',[]))} b-points")
        return json.dumps(parsed)

    except Exception as e:
        logger.error(f"Comparison LLM failed: {e}")
        # Fallback structured response
        import json
        return json.dumps({
            "doc_a_points": [f"Content retrieved from {type_a}", "See citations above for details"],
            "doc_b_points": [f"Content retrieved from {type_b}", "See citations above for details"],
            "similarities": ["Both are professional business documents"],
            "differences":  [f"{type_a} focuses on different aspects than {type_b}"],
            "recommendation": f"Use {type_a} for its specific purpose and {type_b} for its domain."
        })


    