"""
gap_v3 Course Recommendation Agent — OPTIMIZED v3.

Previous version: 5 LLM calls total
  1. gap_analysis_llm_node        (JD extract + gap analysis)
  2. _llm_prioritize_gaps        (select TOP 3 gaps)          ← REMOVED (merged into #1)
  3. _llm_select_courses × N      (select TOP 2 per gap)      ← MERGED into single #3
  4. roadmap_synthesis_node      (roadmap synthesis)           ← MERGED into single #3

Current version: 2 LLM calls total
  1. gap_analysis_llm_node        (JD extract + gap analysis + top_gaps)
  2. _llm_select_courses_unified (courses + roadmap, ALL gaps in 1 call)
"""

import json as _json
import logging
from typing import Dict, Any, List

from ..states import GapAnalysisStateV3
from ..utils.llm_helpers import llm_json_completion
from ..config import get_vector_sim_threshold
from shared.config_utils import config_manager
from shared.youtube_service import youtube_service

logger = logging.getLogger("course_agent_v3")


def _indent_data(text: str) -> str:
    """Indent each line for log readability."""
    return "\n".join("    " + line for line in text.split("\n"))


# ══════════════════════════════════════════════════════════════════════════════
# NODE 4: Course Recommendation + Roadmap (UNIFIED — was 5 LLM calls → 1)
# ══════════════════════════════════════════════════════════════════════════════


