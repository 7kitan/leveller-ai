"""
gap_v3 Course Recommendation Agent.
2-step: LLM prioritize TOP 3 gaps → vector search → LLM select TOP 2.
"""

import logging
from typing import Dict, Any, List

from ..states import GapAnalysisStateV3, CourseRecommendation
from ..utils.llm_helpers import llm_json_completion
from ..config import VECTOR_SIM_THRESHOLD

logger = logging.getLogger("course_agent_v3")


# ─── Node 4: Course Recommendation ─────────────────────────────────────────


async def course_recommendation_llm_node(
    state: GapAnalysisStateV3,
) -> GapAnalysisStateV3:
    """
    Course Recommendation Agent:
    1. LLM chọn TOP 3 gaps cần học nhất (ưu tiên weakest + most critical)
    2. pgvector search candidates per gap
    3. LLM chọn TOP 2 courses phù hợp nhất per gap
    4. Deduplicate + rank
    """
    logger.info("--- [GAP v3] COURSE RECOMMENDATION AGENT ---")

    gap_analysis = state.get("gap_analysis")
    if not gap_analysis:
        return {**state, "course_recommendations": [], "status": "courses_done"}

    skill_gaps = gap_analysis.get("skill_gaps", [])
    jd_context = gap_analysis.get("jd_context", "")

    if not skill_gaps:
        logger.info("  No skill gaps found. Skipping course recommendation.")
        return {**state, "course_recommendations": [], "status": "courses_done"}

    # ── Step 1: LLM Prioritize TOP 3 Gaps ─────────────────────────────
    top_gaps = await _llm_prioritize_gaps(skill_gaps, jd_context)
    logger.info(
        f"  Step 1: {len(top_gaps)} gaps prioritized: {[g['skill'] for g in top_gaps]}"
    )

    if not top_gaps:
        return {**state, "course_recommendations": [], "status": "courses_done"}

    # ── Step 2: Vector Search + LLM Select per gap ───────────────────
    all_recommendations = []
    db = state["db"]

    for gap in top_gaps:
        gap_skill = gap["skill"]
        required_level = gap.get("required_level", "Mid-level")
        estimated_months = gap.get("estimated_months", 3)
        learning_path = gap.get("learning_path", "")

        # Vector search candidates
        course_candidates = await _vector_search_courses(
            skill_name=gap_skill, target_level=required_level, db=db, limit=12
        )

        if not course_candidates:
            logger.info(f"  No courses found for gap: {gap_skill}")
            continue

        logger.info(f"  Step 2: {len(course_candidates)} candidates for '{gap_skill}'")

        # LLM select TOP 2
        selected = await _llm_select_courses(
            gap=gap, candidates=course_candidates, jd_context=jd_context
        )

        for course in selected:
            course["gap_skill"] = gap_skill
            course["gap_severity"] = gap.get("severity", "MEDIUM")
            course["gap_learning_path"] = learning_path
            course["gap_estimated_months"] = estimated_months
            course["is_critical"] = gap.get("is_critical", False)
            all_recommendations.append(course)

    # ── Step 3: Deduplicate + Rank ────────────────────────────────────
    course_recommendations = _deduplicate_and_rank(all_recommendations)

    logger.info(
        f"  Course recommendation done: {len(course_recommendations)} unique courses"
    )

    return {
        **state,
        "course_recommendations": course_recommendations,
        "status": "courses_done",
    }


# ─── Step 1: LLM Prioritize Gaps ──────────────────────────────────────


