"""
gap_v3 Course Recommendation Agent.
STEP 1: LLM prioritize TOP 3 gaps
STEP 2: pgvector search → LLM select TOP 2
"""

import json as _json
import logging
from typing import Dict, Any, List

from ..states import GapAnalysisStateV3
from ..utils.llm_helpers import llm_json_completion
from ..config import VECTOR_SIM_THRESHOLD

logger = logging.getLogger("course_agent_v3")


def _indent_data(text: str) -> str:
    """Indent each line for log readability."""
    return "\n".join("    " + line for line in text.split("\n"))


# ══════════════════════════════════════════════════════════════════════════════
# NODE 4: Course Recommendation
# ══════════════════════════════════════════════════════════════════════════════


async def course_recommendation_llm_node(
    state: GapAnalysisStateV3,
) -> GapAnalysisStateV3:
    """
    Course Recommendation Agent:
      1. LLM chọn TOP 3 gaps cần học nhất (weakest + most critical)
      2. pgvector search candidates per gap
      3. LLM chọn TOP 2 courses phù hợp nhất per gap
      4. Deduplicate + rank
    """
    gap_analysis = state.get("gap_analysis")
    logger.info(
        "\n" + "=" * 50 + "\n"
        "[STEP 4] course_recommendation_llm_node | cv_id=" + state.get("cv_id", "?")
    )

    if not gap_analysis:
        logger.warning("[STEP 4] No gap_analysis — skipping course recommendation")
        return {**state, "course_recommendations": [], "status": "courses_done"}

    skill_gaps = gap_analysis.get("skill_gaps") or []
    jd_context = gap_analysis.get("jd_context") or ""

    if not skill_gaps:
        logger.warning("[STEP 4] No skill_gaps — skipping course recommendation")
        return {**state, "course_recommendations": [], "status": "courses_done"}

    # Reset aborted transaction
    try:
        state["db"].rollback()
    except Exception:
        pass

    # ── Log raw skill_gaps data fed to LLM prioritization ───────────────────
    logger.info(
        f"\n{'═' * 70}\n"
        f"[LLM DATA] ┌─── course_recommendation (STEP 4)\n"
        f"           │ jd_context : {jd_context or '(none)'}\n"
        f"           │ total gaps : {len(skill_gaps)}\n"
        f"           └─────────\n"
        f"[LLM DATA] SKILL GAPS (raw from gap_analysis):\n"
        f"{_indent_data(_json.dumps(skill_gaps, ensure_ascii=False, indent=2)[:3000])}\n"
        f"{'═' * 70}\n"
    )

    # STEP 1: LLM prioritize TOP 3 gaps
    top_gaps = await _llm_prioritize_gaps(skill_gaps, jd_context)
    logger.info(
        "[STEP 4] TOP gaps: "
        + ", ".join(str(g.get("skill", "?")) for g in top_gaps[:3])
    )

    if not top_gaps:
        logger.warning("[STEP 4] No top gaps prioritized")
        return {**state, "course_recommendations": [], "status": "courses_done"}

    all_recommendations: List[Dict] = []
    db = state["db"]

    # STEP 2: Vector search + LLM select per gap
    for gap in top_gaps:
        gap_skill = gap.get("skill") or "?"
        required_level = gap.get("required_level") or "Mid-level"
        estimated_months = gap.get("estimated_months") or 3
        learning_path = gap.get("learning_path") or ""

        course_candidates = await _vector_search_courses(
            skill_name=gap_skill,
            target_level=required_level,
            db=db,
            limit=12,
        )

        if not course_candidates:
            logger.warning("[STEP 4] No courses found for gap: " + gap_skill)
            continue

        logger.info(
            "[STEP 4] "
            + str(len(course_candidates))
            + " candidates for gap: "
            + gap_skill
        )

        # ── Log raw candidate courses fed to LLM ──────────────────────────────
        logger.info(
            f"\n{'─' * 50}\n"
            f"[LLM DATA] ┌─── _llm_select_courses | gap={gap_skill}\n"
            f"           │ candidates  : {len(course_candidates)}\n"
            f"           │ jd_context  : {jd_context or '(none)'}\n"
            f"           │ required_lvl: {required_level}\n"
            f"           │ severity    : {gap.get('severity') or 'MEDIUM'}\n"
            f"           │ est_months  : {estimated_months}\n"
            f"           └─────────\n"
            f"[LLM DATA] COURSE CANDIDATES:\n"
            f"{_indent_data(_json.dumps(course_candidates, ensure_ascii=False, indent=2)[:2000])}\n"
            f"{'─' * 50}\n"
        )

        selected = await _llm_select_courses(
            gap=gap,
            candidates=course_candidates,
            jd_context=jd_context,
        )

        for c in selected:
            c["gap_skill"] = gap_skill
            c["gap_severity"] = gap.get("severity") or "MEDIUM"
            c["gap_learning_path"] = learning_path
            c["gap_estimated_months"] = estimated_months
            c["is_critical"] = bool(gap.get("is_critical"))
            all_recommendations.append(c)

    # STEP 3: Deduplicate + rank
    course_recommendations = _deduplicate_and_rank(all_recommendations)

    logger.info(
        "[STEP 4] DONE | unique courses: "
        + str(len(course_recommendations))
        + " | cv_id="
        + state.get("cv_id", "?")
    )
    return {
        **state,
        "course_recommendations": course_recommendations,
        "status": "courses_done",
    }


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1: LLM Prioritize Gaps
# ══════════════════════════════════════════════════════════════════════════════


