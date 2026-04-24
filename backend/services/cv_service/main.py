from fastapi import FastAPI, Depends, HTTPException, Request, UploadFile, File, Query
from sqlalchemy.orm import Session
from shared.database import get_db
from shared.models import User, UserCV, UserSkillProfile, Skill, UserAnalysis, UserWorkExperience
from worker.celery_app import celery_app
from shared.redis_client import result_cache
from shared.schemas import PaginatedResponse
import uuid
import json
import os
import hashlib
import logging
import re
import magic
from typing import List, Optional
from pydantic import BaseModel

# SECURITY: File upload constraints
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png'}
ALLOWED_MIME_TYPES = {
    'application/pdf',
    'image/jpeg',
    'image/png'
}


class SkillCreate(BaseModel):
    skill_name: str
    years_exp: float = 0.0
    level: str = "Junior"
    category: Optional[str] = "Other"


class SkillUpdate(BaseModel):
    years_exp: Optional[float] = None
    level: Optional[str] = None


class CVUpdate(BaseModel):
    full_name: Optional[str] = None
    summary: Optional[str] = None
    experience_years_total: Optional[float] = None


class FinalizeCVRequest(BaseModel):
    id: str
    full_name: str
    summary: Optional[str] = ""
    experience_years_total: float = 0.0
    skills: List[dict] = []
    work_history: Optional[List[dict]] = []
    education: Optional[List[dict]] = []
    certifications: Optional[List[str]] = []
    seniority: Optional[str] = "Unknown"
    
    # ── Security Validation (Spec 5) ────────────
    from pydantic import validator
    
    @validator("full_name")
    def validate_name(cls, v):
        if len(v) < 2:
            raise ValueError("Tên quá ngắn")
        if len(v) > 255:
            raise ValueError("Tên quá dài")
        # Simple sanitization
        return v.strip().replace("<", "&lt;").replace(">", "&gt;")

    @validator("experience_years_total")
    def validate_exp(cls, v):
        if v < 0 or v > 60:
            raise ValueError("Số năm kinh nghiệm không hợp lệ (0-60)")
        return v


app = FastAPI(title="CV Service")

UPLOAD_DIR = "/app/data/cv_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

logger = logging.getLogger("cv_service")


def calculate_file_hash(file_content: bytes) -> str:
    """Tính SHA256 hash của nội dung file."""
    return hashlib.sha256(file_content).hexdigest()


def validate_uploaded_file(file: UploadFile, file_content: bytes) -> None:
    """
    SECURITY: Validate uploaded file for security threats
    - Check file size
    - Validate file extension
    - Sanitize filename to prevent path traversal
    """
    # Check file size
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"File quá lớn. Kích thước tối đa: {MAX_FILE_SIZE / (1024*1024):.0f}MB"
        )
    
    # Validate filename exists
    if not file.filename:
        raise HTTPException(status_code=400, detail="Tên file không hợp lệ")
    
    # SECURITY: Check for path traversal attempts and null bytes (Spec 5)
    if ".." in file.filename or "/" in file.filename or "\\" in file.filename:
        logger.warning(f"Path traversal attempt detected in filename: {file.filename}")
        raise HTTPException(status_code=400, detail="Tên file chứa ký tự không hợp lệ")
    
    # Check file extension
    filename = os.path.basename(file.filename)
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Định dạng file không được hỗ trợ. Chỉ chấp nhận: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Validate content type using magic bytes (deep check)
    try:
        mime = magic.from_buffer(file_content, mime=True)
        if mime not in ALLOWED_MIME_TYPES:
            logger.warning(f"File content type mismatch: detected {mime}, expected one of {ALLOWED_MIME_TYPES}")
            raise HTTPException(
                status_code=400,
                detail="Nội dung file không hợp lệ hoặc định dạng không được hỗ trợ."
            )
    except Exception as e:
        if isinstance(e, HTTPException): raise
        logger.error(f"Error during magic byte validation: {e}")
        # Fallback to basic check if magic fails
        if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
             raise HTTPException(status_code=400, detail="Định dạng file không hợp lệ")

    # Check for null bytes (potential attack)
    if b'\x00' in file_content[:1024]:  # Check first 1KB
        raise HTTPException(status_code=400, detail="File chứa dữ liệu không hợp lệ")


