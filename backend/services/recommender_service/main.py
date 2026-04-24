from fastapi import FastAPI, Depends, Request, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, func, or_
from shared.database import get_db
from shared.models import Course, JobSkillRequirement, Job
from shared.config_utils import config_manager
from shared.level_mapper import LevelMapper
from pydantic import BaseModel, ConfigDict
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

# Thresholds - Now managed via ConfigManager for hot-reloading
VECTOR_SIM_THRESHOLD = float(config_manager.get_setting("similarity_threshold", 0.60))


class GapSkill(BaseModel):
    skill_name: str
    target_level: str = "Mid-level"
    gap_type: str = "MISSING"  # MISSING | PARTIAL
    severity: str = "MEDIUM"  # HIGH | MEDIUM | LOW


class RecommendRequest(BaseModel):
    gap_skills: List[GapSkill]


class CrawlRequest(BaseModel):
    url: str


class CourseCreate(BaseModel):
    title: str
    platform: Optional[str] = None
    source_platform: Optional[str] = "manual"
    source_id: Optional[str] = None
    external_uuid: Optional[str] = None
    url: str
    level: str = "Beginner"
    provider: Optional[str] = None
    duration_hours: Optional[float] = None
    duration_raw: Optional[str] = None
    cost_usd: float = 0.0
    languages: List[str] = ["en"]
    skills_raw: List[str] = []
    tools_raw: List[str] = []
    outcomes: List[str] = []
    modules: List[str] = []
    tags: List[str] = []


class CourseBulkCreate(BaseModel):
    courses: List[CourseCreate]


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
    title: Optional[str] = None
    platform: Optional[str] = None
    source_platform: Optional[str] = None
    source_id: Optional[str] = None
    external_uuid: Optional[str] = None
    url: Optional[str] = None
    level: Optional[str] = None
    provider: Optional[str] = None
    duration_hours: Optional[float] = None
    duration_raw: Optional[str] = None
    cost_usd: Optional[float] = None
    languages: Optional[List[str]] = None
    skills_raw: Optional[List[str]] = None
    tools_raw: Optional[List[str]] = None
    outcomes: Optional[List[str]] = None
    modules: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


def _vector_search_courses(skill_name: str, target_level: str, db, limit: int = 12):
    """pgvector similarity search cho courses. Fallback ILIKE nếu không có vector."""
    from shared.llm_utils import get_embedding

    # Reset any aborted transaction before querying
    try:
        db.rollback()
    except Exception:
        pass

    # Tăng cường search_text để matching tốt hơn với embedding_context mới
    search_text = f"Skill: {skill_name}. Level: {target_level}. Course teaching {skill_name} concepts and applications."
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
            results = db.execute(
                query,
                {
                    "vec": skill_vector,
                    "sim_threshold": VECTOR_SIM_THRESHOLD,
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
        videos = await youtube_service.search_and_cache(
            query=f"{gap.skill_name} {gap.target_level} tutorial",
            db=db,
            limit=2
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
    if request.headers.get("X-Is-Admin") != "true":
        raise HTTPException(status_code=403, detail="Admin privileges required")

    query = db.query(Course)
    
    if q:
        query = query.filter(
            or_(
                Course.title.ilike(f"%{q}%"),
                Course.platform.ilike(f"%{q}%"),
                Course.provider.ilike(f"%{q}%")
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
    """Admin only: Tạo khóa học mới + tạo embedding."""
    if request.headers.get("X-Is-Admin") != "true":
        raise HTTPException(status_code=403, detail="Admin privileges required")

    from shared.llm_utils import get_embedding

    # Tạo context cho embedding - Flat & Rich context
    context = (
        f"PLATFORM: {req.platform or req.source_platform}. "
        f"TITLE: {req.title}. "
        f"PROVIDER: {req.provider or 'Unknown'}. "
        f"DESCRIPTION: {req.title}. " # Fallback if no description in Create
        f"MODULES: {', '.join(req.modules)}. "
        f"SKILLS: {', '.join(req.skills_raw)}. "
        f"OUTCOMES: {', '.join(req.outcomes)}."
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
    if request.headers.get("X-Is-Admin") != "true":
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

        context = (
            f"PLATFORM: {c_req.platform or c_req.source_platform}. "
            f"TITLE: {c_req.title}. "
            f"PROVIDER: {c_req.provider or 'Unknown'}. "
            f"DESCRIPTION: {c_req.title}. "
            f"MODULES: {', '.join(c_req.modules)}. "
            f"SKILLS: {', '.join(c_req.skills_raw)}. "
            f"OUTCOMES: {', '.join(c_req.outcomes)}."
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


@app.patch("/recommend/admin/courses/{course_id}", response_model=CourseRead)
async def admin_update_course(
    course_id: uuid.UUID,
    req: CourseUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Admin only: Cập nhật khóa học + cập nhật embedding nếu cần."""
    if request.headers.get("X-Is-Admin") != "true":
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

        context = (
            f"PLATFORM: {course.platform or course.source_platform}. "
            f"TITLE: {course.title}. "
            f"PROVIDER: {course.provider or 'Unknown'}. "
            f"DESCRIPTION: {course.description or course.title}. "
            f"MODULES: {', '.join(course.modules or [])}. "
            f"SKILLS: {', '.join(course.skills_raw or [])}. "
            f"OUTCOMES: {', '.join(course.outcomes or [])}."
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
    if request.headers.get("X-Is-Admin") != "true":
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
    if request.headers.get("X-Is-Admin") != "true":
        raise HTTPException(status_code=403, detail="Admin privileges required")

    task = celery_app.send_task(
        "worker.tasks.crawler_tasks.crawl_course_task",
        args=[req.url],
    )
    return {"task_id": task.id, "status": "processing"}


@app.get("/recommend/admin/courses/crawl/status/{task_id}")
async def admin_get_crawl_status(task_id: str, request: Request):
    """Admin only: Check crawl task status."""
    if request.headers.get("X-Is-Admin") != "true":
        raise HTTPException(status_code=403, detail="Admin privileges required")

    res = AsyncResult(task_id, app=celery_app)
    if res.ready():
        # Task is finished (can be success or fail in app logic)
        result = res.result
        if isinstance(result, dict) and "error" in result:
             return {"status": "failed", "error": result["error"]}
        return {"status": "completed", "result": result}
    return {"status": "processing"}


@app.get("/recommend/youtube")
async def get_youtube_recommendations(
    skill: str, 
    level: str = "Beginner", 
    limit: int = 3, 
    db: Session = Depends(get_db)
):
    """
    Tìm kiếm video YouTube cho một kỹ năng cụ thể.
    Sử dụng Vector Search để tối ưu cache.
    """
    query = f"{skill} {level} tutorial course"
    videos = await youtube_service.search_and_cache(query=query, db=db, limit=limit)
    return videos