async def _llm_prioritize_gaps(skill_gaps: List[Dict], jd_context: str) -> List[Dict]:
    """LLM chọn TOP 3 gaps ưu tiên học trước."""
    if not skill_gaps:
        return []

    gaps_str = "\n".join(
        "- #"
        + str(i + 1)
        + " "
        + (g.get("skill") or "?")
        + " | severity="
        + str(g.get("severity") or "?")
        + " | is_critical="
        + str(g.get("is_critical"))
        + " | months="
        + str(g.get("estimated_months") or 0)
        + " | effort="
        + str(g.get("learning_effort") or "?")
        for i, g in enumerate(skill_gaps)
    )

    prompt = (
        "Choose TOP 3 skill gaps to prioritize.\n\n"
        "Job context: " + jd_context + "\n\n"
        "All gaps:\n" + gaps_str + "\n\n"
        "Priority rules:\n"
        "1. HIGH severity + is_critical=True → priority\n"
        "2. transferable (bridge_from not null) → fast ROI\n"
        "3. estimated_months <= 3 → quick win\n"
        "4. LOW severity → skip\n\n"
        "Output JSON:\n"
        '{"top_gaps": [{"skill": "...", "severity": "HIGH|MEDIUM|LOW", '
        '"is_critical": true/false, "estimated_months": 3, '
        '"learning_path": "..."}]}'
    )

    # ── Log raw skill_gaps input ─────────────────────────────────────────────
    logger.info(
        f"\n{'═' * 70}\n"
        f"[LLM DATA] ┌─── prioritize_gaps (STEP 4a)\n"
        f"           │ jd_context  : {jd_context or '(none)'}\n"
        f"           │ total_gaps : {len(skill_gaps)}\n"
        f"           └─────────\n"
        f"[LLM DATA] SKILL GAPS (for prioritization):\n"
        f"{_indent_data(gaps_str)}\n"
        f"[LLM DATA] PRIORITIZATION PROMPT:\n"
        f"{_indent_data(prompt)}\n"
        f"{'═' * 70}\n"
    )

    result = await llm_json_completion(
        prompt=prompt,
        context=jd_context,
        call_name="prioritize_gaps",
    )

    top_gaps = result.get("top_gaps") or []
    if top_gaps:
        logger.info(
            "[STEP 4/Prioritize] LLM OK: " + str(len(top_gaps)) + " gaps chosen"
        )
        logger.info(
            f"[STEP 4/Prioritize] TOP GAPS RESULT:\n"
            f"{_indent_data(_json.dumps(top_gaps, ensure_ascii=False, indent=2))}"
        )
        return top_gaps

    # Fallback: sort by severity + is_critical + estimated_months
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    sorted_gaps = sorted(
        skill_gaps,
        key=lambda g: (
            severity_order.get(g.get("severity") or "LOW", 2),
            -int(bool(g.get("is_critical"))),
            float(g.get("estimated_months") or 999),
        ),
    )
    logger.warning(
        "[STEP 4/Prioritize] LLM failed — fallback sort: "
        + ", ".join(g.get("skill", "?") for g in sorted_gaps[:3])
    )
    return sorted_gaps[:3]


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2a: pgvector course search
# ══════════════════════════════════════════════════════════════════════════════


async def _vector_search_courses(
    skill_name: str,
    target_level: str,
    db,
    limit: int = 12,
) -> List[Dict]:
    from shared.llm_utils import get_embedding

    search_text = skill_name + " " + target_level + " course tutorial"
    skill_vector = get_embedding(search_text)

    if not skill_vector:
        logger.warning("[STEP 4/Search] No embedding for: " + skill_name)
        return []

    from sqlalchemy import text

    query = text("""
        SELECT id, title, platform, url, level, provider,
               duration_hours, is_certification, cost_usd, tags,
               1 - (vector <=> CAST(:vec AS vector)) as similarity
        FROM courses
        WHERE vector IS NOT NULL
          AND 1 - (vector <=> CAST(:vec AS vector)) > :sim_threshold
        ORDER BY similarity DESC
        LIMIT :limit_val
    """)

    results = db.execute(
        query,
        {
            "vec": skill_vector,
            "sim_threshold": VECTOR_SIM_THRESHOLD,
            "limit_val": limit,
        },
    ).fetchall()

    courses = [
        {
            "course_id": str(r.id),
            "title": r.title or "?",
            "platform": r.platform or "Unknown",
            "url": r.url or "",
            "level": r.level or "Unknown",
            "provider": getattr(r, "provider") or "Unknown",
            "duration_hours": float(r.duration_hours or 0),
            "is_certification": bool(r.is_certification),
            "cost_usd": float(r.cost_usd or 0),
            "tags": list(r.tags) if r.tags else [],
            "similarity": float(r.similarity or 0),
        }
        for r in results
    ]

    # ── Log vector search results ─────────────────────────────────────────────
    logger.info(
        f"[STEP 4/Search] {len(courses)} courses found for '{skill_name}' | "
        f"sim_threshold={VECTOR_SIM_THRESHOLD}"
    )
    for c in courses[:5]:
        logger.info(
            f"  course: {c.get('title')} | platform={c.get('platform')} | "
            f"level={c.get('level')} | hrs={c.get('duration_hours')} | "
            f"sim={c.get('similarity', 0):.3f} | cert={c.get('is_certification')}"
        )

    return courses


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2b: LLM Select Best Courses
# ══════════════════════════════════════════════════════════════════════════════