def is_admin(request: Request) -> bool:
    return request.headers.get("X-Is-Admin") == "true"


@app.post("/cv/upload")
async def upload_cv(
    request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)
):
    user_id_str = request.headers.get("X-User-ID")
    is_admin_header = request.headers.get("X-Is-Admin")

    logger.info(
        f"DEBUG CV_SERVICE [upload_cv]: Received X-User-ID={user_id_str}, X-Is-Admin={is_admin_header}"
    )

    if not user_id_str:
        logger.error(
            "DEBUG CV_SERVICE: Authentication failed - X-User-ID header is missing."
        )
        raise HTTPException(status_code=401, detail="User not authenticated")

    user_id = uuid.UUID(user_id_str)
    file_content = await file.read()
    
    # SECURITY: Validate file before processing
    validate_uploaded_file(file, file_content)
    
    file_hash = calculate_file_hash(file_content)

    existing_cv = (
        db.query(UserCV)
        .filter(UserCV.user_id == user_id, UserCV.file_hash == file_hash)
        .first()
    )
    if existing_cv:
        resp = {
            "cv_id": str(existing_cv.id),
            "status": existing_cv.status,
            "is_duplicate": True,
        }
        if existing_cv.status == "completed":
            # Duplicate CV đã parse xong → trả về data luôn để frontend hiển thị
            cv_parsed = getattr(existing_cv, "cv_parsed_json", None)
            is_ocr = cv_parsed.get("is_ocr", False) if cv_parsed else False
            skills_profiles = (
                db.query(UserSkillProfile, Skill.name, Skill.category)
                .join(Skill, UserSkillProfile.skill_id == Skill.id)
                .filter(UserSkillProfile.cv_id == existing_cv.id)
                .all()
            )
            resp["parser_id"] = None
            resp["full_name"] = existing_cv.full_name
            resp["result"] = {
                "id": str(existing_cv.id),
                "full_name": existing_cv.full_name or "Parsed Candidate",
                "summary": existing_cv.summary or "",
                "experience_years_total": existing_cv.experience_years_total or 0,
                "status": existing_cv.status,
                "skills": [
                    {
                        "id": str(sp.id),
                        "skill_id": str(sp.skill_id),
                        "name": n,
                        "category": c,
                        "experience_years": sp.years_exp,
                    }
                    for sp, n, c in skills_profiles
                ],
                "is_ocr": is_ocr,
                "cv_parsed": cv_parsed,
                "work_history": cv_parsed.get("work_history", []) if cv_parsed else [],
                "education": cv_parsed.get("education", []) if cv_parsed else [],
                "certifications": cv_parsed.get("certifications", [])
                if cv_parsed
                else [],
                "seniority": cv_parsed.get("seniority", "Unknown")
                if cv_parsed
                else "Unknown",
                "ocr_confidence": cv_parsed.get("ocr_confidence", 1.0)
                if cv_parsed
                else 1.0,
            }
        return resp

    cv_id = uuid.uuid4()
    # SECURITY: Use sanitized filename extension only, generate new name with UUID
    file_ext = os.path.splitext(os.path.basename(file.filename))[1].lower()
    file_path = os.path.join(UPLOAD_DIR, f"{cv_id}{file_ext}")

    with open(file_path, "wb") as buffer:
        buffer.write(file_content)

    new_cv = UserCV(
        id=cv_id,
        user_id=user_id,
        file_id=str(cv_id),
        file_hash=file_hash,
        status="processing",
    )
    db.add(new_cv)
    db.commit()

    # Feature flag: USE_LLM_GAP_AGENT_V3=true → v3 (LLM structured parse), false → legacy
    use_v3 = os.getenv("USE_LLM_GAP_AGENT_V3", "true").lower() == "true"

    if use_v3:
        task = celery_app.send_task(
            "worker.tasks.cv_parsing_v3_task.run_cv_parsing",
            args=[str(cv_id), str(user_id)],  # cv_id trước, user_id sau
        )
    else:
        task = celery_app.send_task(
            "worker.tasks.parse_cv_task.parse_cv",
            args=[str(user_id), str(cv_id), file_path],
        )

    return {"cv_id": str(cv_id), "parser_id": task.id, "status": "processing"}


