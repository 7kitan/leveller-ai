"""
CV Parsing LangGraph Orchestrator — Pipeline 1.
Chạy 1 lần khi user upload CV.
"""

from langgraph.graph import StateGraph, END
from ..states import CVParsingState
from .nodes.cv_parsing_nodes import (
    extract_text_node,
    llm_parse_cv_node,
    normalize_cv_node,
    persist_cv_data_node,
)


def _should_continue(state: CVParsingState) -> str:
    if state.get("error") or state.get("status") == "failed":
        return "end"
    return "continue"


# Build graph
cv_parsing_workflow = StateGraph(CVParsingState)

cv_parsing_workflow.set_entry_point("extract_text")
cv_parsing_workflow.add_node("extract_text", extract_text_node)
cv_parsing_workflow.add_node("llm_parse", llm_parse_cv_node)
cv_parsing_workflow.add_node("normalize", normalize_cv_node)
cv_parsing_workflow.add_node("persist", persist_cv_data_node)

cv_parsing_workflow.add_conditional_edges(
    "extract_text", _should_continue, {"continue": "llm_parse", "end": END}
)
cv_parsing_workflow.add_conditional_edges(
    "llm_parse", _should_continue, {"continue": "normalize", "end": END}
)
cv_parsing_workflow.add_conditional_edges(
    "normalize", _should_continue, {"continue": "persist", "end": END}
)
cv_parsing_workflow.add_edge("persist", END)

cv_parsing_graph = cv_parsing_workflow.compile()


async def run_cv_parsing_pipeline(cv_id: str, user_id: str, db) -> dict:
    """
    Entry point: Parse CV → structured data → save to DB.
    Gọi từ Celery task sau khi user upload CV thành công.
    """
    initial_state: CVParsingState = {
        "cv_id": cv_id,
        "user_id": user_id,
        "db": db,
        "raw_text": None,
        "is_ocr": False,
        "cv_parsed": None,
        "status": "started",
        "error": None,
    }

    result = await cv_parsing_graph.ainvoke(initial_state)

    if result.get("cv_parsed"):
        return {"status": "success", "cv_parsed": result["cv_parsed"], "cv_id": cv_id}

    return {
        "status": "failed",
        "error": result.get("error", "CV parsing failed with no error"),
        "cv_id": cv_id,
    }
