"""
JD Service — Job Description management + Hybrid search.
Spec: 1.6 JD Parsing, 1.8 Advanced Job Search, 5.1+5.2 Market Analytics.
"""

from fastapi import FastAPI, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, or_, and_
from sqlalchemy.dialects.postgresql import UUID
from shared.database import get_db
from shared.models import Job
from shared.redis_client import result_cache
from shared.llm_utils import get_embedding
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import uuid
import os
import json
import logging

app = FastAPI(title="JD Service")
logger = logging.getLogger("jd_service")

# Feature flag
USE_VECTOR_SEARCH = os.getenv("JD_USE_VECTOR_SEARCH", "true").lower() == "true"


# ─── Pydantic Schemas ─────────────────────────────────────────────────────────


class JobCreate(BaseModel):
    title_raw: str
    raw_text: str
    source_url: Optional[str] = None
    source_label: Optional[str] = "manual"
    company_name: Optional[str] = None
    min_salary_vnd: Optional[int] = None
    max_salary_vnd: Optional[int] = None
    location_raw: Optional[str] = None
    employment_type: Optional[str] = None


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
    similarity: Optional[float] = None  # For search results

    class Config:
        from_attributes = True


# ─── Helpers ────────────────────────────────────────────────────────────────


def _job_to_response(job: Job, similarity: float = None) -> dict:
    """Convert Job model to dict response."""
    return {
        "id": str(job.id),
        "title_raw": job.title_raw,
        "company_name": job.company_name,
        "status": job.status,
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
        "similarity": similarity,
    }


# ─── Endpoints ────────────────────────────────────────────────────────────────


@app.post("/jd/import/text", response_model=JobResponse)
def import_jd_text(job_in: JobCreate, request: Request, db: Session = Depends(get_db)):
    """
    Import JD text và trigger background parsing task (v3 pipeline).
    Spec 1.6: Thu thập và xử lý yêu cầu từ tin tuyển dụng.
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


@app.get("/jd/search", response_model=List[JobResponse])
def search_jobs(
    db: Session = Depends(get_db),
    # ── Text / Semantic search ─────────────────────────────────────────
    q: Optional[str] = Query(None, description="Từ khóa tìm kiếm"),
    # ── Filters spec 1.8 ──────────────────────────────────────────────
    location: Optional[str] = Query(None, description="Địa điểm"),
    min_salary: Optional[int] = Query(None, description="Lương tối thiểu (VND)"),
    max_salary: Optional[int] = Query(None, description="Lương tối đa (VND)"),
    employment_type: Optional[str] = Query(
        None, description="Loại công việc: full-time, part-time, contract"
    ),
    remote_friendly: Optional[bool] = Query(None, description="Hỗ trợ remote"),
    has_insurance: Optional[bool] = Query(None, description="Có bảo hiểm"),
    category: Optional[str] = Query(
        None, description="Ngành/vai trò: Backend, Frontend, DevOps, Data"
    ),
    # ── Pagination ────────────────────────────────────────────────
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    Hybrid job search: pgvector semantic + ILIKE text + filters.
    Spec 1.8: Lọc theo địa điểm, mức lương, loại công việc.

    Priority:
    1. Nếu có q (query): pgvector similarity search
    2. Nếu không có q: ILIKE text search
    3. Áp dụng tất cả filters
    """
    base_query = db.query(Job).filter(Job.status == "active")

    results = []
    similarity_scores = {}

    if q and USE_VECTOR_SEARCH:
        # ── pgvector semantic search ───────────────────────────────────────
        job_vector = get_embedding(q)
        if job_vector:
            vec_query = text("""
                SELECT id,
                       1 - (vector <=> :vec::vector) as similarity
                FROM jobs
                WHERE status = 'active'
                  AND vector IS NOT NULL
                ORDER BY vector <=> :vec::vector
                LIMIT 200
            """)
            vec_results = db.execute(vec_query, {"vec": job_vector}).fetchall()
            vec_job_ids = {str(r.id): float(r.similarity) for r in vec_results}

            if vec_job_ids:
                base_query = base_query.filter(
                    Job.id.in_([uuid.UUID(k) for k in vec_job_ids.keys()])
                )

    # ── Text search fallback / supplement ────────────────────────────────
    if q:
        q_like = f"%{q}%"
        text_filter = or_(
            Job.title_raw.ilike(q_like),
            Job.company_name.ilike(q_like),
            Job.raw_text.ilike(q_like),
            Job.title_category.ilike(q_like),
        )
        base_query = base_query.filter(text_filter)

    # ── Filters spec 1.8 ──────────────────────────────────────────────
    if location:
        base_query = base_query.filter(
            or_(
                Job.location_normalized.ilike(f"%{location}%"),
                Job.location_raw.ilike(f"%{location}%"),
            )
        )

    if min_salary is not None:
        base_query = base_query.filter(
            or_(Job.min_salary_vnd >= min_salary, Job.min_salary_vnd.is_(None))
        )

    if max_salary is not None:
        base_query = base_query.filter(
            or_(Job.max_salary_vnd <= max_salary, Job.max_salary_vnd.is_(None))
        )

    if employment_type:
        base_query = base_query.filter(
            Job.employment_type.ilike(f"%{employment_type}%")
        )

    if remote_friendly is not None:
        base_query = base_query.filter(Job.remote_friendly == remote_friendly)

    if has_insurance is not None:
        base_query = base_query.filter(Job.has_insurance == has_insurance)

    if category:
        base_query = base_query.filter(Job.title_category.ilike(f"%{category}%"))

    # Execute
    jobs = base_query.order_by(Job.created_at.desc()).offset(offset).limit(limit).all()

    # Attach similarity scores if vector search was used
    for job in jobs:
        sim = similarity_scores.get(str(job.id)) if q and USE_VECTOR_SEARCH else None
        results.append(_job_to_response(job, similarity=sim))

    # Sort by similarity if vector search results
    if q and USE_VECTOR_SEARCH and similarity_scores:
        results.sort(
            key=lambda x: (
                similarity_scores.get(x["id"], 0) if x.get("similarity") else 0
            ),
            reverse=True,
        )

    return results