@app.get("/cv/list")
async def list_user_cvs(request: Request, db: Session = Depends(get_db)):
    user_id_str = request.headers.get("X-User-ID")
    logger.info(f"DEBUG CV_SERVICE [cv_list]: Received X-User-ID={user_id_str}")

    if not user_id_str:
        logger.error(
            "DEBUG CV_SERVICE: Authentication failed - X-User-ID header is missing."
        )
        raise HTTPException(status_code=401, detail="User not authenticated")

    user_id = uuid.UUID(user_id_str)
    cvs = (
        db.query(UserCV)
        .filter(UserCV.user_id == user_id)
        .order_by(UserCV.created_at.desc())
        .all()
    )
    return [
        {
            "id": str(cv.id),
            "file_name": cv.full_name or f"CV_{str(cv.id)[:8]}",
            "full_name": cv.full_name,
            "status": cv.status,
            "error_message": cv.error_message,
            "created_at": cv.created_at,
        }
        for cv in cvs
    ]


@app.post("/cv/finalize")
async def finalize_cv(
    req: FinalizeCVRequest, request: Request, db: Session = Depends(get_db)
):
    """
    Spec 1.9: Lưu kết quả bóc tách kĩ năng vào profile người dùng.
    Duyệt qua danh sách kĩ năng đã parser và lưu vào UserSkillProfile.
    """
    user_id_str = request.headers.get("X-User-ID")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Not authenticated")

    cv_uuid = uuid.UUID(req.id)
    cv = db.query(UserCV).filter(UserCV.id == cv_uuid).first()
    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")

    # Kiểm tra quyền sở hữu
    if str(cv.user_id) != user_id_str:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Cập nhật metadata CV (Direct fields)
    cv.full_name = req.full_name
    cv.summary = req.summary.replace("<", "&lt;").replace(">", "&gt;") if req.summary else ""
    cv.experience_years_total = req.experience_years_total
    cv.is_verified = True
    
    # Explicitly update timestamp to invalidate gap analysis cache
    from sqlalchemy import func
    cv.cv_parsed_at = func.now()

    # Cập nhật cv_parsed_json để đồng bộ dữ liệu (Work history, education, certifications)
    # Spec 3.3: Link Radar Chart data to recommended courses
    current_json = cv.cv_parsed_json or {}
    current_json["full_name"] = req.full_name
    current_json["summary"] = cv.summary
    current_json["experience_years_total"] = req.experience_years_total
    current_json["work_history"] = req.work_history
    current_json["education"] = req.education
    current_json["certifications"] = req.certifications
    current_json["seniority"] = req.seniority
    # Sync simple skill names list if needed by other services
    current_json["skills"] = [s.get("name") for s in req.skills]
    
    cv.cv_parsed_json = current_json

    # Cập nhật danh sách skills (Detailed UserSkillProfile)
    # 1. Xóa skills cũ của CV này để ghi đè (Finalize)
    db.query(UserSkillProfile).filter(UserSkillProfile.cv_id == cv.id).delete()

    # 2. Lọc duplicate skills trước khi thêm (Server-side validation)
    seen_skills = set()
    unique_skills = []
    for s_data in req.skills:
        s_name_raw = s_data.get("name", "").strip().lower()
        if not s_name_raw or s_name_raw in seen_skills:
            continue
        seen_skills.add(s_name_raw)
        unique_skills.append(s_data)

    # 3. Thêm skills mới
    for s_data in unique_skills:
        s_name = s_data.get("name", "").strip()
        if not s_name:
            continue

        # Chuẩn hóa tên kĩ năng (Sanitize)
        s_name = s_name.replace("<", "").replace(">", "")
        s_name_std = s_name.title() if len(s_name) > 3 else s_name.upper()

        # Tìm hoặc tạo kĩ năng trong taxonomy
        skill = db.query(Skill).filter(Skill.name.ilike(s_name)).first()
        if not skill:
            # Normalize category to English for DB consistency
            raw_cat = (s_data.get("category") or "Technology").strip()
            if raw_cat.lower() == "công nghệ":
                raw_cat = "Technology"

            skill = Skill(
                id=uuid.uuid4(),
                name=s_name_std,
                category=raw_cat,
            )
            db.add(skill)
            db.commit()
            db.refresh(skill)

        new_prof = UserSkillProfile(
            id=uuid.uuid4(),
            user_id=cv.user_id,
            cv_id=cv.id,
            skill_id=skill.id,
            years_exp=float(s_data.get("experience_years", 0)),
            level=s_data.get("level", "Junior"),
            source="cv_parsed",
        )
        db.add(new_prof)

    # 4. Cập nhật danh sách work_history (UserWorkExperience table)
    # Xóa work experiences cũ của CV này để ghi đè
    db.query(UserWorkExperience).filter(UserWorkExperience.cv_id == cv.id).delete()
    
    for w_data in (req.work_history or []):
        new_work = UserWorkExperience(
            id=uuid.uuid4(),
            cv_id=cv.id,
            position_name=w_data.get("position", "N/A"),
            company_name=w_data.get("company", "N/A"),
            duration_years=float(w_data.get("duration_years") or 0),
            description=w_data.get("description", "")
        )
        db.add(new_work)

    db.commit()
    logger.info(f"CV Fully Finalized: {cv.id} for user {user_id_str}")
    return {"message": "Portfolio updated successfully with full validation", "cv_id": str(cv.id)}


