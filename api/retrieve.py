"""
RAG Retrieve API — FastAPI endpoints
POST /rag/retrieve  — vector search with filters
POST /rag/answer    — grounded Q&A with citations
POST /rag/compare   — compare two document types
POST /rag/refine    — refine a search query
POST /rag/ingest    — ingest Notion documents
GET  /rag/stats     — vector store + Redis stats
GET  /rag/session/{id} — get session history
DELETE /rag/session/{id} — clear session
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional
from utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter(prefix="/rag", tags=["RAG"])


class RetrieveRequest(BaseModel):
    query:      str           = Field(..., description="Search query")
    doc_type:   Optional[str] = Field(None)
    department: Optional[str] = Field(None)
    industry:   Optional[str] = Field(None)
    version:    Optional[str] = Field(None)
    top_k:      int           = Field(5, ge=1, le=20)


class AskRequest(BaseModel):
    question:   str           = Field(..., description="User question")
    session_id: str           = Field("default")
    doc_type:   Optional[str] = None
    department: Optional[str] = None
    industry:   Optional[str] = None
    use_refine: bool          = Field(True)
    top_k:      int           = Field(5, ge=1, le=20)


class CompareRequest(BaseModel):
    query:      str           = Field(..., description="What to compare")
    doc_type_a: str           = Field(..., description="First document type")
    doc_type_b: str           = Field(..., description="Second document type")
    department: Optional[str] = None
    session_id: str           = Field("default")


class IngestRequest(BaseModel):
    token:          str  = Field(..., description="Notion integration token")
    database_id:    str  = Field(..., description="Notion database ID")
    force_reingest: bool = Field(False)


class RefineRequest(BaseModel):
    query:   str = Field(..., description="Query to refine")
    context: str = Field("")


@router.post("/retrieve", summary="Search documents with filters")
def retrieve(req: RetrieveRequest):
    try:
        from rag.tools import search_docs
        result = search_docs(
            query=req.query,
            doc_type=req.doc_type,
            department=req.department,
            industry=req.industry,
            version=req.version,
            top_k=req.top_k,
        )
        return {
            "success": True,
            "query":   req.query,
            "filters": {k: v for k, v in {"doc_type": req.doc_type, "department": req.department, "industry": req.industry, "version": req.version}.items() if v},
            "total":   len(result.get("chunks", [])),
            "cached":  result.get("cached", False),
            "chunks":  result.get("chunks", []),
        }
    except Exception as e:
        logger.error(f"Retrieve failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/answer", summary="Grounded Q&A with citations")
def answer(req: AskRequest):
    try:
        from rag.chain import ask
        filters = {}
        if req.doc_type:   filters["doc_type"]   = req.doc_type
        if req.department: filters["department"] = req.department
        if req.industry:   filters["industry"]   = req.industry

        result = ask(
            question=req.question,
            session_id=req.session_id,
            filters=filters,
            use_refine=req.use_refine,
            top_k=req.top_k,
        )
        return {
            "success":       True,
            "question":      result["question"],
            "answer":        result["answer"],
            "citations":     result["citations"],
            "refined_query": result.get("refined_query", req.question),
            "keywords":      result.get("keywords", []),
            "cached":        result["cached"],
            "session_id":    result["session_id"],
            "chunks_used":   len(result.get("chunks", [])),
        }
    except Exception as e:
        logger.error(f"Answer failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare", summary="Compare two document types")
def compare(req: CompareRequest):
    try:
        import json
        from rag.tools import compare_docs
 
        result = compare_docs(
            query=req.query,
            doc_type_a=req.doc_type_a,
            doc_type_b=req.doc_type_b,
            department=req.department,
        )
 
        # Parse structured JSON
        comparison_raw = result.get("comparison", "{}")
        try:
            if isinstance(comparison_raw, str):
                if "```json" in comparison_raw:
                    comparison_raw = comparison_raw.split("```json")[1].split("```")[0].strip()
                elif "```" in comparison_raw:
                    comparison_raw = comparison_raw.split("```")[1].split("```")[0].strip()
                comparison_data = json.loads(comparison_raw)
            else:
                comparison_data = comparison_raw
        except Exception as e:
            logger.warning(f"JSON parse failed: {e}")
            comparison_data = {}
 
        def safe_len(val):
            if isinstance(val, list): return len(val)
            if isinstance(val, int):  return val
            return 0
 
        return {
            "success":    True,
            "query":      req.query,
            "doc_a": {
                "type":      result["doc_a"]["type"],
                "citations": list(dict.fromkeys(result["doc_a"].get("citations", []))),
                "chunks":    safe_len(result["doc_a"].get("chunks", 0)),
                "points":    comparison_data.get("doc_a_points", []),
            },
            "doc_b": {
                "type":      result["doc_b"]["type"],
                "citations": list(dict.fromkeys(result["doc_b"].get("citations", []))),
                "chunks":    safe_len(result["doc_b"].get("chunks", 0)),
                "points":    comparison_data.get("doc_b_points", []),
            },
            "similarities":   comparison_data.get("similarities",   []),
            "differences":    comparison_data.get("differences",    []),
            "recommendation": comparison_data.get("recommendation", ""),
        }
    except Exception as e:
        logger.error(f"Compare failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
 

# @router.post("/compare", summary="Compare two document types")
# def compare(req: CompareRequest):
#     try:
#         from rag.chain import compare as chain_compare
#         import json

#         result = chain_compare(
#             query=req.query,
#             doc_type_a=req.doc_type_a,
#             doc_type_b=req.doc_type_b,
#             department=req.department,
#             session_id=req.session_id,
#         )

#         def safe_len(val):
#             if isinstance(val, list): return len(val)
#             if isinstance(val, int):  return val
#             return 0

#         # Parse structured JSON from comparison
#         comparison_raw = result.get("comparison", "{}")
#         try:
#             if "```json" in comparison_raw:
#                 comparison_raw = comparison_raw.split("```json")[1].split("```")[0].strip()
#             elif "```" in comparison_raw:
#                 comparison_raw = comparison_raw.split("```")[1].split("```")[0].strip()
#             comparison_data = json.loads(comparison_raw)
#         except Exception:
#             comparison_data = {"raw": comparison_raw}

#         return {
#             "success":    True,
#             "query":      req.query,
#             "doc_a": {
#                 "type":      result["doc_a"]["type"],
#                 "citations": result["doc_a"].get("citations", []),
#                 "chunks":    safe_len(result["doc_a"].get("chunks", 0)),
#                 "points":    comparison_data.get("doc_a_points", []),
#             },
#             "doc_b": {
#                 "type":      result["doc_b"]["type"],
#                 "citations": result["doc_b"].get("citations", []),
#                 "chunks":    safe_len(result["doc_b"].get("chunks", 0)),
#                 "points":    comparison_data.get("doc_b_points", []),
#             },
# "similarities":     [],
# "differences":      [],
#             "recommendation":   comparison_data.get("recommendation", ""),
#             "comparison":       comparison_raw,
#         }
#     except Exception as e:
#         logger.error(f"Compare failed: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=str(e))

@router.post("/refine", summary="Refine a search query")
def refine(req: RefineRequest):
    try:
        from rag.tools import refine_query
        result = refine_query(req.query, req.context)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest", summary="Ingest Notion documents into vector store")
def ingest(req: IngestRequest, background_tasks: BackgroundTasks):
    try:
        from rag.ingestion import ingest_notion_documents
        background_tasks.add_task(
            ingest_notion_documents,
            token=req.token,
            database_id=req.database_id,
            force_reingest=req.force_reingest,
        )
        return {"success": True, "message": "Ingestion started in background. Check /rag/stats for progress."}
    except Exception as e:
        logger.error(f"Ingest failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", summary="Vector store and Redis stats")
def stats():
    try:
        from rag.vector_store import vector_store
        from cache.redis_service import redis_client
        return {
            "success":      True,
            "vector_store": vector_store.stats(),
            "redis":        redis_client.stats(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}", summary="Get session history")
def get_session(session_id: str):
    try:
        from rag.chain import get_session_history
        history = get_session_history(session_id)
        return {"success": True, "session_id": session_id, "messages": history, "count": len(history)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}", summary="Clear session history")
def clear_session(session_id: str):
    try:
        from rag.chain import clear_session as chain_clear
        chain_clear(session_id)
        return {"success": True, "message": f"Session {session_id} cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

    """
