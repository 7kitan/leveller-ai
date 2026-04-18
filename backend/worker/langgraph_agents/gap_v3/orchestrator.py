"""
gap_v3 Orchestrator: LangGraph cho toàn bộ Gap Analysis v3 pipeline.
OPTIMIZED: 5 LLM calls → 2 LLM calls total.
  Pipeline: load_cv → gap_analysis → course_agent → roadmap → finalize

  LLM call #1: gap_analysis_llm_node  (JD extract + gap analysis + top_gaps inline)
  LLM call #2: course_recommendation_llm_node → _llm_select_courses_and_roadmap_unified
                (unified: course selection for ALL gaps + roadmap building)
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
    import logging as _log
    _logger = _log.getLogger("gap_analysis_v3")
    _logger.info(
        f"[ORCHESTRATOR] run_gap_analysis_v3 ENTRY\n"
        f"  cv_id     : {cv_id}\n"
        f"  user_id   : {user_id}\n"
        f"  job_id    : {job_id}\n"
        f"  jd_text   : {'<provided, ' + str(len(jd_text or '')) + ' chars>' if jd_text else '<NONE>'}\n"
        f"  jd_text[:300]: {repr((jd_text or '')[:300])}\n"
        f"  jd_context: {repr(jd_context)}"
    )

    # ── OPTIMIZED: Pre-populate jd_requirements from job_id (no extra LLM) ─────
    pre_jd_requirements = None
    pre_jd_parsed = None

    if job_id and db:
        try:
            import uuid as _uuid
            from shared.models import Job
            job_uuid = _uuid.UUID(job_id)
            job_record = db.query(Job).filter(Job.id == job_uuid).first()
            if job_record:
                if job_record.extracted_requirements_json:
                    # Use pre-extracted requirements from DB — SKIP LLM extraction
                    pre_jd_requirements = job_record.extracted_requirements_json
                    pre_jd_parsed = {
                        "job_title": job_record.title_raw or "Unknown",
                        "requirements": pre_jd_requirements,
                    }
                    _logger.info(
                        f"[ORCHESTRATOR] ✓ Pre-populated from job_id={job_id}\n"
                        f"  title        : {job_record.title_raw}\n"
                        f"  requirements  : {len(pre_jd_requirements)} skills\n"
                        f"  → SKIPPING LLM extraction in gap_analysis_llm_node"
                    )
                elif job_record.raw_text:
                    # Fallback: use raw_text if not yet extracted
                    jd_text = job_record.raw_text
                    _logger.info(
                        f"[ORCHESTRATOR] job_id={job_id} has raw_text but no extracted_requirements_json"
                    )
                else:
                    _logger.warning(f"[ORCHESTRATOR] job_id={job_id} has no raw_text either")
        except Exception as e:
            _logger.warning(f"[ORCHESTRATOR] Failed to pre-populate from job_id: {e}")

    initial_state: GapAnalysisStateV3 = {
        "cv_id": cv_id,
        "user_id": user_id,
        "jd_text": jd_text,
        "job_id": job_id,
        "jd_context": jd_context,
        "db": db,
        "cv_parsed": None,
        # ── Pre-populated from job_id (SKIP LLM extraction) ────────────────────
        "jd_requirements": pre_jd_requirements,
        "jd_parsed": pre_jd_parsed,
        # ─────────────────────────────────────────────────────────────────────
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
