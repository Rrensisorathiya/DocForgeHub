# assistant/graph.py
from langgraph.graph import StateGraph, END
from assistant.state import AssistantState
from assistant.nodes import (
    context_loader, intent_classifier, clarify_node,
    rag_retrieval, answer_node, ticket_node, memory_save,
)
from utils.logger import setup_logger
logger = setup_logger(__name__)


def _route_intent(state: AssistantState) -> str:
    intent = state.get("intent", "retrieve")
    logger.debug(f"route_intent → {intent}")
    if intent == "clarify":  return "clarify"
    if intent == "ticket":   return "ticket"
    return "retrieve"


def _route_evidence(state: AssistantState) -> str:
    score = state.get("evidence_score", 0.0)
    result = "answer" if score >= 0.45 else "ticket"
    logger.debug(f"route_evidence score={score:.3f} → {result}")
    return result


def build_graph():
    g = StateGraph(AssistantState)

    g.add_node("context_loader",    context_loader)
    g.add_node("intent_classifier", intent_classifier)
    g.add_node("clarify_node",      clarify_node)
    g.add_node("rag_retrieval",     rag_retrieval)
    g.add_node("answer_node",       answer_node)
    g.add_node("ticket_node",       ticket_node)
    g.add_node("memory_save",       memory_save)

    g.set_entry_point("context_loader")
    g.add_edge("context_loader", "intent_classifier")

    g.add_conditional_edges("intent_classifier", _route_intent, {
        "clarify":  "clarify_node",
        "retrieve": "rag_retrieval",
        "ticket":   "ticket_node",
    })

    g.add_conditional_edges("rag_retrieval", _route_evidence, {
        "answer": "answer_node",
        "ticket": "ticket_node",
    })

    g.add_edge("clarify_node", "memory_save")
    g.add_edge("answer_node",  "memory_save")
    g.add_edge("ticket_node",  "memory_save")
    g.add_edge("memory_save",  END)

    return g.compile()


# Singleton
assistant_graph = build_graph()


def run_assistant(thread_id: str, message: str,
                  user_id: str = "anonymous",
                  industry: str = None,
                  department: str = None) -> dict:
    import uuid
    from assistant.memory import db_create_thread

    db_create_thread(thread_id, user_id, industry, department)

    initial: AssistantState = {
        "thread_id":        thread_id,
        "user_id":          user_id,
        "trace_id":         str(uuid.uuid4())[:8],
        "industry":         industry,
        "department":       department,
        "message":          message,
        "history":          [],
        "intent":           None,
        "clarify_question": None,
        "retrieved_chunks": [],
        "evidence_score":   0.0,
        "refined_query":    None,
        "answer":           None,
        "citations":        [],
        "notion_ticket_id": None,
        "notion_url":       None,
        "ticket_status":    None,
        "priority":         "medium",
        "next_action":      None,
        "error":            None,
    }

    logger.info(f"run_assistant: thread={thread_id} msg='{message[:60]}'")
    final = assistant_graph.invoke(initial)
    logger.info(f"done: intent={final.get('intent')} ticket={final.get('notion_ticket_id')}")
    return final
# # assistant/graph.py
# from langgraph.graph import StateGraph, END
# from assistant.state import AssistantState
# from assistant.nodes import (
#     context_loader, intent_classifier, clarify_node,
#     rag_retrieval, answer_node, ticket_node, memory_save,
# )
# from utils.logger import setup_logger

# logger = setup_logger(__name__)


# def route_intent(state: AssistantState) -> str:
#     """Conditional edge after intent_classifier."""
#     intent = state.get("intent", "retrieve")
#     logger.debug(f"route_intent → {intent}")
#     if intent == "clarify":
#         return "clarify"
#     elif intent == "ticket":
#         return "ticket"
#     return "retrieve"


# def route_evidence(state: AssistantState) -> str:
#     """Conditional edge after rag_retrieval."""
#     score = state.get("evidence_score", 0.0)
#     logger.debug(f"route_evidence → score={score:.3f}")
#     return "answer" if score >= 0.45 else "ticket"


# def build_graph() -> StateGraph:
#     g = StateGraph(AssistantState)

#     # ── Add nodes ─────────────────────────────────────────────────────
#     g.add_node("context_loader",     context_loader)
#     g.add_node("intent_classifier",  intent_classifier)
#     g.add_node("clarify_node",       clarify_node)
#     g.add_node("rag_retrieval",      rag_retrieval)
#     g.add_node("answer_node",        answer_node)
#     g.add_node("ticket_node",        ticket_node)
#     g.add_node("memory_save",        memory_save)

#     # ── Entry point ───────────────────────────────────────────────────
#     g.set_entry_point("context_loader")

#     # ── Linear edges ──────────────────────────────────────────────────
#     g.add_edge("context_loader",    "intent_classifier")

#     # ── Conditional: intent ───────────────────────────────────────────
#     g.add_conditional_edges(
#         "intent_classifier",
#         route_intent,
#         {
#             "clarify":  "clarify_node",
#             "retrieve": "rag_retrieval",
#             "ticket":   "ticket_node",
#         }
#     )

#     # ── Conditional: evidence score ───────────────────────────────────
#     g.add_conditional_edges(
#         "rag_retrieval",
#         route_evidence,
#         {
#             "answer": "answer_node",
#             "ticket": "ticket_node",
#         }
#     )

#     # ── Converge to memory_save ───────────────────────────────────────
#     g.add_edge("clarify_node",  "memory_save")
#     g.add_edge("answer_node",   "memory_save")
#     g.add_edge("ticket_node",   "memory_save")
#     g.add_edge("memory_save",   END)

#     return g.compile()


# # Singleton compiled graph
# assistant_graph = build_graph()


# def run_assistant(thread_id: str, message: str,
#                   user_id: str = "anonymous",
#                   industry: str = None,
#                   department: str = None) -> dict:
#     """
#     Main entry point — run the full LangGraph assistant.
#     Returns the final state dict.
#     """
#     import uuid
#     from assistant.memory import create_thread_in_db

#     # Ensure thread exists in DB
#     create_thread_in_db(thread_id, user_id, industry, department)

#     initial_state: AssistantState = {
#         "thread_id":         thread_id,
#         "user_id":           user_id,
#         "trace_id":          str(uuid.uuid4())[:8],
#         "industry":          industry,
#         "department":        department,
#         "message":           message,
#         "history":           [],
#         "intent":            None,
#         "clarify_question":  None,
#         "retrieved_chunks":  [],
#         "evidence_score":    0.0,
#         "refined_query":     None,
#         "answer":            None,
#         "citations":         [],
#         "rationale":         None,
#         "ticket_id":         None,
#         "notion_ticket_id":  None,
#         "notion_url":        None,
#         "ticket_status":     None,
#         "priority":          "medium",
#         "next_action":       None,
#         "error":             None,
#     }

#     logger.info(f"Running assistant: thread={thread_id} msg='{message[:60]}'")
#     final_state = assistant_graph.invoke(initial_state)
#     logger.info(f"Assistant done: intent={final_state.get('intent')} "
#                 f"ticket={final_state.get('notion_ticket_id')}")
#     return final_state