async def course_recommendation_llm_node(
    state: GapAnalysisStateV3,
) -> GapAnalysisStateV3:
    """
    OPTIMIZED v3: Single node handles all course selection + roadmap in ONE LLM call.

    Previous flow (5 LLM calls):
      gap_analysis_llm_node → _llm_prioritize_gaps → _llm_select_courses × 3 → roadmap_synthesis_node

    New flow (2 LLM calls total):
      gap_analysis_llm_node  (gap analysis + top_gaps inline)   ← already done
      course_recommendation_llm_node (unified: courses + roadmap) ← THIS node

    Data flow:
      1. Get top_gaps from gap_analysis state  ← already prioritized, no LLM needed
      2. pgvector search per gap (vector only, no LLM)
      3. Single LLM call: select best courses for ALL gaps + build roadmap together
    """
    gap_analysis = state.get("gap_analysis")
    logger.info(
        "\n" + "=" * 50 + "\n"
        "[STEP 4] course_recommendation_llm_node (OPTIMIZED v3) | cv_id="
        + state.get("cv_id", "?")
    )

    if not gap_analysis:
        logger.warning("[STEP 4] No gap_analysis — skipping course recommendation")
        return {**state, "course_recommendations": [], "career_roadmap": {}, "status": "courses_done"}

    # ── top_gaps already computed inline in gap_analysis_llm_node (no extra LLM) ──
    top_gaps = gap_analysis.get("top_gaps") or []
    all_skill_gaps = gap_analysis.get("skill_gaps") or []
    jd_context = gap_analysis.get("jd_context") or ""

    if not top_gaps and not all_skill_gaps:
        logger.warning("[STEP 4] No gaps found — skipping course recommendation")
        return {**state, "course_recommendations": [], "career_roadmap": {}, "status": "courses_done"}

    # Use top_gaps if available, fallback to top-3 of all_skill_gaps
    gaps_to_process = top_gaps if top_gaps else all_skill_gaps[:3]

    logger.info(
        f"[STEP 4] ✓ Using top_gaps (from gap_analysis state — no extra LLM)\n"
        f"  gaps: {', '.join(str(g.get('skill', '?')) for g in gaps_to_process)}"
    )

    # Reset aborted transaction
    try:
        state["db"].rollback()
    except Exception:
        pass

    db = state["db"]
    all_recommendations: List[Dict] = []

    import asyncio

    # ── STEP 1: Vector search per gap (Parallel) ───────────────────
    logger.info(f"[STEP 4] Searching courses for {len(gaps_to_process)} gaps in parallel...")
    
    async def search_gap_courses(gap):
        gap_skill = gap.get("skill") or "?"
        required_level = gap.get("required_level") or "Mid-level"
        learning_path = gap.get("learning_path") or ""
        estimated_months = gap.get("estimated_months") or 3
        
        candidates = await _vector_search_courses(
            skill_name=gap_skill,
            target_level=required_level,
            db=db,
            limit=12,
        )
        
        sim_threshold = config_manager.get_setting("gap_vector_sim_threshold", default=0.35, cast=float)
        logger.info(f"[STEP 4] {len(candidates)} candidates for '{gap_skill}' | sim_threshold={sim_threshold}")
        
        # Attach gap metadata
        for c in candidates:
            c["_gap_skill"] = gap_skill
            c["_gap_severity"] = gap.get("severity") or "MEDIUM"
            c["_gap_learning_path"] = learning_path
            c["_gap_estimated_months"] = estimated_months
            c["_is_critical"] = bool(gap.get("is_critical"))
        return candidates

    # Run vector searches in parallel
    course_candidate_lists = await asyncio.gather(*[search_gap_courses(g) for g in gaps_to_process])
    for cand_list in course_candidate_lists:
        all_recommendations.extend(cand_list)

    # ── STEP 1.5: YouTube Search (Free Resources - Parallel) ───────────
    youtube_videos = []
    current_lang = state.get("lang", "vi")
    
    async def search_yt(gap):
        skill_name = gap.get("skill") or "?"
        level_name = gap.get("required_level") or "Mid-level"
        v_results = await youtube_service.search_and_cache(
            query=f"{skill_name} {level_name}",
            db=db,
            limit=3,
            lang=current_lang
        )
        for v in v_results:
            v["gap_skill"] = skill_name
        return v_results

    # Run YouTube searches in parallel for top 3 gaps
    yt_results = await asyncio.gather(*[search_yt(g) for g in gaps_to_process[:3]])
    for v_list in yt_results:
        youtube_videos.extend(v_list)

    if not all_recommendations:
        logger.warning("[STEP 4] No courses found for any gap. Providing YouTube only.")
        return {
            **state, 
            "course_recommendations": [], 
            "youtube_videos": youtube_videos,
            "career_roadmap": {}, 
            "status": "courses_done"
        }

    # ── STEP 2 (FINAL LLM CALL): Unified course selection + roadmap ─────────
    unified_result = await _llm_select_courses_and_roadmap_unified(
        all_candidates=all_recommendations,
        youtube_candidates=youtube_videos,
        gaps=gaps_to_process,
        jd_context=jd_context,
        user_id=state.get("user_id")
    )

    selected_courses = unified_result.get("selected_courses", [])
    career_roadmap = unified_result.get("career_roadmap", {})

    # ── Attach gap metadata to selected courses ──────────────────────────────
    # Map both standard courses (by course_id) and youtube videos (by video_id)
    course_id_map = {c.get("course_id"): c for c in all_recommendations}
    youtube_id_map = {v.get("video_id"): v for v in youtube_videos}
    
    final_courses = []
    selected_youtube = []

    for item in selected_courses:
        cid = item.get("course_id")
        vid = item.get("video_id")
        reason = item.get("selection_reason") or ""
        
        if cid:
            c = course_id_map.get(cid)
            if c:
                c_copy = c.copy()
                c_copy["gap_skill"] = c_copy.pop("_gap_skill", item.get("gap_skills", [""])[0] if item.get("gap_skills") else "")
                c_copy["gap_severity"] = c_copy.pop("_gap_severity", "MEDIUM")
                c_copy["gap_learning_path"] = c_copy.pop("_gap_learning_path", "")
                c_copy["gap_estimated_months"] = c_copy.pop("_gap_estimated_months", 0)
                c_copy["is_critical"] = c_copy.pop("_is_critical", False)
                c_copy["selection_reason"] = reason
                c_copy["is_youtube"] = False
                final_courses.append(c_copy)
        
        if vid:
            v = youtube_id_map.get(vid)
            if v:
                v_copy = v.copy()
                # Standardize YouTube video to look like a course if needed, or keep as video
                v_copy["selection_reason"] = reason
                v_copy["gap_skill"] = v.get("gap_skill", item.get("gap_skills", [""])[0] if item.get("gap_skills") else "")
                selected_youtube.append(v_copy)

    # ── STEP 3: Deduplicate + rank ───────────────────────────────────────────
    course_recommendations = _deduplicate_and_rank(final_courses, gaps=gaps_to_process)

    logger.info(
        f"[STEP 4] DONE (OPTIMIZED) | courses={len(course_recommendations)} "
        f"| youtube={len(selected_youtube)} | roadmap stages={len(career_roadmap.get('stages', []))}"
    )

    return {
        **state,
        "course_recommendations": course_recommendations,
        "selected_youtube_videos": selected_youtube,
        "youtube_videos": youtube_videos, # Keep raw results just in case
        "career_roadmap": career_roadmap,
        "status": "courses_done",
    }