@app.get("/cv/admin/all", response_model=PaginatedResponse[dict])
async def admin_list_all_cvs(
    request: Request, 
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(None)
):
    """Admin only: Lấy tất cả CV của toàn hệ thống với phân trang."""
    if not is_admin(request):
        raise HTTPException(status_code=403, detail="Admin privileges required")

    query = db.query(UserCV, User.email).join(User, UserCV.user_id == User.id)
    
    if q:
        query = query.filter(
            (UserCV.full_name.ilike(f"%{q}%")) | (User.email.ilike(f"%{q}%"))
        )

    total = query.count()
    results = query.order_by(UserCV.created_at.desc()).offset(offset).limit(limit).all()

    items = [
        {
            "id": str(cv.id),
            "user_email": email,
            "full_name": cv.full_name,
            "status": cv.status,
            "created_at": cv.created_at,
        }
        for cv, email in results
    ]
    
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "page": (offset // limit) + 1,
        "pages": (total + limit - 1) // limit
    }


@app.delete("/cv/{cv_id}")
async def delete_cv(cv_id: str, request: Request, db: Session = Depends(get_db)):
    """Xóa CV (Admin hoặc Owner)."""
    user_id_str = request.headers.get("X-User-ID")
    logger.info(
        f"DEBUG CV_SERVICE [delete_cv]: cv_id={cv_id}, X-User-ID={user_id_str}, X-Is-Admin={request.headers.get('X-Is-Admin')}"
    )

    if not user_id_str:
        logger.error(
            "DEBUG CV_SERVICE: Authentication failed - X-User-ID header is missing."
        )
        raise HTTPException(status_code=401, detail="Not authenticated")

    cv_uuid = uuid.UUID(cv_id)
    cv = db.query(UserCV).filter(UserCV.id == cv_uuid).first()
    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")

    # Quyền xóa: Admin hoặc Chủ sở hữu
    if not is_admin(request) and str(cv.user_id) != user_id_str:
        raise HTTPException(status_code=403, detail="Not authorized to delete this CV")

    # Xóa file vật lý trong Local Storage
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
async def update_cv_metadata(
    cv_id: str, payload: CVUpdate, request: Request, db: Session = Depends(get_db)
):
    """Cập nhật thông tin cơ bản của CV."""
    user_id_str = request.headers.get("X-User-ID")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Authentication required")

    cv = db.query(UserCV).filter(UserCV.id == uuid.UUID(cv_id)).first()
    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")

    if not is_admin(request) and str(cv.user_id) != user_id_str:
        raise HTTPException(status_code=403, detail="Not authorized")

    if payload.full_name is not None:
        cv.full_name = payload.full_name
    if payload.summary is not None:
        cv.summary = payload.summary
    if payload.experience_years_total is not None:
        cv.experience_years_total = payload.experience_years_total

    db.commit()
    return {
        "message": "CV updated successfully",
        "cv": {
            "full_name": cv.full_name,
            "experience_years_total": cv.experience_years_total,
        },
    }


