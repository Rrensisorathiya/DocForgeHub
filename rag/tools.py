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
# # rag/tools.py
# import hashlib, os
# from typing import Optional
# from utils.logger import setup_logger

# logger = setup_logger(__name__)

# AZURE_ENDPOINT    = os.getenv("AZURE_LLM_ENDPOINT", "")
# AZURE_API_KEY     = os.getenv("AZURE_OPENAI_LLM_KEY", "")
# AZURE_API_VERSION = os.getenv("AZURE_LLM_API_VERSION", "2024-02-15-preview")
# AZURE_CHAT_DEPLOY = os.getenv("AZURE_LLM_DEPLOYMENT_41_MINI", "")


# # ── helpers ──────────────────────────────────────────────────────────────

# def _build_filter(doc_type=None, department=None, industry=None, version=None) -> Optional[dict]:
#     """Build a ChromaDB $and / single-condition where-clause."""
#     conditions = []
#     if doc_type:   conditions.append({"doc_type":   {"$eq": doc_type}})
#     if department: conditions.append({"department": {"$eq": department}})
#     if industry:   conditions.append({"industry":   {"$eq": industry}})
#     if version:    conditions.append({"version":    {"$eq": version}})

#     if not conditions:
#         return None
#     if len(conditions) == 1:
#         return conditions[0]
#     return {"$and": conditions}


# def _cache_key(*parts) -> str:
#     raw = "|".join(str(p) for p in parts)
#     return hashlib.md5(raw.encode()).hexdigest()


# # ── public tools ─────────────────────────────────────────────────────────

# def search_docs(query: str, doc_type=None, department=None,
#                 industry=None, version=None, top_k: int = 5) -> dict:
#     """
#     Vector-search ChromaDB with optional metadata filters.
#     Results are cached in Redis for 5 minutes.
#     """
#     from cache.redis_service import redis_client
#     from rag.vector_store import vector_store

#     key    = _cache_key("search", query, doc_type, department, industry, version, top_k)
#     cached = redis_client.get(key)
#     if cached:
#         logger.debug(f"Cache HIT for search: {query[:40]}")
#         cached["cached"] = True
#         return cached

#     where  = _build_filter(doc_type, department, industry, version)
#     chunks = vector_store.similarity_search(query, k=top_k, where=where)

#     result = {"chunks": chunks, "cached": False}
#     redis_client.set(key, result, ttl=300)
#     return result


# def refine_query(query: str, context: str = "") -> dict:
#     """
#     Use Azure OpenAI to rewrite a vague query into a precise retrieval phrase.
#     Returns { refined, keywords, suggestions }.
#     """
#     from cache.redis_service import redis_client

#     key    = _cache_key("refine", query, context[:50])
#     cached = redis_client.get(key)
#     if cached:
#         return cached

#     try:
#         from langchain_openai import AzureChatOpenAI
#         llm = AzureChatOpenAI(
#             azure_endpoint   = AZURE_ENDPOINT,
#             api_key          = AZURE_API_KEY,
#             api_version      = AZURE_API_VERSION,
#             azure_deployment = AZURE_CHAT_DEPLOY,
#             temperature      = 0,
#             max_tokens       = 200,
#         )

#         prompt = f"""Rewrite this search query to retrieve better legal/business document chunks.

# Original: {query}
# Context: {context or 'none'}

# Reply with JSON only:
# {{
#   "refined": "<precise 5-15 word query>",
#   "keywords": ["<keyword1>", "<keyword2>", "<keyword3>"],
#   "suggestions": ["<alt query 1>", "<alt query 2>"]
# }}"""

#         import json, re
#         raw = llm.invoke(prompt).content.strip()
#         # strip markdown fences
#         raw = re.sub(r"```json|```", "", raw).strip()
#         result = json.loads(raw)
#     except Exception as e:
#         logger.warning(f"Refine LLM error: {e}")
#         result = {
#             "refined":     query,
#             "keywords":    query.split()[:3],
#             "suggestions": [query],
#         }

