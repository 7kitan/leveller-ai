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
    force: bool = False,
    lang: str = "vi",
    on_update=None,
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
                # Always load jd_timestamp if record exists
                jd_timestamp = int(job_record.updated_at.timestamp()) if job_record.updated_at else int(job_record.created_at.timestamp())
                
                # 1. Try JSON blob first
                if job_record.extracted_requirements_json:
                    pre_jd_requirements = job_record.extracted_requirements_json
                    _logger.info(f"[ORCHESTRATOR] ✓ Using extracted_requirements_json from job_id={job_id}")
                
                # 2. Fallback to JobSkillRequirement table (the "separate columns" the user mentioned)
                elif job_record.skills_required:
                    _logger.info(f"[ORCHESTRATOR] Found {len(job_record.skills_required)} items in JobSkillRequirement table. Assembling...")
                    assembled_reqs = []
                    for jsr in job_record.skills_required:
                        # Join with Skill to get the name
                        skill_name = jsr.skill.name if jsr.skill else "Unknown Skill"
                        
                        # Check if this is a skill group
                        if jsr.is_group:
                            # Skill group: user needs ANY ONE (or N) from alternatives
                            assembled_reqs.append({
                                "type": "group",
                                "skill": skill_name,  # Group name (e.g., "3D Modeling Software")
                                "is_group": True,
                                "group_strategy": jsr.group_strategy,
                                "alternative_skills": jsr.alternative_skills or [],
                                "min_required": jsr.min_required or 1,
                                "target_level": jsr.required_level or "Junior",
                                "years_required": jsr.min_years_exp or 0,
                                "is_mandatory": jsr.is_mandatory,
                                "importance_weight": jsr.importance_weight or 5
                            })
                        else:
                            # Individual skill (existing logic)
                            assembled_reqs.append({
                                "type": "skill",
                                "skill": skill_name,
                                "target_level": jsr.required_level or "Junior",
                                "years_required": jsr.min_years_exp or 0,
                                "is_mandatory": jsr.is_mandatory,
                                "importance_weight": jsr.importance_weight or 5
                            })
                    pre_jd_requirements = assembled_reqs
                    _logger.info(f"[ORCHESTRATOR] ✓ Assembled {len(pre_jd_requirements)} requirements from separate DB columns.")

                if pre_jd_requirements:
                    # Successfully loaded requirements (from JSON or Table)
                    pre_jd_parsed = {
                        "job_title": job_record.title_raw or "Unknown",
                        "requirements": pre_jd_requirements,
                    }
                    _logger.info(
                        f"[ORCHESTRATOR] Path A READY | title={job_record.title_raw} | ts={jd_timestamp}\n"
                        f"  → SKIPPING LLM extraction in gap_analysis_llm_node"
                    )
                elif job_record.raw_text:
                    # Fallback: use raw_text if not yet extracted
                    jd_text = job_record.raw_text
                    _logger.info(
                        f"[ORCHESTRATOR] job_id={job_id} has raw_text but no extracted_requirements_json. ts={jd_timestamp}"
                    )
                else:
                    _logger.warning(f"[ORCHESTRATOR] job_id={job_id} has no raw_text either")
        except Exception as e:
            _logger.warning(f"[ORCHESTRATOR] Failed to pre-populate from job_id: {e}")
            import traceback
            _logger.warning(traceback.format_exc())

    # ── Load CV metadata (timestamp) ──────────────────────────────────────────
    cv_timestamp = 0
    if cv_id and db:
        try:
            import uuid as _uuid
            from shared.models import UserCV
            cv_record = db.query(UserCV).filter(UserCV.id == _uuid.UUID(cv_id)).first()
            if cv_record:
                cv_timestamp = int(cv_record.updated_at.timestamp()) if cv_record.updated_at else int(cv_record.created_at.timestamp())
                _logger.info(f"[ORCHESTRATOR] CV timestamp loaded: {cv_timestamp}")
        except Exception as e:
            _logger.warning(f"[ORCHESTRATOR] Failed to load CV timestamp: {e}")

    final_jd_timestamp = locals().get("jd_timestamp") or 0

    initial_state: GapAnalysisStateV3 = {
        "cv_id": cv_id,
        "user_id": user_id,
        "jd_text": jd_text,
        "job_id": job_id,
        "jd_context": jd_context,
        "lang": lang,
        "db": db,
        "cv_parsed": None,
        # ── Pre-populated from job_id (SKIP LLM extraction) ────────────────────
        "jd_requirements": pre_jd_requirements,
        "jd_parsed": pre_jd_parsed,
        "cv_timestamp": cv_timestamp,
        "jd_timestamp": final_jd_timestamp,
        "force_recompute": force,
        # ─────────────────────────────────────────────────────────────────────
        "gap_analysis": None,
        "course_recommendations": None,
        "career_roadmap": None,
        "final_report": None,
        "status": "started",
        "error": None,
    }

    # ── Progressive Loading with astream ──────────────────────────────────────
    final_state = initial_state
    async for event in gap_v3_graph.astream(initial_state):
        # event is a dict: {node_name: {state_updates}}
        for node_name, state_update in event.items():
            final_state.update(state_update)
            
            # Nếu node quan trọng hoàn thành, trigger callback để UI cập nhật sớm
            if node_name in ["gap_analysis", "course_agent", "roadmap", "finalize"]:
                if on_update:
                    try:
                        # Gửi partial report về cho Celery task
                        partial_report = {
                            "overall_match_pct": (final_state.get("gap_analysis") or {}).get("overall_match_pct") or 0,
                            "overall_assessment": (final_state.get("gap_analysis") or {}).get("overall_assessment") or "",
                            "skill_gaps": (final_state.get("gap_analysis") or {}).get("skill_gaps") or [],
                            "course_recommendations": final_state.get("course_recommendations") or [],
                            "selected_youtube_videos": final_state.get("selected_youtube_videos") or [],
                            "career_roadmap": final_state.get("career_roadmap") or {},
                            "status": final_state.get("status") or "processing",
                            "is_cached": final_state.get("is_cached", False),
                            "node": node_name
                        }
                        await on_update(partial_report)
                    except Exception as up_err:
                        _logger.warning(f"[ORCHESTRATOR] Callback failed: {up_err}")

    result = final_state

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