# ══════════════════════════════════════════════════════════════════════════════
# UNIFIED LLM CALL: Course Selection + Roadmap (replaces 3+1 separate calls)
# ══════════════════════════════════════════════════════════════════════════════


async def _llm_select_courses_and_roadmap_unified(
    all_candidates: List[Dict],
    youtube_candidates: List[Dict],
    gaps: List[Dict],
    jd_context: str,
    user_id: str = None,
) -> Dict[str, Any]:
    """
    ONE LLM call handles BOTH:
      - Select best courses for ALL gaps
      - Build career roadmap

    Previously: 4 separate LLM calls
      _llm_prioritize_gaps → _llm_select_courses × N → roadmap_synthesis

    Now: 1 LLM call
      _llm_select_courses_and_roadmap_unified
    """
    # ── Build gap context block (JSON) ──────────────────────────────────────────
    gaps_json = []
    for g in gaps:
        gaps_json.append({
            "skill": g.get("skill") or "?",
            "required_level": g.get("required_level") or "Mid-level",
            "severity": g.get("severity") or "MEDIUM",
            "estimated_months": g.get("estimated_months") or 3,
            "learning_path": g.get("learning_path") or ""
        })
    gaps_context = _json.dumps(gaps_json, ensure_ascii=False, indent=2)

    # ── Build candidates block (JSON) ──────────────────────────────────────────
    # Increase limit to 10 to give more options across all gaps
    sorted_candidates = sorted(
        all_candidates, 
        key=lambda x: float(x.get("similarity") or 0), 
        reverse=True
    )[:10]

    candidates_json = []
    for c in sorted_candidates:
        candidates_json.append({
            "course_id": c.get("course_id"),
            "target_gap_skill": c.get("_gap_skill") or "?",
            "title": c.get("title"),
            "platform": c.get("platform"),
            "skills": (c.get("skills_raw") or [])[:6],
        })
    candidates_context = _json.dumps(candidates_json, ensure_ascii=False, indent=2)

    # ── Build YouTube candidates block (JSON) ──────────────────────────────────
    yt_json = []
    for v in youtube_candidates:
        yt_json.append({
            "video_id": v.get("video_id"),
            "target_gap_skill": v.get("gap_skill") or "?",
            "title": v.get("title"),
            "channel": v.get("channel_name"),
        })
    yt_context = _json.dumps(yt_json, ensure_ascii=False, indent=2)

    prompt = (
        "You are a Senior Learning Path Advisor. Select the best resources (paid courses + free YouTube) and build a career roadmap.\n\n"
        "## GAP CONTEXT:\n" + gaps_context + "\n\n"
        "## PAID COURSE CANDIDATES:\n" + candidates_context + "\n\n"
        "## FREE YOUTUBE CANDIDATES:\n" + yt_context + "\n\n"
        "## MISSION:\n"
        "1. SELECT RESOURCES: For each gap, pick 1 best paid course AND 1 best YouTube video.\n"
        "   - STRICTOR REASONING: The 'selection_reason' MUST describe the specific resource selected.\n"
        "   - DO NOT mix YouTube details into a Paid Course description.\n"
        "   - If you select a Coursera course, talk about its curriculum. If you select a YouTube video, talk about its content/length.\n"
        "   - Selection reason must be in Vietnamese.\n"
        "2. BUILD ROADMAP: Create a personalized learning roadmap in Vietnamese.\n"
        "   - Group resources by learning stage (Stage 1: fundamentals → Stage 2: intermediate → Stage 3: advanced)\n"
        "   - Use English for skill names, Vietnamese for descriptions\n"
        "   - Each stage: focus skill, duration_weeks, milestones\n\n"
        "## OUTPUT JSON SCHEMA:\n"
        "{\n"
        '  "selected_courses": [\n'
        '    {\n'
        '      "course_id": "standard_course_id_here",\n'
        '      "video_id": "youtube_video_id_here (if youtube)",\n'
        '      "gap_skills": ["skill1"],\n'
        '      "selection_reason": "...",\n'
        '      "stage": 1\n'
        '    }\n'
        '  ],\n'
        '  "career_roadmap": {\n'
        '    "stages": [\n'
        '      {\n'
        '        "stage": 1,\n'
        '        "focus": "skill name in English",\n'
        '        "duration_weeks": 4,\n'
        '        "skills_acquired": ["..."],\n'
        '        "courses_taken": ["course titles or video titles"],\n'
        '        "milestones": [{"week": 1, "milestone": "..."}]\n'
        '      }\n'
        '    ],\n'
        '    "total_weeks": 12,\n'
        '    "total_hours": 40,\n'
        '    "summary": "Vietnamese summary"\n'
        '  }\n'
        "}\n\n"
        "Return ONLY valid JSON."
    )

    logger.info(
        f"\n{'═' * 70}\n"
        f"[LLM DATA] ┌─── _llm_select_courses_and_roadmap_unified\n"
        f"           │ gaps_count   : {len(gaps)}\n"
        f"           │ candidates  : {len(all_candidates)}\n"
        f"           │ jd_context  : {jd_context or '(none)'}\n"
        f"           └─────────\n"
        f"[LLM DATA] PROMPT (first 2000 chars):\n"
        f"{_indent_data(prompt[:2000])}\n"
        f"{'═' * 70}\n"
    )

    # user_id is passed from node to llm_json_completion
    result = await llm_json_completion(
        prompt=prompt,
        context=jd_context,
        call_name="select_courses_and_roadmap_unified",
        user_id=user_id
    )

    if not result:
        logger.warning("[STEP 4/Unified] LLM returned empty — returning empty results")
        return {"selected_courses": [], "career_roadmap": {}}

    logger.info(
        f"[STEP 4/Unified] LLM OK | selected={len(result.get('selected_courses', []))} "
        f"| roadmap stages={len(result.get('career_roadmap', {}).get('stages', []))}\n"
        f"{_indent_data(_json.dumps(result, ensure_ascii=False, indent=2)[:1000])}"
    )
    return result


