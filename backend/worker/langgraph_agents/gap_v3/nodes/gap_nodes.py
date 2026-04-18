"""
gap_v3 Gap Analysis Nodes (Pipeline 2):
- load_cv_parsed_data_node
- extract_jd_node
- gap_analysis_llm_node
"""

import json
import hashlib
import logging
import uuid as _uuid
from typing import Dict, Any, Optional, List

from ..states import GapAnalysisStateV3, GapAnalysisResult
from ..utils.llm_helpers import llm_json_completion

logger = logging.getLogger("gap_analysis_v3")


def _indent_data(text: str) -> str:
    """Indent each line for log readability."""
    return "\n".join("    " + line for line in text.split("\n"))


# ══════════════════════════════════════════════════════════════════════════════
# NODE 1: Load CV from DB
# ══════════════════════════════════════════════════════════════════════

async def load_cv_parsed_data_node(state: GapAnalysisStateV3) -> GapAnalysisStateV3:
    """
    STEP 1: Load cv_parsed_json from DB.

    Retry logic:
      1. Query DB cv_parsed_json
      2. If missing → trigger CV parsing pipeline as fallback
      3. If fallback fails → mark failed
    """
    db = state["db"]
    cv_id_str = state["cv_id"]

    logger.info(
        f"\n{'─' * 50}\n"
        f"[STEP 1] load_cv_parsed_data_node | cv_id={cv_id_str}"
    )

    # Reset any aborted transaction from previous node
    try:
        db.rollback()
    except Exception:
        pass

    try:
        from shared.models import UserCV

        cv_uuid = _uuid.UUID(cv_id_str)
        cv_record = db.query(UserCV).filter(UserCV.id == cv_uuid).first()

        if not cv_record:
            logger.error(f"[STEP 1] CV not found in DB: cv_id={cv_id_str}")
            return {**state, "error": f"CV not found: {cv_id_str}", "status": "failed"}

        parsed = getattr(cv_record, "cv_parsed_json", None)

        if parsed:
            skills_count = len(parsed.get("skills") or [])
            work_count  = len(parsed.get("work_history") or [])
            edu_count  = len(parsed.get("education") or [])
            logger.info(
                f"[STEP 1] ✓ Cache HIT — cv_parsed_json loaded\n"
                f"  skills={skills_count} | work={work_count} | education={edu_count}\n"
                f"  seniority={parsed.get('seniority')} | "
                f"experience={parsed.get('experience_years_total')} yrs"
            )
            return {**state, "cv_parsed": parsed, "status": "cv_loaded"}

        # Cache miss → trigger CV parsing
        logger.warning(f"[STEP 1] No cv_parsed_json — triggering re-parse fallback")
        parsed = await _run_cv_parsing_fallback(cv_id_str, state["user_id"], db)

        if parsed:
            logger.info(f"[STEP 1] ✓ Fallback CV parsing succeeded")
            return {**state, "cv_parsed": parsed, "status": "cv_loaded"}

        logger.error(f"[STEP 1] ✗ Fallback CV parsing also failed")
        return {**state, "error": "CV not parsed and re-parse fallback failed", "status": "failed"}

    except Exception as e:
        logger.error(f"[STEP 1] ✗ EXCEPTION: {e}", exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
        return {**state, "error": str(e), "status": "failed"}


async def _run_cv_parsing_fallback(cv_id: str, user_id: str, db) -> Optional[dict]:
    """Fallback: gọi CV parsing pipeline nếu cv_parsed_json chưa có."""
    try:
        from ..cv_parsing_graph import run_cv_parsing_pipeline

        result = await run_cv_parsing_pipeline(cv_id=cv_id, user_id=user_id or "", db=db)
        return result.get("cv_parsed")
    except Exception as e:
        logger.error(f"[STEP 1] CV re-parse fallback failed: {e}", exc_info=True)
        return None


# ══════════════════════════════════════════════════════════════════════════════
# NODE 2: Extract JD Requirements (LLM)
# ══════════════════════════════════════════════════════════════════════════════

async def extract_jd_node(state: GapAnalysisStateV3) -> GapAnalysisStateV3:
    """
    [DEPRECATED] Combined into gap_analysis_llm_node.
    Keeping signature to avoid breaking imports, but logic is moved.
    """
    logger.info("[STEP 2] extract_jd_node (DEPRECATED) - skipping...")
    return {**state, "status": "jd_extracted_skipped"}


# [DEPRECATED] _build_jd_extraction_prompt — kept to avoid breaking existing imports.
# Logic merged into _build_merged_gap_prompt and _build_gap_only_prompt.


# ══════════════════════════════════════════════════════════════════════════════
# NODE 3: Holistic Gap Analysis (LLM)
# ══════════════════════════════════════════════════════════════════════════════

async def gap_analysis_llm_node(state: GapAnalysisStateV3) -> GapAnalysisStateV3:
    """
    OPTIMIZED STEP 2+3 (COMBINED): Gap Analysis.

    TWO paths:
      Path A (Pre-populated): jd_requirements / jd_parsed already in state
        → SKIP LLM extraction — go straight to gap analysis with CV
        → from orchestrator.py when job_id is used and DB has extracted_requirements_json

      Path B (Full): No pre-population
        → LLM does JD extraction + gap analysis + top_gaps in ONE call
    """
    cv_id = state.get("cv_id")
    jd_text_raw = state.get("jd_text")
    jd_text = (jd_text_raw or "").strip()
    jd_context = state.get("jd_context") or ""
    job_id = state.get("job_id")
    cv_parsed = state.get("cv_parsed")

    # ── Pre-populated from orchestrator (job_id path) ─────────────────────
    pre_jd_requirements = state.get("jd_requirements")
    pre_jd_parsed = state.get("jd_parsed")

    logger.info(
        f"\n{'─' * 50}\n"
        f"[STEP 3] gap_analysis_llm_node | cv_id={cv_id}\n"
        f"  pre_jd_requirements: {f'{len(pre_jd_requirements)} items' if pre_jd_requirements else 'None'}\n"
        f"  pre_jd_parsed      : {'present' if pre_jd_parsed else 'None'}\n"
        f"  jd_text_raw        : {repr(jd_text_raw)}\n"
        f"  jd_text len        : {len(jd_text)}\n"
        f"  job_id             : {job_id}\n"
        f"  jd_context         : {repr(jd_context)}"
    )

    if not cv_parsed:
        logger.error("[STEP 3] ✗ No cv_parsed in state")
        return {**state, "error": "No CV parsed data", "status": "failed"}

    if not jd_text and not pre_jd_requirements:
        logger.error(
            f"[STEP 3] ✗ No JD — FAILING\n"
            f"  jd_text_raw={repr(jd_text_raw)}\n"
            f"  job_id={job_id}\n"
            f"  jd_context={repr(jd_context)}"
        )
        return {**state, "error": "No JD text", "status": "failed"}

    # Reset any aborted transaction
    try:
        state["db"].rollback()
    except Exception:
        pass

    # ══ PATH A: Pre-populated from job_id — SKIP LLM JD extraction ══════════
    if pre_jd_requirements:
        logger.info(
            f"[STEP 3] PATH A: Using pre-extracted requirements ({len(pre_jd_requirements)} items)\n"
            f"  → SKIPPING LLM extraction\n"
            f"  → Proceeding to gap analysis with CV only"
        )

        cv_text = _format_cv_for_llm(cv_parsed)
        jd_parsed_info = pre_jd_parsed or {}
        job_title = jd_parsed_info.get("job_title") or jd_context

        # Build gap-analysis prompt WITHOUT JD text (JD already extracted)
        prompt = _build_gap_only_prompt(cv_text, pre_jd_requirements, job_title)
        system = (
            "You are a Senior Career Match Analyst. Analyze the candidate's CV "
            "against the EXTRACTED job requirements provided below. "
            "Write assessment and learning paths in Vietnamese. "
            "Keep technical skill names in English."
        )

        result = await llm_json_completion(
            prompt=prompt,
            context=jd_context,
            system_prompt=system,
            temperature=0.1,
            call_name="gap_analysis_from_requirements",
        )

        if result:
            logger.info(
                f"\n[LLM DATA] ┌─── gap_analysis_from_requirements (PATH A)\n"
                f"           └─────────\n"
                f"{_indent_data(json.dumps(result, ensure_ascii=False, indent=2))}\n"
            )

        if not result or "gap_analysis" not in result:
            logger.error("[STEP 3/PATH_A] LLM failed or returned partial result")
            return {**state, "error": "Gap analysis LLM failed", "status": "failed"}

        gap_analysis_raw = result.get("gap_analysis") or {}

        # Compute top_gaps inline
        top_gaps_raw = gap_analysis_raw.get("top_gaps") or []
        top_gaps: List[Any] = list(top_gaps_raw)
        if not top_gaps:
            skill_gaps_fallback = gap_analysis_raw.get("skill_gaps") or []
            severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
            top_gaps = sorted(
                skill_gaps_fallback,
                key=lambda g: (
                    severity_order.get(g.get("severity") or "LOW", 2),
                    -int(bool(g.get("is_critical"))),
                    float(g.get("estimated_months") or 999),
                ),
            )[:3]

        gap_analysis = {
            **gap_analysis_raw,
            "match_breakdown": gap_analysis_raw.get("match_breakdown") or {},
            "strengths": list(gap_analysis_raw.get("strengths") or []),
            "weaknesses": list(gap_analysis_raw.get("weaknesses") or []),
            "skill_gaps": list(gap_analysis_raw.get("skill_gaps") or []),
            "transferable_insights": list(gap_analysis_raw.get("transferable_insights") or []),
            "jd_context": jd_context,
            "top_gaps": top_gaps,
        }

        # Build jd_parsed to match schema
        jd_parsed = {
            "job_title": job_title,
            "requirements": pre_jd_requirements,
        }

        logger.info(f"[STEP 3] PATH A DONE | match={gap_analysis.get('overall_match_pct')}%")

        return {
            **state,
            "jd_parsed": jd_parsed,
            "jd_requirements": pre_jd_requirements,
            "gap_analysis": gap_analysis,
            "status": "gap_analyzed",
        }

    # ══ PATH B: Full JD text — LLM extracts + analyzes in one call ═══════════
    else:
        logger.info(
            f"[STEP 3] PATH B: Using jd_text ({len(jd_text)} chars) — full LLM extraction"
        )

        # Redis cache check
        from shared.redis_client import result_cache
        from ..config import GAP_CACHE_TTL

        jd_hash = hashlib.md5(jd_text.encode()).hexdigest()[:16]
        cache_key = f"gap_v3_combined:{cv_id}:{jd_hash}"

        cached_raw = result_cache.get(cache_key)
        if cached_raw:
            try:
                cached_data = json.loads(cached_raw)
                logger.info(f"[STEP 3] ✓ Redis CACHE HIT | key={cache_key}")
                return {
                    **state,
                    "jd_parsed": cached_data["jd_parsed"],
                    "jd_requirements": cached_data["jd_parsed"].get("requirements") or [],
                    "gap_analysis": cached_data["gap_analysis"],
                    "status": "gap_analyzed",
                }
            except Exception as e:
                logger.warning(f"[STEP 3] Cache parse failed: {e}")

        # ── Format for LLM ────────────────────────────────────────────────
        cv_text = _format_cv_for_llm(cv_parsed)

        logger.info(
            f"[STEP 3/PATH_B] Calling Combined LLM | jd_chars={len(jd_text)} | cv_chars={len(cv_text)}"
        )

        prompt = _build_merged_gap_prompt(cv_text, jd_text)
        system = (
            "You are a Senior Career Match Analyst. Conduct a thorough JD extraction and "
            "holistic gap analysis. Write assessment and learning paths in Vietnamese. "
            "Keep technical skill names in English."
        )

        result = await llm_json_completion(
            prompt=prompt,
            context=jd_context,
            system_prompt=system,
            temperature=0.1,
            call_name="gap_analysis_combined",
        )

        if result:
            logger.info(
                f"\n[LLM DATA] ┌─── gap_analysis_combined (PATH B)\n"
                f"           └─────────\n"
                f"{_indent_data(json.dumps(result, ensure_ascii=False, indent=2))}\n"
            )

        if not result or "gap_analysis" not in result:
            logger.error("[STEP 3/PATH_B] LLM failed or returned partial result")
            return {**state, "error": "Combined LLM analysis failed", "status": "failed"}

        jd_parsed = result.get("jd_parsed") or {}
        gap_analysis_raw = result.get("gap_analysis") or {}

        # Compute top_gaps inline
        top_gaps_raw = gap_analysis_raw.get("top_gaps") or []
        top_gaps: List[Any] = list(top_gaps_raw)
        if not top_gaps:
            skill_gaps_fallback = gap_analysis_raw.get("skill_gaps") or []
            severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
            top_gaps = sorted(
                skill_gaps_fallback,
                key=lambda g: (
                    severity_order.get(g.get("severity") or "LOW", 2),
                    -int(bool(g.get("is_critical"))),
                    float(g.get("estimated_months") or 999),
                ),
            )[:3]

        gap_analysis = {
            **gap_analysis_raw,
            "match_breakdown": gap_analysis_raw.get("match_breakdown") or {},
            "strengths": list(gap_analysis_raw.get("strengths") or []),
            "weaknesses": list(gap_analysis_raw.get("weaknesses") or []),
            "skill_gaps": list(gap_analysis_raw.get("skill_gaps") or []),
            "transferable_insights": list(gap_analysis_raw.get("transferable_insights") or []),
            "jd_context": jd_context,
            "top_gaps": top_gaps,
        }

        # Cache result
        try:
            combined_result = {
                "jd_parsed": jd_parsed,
                "gap_analysis": gap_analysis,
            }
            result_cache.setex(cache_key, GAP_CACHE_TTL, json.dumps(combined_result))
            logger.info(f"[STEP 3/PATH_B] ✓ Cached combined result | key={cache_key}")
        except Exception as e:
            logger.warning(f"[STEP 3/PATH_B] Caching failed: {e}")

        logger.info(f"[STEP 3/PATH_B] DONE | match={gap_analysis.get('overall_match_pct')}%")

        return {
            **state,
            "jd_parsed": jd_parsed,
            "jd_requirements": jd_parsed.get("requirements") or [],
            "gap_analysis": gap_analysis,
            "status": "gap_analyzed",
        }


def _format_cv_for_llm(cv_parsed: dict) -> str:
    """Format structured CV parsed data as plain text for LLM."""
    skills       = cv_parsed.get("skills") or []
    work_history = cv_parsed.get("work_history") or []
    education   = cv_parsed.get("education") or []
    certs       = cv_parsed.get("certifications") or []

    # Skills
    skill_lines = []
    for s in skills:
        nm   = s.get("name") or "?"
        lvl  = s.get("level") or "Unknown"
        yrs  = float(s.get("years_exp") or 0)
        skill_lines.append(f"  - {nm} | {lvl} | {yrs:.1f} yrs")
    skills_text = "\n".join(skill_lines) or "  (no skills)"

    # Work history
    work_lines = []
    for w in work_history:
        pos = w.get("position") or "?"
        co  = w.get("company") or "?"
        dur = float(w.get("duration_years") or 0)
        desc = (w.get("description") or "")[:200]
        su  = ", ".join((w.get("skills_used") or [])[:5])
        work_lines.append(
            f"  - [{dur:.1f} yrs] {pos} @ {co}\n    {desc}\n    Skills: {su}"
        )
    work_text = "\n".join(work_lines) or "  (no work history)"

    # Education
    edu_lines = []
    for e in education:
        deg = e.get("degree") or "?"
        inst = e.get("institution") or "?"
        yr   = e.get("year") or "?"
        edu_lines.append(f"  - {deg} @ {inst} ({yr})")
    edu_text = "\n".join(edu_lines) or "  (no education)"

    seniority  = cv_parsed.get("seniority") or "Unknown"
    exp_total = float(cv_parsed.get("experience_years_total") or 0)
    summary   = cv_parsed.get("summary") or ""

    return (
        f"Seniority: {seniority} | Experience: {exp_total:.0f} yrs\n"
        f"Summary: {summary}\n\n"
        f"SKILLS:\n{skills_text}\n\n"
        f"WORK EXPERIENCE:\n{work_text}\n\n"
        f"EDUCATION:\n{edu_text}"
    )


def _format_jd_for_llm(requirements: list) -> str:
    """Format JD requirements as plain text for LLM."""
    if not requirements:
        return "  (no requirements)"

    lines = []
    for req in requirements:
        nm   = req.get("skill") or req.get("group_name") or "?"
        lvl  = req.get("target_level") or "?"
        yrs  = float(req.get("years_required") or 0)
        mand = "REQUIRED" if req.get("is_mandatory") else "OPTIONAL"
        wgt  = req.get("importance_weight") or 5

        lines.append(
            f"  [{mand}] {nm} | level={lvl} | yrs={yrs} | weight={wgt}"
        )

    return "\n".join(lines)


def _build_merged_gap_prompt(cv_text: str, jd_text: str) -> str:
    """
    Optimized v3: Merges JD extraction + Gap analysis + Gap prioritization into ONE LLM call.

    Previous version: separate calls for gap_analysis and gap_prioritization.
    Current version : single call returns all, including top_gaps.
    """
    return (
        "You are a Senior Career Match Analyst. Your task is to perform a deep analysis of a candidate's CV against a Job Description (JD).\n\n"
        "## JD RAW TEXT:\n"
        + jd_text +
        "\n\n## CANDIDATE CV (PARSED):\n"
        + cv_text +
        "\n\n"
        "## MISSION:\n"
        "1. EXTRACT: Analyze the raw JD text to identify the Job Title and structured Technical Requirements (skills, levels, years).\n"
        "2. ANALYZE: Compare the candidate's CV against the extracted requirements and the overall job context.\n"
        "3. EVALUATE: Provide a holistic match score, breakdown of skill matches, strengths, weaknesses, and a detailed list of gaps.\n"
        "4. PRIORITIZE: From the skill_gaps list, select TOP 3 gaps that should be addressed FIRST.\n\n"
        "## PRIORITIZATION RULES (for top_gaps):\n"
        "  - HIGH severity + is_critical=True → highest priority\n"
        "  - transferable (bridge_from not null) → fast ROI, prefer these\n"
        "  - estimated_months <= 3 → quick wins, elevate priority\n"
        "  - LOW severity + not is_critical → skip (do NOT include in top_gaps)\n"
        "  - If fewer than 3 gaps exist, return only what is available.\n\n"
        "## OUTPUT JSON SCHEMA:\n"
        "{\n"
        '  "jd_parsed": {\n'
        '    "job_title": "...",\n'
        '    "requirements": [\n'
        '      {\n'
        '        "skill": "SkillName (English)",\n'
        '        "target_level": "Junior | Mid-level | Senior | Expert",\n'
        '        "years_required": number,\n'
        '        "is_mandatory": boolean,\n'
        '        "importance_weight": score 1-10\n'
        '      }\n'
        '    ]\n'
        '  },\n'
        '  "gap_analysis": {\n'
        '    "overall_match_pct": score 0-100,\n'
        '    "overall_assessment": "summary in Vietnamese",\n'
        '    "match_breakdown": {\n'
        '      "Technical Skills": 0-100,\n'
        '      "Experience": 0-100,\n'
        '      "Soft Skills": 0-100,\n'
        '      "Education": 0-100,\n'
        '      "Domain Knowledge": 0-100\n'
        '    },\n'
        '    "strengths": ["..."],\n'
        '    "weaknesses": ["..."],\n'
        '    "skill_gaps": [\n'
        '       { "skill": "English Name", "required_level": "Mid-level", "severity": "HIGH | MEDIUM | LOW", "is_critical": boolean, "estimated_months": number, "learning_path": "Vietnamese description" }\n'
        '    ],\n'
        '    "transferable_insights": ["..."],\n'
        '    "top_gaps": [\n'
        '       { "skill": "English Name", "required_level": "Mid-level", "severity": "HIGH | MEDIUM | LOW", "is_critical": boolean, "estimated_months": number, "learning_path": "Vietnamese description" }\n'
        '    ]\n'
        '  }\n'
        "}\n\n"
        "Return ONLY valid JSON."
    )


def _build_gap_only_prompt(
    cv_text: str,
    pre_jd_requirements: list,
    job_title: str,
) -> str:
    """
    OPTIMIZED PATH A: Gap analysis WITHOUT JD raw text.

    Used when job_id is provided and extracted_requirements_json already exists in DB.
    The JD text has already been processed — just analyze CV against the structured requirements.
    """
    # Format requirements as structured list
    req_lines = []
    for i, req in enumerate(pre_jd_requirements):
        if req.get("type") == "group":
            group_name = req.get("group_name") or "Skill Group"
            strategy = req.get("group_strategy") or "exclusive"
            sub_skills = req.get("skills") or []
            skills_str = ", ".join(
                f"{s.get('skill')} ({s.get('target_level')}, {s.get('years_required', 0)} yrs)"
                for s in sub_skills
            )
            req_lines.append(
                f"  [{i + 1}] GROUP: {group_name} [{strategy.upper()}]\n"
                f"      Skills: {skills_str}"
            )
        else:
            skill_name = req.get("skill") or req.get("name") or "?"
            target_level = req.get("target_level") or "Junior"
            years = req.get("years_required", 0)
            mandatory = "REQUIRED" if req.get("is_mandatory") else "OPTIONAL"
            weight = req.get("importance_weight") or 5
            req_lines.append(
                f"  [{i + 1}] [{mandatory}] {skill_name} | level={target_level} | "
                f"yrs={years} | weight={weight}"
            )
    requirements_text = "\n".join(req_lines) if req_lines else "  (no requirements)"

    return (
        "You are a Senior Career Match Analyst. Your task is to analyze a candidate's CV "
        "against the EXTRACTED job requirements provided below.\n\n"
        "## JOB TITLE: " + job_title + "\n\n"
        "## EXTRACTED JOB REQUIREMENTS:\n" + requirements_text + "\n\n"
        "## CANDIDATE CV (PARSED):\n" + cv_text + "\n\n"
        "## MISSION:\n"
        "1. ANALYZE: Compare the candidate's CV against the extracted requirements.\n"
        "2. EVALUATE: Provide a holistic match score, breakdown of skill matches, "
        "strengths, weaknesses, and a detailed list of gaps.\n"
        "3. PRIORITIZE: From the skill_gaps list, select TOP 3 gaps that should be "
        "addressed FIRST.\n\n"
        "## PRIORITIZATION RULES (for top_gaps):\n"
        "  - HIGH severity + is_critical=True → highest priority\n"
        "  - transferable (bridge_from not null) → fast ROI, prefer these\n"
        "  - estimated_months <= 3 → quick wins, elevate priority\n"
        "  - LOW severity + not is_critical → skip (do NOT include in top_gaps)\n\n"
        "## OUTPUT JSON SCHEMA:\n"
        "{\n"
        '  "gap_analysis": {\n'
        '    "overall_match_pct": score 0-100,\n'
        '    "overall_assessment": "summary in Vietnamese",\n'
        '    "match_breakdown": {\n'
        '      "Technical Skills": 0-100,\n'
        '      "Experience": 0-100,\n'
        '      "Soft Skills": 0-100,\n'
        '      "Education": 0-100,\n'
        '      "Domain Knowledge": 0-100\n'
        '    },\n'
        '    "strengths": ["..."],\n'
        '    "weaknesses": ["..."],\n'
        '    "skill_gaps": [\n'
        '       { "skill": "English Name", "required_level": "Mid-level", "severity": "HIGH | MEDIUM | LOW", "is_critical": boolean, "estimated_months": number, "learning_path": "Vietnamese description" }\n'
        '    ],\n'
        '    "transferable_insights": ["..."],\n'
        '    "top_gaps": [\n'
        '       { "skill": "English Name", "required_level": "Mid-level", "severity": "HIGH | MEDIUM | LOW", "is_critical": boolean, "estimated_months": number, "learning_path": "Vietnamese description" }\n'
        '    ]\n'
        '  }\n'
        "}\n\n"
        "Return ONLY valid JSON."
    )
