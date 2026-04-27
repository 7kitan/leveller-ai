from fastapi import FastAPI, Depends, Request, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, func, or_
from shared.database import get_db
from shared.models import Course, JobSkillRequirement, Job, UserRole, YouTubeCourse
from shared.config_utils import config_manager
from shared.level_mapper import LevelMapper
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
import logging
import os
from datetime import datetime
from worker.celery_app import celery_app
from celery.result import AsyncResult
from shared.schemas import PaginatedResponse
from shared.youtube_service import youtube_service
from shared.database import init_db

app = FastAPI(title="Recommender Service")

@app.on_event("startup")
async def startup_event():
    init_db()
logger = logging.getLogger("recommender")

# NOTE: VECTOR_SIM_THRESHOLD is now fetched dynamically via config_manager.get_setting()
# at the point of use to support hot-reloading without service restart


class GapSkill(BaseModel):
    skill_name: str
    target_level: str = "Mid-level"
    gap_type: str = "MISSING"  # MISSING | PARTIAL
    severity: str = "MEDIUM"  # HIGH | MEDIUM | LOW


class RecommendRequest(BaseModel):
    gap_skills: List[GapSkill]
    lang: str = "vi"


class CrawlRequest(BaseModel):
    url: str


class CourseCreate(BaseModel):
    title: str = Field(..., max_length=500)
    platform: Optional[str] = Field(None, max_length=100)
    source_platform: Optional[str] = Field(default="manual", max_length=100)
    source_id: Optional[str] = Field(None, max_length=255)
    external_uuid: Optional[str] = Field(None, max_length=100)
    url: str = Field(..., max_length=500)
    level: str = Field(default="Beginner", max_length=50)
    provider: Optional[str] = Field(None, max_length=100)
    duration_hours: Optional[float] = Field(None, ge=0, le=10000)
    duration_raw: Optional[str] = Field(None, max_length=100)
    cost_usd: float = Field(default=0.0, ge=0, le=999999)
    languages: List[str] = Field(default_factory=lambda: ["en"], max_items=50)
    skills_raw: List[str] = Field(default_factory=list, max_items=50)
    tools_raw: List[str] = Field(default_factory=list, max_items=50)
    outcomes: List[str] = Field(default_factory=list, max_items=20)
    modules: List[str] = Field(default_factory=list, max_items=100)
    tags: List[str] = Field(default_factory=list, max_items=20)
    description: Optional[str] = Field(None, max_length=5000)  # SECURITY: Prevent unbounded descriptions


class CourseBulkCreate(BaseModel):
    courses: List[CourseCreate]


class CourseFullImport(BaseModel):
    """Schema for importing courses with pre-computed vectors"""
    id: Optional[uuid.UUID] = None
    title: str = Field(..., max_length=500)
    description: Optional[str] = Field(None, max_length=5000)
    source_platform: str = Field(..., max_length=100)
    source_id: str = Field(..., max_length=255)
    external_uuid: Optional[str] = Field(None, max_length=100)
    provider: Optional[str] = Field(None, max_length=100)
    platform: Optional[str] = Field(None, max_length=100)
    url: str = Field(..., max_length=500)
    level: Optional[str] = Field(None, max_length=50)
    is_certification: bool = False
    duration_hours: Optional[float] = Field(None, ge=0, le=10000)
    duration_raw: Optional[str] = Field(None, max_length=100)
    cost_usd: float = Field(default=0.0, ge=0, le=999999)
    languages: Optional[List[str]] = Field(default_factory=list, max_items=50)
    skills_raw: Optional[List[str]] = Field(default_factory=list, max_items=50)
    tools_raw: Optional[List[str]] = Field(default_factory=list, max_items=50)
    outcomes: Optional[List[str]] = Field(default_factory=list, max_items=20)
    modules: Optional[List[str]] = Field(default_factory=list, max_items=100)
    tags: Optional[List[str]] = Field(default_factory=list, max_items=20)
    embedding_context: Optional[str] = Field(None, max_length=10000)
    vector: List[float] = Field(..., min_length=1536, max_length=1536)
    is_active: bool = True