# ══════════════════════════════════════════════════════════════════════════════
# Vector Search (no LLM — pure pgvector)
# ══════════════════════════════════════════════════════════════════════════════


async def _vector_search_courses(
    skill_name: str,
    target_level: str,
    db,
    limit: int = 12,
) -> List[Dict]:
    from shared.llm_utils import get_embedding
    from sqlalchemy import text

    search_text = skill_name + " " + target_level + " course tutorial"
    skill_vector = get_embedding(search_text)

    if not skill_vector:
        logger.warning("[STEP 4/Search] No embedding for: " + skill_name)
        # ── Fallback: ILIKE text search when embedding unavailable ──────────────
        return _search_courses_ilike(skill_name, target_level, db, limit)

    # ── pgvector search: fetch skills_raw + modules for ranking ────────────────
    sim_threshold = config_manager.get_setting("gap_vector_sim_threshold", default=0.35, cast=float)
    query = text("""
        SELECT id, title, platform, url, level, provider, source_platform,
               duration_hours, is_certification, cost_usd, tags,
               skills_raw, modules, outcomes, embedding_context,
               1 - (vector <=> CAST(:vec AS vector)) as similarity
        FROM courses
        WHERE vector IS NOT NULL
          AND 1 - (vector <=> CAST(:vec AS vector)) > :sim_threshold
        ORDER BY similarity DESC
        LIMIT :limit_val
    """)

    try:
        results = db.execute(
            query,
            {
                "vec": skill_vector,
                "sim_threshold": sim_threshold,
                "limit_val": limit,
            },
        ).fetchall()
    except Exception as e:
        logger.warning(f"[STEP 4/Search] pgvector query failed: {e}")
        results = []

    courses = []
    for r in results:
        courses.append({
            "course_id": str(r.id),
            "title": r.title or "?",
            "platform": r.platform or r.source_platform or "Unknown",
            "url": r.url or "",
            "level": r.level or "Unknown",
            "provider": getattr(r, "provider") or "Unknown",
            "duration_hours": float(r.duration_hours or 0),
            "is_certification": bool(r.is_certification),
            "cost_usd": float(r.cost_usd or 0),
            "tags": list(r.tags) if r.tags else [],
            # ── CRITICAL: skills_raw + modules for ranking ──────────────────────
            "skills_raw": r.skills_raw or [],
            "modules": r.modules or [],
            "outcomes": r.outcomes or [],
            "embedding_context": r.embedding_context or "",
            "similarity": float(r.similarity or 0),
        })

    # ── Log vector search results ─────────────────────────────────────────────
    logger.info(
        f"[STEP 4/Search] {len(courses)} courses found for '{skill_name}' | "
        f"sim_threshold={sim_threshold}"
    )
    for c in courses[:5]:
        logger.info(
            f"  course: {c.get('title')} | platform={c.get('platform')} | "
            f"level={c.get('level')} | hrs={c.get('duration_hours')} | "
            f"sim={c.get('similarity', 0):.3f} | cert={c.get('is_certification')}"
        )

    return courses