async def _llm_select_courses(
    gap: Dict,
    candidates: List[Dict],
    jd_context: str,
) -> List[Dict]:
    """LLM chọn TOP 2 courses phù hợp nhất cho 1 gap skill."""
    if not candidates:
        return []

    skill_name = gap.get("skill") or "?"
    required_level = gap.get("required_level") or "Mid-level"
    estimated_months = gap.get("estimated_months") or 3
    severity = gap.get("severity") or "MEDIUM"

    candidates_str = "\n".join(
        "  ["
        + str(i + 1)
        + "] "
        + c.get("title", "?")
        + " | "
        + (c.get("platform") or "?")
        + " | "
        + (c.get("level") or "?")
        + " | "
        + str(c.get("duration_hours") or "0")
        + "h"
        + " | cert="
        + str(c.get("is_certification"))
        + " | sim="
        + f"{c.get('similarity', 0):.2f}"
        for i, c in enumerate(candidates)
    )

    prompt = (
        "Choose TOP 2 courses for gap: " + skill_name + "\n"
        "Required level: " + required_level + "\n"
        "Severity: " + severity + " | estimated_months: " + str(estimated_months) + "\n"
        "Candidates:\n" + candidates_str + "\n\n"
        "Priority: certification > level match > free/cheap > relevance\n\n"
        'Output JSON: {"selected_courses": [{"course_id": "<id>", "selection_reason": "..."}]}'
    )

    # ── Log course selection prompt ───────────────────────────────────────────
    logger.info(
        f"[STEP 4/select] Calling LLM for gap={skill_name} | "
        f"{len(candidates)} candidates | context={jd_context or '(none)'}"
    )
    logger.info(f"[STEP 4/select] COURSE SELECTION PROMPT:\n{_indent_data(prompt)}\n")

    result = await llm_json_completion(
        prompt=prompt,
        context=jd_context,
        call_name="select_courses",
    )

    selected_list = result.get("selected_courses") or []
    course_map = {c.get("course_id"): c for c in candidates}

    logger.info(
        f"[STEP 4/select] LLM selected {len(selected_list)} courses:\n"
        f"{_indent_data(_json.dumps(selected_list, ensure_ascii=False, indent=2))}"
    )

    output = []
    for item in selected_list[:2]:
        cid = item.get("course_id")
        course = course_map.get(cid)
        if course:
            course["selection_reason"] = item.get("selection_reason") or ""
            output.append(course)

    return output


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3: Deduplicate + Rank
# ══════════════════════════════════════════════════════════════════════════════


def _deduplicate_and_rank(courses: List[Dict]) -> List[Dict]:
    """Deduplicate và rank theo severity × certification × similarity."""
    seen = {}
    for c in courses:
        cid = c.get("course_id")
        if cid and cid not in seen:
            seen[cid] = c

    ranked = list(seen.values())
    severity_w = {"HIGH": 1.0, "MEDIUM": 0.7, "LOW": 0.4}

    for c in ranked:
        sev = severity_w.get(c.get("gap_severity") or "LOW", 0.4)
        cert_bonus = 0.2 if c.get("is_certification") else 0.0
        sim = float(c.get("similarity") or 0) * 0.2
        c["rank_score"] = round(sev * 0.6 + cert_bonus + sim, 3)

    ranked.sort(key=lambda x: x.get("rank_score", 0), reverse=True)

    # ── Log final ranked courses ─────────────────────────────────────────────
    logger.info(f"[STEP 4/Rank] Final ranked {len(ranked)} courses:")
    for i, c in enumerate(ranked[:8]):
        logger.info(
            f"  [{i + 1}] {c.get('title')} | gap={c.get('gap_skill')} | "
            f"severity={c.get('gap_severity')} | rank_score={c.get('rank_score')} | "
            f"cert={c.get('is_certification')} | sim={c.get('similarity', 0):.3f}"
        )

    return ranked
