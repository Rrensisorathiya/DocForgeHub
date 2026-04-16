import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from utils.logger import setup_logger
 
logger = setup_logger(__name__)
 
router       = APIRouter(prefix="/assistant", tags=["P3 Assistant"])
ticket_router= APIRouter(prefix="/tickets",   tags=["P3 Tickets"])
 
 
# ── Models ────────────────────────────────────────────────────────────────
 
class ThreadCreate(BaseModel):
    user_id:    str           = "anonymous"
    industry:   Optional[str] = None
    department: Optional[str] = None
 
class ChatRequest(BaseModel):
    thread_id:  str
    message:    str
    user_id:    str           = "anonymous"
    industry:   Optional[str] = None
    department: Optional[str] = None
 
class StatusUpdate(BaseModel):
    status: str  # open | in_progress | resolved | closed
 
 
# ── Thread endpoints ──────────────────────────────────────────────────────
 
@router.post("/threads")
def create_thread(req: ThreadCreate):
    from assistant.memory import db_create_thread, redis_save_context
    tid = str(uuid.uuid4())[:16]
    db_create_thread(tid, req.user_id, req.industry, req.department)
    redis_save_context(tid, req.industry or "", req.department or "", req.user_id)
    return {"success": True, "thread_id": tid}
 
 
@router.get("/threads")
def list_threads(user_id: Optional[str] = None):
    from assistant.memory import db_list_threads
    threads = db_list_threads(user_id)
    return {"success": True, "threads": threads, "total": len(threads)}
 
 
@router.get("/threads/{thread_id}")
def get_thread(thread_id: str):
    from assistant.memory import db_get_thread, db_load_messages
    thread = db_get_thread(thread_id)
    if not thread:
        raise HTTPException(404, f"Thread {thread_id} not found")
    messages = db_load_messages(thread_id, limit=50)
    return {"success": True, "thread": thread,
            "messages": messages, "count": len(messages)}
 
 
@router.delete("/threads/{thread_id}")
def delete_thread(thread_id: str):
    from assistant.memory import redis_clear_thread
    from db import get_connection
    redis_clear_thread(thread_id)
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("DELETE FROM assistant_threads WHERE thread_id=%s", (thread_id,))
    conn.commit(); cur.close(); conn.close()
    return {"success": True}
 
 
# ── Chat endpoint ─────────────────────────────────────────────────────────
 
@router.post("/chat")
def chat(req: ChatRequest):
    """
    Main assistant endpoint.
    Runs LangGraph: context_loader → intent → retrieve/clarify/ticket → memory_save
    Reuses Project 2's rag.tools and rag.chain internally.
    """
    try:
        from assistant.graph import run_assistant
        state = run_assistant(
            thread_id  = req.thread_id,
            message    = req.message,
            user_id    = req.user_id,
            industry   = req.industry,
            department = req.department,
        )
        return {
            "success":        True,
            "thread_id":      req.thread_id,
            "trace_id":       state.get("trace_id"),
            "intent":         state.get("intent"),
            "answer":         state.get("answer", ""),
            "citations":      state.get("citations", []),
            "evidence_score": state.get("evidence_score", 0.0),
            "ticket_created": bool(state.get("notion_ticket_id")),
            "notion_url":     state.get("notion_url"),
            "ticket_status":  state.get("ticket_status"),
        }
    except Exception as e:
        logger.error(f"Assistant chat error: {e}", exc_info=True)
        raise HTTPException(500, str(e))
 
 
# ── Ticket endpoints ──────────────────────────────────────────────────────
 
@ticket_router.get("/")
def list_tickets(status: Optional[str] = None, department: Optional[str] = None):
    from assistant.memory import db_list_tickets
    tickets = db_list_tickets(status, department)
    return {"success": True, "tickets": tickets, "total": len(tickets)}
 
 
@ticket_router.get("/stats")
def ticket_stats():
    from db import get_connection
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("SELECT status, COUNT(*) FROM assistant_tickets GROUP BY status")
    by_status = dict(cur.fetchall())
    cur.execute("SELECT department, COUNT(*) FROM assistant_tickets GROUP BY department ORDER BY COUNT(*) DESC LIMIT 10")
    by_dept = dict(cur.fetchall())
    cur.execute("SELECT COUNT(*) FROM assistant_tickets")
    total = cur.fetchone()[0]
    cur.close(); conn.close()
    return {"success": True, "total": total,
            "by_status": by_status, "by_department": by_dept}
 
 
