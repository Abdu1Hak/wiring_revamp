from langgraph.graph import StateGraph, END
from .state import PreProcessState
from .nodes import (
    check_vector_db_node,
    validate_datasheet_node,
    web_search_node,
    dispatch_ingestion_node,
    poll_and_finalize_node,
)
# ─── Routing Functions (conditional edges) ────────────────────────────────────
def route_after_check(state: PreProcessState) -> str:
    """After checking vector DB: skip if already indexed."""
    if state["already_indexed"]:
        return "already_done"
    return "validate"

def route_after_validation(state: PreProcessState) -> str:
    """After validation: search web if no valid PDF, else dispatch directly."""
    if state.get("status") == "failed":
        return "failed"
    if state["needs_web_search"]:
        return "search"
    return "dispatch"

def route_after_web_search(state: PreProcessState) -> str:
    """After web search: dispatch if we got a PDF, else fail."""
    if state.get("status") == "failed" or not state.get("pdf_base64"):
        return "failed"
    return "dispatch"

def route_after_dispatch(state: PreProcessState) -> str:
    """After dispatch: finalize if job dispatched, else fail."""
    if state.get("status") == "failed":
        return "failed"
    return "finalize"

# ─── Graph Builder ────────────────────────────────────────────────────────────
def build_preprocess_graph():
    # pyrefly: ignore [bad-specialization]
    g = StateGraph(PreProcessState)
    # Register nodes
    g.add_node("check_vector_db",    check_vector_db_node)
    g.add_node("validate_datasheet", validate_datasheet_node)
    g.add_node("web_search",         web_search_node)
    g.add_node("dispatch_ingestion", dispatch_ingestion_node)
    g.add_node("poll_and_finalize",  poll_and_finalize_node)

    # Entry point
    g.set_entry_point("check_vector_db")

    # Conditional edges
    g.add_conditional_edges(
        "check_vector_db",
        route_after_check,
        {"already_done": END, "validate": "validate_datasheet"},
    )
    g.add_conditional_edges(
        "validate_datasheet",
        route_after_validation,
        {"dispatch": "dispatch_ingestion", "search": "web_search", "failed": END},
    )
    g.add_conditional_edges(
        "web_search",
        route_after_web_search,
        {"dispatch": "dispatch_ingestion", "failed": END},
    )
    g.add_conditional_edges(
        "dispatch_ingestion",
        route_after_dispatch,
        {"finalize": "poll_and_finalize", "failed": END},
    )
    g.add_edge("poll_and_finalize", END)
    return g.compile()

# Singleton — import this in FastAPI routes
preprocess_graph = build_preprocess_graph()