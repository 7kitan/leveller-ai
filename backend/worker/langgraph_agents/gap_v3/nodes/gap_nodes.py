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
from datetime import datetime as _datetime
from typing import Dict, Any, Optional, List

from ..states import GapAnalysisStateV3, GapAnalysisResult
from ..utils.llm_helpers import llm_json_completion


logger = logging.getLogger("gap_analysis_v3")


def _compute_cv_hash(cv_parsed: dict) -> str:
    """Compute a stable hash of CV skills and summary for cache invalidation."""
    skills = cv_parsed.get("skills") or []
    summary = cv_parsed.get("summary") or ""
    exp_total = cv_parsed.get("experience_years_total") or 0
    
    # Sort skills by name for stability
    skill_data = sorted([
        f"{s.get('name')}:{s.get('level')}:{s.get('years_exp') or s.get('experience_years')}" 
        for s in skills
    ])
    
    cv_fingerprint = f"summary:{summary}|exp:{exp_total}|skills:{'|'.join(skill_data)}"
    return hashlib.md5(cv_fingerprint.encode()).hexdigest()[:16]



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
        # Use updated_at as it catches manual edits too
        cv_updated_at = getattr(cv_record, "updated_at", None) or getattr(cv_record, "cv_parsed_at", None)
        cv_timestamp = cv_updated_at.isoformat() if cv_updated_at else "none"

        if parsed:
            # Sync direct columns from UserCV (Source of truth for manual edits)
            # Remove full_name as per user request to keep JSON clean for LLM
            parsed.pop("full_name", None)
            parsed["summary"] = cv_record.summary or parsed.get("summary")
            if cv_record.experience_years_total is not None:
                parsed["experience_years_total"] = cv_record.experience_years_total

            # Refresh skills from DB to ensure we use the latest edits (ignoring the potentially stale JSON blob)
            from shared.models import UserSkillProfile, Skill
            db_skills = (
                db.query(UserSkillProfile, Skill.name)
                .join(Skill, UserSkillProfile.skill_id == Skill.id)
                .filter(UserSkillProfile.cv_id == cv_record.id)
                .all()
            )
            if db_skills:
                updated_skills = []
                for sp, name in db_skills:
                    updated_skills.append({
                        "name": name,
                        "level": sp.level,
                        "years_exp": sp.years_exp
                    })
                parsed["skills"] = updated_skills
                logger.info(f"[STEP 1] Refreshed {len(updated_skills)} skills from UserSkillProfile table.")
            
            skills_count = len(parsed.get("skills") or [])
            work_count  = len(parsed.get("work_history") or [])
            edu_count  = len(parsed.get("education") or [])
            logger.info(
                f"[STEP 1] ✓ CV data loaded & synced\n"
                f"  name={parsed.get('full_name')} | skills={skills_count}\n"
                f"  experience={parsed.get('experience_years_total')} yrs"
            )
            cv_timestamp = int(cv_record.updated_at.timestamp()) if cv_record.updated_at else 0
            return {
                **state, 
                "cv_parsed": parsed, 
                "cv_timestamp": cv_timestamp,
                "status": "cv_loaded"
            }

        # Cache miss → trigger CV parsing
        logger.warning(f"[STEP 1] No cv_parsed_json — triggering re-parse fallback")
        fallback_result = await _run_cv_parsing_fallback(cv_id_str, state["user_id"], db)

        if fallback_result:
            logger.info(f"[STEP 1] ✓ Fallback CV parsing succeeded")
            return {
                **state, 
                "cv_parsed": fallback_result, 
                "cv_timestamp": int(__import__("time").time()),
                "status": "cv_loaded"
            }

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

        # Redis cache check (Path A)
        from shared.redis_client import result_cache
        from ..config import GAP_CACHE_TTL
        
        cv_hash = _compute_cv_hash(cv_parsed)
        # Hash requirements to detect changes in extracted data
        jd_req_hash = hashlib.md5(json.dumps(pre_jd_requirements).encode()).hexdigest()[:16]
        
        # BUG-006 FIX: Include JD text hash to prevent cache collision when job_id is None
        # Different JD texts with no job_id should have different cache keys
        jd_text_for_hash = state.get("jd_text", "")
        jd_text_hash = hashlib.md5(jd_text_for_hash.encode()).hexdigest()[:8] if jd_text_for_hash else "notxt"
        
        # Path A cache key: includes job_id, JD text hash, content hashes, and CV timestamp
        cv_ts = state.get("cv_timestamp", 0)
        cache_key = f"gap_v3_path_a:{cv_id}:{job_id or 'nojob'}:{jd_text_hash}:{jd_req_hash}:cvh_{cv_hash}:ts_{cv_ts}"
        
        force_recompute = state.get("force_recompute", False)
        cached_raw = result_cache.get(cache_key) if not force_recompute else None
        
        if cached_raw:
            try:
                cached_data = json.loads(cached_raw)
                logger.info(f"[STEP 3] ✓ Redis CACHE HIT (Path A) | key={cache_key}")
                
                # BUG-022 FIX: Log cached token usage for analytics
                if "token_usage" in cached_data:
                    logger.info(f"[STEP 3] Cache hit - original token usage: {cached_data['token_usage']}")
                
                return {
                    **state,
                    "gap_analysis": cached_data["gap_analysis"],
                    "status": "gap_analyzed",
                    "is_cached": True,
                    "cached_token_usage": cached_data.get("token_usage"),  # BUG-022 FIX: Include in response
                }
            except Exception as e:
                logger.warning(f"[STEP 3/Path_A] Cache parse failed: {e}")

        # Build gap-analysis prompt WITHOUT JD text (JD already extracted)
        # Remove PII/Unnecessary fields before sending to LLM
        cv_clean = cv_parsed.copy()
        cv_clean.pop("full_name", None)
        cv_clean.pop("raw_text_masked", None)
        
        cv_json_str = json.dumps(cv_clean, ensure_ascii=False, indent=2)
        reqs_json_str = json.dumps(pre_jd_requirements, ensure_ascii=False, indent=2)
        target_lang = "English" if state.get("lang") == "en" else "Vietnamese"
        
        prompt = _build_gap_only_prompt(cv_json_str, reqs_json_str, job_title, language=target_lang)
        system = (
            "You are a Senior Career Match Analyst. Analyze the candidate's CV "
            "against the structured job requirements JSON provided. "
            "Perform step-by-step reasoning (Chain of Thought) before outputting the final JSON. "
            "Write assessment and learning paths in " + target_lang + ". "
            "Keep technical skill names in English."
        )

        user_id = state.get("user_id")
        result = await llm_json_completion(
            prompt=prompt,
            context=jd_context,
            system_prompt=system,
            temperature=0.1,
            call_name="gap_analysis_from_requirements",
            user_id=user_id
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

        # BUG-022 FIX: Cache result (Path A) with token usage
        try:
            combined_result = {
                "gap_analysis": gap_analysis,
                "token_usage": result.get("token_usage") if result else None,  # BUG-022 FIX: Store token usage
            }
            result_cache.setex(cache_key, GAP_CACHE_TTL, json.dumps(combined_result))
            logger.info(f"[STEP 3/PATH_A] ✓ Cached analysis | key={cache_key}")
        except Exception as e:
            logger.warning(f"[STEP 3/PATH_A] Caching failed: {e}")

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

        cv_hash = _compute_cv_hash(cv_parsed)
        jd_hash = hashlib.md5(jd_text.encode()).hexdigest()[:16]
        
        # BUG-006 FIX: Path B already includes jd_hash which prevents collision
        # Path B cache key: includes job_id, JD text hash, content hashes, and CV timestamp
        cv_ts = state.get("cv_timestamp", 0)
        cache_key = f"gap_v3_combined:{cv_id}:{job_id or 'nojob'}:{jd_hash}:cvh_{cv_hash}:ts_{cv_ts}"

        force_recompute = state.get("force_recompute", False)
        cached_raw = result_cache.get(cache_key) if not force_recompute else None
        
        if cached_raw:
            try:
                cached_data = json.loads(cached_raw)
                logger.info(f"[STEP 3] ✓ Redis CACHE HIT (Path B) | key={cache_key}")
                
                # BUG-022 FIX: Log cached token usage for analytics
                if "token_usage" in cached_data:
                    logger.info(f"[STEP 3] Cache hit - original token usage: {cached_data['token_usage']}")
                
                return {
                    **state,
                    "jd_parsed": cached_data["jd_parsed"],
                    "jd_requirements": cached_data["jd_parsed"].get("requirements") or [],
                    "gap_analysis": cached_data["gap_analysis"],
                    "status": "gap_analyzed",
                    "is_cached": True,
                    "cached_token_usage": cached_data.get("token_usage"),  # BUG-022 FIX: Include in response
                }
            except Exception as e:
                logger.warning(f"[STEP 3] Cache parse failed: {e}")

        # ── Format for LLM ────────────────────────────────────────────────
        # Remove PII/Unnecessary fields before sending to LLM
        cv_clean = cv_parsed.copy()
        cv_clean.pop("full_name", None)
        cv_clean.pop("raw_text_masked", None)
        
        cv_json_str = json.dumps(cv_clean, ensure_ascii=False, indent=2)
        target_lang = "English" if state.get("lang") == "en" else "Vietnamese"

        logger.info(
            f"[STEP 3/PATH_B] Calling Combined LLM | jd_chars={len(jd_text)} | cv_json_chars={len(cv_json_str)} | lang={target_lang}"
        )

        prompt = _build_merged_gap_prompt(cv_json_str, jd_text, language=target_lang)
        system = (
            "You are a Senior Career Match Analyst. Conduct a thorough JD extraction and "
            "holistic gap analysis using Chain of Thought reasoning. "
            "Write assessment and learning paths in " + target_lang + ". "
            "Keep technical skill names in English."
        )

        user_id = state.get("user_id")
        result = await llm_json_completion(
            prompt=prompt,
            context=jd_context,
            system_prompt=system,
            temperature=0.1,
            call_name="gap_analysis_combined",
            user_id=user_id
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

        # BUG-022 FIX: Cache result to Redis with token usage
        try:
            combined_result = {
                "jd_parsed": jd_parsed,
                "gap_analysis": gap_analysis,
                "token_usage": result.get("token_usage") if result else None,  # BUG-022 FIX: Store token usage
            }
            result_cache.setex(cache_key, GAP_CACHE_TTL, json.dumps(combined_result))
            logger.info(f"[STEP 3/PATH_B] ✓ Cached combined result to Redis | key={cache_key}")
        except Exception as e:
            logger.warning(f"[STEP 3/PATH_B] Redis caching failed: {e}")

        # BUG-008 FIX: Persistent DB update - Save extraction back to Job record
        # so next time it goes through Path A (pre-populated path)
        if job_id and jd_parsed and "requirements" in jd_parsed:
            try:
                from shared.models import Job
                job_record = db.query(Job).filter(Job.id == job_id).first()
                if job_record:
                    job_record.extracted_requirements_json = jd_parsed.get("requirements")
                    db.commit()
                    logger.info(f"[STEP 3/PATH_B] ✓ Persisted JD extraction to Job record {job_id}")
            except Exception as e:
                logger.warning(f"[STEP 3/PATH_B] Failed to persist JD extraction: {e}")
                db.rollback()

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
        yrs  = float(s.get("years_exp") or s.get("experience_years") or 0)
        skill_lines.append(f"  - {nm} | {lvl} | {yrs:.1f} yrs")
    skills_text = "\n".join(skill_lines) or "  (no skills)"

    # Work history
    work_lines = []
    for w in work_history:
        pos = w.get("position") or "?"
        co  = w.get("company") or "?"
        dur = float(w.get("duration_years") or 0)
        desc = (w.get("description") or "")[:200]
        work_lines.append(
            f"  - [{dur:.1f} yrs] {pos} @ {co}\n    {desc}"
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


def _build_merged_gap_prompt(cv_text: str, jd_text: str, language: str = "Vietnamese") -> str:
    """
    Optimized v3: Merges JD extraction + Gap analysis + Gap prioritization into ONE LLM call.

    Previous version: separate calls for gap_analysis and gap_prioritization.
    Current version : single call returns all, including top_gaps.
    """
    return (
        "You are a Senior Career Match Analyst. Your task is to perform a deep analysis of a candidate's CV against a Job Description (JD).\n\n"
        "## JD RAW TEXT:\n"
        + jd_text +
        "\n\n## CANDIDATE CV JSON:\n"
        + cv_text +
        "\n\n"
        "## MISSION:\n"
        "1. EXTRACT: Analyze JD to identify requirements.\n"
        "2. CHAIN OF THOUGHT (CoT):\n"
        "   - Step 1: List all extracted JD requirements.\n"
        "   - Step 2: For each requirement, search the 'skills', 'summary', and 'work_history' in the CV JSON for evidence.\n"
        "   - Step 3: Compare candidate level/years vs requirement level/years.\n"
        "   - Step 4: Finalize MATCH vs GAP decision based on STRICT evidence.\n"
        "3. ANALYZE & MATCH (STRICT RULES):\n"
        "   - NO HALLUCINATIONS: If evidence exists in CV, it is a MATCH. Do NOT assume skills not explicitly mentioned.\n"
        "   - NO LEVEL UPSCALING: If JD asks for Junior, Junior is a MATCH.\n"
        "   - STANDARDIZED LEVELS: Use only 'Beginner', 'Intermediate', or 'Advanced' for 'required_level'. If the JD specifies years (e.g. '5 years'), translate it to the appropriate level (e.g. 'Advanced').\n"
        "4. RESPONSE STRUCTURE (for " + language + "):\n"
        "   - overall_assessment: Must be structured as follows:\n"
        "     1. Tóm tắt mức độ tương thích (High/Medium/Low).\n"
        "     2. Lộ trình hành động: Liệt kê top 3 kỹ năng cần học ngay.\n"
        "     3. Lời khuyên tối ưu CV.\n"
        "5. OUTPUT: Provide the result in the specified JSON format.\n\n"
        "## OUTPUT JSON SCHEMA:\n"
        "{\n"
        '  "thought_process": "Your step-by-step analytical reasoning in English",\n'
        '  "jd_parsed": {\n'
        '    "job_title": "...",\n'
        '    "requirements": [\n'
        '      { "skill": "...", "target_level": "...", "years_required": number, "is_mandatory": boolean, "importance_weight": number }\n'
        '    ]\n'
        '  },\n'
        '  "gap_analysis": {\n'
        '    "overall_match_pct": score 0-100,\n'
        '    "overall_assessment": "summary in Vietnamese",\n'
        '    "match_breakdown": { "Technical Skills": 0-100, "Soft Skills": 0-100, "Tools & Frameworks": 0-100, "Domain Knowledge": 0-100, "Certifications": 0-100 },\n'
        '    "strengths": ["..."],\n'
        '    "weaknesses": ["..."],\n'
        '    "skill_gaps": [\n'
        '       { "skill": "...", "category": "Technical Skills|Soft Skills|Tools & Frameworks|Domain Knowledge|Certifications", "required_level": "Beginner|Intermediate|Advanced", "severity": "...", "is_critical": boolean, "estimated_months": number, "reasoning": "Vietnamese", "learning_path": "Vietnamese" }\n'
        '    ],\n'
        '    "transferable_insights": ["..."],\n'
        '    "top_gaps": [\n'
        '       { "skill": "...", "category": "Technical Skills|Soft Skills|Tools & Frameworks|Domain Knowledge|Certifications", "required_level": "Beginner|Intermediate|Advanced", "severity": "...", "is_critical": boolean, "estimated_months": number, "learning_path": "Vietnamese" }\n'
        '    ]\n'
        '  }\n'
        "}\n\n"
        "Return ONLY valid JSON."
    )


def _build_gap_only_prompt(
    cv_json_str: str,
    requirements_json: str,
    job_title: str,
    language: str = "Vietnamese",
) -> str:
    """
    OPTIMIZED PATH A: Gap analysis WITHOUT JD raw text.
    Uses JSON inputs for both CV and JD requirements to enable CoT reasoning.
    """
    return (
        "You are a Senior Career Match Analyst. Your task is to analyze a candidate's CV against structured Job Requirements JSON.\n\n"
        "## JOB TITLE: " + job_title + "\n\n"
        "## JOB REQUIREMENTS JSON:\n" + requirements_json + "\n\n"
        "## CANDIDATE CV JSON:\n" + cv_json_str + "\n\n"
        "## MISSION:\n"
        "1. CHAIN OF THOUGHT (CoT):\n"
        "   - Step 1: List all JD requirements from the JSON.\n"
        "   - Step 2: For each requirement, perform an exhaustive search in the CV JSON (check 'skills', 'summary', 'work_history').\n"
        "   - Step 3: Compare candidate's years/level against requirement. Match synonyms (e.g. 'Cisco' matches 'Cisco Router').\n"
        "   - Step 4: Make a strict MATCH/GAP decision. If skill is in CV JSON, it is NOT a gap.\n"
        "2. ANALYZE & MATCH (STRICT RULES):\n"
        "   - NO HALLUCINATIONS: Do not invent gaps. If CV lists the skill, it's a match. Do NOT assume skills not explicitly mentioned.\n"
        "   - NO LEVEL UPSCALING: Match Junior to Junior. Do not demand higher levels.\n"
        "   - STANDARDIZED LEVELS: Use only 'Beginner', 'Intermediate', or 'Advanced' for 'required_level'. If the JD specifies years (e.g. '5 years'), translate it to the appropriate level (e.g. 'Advanced').\n"
        "3. RESPONSE STRUCTURE (for " + language + "):\n"
        "   - overall_assessment: Must be structured as follows:\n"
        "     1. Tóm tắt mức độ tương thích (High/Medium/Low).\n"
        "     2. Lộ trình hành động: Liệt kê top 3 kỹ năng cần học ngay.\n"
        "     3. Lời khuyên tối ưu CV.\n"
        "4. OUTPUT: Provide the result in the specified JSON format.\n\n"
        "## OUTPUT JSON SCHEMA:\n"
        "{\n"
        '  "thought_process": "Your step-by-step analytical reasoning in English",\n'
        '  "gap_analysis": {\n'
        '    "overall_match_pct": score 0-100,\n'
        '    "overall_assessment": "summary in Vietnamese",\n'
        '    "match_breakdown": { "Technical Skills": 0-100, "Soft Skills": 0-100, "Tools & Frameworks": 0-100, "Domain Knowledge": 0-100, "Certifications": 0-100 },\n'
        '    "strengths": ["..."],\n'
        '    "weaknesses": ["..."],\n'
        '    "skill_gaps": [\n'
        '       { "skill": "...", "category": "Technical Skills|Soft Skills|Tools & Frameworks|Domain Knowledge|Certifications", "required_level": "Beginner|Intermediate|Advanced", "severity": "...", "is_critical": boolean, "estimated_months": number, "reasoning": "Vietnamese", "learning_path": "Vietnamese" }\n'
        '    ],\n'
        '    "transferable_insights": ["..."],\n'
        '    "top_gaps": [\n'
        '       { "skill": "...", "category": "Technical Skills|Soft Skills|Tools & Frameworks|Domain Knowledge|Certifications", "required_level": "Beginner|Intermediate|Advanced", "severity": "...", "is_critical": boolean, "estimated_months": number, "learning_path": "Vietnamese" }\n'
        '    ]\n'
        '  }\n'
        "}\n\n"
        "Return ONLY valid JSON."
    )

