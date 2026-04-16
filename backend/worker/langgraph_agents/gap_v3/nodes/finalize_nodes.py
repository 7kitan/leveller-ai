"""
gap_v3 Roadmap Synthesis + Finalize Nodes.
"""

import logging
from typing import Dict, Any

from ..states import GapAnalysisStateV3, CareerRoadmap
from ..utils.llm_helpers import llm_json_completion

logger = logging.getLogger("roadmap_v3")


# ─── Node 5: Roadmap Synthesis ──────────────────────────────────────────────


async def roadmap_synthesis_node(state: GapAnalysisStateV3) -> GapAnalysisStateV3:
    """
    Roadmap Synthesizer Agent: Tạo career roadmap với timeline stages + milestones.
    """
    logger.info("--- [GAP v3] ROADMAP SYNTHESIS ---")

    gap_analysis = state.get("gap_analysis")
    course_recommendations = state.get("course_recommendations", [])

    if not gap_analysis:
        return {**state, "career_roadmap": {}, "status": "roadmap_done"}

    skill_gaps = gap_analysis.get("skill_gaps", [])
    jd_context = gap_analysis.get("jd_context", "")

    if not skill_gaps or not course_recommendations:
        logger.info("  No gaps or courses. Skipping roadmap.")
        return {**state, "career_roadmap": {}, "status": "roadmap_done"}

    # Format data for LLM
    gaps_str = "\n".join(
        [
            f"- {g['skill']}: {g['estimated_months']:.0f} tháng, "
            f"severity: {g['severity']}, effort: {g.get('learning_effort')}, "
            f"path: {g.get('learning_path', '')}"
            for g in skill_gaps[:5]
        ]
    )

    courses_str = "\n".join(
        [
            f"- {c['title']} ({c['platform']}) | {c['duration_hours']:.0f}h | "
            f"for: {c.get('gap_skill', '')} | cert: {c.get('is_certification')}"
            for c in course_recommendations[:6]
        ]
    )

    prompt = f"""Tạo lộ trình học tập (career roadmap) cá nhân hóa.

## Skills cần học (theo thứ tự ưu tiên):
{gaps_str}

## Khóa học đề xuất:
{courses_str}

## Yêu cầu:
1. Sắp xếp stages theo: severity (HIGH trước) + dependency (VD: Docker trước Kubernetes)
2. Mỗi stage = 2-4 tuần học tập, mỗi stage có 2-3 milestones cụ thể
3. Milestone phải đo lường được: "deploy được app lên K8s" không phải "học K8s"
4. Ước tính tổng thời gian realistic
5. Gắn course vào từng stage
6. Bám sát learning_path đã đề xuất

## Output JSON:
{{
  "career_roadmap": {{
    "stages": [
      {{
        "stage": 1,
        "focus": "<tên focus, ví dụ: Kubernetes Fundamentals>",
        "duration_weeks": <số tuân>,
        "skills_acquired": ["<skill1>", "<skill2>"],
        "courses_taken": ["<tên course>"],
        "milestones": [
          {{"week": <số>, "milestone": "<mô tả milestone cụ thể>"}}
        ]
      }}
    ],
    "total_weeks": <tổng số tuần>,
    "total_hours": <tổng số giờ>,
    "summary": "<tóm tắt roadmap 2-3 câu>"
  }}
}}
CHỈ trả về JSON hợp lệ."""

    logger.info(
        f"  LLM Roadmap synthesis: {len(skill_gaps)} gaps, {len(course_recommendations)} courses"
    )
    result = await llm_json_completion(prompt, context=jd_context)

    roadmap = result.get("career_roadmap", {})
    if roadmap:
        logger.info(
            f"  Roadmap done: {len(roadmap.get('stages', []))} stages, "
            f"{roadmap.get('total_weeks', 0)} weeks total"
        )

    return {**state, "career_roadmap": roadmap, "status": "roadmap_done"}


# ─── Node 6: Finalize Report ──────────────────────────────────────────────