@ticket_router.get("/{ticket_id}")
def get_ticket(ticket_id: int):
    from db import get_connection
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM assistant_tickets WHERE id=%s", (ticket_id,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, f"Ticket {ticket_id} not found")
    cols = [d[0] for d in cur.description]
    cur.close(); conn.close()
    return {"success": True, "ticket": dict(zip(cols, row))}
 
 
@ticket_router.put("/{ticket_id}/status")
def update_ticket(ticket_id: int, req: StatusUpdate):
    from assistant.memory import db_update_ticket_status
    from assistant.ticket import update_notion_ticket_status
    notion_id = db_update_ticket_status(ticket_id, req.status)
    if not notion_id:
        raise HTTPException(404, f"Ticket {ticket_id} not found")
    if notion_id:
        try:
            update_notion_ticket_status(notion_id, req.status)
        except Exception as e:
            logger.warning(f"Notion status sync failed: {e}")
    return {"success": True, "ticket_id": ticket_id, "status": req.status}
 
# # api/assistant.py
# import uuid
# from fastapi import APIRouter, HTTPException
# from pydantic import BaseModel, Field
# from typing import Optional
# from utils.logger import setup_logger

# logger = setup_logger(__name__)
# router = APIRouter(prefix="/assistant", tags=["Assistant"])


# # ── Request / Response models ─────────────────────────────────────────────

# class ChatRequest(BaseModel):
#     thread_id:  str         = Field(..., description="Thread ID from POST /assistant/threads")
#     message:    str         = Field(..., description="User message")
#     user_id:    str         = Field("anonymous")
#     industry:   Optional[str] = None
#     department: Optional[str] = None


# class ThreadRequest(BaseModel):
#     user_id:    str           = Field("anonymous")
#     industry:   Optional[str] = None
#     department: Optional[str] = None


# class TicketStatusRequest(BaseModel):
#     status: str  # open | in_progress | resolved | closed


# # ── Thread management ─────────────────────────────────────────────────────

# @router.post("/threads", summary="Create new conversation thread")
# def create_thread(req: ThreadRequest):
#     from assistant.memory import create_thread_in_db, save_context_to_redis
#     thread_id = str(uuid.uuid4())[:16]
#     create_thread_in_db(thread_id, req.user_id, req.industry, req.department)
#     save_context_to_redis(thread_id, req.industry or "",
#                           req.department or "", req.user_id)
#     logger.info(f"Thread created: {thread_id}")
#     return {"success": True, "thread_id": thread_id}


# @router.get("/threads/{thread_id}", summary="Get thread info + message history")
# def get_thread(thread_id: str):
#     from assistant.memory import get_thread_from_db, load_messages_from_db
#     thread = get_thread_from_db(thread_id)
#     if not thread:
#         raise HTTPException(404, f"Thread {thread_id} not found")
#     messages = load_messages_from_db(thread_id, limit=50)
#     return {"success": True, "thread": thread, "messages": messages,
#             "count": len(messages)}


# @router.delete("/threads/{thread_id}", summary="Delete thread + clear Redis cache")
# def delete_thread(thread_id: str):
#     from assistant.memory import clear_thread_cache
#     from db import get_connection
#     clear_thread_cache(thread_id)
#     conn = get_connection()
#     cur  = conn.cursor()
#     cur.execute("DELETE FROM assistant_threads WHERE thread_id = %s", (thread_id,))
#     conn.commit()
#     cur.close(); conn.close()
#     return {"success": True, "message": f"Thread {thread_id} deleted"}


# # ── Main chat endpoint ────────────────────────────────────────────────────