async def _llm_prioritize_gaps(skill_gaps: List[Dict], jd_context: str) -> List[Dict]:
    """LLM chọn TOP 3 gaps cần học nhất."""
    if not skill_gaps:
        return []

    gaps_str = "\n".join(
        [
            f"- #{i + 1} {g['skill']} | severity: {g['severity']} | "
            f"is_critical: {g.get('is_critical')} | "
            f"months: {g.get('estimated_months')} | "
            f"learning_effort: {g.get('learning_effort')} | "
            f"bridge_from: {g.get('bridge_from', 'none')} | "
            f"learning_path: {g.get('learning_path', '')}"
            for i, g in enumerate(skill_gaps)
        ]
    )

    prompt = f"""Chọn TOP 3 skill gaps ƯU TIÊN NHẤT để lấp gap.

## Job Context: {jd_context}

## All Skill Gaps:
{gaps_str}

## Quy tắc ưu tiên:
1. HIGH severity + is_critical=True → HỌC TRƯỚC (job requirement thiết yếu)
2. Có bridge_from (transferable) → học NHANH (ROI cao) → ưu tiên
3. estimated_months ≤ 3 → có thể hoàn thành trước khi apply
4. LOW severity → bỏ qua (dễ tự học, không cần course)
5. Tối đa 3 gaps — không cần học quá nhiều cùng lúc

## Output JSON:
{{
  "top_gaps": [
    {{
      "skill": "<tên>",
      "severity": "HIGH | MEDIUM | LOW",
      "is_critical": true|false,
      "priority_rank": <1, 2, 3>,
      "estimated_months": <số tháng>,
      "bridge_from": "<skill đã có, null>",
      "learning_path": "<lộ trình>",
      "reason": "<tại sao ưu tiên skill này>"
    }}
  ]
}}
CHỈ trả về JSON hợp lệ. Tối đa 3 gaps."""

    result = await llm_json_completion(prompt, context=jd_context)
    top_gaps = result.get("top_gaps", [])

    # Fallback: sort by severity + is_critical if LLM failed
    if not top_gaps:
        severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        sorted_gaps = sorted(
            skill_gaps,
            key=lambda g: (
                severity_order.get(g.get("severity", "LOW"), 2),
                -int(g.get("is_critical", False)),
                g.get("estimated_months", 99),
            ),
        )
        top_gaps = sorted_gaps[:3]
        logger.info(
            f"  LLM prioritize failed. Using fallback sort: {[g['skill'] for g in top_gaps]}"
        )

    return top_gaps


# ─── Step 2a: Vector Search ─────────────────────────────────────────────


async def _vector_search_courses(
    skill_name: str, target_level: str, db, limit: int = 12
) -> List[Dict]:
    """pgvector similarity search cho courses."""
    from sqlalchemy import text
    from shared.llm_utils import get_embedding

    search_text = f"{skill_name} {target_level} course tutorial"
    skill_vector = get_embedding(search_text)

    if not skill_vector:
        logger.warning(f"  No embedding for: {skill_name}")
        # Fallback: text search
        return await _text_search_courses(skill_name, db, limit)

    query = text("""
        SELECT id, title, platform, url, level, provider,
               duration_hours, is_certification, cost_usd, tags,
               1 - (vector <=> :vec::vector) as similarity
        FROM courses
        WHERE vector IS NOT NULL
          AND 1 - (vector <=> :vec::vector) > :sim_threshold
        ORDER BY similarity DESC
        LIMIT :limit
    """)

    results = db.execute(
        query,
        {"vec": skill_vector, "sim_threshold": VECTOR_SIM_THRESHOLD, "limit": limit},
    ).fetchall()

    return [
        {
            "course_id": str(r.id),
            "title": r.title,
            "platform": r.platform,
            "url": r.url,
            "level": r.level or "Unknown",
            "provider": getattr(r, "provider", "Unknown") or "Unknown",
            "duration_hours": float(r.duration_hours or 0),
            "is_certification": bool(r.is_certification),
            "cost_usd": float(r.cost_usd or 0),
            "tags": r.tags or [],
            "similarity": float(r.similarity),
        }
        for r in results
    ]


async def _text_search_courses(skill_name: str, db, limit: int = 12) -> List[Dict]:
    """Fallback: text search khi không có vector."""
    from sqlalchemy import text

    query = text("""
        SELECT id, title, platform, url, level, provider,
               duration_hours, is_certification, cost_usd, tags
        FROM courses
        WHERE title ILIKE :pattern
           OR :skill = ANY(tags::text[])
        ORDER BY is_certification DESC, duration_hours ASC
        LIMIT :limit
    """)

    results = db.execute(
        query, {"pattern": f"%{skill_name}%", "skill": skill_name, "limit": limit}
    ).fetchall()

    return [
        {
            "course_id": str(r.id),
            "title": r.title,
            "platform": r.platform,
            "url": r.url,
            "level": r.level or "Unknown",
            "provider": getattr(r, "provider", "Unknown") or "Unknown",
            "duration_hours": float(r.duration_hours or 0),
            "is_certification": bool(r.is_certification),
            "cost_usd": float(r.cost_usd or 0),
            "tags": r.tags or [],
            "similarity": 0.5,  # Default
        }
        for r in results
    ]


