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
# # assistant/state.py
# from typing import TypedDict, Optional, List, Dict, Any

# class AssistantState(TypedDict):
#     # ── Identity ─────────────────────────────────────────────────────────
#     thread_id:    str
#     user_id:      str
#     trace_id:     str

#     # ── User context ─────────────────────────────────────────────────────
#     industry:     Optional[str]
#     department:   Optional[str]
#     message:      str                  # current user message

#     # ── Conversation ─────────────────────────────────────────────────────
#     history:      List[Dict[str, str]] # [{role, content}, ...]

#     # ── Intent ───────────────────────────────────────────────────────────
#     intent:       Optional[str]        # "clarify" | "retrieve" | "ticket"
#     clarify_question: Optional[str]    # question to ask back

#     # ── Retrieval ────────────────────────────────────────────────────────
#     retrieved_chunks:  List[Dict[str, Any]]
#     evidence_score:    float
#     refined_query:     Optional[str]

#     # ── Answer ───────────────────────────────────────────────────────────
#     answer:       Optional[str]
#     citations:    List[str]
#     rationale:    Optional[str]

#     # ── Ticket ───────────────────────────────────────────────────────────
#     ticket_id:    Optional[str]        # DB id
#     notion_ticket_id: Optional[str]    # Notion page id
#     notion_url:   Optional[str]
#     ticket_status: Optional[str]       # open|in_progress|closed
#     priority:     Optional[str]        # low|medium|high|critical

#     # ── Flow control ─────────────────────────────────────────────────────
#     next_action:  Optional[str]        # used by conditional edges
#     error:        Optional[str]

# # ── Evidence threshold ────────────────────────────────────────────────────
# EVIDENCE_THRESHOLD = 0.45

# # ── Priority rules by keyword ─────────────────────────────────────────────
# PRIORITY_RULES = {
#     "critical": ["breach", "outage", "data loss", "security incident", "urgent"],
#     "high":     ["rate card", "pricing", "contract value", "legal", "compliance"],
#     "medium":   ["vendor", "onboarding", "policy", "sop", "process"],
#     "low":      ["general", "question", "information", "how to"],
# }

# # ── Policy keywords → direct ticket (skip retrieval) ─────────────────────
# DIRECT_TICKET_KEYWORDS = [
#     "rate card", "pricing table", "contract value", "raise a ticket",
#     "escalate", "create ticket", "log a ticket", "our current rates",
# ]

# def get_priority(question: str) -> str:
#     q = question.lower()
#     for priority, keywords in PRIORITY_RULES.items():
#         if any(kw in q for kw in keywords):
#             return priority
#     return "medium"

# def is_direct_ticket(question: str) -> bool:
#     q = question.lower()
#     return any(kw in q for kw in DIRECT_TICKET_KEYWORDS)