@app.get("/cv/{cv_id}")
async def get_cv_detail(cv_id: str, request: Request, db: Session = Depends(get_db)):
    """
    Lấy chi tiết CV bao gồm cả:
    - Thông tin cơ bản
    - Skills từ DB
    - Structured CV parsed data (cv_parsed_json)
    - Transparency: is_ocr flag + ocr_confidence + cảnh báo
    """
    cv_uuid = uuid.UUID(cv_id)
    cv = db.query(UserCV).filter(UserCV.id == cv_uuid).first()
    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")

    # Authorization
    user_id_str = request.headers.get("X-User-ID")
    if not is_admin(request) and user_id_str and str(cv.user_id) != user_id_str:
        raise HTTPException(status_code=403, detail="Not authorized")

    skills_profiles = (
        db.query(UserSkillProfile, Skill.name, Skill.category)
        .join(Skill, UserSkillProfile.skill_id == Skill.id)
        .filter(UserSkillProfile.cv_id == cv.id)
        .all()
    )

    # Lấy structured parsed data (v3)
    cv_parsed = getattr(cv, "cv_parsed_json", None)

    # Transparency: kiểm tra CV có phải từ OCR không
    is_ocr = cv_parsed.get("is_ocr", False) if cv_parsed else False
    ocr_confidence = cv_parsed.get("ocr_confidence", 1.0) if cv_parsed else 1.0

    response = {
        "id": str(cv.id),
        "full_name": cv.full_name,
        "summary": cv.summary,
        "experience_years_total": cv.experience_years_total,
        "is_verified": cv.is_verified,
        "status": cv.status,
        "error_message": cv.error_message,
        "user_info": {
            "full_name": cv.full_name or "Parsed Candidate",
            "total_exp_years": cv.experience_years_total or 0,
        },
        "skills": [
            {
                "id": str(sp.id),
                "skill_id": str(sp.skill_id),
                "name": n,
                "category": c,
                "experience_years": sp.years_exp,  # Map years_exp to experience_years for frontend
                "years_exp": sp.years_exp,
                "level": sp.level,
            }
            for sp, n, c in skills_profiles
        ],
        "created_at": cv.created_at,
        # ── Transparency (3.2) ────────────────────────────────────────────
        "is_ocr": is_ocr,
        "ocr_confidence": ocr_confidence,
        "ocr_warning": (
            "⚠️ CV này được xử lý từ ảnh/scan. "
            "Độ chính xác có thể không đảm bảo 100%. "
            "Vui lòng kiểm tra lại thông tin."
            if is_ocr and ocr_confidence < 0.8
            else (
                "⚠️ CV này được xử lý từ ảnh/scan. Vui lòng kiểm tra lại thông tin."
                if is_ocr
                else None
            )
        ),
        "cv_parsed": cv_parsed,  # Structured CV data (v3)
        # Work history từ cv_parsed (nếu có)
        "work_history": cv_parsed.get("work_history", []) if cv_parsed else [],
        "education": cv_parsed.get("education", []) if cv_parsed else [],
        "certifications": cv_parsed.get("certifications", []) if cv_parsed else [],
        "seniority": cv_parsed.get("seniority", "Unknown") if cv_parsed else "Unknown",
    }

    return response


@app.post("/cv/{cv_id}/skills")
async def add_cv_skill(
    cv_id: str, payload: SkillCreate, request: Request, db: Session = Depends(get_db)
):
    user_id_str = request.headers.get("X-User-ID")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Authentication required")

    cv = db.query(UserCV).filter(UserCV.id == uuid.UUID(cv_id)).first()
    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")
    if not is_admin(request) and str(cv.user_id) != user_id_str:
        raise HTTPException(status_code=403, detail="Not authorized")

    s_name = payload.skill_name.strip()
    if not s_name:
        raise HTTPException(status_code=400, detail="Skill name cannot be empty")
    s_name_cap = s_name.title() if len(s_name) > 3 else s_name.upper()

    skill = db.query(Skill).filter(Skill.name.ilike(s_name)).first()
    if not skill:
        # Normalize category to English for DB consistency
        raw_cat = (payload.category or "Technology").strip()
        if raw_cat.lower() == "công nghệ":
            raw_cat = "Technology"

        skill = Skill(id=uuid.uuid4(), name=s_name_cap, category=raw_cat)
        db.add(skill)
        db.commit()
        db.refresh(skill)

    existing = (
        db.query(UserSkillProfile)
        .filter(UserSkillProfile.cv_id == cv.id, UserSkillProfile.skill_id == skill.id)
        .first()
    )
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
            source="manual",
        )
        db.add(new_prof)

    # Invalidate cache by updating UserCV timestamp
    cv.updated_at = func.now()

    db.commit()
    return {"message": "Skill added successfully"}