def _search_courses_ilike(
    skill_name: str,
    target_level: str,
    db,
    limit: int = 12,
) -> List[Dict]:
    """Fallback search when vector embedding unavailable."""
    from sqlalchemy import text

    logger.warning(f"[STEP 4/Search] ILIKE fallback for skill='{skill_name}'")

    query = text("""
        SELECT id, title, platform, url, level, provider, source_platform,
               duration_hours, is_certification, cost_usd, tags,
               skills_raw, modules, outcomes, embedding_context,
               0.6 as similarity
        FROM courses
        WHERE title ILIKE :pattern
           OR :skill_name = ANY(tags::text[])
           OR embedding_context ILIKE :pattern
        ORDER BY is_certification DESC, duration_hours ASC
        LIMIT :limit_val
    """)

    try:
        results = db.execute(
            query,
            {
                "pattern": f"%{skill_name}%",
                "skill_name": skill_name,
                "limit_val": limit,
            },
        ).fetchall()
    except Exception as e:
        logger.warning(f"[STEP 4/Search] ILIKE fallback failed: {e}")
        return []

    return [
        {
            "course_id": str(r.id),
            "title": r.title or "?",
            "platform": r.platform or r.source_platform or "Unknown",
            "url": r.url or "",
            "level": r.level or "Unknown",
            "provider": getattr(r, "provider") or "Unknown",
            "duration_hours": float(r.duration_hours or 0),
            "is_certification": bool(r.is_certification),
            "cost_usd": float(r.cost_usd or 0),
            "tags": list(r.tags) if r.tags else [],
            "skills_raw": r.skills_raw or [],
            "modules": r.modules or [],
            "outcomes": r.outcomes or [],
            "embedding_context": r.embedding_context or "",
            "similarity": float(r.similarity or 0),
        }
        for r in results
    ]


# ══════════════════════════════════════════════════════════════════════════════
# Deduplicate + Rank (no LLM — pure formula)
# ══════════════════════════════════════════════════════════════════════════════


