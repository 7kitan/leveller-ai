"""
gap_v3 Roadmap + Finalize nodes.
"""

import logging
import json as _json
from typing import Dict, Any, Optional

from ..states import GapAnalysisStateV3

logger = logging.getLogger("roadmap_v3")


def _indent_data(text: str) -> str:
    """Indent each line for log readability."""
    return "\n".join("    " + line for line in text.split("\n"))


async def roadmap_synthesis_node(state: GapAnalysisStateV3) -> GapAnalysisStateV3:
    """
    STEP 5: Roadmap pass-through (OPTIMIZED — roadmap already built inside course_recommendation_llm_node).

    Previous version: separate LLM call → removed.
    Current version : just return career_roadmap from state (already computed).
    """
    career_roadmap = state.get("career_roadmap") or {}
    logger.info(
        "\n" + "=" * 50 + "\n"
        "[STEP 5] roadmap_synthesis (PASS-THROUGH) | cv_id=" + state.get("cv_id", "?") +
        " | roadmap_stages=" + str(len(career_roadmap.get("stages") or []))
    )
    return {**state, "career_roadmap": career_roadmap, "status": "roadmap_done"}


async def _llm_build_roadmap(
    gaps_str: str,
    courses_str: str,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    LEGACY: Gọi LLM để tạo career roadmap JSON.
    NOTE: Currently integrated into course_recommendation_llm_node.
    This function kept for potential standalone use.
    """
    from ..utils.llm_helpers import llm_json_completion
    from shared.prompt_manager import get_prompt

    # ── Get prompt from prompt manager ──────────────────────────────────────
    try:
        prompt, llm_config = get_prompt(
            'roadmap_building',
            selected_courses=courses_str,
            skill_gaps=gaps_str,
            target_role="Target Role"  # TODO: Pass actual target role if available
        )
        
        if not prompt:
            raise ValueError("Prompt manager returned empty prompt")
            
        logger.info("[ROADMAP] Using managed prompt: roadmap_building")
        
    except Exception as e:
        logger.warning(f"[ROADMAP] Failed to load managed prompt, using fallback: {e}")
        
        # Fallback to hardcoded prompt
        llm_config = {"temperature": 0.6, "max_tokens": 3000}
        prompt = (
            "Build a personalized learning roadmap (in Vietnamese). "
            "Use English for skill names.\n\n"
            "## Skill gaps (prioritized):\n" + gaps_str + "\n\n"
            "## Recommended courses:\n" + courses_str + "\n\n"
            "Output JSON:\n"
            '{"stages": [{"stage": 1, "focus": "...", "duration_weeks": 4, '
            '"skills_acquired": [...], "courses_taken": [...], '
            '"milestones": [{"week": 1, "milestone": "..."}], '
            '"total_weeks": 0, "total_hours": 0, "summary": "..."}'
            "}"
        )

    logger.info(f"[STEP 5/LLM] Calling LLM | prompt_chars={len(prompt)}")

    temperature = llm_config.get("temperature", 0.6) if llm_config else 0.6
    result = await llm_json_completion(
        prompt=prompt,
        temperature=temperature,
        call_name="build_roadmap",
        user_id=user_id
    )
    return result or {}


def _format_gaps_for_prompt(gaps: list) -> str:
    lines = []
    for g in gaps[:6]:
        lines.append(
            "- "
            + (g.get("skill") or "?")
            + " | severity="
            + str(g.get("severity") or "?")
            + " | months="
            + str(g.get("estimated_months") or 3)
            + " | effort="
            + (g.get("learning_effort") or "?")
            + " | path="
            + (g.get("learning_path") or "")
        )
    return "\n".join(lines)


def _format_courses_for_prompt(courses: list) -> str:
    lines = []
    for c in courses[:8]:
        lines.append(
            "- "
            + (c.get("title") or "?")
            + " | platform="
            + (c.get("platform") or "?")
            + " | hrs="
            + str(float(c.get("duration_hours") or 0))
            + " | cert="
            + str(c.get("is_certification"))
        )
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# STEP 6: Finalize Report
# ══════════════════════════════════════════════════════════════════════════════


async def finalize_report_node(state: GapAnalysisStateV3) -> GapAnalysisStateV3:
    """
    STEP 6: Merge all outputs → final_report JSON.
    1. Build course_recommendations output
    2. Calculate radar chart scores (5-dimension CV vs JD comparison)
    3. Cache to Redis
    4. Persist to UserAnalysis table
    """
    gap_analysis = state.get("gap_analysis") or {}
    course_recommendations = state.get("course_recommendations") or []
    career_roadmap = state.get("career_roadmap") or {}
    cv_parsed = state.get("cv_parsed") or {}

    logger.info(
        "\n" + "=" * 50 + "\n"
        "[STEP 6] finalize_report_node | cv_id=" + state.get("cv_id", "?")
    )

    # Build course_recommendations output
    course_output = []
    for c in course_recommendations:
        course_output.append(
            {
                "course_id": c.get("course_id") or "",
                "gap_skill": c.get("gap_skill") or "",
                "gap_severity": c.get("gap_severity") or "MEDIUM",
                "gap_learning_path": c.get("gap_learning_path") or "",
                "gap_estimated_months": float(c.get("gap_estimated_months") or 0),
                "is_critical": bool(c.get("is_critical") or False),
                "title": c.get("title") or "",
                "platform": c.get("platform") or "",
                "url": c.get("url") or "",
                "level": c.get("level") or "Unknown",
                "provider": c.get("provider") or "",
                "duration_hours": float(c.get("duration_hours") or 0),
                "is_certification": bool(c.get("is_certification") or False),
                "cost_usd": float(c.get("cost_usd") or 0),
                "tags": list(c.get("tags") or []),
                "similarity": float(c.get("similarity") or 0),
                "rank_score": float(c.get("rank_score") or 0),
                "selection_reason": c.get("selection_reason") or "",
            }
        )

    # ── Match Calculation (Enriched with real DB stats) ──────────────────
    llm_match_pct = float(gap_analysis.get("overall_match_pct") or 0)
    skill_gaps = list(gap_analysis.get("skill_gaps") or [])
    
    # Enrich gaps with real Market Data (demand, impact)
    try:
        from services.analysis_service.growth_calculator import calculate_skill_impact
        potential_match_pct, enriched_gaps = calculate_skill_impact(
            skill_gaps=skill_gaps,
            job_id=state.get("job_id"),
            current_match_pct=llm_match_pct,
            db=db
        )
        # Update gaps in the gap_analysis object for final report
        gap_analysis["skill_gaps"] = enriched_gaps
        logger.info(f"[STEP 6] Gaps enriched with DB stats | potential={potential_match_pct}%")
    except Exception as e:
        logger.warning(f"[STEP 6] Failed to enrich gaps with DB stats: {e}")
        potential_match_pct = float(gap_analysis.get("potential_match_pct") or 0)

    overall_match_pct = llm_match_pct
    
    # Build match_breakdown for frontend (5 dimensions)
    # We use the breakdown returned by the LLM as it understands synonyms
    llm_breakdown = gap_analysis.get("match_breakdown") or {}
    
    # Mapping English LLM keys to normalized keys expected by frontend
    key_map = {
        "Technical Skills": ["Technical Skills", "Technology", "Kỹ năng kỹ thuật"],
        "Soft Skills": ["Soft Skills", "Kỹ năng mềm"],
        "Tools & Frameworks": ["Tools & Frameworks", "Tools", "Công cụ & Framework"],
        "Domain Knowledge": ["Domain Knowledge", "Domain", "Kiến thức Domain"],
        "Certifications": ["Certifications", "Certs", "Chứng chỉ"]
    }
    
    match_breakdown = {}
    for norm_key, aliases in key_map.items():
        val = 0
        # Check if any alias exists in LLM response
        for alias in aliases:
            if alias in llm_breakdown:
                val = llm_breakdown[alias]
                break
        
        # Fallback: if JD didn't have this category, LLM should have set it to 100 
        # (based on our new prompt instruction), but we ensure it here too.
        match_breakdown[norm_key] = float(val)

    # Ensure all 5 dimensions exist to avoid frontend issues
    for dim in ["Technical Skills", "Soft Skills", "Tools & Frameworks", "Domain Knowledge", "Certifications"]:
        if dim not in match_breakdown:
            match_breakdown[dim] = 0.0

    final_report = {
        "overall_match_pct": float(overall_match_pct),
        "potential_match_pct": float(potential_match_pct),
        "overall_assessment": gap_analysis.get("overall_assessment") or "",
        "strengths": list(gap_analysis.get("strengths") or []),
        "weaknesses": list(gap_analysis.get("weaknesses") or []),
        "skill_gaps": list(gap_analysis.get("skill_gaps") or []),
        "gap_summary": gap_analysis.get("gap_summary") or {},
        "match_breakdown": match_breakdown,
        "transferable_insights": list(gap_analysis.get("transferable_insights") or []),
        "jd_context": gap_analysis.get("jd_context") or "",
        "job_id": state.get("job_id"),  # ✅ ADD THIS - needed for API enrichment
        "course_recommendations": course_output,
        "selected_youtube_videos": state.get("selected_youtube_videos") or [],
        "youtube_videos": state.get("youtube_videos") or [],
        "career_roadmap": career_roadmap,
        "cv_parsed": cv_parsed,
        "notes": [
            "Analysis Method: LLM Holistic v3 Optimized (2 LLM calls total)",
            "CV parsed=" + (cv_parsed.get("full_name") or state.get("cv_id", "?")),
            "JD context=" + (gap_analysis.get("jd_context") or "?"),
            "Courses recommended=" + str(len(course_output)),
            "Scoring: 100% AI Semantic Analysis (math-based)",
        ],
    }

    # ── Log final report summary ─────────────────────────────────────────────
    logger.info(
        f"\n{'═' * 70}\n"
        f"[FINAL REPORT] ┌─── complete report | cv_id={state.get('cv_id')}\n"
        f"               │ overall_match_pct  : {final_report['overall_match_pct']}%\n"
        f"               │ potential_match_pct: {final_report['potential_match_pct']}%\n"
        f"               │ strengths          : {len(final_report['strengths'])}\n"
        f"               │ weaknesses         : {len(final_report['weaknesses'])}\n"
        f"               │ skill_gaps         : {len(final_report['skill_gaps'])}\n"
        f"               │ courses            : {len(final_report['course_recommendations'])}\n"
        f"               │ roadmap stages     : {len(final_report.get('career_roadmap', {}).get('stages', []))}\n"
        f"               │ transferable       : {len(final_report['transferable_insights'])}\n"
        f"               └─────────\n"
        f"[FINAL REPORT] FULL REPORT JSON (first 3000 chars):\n"
        f"{_indent_data(_json.dumps(final_report, ensure_ascii=False, indent=2)[:3000])}\n"
        f"{'═' * 70}\n"
    )

    # Redis cache
    _cache_result(state.get("cv_id") or "?", state.get("job_id"), final_report)

    logger.info(
        "[STEP 6] ✓ Finalize DONE | match="
        + str(final_report.get("overall_match_pct"))
        + "% | gaps="
        + str(len(final_report.get("skill_gaps") or []))
        + " | courses="
        + str(len(course_output))
        + "\n"
        + "=" * 50
    )

    return {**state, "final_report": final_report, "status": "completed"}


def _cache_result(cv_id: str, job_id: str, report: Dict):
    """Cache final_report vào Redis."""
    try:
        from shared.redis_client import result_cache
        from ..config import GAP_CACHE_TTL

        key = "gap:" + cv_id + ":" + (job_id or "market")
        result_cache.setex(key, GAP_CACHE_TTL, _json.dumps(report))
        logger.info("[STEP 6] Redis cached: " + key)
    except Exception as e:
        logger.warning("[STEP 6] Redis cache failed: " + str(e))


def _persist_db(state: Dict, report: Dict):
    """Persist gap analysis result vào UserAnalysis table."""
    import uuid
    from datetime import datetime
    from shared.models import UserAnalysis

    db = state.get("db")
    if not db:
        logger.warning("[STEP 6] No db session — skipping DB persist")
        return

    try:
        db.rollback()  # reset any aborted transaction
    except Exception:
        pass

    try:
        cv_id_str = state.get("cv_id") or ""
        user_id_str = state.get("user_id") or ""

        record = UserAnalysis(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id_str) if user_id_str else None,
            cv_id=uuid.UUID(cv_id_str) if cv_id_str else None,
            job_id=uuid.UUID(state["job_id"]) if state.get("job_id") else None,
            match_score=float(report.get("overall_match_pct") or 0),
            result_json=report,
            created_at=datetime.now(),
        )
        db.add(record)
        db.commit()
        logger.info(
            "[STEP 6] ✓ Persisted UserAnalysis | id="
            + str(record.id)
            + " | cv_id="
            + cv_id_str
        )
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        logger.error("[STEP 6] ✗ DB persist failed: " + str(e))
