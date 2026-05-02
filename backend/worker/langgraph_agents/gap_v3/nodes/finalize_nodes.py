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
    """Gọi LLM để tạo career roadmap JSON."""
    from ..utils.llm_helpers import llm_json_completion

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

    result = await llm_json_completion(
        prompt=prompt,
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

    # ── Calculate Radar Chart (5-dimension CV vs JD comparison) ──────────────
    # Dimensions: Technical Skills, Soft Skills, Tools & Frameworks, Domain Knowledge, Certifications
    radar_chart_data = None
    try:
        from shared.radar_dimensions import calculate_radar_scores, get_priority_gaps, SOFT_SKILL_CATEGORIES
        
        # Extract CV skills with categories (include ALL skills)
        cv_skills = []
        if cv_parsed and cv_parsed.get("skills"):
            for skill in cv_parsed["skills"]:
                if isinstance(skill, dict):
                    category = skill.get("category") or "Technology"
                    cv_skills.append({
                        "skill_name": skill.get("name") or skill.get("skill_name") or "",
                        "category": category
                    })
                elif isinstance(skill, str):
                    cv_skills.append({
                        "skill_name": skill,
                        "category": "Technology"
                    })
        
        # Extract JD skills with categories from jd_requirements (include ALL skills)
        jd_skills = []
        jd_requirements = state.get("jd_requirements") or []
        for req in jd_requirements:
            if isinstance(req, dict):
                skill_name = req.get("skill") or req.get("skill_name") or req.get("name") or ""
                category = req.get("category") or "Technology"
                if skill_name:
                    jd_skills.append({
                        "skill_name": skill_name,
                        "category": category
                    })
        
        # If we have both CV and JD skills, calculate radar scores
        if cv_skills and jd_skills:
            radar_chart_data = calculate_radar_scores(cv_skills, jd_skills)
            priority_gaps = get_priority_gaps(radar_chart_data, threshold=70.0)
            radar_chart_data["priority_gaps"] = priority_gaps
            
            # Extract soft skills match from radar chart (Soft Skills dimension)
            soft_skills_match_pct = None
            if "Soft Skills" in radar_chart_data.get("dimension_details", {}):
                soft_skills_match_pct = radar_chart_data["dimension_details"]["Soft Skills"]["match_percentage"]
            
            logger.info(
                f"[STEP 6] ✓ Radar chart calculated | "
                f"overall_match={radar_chart_data['overall_match']}% | "
                f"priority_gaps={len(priority_gaps)} | "
                f"5 dimensions: Technical Skills, Soft Skills, Tools & Frameworks, Domain Knowledge, Certifications"
            )
        else:
            logger.warning(
                f"[STEP 6] Radar chart skipped | "
                f"cv_skills={len(cv_skills)} | jd_skills={len(jd_skills)}"
            )
    except Exception as radar_err:
        logger.error(f"[STEP 6] Radar chart calculation failed: {radar_err}", exc_info=True)
    
    # ── Extract Soft Skills details from radar chart ─────────────────────────
    # Soft Skills is one of the 5 dimensions in radar chart
    soft_skills_comparison = None
    if radar_chart_data and "Soft Skills" in radar_chart_data.get("dimension_details", {}):
        soft_details = radar_chart_data["dimension_details"]["Soft Skills"]
        soft_skills_comparison = {
            "cv_soft_skills": soft_details["cv_skills"],
            "jd_soft_skills": soft_details["jd_skills"],
            "matched": soft_details["matched"],
            "missing": soft_details["missing"],
            "extra": soft_details["extra"],
            "match_percentage": soft_details["match_percentage"],
            "skill_count": soft_details["skill_count"]
        }
        
        logger.info(
            f"[STEP 6] ✓ Soft skills from radar chart | "
            f"match={soft_skills_comparison['match_percentage']}% | "
            f"cv={soft_details['skill_count']['cv']} | "
            f"jd={soft_details['skill_count']['jd']} | "
            f"missing={soft_details['skill_count']['missing']}"
        )

    # ── Calculate final match percentages ────────────────────────────────────
    # Use radar chart's overall match (includes all 5 dimensions)
    llm_match_pct = float(gap_analysis.get("overall_match_pct") or 0)
    overall_match_pct = radar_chart_data["overall_match"] if radar_chart_data else llm_match_pct
    soft_skills_match_pct = soft_skills_comparison["match_percentage"] if soft_skills_comparison else None
    
    # Build match_breakdown for frontend (5 dimensions)
    match_breakdown = {}
    if radar_chart_data:
        for dimension in radar_chart_data["dimensions"]:
            match_breakdown[dimension] = radar_chart_data["dimension_details"][dimension]["match_percentage"]
    
    logger.info(
        f"[STEP 6] Match percentages calculated:\n"
        f"  Overall match (5 dimensions): {overall_match_pct}%\n"
        f"  Soft skills: {soft_skills_match_pct}%\n"
        f"  LLM original: {llm_match_pct}%\n"
        f"  Match breakdown: {match_breakdown}"
    )

    final_report = {
        "overall_match_pct": float(overall_match_pct),  # Overall match from radar chart (5 dimensions)
        "soft_skills_match_pct": float(soft_skills_match_pct) if soft_skills_match_pct is not None else None,
        "llm_overall_match_pct": float(llm_match_pct),  # Original LLM match (for reference)
        "overall_assessment": gap_analysis.get("overall_assessment") or "",
        "strengths": list(gap_analysis.get("strengths") or []),
        "weaknesses": list(gap_analysis.get("weaknesses") or []),
        "skill_gaps": list(gap_analysis.get("skill_gaps") or []),
        "gap_summary": gap_analysis.get("gap_summary") or {},
        "match_breakdown": match_breakdown,  # 5-dimension breakdown for frontend radar chart
        "transferable_insights": list(gap_analysis.get("transferable_insights") or []),
        "jd_context": gap_analysis.get("jd_context") or "",
        "top_gaps": list(gap_analysis.get("top_gaps") or []),  # Optimized: inline from gap_analysis
        "course_recommendations": course_output,
        "selected_youtube_videos": state.get("selected_youtube_videos") or [],
        "youtube_videos": state.get("youtube_videos") or [], # Thêm hỗ trợ YouTube videos
        "career_roadmap": career_roadmap,
        "radar_chart": radar_chart_data,  # 5-dimension radar chart (Technical, Soft, Tools, Domain, Certifications)
        "soft_skills": soft_skills_comparison,  # Soft skills details (extracted from radar chart)
        "cv_parsed": cv_parsed,
        "notes": [
            "Analysis Method: LLM Holistic v3 Optimized (2 LLM calls total)",
            "CV parsed=" + (cv_parsed.get("full_name") or state.get("cv_id", "?")),
            "JD context=" + (gap_analysis.get("jd_context") or "?"),
            "Courses recommended=" + str(len(course_output)),
            "Match calculation: 5-dimension radar chart (Technical Skills, Soft Skills, Tools & Frameworks, Domain Knowledge, Certifications)",
            "Radar chart=" + ("calculated (5 dimensions)" if radar_chart_data else "skipped"),
            "Soft skills=" + ("included in radar chart as Soft Skills dimension" if soft_skills_comparison else "none"),
        ],
    }

    # ── Log final report summary ─────────────────────────────────────────────
    radar_info = ""
    if radar_chart_data:
        radar_info = (
            f"               │ radar_chart        : {radar_chart_data['overall_match']}% "
            f"({len(radar_chart_data.get('priority_gaps', []))} priority gaps)\n"
        )
    
    logger.info(
        f"\n{'═' * 70}\n"
        f"[FINAL REPORT] ┌─── complete report | cv_id={state.get('cv_id')}\n"
        f"               │ overall_match_pct  : {final_report['overall_match_pct']}\n"
        f"               │ strengths          : {len(final_report['strengths'])}\n"
        f"               │ weaknesses         : {len(final_report['weaknesses'])}\n"
        f"               │ skill_gaps         : {len(final_report['skill_gaps'])}\n"
        f"               │ courses            : {len(final_report['course_recommendations'])}\n"
        f"               │ roadmap stages     : {len(final_report.get('career_roadmap', {}).get('stages', []))}\n"
        f"               │ transferable       : {len(final_report['transferable_insights'])}\n"
        f"{radar_info}"
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
