"""
gap_v3 Orchestrator: LangGraph cho toàn bộ Gap Analysis v3 pipeline.
"""

from langgraph.graph import StateGraph, END
from .states import GapAnalysisStateV3
from .nodes.gap_nodes import (
    load_cv_parsed_data_node,
    extract_jd_node,
    gap_analysis_llm_node,
)
from .nodes.course_nodes import course_recommendation_llm_node
from .nodes.finalize_nodes import roadmap_synthesis_node, finalize_report_node


def _should_continue(state: GapAnalysisStateV3) -> str:
    if state.get("error") or state.get("status") == "failed":
        return "end"
    return "continue"


# ── Build LangGraph ──────────────────────────────────────────────────────

gap_v3_workflow = StateGraph(GapAnalysisStateV3)

gap_v3_workflow.set_entry_point("load_cv")
gap_v3_workflow.add_node("load_cv", load_cv_parsed_data_node)
gap_v3_workflow.add_node("gap_analysis", gap_analysis_llm_node)
gap_v3_workflow.add_node("course_agent", course_recommendation_llm_node)
gap_v3_workflow.add_node("roadmap", roadmap_synthesis_node)
gap_v3_workflow.add_node("finalize", finalize_report_node)

# Edges
gap_v3_workflow.add_conditional_edges(
    "load_cv", _should_continue, {"continue": "gap_analysis", "end": END}
)
gap_v3_workflow.add_conditional_edges(
    "gap_analysis", _should_continue, {"continue": "course_agent", "end": END}
)
gap_v3_workflow.add_conditional_edges(
    "course_agent", _should_continue, {"continue": "roadmap", "end": END}
)
gap_v3_workflow.add_edge("roadmap", "finalize")
gap_v3_workflow.add_edge("finalize", END)

gap_v3_graph = gap_v3_workflow.compile()


# ── Public entry point ────────────────────────────────────────────────────


async def run_gap_analysis_v3(
    cv_id: str,
    user_id: str,
    jd_text: str = None,
    job_id: str = None,
    db=None,
    jd_context: str = "Vị trí chưa xác định",
) -> dict:
    """
    Entry point cho toàn bộ Gap Analysis v3 pipeline.

    Pipeline:
      load_cv → extract_jd → gap_analysis → course_agent → roadmap → finalize

    Args:
        cv_id: CV UUID string
        user_id: User UUID string
        jd_text: Raw JD text (nếu user paste JD)
        job_id: Job UUID string (nếu chọn từ job list)
        db: SQLAlchemy session
        jd_context: JD title/position context

    Returns:
        final_report dict
    """
    initial_state: GapAnalysisStateV3 = {
        "cv_id": cv_id,
        "user_id": user_id,
        "jd_text": jd_text,
        "job_id": job_id,
        "jd_context": jd_context,
        "db": db,
        "cv_parsed": None,
        "jd_requirements": None,
        "jd_parsed": None,
        "gap_analysis": None,
        "course_recommendations": None,
        "career_roadmap": None,
        "final_report": None,
        "status": "started",
        "error": None,
    }

    result = await gap_v3_graph.ainvoke(initial_state)

    if result.get("final_report"):
        return result["final_report"]

    return {
        "overall_match_pct": 0,
        "overall_assessment": "Analysis failed.",
        "strengths": [],
        "weaknesses": [],
        "skill_gaps": [],
        "gap_summary": {},
        "transferable_insights": [],
        "course_recommendations": [],
        "career_roadmap": {},
        "notes": [f"ERROR: {result.get('error', 'Unknown')}"],
        "status": "failed",
    }