class CourseFullImportBulk(BaseModel):
    courses: List[CourseFullImport]


class CourseExport(BaseModel):
    """Schema for exporting courses with vectors"""
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    source_platform: Optional[str] = None
    source_id: Optional[str] = None
    external_uuid: Optional[str] = None
    provider: Optional[str] = None
    platform: Optional[str] = None
    url: Optional[str] = None
    level: Optional[str] = None
    is_certification: bool = False
    duration_hours: Optional[float] = None
    duration_raw: Optional[str] = None
    cost_usd: float = 0.0
    languages: Optional[List[str]] = None
    skills_raw: Optional[List[str]] = None
    tools_raw: Optional[List[str]] = None
    outcomes: Optional[List[str]] = None
    modules: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    embedding_context: Optional[str] = None
    vector: List[float]
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CourseRead(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    source_platform: Optional[str] = None
    source_id: Optional[str] = None
    external_uuid: Optional[str] = None
    provider: Optional[str] = None
    platform: Optional[str] = None
    url: Optional[str] = None
    level: Optional[str] = None
    is_certification: bool = False
    duration_hours: Optional[float] = None
    duration_raw: Optional[str] = None
    cost_usd: float = 0.0
    languages: Optional[List[str]] = None
    skills_raw: Optional[List[str]] = None
    tools_raw: Optional[List[str]] = None
    outcomes: Optional[List[str]] = None
    modules: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    is_active: bool = True
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CourseUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    platform: Optional[str] = Field(None, max_length=100)
    source_platform: Optional[str] = Field(None, max_length=100)
    source_id: Optional[str] = Field(None, max_length=255)
    external_uuid: Optional[str] = Field(None, max_length=100)
    url: Optional[str] = Field(None, max_length=500)
    level: Optional[str] = Field(None, max_length=50)
    provider: Optional[str] = Field(None, max_length=100)
    duration_hours: Optional[float] = Field(None, ge=0, le=10000)
    duration_raw: Optional[str] = Field(None, max_length=100)
    cost_usd: Optional[float] = Field(None, ge=0, le=999999)
    languages: Optional[List[str]] = Field(None, max_items=50)
    skills_raw: Optional[List[str]] = Field(None, max_items=50)
    tools_raw: Optional[List[str]] = Field(None, max_items=50)
    outcomes: Optional[List[str]] = Field(None, max_items=20)
    modules: Optional[List[str]] = Field(None, max_items=100)
    tags: Optional[List[str]] = Field(None, max_items=20)
    description: Optional[str] = Field(None, max_length=5000)  # SECURITY: Consistent with CourseCreate
    is_active: Optional[bool] = None


class YouTubeCourseRead(BaseModel):
    id: uuid.UUID
    video_id: str
    title: str
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    channel_name: Optional[str] = None
    url: Optional[str] = None
    duration_raw: Optional[str] = None
    published_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


def _vector_search_courses(skill_name: str, target_level: str, db, limit: int = 12):
    """pgvector similarity search cho courses. Fallback ILIKE nếu không có vector."""
    from shared.llm_utils import get_embedding

    # Reset any aborted transaction before querying
    try:
        db.rollback()
    except Exception:
        pass

    # Match structure with embedding context for better cosine similarity
    search_text = (
        f"TITLE: {skill_name}. "
        f"LEVEL: {target_level}. "
        f"SKILLS: {skill_name}."
    )
    skill_vector = get_embedding(search_text)

    if skill_vector:
        # Fetch thêm các trường JSONB để ranking chính xác hơn
        query = text("""
            SELECT id, title, source_platform, platform, url, level, provider,
                   duration_hours, is_certification, cost_usd, tags,
                   skills_raw, modules, outcomes,
                   1 - (vector <=> :vec) as similarity
            FROM courses
            WHERE vector IS NOT NULL
              AND is_active = TRUE
              AND 1 - (vector <=> :vec) > :sim_threshold
            ORDER BY similarity DESC
            LIMIT :limit
        """)
        try:
            # Get threshold dynamically for hot-reload support
            sim_threshold = float(config_manager.get_setting("SIMILARITY_THRESHOLD", 0.60))
            
            results = db.execute(
                query,
                {
                    "vec": skill_vector,
                    "sim_threshold": sim_threshold,
                    "limit": limit,
                },
            ).fetchall()
        except Exception as e:
            db.rollback()
            logger.error(f"[_vector_search_courses] pgvector query failed: {e}")
            results = []
    else:
        # Fallback: ILIKE text search
        # Sử dụng tham số binding cho pattern và skill_name để ngăn chặn SQL Injection
        query = text("""
            SELECT id, title, source_platform, platform, url, level, provider,
                   duration_hours, is_certification, cost_usd, tags,
                   skills_raw, modules, outcomes,
                   0.6 as similarity
            FROM courses
            WHERE is_active = TRUE
              AND (title ILIKE :pattern
               OR :skill_name = ANY(tags))
            ORDER BY is_certification DESC, duration_hours ASC
            LIMIT :limit
        """)
        try:
            results = db.execute(
                query,
                {
                    "pattern": f"%{skill_name}%",
                    "skill_name": skill_name,
                    "limit": limit,
                },
            ).fetchall()
        except Exception as e:
            db.rollback()
            logger.error(f"[_vector_search_courses] ILIKE fallback failed: {e}")
            results = []

    return [
        {
            "course_id": str(r.id),
            "title": r.title,
            "platform": r.platform or r.source_platform,
            "url": r.url,
            "level": r.level or "Unknown",
            "provider": getattr(r, "provider", "Unknown") or "Unknown",
            "duration_hours": float(r.duration_hours or 0),
            "is_certification": bool(r.is_certification),
            "cost_usd": float(r.cost_usd or 0),
            "tags": r.tags or [],
            "skills_raw": r.skills_raw or [],
            "modules": r.modules or [],
            "outcomes": r.outcomes or [],
            "similarity": float(r.similarity),
        }
        for r in results
    ]


def _rank_courses(
    candidates: List[dict], target_level: str, severity: str, skill_name: str
) -> List[dict]:
    """
    Rank courses: similarity (60%) + certification/level (40%).
    Cộng điểm bonus nếu khớp chính xác tên Skill trong metadata.
    """
    target_score = LevelMapper.to_score(target_level)
    severity_w = {"HIGH": 1.0, "MEDIUM": 0.7, "LOW": 0.4}
    sev = severity_w.get(severity, 0.4)

    for c in candidates:
        # 1. Similarity Score (60% weight)
        sim_score = c.get("similarity", 0.5) * 0.6

        # 2. Certification Bonus
        cert_bonus = 0.15 if c.get("is_certification") else 0
        
        # 3. Level Match
        c_level_score = LevelMapper.to_score(c.get("level") or "Unknown")
        level_diff = c_level_score - target_score
        level_bonus = 0.05 if level_diff >= 0 else (level_diff * 0.1)

        # 4. Hard Match Bonus (0.1) - Tìm trong tags, skills_raw, hoặc modules
        hard_match_bonus = 0
        search_area = (
            [s.lower() for s in c.get("tags", [])] +
            [s.lower() for s in c.get("skills_raw", [])] +
            [str(m).lower() for m in c.get("modules", [])]
        )
        if any(skill_name.lower() in item for item in search_area):
            hard_match_bonus = 0.1

        # Final Rank Score
        c["rank_score"] = round(
            (sim_score + cert_bonus + level_bonus + hard_match_bonus) * sev, 3
        )

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
        ranked = _rank_courses(candidates, gap.target_level, gap.severity, gap.skill_name)

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

    # ─── YouTube Integration (Free Resources) ────────────────────────
    # Tìm kiếm video YouTube cho các Gap Skills (Top 3 skills có severity cao nhất)
    youtube_resources = []
    top_gaps = sorted_gaps[:2] # Lấy 2 gap quan trọng nhất để tìm video
    
    for gap in top_gaps:
        # Infer domain from skill category
        category = gap.category.lower() if gap.category else ""
        domain = "programming"  # default
        if "devops" in category or "tools" in category:
            domain = "devops"
        elif "data" in category or "analytics" in category:
            domain = "data-science"
        elif "web" in category or "frontend" in category or "backend" in category:
            domain = "web-development"
        elif "mobile" in category or "android" in category or "ios" in category:
            domain = "mobile"
        
        videos = await youtube_service.search_and_cache(
            query=f"{gap.skill_name} {gap.target_level}",
            db=db,
            limit=2,
            lang=req.lang,
            domain=domain
        )
        for v in videos:
            v["gap_skill"] = gap.skill_name
            youtube_resources.append(v)

    return {
        "courses": all_recommendations,
        "youtube_videos": youtube_resources
    }


@app.get("/recommend/trending-skills")
async def get_trending_skills(
    days: int = 30, limit: int = 20, db: Session = Depends(get_db)
):
    """
    Lọc top Skills có tần suất xuất hiện cao nhất trong Job Requirement 30 ngày gần đây.
    Trả về: skill_name, job_count, avg_min_salary, avg_max_salary.
    """
    # Use bind parameters for limit. Interval is safe as days is an integer validated by FastAPI.
    safe_query = text("""
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
          AND j.created_at >= NOW() - (INTERVAL '1 day' * :days)
        GROUP BY s.id, s.name
        ORDER BY job_count DESC
        LIMIT :limit
    """)

    res = db.execute(safe_query, {"limit": limit, "days": days}).fetchall()

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


@app.get("/recommend/admin/courses", response_model=PaginatedResponse[CourseRead])
async def admin_list_courses(
    request: Request, 
    db: Session = Depends(get_db), 
    limit: int = Query(20, ge=1, le=100), 
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(None)
):
    """Admin only: Danh sách tất cả khóa học với phân trang."""
    if request.headers.get("X-User-Role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    query = db.query(Course)
    
    if q:
        # Sanitize search query to prevent SQL injection
        # Escape special characters for ILIKE pattern matching
        safe_q = q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        search_pattern = f"%{safe_q}%"
        
        # Search across multiple fields using indexes:
        # - title, platform, provider: uses pg_trgm GIN indexes (idx_courses_*_trgm)
        # - tags: uses GIN index (idx_courses_tags_gin) with ANY operator
        # - skills_raw: uses GIN index (idx_courses_skills_raw_gin) with JSONB contains
        query = query.filter(
            or_(
                Course.title.ilike(search_pattern),
                Course.platform.ilike(search_pattern),
                Course.provider.ilike(search_pattern),
                text("(:keyword = ANY(tags))").bindparams(keyword=q),
                text("(skills_raw::jsonb @> to_jsonb(:skill::text))").bindparams(skill=q),
                text("EXISTS (SELECT 1 FROM jsonb_array_elements_text(skills_raw::jsonb) skill WHERE skill ILIKE :pattern)").bindparams(pattern=search_pattern)
            )
        )

    total = query.count()
    items = query.order_by(Course.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "page": (offset // limit) + 1,
        "pages": (total + limit - 1) // limit
    }


@app.post("/recommend/admin/courses", response_model=CourseRead)
async def admin_create_course(
    req: CourseCreate, request: Request, db: Session = Depends(get_db)
):
    """Admin only: Tạo khóa học mới + tạo embedding. Returns existing if duplicate."""
    if request.headers.get("X-User-Role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    # Check if course already exists
    existing = db.query(Course).filter(
        Course.source_platform == req.source_platform,
        Course.source_id == req.source_id
    ).first()
    
    if existing:
        # Return existing course instead of error
        return existing

    from shared.llm_utils import get_embedding

    # Minimal embedding context: Title + Level + Skills only (focused signal)
    context = (
        f"TITLE: {req.title}. "
        f"LEVEL: {req.level or 'Unknown'}. "
        f"SKILLS: {', '.join(req.skills_raw)}."
    )
    vector = get_embedding(context)

    new_course = Course(
        id=uuid.uuid4(),
        title=req.title,
        source_platform=req.source_platform,
        source_id=req.source_id,
        external_uuid=req.external_uuid,
        platform=req.platform,
        url=req.url,
        level=req.level,
        provider=req.provider,
        duration_hours=req.duration_hours,
        duration_raw=req.duration_raw,
        languages=req.languages,
        cost_usd=req.cost_usd,
        skills_raw=req.skills_raw,
        tools_raw=req.tools_raw,
        outcomes=req.outcomes,
        modules=req.modules,
        tags=req.tags,
        embedding_context=context,
        vector=vector,
    )
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return new_course


@app.post("/recommend/admin/courses/bulk")
async def admin_bulk_create_courses(
    req: CourseBulkCreate, request: Request, db: Session = Depends(get_db)
):
    """Admin only: Tạo nhiều khóa học mới trong một transaction."""
    if request.headers.get("X-User-Role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    from shared.llm_utils import get_embedding

    new_courses = []
    for c_req in req.courses:
        # Check if exists (optional but recommended for bulk)
        existing = db.query(Course).filter(
            Course.source_platform == c_req.source_platform,
            Course.source_id == c_req.source_id
        ).first()
        if existing:
            continue

        # Minimal embedding context: Title + Level + Skills only (focused signal)
        context = (
            f"TITLE: {c_req.title}. "
            f"LEVEL: {c_req.level or 'Unknown'}. "
            f"SKILLS: {', '.join(c_req.skills_raw)}."
        )
        vector = get_embedding(context)

        new_course = Course(
            id=uuid.uuid4(),
            title=c_req.title,
            source_platform=c_req.source_platform,
            source_id=c_req.source_id,
            external_uuid=c_req.external_uuid,
            platform=c_req.platform,
            url=c_req.url,
            level=c_req.level,
            provider=c_req.provider,
            duration_hours=c_req.duration_hours,
            duration_raw=c_req.duration_raw,
            languages=c_req.languages,
            cost_usd=c_req.cost_usd,
            skills_raw=c_req.skills_raw,
            tools_raw=c_req.tools_raw,
            outcomes=c_req.outcomes,
            modules=c_req.modules,
            tags=c_req.tags,
            embedding_context=context,
            vector=vector,
        )
        db.add(new_course)
        new_courses.append(new_course)

    db.commit()
    for c in new_courses:
        db.refresh(c)
    
    return {"count": len(new_courses), "status": "success"}


@app.get("/recommend/admin/courses/export")
async def admin_export_courses(
    request: Request, 
    db: Session = Depends(get_db),
    limit: Optional[int] = Query(None, ge=1, le=10000),
    offset: int = Query(0, ge=0)
):
    """Admin only: Export all courses with vectors for backup/migration."""
    if request.headers.get("X-User-Role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    query = db.query(Course).filter(Course.is_active == True)
    
    if limit:
        query = query.limit(limit).offset(offset)
    
    courses = query.all()
    
    # Convert to export format with vectors as lists
    export_data = []
    for course in courses:
        vector_list = course.vector if isinstance(course.vector, list) else list(course.vector) if course.vector else []
        
        export_data.append({
            "id": str(course.id),
            "title": course.title,
            "description": course.description,
            "source_platform": course.source_platform,
            "source_id": course.source_id,
            "external_uuid": course.external_uuid,
            "provider": course.provider,
            "platform": course.platform,
            "url": course.url,
            "level": course.level,
            "is_certification": course.is_certification,
            "duration_hours": course.duration_hours,
            "duration_raw": course.duration_raw,
            "cost_usd": course.cost_usd,
            "languages": course.languages,
            "skills_raw": course.skills_raw,
            "tools_raw": course.tools_raw,
            "outcomes": course.outcomes,
            "modules": course.modules,
            "tags": course.tags,
            "embedding_context": course.embedding_context,
            "vector": vector_list,
            "is_active": course.is_active,
            "created_at": course.created_at.isoformat() if course.created_at else None,
            "updated_at": course.updated_at.isoformat() if course.updated_at else None
        })
    
    return {
        "count": len(export_data),
        "courses": export_data,
        "metadata": {
            "exported_at": datetime.utcnow().isoformat(),
            "total_exported": len(export_data),
            "offset": offset,
            "limit": limit
        }
    }


@app.post("/recommend/admin/courses/import-full")
async def admin_import_courses_full(
    req: CourseFullImportBulk,
    request: Request,
    db: Session = Depends(get_db)
):
    """Admin only: Import courses with pre-computed vectors (skip embedding generation)."""
    if request.headers.get("X-User-Role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    imported = []
    skipped = []
    errors = []

    for c_req in req.courses:
        try:
            # Check if exists
            existing = db.query(Course).filter(
                Course.source_platform == c_req.source_platform,
                Course.source_id == c_req.source_id
            ).first()
            
            if existing:
                skipped.append({
                    "source_platform": c_req.source_platform,
                    "source_id": c_req.source_id,
                    "reason": "Already exists"
                })
                continue

            # Use provided ID or generate new one
            course_id = c_req.id if c_req.id else uuid.uuid4()

            # Create course with provided vector (no embedding generation)
            new_course = Course(
                id=course_id,
                title=c_req.title,
                description=c_req.description,
                source_platform=c_req.source_platform,
                source_id=c_req.source_id,
                external_uuid=c_req.external_uuid,
                platform=c_req.platform,
                url=c_req.url,
                level=c_req.level,
                provider=c_req.provider,
                is_certification=c_req.is_certification,
                duration_hours=c_req.duration_hours,
                duration_raw=c_req.duration_raw,
                languages=c_req.languages,
                cost_usd=c_req.cost_usd,
                skills_raw=c_req.skills_raw,
                tools_raw=c_req.tools_raw,
                outcomes=c_req.outcomes,
                modules=c_req.modules,
                tags=c_req.tags,
                embedding_context=c_req.embedding_context,
                vector=c_req.vector,  # Use pre-computed vector
                is_active=c_req.is_active,
            )
            db.add(new_course)
            imported.append(str(course_id))
            
        except Exception as e:
            errors.append({
                "source_platform": c_req.source_platform,
                "source_id": c_req.source_id,
                "error": str(e)
            })

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database commit failed: {str(e)}")
    
    return {
        "status": "success",
        "imported_count": len(imported),
        "skipped_count": len(skipped),
        "error_count": len(errors),
        "imported_ids": imported,
        "skipped": skipped,
        "errors": errors
    }


@app.patch("/recommend/admin/courses/{course_id}", response_model=CourseRead)
async def admin_update_course(
    course_id: uuid.UUID,
    req: CourseUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Admin only: Cập nhật khóa học + cập nhật embedding nếu cần."""
    if request.headers.get("X-User-Role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    needs_re_embedding = False
    if req.title is not None:
        course.title = req.title
        needs_re_embedding = True
    if req.platform is not None:
        course.platform = req.platform
        needs_re_embedding = True
    if req.source_platform is not None:
        course.source_platform = req.source_platform
        needs_re_embedding = True
    if req.source_id is not None:
        course.source_id = req.source_id
    if req.external_uuid is not None:
        course.external_uuid = req.external_uuid
    if req.level is not None:
        course.level = req.level
        needs_re_embedding = True
    if req.tags is not None:
        course.tags = req.tags
        needs_re_embedding = True
    if req.is_active is not None:
        course.is_active = req.is_active

    if req.url is not None:
        course.url = req.url
    if req.provider is not None:
        course.provider = req.provider
    if req.duration_hours is not None:
        course.duration_hours = req.duration_hours
    if req.duration_raw is not None:
        course.duration_raw = req.duration_raw
    if req.cost_usd is not None:
        course.cost_usd = req.cost_usd
    if req.languages is not None:
        course.languages = req.languages
    if req.skills_raw is not None:
        course.skills_raw = req.skills_raw
        needs_re_embedding = True
    if req.tools_raw is not None:
        course.tools_raw = req.tools_raw
    if req.outcomes is not None:
        course.outcomes = req.outcomes
        needs_re_embedding = True
    if req.modules is not None:
        course.modules = req.modules
        needs_re_embedding = True

    if needs_re_embedding:
        from shared.llm_utils import get_embedding

        # Minimal embedding context: Title + Level + Skills only (focused signal)
        context = (
            f"TITLE: {course.title}. "
            f"LEVEL: {course.level or 'Unknown'}. "
            f"SKILLS: {', '.join(course.skills_raw or [])}."
        )
        course.embedding_context = context
        course.vector = get_embedding(context)

    db.commit()
    db.refresh(course)
    return course


@app.delete("/recommend/admin/courses/{course_id}")
async def admin_delete_course(
    course_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    """Admin only: Xóa khóa học."""
    if request.headers.get("X-User-Role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    db.delete(course)
    db.commit()
    return {"message": "Deleted successfully"}


@app.post("/recommend/admin/courses/crawl")
async def admin_crawl_course(req: CrawlRequest, request: Request):
    """Admin only: Dispatch background task to crawl course data."""
    if request.headers.get("X-User-Role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    task = celery_app.send_task(
        "worker.tasks.crawler_tasks.crawl_course_task",
        args=[req.url],
        queue="market_stats",
    )
    return {"task_id": task.id, "status": "processing"}


@app.get("/recommend/admin/courses/crawl/status/{task_id}")
async def admin_get_crawl_status(task_id: str, request: Request):
    """Admin only: Check crawl task status."""
    if request.headers.get("X-User-Role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    res = AsyncResult(task_id, app=celery_app)
    if res.ready():
        # Task is finished (can be success or fail in app logic)
        result = res.result
        if isinstance(result, dict) and "error" in result:
             return {"status": "failed", "error": result["error"]}
        return {"status": "completed", "result": result}
    return {"status": "processing"}


@app.get("/recommend/admin/youtube", response_model=PaginatedResponse[YouTubeCourseRead])
async def admin_list_youtube(
    request: Request, 
    db: Session = Depends(get_db), 
    limit: int = Query(20, ge=1, le=100), 
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(None)
):
    """Admin only: Danh sách tất cả video YouTube đã cache."""
    if request.headers.get("X-User-Role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    query = db.query(YouTubeCourse)
    
    if q:
        query = query.filter(
            or_(
                YouTubeCourse.title.ilike(f"%{q}%"),
                YouTubeCourse.channel_name.ilike(f"%{q}%")
            )
        )

    total = query.count()
    items = query.order_by(YouTubeCourse.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "page": (offset // limit) + 1,
        "pages": (total + limit - 1) // limit
    }


@app.delete("/recommend/admin/youtube/{video_id}")
async def admin_delete_youtube(
    video_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Admin only: Xóa video YouTube khỏi cache."""
    if request.headers.get("X-User-Role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    video = db.query(YouTubeCourse).filter(YouTubeCourse.video_id == video_id).first()
    if not video:
        # Also try by internal UUID if video_id is not the YouTube ID
        try:
            video_uuid = uuid.UUID(video_id)
            video = db.query(YouTubeCourse).filter(YouTubeCourse.id == video_uuid).first()
        except:
            pass
            
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    db.delete(video)
    db.commit()
    return {"message": "Deleted successfully"}


@app.get("/recommend/youtube")
async def get_youtube_recommendations(
    skill: str, 
    level: str = "Beginner", 
    limit: int = 3, 
    lang: str = "vi",
    domain: str = "programming",
    db: Session = Depends(get_db)
):
    """
    Tìm kiếm video YouTube cho một kỹ năng cụ thể.
    Sử dụng Vector Search để tối ưu cache.
    
    Args:
        skill: Tên kỹ năng (e.g. "Python", "Docker")
        level: Cấp độ (Beginner, Intermediate, Advanced)
        limit: Số lượng video tối đa
        lang: Ngôn ngữ ("vi" hoặc "en")
        domain: Lĩnh vực (programming, devops, data-science, web-development, mobile)
    """
    query = f"{skill} {level}"
    videos = await youtube_service.search_and_cache(query=query, db=db, limit=limit, lang=lang, domain=domain)
    return videos


# ─── Health Check ───────────────────────────────────────────────────────────

@app.get("/recommend/health")
def health_check():
    """Health check endpoint for Docker and monitoring."""
    return {"status": "ok", "service": "recommender_service"}
