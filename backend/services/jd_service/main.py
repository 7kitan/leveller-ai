"""
JD Service â€” Job Description management + Hybrid search.
Spec: 1.6 JD Parsing, 1.8 Advanced Job Search, 5.1+5.2 Market Analytics.
"""

from fastapi import FastAPI, Depends, HTTPException, Request, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import text, or_, and_
from sqlalchemy.dialects.postgresql import UUID
from shared.database import get_db, init_db
from shared.models import Job, SystemSetting, UserRole
from shared.config_utils import config_manager
from shared.llm_utils import normalize_location
from shared.ai_service import AI_REGISTRY
from shared.scrapers.topcv import TopCVScraper
from pydantic import BaseModel, Field
from shared.schemas import PaginatedResponse
from typing import List, Optional, Any
from datetime import datetime, timedelta
import uuid
import os
import json
import logging
import re
import traceback
from worker.celery_app import celery_app

app = FastAPI(title="JD Service")

@app.on_event("startup")
async def startup_event():
    init_db()

logger = logging.getLogger("jd_service")


# â”€â”€â”€ Pydantic Schemas â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


class JobCreate(BaseModel):
    title_raw: str = Field(..., max_length=500)
    raw_text: str = Field(..., max_length=50000)
    source_url: Optional[str] = Field(None, max_length=500)
    source_label: Optional[str] = Field(default="manual", max_length=100)
    company_name: Optional[str] = Field(None, max_length=255)
    min_salary_vnd: Optional[int] = Field(None, ge=0, le=999999999)
    max_salary_vnd: Optional[int] = Field(None, ge=0, le=999999999)
    location_raw: Optional[str] = Field(None, max_length=500)
    location_normalized: Optional[str] = Field(None, max_length=100)
    location_district: Optional[str] = Field(None, max_length=100)
    employment_type: Optional[str] = Field(None, max_length=50)
    
    # Structured fields from parsing
    job_description: Optional[str] = Field(None, max_length=10000)
    requirements: Optional[str] = Field(None, max_length=10000)
    benefits: Optional[str] = Field(None, max_length=5000)


class JobUpdate(BaseModel):
    status: Optional[str] = None
    min_salary_vnd: Optional[int] = None
    max_salary_vnd: Optional[int] = None
    title_category: Optional[str] = None


class JobResponse(BaseModel):
    id: uuid.UUID
    title_raw: str
    company_name: Optional[str]
    status: str
    min_salary_vnd: Optional[int]
    max_salary_vnd: Optional[int]
    location_raw: Optional[str]
    employment_type: Optional[str]
    has_insurance: bool
    has_13th_month: bool
    remote_friendly: bool
    source_label: Optional[str]
    created_at: Optional[datetime]
    source_url: Optional[str] = None
    job_description: Optional[str] = None
    requirements: Optional[str] = None
    benefits: Optional[str] = None
    title: str
    location: Optional[str]
    similarity: Optional[float] = None  # For search results
    extracted_skills: Optional[List[dict]] = None  # Extracted skills from requirements
    
    # Classification fields
    is_tech_job: bool = True
    job_classification_confidence: Optional[float] = None
    job_primary_domain: Optional[str] = None
    job_classification_reason: Optional[str] = None
    classified_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CrawlUrlRequest(BaseModel):
    url: str


class JobBulkCreate(BaseModel):
    jobs: List[JobCreate]


class JobFullImport(BaseModel):
    """Schema for importing jobs with pre-computed vectors"""
    id: Optional[uuid.UUID] = None
    source_id: str = Field(..., max_length=100)
    title_raw: str = Field(..., max_length=500)
    title_category: Optional[str] = Field(None, max_length=100)
    domain_role: Optional[str] = Field(None, max_length=100)
    company_name: Optional[str] = Field(None, max_length=255)
    source_url: Optional[str] = Field(None, max_length=1000)
    source_label: Optional[str] = Field(None, max_length=100)
    raw_text: Optional[str] = Field(None, max_length=50000)
    job_description: Optional[str] = Field(None, max_length=10000)
    requirements: Optional[str] = Field(None, max_length=10000)
    benefits: Optional[str] = Field(None, max_length=5000)
    min_salary_vnd: Optional[int] = Field(None, ge=0, le=999999999)
    max_salary_vnd: Optional[int] = Field(None, ge=0, le=999999999)
    required_exp_years: Optional[float] = None
    employment_type: Optional[str] = Field(None, max_length=50)
    location_raw: Optional[str] = Field(None, max_length=500)
    location_normalized: Optional[str] = Field(None, max_length=100)
    location_district: Optional[str] = Field(None, max_length=100)
    status: str = Field(default="active", max_length=20)
    embedding_context: Optional[str] = Field(None, max_length=10000)
    vector: List[float] = Field(..., min_length=1536, max_length=1536)
    has_insurance: bool = False
    has_13th_month: bool = False
    remote_friendly: bool = False
    extracted_requirements_json: Optional[List[dict]] = None
    # Job classification fields (added to match table structure)
    is_tech_job: bool = True
    job_classification_confidence: Optional[float] = None
    job_primary_domain: Optional[str] = Field(None, max_length=100)
    job_classification_reason: Optional[str] = None
    classified_at: Optional[datetime] = None


class JobFullImportBulk(BaseModel):
    jobs: List[JobFullImport]


