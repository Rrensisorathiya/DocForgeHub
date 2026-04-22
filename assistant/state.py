# assistant/state.py
from typing import TypedDict, Optional, List, Dict, Any

class AssistantState(TypedDict):
    thread_id:         str
    user_id:           str
    trace_id:          str
    industry:          Optional[str]
    department:        Optional[str]
    message:           str
    history:           List[Dict[str, str]]
    intent:            Optional[str]
    clarify_question:  Optional[str]
    retrieved_chunks:  List[Dict[str, Any]]
    evidence_score:    float
    refined_query:     Optional[str]
    answer:            Optional[str]
    citations:         List[str]
    notion_ticket_id:  Optional[str]
    notion_url:        Optional[str]
    ticket_status:     Optional[str]
    duplicate_ticket:  Optional[bool]
    priority:          Optional[str]
    next_action:       Optional[str]
    error:             Optional[str]

# ── Evidence threshold ────────────────────────────────────────
EVIDENCE_THRESHOLD = 0.45

# ── Direct ticket keywords (skip retrieval) ───────────────────
DIRECT_TICKET_KEYWORDS = [
    "rate card", "pricing table", "contract value",
    "raise a ticket", "escalate", "create ticket",
    "log a ticket", "our current rates", "vendor rate",
]

# ── Priority rules ────────────────────────────────────────────
PRIORITY_KEYWORDS = {
    "critical": ["breach", "outage", "data loss", "security incident", "urgent"],
    "high":     ["rate card", "pricing", "contract value", "legal", "compliance"],
    "medium":   ["vendor", "onboarding", "policy", "sop", "process"],
    "low":      [],
}

def get_priority(question: str) -> str:
    q = question.lower()
    for priority, keywords in PRIORITY_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            return priority
    return "medium"

def is_direct_ticket(question: str) -> bool:
    q = question.lower()
    return any(kw in q for kw in DIRECT_TICKET_KEYWORDS)
