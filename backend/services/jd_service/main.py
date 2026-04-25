"""
JD Service â€” Job Description management + Hybrid search.
Spec: 1.6 JD Parsing, 1.8 Advanced Job Search, 5.1+5.2 Market Analytics.
"""

from fastapi import FastAPI, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, or_, and_
from sqlalchemy.dialects.postgresql import UUID
from shared.database import get_db
from shared.models import Job, SystemSetting
from shared.config_utils import config_manager
from shared.llm_utils import get_embedding
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
logger = logging.getLogger("jd_service")

# Feature flag
USE_VECTOR_SEARCH = os.getenv("JD_USE_VECTOR_SEARCH", "true").lower() == "true"


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
    similarity: Optional[float] = None  # For search results

    class Config:
        from_attributes = True



    class Config:
        from_attributes = True


class CrawlUrlRequest(BaseModel):
    url: str


class JobBulkCreate(BaseModel):
    jobs: List[JobCreate]


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
        "location_normalized": job.location_normalized,
        "employment_type": job.employment_type,
        "has_insurance": job.has_insurance,
        "has_13th_month": job.has_13th_month,
        "remote_friendly": job.remote_friendly,
        "source_label": job.source_label,
        "created_at": job.created_at,
        "source_url": job.source_url,
        "similarity": similarity,
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

    # Trigger real JD parsing task (not stub)
    try:
        celery_app.send_task(
            "worker.tasks.parse_jd_task.parse_jd", args=[str(new_job.id)]
        )
    except Exception as e:
        logger.warning(f"Failed to trigger JD parsing task: {e}")

    return _job_to_response(new_job)


