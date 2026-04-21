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
    result = "answer" if score >= 0.20 else "ticket"
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