def _deduplicate_and_rank(
    courses: List[Dict],
    gaps: List[Dict] = None,
) -> List[Dict]:
    """
    Deduplicate và rank courses.

    Ranking formula (aligned with recommender_service):
      rank = severity_weight × (sim×0.6 + cert_bonus + level_bonus + hard_match_bonus)

    Improvements vs. old version:
      - LevelMapper: penalizes courses below target level, rewards above
      - Hard Match Bonus: +0.1 if skill name appears in tags/skills_raw/modules
      - ILIKE fallback: returns 0.6 similarity score
    """
    from shared.level_mapper import LevelMapper

    # Build skill_name → target_level map from gaps
    gap_level_map: Dict[str, str] = {}
    if gaps:
        for g in gaps:
            skill = (g.get("skill") or "").lower()
            level = g.get("required_level") or g.get("target_level") or "Mid-level"
            gap_level_map[skill] = level

    severity_w = {"HIGH": 1.0, "MEDIUM": 0.7, "LOW": 0.4}

    # Deduplicate by course_id (keep first occurrence = highest-ranked)
    seen = {}
    for c in courses:
        cid = c.get("course_id")
        if cid and cid not in seen:
            seen[cid] = c

    ranked = list(seen.values())

    for c in ranked:
        gap_skill = (c.get("gap_skill") or "").lower()
        sev = severity_w.get(c.get("gap_severity") or "LOW", 0.4)

        # 1. Similarity Score (60%)
        sim = float(c.get("similarity") or 0.5) * 0.6

        # 2. Certification Bonus (0.15)
        cert_bonus = 0.15 if c.get("is_certification") else 0.0

        # 3. Level Match Bonus
        target_level = gap_level_map.get(gap_skill, "Mid-level")
        target_score = LevelMapper.to_score(target_level)
        c_level = c.get("level") or "Unknown"
        c_score = LevelMapper.to_score(c_level)
        level_diff = c_score - target_score
        # Reward: course meets or exceeds required level
        level_bonus = 0.05 if level_diff >= 0 else (level_diff * 0.1)
        # Cap penalty: max -0.1
        level_bonus = max(level_bonus, -0.1)

        # 4. Hard Match Bonus (+0.1) — exact skill name in tags/skills_raw/modules
        hard_match_bonus = 0.0
        if gap_skill and gap_skill != "?":
            search_area = (
                [s.lower() for s in c.get("tags", [])] +
                [s.lower() for s in c.get("skills_raw", [])] +
                [str(m).lower() for m in c.get("modules", [])]
            )
            if any(gap_skill in item for item in search_area):
                hard_match_bonus = 0.1

        # Final score
        raw_score = sim + cert_bonus + level_bonus + hard_match_bonus
        c["rank_score"] = round(raw_score * sev, 3)
        c["_level_match"] = f"{c_level} (target={target_level}, diff={level_diff})"
        c["_hard_match"] = hard_match_bonus > 0

        # ── Log per-course scoring ─────────────────────────────────────────────
        logger.info(
            f"  [RANK] {c.get('title', '?')[:50]} | "
            f"level={c_level} (target={target_level}) | "
            f"cert={c.get('is_certification')} | "
            f"sim={sim:.3f} cert={cert_bonus:.2f} level={level_bonus:.2f} hard={hard_match_bonus:.2f} "
            f"→ rank={c['rank_score']:.3f}"
        )

    ranked.sort(key=lambda x: x.get("rank_score", 0), reverse=True)

    # ── Log final ranked courses ─────────────────────────────────────────────
    logger.info(f"[STEP 4/Rank] Final ranked {len(ranked)} courses:")
    for i, c in enumerate(ranked[:8]):
        logger.info(
            f"  [{i + 1}] {c.get('title', '?')[:60]} | "
            f"gap={c.get('gap_skill')} | rank={c.get('rank_score')} | "
            f"cert={c.get('is_certification')} | sim={c.get('similarity', 0):.3f} | "
            f"level_match={c.get('_level_match')}"
        )

    return ranked