@app.put("/cv/{cv_id}/skills/{profile_id}")
async def update_cv_skill(
    cv_id: str,
    profile_id: str,
    payload: SkillUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    user_id_str = request.headers.get("X-User-ID")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Authentication required")

    cv = db.query(UserCV).filter(UserCV.id == uuid.UUID(cv_id)).first()
    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")
    if not is_admin(request) and str(cv.user_id) != user_id_str:
        raise HTTPException(status_code=403, detail="Not authorized")

    prof = (
        db.query(UserSkillProfile)
        .filter(
            UserSkillProfile.id == uuid.UUID(profile_id),
            UserSkillProfile.cv_id == cv.id,
        )
        .first()
    )
    if not prof:
        raise HTTPException(status_code=404, detail="Skill profile not found")

    if payload.years_exp is not None:
        prof.years_exp = payload.years_exp
    if payload.level:
        prof.level = payload.level

    # Invalidate cache by updating UserCV timestamp
    cv.updated_at = func.now()
    
    db.commit()
    return {"message": "Skill updated successfully"}


@app.delete("/cv/{cv_id}/skills/{profile_id}")
async def delete_cv_skill(
    cv_id: str, profile_id: str, request: Request, db: Session = Depends(get_db)
):
    user_id_str = request.headers.get("X-User-ID")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Authentication required")

    cv = db.query(UserCV).filter(UserCV.id == uuid.UUID(cv_id)).first()
    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")
    if not is_admin(request) and str(cv.user_id) != user_id_str:
        raise HTTPException(status_code=403, detail="Not authorized")

    prof = (
        db.query(UserSkillProfile)
        .filter(
            UserSkillProfile.id == uuid.UUID(profile_id),
            UserSkillProfile.cv_id == cv.id,
        )
        .first()
    )
    if not prof:
        raise HTTPException(status_code=404, detail="Skill profile not found")

    db.delete(prof)
    
    # Invalidate cache by updating UserCV timestamp
    cv.updated_at = func.now()

    db.commit()
    return {"message": "Skill deleted successfully"}


@app.get("/cv/status/{task_id}")
async def get_cv_status(
    task_id: str,
    cv_id: Optional[str] = Query(None, description="CV ID to lookup granular progress"),
    request: Request = None, 
    db: Session = Depends(get_db)):
    """
    Poll Celery task status.
    Khi task SUCCESS → tự động fetch CV data từ DB và trả về đầy đủ
    để frontend không cần gọi thêm /cv/{cv_id}.
    """
    task_result = celery_app.AsyncResult(task_id)

    # Translate Celery state → frontend-friendly status
    celery_status = task_result.status
    if celery_status == "SUCCESS":
        status = "completed"
    elif celery_status == "FAILURE":
        status = "failed"
    else:
        status = "processing"

    progress_data = None
    if status == "processing" and cv_id:
        try:
            cached_progress = result_cache.get(f"cv_progress:{cv_id}")
            if cached_progress:
                progress_data = json.loads(cached_progress)
        except Exception as e:
            logger.warning(f"Failed to fetch progress from redis: {e}")

    result_data = None
    if task_result.ready():
        raw = task_result.result
        if celery_status == "SUCCESS" and isinstance(raw, dict):
            cv_id = raw.get("cv_id")
            if cv_id:
                # Fetch full CV data from DB
                try:
                    cv_uuid = uuid.UUID(cv_id)
                    cv = db.query(UserCV).filter(UserCV.id == cv_uuid).first()
                    if cv:
                        # Get skills from UserSkillProfile
                        skills_profiles = (
                            db.query(UserSkillProfile, Skill.name, Skill.category)
                            .join(Skill, UserSkillProfile.skill_id == Skill.id)
                            .filter(UserSkillProfile.cv_id == cv.id)
                            .all()
                        )
                        cv_parsed = getattr(cv, "cv_parsed_json", None)
                        is_ocr = cv_parsed.get("is_ocr", False) if cv_parsed else False

                        result_data = {
                            "id": str(cv.id),
                            "full_name": cv.full_name or "Parsed Candidate",
                            "summary": cv.summary or "",
                            "experience_years_total": cv.experience_years_total or 0,
                            "is_verified": cv.is_verified,
                            "status": cv.status,
                            "skills": [
                                {
                                    "id": str(sp.id),
                                    "skill_id": str(sp.skill_id),
                                    "name": n,
                                    "category": c,
                                    "experience_years": sp.years_exp,
                                }
                                for sp, n, c in skills_profiles
                            ],
                            "is_ocr": is_ocr,
                            "cv_parsed": cv_parsed,
                            "work_history": cv_parsed.get("work_history", [])
                            if cv_parsed
                            else [],
                            "education": cv_parsed.get("education", [])
                            if cv_parsed
                            else [],
                            "certifications": cv_parsed.get("certifications", [])
                            if cv_parsed
                            else [],
                            "seniority": cv_parsed.get("seniority", "Unknown")
                            if cv_parsed
                            else "Unknown",
                            "ocr_confidence": cv_parsed.get("ocr_confidence", 1.0)
                            if cv_parsed
                            else 1.0,
                        }
                        status = cv.status  # reflects actual DB status
                except Exception as e:
                    logger.warning(f"get_cv_status: failed to fetch CV data: {e}")

        elif celery_status == "FAILURE":
            status = "failed"

    # If failed, try to get error_message from DB if we have cv_id
    error_message = None
    if status == "failed":
        if celery_status == "FAILURE" and task_result.result:
            error_message = str(task_result.result)
        
        if cv_id:
            try:
                cv_uuid = uuid.UUID(cv_id)
                cv = db.query(UserCV).filter(UserCV.id == cv_uuid).first()
                if cv and cv.error_message:
                    error_message = cv.error_message
            except:
                pass

    return {
        "task_id": task_id,
        "status": status,
        "progress": progress_data,
        "result": result_data,
        "error_message": error_message,
    }


@app.delete("/cv/status/{task_id}")
async def revoke_cv_task(task_id: str, request: Request):
    """
    Spec 4.1: Graceful Cancellation.
    Dừng task đang chạy và giải phóng worker.
    """
    logger.info(f"[CV REVOKE] Request to revoke task_id={task_id}")
    task_result = celery_app.AsyncResult(task_id)
    
    # Revoke task (terminate=True will send SIGTERM to worker child process)
    task_result.revoke(terminate=True)
    
    return {"message": "Task revocation request sent", "task_id": task_id}


# ─── 4.2 + 2.1: Analysis History ────────────────────────────────────────────


@app.get("/cv/{cv_id}/analysis/history")
async def get_cv_analysis_history(
    cv_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Lấy lịch sử tất cả analysis cho 1 CV.
    Spec 4.2: Lưu lịch sử phân tích.
    """
    user_id_str = request.headers.get("X-User-ID")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Authentication required")

    cv_uuid = uuid.UUID(cv_id)
    cv = db.query(UserCV).filter(UserCV.id == cv_uuid).first()
    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")
    if not is_admin(request) and str(cv.user_id) != user_id_str:
        raise HTTPException(status_code=403, detail="Not authorized")

    analyses = (
        db.query(UserAnalysis)
        .filter(UserAnalysis.cv_id == cv_uuid)
        .order_by(UserAnalysis.created_at.desc())
        .all()
    )

    return [
        {
            "id": str(a.id),
            "user_id": str(a.user_id),
            "cv_id": str(a.cv_id),
            "job_id": str(a.job_id) if a.job_id else None,
            "match_score": a.match_score,
            "created_at": a.created_at,
            "overall_match_pct": (
                a.result_json.get("overall_match_pct")
                if a.result_json and isinstance(a.result_json, dict)
                else None
            ),
            "overall_assessment": (
                a.result_json.get("overall_assessment")
                if a.result_json and isinstance(a.result_json, dict)
                else None
            ),
        }
        for a in analyses
    ]
