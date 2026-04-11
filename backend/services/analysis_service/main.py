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

@app.get("/analysis/market-fit")
def get_market_fit(request: Request, db: Session = Depends(get_db)):
    user_id = request.headers.get("X-User-ID")
    return {
        "user_id": user_id,
        "market_fit_pct": 65.5,
        "top_matching_roles": ["Backend Developer", "DevOps Engineer"]
    }