# @router.post("/chat", summary="Send message to assistant")
# def chat(req: ChatRequest):
#     """
#     Main entry point for the stateful RAG assistant.
#     Runs LangGraph: context → intent → retrieve/clarify/ticket → memory save.
#     """
#     try:
#         from assistant.graph import run_assistant
#         state = run_assistant(
#             thread_id  = req.thread_id,
#             message    = req.message,
#             user_id    = req.user_id,
#             industry   = req.industry,
#             department = req.department,
#         )
#         return {
#             "success":         True,
#             "thread_id":       req.thread_id,
#             "intent":          state.get("intent"),
#             "answer":          state.get("answer", ""),
#             "citations":       state.get("citations", []),
#             "evidence_score":  state.get("evidence_score", 0.0),
#             "ticket_created":  bool(state.get("notion_ticket_id")),
#             "notion_url":      state.get("notion_url"),
#             "ticket_status":   state.get("ticket_status"),
#             "trace_id":        state.get("trace_id"),
#         }
#     except Exception as e:
#         logger.error(f"Assistant chat error: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/state/{thread_id}", summary="Get current LangGraph state from Redis")
# def get_state(thread_id: str):
#     from assistant.memory import load_state_from_redis
#     state = load_state_from_redis(thread_id)
#     if not state:
#         raise HTTPException(404, "No active state found for this thread")
#     return {"success": True, "state": state}


# # ── Ticket endpoints ──────────────────────────────────────────────────────

# ticket_router = APIRouter(prefix="/tickets", tags=["Tickets"])


# @ticket_router.get("/", summary="List all tickets")
# def list_tickets(status: Optional[str] = None, department: Optional[str] = None):
#     from db import get_connection
#     conn = get_connection()
#     cur  = conn.cursor()
#     query  = "SELECT * FROM assistant_tickets WHERE 1=1"
#     params = []
#     if status:
#         query += " AND status = %s"; params.append(status)
#     if department:
#         query += " AND department = %s"; params.append(department)
#     query += " ORDER BY created_at DESC LIMIT 100"
#     cur.execute(query, params)
#     cols = [d[0] for d in cur.description]
#     rows = [dict(zip(cols, r)) for r in cur.fetchall()]
#     cur.close(); conn.close()
#     return {"success": True, "tickets": rows, "total": len(rows)}


# @ticket_router.get("/stats", summary="Ticket statistics")
# def ticket_stats():
#     from db import get_connection
#     conn = get_connection()
#     cur  = conn.cursor()
#     cur.execute("SELECT status, COUNT(*) FROM assistant_tickets GROUP BY status")
#     by_status = dict(cur.fetchall())
#     cur.execute("SELECT department, COUNT(*) FROM assistant_tickets GROUP BY department ORDER BY COUNT(*) DESC LIMIT 10")
#     by_dept = dict(cur.fetchall())
#     cur.execute("SELECT COUNT(*) FROM assistant_tickets")
#     total = cur.fetchone()[0]
#     cur.close(); conn.close()
#     return {"success": True, "total": total,
#             "by_status": by_status, "by_department": by_dept}


# @ticket_router.get("/{ticket_id}", summary="Get ticket detail")
# def get_ticket(ticket_id: int):
#     from db import get_connection
#     conn = get_connection()
#     cur  = conn.cursor()
#     cur.execute("SELECT * FROM assistant_tickets WHERE id = %s", (ticket_id,))
#     row = cur.fetchone()
#     if not row:
#         raise HTTPException(404, f"Ticket {ticket_id} not found")
#     cols = [d[0] for d in cur.description]
#     cur.close(); conn.close()
#     return {"success": True, "ticket": dict(zip(cols, row))}


# @ticket_router.put("/{ticket_id}/status", summary="Update ticket status")
# def update_ticket_status(ticket_id: int, req: TicketStatusRequest):
#     from db import get_connection
#     from assistant.ticket import update_ticket_status as notion_update
#     conn = get_connection()
#     cur  = conn.cursor()
#     cur.execute("""
#         UPDATE assistant_tickets SET status = %s,
#         resolved_at = CASE WHEN %s IN ('resolved','closed') THEN CURRENT_TIMESTAMP ELSE NULL END
#         WHERE id = %s RETURNING notion_ticket_id
#     """, (req.status, req.status, ticket_id))
#     row = cur.fetchone()
#     if not row:
#         raise HTTPException(404, f"Ticket {ticket_id} not found")
#     conn.commit()
#     # Also update in Notion
#     if row[0]:
#         try:
#             notion_update(row[0], req.status.replace("_", " ").title())
#         except Exception as e:
#             logger.warning(f"Notion status update failed: {e}")
#     cur.close(); conn.close()
#     return {"success": True, "ticket_id": ticket_id, "status": req.status}