class JobExport(BaseModel):
    """Schema for exporting jobs with vectors"""
    id: uuid.UUID
    source_id: str
    title_raw: str
    title_category: Optional[str] = None
    domain_role: Optional[str] = None
    company_name: Optional[str] = None
    source_url: Optional[str] = None
    source_label: Optional[str] = None
    raw_text: Optional[str] = None
    job_description: Optional[str] = None
    requirements: Optional[str] = None
    benefits: Optional[str] = None
    min_salary_vnd: Optional[int] = None
    max_salary_vnd: Optional[int] = None
    required_exp_years: Optional[float] = None
    employment_type: Optional[str] = None
    location_raw: Optional[str] = None
    location_normalized: Optional[str] = None
    location_district: Optional[str] = None
    status: str
    embedding_context: Optional[str] = None
    vector: List[float]
    has_insurance: bool = False
    has_13th_month: bool = False
    remote_friendly: bool = False
    indexed_at: Optional[datetime] = None
    last_analyzed_at: Optional[datetime] = None
    extracted_requirements_json: Optional[List[dict]] = None
    # Job classification fields (added to match table structure)
    is_tech_job: bool = True
    job_classification_confidence: Optional[float] = None
    job_primary_domain: Optional[str] = None
    job_classification_reason: Optional[str] = None
    classified_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# â”€â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def _job_to_response(job: Job, similarity: float = None) -> dict:
    """Convert Job model to dict response."""
    return {
        "id": str(job.id),
        "title_raw": job.title_raw,
        "company_name": job.company_name,
        "status": job.status,
        "job_description": job.job_description,
        "requirements": job.requirements,
        "benefits": job.benefits,
        "min_salary_vnd": job.min_salary_vnd,
        "max_salary_vnd": job.max_salary_vnd,
        "location_raw": job.location_raw,
        "title": job.title_raw,
        "location": job.location_raw,
        "location_normalized": job.location_normalized,
        "employment_type": job.employment_type,
        "has_insurance": job.has_insurance,
        "has_13th_month": job.has_13th_month,
        "remote_friendly": job.remote_friendly,
        "source_label": job.source_label,
        "created_at": job.created_at,
        "source_url": job.source_url,
        "similarity": similarity,
        "extracted_skills": job.extracted_requirements_json,  # Include extracted skills
        
        # Classification fields
        "is_tech_job": job.is_tech_job,
        "job_classification_confidence": job.job_classification_confidence,
        "job_primary_domain": job.job_primary_domain,
        "job_classification_reason": job.job_classification_reason,
        "classified_at": job.classified_at,
    }


# ——————————————————————————————————————————————————————————————————————————————