@app.get("/jd/list", response_model=List[JobResponse])
def list_jobs(
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    """Danh sÃ¡ch jobs active, cÃ³ phÃ¢n trang."""
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
    Hybrid job search: pgvector semantic + ILIKE text + filters.
    Spec 1.8: Lá»c theo Ä‘á»‹a Ä‘iá»ƒm, má»©c lÆ°Æ¡ng, loáº¡i cÃ´ng viá»‡c.

    Priority:
    1. Náº¿u cÃ³ q (query): pgvector similarity search
    2. Náº¿u khÃ´ng cÃ³ q: ILIKE text search
    3. Ãp dá»¥ng táº¥t cáº£ filters
    """
    base_query = db.query(Job).filter(Job.status == "active")

    results = []
    similarity_scores = {}

    if q and USE_VECTOR_SEARCH:
        # â”€â”€ pgvector semantic search â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # Reset any aborted transaction before vector query
        try:
            db.rollback()
        except Exception:
            pass

        job_vector = get_embedding(q)
        if job_vector:
            vec_query = text("""
                SELECT id,
                       1 - (vector <=> :vec) as similarity
                FROM jobs
                WHERE status = 'active'
                  AND vector IS NOT NULL
                ORDER BY vector <=> :vec
                LIMIT 200
            """)
            try:
                vec_results = db.execute(vec_query, {"vec": job_vector}).fetchall()
                vec_job_ids = {str(r.id): float(r.similarity) for r in vec_results}
                # BUG-014 FIX: Populate similarity_scores dict so it can be used later
                similarity_scores = vec_job_ids.copy()
            except Exception as e:
                db.rollback()
                # BUG-011 FIX: Log error and fallback to text search automatically
                logger.error(f"[job search] pgvector query failed: {e}. Falling back to text search.")
                vec_job_ids = {}
                similarity_scores = {}

            if vec_job_ids:
                base_query = base_query.filter(
                    Job.id.in_([uuid.UUID(k) for k in vec_job_ids.keys()])
                )
            else:
                # BUG-011 FIX: If vector search failed or returned no results, continue with text search
                logger.info(f"[job search] Vector search returned no results, using text search fallback")

    # â”€â”€ Text search fallback / supplement â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

    # Attach similarity scores if vector search was used
    for job in jobs:
        sim = similarity_scores.get(str(job.id)) if q and USE_VECTOR_SEARCH else None
        results.append(_job_to_response(job, similarity=sim))

    # Sort by similarity if vector search results
    if q and USE_VECTOR_SEARCH and similarity_scores:
        results.sort(
            key=lambda x: (
                similarity_scores.get(str(x["id"]), 0) if x.get("similarity") else 0
            ),
            reverse=True,
        )

    return {
        "items": results,
        "total": total,
        "limit": limit,
        "offset": offset,
        "page": (offset // limit) + 1,
        "pages": (total + limit - 1) // limit
    }


@app.get("/jd/{job_id}", response_model=JobResponse)
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    """Láº¥y chi tiáº¿t 1 job."""
    job = db.query(Job).filter(Job.id == job_id).first()
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
    if request.headers.get("X-Is-Admin") != "true":
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
    if request.headers.get("X-Is-Admin") != "true":
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
    if request.headers.get("X-Is-Admin") != "true":
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
    if request.headers.get("X-Is-Admin") != "true":
        raise HTTPException(status_code=403, detail="Admin privileges required")

    source_id = f"manual_{uuid.uuid4()}"

    # Generate Embedding
    embedding_ctx = f"{job_in.title_raw} at {job_in.company_name}. {job_in.location_raw}. {job_in.raw_text[:1000]}"
    vector = get_embedding(embedding_ctx)

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
        status="active",
        embedding_context=embedding_ctx,
        vector=vector
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    return _job_to_response(new_job)


@app.post("/jd/admin/crawl")
def admin_trigger_crawl(request: Request):
    """Admin only: KÃ­ch hoáº¡t cÃ o tin TopCV ngay láº­p tá»©c."""
    if request.headers.get("X-Is-Admin") != "true":
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
    if request.headers.get("X-Is-Admin") != "true":
        raise HTTPException(status_code=403, detail="Admin privileges required")

    if "topcv.vn" not in req.url:
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ URL từ TopCV.vn")

    try:
        scraper = TopCVScraper()
        logger.info(f"[ADMIN CRAWL] Fetching job from URL: {req.url}")
        
        data = scraper.scrape_job_details(req.url)
        
        if not data:
            logger.error(f"[ADMIN CRAWL] Scraper returned None for URL: {req.url}")
            raise HTTPException(
                status_code=404, 
                detail="Không thể lấy dữ liệu từ URL này. Vui lòng kiểm tra:\n1. URL có đúng format không?\n2. Job còn active trên TopCV không?\n3. Thử lại sau vài giây."
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
    if request.headers.get("X-Is-Admin") != "true":
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

        # Generate Embedding - ONLY from requirements field
        title = job_in.title_raw
        company = job_in.company_name or "Unknown"
        location = job_in.location_raw or ""
        requirements = job_in.requirements or ""
        
        if requirements:
            # Primary: Use only requirements (most relevant for matching)
            embedding_ctx = f"Job: {title} at {company}. Location: {location}. Requirements: {requirements}"
        else:
            # Fallback: Use title and location only if no requirements
            embedding_ctx = f"Job: {title} at {company}. Location: {location}."
            logger.warning(f"[BULK IMPORT] No requirements found for {source_id}, using minimal context")
        
        # Generate embedding with cost logging
        logger.info(f"[BULK IMPORT] Generating embedding for {source_id}...")
        vector = get_embedding(embedding_ctx, log_cost=True)
        
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
            # Embedding
            status="active",
            embedding_context=embedding_ctx,
            vector=vector
        )
        db.add(job)
        new_jobs_count += 1

    db.commit()
    logger.info(f"[BULK IMPORT] ✅ Successfully imported {new_jobs_count} jobs")
    
    # Trigger async skill extraction for imported jobs
    if new_jobs_count > 0:
        logger.info(f"[BULK IMPORT] Triggering skill extraction for {new_jobs_count} jobs...")
        try:
            celery_app.send_task(
                "worker.tasks.crawler_tasks.batch_extract_skills_task",
                kwargs={"limit": new_jobs_count, "skip_existing": False}
            )
            logger.info(f"[BULK IMPORT] ✓ Skill extraction task queued")
        except Exception as e:
            logger.error(f"[BULK IMPORT] Failed to trigger skill extraction: {e}")
    
    return {"message": f"Successfully imported {new_jobs_count} jobs", "count": new_jobs_count}


# ─── Skill Extraction Endpoints ──────────────────────────────────────────────

@app.post("/jd/admin/extract-skills/{job_id}")
def admin_extract_job_skills(job_id: str, request: Request, db: Session = Depends(get_db)):
    """Admin only: Trigger skill extraction for a specific job."""
    if request.headers.get("X-Is-Admin") != "true":
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
    if request.headers.get("X-Is-Admin") != "true":
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


@app.get("/jd/{job_id}/skills")
def get_job_skills(job_id: str, db: Session = Depends(get_db)):
    """Get extracted skills for a specific job."""
    from shared.models import JobSkillRequirement, Skill
    
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get skills with their details
    skills = db.query(JobSkillRequirement, Skill).join(
        Skill, JobSkillRequirement.skill_id == Skill.id
    ).filter(
        JobSkillRequirement.job_id == job_id
    ).all()
    
    return {
        "job_id": job_id,
        "job_title": job.title_raw,
        "skills": [
            {
                "skill_name": skill.name,
                "category": skill.category,
                "required_level": req.required_level,
                "min_years_exp": req.min_years_exp,
                "is_mandatory": req.is_mandatory,
                "importance_weight": req.importance_weight
            }
            for req, skill in skills
        ],
        "extracted_at": job.last_analyzed_at,
        "raw_extraction": job.extracted_requirements_json
    }


# â”€â”€â”€ 5.1 + 5.2: Market Analytics â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


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

