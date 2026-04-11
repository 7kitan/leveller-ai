from fastapi import FastAPI, Depends, HTTPException, Request, UploadFile, File
from sqlalchemy.orm import Session
from shared.database import get_db
from shared.models import User, UserCV, UserSkillProfile, Skill
from worker.celery_app import celery_app
import uuid
import os
import hashlib
import logging
from typing import List, Optional
from pydantic import BaseModel

class SkillCreate(BaseModel):
    skill_name: str
    years_exp: float = 0.0
    level: str = "Mid-level"
    category: Optional[str] = "Other"

class SkillUpdate(BaseModel):
    years_exp: Optional[float] = None
    level: Optional[str] = None

class CVUpdate(BaseModel):
    full_name: Optional[str] = None
    summary: Optional[str] = None
    experience_years_total: Optional[float] = None

app = FastAPI(title="CV Service")

UPLOAD_DIR = "/app/data/cv_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

logger = logging.getLogger("cv_service")

def calculate_file_hash(file_content: bytes) -> str:
    """Tính SHA256 hash của nội dung file."""
    return hashlib.sha256(file_content).hexdigest()

def is_admin(request: Request) -> bool:
    return request.headers.get("X-Is-Admin") == "true"

@app.post("/cv/upload")
async def upload_cv(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    user_id_str = request.headers.get("X-User-ID")
    is_admin_header = request.headers.get("X-Is-Admin")
    
    logger.info(f"DEBUG CV_SERVICE [upload_cv]: Received X-User-ID={user_id_str}, X-Is-Admin={is_admin_header}")
    
    if not user_id_str:
        logger.error("DEBUG CV_SERVICE: Authentication failed - X-User-ID header is missing.")
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    user_id = uuid.UUID(user_id_str)
    file_content = await file.read()
    file_hash = calculate_file_hash(file_content)

    existing_cv = db.query(UserCV).filter(UserCV.user_id == user_id, UserCV.file_hash == file_hash).first()
    if existing_cv:
        return {"cv_id": str(existing_cv.id), "status": existing_cv.status, "is_duplicate": True}

    cv_id = uuid.uuid4()
    file_ext = file.filename.split(".")[-1]
    file_path = os.path.join(UPLOAD_DIR, f"{cv_id}.{file_ext}")

    with open(file_path, "wb") as buffer:
        buffer.write(file_content)

    new_cv = UserCV(id=cv_id, user_id=user_id, file_id=str(cv_id), file_hash=file_hash, status="processing")
    db.add(new_cv)
    db.commit()

    celery_app.send_task("worker.tasks.parse_cv_task.parse_cv", args=[str(user_id), str(cv_id), file_path])
    return {"cv_id": str(cv_id), "status": "processing"}

@app.get("/cv/list")
async def list_user_cvs(request: Request, db: Session = Depends(get_db)):
    user_id_str = request.headers.get("X-User-ID")
    logger.info(f"DEBUG CV_SERVICE [cv_list]: Received X-User-ID={user_id_str}")
    
    if not user_id_str: 
        logger.error("DEBUG CV_SERVICE: Authentication failed - X-User-ID header is missing.")
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    user_id = uuid.UUID(user_id_str)
    cvs = db.query(UserCV).filter(UserCV.user_id == user_id).order_by(UserCV.created_at.desc()).all()
    return [{"id": str(cv.id), "full_name": cv.full_name, "status": cv.status, "error_message": cv.error_message, "created_at": cv.created_at} for cv in cvs]

@app.get("/cv/admin/all")
async def admin_list_all_cvs(request: Request, db: Session = Depends(get_db)):
    """Admin only: Lấy tất cả CV của toàn hệ thống."""
    if not is_admin(request):
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    # Query all CVs and join with User to get email
    results = db.query(UserCV, User.email).join(User, UserCV.user_id == User.id).order_by(UserCV.created_at.desc()).all()
    
    return [
        {
            "id": str(cv.id),
            "user_email": email,
            "full_name": cv.full_name,
            "status": cv.status,
            "created_at": cv.created_at
        }
        for cv, email in results
    ]

@app.delete("/cv/{cv_id}")
async def delete_cv(cv_id: str, request: Request, db: Session = Depends(get_db)):
    """Xóa CV (Admin hoặc Owner)."""
    user_id_str = request.headers.get("X-User-ID")
    logger.info(f"DEBUG CV_SERVICE [delete_cv]: cv_id={cv_id}, X-User-ID={user_id_str}, X-Is-Admin={request.headers.get('X-Is-Admin')}")
    
    if not user_id_str: 
        logger.error("DEBUG CV_SERVICE: Authentication failed - X-User-ID header is missing.")
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    cv_uuid = uuid.UUID(cv_id)
    cv = db.query(UserCV).filter(UserCV.id == cv_uuid).first()
    if not cv: raise HTTPException(status_code=404, detail="CV not found")

    # Quyền xóa: Admin hoặc Chủ sở hữu
    if not is_admin(request) and str(cv.user_id) != user_id_str:
        raise HTTPException(status_code=403, detail="Not authorized to delete this CV")

    # Xóa file vật lý nếu tồn tại
    # Lưu ý: Trong thực tế nên xóa cả trong Storage (MinIO)
    try:
        # Tìm file có ID tương ứng trong UPLOAD_DIR
        for filename in os.listdir(UPLOAD_DIR):
            if filename.startswith(str(cv.id)):
                os.remove(os.path.join(UPLOAD_DIR, filename))
                break
    except Exception as e:
        logger.error(f"Error deleting physical file: {e}")

    db.delete(cv)
    db.commit()
    return {"message": "Successfully deleted CV and associated data."}

@app.patch("/cv/{cv_id}")
async def update_cv_metadata(cv_id: str, payload: CVUpdate, request: Request, db: Session = Depends(get_db)):
    """Cập nhật thông tin cơ bản của CV."""
    user_id_str = request.headers.get("X-User-ID")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Authentication required")
        
    cv = db.query(UserCV).filter(UserCV.id == uuid.UUID(cv_id)).first()
    if not cv: raise HTTPException(status_code=404, detail="CV not found")
    
    if not is_admin(request) and str(cv.user_id) != user_id_str:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    if payload.full_name is not None: cv.full_name = payload.full_name
    if payload.summary is not None: cv.summary = payload.summary
    if payload.experience_years_total is not None: cv.experience_years_total = payload.experience_years_total
    
    db.commit()
    return {"message": "CV updated successfully", "cv": {"full_name": cv.full_name, "experience_years_total": cv.experience_years_total}}

@app.get("/cv/{cv_id}")
async def get_cv_detail(cv_id: str, db: Session = Depends(get_db)):
    cv_uuid = uuid.UUID(cv_id)
    cv = db.query(UserCV).filter(UserCV.id == cv_uuid).first()
    if not cv: raise HTTPException(status_code=404, detail="CV not found")
    
    skills_profiles = db.query(UserSkillProfile, Skill.name, Skill.category)\
        .join(Skill, UserSkillProfile.skill_id == Skill.id)\
        .filter(UserSkillProfile.cv_id == cv.id).all()
    
    return {
        "id": str(cv.id),
        "full_name": cv.full_name,
        "summary": cv.summary,
        "experience_years_total": cv.experience_years_total,
        "status": cv.status,
        "error_message": cv.error_message,
        "skills": [
            {
                "id": str(sp.id),
                "skill_id": str(sp.skill_id),
                "name": n,
                "category": c,
                "years_exp": sp.years_exp,
                "level": sp.level
            } for sp, n, c in skills_profiles
        ],
        "created_at": cv.created_at
    }

@app.post("/cv/{cv_id}/skills")
async def add_cv_skill(cv_id: str, payload: SkillCreate, request: Request, db: Session = Depends(get_db)):
    user_id_str = request.headers.get("X-User-ID")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Authentication required")
        
    cv = db.query(UserCV).filter(UserCV.id == uuid.UUID(cv_id)).first()
    if not cv: raise HTTPException(status_code=404, detail="CV not found")
    if not is_admin(request) and str(cv.user_id) != user_id_str:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    s_name = payload.skill_name.strip()
    if not s_name: raise HTTPException(status_code=400, detail="Skill name cannot be empty")
    s_name_cap = s_name.title() if len(s_name) > 3 else s_name.upper()
    
    skill = db.query(Skill).filter(Skill.name.ilike(s_name)).first()
    if not skill:
        skill = Skill(id=uuid.uuid4(), name=s_name_cap, category=payload.category)
        db.add(skill)
        db.commit()
        db.refresh(skill)
        
    existing = db.query(UserSkillProfile).filter(UserSkillProfile.cv_id == cv.id, UserSkillProfile.skill_id == skill.id).first()
    if existing:
        existing.years_exp = payload.years_exp
        existing.level = payload.level
    else:
        new_prof = UserSkillProfile(
            id=uuid.uuid4(),
            user_id=cv.user_id, 
            cv_id=cv.id,
            skill_id=skill.id,
            years_exp=payload.years_exp,
            level=payload.level,
            source="manual"
        )
        db.add(new_prof)
    
    db.commit()
    return {"message": "Skill added successfully"}

@app.put("/cv/{cv_id}/skills/{profile_id}")
async def update_cv_skill(cv_id: str, profile_id: str, payload: SkillUpdate, request: Request, db: Session = Depends(get_db)):
    user_id_str = request.headers.get("X-User-ID")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Authentication required")
        
    cv = db.query(UserCV).filter(UserCV.id == uuid.UUID(cv_id)).first()
    if not cv: raise HTTPException(status_code=404, detail="CV not found")
    if not is_admin(request) and str(cv.user_id) != user_id_str:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    prof = db.query(UserSkillProfile).filter(UserSkillProfile.id == uuid.UUID(profile_id), UserSkillProfile.cv_id == cv.id).first()
    if not prof: raise HTTPException(status_code=404, detail="Skill profile not found")
    
    if payload.years_exp is not None: prof.years_exp = payload.years_exp
    if payload.level: prof.level = payload.level
    
    db.commit()
    return {"message": "Skill updated successfully"}

@app.delete("/cv/{cv_id}/skills/{profile_id}")
async def delete_cv_skill(cv_id: str, profile_id: str, request: Request, db: Session = Depends(get_db)):
    user_id_str = request.headers.get("X-User-ID")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Authentication required")
        
    cv = db.query(UserCV).filter(UserCV.id == uuid.UUID(cv_id)).first()
    if not cv: raise HTTPException(status_code=404, detail="CV not found")
    if not is_admin(request) and str(cv.user_id) != user_id_str:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    prof = db.query(UserSkillProfile).filter(UserSkillProfile.id == uuid.UUID(profile_id), UserSkillProfile.cv_id == cv.id).first()
    if not prof: raise HTTPException(status_code=404, detail="Skill profile not found")
    
    db.delete(prof)
    db.commit()
    return {"message": "Skill deleted successfully"}

@app.get("/cv/status/{task_id}")
async def get_cv_status(task_id: str):
    task_result = celery_app.AsyncResult(task_id)
    return {"task_id": task_id, "status": task_result.status, "result": task_result.result if task_result.ready() else None}
