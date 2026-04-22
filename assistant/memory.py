# assistant/memory.py
import json
import re
from typing import Optional
from utils.logger import setup_logger

logger = setup_logger(__name__)

THREAD_TTL  = 7200   # 2h Redis TTL
CONTEXT_TTL = 86400  # 24h context TTL


def _r():
    from cache.redis_service import redis_client
    return redis_client

# ── Redis ──────────────────────────────────────────────────────────────

def redis_save_messages(thread_id: str, messages: list):
    _r().set(f"asst:{thread_id}:msgs", messages[-20:], ttl=THREAD_TTL)

def redis_load_messages(thread_id: str) -> list:
    return _r().get(f"asst:{thread_id}:msgs") or []

def redis_save_context(thread_id: str, industry: str, department: str, user_id: str):
    _r().set(f"asst:{thread_id}:ctx",
             {"industry": industry, "department": department, "user_id": user_id},
             ttl=CONTEXT_TTL)

def redis_load_context(thread_id: str) -> dict:
    return _r().get(f"asst:{thread_id}:ctx") or {}

def redis_check_idempotency(thread_id: str) -> bool:
    """True if ticket already created for this thread."""
    return _r().get(f"asst:idem:{thread_id}") is not None

def redis_set_idempotency(thread_id: str):
    _r().set(f"asst:idem:{thread_id}", {"created": True}, ttl=3600)

def redis_clear_thread(thread_id: str):
    for suffix in ["msgs", "ctx", "idem"]:
        _r().delete(f"asst:{thread_id}:{suffix}")

# ── PostgreSQL ──────────────────────────────────────────────────────────

def db_create_thread(thread_id: str, user_id: str,
                     industry: str = None, department: str = None):
    from db import get_connection
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO assistant_threads (thread_id, user_id, industry, department)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (thread_id) DO UPDATE SET updated_at = CURRENT_TIMESTAMP
    """, (thread_id, user_id, industry, department))
    conn.commit(); cur.close(); conn.close()

def db_save_message(thread_id: str, role: str, content: str,
                    intent: str = None, citations: list = None,
                    evidence_score: float = None, trace_id: str = None):
    from db import get_connection
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO assistant_messages
            (thread_id, role, content, intent, citations, evidence_score, trace_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (thread_id, role, content, intent,
          json.dumps(citations or []), evidence_score, trace_id))
    conn.commit(); cur.close(); conn.close()

def db_load_messages(thread_id: str, limit: int = 20) -> list:
    from db import get_connection
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT role, content, citations, intent, created_at
        FROM assistant_messages
        WHERE thread_id = %s
        ORDER BY created_at DESC LIMIT %s
    """, (thread_id, limit))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [
        {
            "role":       r[0],
            "content":    r[1],
            "citations":  r[2] if isinstance(r[2], list) else [],
            "intent":     r[3],
            "created_at": str(r[4])[:16],
        }
        for r in reversed(rows)
    ]

def db_get_thread(thread_id: str) -> Optional[dict]:
    from db import get_connection
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT thread_id, user_id, industry, department, created_at
        FROM assistant_threads WHERE thread_id = %s
    """, (thread_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    if not row:
        return None
    return {"thread_id": row[0], "user_id": row[1],
            "industry": row[2], "department": row[3], "created_at": str(row[4])}


def _normalize_ticket_question(question: str) -> str:
    text = (question or "").lower().strip()
    text = re.sub(r"\bnad\b", "nda", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def db_find_existing_ticket(question: str) -> Optional[dict]:
    """Return an open/in-progress ticket matching the normalized question."""
    normalized = _normalize_ticket_question(question)
    if not normalized:
        return None

    from db import get_connection
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, thread_id, notion_ticket_id, notion_url, question, status, priority, department, created_at
        FROM assistant_tickets
        WHERE status IN ('open', 'in_progress')
        ORDER BY created_at DESC
        LIMIT 100
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()

    for row in rows:
        existing_q = _normalize_ticket_question(row[4])
        if existing_q == normalized:
            return {
                "id": row[0],
                "thread_id": row[1],
                "notion_ticket_id": row[2],
                "notion_url": row[3],
                "question": row[4],
                "status": row[5],
                "priority": row[6],
                "department": row[7],
                "created_at": str(row[8])[:16],
            }
    return None

def db_list_threads(user_id: str = None) -> list:
    from db import get_connection
    conn = get_connection()
    cur  = conn.cursor()
    if user_id:
        cur.execute("""
            SELECT t.thread_id, t.user_id, t.industry, t.department,
                   t.created_at, COUNT(m.id) as msg_count
            FROM assistant_threads t
            LEFT JOIN assistant_messages m ON m.thread_id = t.thread_id
            WHERE t.user_id = %s
            GROUP BY t.thread_id ORDER BY t.created_at DESC LIMIT 50
        """, (user_id,))
    else:
        cur.execute("""
            SELECT t.thread_id, t.user_id, t.industry, t.department,
                   t.created_at, COUNT(m.id) as msg_count
            FROM assistant_threads t
            LEFT JOIN assistant_messages m ON m.thread_id = t.thread_id
            GROUP BY t.thread_id ORDER BY t.created_at DESC LIMIT 50
        """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [
        {"thread_id": r[0], "user_id": r[1], "industry": r[2],
         "department": r[3], "created_at": str(r[4])[:16], "msg_count": r[5]}
        for r in rows
    ]

def db_save_ticket(thread_id: str, question: str, notion_ticket_id: str,
                   notion_url: str, status: str, priority: str,
                   department: str, owner: str, evidence_score: float,
                   sources_tried: list, conversation_summary: str) -> int:
    from db import get_connection
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO assistant_tickets
            (thread_id, notion_ticket_id, notion_url, question,
             status, priority, department, assigned_owner,
             evidence_score, sources_tried, conversation_summary)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
    """, (thread_id, notion_ticket_id, notion_url, question,
          status, priority, department, owner,
          evidence_score, json.dumps(sources_tried), conversation_summary))
    tid = cur.fetchone()[0]
    conn.commit(); cur.close(); conn.close()
    return tid

def db_list_tickets(status: str = None, department: str = None) -> list:
    from db import get_connection
    conn = get_connection()
    cur  = conn.cursor()
    q    = "SELECT * FROM assistant_tickets WHERE 1=1"
    p    = []
    if status:
        q += " AND status=%s"; p.append(status)
    if department:
        q += " AND department=%s"; p.append(department)
    q += " ORDER BY created_at DESC LIMIT 100"
    cur.execute(q, p)
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows

def db_update_ticket_status(ticket_id: int, status: str) -> Optional[str]:
    """Returns notion_ticket_id for Notion sync."""
    from db import get_connection
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        UPDATE assistant_tickets SET status=%s,
        resolved_at = CASE WHEN %s IN ('resolved','closed')
                     THEN CURRENT_TIMESTAMP ELSE NULL END
        WHERE id=%s RETURNING notion_ticket_id
    """, (status, status, ticket_id))
    row = cur.fetchone()
    conn.commit(); cur.close(); conn.close()
    return row[0] if row else None