async def finalize_report_node(state: GapAnalysisStateV3) -> GapAnalysisStateV3:
    """
    Merge tất cả outputs → final_report JSON.
    Cache vào Redis + persist vào UserAnalysis table.
    """
    logger.info("--- [GAP v3] FINALIZE REPORT ---")

    gap_analysis = state.get("gap_analysis")
    course_recommendations = state.get("course_recommendations", [])
    career_roadmap = state.get("career_roadmap") or {}

    if not gap_analysis:
        return {
            **state,
            "final_report": {
                "overall_match_pct": 0,
                "overall_assessment": "Analysis failed.",
                "notes": ["ERROR: No gap analysis result"],
            },
            "status": "completed",
        }

    # Build course_recommendations format
    course_output = []
    for c in course_recommendations:
        course_output.append(
            {
                "gap_skill": c.get("gap_skill", ""),
                "gap_severity": c.get("gap_severity", "MEDIUM"),
                "gap_learning_path": c.get("gap_learning_path", ""),
                "is_critical": c.get("is_critical", False),
                "course": {
                    "id": c.get("course_id", ""),
                    "title": c.get("title", ""),
                    "platform": c.get("platform", ""),
                    "url": c.get("url", ""),
                    "level": c.get("level", ""),
                    "provider": c.get("provider", ""),
                    "duration_hours": c.get("duration_hours", 0),
                    "is_certification": c.get("is_certification", False),
                    "cost_usd": c.get("cost_usd", 0),
                },
                "rank_score": c.get("rank_score", 0),
                "selection_reason": c.get("selection_reason", ""),
            }
        )

    final_report = {
        "overall_match_pct": gap_analysis.get("overall_match_pct", 0),
        "overall_assessment": gap_analysis.get("overall_assessment", ""),
        "strengths": gap_analysis.get("strengths", []),
        "weaknesses": gap_analysis.get("weaknesses", []),
        "skill_gaps": gap_analysis.get("skill_gaps", []),
        "gap_summary": gap_analysis.get("gap_summary", {}),
        "transferable_insights": gap_analysis.get("transferable_insights", []),
        "course_recommendations": course_output,
        "career_roadmap": career_roadmap,
        "notes": [
            f"Analysis Method: LLM Holistic v3",
            f"CV parsed: {state.get('cv_parsed', {}).get('is_ocr', False) and 'OCR' or 'Direct'}",
            f"JD requirements: {len(state.get('jd_requirements', []))}",
            f"Courses recommended: {len(course_output)}",
        ],
        "jd_context": gap_analysis.get("jd_context", ""),
    }

    # Cache vào Redis
    try:
        from shared.redis_client import result_cache
        from ..config import GAP_CACHE_TTL
        import json

        cache_key = f"gap:{state['cv_id']}:{state.get('job_id') or 'market'}"
        result_cache.setex(cache_key, GAP_CACHE_TTL, json.dumps(final_report))
        logger.info(f"  Cached to Redis: {cache_key}")
    except Exception as e:
        logger.warning(f"  Redis cache failed: {e}")

    # Persist vào DB
    try:
        import uuid
        from datetime import datetime
        from shared.models import UserAnalysis

        db = state["db"]
        user_id = uuid.UUID(state["user_id"]) if state.get("user_id") else None
        cv_uuid = uuid.UUID(state["cv_id"])
        job_uuid = uuid.UUID(state["job_id"]) if state.get("job_id") else None

        analysis_record = UserAnalysis(
            id=uuid.uuid4(),
            user_id=user_id,
            cv_id=cv_uuid,
            job_id=job_uuid,
            match_score=gap_analysis.get("overall_match_pct", 0),
            result_json=final_report,
            created_at=datetime.now(),
        )
        db.add(analysis_record)
        db.commit()
        logger.info(f"  Persisted to UserAnalysis: {analysis_record.id}")

    except Exception as e:
        logger.warning(f"  DB persist failed: {e}")

    logger.info(
        f"  Final report: {gap_analysis.get('overall_match_pct')}% match, "
        f"{len(course_output)} courses"
    )

    return {**state, "final_report": final_report, "status": "completed"}