#     redis_client.set(key, result, ttl=600)
#     return result
# # """
# # RAG Tools — 3 tools for LangChain agent
# # 1. search_docs    — vector search + metadata filters
# # 2. refine_query   — rewrite query for better retrieval
# # 3. compare_docs   — side-by-side comparison of 2 documents
# # """

# # import os
# # import json
# # from dotenv import load_dotenv
# # from utils.logger import setup_logger
# # from rag.vector_store import vector_store
# # from cache.redis_service import redis_client

# # load_dotenv()
# # logger = setup_logger(__name__)


# # def search_docs(
# #     query: str,
# #     doc_type: str   = None,
# #     department: str = None,
# #     industry: str   = None,
# #     version: str    = None,
# #     top_k: int      = 5,
# # ) -> dict:
# #     filters = {}
# #     if doc_type:   filters["doc_type"]   = doc_type
# #     if department: filters["department"] = department
# #     if industry:   filters["industry"]   = industry
# #     if version:    filters["version"]    = version

# #     cached = redis_client.get_retrieval(query, filters)
# #     if cached:
# #         logger.info(f"Cache HIT for query: {query[:40]}")
# #         return {"query": query, "chunks": cached, "cached": True, "filters": filters}

# #     chunks = vector_store.search(query, top_k=top_k, filters=filters or None)

# #     if not chunks:
# #         return {
# #             "query":   query,
# #             "chunks":  [],
# #             "cached":  False,
# #             "filters": filters,
# #             "message": "No relevant documents found. Try different keywords or remove filters.",
# #         }

# #     redis_client.set_retrieval(query, filters, chunks)
# #     logger.info(f"search_docs: '{query[:40]}' → {len(chunks)} chunks")
# #     return {"query": query, "chunks": chunks, "cached": False, "filters": filters}


# # def refine_query(original_query: str, context: str = "") -> dict:
# #     cache_key = f"refine:{hash(original_query)}"
# #     cached    = redis_client.get(cache_key)
# #     if cached:
# #         return cached

# #     try:
# #         from openai import AzureOpenAI
# #         import httpx

# #         client = AzureOpenAI(
# #             azure_endpoint=os.getenv("AZURE_LLM_ENDPOINT", "").rstrip("/"),
# #             api_key=(
# #                 os.getenv("AZURE_OPENAI_LLM_KEY")
# #                 or os.getenv("AZURE_OPENAI_API_KEY")
# #             ),
# #             api_version=os.getenv("AZURE_LLM_API_VERSION", "2025-01-01-preview"),
# #             http_client=httpx.Client(),
# #         )

# #         prompt = f"""You are a search query optimizer for a legal/business document retrieval system.

# # User query: "{original_query}"
# # {f'Context: {context}' if context else ''}

# # Return a JSON object with:
# # 1. "refined": A clearer, more specific version of the query
# # 2. "keywords": List of 3-5 key terms for search
# # 3. "suggestions": 2-3 alternative search queries

# # JSON only, no explanation."""

# #         response = client.chat.completions.create(
# #             model=os.getenv("AZURE_LLM_DEPLOYMENT_41_MINI", "gpt-4.1-mini"),
# #             messages=[{"role": "user", "content": prompt}],
# #             temperature=0.3,
# #             max_tokens=300,
# #         )

# #         content = response.choices[0].message.content.strip()
# #         if "```json" in content:
# #             content = content.split("```json")[1].split("```")[0].strip()
# #         elif "```" in content:
# #             content = content.split("```")[1].split("```")[0].strip()

# #         parsed = json.loads(content)
# #         result = {
# #             "original":    original_query,
# #             "refined":     parsed.get("refined", original_query),
# #             "keywords":    parsed.get("keywords", []),
# #             "suggestions": parsed.get("suggestions", []),
# #         }

