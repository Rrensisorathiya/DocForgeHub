# rag/vector_store.py
import os
from typing import Optional
from utils.logger import setup_logger

logger = setup_logger(__name__)

CHROMA_DIR        = os.getenv("CHROMA_DIR", "./chroma_db")
AZURE_ENDPOINT   = os.getenv("AZURE_EMB_ENDPOINT", "")
AZURE_API_KEY    = os.getenv("AZURE_OPENAI_EMB_KEY", "")
AZURE_API_VERSION= os.getenv("AZURE_EMB_API_VERSION", "2024-02-15-preview")
EMBEDDING_DEPLOY = os.getenv("AZURE_EMB_DEPLOYMENT", "")


class VectorStore:
    def __init__(self):
        self._db  = None
        self._emb = None

    # ── lazy init ────────────────────────────────────────────────────────
    def _get_embeddings(self):
        if self._emb is None:
            from langchain_openai import AzureOpenAIEmbeddings
            self._emb = AzureOpenAIEmbeddings(
                azure_endpoint    = AZURE_ENDPOINT,
                api_key           = AZURE_API_KEY,
                api_version       = AZURE_API_VERSION,
                azure_deployment  = EMBEDDING_DEPLOY,
            )
        return self._emb

    def _get_db(self):
        if self._db is None:
            from langchain_community.vectorstores import Chroma
            self._db = Chroma(
                persist_directory  = CHROMA_DIR,
                embedding_function = self._get_embeddings(),
            )
            logger.info(f"ChromaDB loaded from {CHROMA_DIR}")
        return self._db

    # ── public API ───────────────────────────────────────────────────────
    def similarity_search(self, query: str, k: int = 5,
                          where: Optional[dict] = None) -> list:
        db = self._get_db()
        try:
            if where:
                results = db.similarity_search_with_relevance_scores(
                    query, k=k, filter=where
                )
            else:
                results = db.similarity_search_with_relevance_scores(query, k=k)
        except Exception as e:
            logger.warning(f"Filtered search failed ({e}), retrying without filter")
            results = db.similarity_search_with_relevance_scores(query, k=k)

        chunks = []
        for doc, score in results:
            m = doc.metadata
            chunks.append({
                "text":        doc.page_content,
                "score":       round(float(score), 4),
                "doc_title":   m.get("doc_title", "Unknown"),
                "section":     m.get("section", ""),
                "page_id":     m.get("page_id", ""),
                "block_range": m.get("block_range", ""),
                "citation":    f"{m.get('doc_title','?')} › {m.get('section','') or 'General'}",
                "metadata": {
                    "industry":   m.get("industry", ""),
                    "doc_type":   m.get("doc_type", ""),
                    "department": m.get("department", ""),
                    "version":    m.get("version", ""),
                },
            })
        return chunks

    def add_documents(self, docs: list):
        db = self._get_db()
        db.add_documents(docs)
        logger.info(f"Added {len(docs)} documents to ChromaDB")

    def stats(self) -> dict:
        try:
            db         = self._get_db()
            collection = db._collection
            total      = collection.count()
            meta_list  = collection.get(include=["metadatas"])["metadatas"] or []
            doc_types   = list({m.get("doc_type","")   for m in meta_list if m.get("doc_type")})
            departments = list({m.get("department","") for m in meta_list if m.get("department")})
            industries  = list({m.get("industry","")   for m in meta_list if m.get("industry")})
            return {
                "total_chunks": total,
                "doc_types":    doc_types,
                "departments":  departments,
                "industries":   industries,
            }
        except Exception as e:
            logger.error(f"Stats error: {e}")
            return {"total_chunks": 0, "doc_types": [], "departments": [], "industries": []}


# singleton
vector_store = VectorStore()