@app.get("/jd/{job_id}", response_model=JobResponse)
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    """Lấy chi tiết 1 job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_response(job)


# ─── 5.1 + 5.2: Market Analytics ──────────────────────────────────────────


@app.get("/jd/analytics/salary-range")
def get_salary_range_by_role(
    db: Session = Depends(get_db),
    category: Optional[str] = Query(None, description="Filter by job category"),
    days: int = Query(90, ge=1, le=365, description="Days back"),
):
    """
    Spec 5.2: Mức lương tham khảo theo role.
    Trả về salary ranges (min, median, max) theo title_category.
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
    Spec 5.1: Xu hướng kỹ năng — kỹ năng phổ biến nhất trong JD gần đây.
    Kết hợp: job count + avg salary insights.
    """
    since = datetime.now() - timedelta(days=days)

    # Sử dụng extracted_requirements_json hoặc job_skill_requirement
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

    try:
        safe_query = text(f"""
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
              AND j.created_at >= NOW() - INTERVAL '{days} days'
              AND jsr.skill_id IS NOT NULL
              AND j.min_salary_vnd IS NOT NULL
            GROUP BY s.id, s.name, s.category
            HAVING COUNT(DISTINCT jsr.job_id) >= 3
            ORDER BY job_count DESC
            LIMIT :limit
        """)
        results = db.execute(safe_query, {"limit": limit}).fetchall()
    except Exception as e:
        logger.warning(f"Trending skills query failed: {e}")
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
    Spec 5.2: Thông tin nghề nghiệp — vai trò phổ biến + mức lương theo role.
    """
    safe_query = text(f"""
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
          AND j.created_at >= NOW() - INTERVAL '{days} days'
          AND j.title_category IS NOT NULL
        GROUP BY j.title_category
        HAVING COUNT(*) >= 2
        ORDER BY job_count DESC
        LIMIT :limit
    """)

    try:
        results = db.execute(safe_query, {"limit": limit}).fetchall()
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


# ─── Internal helpers ─────────────────────────────────────────────────────────

from worker.celery_app import celery_app