# #     except Exception as e:
# #         logger.warning(f"refine_query LLM failed: {e} — using original")
# #         result = {
# #             "original":    original_query,
# #             "refined":     original_query,
# #             "keywords":    original_query.split()[:5],
# #             "suggestions": [],
# #         }

# #     redis_client.set(cache_key, result, ttl=3600)
# #     logger.info(f"refine_query: '{original_query[:40]}' → '{result['refined'][:40]}'")
# #     return result


# # def compare_docs(query: str, doc_type_a: str, doc_type_b: str, department: str = None) -> dict:
# #     cache_key = f"compare:{hash(f'{query}|{doc_type_a}|{doc_type_b}')}"
# #     cached    = redis_client.get(cache_key)
# #     if cached:
# #         return cached

# #     filters_a = {"doc_type": doc_type_a}
# #     filters_b = {"doc_type": doc_type_b}
# #     if department:
# #         filters_a["department"] = department
# #         filters_b["department"] = department

# #     chunks_a = vector_store.search(query, top_k=3, filters=filters_a)
# #     chunks_b = vector_store.search(query, top_k=3, filters=filters_b)

# #     if not chunks_a and not chunks_b:
# #         return {
# #             "query":      query,
# #             "doc_a":      {"type": doc_type_a, "chunks": [], "citations": []},
# #             "doc_b":      {"type": doc_type_b, "chunks": [], "citations": []},
# #             "comparison": f"No content found for either {doc_type_a} or {doc_type_b}.",
# #         }

# #     ctx_a = "\n".join([c["text"] for c in chunks_a]) if chunks_a else "No content found."
# #     ctx_b = "\n".join([c["text"] for c in chunks_b]) if chunks_b else "No content found."

# #     comparison_text = _generate_comparison(query, doc_type_a, ctx_a, doc_type_b, ctx_b)

# #     result = {
# #         "query": query,
# #         "doc_a": {"type": doc_type_a, "chunks": chunks_a, "citations": [c["citation"] for c in chunks_a]},
# #         "doc_b": {"type": doc_type_b, "chunks": chunks_b, "citations": [c["citation"] for c in chunks_b]},
# #         "comparison": comparison_text,
# #     }

# #     redis_client.set(cache_key, result, ttl=1800)
# #     logger.info(f"compare_docs: {doc_type_a} vs {doc_type_b}")
# #     return result


# # def _generate_comparison(query: str, type_a: str, ctx_a: str, type_b: str, ctx_b: str) -> str:
# #     try:
# #         from openai import AzureOpenAI
# #         import httpx

# #         client = AzureOpenAI(
# #             azure_endpoint=os.getenv("AZURE_LLM_ENDPOINT", "").rstrip("/"),
# #             api_key=(
# #                 os.getenv("AZURE_OPENAI_LLM_KEY")
# #                 or os.getenv("AZURE_OPENAI_API_KEY")
# #             ),
# #             api_version=os.getenv("AZURE_LLM_API_VERSION", "2025-01-01-preview"),
# #             http_client=httpx.Client(),
# #         )

# #         prompt = f"""Compare these two documents regarding: "{query}"

# # {type_a}:
# # {ctx_a[:1500]}

# # {type_b}:
# # {ctx_b[:1500]}

# # Provide a clear, structured comparison covering:
# # 1. Key similarities
# # 2. Key differences
# # 3. Which is more suitable for specific use cases

# # Be concise and cite specific clauses where possible."""

# #         response = client.chat.completions.create(
# #             model=os.getenv("AZURE_LLM_DEPLOYMENT_41_MINI", "gpt-4.1-mini"),
# #             messages=[{"role": "user", "content": prompt}],
# #             temperature=0.3,
# #             max_tokens=600,
# #         )
# #         return response.choices[0].message.content.strip()

# #     except Exception as e:
# #         logger.warning(f"Comparison LLM failed: {e}")
# #         return f"Comparison generated from retrieved content. {type_a} and {type_b} differ in scope and application."