@app.post("/jd/import/text", response_model=JobResponse)
def import_jd_text(job_in: JobCreate, request: Request, db: Session = Depends(get_db)):
    """
    Import JD text vÃ  trigger background parsing task (v3 pipeline).
    Spec 1.6: Thu tháº­p vÃ  xá»­ lÃ½ yÃªu cáº§u tá»« tin tuyá»ƒn dá»¥ng.
    """
    source_id = f"manual_{uuid.uuid4()}"

    new_job = Job(
        source_id=source_id,
        title_raw=job_in.title_raw,
        raw_text=job_in.raw_text,
        company_name=job_in.company_name,
        source_url=job_in.source_url,
        source_label=job_in.source_label or "manual",
        min_salary_vnd=job_in.min_salary_vnd,
        max_salary_vnd=job_in.max_salary_vnd,
        location_raw=job_in.location_raw,
        employment_type=job_in.employment_type,
        status="processing",
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    # Trigger skill extraction (parse_jd_task is deprecated stub)
    try:
        celery_app.send_task(
            "worker.tasks.crawler_tasks.extract_job_skills_task",
            args=[str(new_job.id)],
            queue="market_stats"
        )
        logger.info(f"[IMPORT JD] Triggered skill extraction for job {new_job.id}")
    except Exception as e:
        logger.warning(f"[IMPORT JD] Failed to trigger skill extraction: {e}")

    return _job_to_response(new_job)


@app.get("/jd/health")
def health_check():
    """Health check endpoint for Docker and monitoring."""
    return {"status": "ok", "service": "jd_service"}


@app.get("/jd/list", response_model=List[JobResponse])
def list_jobs(
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    """Danh sách jobs active, có phân trang."""
    jobs = (
        db.query(Job)
        .filter(Job.status == "active")
        .order_by(Job.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [_job_to_response(j) for j in jobs]


@app.get("/jd/search", response_model=PaginatedResponse[JobResponse])
def search_jobs(
    db: Session = Depends(get_db),
    # â”€â”€ Text / Semantic search â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    q: Optional[str] = Query(None, description="Tá»« khÃ³a tÃ¬m kiáº¿m"),
    # â”€â”€ Filters spec 1.8 â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    location: Optional[str] = Query(None, description="Äá»‹a Ä‘iá»ƒm"),
    min_salary: Optional[int] = Query(None, description="LÆ°Æ¡ng tá»‘i thiá»ƒu (VND)"),
    max_salary: Optional[int] = Query(None, description="LÆ°Æ¡ng tá»‘i Ä‘a (VND)"),
    employment_type: Optional[str] = Query(
        None, description="Loáº¡i cÃ´ng viá»‡c: full-time, part-time, contract"
    ),
    remote_friendly: Optional[bool] = Query(None, description="Há»— trá»£ remote"),
    has_insurance: Optional[bool] = Query(None, description="CÃ³ báº£o hiá»ƒm"),
    category: Optional[str] = Query(
        None, description="NgÃ nh/vai trÃ²: Backend, Frontend, DevOps, Data"
    ),
    # â”€â”€ Pagination â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    Job search with text matching + filters.
    Spec 1.8: Filter by location, salary, employment type.
    """
    base_query = db.query(Job).filter(Job.status == "active")

    # ── Text search ──────────────────────────────────────────────────────────
    if q:
        q_like = f"%{q}%"
        text_filter = or_(
            Job.title_raw.ilike(q_like),
            Job.company_name.ilike(q_like),
            Job.raw_text.ilike(q_like),
            Job.title_category.ilike(q_like),
        )
        base_query = base_query.filter(text_filter)

    # â”€â”€ Filters spec 1.8 â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if location:
        base_query = base_query.filter(
            or_(
                Job.location_normalized.ilike(f"%{location}%"),
                Job.location_raw.ilike(f"%{location}%"),
            )
        )

    # BUG-012 FIX: Salary filter logic - Only include jobs with known salary
    if min_salary is not None:
        base_query = base_query.filter(
            and_(Job.min_salary_vnd >= min_salary, Job.min_salary_vnd.is_not(None))
        )

    if max_salary is not None:
        base_query = base_query.filter(
            and_(Job.max_salary_vnd <= max_salary, Job.max_salary_vnd.is_not(None))
        )

    # BUG-013 FIX: Employment type case-sensitive - Normalize before comparison
    if employment_type:
        employment_type_normalized = employment_type.lower().strip()
        base_query = base_query.filter(
            Job.employment_type.ilike(f"%{employment_type_normalized}%")
        )

    if remote_friendly is not None:
        base_query = base_query.filter(Job.remote_friendly == remote_friendly)

    if has_insurance is not None:
        base_query = base_query.filter(Job.has_insurance == has_insurance)

    if category:
        base_query = base_query.filter(Job.title_category.ilike(f"%{category}%"))

    total = base_query.count()
    jobs = base_query.order_by(Job.created_at.desc()).offset(offset).limit(limit).all()

    results = [_job_to_response(job) for job in jobs]

    return {
        "items": results,
        "total": total,
        "limit": limit,
        "offset": offset,
        "page": (offset // limit) + 1,
        "pages": (total + limit - 1) // limit
    }


@app.get("/jd/{job_id}", response_model=JobResponse)
def get_job_by_id(job_id: str, db: Session = Depends(get_db)):
    """Get a single job by ID."""
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    
    job = db.query(Job).filter(Job.id == job_uuid).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return _job_to_response(job)


@app.get("/jd/admin/list", response_model=PaginatedResponse[JobResponse])
def admin_list_jobs(
    request: Request,
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
    q: Optional[str] = Query(None)
):
    """Admin only: Láº¥y táº¥t cáº£ Job vá»›i phÃ¢n trang."""
    if request.headers.get("X-User-Role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    query = db.query(Job)
    if status:
        query = query.filter(Job.status == status)
    
    if q:
        query = query.filter(
            or_(
                Job.title_raw.ilike(f"%{q}%"),
                Job.company_name.ilike(f"%{q}%"),
                Job.raw_text.ilike(f"%{q}%")
            )
        )

    total = query.count()
    jobs = query.order_by(Job.created_at.desc()).offset(offset).limit(limit).all()

    items = [_job_to_response(j) for j in jobs]
    
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "page": (offset // limit) + 1,
        "pages": (total + limit - 1) // limit
    }


@app.patch("/jd/admin/{job_id}", response_model=JobResponse)
def admin_update_job(
    job_id: uuid.UUID,
    job_in: JobUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Admin only: Cáº­p nháº­t Job."""
    if request.headers.get("X-User-Role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job_in.status is not None:
        job.status = job_in.status
    if job_in.min_salary_vnd is not None:
        job.min_salary_vnd = job_in.min_salary_vnd
    if job_in.max_salary_vnd is not None:
        job.max_salary_vnd = job_in.max_salary_vnd
    if job_in.title_category is not None:
        job.title_category = job_in.title_category

    db.commit()
    db.refresh(job)
    return _job_to_response(job)


@app.delete("/jd/admin/{job_id}")
def admin_delete_job(
    job_id: uuid.UUID, request: Request, db: Session = Depends(get_db)
):
    """Admin only: XÃ³a Job."""
    if request.headers.get("X-User-Role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    db.delete(job)
    db.commit()
    return {"message": "Job deleted successfully"}


@app.post("/jd/admin", response_model=JobResponse)
def admin_create_job(job_in: JobCreate, request: Request, db: Session = Depends(get_db)):
    """Admin only: Táº¡o má»›i Job thá»§ cÃ´ng."""
    if request.headers.get("X-User-Role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    source_id = f"manual_{uuid.uuid4()}"

    # Normalize location to standard cities
    location_normalized = normalize_location(job_in.location_raw or "")
    logger.info(f"[MANUAL JOB] Location normalized: '{job_in.location_raw}' → '{location_normalized}'")

    new_job = Job(
        source_id=source_id,
        title_raw=job_in.title_raw,
        raw_text=job_in.raw_text,
        company_name=job_in.company_name,
        source_url=job_in.source_url,
        source_label=job_in.source_label or "manual",
        min_salary_vnd=job_in.min_salary_vnd,
        max_salary_vnd=job_in.max_salary_vnd,
        location_raw=job_in.location_raw,
        location_normalized=location_normalized,
        employment_type=job_in.employment_type,
        status="active"
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    # Trigger background skill extraction
    try:
        from shared.skill_extraction import extract_and_save_job_skills
        
        # Run skill extraction in background task
        celery_app.send_task(
            "worker.tasks.crawler_tasks.extract_job_skills_task",
            args=[str(new_job.id)],
            queue="market_stats"
        )
        logger.info(f"[MANUAL JOB] Triggered skill extraction for job {new_job.id}")
    except Exception as e:
        logger.warning(f"[MANUAL JOB] Failed to trigger skill extraction: {e}")
        # Don't fail the request, extraction can be retried later

    return _job_to_response(new_job)


@app.post("/jd/admin/crawl")
def admin_trigger_crawl(request: Request):
    """Admin only: KÃ­ch hoáº¡t cÃ o tin TopCV ngay láº­p tá»©c."""
    if request.headers.get("X-User-Role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        task = celery_app.send_task("worker.tasks.crawler_tasks.crawl_topcv_jobs_task", args=[20], kwargs={"force": True})
        return {"message": "Crawler task started", "task_id": task.id}
    except Exception as e:
        logger.error(f"Failed to trigger crawler task: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Could not trigger crawler: {str(e)}")


# â”€â”€â”€ Admin Settings & Manual Crawl â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€





@app.post("/jd/admin/crawl/fetch")
def admin_crawl_fetch_job(req: CrawlUrlRequest, request: Request):
    """Admin only: Cào dữ liệu từ 1 URL TopCV để hiển thị ra form (chưa lưu)."""
    if request.headers.get("X-User-Role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    if "topcv.vn" not in req.url:
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ URL từ TopCV.vn")

    try:
        # Get proxy list from SystemSetting (global PROXY_LIST for all crawlers)
        db = get_db().__next__()
        proxy_list = []
        try:
            proxy_setting = db.query(SystemSetting).filter(SystemSetting.key == "PROXY_LIST").first()
            if proxy_setting and proxy_setting.value:
                # Parse proxy list - support both comma-separated and newline-separated
                proxy_str = str(proxy_setting.value).strip()
                if proxy_str:
                    # Split by both comma and newline, then filter empty strings
                    proxy_list = [p.strip() for p in re.split(r'[,\n\r]+', proxy_str) if p.strip()]
                    logger.info(f"[ADMIN CRAWL] Loaded {len(proxy_list)} proxies from global PROXY_LIST")
            else:
                logger.info(f"[ADMIN CRAWL] No proxy list configured in settings")
        except Exception as e:
            logger.warning(f"[ADMIN CRAWL] Failed to load proxy list from settings: {e}")
        finally:
            db.close()
        
        scraper = TopCVScraper(proxy_list=proxy_list)
        logger.info(f"[ADMIN CRAWL] Fetching job from URL: {req.url}")
        
        # Increase timeout and retries for production environment
        data = scraper.scrape_job_details(req.url, max_retries=3)
        
        if not data:
            logger.error(f"[ADMIN CRAWL] Scraper returned None for URL: {req.url}")
            logger.error(f"[ADMIN CRAWL] Check logs at /app/data/logs/ for detailed error information")
            raise HTTPException(
                status_code=404, 
                detail="Không thể lấy dữ liệu từ URL này. Vui lòng kiểm tra:\n1. URL có đúng format không?\n2. Job còn active trên TopCV không?\n3. Thử lại sau vài giây.\n4. Kiểm tra logs để biết chi tiết lỗi."
            )
        
        logger.info(f"[ADMIN CRAWL] Successfully scraped: {data.get('title_raw')}")
        return data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ADMIN CRAWL] Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi không mong đợi: {str(e)}")


@app.post("/jd/admin/crawl/upload-urls")
async def admin_upload_urls_for_crawl(
    file: UploadFile = File(...),
    request: Request = None
):
    """
    Admin only: Upload a .txt file with TopCV URLs (one per line) and queue them for background crawling.
    Each URL will be crawled by a worker and auto-saved to the database.
    
    Returns:
        - queued: number of URLs queued for crawling
        - skipped: number of invalid URLs skipped
        - task_ids: list of Celery task IDs
    """
    if request.headers.get("X-User-Role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    # Validate file type
    if not file.filename.endswith('.txt'):
        raise HTTPException(status_code=400, detail="Only .txt files are supported")
    
    try:
        # Read file content
        content = await file.read()
        text = content.decode('utf-8')
        
        # Parse URLs (one per line)
        lines = text.split('\n')
        urls = [line.strip() for line in lines if line.strip()]
        
        # Filter valid TopCV URLs
        valid_urls = []
        skipped = 0
        
        for url in urls:
            if 'topcv.vn' in url and url.startswith('http'):
                valid_urls.append(url)
            else:
                skipped += 1
                logger.warning(f"[UPLOAD CRAWL] Skipped invalid URL: {url}")
        
        if not valid_urls:
            raise HTTPException(
                status_code=400, 
                detail=f"No valid TopCV URLs found in file. Skipped {skipped} invalid lines."
            )
        
        # Queue each URL to worker
        task_ids = []
        for url in valid_urls:
            try:
                task = celery_app.send_task(
                    "worker.tasks.crawler_tasks.crawl_single_job_url_task",
                    args=[url],
                    queue="market_stats"
                )
                task_ids.append(task.id)
                logger.info(f"[UPLOAD CRAWL] Queued URL: {url} (task: {task.id})")
            except Exception as e:
                logger.error(f"[UPLOAD CRAWL] Failed to queue URL {url}: {e}")
                skipped += 1
        
        logger.info(f"[UPLOAD CRAWL] Successfully queued {len(task_ids)} URLs for crawling")
        
        return {
            "message": "URLs queued for background crawling",
            "queued": len(task_ids),
            "skipped": skipped,
            "total_urls": len(urls),
            "task_ids": task_ids[:10]  # Return first 10 task IDs only
        }
        
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded text")
    except Exception as e:
        logger.error(f"[UPLOAD CRAWL] Error processing file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")


@app.post("/jd/admin/crawl/fetch")
def admin_crawl_fetch_job(req: CrawlUrlRequest, request: Request):
    """Admin only: Cào dữ liệu từ 1 URL TopCV để hiển thị ra form (chưa lưu)."""
    if request.headers.get("X-User-Role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    if "topcv.vn" not in req.url:
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ URL từ TopCV.vn")

    try:
        # Get proxy list from SystemSetting (global PROXY_LIST for all crawlers)
        db = get_db().__next__()
        proxy_list = []
        try:
            proxy_setting = db.query(SystemSetting).filter(SystemSetting.key == "PROXY_LIST").first()
            if proxy_setting and proxy_setting.value:
                # Parse proxy list - support both comma-separated and newline-separated
                proxy_str = str(proxy_setting.value).strip()
                if proxy_str:
                    # Split by both comma and newline, then filter empty strings
                    proxy_list = [p.strip() for p in re.split(r'[,\n\r]+', proxy_str) if p.strip()]
                    logger.info(f"[ADMIN CRAWL] Loaded {len(proxy_list)} proxies from global PROXY_LIST")
            else:
                logger.info(f"[ADMIN CRAWL] No proxy list configured in settings")
        except Exception as e:
            logger.warning(f"[ADMIN CRAWL] Failed to load proxy list from settings: {e}")
        finally:
            db.close()
        
        scraper = TopCVScraper(proxy_list=proxy_list)
        logger.info(f"[ADMIN CRAWL] Fetching job from URL: {req.url}")
        
        # Increase timeout and retries for production environment
        data = scraper.scrape_job_details(req.url, max_retries=3)
        
        if not data:
            logger.error(f"[ADMIN CRAWL] Scraper returned None for URL: {req.url}")
            logger.error(f"[ADMIN CRAWL] Check logs at /app/data/logs/ for detailed error information")
            raise HTTPException(
                status_code=404, 
                detail="Không thể lấy dữ liệu từ URL này. Vui lòng kiểm tra:\n1. URL có đúng format không?\n2. Job còn active trên TopCV không?\n3. Thử lại sau vài giây.\n4. Kiểm tra logs để biết chi tiết lỗi."
            )
        
        logger.info(f"[ADMIN CRAWL] Successfully scraped: {data.get('title_raw')}")
        return data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ADMIN CRAWL] Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi cào dữ liệu: {str(e)}"
        )


@app.post("/jd/admin/bulk")
def admin_bulk_create_jobs(req: JobBulkCreate, request: Request, db: Session = Depends(get_db)):
    """Admin only: Lưu nhiều job cùng lúc (từ manual import)."""
    if request.headers.get("X-User-Role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    new_jobs_count = 0
    total_tokens = 0
    total_cost = 0.0
    
    for job_in in req.jobs:
        # Check if already exists
        job_id_match = re.search(r'/(\d+)\.html', job_in.source_url or "")
        source_id = f"TOPCV_{job_id_match.group(1)}" if job_id_match else f"manual_{uuid.uuid4()}"
        
        existing = db.query(Job).filter(Job.source_id == source_id).first()
        if existing:
            logger.info(f"[BULK IMPORT] Skipping existing job: {source_id}")
            continue

        job = Job(
            source_id=source_id,
            title_raw=job_in.title_raw,
            raw_text=job_in.raw_text,
            company_name=job_in.company_name,
            source_url=job_in.source_url,
            source_label=job_in.source_label or "manual",
            min_salary_vnd=job_in.min_salary_vnd,
            max_salary_vnd=job_in.max_salary_vnd,
            location_raw=job_in.location_raw,
            location_normalized=job_in.location_normalized,
            location_district=job_in.location_district,
            employment_type=job_in.employment_type,
            # Structured fields
            job_description=job_in.job_description,
            requirements=job_in.requirements,
            benefits=job_in.benefits,
            status="active"
        )
        db.add(job)
        new_jobs_count += 1

    db.commit()
    logger.info(f"[BULK IMPORT] ✅ Successfully imported {new_jobs_count} jobs")
    
    # Trigger skill extraction for EACH newly imported job (not batch)
    if new_jobs_count > 0:
        logger.info(f"[BULK IMPORT] Triggering skill extraction for {new_jobs_count} new jobs...")
        
        # Get the newly imported jobs
        imported_jobs = db.query(Job).filter(
            Job.requirements.isnot(None),
            Job.extracted_requirements_json.is_(None)
        ).order_by(Job.created_at.desc()).limit(new_jobs_count).all()
        
        extraction_count = 0
        try:
            for job in imported_jobs:
                celery_app.send_task(
                    "worker.tasks.crawler_tasks.extract_job_skills_task",
                    args=[str(job.id)],
                    queue="market_stats"
                )
                extraction_count += 1
                logger.info(f"[BULK IMPORT] Queued extraction for: {job.title_raw}")
            
            logger.info(f"[BULK IMPORT] ✓ Queued {extraction_count} extraction tasks")
        except Exception as e:
            logger.error(f"[BULK IMPORT] Failed to trigger skill extraction: {e}")
    
    return {"message": f"Successfully imported {new_jobs_count} jobs", "count": new_jobs_count}


@app.get("/jd/admin/export-info")
def get_export_info(request: Request, db: Session = Depends(get_db)):
    """
    Admin only: Get export information for planning.
    
    Returns total count and recommendations for splitting into parts.
    """
    if request.headers.get("X-User-Role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    total = db.query(Job).filter(Job.status == "active").count()
    
    # Estimate size (rough calculation)
    # Average job: ~5KB (text only, no vectors)
    avg_size_kb = 5
    total_size_mb = (total * avg_size_kb) / 1024
    
    # Recommend parts to keep each part under 20MB
    max_size_per_part_mb = 20
    recommended_parts = max(1, int(total_size_mb / max_size_per_part_mb) + 1)
    recommended_per_part = total // recommended_parts if recommended_parts > 0 else total
    
    return {
        "total_jobs": total,
        "recommended_parts": recommended_parts,
        "recommended_per_part": recommended_per_part,
        "estimated_total_size_mb": round(total_size_mb, 2),
        "estimated_size_per_part_mb": round(total_size_mb / recommended_parts, 2) if recommended_parts > 0 else 0
    }


@app.get("/jd/admin/export")
async def admin_export_jobs(
    request: Request,
    db: Session = Depends(get_db),
    limit: int = Query(2000, ge=1, le=5000, description="Number of jobs per part"),
    offset: int = Query(0, ge=0, description="Starting position"),
    part: Optional[int] = Query(None, description="Part number (for reference)")
):
    """
    Admin only: Export jobs for backup/migration.
    
    Use /jd/admin/export-info first to plan your export.
    Supports pagination for splitting large exports into parts.
    """
    if request.headers.get("X-User-Role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    total = db.query(Job).filter(Job.status == "active").count()
    query = db.query(Job).filter(Job.status == "active").limit(limit).offset(offset)
    
    jobs = query.all()
    
    # Convert to export format (no vectors)
    export_data = []
    for job in jobs:
        export_data.append({
            "id": str(job.id),
            "source_id": job.source_id,
            "title_raw": job.title_raw,
            "title_category": job.title_category,
            "domain_role": job.domain_role,
            "company_name": job.company_name,
            "source_url": job.source_url,
            "source_label": job.source_label,
            "raw_text": job.raw_text,
            "job_description": job.job_description,
            "requirements": job.requirements,
            "benefits": job.benefits,
            "min_salary_vnd": job.min_salary_vnd,
            "max_salary_vnd": job.max_salary_vnd,
            "required_exp_years": job.required_exp_years,
            "employment_type": job.employment_type,
            "location_raw": job.location_raw,
            "location_normalized": job.location_normalized,
            "location_district": job.location_district,
            "status": job.status,
            "has_insurance": job.has_insurance,
            "has_13th_month": job.has_13th_month,
            "remote_friendly": job.remote_friendly,
            "indexed_at": job.indexed_at.isoformat() if job.indexed_at else None,
            "last_analyzed_at": job.last_analyzed_at.isoformat() if job.last_analyzed_at else None,
            "extracted_requirements_json": job.extracted_requirements_json,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None
        })
    
    return {
        "count": len(export_data),
        "jobs": export_data,
        "metadata": {
            "exported_at": datetime.utcnow().isoformat(),
            "total_available": total,
            "offset": offset,
            "limit": limit,
            "part": part,
            "has_more": (offset + limit) < total,
            "next_offset": offset + limit if (offset + limit) < total else None,
            "total_exported": len(export_data)
        }
    }


@app.post("/jd/admin/import-full")
def admin_import_jobs_full(
    req: JobFullImportBulk,
    request: Request,
    db: Session = Depends(get_db)
):
    """Admin only: Import jobs for backup/restore (no vector generation)."""
    if request.headers.get("X-User-Role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    imported = []
    skipped = []
    errors = []

    for job_req in req.jobs:
        try:
            # Check if exists by source_id
            existing = db.query(Job).filter(Job.source_id == job_req.source_id).first()
            
            if existing:
                skipped.append({
                    "source_id": job_req.source_id,
                    "reason": "Already exists"
                })
                continue

            # Use provided ID or generate new one
            job_id = job_req.id if job_req.id else uuid.uuid4()

            # Create job without vector
            new_job = Job(
                id=job_id,
                source_id=job_req.source_id,
                title_raw=job_req.title_raw,
                title_category=job_req.title_category,
                domain_role=job_req.domain_role,
                company_name=job_req.company_name,
                source_url=job_req.source_url,
                source_label=job_req.source_label,
                raw_text=job_req.raw_text,
                job_description=job_req.job_description,
                requirements=job_req.requirements,
                benefits=job_req.benefits,
                min_salary_vnd=job_req.min_salary_vnd,
                max_salary_vnd=job_req.max_salary_vnd,
                required_exp_years=job_req.required_exp_years,
                employment_type=job_req.employment_type,
                location_raw=job_req.location_raw,
                location_normalized=job_req.location_normalized,
                location_district=job_req.location_district,
                status=job_req.status,
                has_insurance=job_req.has_insurance,
                has_13th_month=job_req.has_13th_month,
                remote_friendly=job_req.remote_friendly,
                extracted_requirements_json=job_req.extracted_requirements_json
            )
            db.add(new_job)
            imported.append(str(job_id))
            
        except Exception as e:
            errors.append({
                "source_id": job_req.source_id,
                "error": str(e)
            })

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database commit failed: {str(e)}")
    
    # Trigger skill extraction for jobs that don't have extracted_requirements_json
    jobs_need_extraction = []
    for job_id in imported:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job and not job.extracted_requirements_json and job.requirements:
            jobs_need_extraction.append(job_id)
    
    if jobs_need_extraction:
        logger.info(f"[IMPORT FULL] Triggering skill extraction for {len(jobs_need_extraction)} jobs without extracted skills")
        try:
            for job_id in jobs_need_extraction:
                celery_app.send_task(
                    "worker.tasks.crawler_tasks.extract_job_skills_task",
                    args=[job_id],
                    queue="market_stats"
                )
            logger.info(f"[IMPORT FULL] ✓ Skill extraction tasks queued")
        except Exception as e:
            logger.error(f"[IMPORT FULL] Failed to trigger skill extraction: {e}")
    
    return {
        "imported": len(imported),
        "skipped": len(skipped),
        "errors": len(errors),
        "imported_ids": imported,
        "skipped_details": skipped,
        "error_details": errors,
        "skill_extraction_queued": len(jobs_need_extraction)
    }


# ─── Skill Extraction Endpoints ──────────────────────────────────────────────

@app.post("/jd/admin/extract-skills/{job_id}")
def admin_extract_job_skills(job_id: str, request: Request, db: Session = Depends(get_db)):
    """Admin only: Trigger skill extraction for a specific job."""
    if request.headers.get("X-User-Role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    # Check if job exists
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if not job.requirements:
        raise HTTPException(status_code=400, detail="Job has no requirements to extract from")
    
    try:
        # Trigger async task
        task = celery_app.send_task(
            "worker.tasks.crawler_tasks.extract_job_skills_task",
            args=[job_id]
        )
        return {
            "message": "Skill extraction task started",
            "task_id": task.id,
            "job_id": job_id
        }
    except Exception as e:
        logger.error(f"Failed to trigger skill extraction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Could not trigger extraction: {str(e)}")


@app.post("/jd/admin/batch-extract-skills")
def admin_batch_extract_skills(
    request: Request,
    limit: int = Query(100, ge=1, le=1000),
    skip_existing: bool = Query(True)
):
    """Admin only: Trigger batch skill extraction for multiple jobs."""
    if request.headers.get("X-User-Role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    try:
        task = celery_app.send_task(
            "worker.tasks.crawler_tasks.batch_extract_skills_task",
            kwargs={"limit": limit, "skip_existing": skip_existing}
        )
        return {
            "message": f"Batch skill extraction started for up to {limit} jobs",
            "task_id": task.id,
            "limit": limit,
            "skip_existing": skip_existing
        }
    except Exception as e:
        logger.error(f"Failed to trigger batch extraction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Could not trigger extraction: {str(e)}")


@app.get("/jd/analytics/salary-range")
def get_salary_range_by_role(
    db: Session = Depends(get_db),
    category: Optional[str] = Query(None, description="Filter by job category"),
    days: int = Query(90, ge=1, le=365, description="Days back"),
):
    """
    Spec 5.2: Má»©c lÆ°Æ¡ng tham kháº£o theo role.
    Tráº£ vá» salary ranges (min, median, max) theo title_category.
    """
    since = datetime.now() - timedelta(days=days)
    query = db.query(
        Job.title_category,
        text(
            " percentile_cont(0.25) WITHIN GROUP (ORDER BY min_salary_vnd) as q1_salary"
        ),
        text(
            " percentile_cont(0.50) WITHIN GROUP (ORDER BY min_salary_vnd) as median_salary"
        ),
        text(
            " percentile_cont(0.75) WITHIN GROUP (ORDER BY min_salary_vnd) as q3_salary"
        ),
        text(" AVG(min_salary_vnd) as avg_min"),
        text(" AVG(max_salary_vnd) as avg_max"),
        text(" COUNT(*) as job_count"),
    ).filter(
        Job.status == "active",
        Job.min_salary_vnd.isnot(None),
        Job.created_at >= since,
    )

    if category:
        query = query.filter(Job.title_category.ilike(f"%{category}%"))

    query = query.group_by(Job.title_category)

    raw = query.all()

    return [
        {
            "category": r.title_category or "Unknown",
            "job_count": int(r.job_count),
            "salary_range": {
                "q25_min": float(r.q1_salary) if r.q1_salary else None,
                "median_min": float(r.median_salary) if r.median_salary else None,
                "q75_min": float(r.q3_salary) if r.q3_salary else None,
                "avg_min": float(r.avg_min) if r.avg_min else None,
                "avg_max": float(r.avg_max) if r.avg_max else None,
            },
        }
        for r in raw
        if r.job_count >= 3  # Only roles with enough data
    ]


@app.get("/jd/analytics/trending-skills")
def get_trending_skills(
    db: Session = Depends(get_db),
    days: int = Query(30, ge=7, le=365),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Spec 5.1: Xu hÆ°á»›ng ká»¹ nÄƒng â€” ká»¹ nÄƒng phá»• biáº¿n nháº¥t trong JD gáº§n Ä‘Ã¢y.
    Káº¿t há»£p: job count + avg salary insights.
    """
    since = datetime.now() - timedelta(days=days)

    # Sá»­ dá»¥ng extracted_requirements_json hoáº·c job_skill_requirement
    query = text(f"""
        WITH skill_stats AS (
            SELECT
                s.name as skill_name,
                s.category as skill_category,
                COUNT(DISTINCT jsr.job_id) as job_count,
                AVG(j.min_salary_vnd) as avg_min_salary,
                AVG(j.max_salary_vnd) as avg_max_salary,
                ARRAY_AGG(DISTINCT j.title_category) FILTER (WHERE j.title_category IS NOT NULL) as roles
            FROM job_skill_requirement jsr
            JOIN skills s ON s.id = jsr.skill_id
            JOIN jobs j ON j.id = jsr.job_id
            WHERE j.status = 'active'
              AND j.created_at >= :since
              AND jsr.skill_id IS NOT NULL
            GROUP BY s.id, s.name, s.category
        )
        SELECT
            skill_name,
            skill_category,
            job_count,
            avg_min_salary,
            avg_max_salary,
            roles,
            -- Salary percentile
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY avg_min_salary) as salary_q25,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY avg_min_salary) as salary_q75
        FROM skill_stats
        WHERE job_count >= 3
        GROUP BY skill_name, skill_category, job_count, avg_min_salary, avg_max_salary, roles
        ORDER BY job_count DESC
        LIMIT :limit
    """)

    # Simplified query (PostgreSQL group by limitation workaround)
    simple_query = text("""
        SELECT
            s.name as skill_name,
            s.category as skill_category,
            COUNT(DISTINCT jsr.job_id) as job_count,
            AVG(j.min_salary_vnd) as avg_min_salary,
            AVG(j.max_salary_vnd) as avg_max_salary,
            COUNT(DISTINCT j.title_category) as unique_roles
        FROM job_skill_requirement jsr
        JOIN skills s ON s.id = jsr.skill_id
        JOIN jobs j ON j.id = jsr.job_id
        WHERE j.status = 'active'
          AND j.created_at >= NOW() - INTERVAL ':days days'
          AND jsr.skill_id IS NOT NULL
          AND j.min_salary_vnd IS NOT NULL
        GROUP BY s.id, s.name, s.category
        HAVING COUNT(DISTINCT jsr.job_id) >= 3
        ORDER BY job_count DESC
        LIMIT :limit
    """)

    # BUG-015 FIX: Trending skills query with graceful fallback
    try:
        safe_query = text("""
            SELECT
                s.name as skill_name,
                s.category as skill_category,
                COUNT(DISTINCT jsr.job_id) as job_count,
                AVG(j.min_salary_vnd) as avg_min_salary,
                AVG(j.max_salary_vnd) as avg_max_salary,
                COUNT(DISTINCT j.title_category) as unique_roles
            FROM job_skill_requirement jsr
            JOIN skills s ON s.id = jsr.skill_id
            JOIN jobs j ON j.id = jsr.job_id
            WHERE j.status = 'active'
              AND j.created_at >= NOW() - (INTERVAL '1 day' * :days)
              AND jsr.skill_id IS NOT NULL
              AND j.min_salary_vnd IS NOT NULL
            GROUP BY s.id, s.name, s.category
            HAVING COUNT(DISTINCT jsr.job_id) >= 3
            ORDER BY job_count DESC
            LIMIT :limit
        """)
        results = db.execute(safe_query, {"limit": limit, "days": days}).fetchall()
        
        # BUG-015 FIX: Return empty array if no results instead of failing
        if not results:
            logger.info(f"Trending skills query returned no results (empty DB or no data for {days} days)")
            return []
            
    except Exception as e:
        # BUG-015 FIX: Graceful fallback on error
        logger.error(f"Trending skills query failed: {e}")
        return []

    return [
        {
            "skill_name": r.skill_name,
            "category": r.skill_category or "Technology",
            "job_count": int(r.job_count),
            "avg_min_salary_vnd": float(r.avg_min_salary) if r.avg_min_salary else None,
            "avg_max_salary_vnd": float(r.avg_max_salary) if r.avg_max_salary else None,
            "unique_roles": int(r.unique_roles),
            "trend_period_days": days,
        }
        for r in results
    ]


@app.get("/jd/analytics/roles")
def get_role_analytics(
    db: Session = Depends(get_db),
    days: int = Query(90, ge=7, le=365),
    limit: int = Query(20, ge=1, le=50),
):
    """
    Spec 5.2: ThÃ´ng tin nghá» nghiá»‡p â€” vai trÃ² phá»• biáº¿n + má»©c lÆ°Æ¡ng theo role.
    """
    safe_query = text("""
        SELECT
            COALESCE(j.title_category, 'Other') as role,
            COUNT(*) as job_count,
            AVG(j.min_salary_vnd) as avg_min_salary,
            AVG(j.max_salary_vnd) as avg_max_salary,
            AVG(j.required_exp_years) as avg_exp_years,
            COUNT(*) FILTER (WHERE j.remote_friendly = true) as remote_count,
            COUNT(*) FILTER (WHERE j.has_insurance = true) as insured_count
        FROM jobs j
        WHERE j.status = 'active'
          AND j.created_at >= NOW() - (INTERVAL '1 day' * :days)
          AND j.title_category IS NOT NULL
        GROUP BY j.title_category
        HAVING COUNT(*) >= 2
        ORDER BY job_count DESC
        LIMIT :limit
    """)

    try:
        results = db.execute(safe_query, {"limit": limit, "days": days}).fetchall()
    except Exception as e:
        logger.warning(f"Role analytics query failed: {e}")
        return []

    return [
        {
            "role": r.role,
            "job_count": int(r.job_count),
            "avg_min_salary_vnd": float(r.avg_min_salary) if r.avg_min_salary else None,
            "avg_max_salary_vnd": float(r.avg_max_salary) if r.avg_max_salary else None,
            "avg_exp_years": float(r.avg_exp_years) if r.avg_exp_years else None,
            "remote_pct": round(int(r.remote_count) / int(r.job_count) * 100, 1)
            if r.job_count > 0
            else 0,
            "insured_pct": round(int(r.insured_count) / int(r.job_count) * 100, 1)
            if r.job_count > 0
            else 0,
        }
        for r in results
    ]


@app.get("/jd/health")
def health_check():
    """Health check endpoint for Docker and monitoring."""
    return {"status": "ok", "service": "jd_service"}


# â”€â”€â”€ Internal helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

