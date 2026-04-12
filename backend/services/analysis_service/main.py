from fastapi import FastAPI, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from shared.database import get_db
from shared.redis_client import result_cache
from shared.taxonomy_service import taxonomy_service
from shared.models import UserAnalysis
from pydantic import BaseModel
from typing import Optional, List
import uuid
import json
import logging
from worker.celery_app import celery_app
from celery.result import AsyncResult

app = FastAPI(title="Analysis Service")

class GapRequest(BaseModel):
    cv_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    jd_text: Optional[str] = None

class SkillCreate(BaseModel):
    name: str
    category: str = "Technology"
    type: str = "Skill"
    aliases: List[str] = []

class LinkRequest(BaseModel):
    parent: str
    child: str
    rel_type: str = "COMPRISED_OF"

@app.post("/analysis/gap")
async def start_gap_analysis(req: GapRequest, request: Request, db: Session = Depends(get_db)):
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")

    # Gửi task vào Celery Queue để xử lý bất đồng bộ
    task = celery_app.send_task(
        "worker.tasks.analysis_tasks.run_gap_analysis",
        args=[str(user_id), str(req.cv_id), str(req.job_id) if req.job_id else None, req.jd_text]
    )
    
    return {"task_id": task.id, "status": "processing"}

@app.get("/analysis/status/{task_id}")
async def get_task_status(task_id: str):
    res = AsyncResult(task_id, app=celery_app)
    
    if res.ready():
        result = res.result
        if isinstance(result, dict) and "error" in result:
             raise HTTPException(status_code=500, detail=result["error"])
        return {
            "status": "completed",
            "result": result
        }
    
    return {"status": "processing"}

@app.get("/analysis/user/latest")
async def get_latest_analysis(request: Request, db: Session = Depends(get_db)):
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    # Tìm kết quả phân tích gần đây nhất của người dùng này
    analysis = db.query(UserAnalysis)\
        .filter(UserAnalysis.user_id == uuid.UUID(user_id))\
        .order_by(UserAnalysis.created_at.desc())\
        .first()
        
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis report found for this user. Please upload a CV first.")
        
    return analysis.result_json

@app.get("/analysis/user/cv/{cv_id}")
async def get_cv_analysis(cv_id: str, request: Request, db: Session = Depends(get_db)):
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    analysis = db.query(UserAnalysis)\
        .filter(UserAnalysis.user_id == uuid.UUID(user_id), UserAnalysis.cv_id == uuid.UUID(cv_id))\
        .order_by(UserAnalysis.created_at.desc())\
        .first()
        
    if not analysis:
        # Nếu chưa có bản lưu, chúng ta có thể trigger phân tích ở đây 
        # nhưng tốt nhất là trả về 404 để frontend xử lý (ví dụ: hiển thị nút 'Analyze Now')
        raise HTTPException(status_code=404, detail="No analysis found for this specific CV")
        
    return analysis.result_json

# --- ADMIN TAXONOMY ROUTES ---

def check_admin(request: Request):
    if request.headers.get("X-Is-Admin") != "true":
        raise HTTPException(status_code=403, detail="Admin privileges required")

@app.get("/analysis/admin/taxonomy/skills")
async def get_taxonomy_skills(request: Request, limit: int = 100, skip: int = 0):
    check_admin(request)
    return taxonomy_service.get_all_skills(limit, skip)

@app.post("/analysis/admin/taxonomy/skills")
async def manage_skill(skill: SkillCreate, request: Request):
    check_admin(request)
    result = taxonomy_service.create_or_update_skill(
        name=skill.name,
        category=skill.category,
        skill_type=skill.type,
        aliases=skill.aliases
    )
    return {"message": "Skill managed successfully", "name": skill.name}

@app.delete("/analysis/admin/taxonomy/skills/{name}")
async def delete_skill(name: str, request: Request):
    check_admin(request)
    taxonomy_service.delete_skill(name)
    return {"message": f"Skill {name} deleted"}

@app.post("/analysis/admin/taxonomy/link")
async def link_skills(req: LinkRequest, request: Request):
    check_admin(request)
    taxonomy_service.link_skills(req.parent, req.child, req.rel_type)
    return {"message": f"Linked {req.parent} to {req.child} via {req.rel_type}"}

@app.get("/analysis/admin/taxonomy/relationships/grouped")
async def get_relationships_grouped(request: Request, limit: int = 200, type: Optional[str] = None):
    check_admin(request)
    return taxonomy_service.get_relationships_grouped(limit, parent_type=type)

@app.get("/analysis/admin/taxonomy/relationships")
async def get_relationships(request: Request, limit: int = 100):
    check_admin(request)
    return taxonomy_service.get_all_relationships(limit)

@app.delete("/analysis/admin/taxonomy/relationships")
async def delete_relationship(parent: str, child: str, rel_type: str, request: Request):
    check_admin(request)
    taxonomy_service.delete_relationship(parent, child, rel_type)
    return {"message": f"Relationship {rel_type} between {parent} and {child} deleted"}

