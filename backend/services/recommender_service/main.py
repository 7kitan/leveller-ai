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

app = FastAPI(title="Recommender Service")
logger = logging.getLogger("recommender")

class GapSkill(BaseModel):
    skill_name: str
    target_level: str = "Mid-level"
    gap_type: str = "MISSING"

class RecommendRequest(BaseModel):
    gap_skills: List[GapSkill]

@app.post("/recommend/courses")
async def recommend_courses(req: RecommendRequest, db: Session = Depends(get_db)):
    all_recommendations = []
    seen_ids = set()

    for gap in req.gap_skills:
        logger.info(f"Recommending for: {gap.skill_name} | Gap: {gap.gap_type} | Level: {gap.target_level}")
        target_score = LevelMapper.to_score(gap.target_level)
        
        search_terms = [s.strip() for s in gap.skill_name.split('/')]
        primary_term = search_terms[0] if search_terms else gap.skill_name
        
        query = text("""
            SELECT id, title, platform, url, level, is_certification, provider, 0.9 as similarity
            FROM courses
            WHERE title ILIKE :name_pattern OR provider ILIKE :name_pattern OR tags::text ILIKE :name_pattern
            LIMIT 5
        """)
        
        res = db.execute(query, {"name_pattern": f"%{primary_term}%"}).fetchall()
        
        scored_courses = []
        for r in res:
            c_level_score = LevelMapper.to_score(r.level)
            rank_score = float(r.similarity)
            
            level_diff = c_level_score - target_score
            if level_diff < 0:
                rank_score += (level_diff * 0.15) 
            elif level_diff >= 0:
                rank_score += 0.05 
            
            if getattr(r, 'is_certification', False):
                rank_score += 0.2
            
            scored_courses.append({
                "course": {
                    "id": str(r.id),
                    "title": r.title,
                    "platform": r.platform,
                    "url": r.url,
                    "level": r.level,
                    "provider": getattr(r, 'provider', 'Unknown'),
                    "is_certification": getattr(r, 'is_certification', False)
                },
                "rank": rank_score
            })
        
        scored_courses.sort(key=lambda x: x["rank"], reverse=True)
        limit = 2 if gap.gap_type == "MISSING" else 1
        
        for sc in scored_courses[:limit]:
            if sc["course"]["id"] not in seen_ids:
                all_recommendations.append(sc["course"])
                seen_ids.add(sc["course"]["id"])

    return all_recommendations

@app.get("/recommend/trending-skills")
async def get_trending_skills(days: int = 30, limit: int = 20, db: Session = Depends(get_db)):
    """Lọc top Skills có tần suất xuất hiện cao nhất trong Job Requirement 30 ngày gần đây."""
    query = text("""
        SELECT s.name as skill_name, COUNT(DISTINCT jsr.job_id) as job_count, AVG(j.min_salary_vnd) as avg_salary
        FROM job_skill_requirement jsr
        JOIN jobs j ON j.id = jsr.job_id
        JOIN skills s ON s.id = jsr.skill_id
        WHERE j.status = 'active'
          AND j.created_at >= NOW() - INTERVAL ':days days'
        GROUP BY s.id, s.name
        ORDER BY job_count DESC
        LIMIT :limit
    """)
    
    # Do param thay thế INTERVAL qua SQLAlchemy text có chút phức tạp, ta handle = f-string an toàn vì days là cast int:
    safe_query = text(f"""
        SELECT s.name as skill_name, COUNT(DISTINCT jsr.job_id) as job_count, AVG(j.min_salary_vnd) as avg_salary
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
            "avg_salary_vnd": float(r.avg_salary) if r.avg_salary else None
        } for r in res
    ]
