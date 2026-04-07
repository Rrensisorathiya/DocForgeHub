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
# """
# Vector Store Service — ChromaDB
# Stores document chunks with metadata for RAG retrieval.
# """

# import os
# from typing import Optional
# from dotenv import load_dotenv
# from utils.logger import setup_logger

# load_dotenv()
# logger = setup_logger(__name__)

# CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")


# class VectorStore:
#     def __init__(self, collection_name: str = "docforge_docs"):
#         self._client     = None
#         self._collection = None
#         self._ef         = None
#         self._name       = collection_name
#         self._init()

#     def _init(self):
#         try:
#             import chromadb
#             from chromadb.utils import embedding_functions

#             self._client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

#             self._ef = embedding_functions.SentenceTransformerEmbeddingFunction(
#                 model_name="all-MiniLM-L6-v2"
#             )
#             logger.info("Using local SentenceTransformer embeddings (all-MiniLM-L6-v2)")

#             self._collection = self._client.get_or_create_collection(
#                 name=self._name,
#                 embedding_function=self._ef,
#                 metadata={"hnsw:space": "cosine"},
#             )
#             logger.info(f"ChromaDB ready — collection: {self._name} | docs: {self._collection.count()}")

#         except ImportError:
#             logger.error("chromadb not installed. Run: pip install chromadb")
#         except Exception as e:
#             logger.error(f"VectorStore init failed: {e}", exc_info=True)

#     @property
#     def available(self) -> bool:
#         return self._collection is not None

#     @property
#     def count(self) -> int:
#         if not self.available:
#             return 0
#         return self._collection.count()

#     def add_chunks(self, chunks: list) -> int:
#         if not self.available or not chunks:
#             return 0

#         ids       = [c["id"]       for c in chunks]
#         documents = [c["text"]     for c in chunks]
#         metadatas = [c["metadata"] for c in chunks]

#         try:
#             existing     = self._collection.get(ids=ids)
#             existing_ids = set(existing["ids"])
#             new_chunks   = [c for c in chunks if c["id"] not in existing_ids]
#             if not new_chunks:
#                 logger.info("All chunks already exist — skipping")
#                 return 0
#             ids       = [c["id"]       for c in new_chunks]
#             documents = [c["text"]     for c in new_chunks]
#             metadatas = [c["metadata"] for c in new_chunks]
#         except Exception:
#             pass

#         self._collection.add(ids=ids, documents=documents, metadatas=metadatas)
#         logger.info(f"Added {len(ids)} chunks to vector store")
#         return len(ids)

#     def search(self, query: str, top_k: int = 5, filters: Optional[dict] = None) -> list:
#         if not self.available:
#             return []

#         where = self._build_where(filters) if filters else None

#         try:
#             results = self._collection.query(
#                 query_texts=[query],
#                 n_results=min(top_k, self._collection.count() or 1),
#                 where=where,
#                 include=["documents", "metadatas", "distances"],
#             )

#             chunks    = []
#             docs      = results["documents"][0]
#             metas     = results["metadatas"][0]
#             distances = results["distances"][0]
#             ids       = results["ids"][0]

#             for doc, meta, dist, cid in zip(docs, metas, distances, ids):
#                 chunks.append({
#                     "id":       cid,
#                     "text":     doc,
#                     "metadata": meta,
#                     "score":    round(1 - dist, 4),
#                     "citation": self._format_citation(meta),
#                 })

#             return chunks

#         except Exception as e:
#             logger.error(f"Search failed: {e}")
#             return []

#     def delete_by_doc_id(self, doc_id: str) -> int:
#         if not self.available:
#             return 0
#         try:
#             existing = self._collection.get(where={"doc_id": doc_id})
#             ids      = existing["ids"]
#             if ids:
#                 self._collection.delete(ids=ids)
#                 logger.info(f"Deleted {len(ids)} chunks for doc_id={doc_id}")
#             return len(ids)
#         except Exception as e:
#             logger.error(f"Delete failed: {e}")
#             return 0

#     def delete_all(self) -> None:
#         if not self.available:
#             return
#         self._client.delete_collection(self._name)
#         self._collection = self._client.get_or_create_collection(
#             name=self._name,
#             embedding_function=self._ef,
#         )
#         logger.warning("Vector store cleared!")

#     @staticmethod
#     def _build_where(filters: dict) -> Optional[dict]:
#         valid = {
#             k: str(v) for k, v in filters.items()
#             if v and v != "All" and k in {"doc_type", "department", "industry", "version"}
#         }
#         if not valid:
#             return None
#         if len(valid) == 1:
#             k, v = next(iter(valid.items()))
#             return {k: {"$eq": v}}
#         return {"$and": [{k: {"$eq": v}} for k, v in valid.items()]}

#     @staticmethod
#     def _format_citation(meta: dict) -> str:
#         title   = meta.get("title",   "Unknown Document")
#         section = meta.get("section", "")
#         if section:
#             return f"{title} → {section}"
#         return title

#     def stats(self) -> dict:
#         if not self.available:
#             return {"available": False}
#         try:
#             total  = self._collection.count()
#             sample = self._collection.get(limit=1000, include=["metadatas"])
#             doc_types   = set()
#             departments = set()
#             for m in sample["metadatas"]:
#                 if m.get("doc_type"):   doc_types.add(m["doc_type"])
#                 if m.get("department"): departments.add(m["department"])
#             return {
#                 "available":    True,
#                 "total_chunks": total,
#                 "doc_types":    list(doc_types),
#                 "departments":  list(departments),
#                 "persist_dir":  CHROMA_PERSIST_DIR,
#             }
#         except Exception as e:
#             return {"available": False, "error": str(e)}


# vector_store = VectorStore()