class FeedbackRequest(BaseModel):
    analysis_id: str
    rating: int
    is_accurate: bool
    missing_skills: list = []
    comment: Optional[str] = None

class SimulateRequest(BaseModel):
    cv_id: uuid.UUID
    selected_course_ids: List[uuid.UUID]
    job_id: Optional[uuid.UUID] = None

@app.post("/analysis/feedback")
def submit_feedback(req: FeedbackRequest, request: Request, db: Session = Depends(get_db)):
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    from shared.models import UserFeedback
    fb = UserFeedback(
        user_id=uuid.UUID(user_id),
        analysis_id=req.analysis_id,
        rating=req.rating,
        is_accurate=req.is_accurate,
        missing_skills=req.missing_skills,
        comment=req.comment
    )
    db.add(fb)
    db.commit()
    return {"message": "Feedback submitted successfully"}

@app.get("/analysis/market-fit")
def get_market_fit(request: Request, db: Session = Depends(get_db)):
    user_id = request.headers.get("X-User-ID")
    if not user_id:
         raise HTTPException(status_code=401, detail="User not authenticated")
    
    from sqlalchemy import text
    query = text("""
        SELECT COUNT(*) FILTER (WHERE match_pct >= 70) AS matched_jobs,
               COUNT(*) AS total_jobs,
               ROUND(COUNT(*) FILTER (WHERE match_pct >= 70)::numeric / GREATEST(COUNT(*), 1) * 100, 1) AS market_fit_pct
        FROM (
            SELECT jsr.job_id,
                SUM(CASE WHEN usp.skill_id IS NOT NULL THEN jsr.importance_weight ELSE 0 END) * 100.0 / NULLIF(SUM(jsr.importance_weight), 0) AS match_pct
            FROM job_skill_requirement jsr
            JOIN jobs j ON j.id = jsr.job_id AND j.status = 'active'
            LEFT JOIN user_skill_profile usp ON usp.skill_id = jsr.skill_id AND usp.user_id = :user_id
            GROUP BY jsr.job_id
        ) sub;
    """)
    res = db.execute(query, {"user_id": user_id}).fetchone()
    
    top_roles_query = text("""
        SELECT j.title_category, COUNT(j.id) as count
        FROM job_skill_requirement jsr
        JOIN jobs j ON j.id = jsr.job_id AND j.status = 'active'
        JOIN user_skill_profile usp ON usp.skill_id = jsr.skill_id AND usp.user_id = :user_id
        GROUP BY j.id, j.title_category
        HAVING SUM(jsr.importance_weight) > 0
        ORDER BY count DESC
        LIMIT 3
    """)
    roles = db.execute(top_roles_query, {"user_id": user_id}).fetchall()
    top_roles = [r.title_category for r in roles if r.title_category]
    
    return {
        "user_id": user_id,
        "market_fit_pct": float(res.market_fit_pct) if res and res.market_fit_pct else 0.0,
        "matched_jobs": res.matched_jobs if res else 0,
        "total_jobs": res.total_jobs if res else 0,
        "top_matching_roles": top_roles
    }

@app.post("/analysis/simulate")
async def simulate_roadmap(req: SimulateRequest, request: Request, db: Session = Depends(get_db)):
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    from shared.models import Course
    
    courses = db.query(Course).filter(Course.id.in_(req.selected_course_ids)).all()
    if not courses:
        raise HTTPException(status_code=404, detail="Courses not found")
        
    gained_skills = []
    total_hours = 0.0
    for c in courses:
        total_hours += c.duration_hours or 0.0
        if c.tags:
            gained_skills.extend(c.tags)
            
    # Chuyển đổi thành string list duy nhất
    unique_skills = list(set(gained_skills))
    
    roadmap_stages = []
    if courses:
        stage1_skills = list(set(courses[0].tags)) if courses[0].tags else []
        roadmap_stages.append({
            "stage": 1,
            "focus": courses[0].title,
            "courses": [courses[0].title],
            "skills_acquired": stage1_skills
        })
        if len(courses) > 1:
            stage2_skills = []
            for c in courses[1:]:
                if c.tags: stage2_skills.extend(c.tags)
            roadmap_stages.append({
                "stage": 2,
                "focus": "Nâng cao kỹ năng / Thực hành",
                "courses": [c.title for c in courses[1:]],
                "skills_acquired": list(set(stage2_skills))
            })

    return {
        "virtual_skills_gained": unique_skills,
        "estimated_duration_hours": total_hours,
        "estimated_duration_weeks": round(total_hours / 10), 
        "projected_market_fit_pct": 75.0, 
        "projected_jd_match_pct": 82.5 if req.job_id else None,
        "roadmap_stages": roadmap_stages
    }

