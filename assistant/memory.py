# assistant/memory.py
import os, json
from typing import Optional, List, Dict
from utils.logger import setup_logger

logger = setup_logger(__name__)

THREAD_TTL  = 7200   # 2 hours Redis TTL
CONTEXT_TTL = 86400  # 24 hours for context


# ── Redis helpers ─────────────────────────────────────────────────────────

def _redis():
    from cache.redis_service import redis_client
    return redis_client


def save_state_to_redis(thread_id: str, state: dict):
    """Save full LangGraph state to Redis."""
    r = _redis()
    # Save only serializable parts
    safe = {k: v for k, v in state.items()
            if isinstance(v, (str, int, float, bool, list, dict, type(None)))}
    r.set(f"thread:{thread_id}:state", safe, ttl=THREAD_TTL)


def load_state_from_redis(thread_id: str) -> Optional[dict]:
    r = _redis()
    return r.get(f"thread:{thread_id}:state")


def save_context_to_redis(thread_id: str, industry: str, department: str, user_id: str):
    r = _redis()
    r.set(f"thread:{thread_id}:ctx", {
        "industry":   industry,
        "department": department,
        "user_id":    user_id,
    }, ttl=CONTEXT_TTL)


def load_context_from_redis(thread_id: str) -> dict:
    r = _redis()
    return r.get(f"thread:{thread_id}:ctx") or {}


def save_messages_to_redis(thread_id: str, messages: list):
    r = _redis()
    r.set(f"thread:{thread_id}:msgs", messages[-10:], ttl=THREAD_TTL)


def load_messages_from_redis(thread_id: str) -> list:
    r = _redis()
    return r.get(f"thread:{thread_id}:msgs") or []


def check_idempotency(thread_id: str) -> bool:
    """Returns True if ticket already created for this thread."""
    r = _redis()
    return r.get(f"ticket:idem:{thread_id}") is not None


def set_idempotency(thread_id: str):
    """Mark ticket as created — prevents duplicates on retry."""
    r = _redis()
    r.set(f"ticket:idem:{thread_id}", {"created": True}, ttl=3600)


def clear_thread_cache(thread_id: str):
    r = _redis()
    for suffix in ["state", "msgs", "ctx"]:
        r.delete(f"thread:{thread_id}:{suffix}")


# ── PostgreSQL helpers ────────────────────────────────────────────────────

def create_thread_in_db(thread_id: str, user_id: str,
                         industry: str = None, department: str = None):
    from db import get_connection
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO assistant_threads (thread_id, user_id, industry, department)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (thread_id) DO UPDATE
        SET updated_at = CURRENT_TIMESTAMP
    """, (thread_id, user_id, industry, department))
    conn.commit()
    cur.close()
    conn.close()


def save_message_to_db(thread_id: str, role: str, content: str,
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
    conn.commit()
    cur.close()
    conn.close()


def load_messages_from_db(thread_id: str, limit: int = 20) -> list:
    from db import get_connection
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT role, content FROM assistant_messages
        WHERE thread_id = %s
        ORDER BY created_at DESC LIMIT %s
    """, (thread_id, limit))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]


def save_ticket_to_db(thread_id: str, question: str, notion_ticket_id: str,
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
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
    """, (thread_id, notion_ticket_id, notion_url, question,
          status, priority, department, owner,
          evidence_score, json.dumps(sources_tried), conversation_summary))
    ticket_db_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return ticket_db_id


def get_thread_from_db(thread_id: str) -> Optional[dict]:
    from db import get_connection
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT thread_id, user_id, industry, department, created_at
        FROM assistant_threads WHERE thread_id = %s
    """, (thread_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    return {
        "thread_id":  row[0],
        "user_id":    row[1],
        "industry":   row[2],
        "department": row[3],
        "created_at": str(row[4]),
    }