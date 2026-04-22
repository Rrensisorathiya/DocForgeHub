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
            "duplicate_ticket": bool(state.get("duplicate_ticket")),
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
 