Add these endpoints to api/retrieve.py — paste at the end of the file
"""
 
# ── Eval Schemas ──────────────────────────────────────
class EvalQuestion(BaseModel):
    question:     str = Field(..., description="Test question")
    ground_truth: str = Field("", description="Expected answer")
 
 
class EvalRequest(BaseModel):
    dataset:      list  = Field([], description="List of {question, ground_truth}")
    top_k:        int   = Field(5, ge=1, le=20)
    use_refine:   bool  = Field(True)
    save_results: bool  = Field(True)
    filters:      dict  = Field({})
 
 
@router.post("/eval/run", summary="Run RAGAS evaluation")
def run_eval(req: EvalRequest, background_tasks: BackgroundTasks):
    """
    Run RAGAS evaluation on RAG pipeline.
    Uses default dataset if none provided.
    Runs in background for large datasets.
    """
    try:
        from eval.ragas_eval import run_ragas_evaluation
 
        config = {
            "top_k":      req.top_k,
            "use_refine": req.use_refine,
            "filters":    req.filters,
        }
 
        dataset = req.dataset if req.dataset else None
 
        # Run in background
        background_tasks.add_task(
            run_ragas_evaluation,
            dataset=dataset,
            config=config,
            save_results=req.save_results,
        )
 
        return {
            "success": True,
            "message": f"Evaluation started with {len(dataset) if dataset else 5} questions. Check /rag/eval/results.",
        }
    except Exception as e:
        logger.error(f"Eval run failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
 
 
@router.get("/eval/results", summary="Get latest evaluation results")
def get_eval_results():
    """Get the most recent RAGAS evaluation results."""
    try:
        from eval.ragas_eval import load_latest_results
        result = load_latest_results()
        if not result:
            return {"success": True, "message": "No evaluation results yet. Run /rag/eval/run first.", "results": None}
        return {"success": True, "results": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
 
 
@router.get("/eval/history", summary="Get all evaluation results")
def get_eval_history():
    """Get all RAGAS evaluation results for comparison."""
    try:
        from eval.ragas_eval import load_all_results
        results = load_all_results()
        return {"success": True, "count": len(results), "history": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
 