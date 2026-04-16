from fastapi import FastAPI, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from shared.database import get_db
from shared.models import Course, JobSkillRequirement, Job
from shared.level_mapper import LevelMapper
from pydantic import BaseModel
from typing import List, Optional
import uuid
import logging
import os

app = FastAPI(title="Recommender Service")
logger = logging.getLogger("recommender")

# Thresholds
VECTOR_SIM_THRESHOLD = float(os.getenv("GAP_VECTOR_SIM_THRESHOLD", "0.60"))


class GapSkill(BaseModel):
    skill_name: str
    target_level: str = "Mid-level"
    gap_type: str = "MISSING"
    severity: str = "MEDIUM"  # HIGH | MEDIUM | LOW — ảnh hưởng rank
    severity: str = "MEDIUM"


class RecommendRequest(BaseModel):
    gap_skills: List[GapSkill]


def _vector_search_courses(skill_name: str, target_level: str, db, limit: int = 12):
    """pgvector similarity search cho courses. Fallback ILIKE nếu không có vector."""
    from shared.llm_utils import get_embedding

    search_text = f"{skill_name} {target_level} course tutorial"
    skill_vector = get_embedding(search_text)

    if skill_vector:
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
            {
                "vec": skill_vector,
                "sim_threshold": VECTOR_SIM_THRESHOLD,
                "limit": limit,
            },
        ).fetchall()
    else:
        # Fallback: ILIKE text search
        query = text("""
            SELECT id, title, platform, url, level, provider,
                   duration_hours, is_certification, cost_usd, tags,
                   0.6 as similarity
            FROM courses
            WHERE title ILIKE :pattern
               OR :skill_name = ANY(tags::text[])
            ORDER BY is_certification DESC, duration_hours ASC
            LIMIT :limit
        """)
        results = db.execute(
            query,
            {"pattern": f"%{skill_name}%", "skill_name": skill_name, "limit": limit},
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


def _rank_courses(
    candidates: List[dict], target_level: str, severity: str
) -> List[dict]:
    """Rank courses: severity × certification × level_match × similarity."""
    target_score = LevelMapper.to_score(target_level)
    severity_w = {"HIGH": 1.0, "MEDIUM": 0.7, "LOW": 0.4}

    sev = severity_w.get(severity, 0.4)

    for c in candidates:
        cert_bonus = 0.2 if c.get("is_certification") else 0
        c_level_score = LevelMapper.to_score(c.get("level") or "Unknown")
        level_diff = c_level_score - target_score

        level_bonus = 0.05 if level_diff >= 0 else (level_diff * 0.15)
        sim = c.get("similarity", 0.5) * 0.2

        c["rank_score"] = round(sev * 0.5 + cert_bonus * 0.3 + level_bonus + sim, 3)

    candidates.sort(key=lambda x: x["rank_score"], reverse=True)
    return candidates


@app.post("/recommend/courses")
async def recommend_courses(req: RecommendRequest, db: Session = Depends(get_db)):
    """
    Recommend courses cho gap skills.
    Sử dụng pgvector similarity search (thay vì ILIKE).
    Priority: HIGH severity → certification → level match → similarity.
    """
    all_recommendations = []
    seen_ids = set()

    # Sort: severity HIGH → MEDIUM → LOW
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    sorted_gaps = sorted(
        req.gap_skills,
        key=lambda g: (severity_order.get(g.severity, 2), g.gap_type == "PARTIAL"),
    )

    for gap in sorted_gaps:
        logger.info(
            f"Recommending for: {gap.skill_name} | Gap: {gap.gap_type} "
            f"| Level: {gap.target_level} | Severity: {gap.severity}"
        )

        # Vector search
        candidates = _vector_search_courses(
            skill_name=gap.skill_name, target_level=gap.target_level, db=db, limit=10
        )

        if not candidates:
            logger.info(f"  No courses found for: {gap.skill_name}")
            continue

        # Rank
        ranked = _rank_courses(candidates, gap.target_level, gap.severity)

        # Giới hạn: 2 cho MISSING, 1 cho PARTIAL
        limit = 2 if gap.gap_type == "MISSING" else 1

        for c in ranked[:limit]:
            if c["course_id"] not in seen_ids:
                all_recommendations.append(
                    {
                        "id": c["course_id"],
                        "title": c["title"],
                        "platform": c["platform"],
                        "url": c["url"],
                        "level": c["level"],
                        "provider": c["provider"],
                        "duration_hours": c["duration_hours"],
                        "is_certification": c["is_certification"],
                        "cost_usd": c["cost_usd"],
                        "rank_score": c["rank_score"],
                        "similarity": c["similarity"],
                        "gap_skill": gap.skill_name,
                        "gap_severity": gap.severity,
                    }
                )
                seen_ids.add(c["course_id"])

        logger.info(
            f"  Found {len(candidates)} candidates, selected top {min(limit, len(ranked))}"
        )

    return all_recommendations


@app.get("/recommend/trending-skills")
async def get_trending_skills(
    days: int = 30, limit: int = 20, db: Session = Depends(get_db)
):
    """
    Lọc top Skills có tần suất xuất hiện cao nhất trong Job Requirement 30 ngày gần đây.
    Trả về: skill_name, job_count, avg_min_salary, avg_max_salary.
    """
    # Use f-string for INTERVAL (safe: days is int, not from user input)
    safe_query = text(f"""
        SELECT
            s.name as skill_name,
            COUNT(DISTINCT jsr.job_id) as job_count,
            AVG(j.min_salary_vnd) as avg_min_salary,
            AVG(j.max_salary_vnd) as avg_max_salary,
            ARRAY_AGG(DISTINCT j.title_category) FILTER (WHERE j.title_category IS NOT NULL) as roles
        FROM job_skill_requirement jsr
        JOIN jobs j ON j.id = jsr.job_id
        JOIN skills s ON s.id = jsr.skill_id
        WHERE j.status = 'active'
          AND j.created_at >= NOW() - INTERVAL '{days} days'
        GROUP BY s.id, s.name
        ORDER BY job_count DESC
        LIMIT :limit
    """)

    res = db.execute(safe_query, {"limit": limit}).fetchall()

    return [
        {
            "skill_name": r.skill_name,
            "job_count": r.job_count,
            "avg_min_salary_vnd": float(r.avg_min_salary) if r.avg_min_salary else None,
            "avg_max_salary_vnd": float(r.avg_max_salary) if r.avg_max_salary else None,
            "roles": list(r.roles) if r.roles else [],
        }
        for r in res
    ]
