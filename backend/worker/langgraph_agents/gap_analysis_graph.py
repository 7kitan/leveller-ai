"""
Gap Analysis LangGraph Agent.

Flow:
  prep_context_node (load full CV from DB)
    → llm_gap_analyze_node (GPT phân tích toàn bộ)
    → course_lookup_node (query DB courses)
    → finalize_report_node (merge + format)
"""
from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional, List, Dict, Any
from sqlalchemy.orm import Session

from .nodes.gap_nodes import (
    prep_context_node,
    llm_gap_analyze_node,
    course_lookup_node,
    finalize_report_node,
)


class GapAnalysisState(TypedDict):
    # ── Input ──────────────────────────────
    cv_id: str
    user_id: str
    jd_requirements: List[Dict[str, Any]]   # Extracted JD reqs
    jd_context: str                          # JD title / vị trí
    db: Any                                  # SQLAlchemy Session (passed through)

    # ── Intermediate ───────────────────────
    cv_profile_text: Optional[str]           # Full CV context string
    llm_raw_output: Optional[Dict[str, Any]]
    course_results: Optional[List[Dict[str, Any]]]

    # ── Output ─────────────────────────────
    final_report: Optional[Dict[str, Any]]
    error: Optional[str]
    status: str


# ─── Build Graph ──────────────────────────────────────────────────────────────

def _should_continue(state: GapAnalysisState) -> str:
    """Edge condition: dừng sớm nếu có lỗi."""
    if state.get("status") == "failed" or state.get("error"):
        return "end"
    return "continue"


workflow = StateGraph(GapAnalysisState)

workflow.add_node("prep_context",    prep_context_node)
workflow.add_node("llm_gap_analyze", llm_gap_analyze_node)
workflow.add_node("course_lookup",   course_lookup_node)
workflow.add_node("finalize_report", finalize_report_node)

workflow.set_entry_point("prep_context")

# Conditional edges: dừng nếu có lỗi ở bất kỳ bước nào
workflow.add_conditional_edges(
    "prep_context",
    _should_continue,
    {"continue": "llm_gap_analyze", "end": END}
)
workflow.add_conditional_edges(
    "llm_gap_analyze",
    _should_continue,
    {"continue": "course_lookup", "end": END}
)
workflow.add_edge("course_lookup",   "finalize_report")
workflow.add_edge("finalize_report", END)

gap_analysis_graph = workflow.compile()


# ─── Public entry point ───────────────────────────────────────────────────────

async def run_gap_analysis_agent(
    cv_id: str,
    user_id: str,
    jd_requirements: List[Dict[str, Any]],
    db: Session,
    jd_context: str = "Vị trí chưa xác định",
) -> Dict[str, Any]:
    """
    Chạy Gap Analysis Agent và trả về final_report.
    Được gọi từ analysis_tasks.py thay cho GapCalculator.calculate_gap_v2().
    """
    initial_state: GapAnalysisState = {
        "cv_id": cv_id,
        "user_id": user_id,
        "jd_requirements": jd_requirements,
        "jd_context": jd_context,
        "db": db,
        "cv_profile_text": None,
        "llm_raw_output": None,
        "course_results": None,
        "final_report": None,
        "error": None,
        "status": "started",
    }

    result = await gap_analysis_graph.ainvoke(initial_state)

    if result.get("final_report"):
        return result["final_report"]

    # Fallback nếu agent thất bại
    error_msg = result.get("error", "Gap Analysis Agent returned no result")
    return {
        "overall_match_pct": 0,
        "overall_assessment": "Phân tích không thành công.",
        "strengths": [],
        "weaknesses": [],
        "breakdown": {"met": [], "partial": [], "gap": []},
        "gap_matrix": [],
        "skill_gaps": [],
        "course_recommendations": [],
        "recommendations": [],
        "notes": [f"ERROR: {error_msg}"]
    }