# ─── Step 2b: LLM Select Best Courses ────────────────────────────────


async def _llm_select_courses(
    gap: Dict, candidates: List[Dict], jd_context: str
) -> List[Dict]:
    """LLM chọn TOP 2 courses phù hợp nhất cho 1 gap skill."""
    if not candidates:
        return []

    skill_name = gap["skill"]
    required_level = gap.get("required_level", "Mid-level")
    estimated_months = gap.get("estimated_months", 3)
    learning_path = gap.get("learning_path", "")
    severity = gap.get("severity", "MEDIUM")

    candidates_str = "\n".join(
        [
            f"- [{i + 1}] {c['title']} | {c['platform']} | {c['level']} | "
            f"{c['duration_hours']}h | cert: {c['is_certification']} | "
            f"similarity: {c['similarity']:.2f} | ${c['cost_usd']:.2f} | "
            f"tags: {', '.join(c['tags'][:5] if c['tags'] else [])}"
            for i, c in enumerate(candidates)
        ]
    )

    prompt = f"""Chọn TOP 2 khóa học phù hợp nhất để lấp gap "{skill_name}"
(target level: {required_level}, severity: {severity}, ước tính: {estimated_months} tháng).

## Learning path đề xuất: {learning_path}

## Available Courses ({len(candidates)} candidates):
{candidates_str}

## Quy tắc chọn:
1. Ưu tiên is_certification = true (giá trị trên CV)
2. Duration phù hợp: không quá 2.5× estimated_months (VD: 3 tháng → khóa ≤ 80 giờ)
3. Level phù hợp với gap:
   - severity=HIGH → Beginner courses (chưa có gì)
   - severity=MEDIUM → Intermediate courses
4. Platform uy tín: Udemy, Coursera, Pluralsight, LinkedIn Learning, edX
5. Free hoặc < $50 là best value
6. Khóa nào phù hợp với learning_path → ưu tiên

## Output JSON:
{{
  "selected_courses": [
    {{
      "course_id": "<id>",
      "selection_reason": "<tại sao chọn khóa này cho gap {skill_name}>"
    }}
  ]
}}
CHỈ trả về JSON hợp lệ. Top 2 thôi."""

    result = await llm_json_completion(prompt, context=jd_context)
    selected_ids = [c["course_id"] for c in result.get("selected_courses", [])]

    # Map back to full course data
    course_map = {c["course_id"]: c for c in candidates}
    output = []

    for cid in selected_ids[:2]:
        course = course_map.get(cid)
        if not course:
            continue
        sel = next(
            (s for s in result.get("selected_courses", []) if s["course_id"] == cid), {}
        )
        output.append(
            {
                **course,
                "selection_reason": sel.get("selection_reason", ""),
                "learning_path": learning_path,
            }
        )

    return output


# ─── Step 3: Deduplicate + Rank ────────────────────────────────────


def _deduplicate_and_rank(courses: List[Dict]) -> List[Dict]:
    """Deduplicate và rank theo severity × certification × similarity."""
    seen_ids = {}
    for c in courses:
        cid = c.get("course_id")
        if cid and cid not in seen_ids:
            seen_ids[cid] = c

    ranked = list(seen_ids.values())

    severity_w = {"HIGH": 1.0, "MEDIUM": 0.7, "LOW": 0.4}
    for c in ranked:
        sev = severity_w.get(c.get("gap_severity", "LOW"), 0.4)
        cert = 0.2 if c.get("is_certification") else 0
        sim = c.get("similarity", 0) * 0.2
        c["rank_score"] = round(sev * 0.6 + cert * 0.2 + sim, 3)

    ranked.sort(key=lambda x: x["rank_score"], reverse=True)
    return ranked
