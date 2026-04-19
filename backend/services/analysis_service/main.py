"""
Analysis Service — Gap Analysis + Feedback + Simulation APIs.
Spec: 1.9 Skill Gap, 1.10 Course Recommendations, 1.11 Career Roadmap,
      2.1 Feedback, 2.2 System Improvement, 3.2 Transparency, 4.2 History.
"""

from fastapi import FastAPI, Request, HTTPException, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from shared.database import get_db
from shared.redis_client import result_cache
from shared.schemas import PaginatedResponse
from shared.taxonomy_service import taxonomy_service
from shared.models import User, UserAnalysis, UserFeedback, Job, UserCV
from pydantic import BaseModel
from typing import Optional, List
import uuid
import json
import logging
from worker.celery_app import celery_app
from celery.result import AsyncResult

app = FastAPI(title="Analysis Service")
logger = logging.getLogger("analysis_service")


# ─── Pydantic Schemas ────────────────────────────────────────────────


class GapRequest(BaseModel):
    cv_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    jd_text: Optional[str] = None


class FeedbackRequest(BaseModel):
    """Spec 2.1: User feedback cho analysis accuracy."""

    analysis_id: str
    rating: int
    is_accurate: bool
    missing_skills: List[str] = []
    comment: Optional[str] = None


class SimulateRequest(BaseModel):
    cv_id: uuid.UUID
    selected_course_ids: List[uuid.UUID]
    job_id: Optional[uuid.UUID] = None


class SimulateBoostRequest(BaseModel):
    cv_id: uuid.UUID
    selected_course_ids: List[uuid.UUID]
    job_id: Optional[uuid.UUID] = None


# ─── 1.9 + 4.2: Gap Analysis Endpoints ─────────────────────────────────


@app.post("/analysis/gap")
async def start_gap_analysis(
    req: GapRequest, request: Request, db: Session = Depends(get_db)
):
    """
    Trigger gap analysis cho CV vs JD.
    Xử lý bất đồng bộ qua Celery task (gap_v3 khi USE_LLM_GAP_AGENT_V3=true).
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")

    logger.info(
        f"[ANALYSIS GAP] start_gap_analysis — "
        f"user_id={user_id} | cv_id={req.cv_id} | "
        f"job_id={req.job_id} | jd_text={'provided' if req.jd_text else 'None'}"
    )

    # Verify CV belongs to this user
    cv = (
        db.query(UserCV)
        .filter(
            UserCV.id == req.cv_id,
            UserCV.user_id == uuid.UUID(user_id),
        )
        .first()
    )
    if not cv:
        logger.warning(
            f"[ANALYSIS GAP] CV not found or unauthorized — cv_id={req.cv_id} user_id={user_id}"
        )
        raise HTTPException(status_code=404, detail="CV not found or unauthorized")

    # Verify CV is completed
    if cv.status != "completed":
        logger.warning(
            f"[ANALYSIS GAP] CV not ready — cv_id={req.cv_id} status={cv.status}"
        )
        raise HTTPException(
            status_code=400,
            detail=f"CV chưa hoàn tất phân tích (status={cv.status}). Vui lòng đợi CV được xử lý xong.",
        )

    task = celery_app.send_task(
        "worker.tasks.analysis_tasks.run_gap_analysis",
        args=[
            str(user_id),
            str(req.cv_id),
            str(req.job_id) if req.job_id else None,
            req.jd_text,
        ],
    )
    logger.info(
        f"[ANALYSIS GAP] Task dispatched — task_id={task.id} | "
        f"cv_id={req.cv_id} | job_id={req.job_id}"
    )
    return {"task_id": task.id, "status": "processing"}


@app.get("/analysis/status/{task_id}")
async def get_task_status(task_id: str):
    res = AsyncResult(task_id, app=celery_app)
    state = res.state

    logger.info(
        f"[ANALYSIS STATUS] task_id={task_id} | state={state} | "
        f"ready={res.ready()} | result_type={type(res.result).__name__}"
    )

    if res.ready():
        result = res.result
        if isinstance(result, dict) and "error" in result:
            logger.error(
                f"[ANALYSIS STATUS] task FAILED — task_id={task_id} error={result['error']}"
            )
            raise HTTPException(status_code=500, detail=result["error"])

        # Log success summary
        if isinstance(result, dict):
            logger.info(
                f"[ANALYSIS STATUS] task SUCCESS — task_id={task_id}\n"
                f"  overall_match_pct : {result.get('overall_match_pct')}\n"
                f"  skill_gaps        : {len(result.get('skill_gaps', []))}\n"
                f"  recommended_courses: {len(result.get('recommended_courses', []))}\n"
                f"  career_roadmap    : {bool(result.get('career_roadmap'))}"
            )
        return {"status": "completed", "result": result}

    if state == "PROGRESS":
        return {
            "status": "processing",
            "progress": res.info.get("percent", 0),
            "message": res.info.get("message", "Processing...")
        }

    return {"status": "processing"}
    
    
@app.delete("/analysis/status/{task_id}")
async def revoke_analysis_task(task_id: str):
    """
    Dừng phân tích gap đang chạy.
    """
    logger.info(f"[ANALYSIS REVOKE] Request for task_id={task_id}")
    res = AsyncResult(task_id, app=celery_app)
    res.revoke(terminate=True)
    return {"message": "Task revoked", "task_id": task_id}


@app.post("/analysis/notify/{task_id}")
async def register_notification(task_id: str, request: Request):
    """
    Đăng ký nhận thông báo khi task hoàn thành.
    Hiện tại log lại để giả lập, sau này có thể tích hợp email/push.
    """
    user_id = request.headers.get("X-User-ID")
    logger.info(f"[ANALYSIS NOTIFY] User {user_id} requested notification for task {task_id}")
    
    # Store in Redis or DB for the worker to check later
    result_cache.set(f"notify_me:{task_id}", user_id, ex=3600*24)
    
    return {"message": "Chúng tôi sẽ thông báo cho bạn khi kết quả sẵn sàng."}


@app.get("/analysis/user/latest")
async def get_latest_analysis(request: Request, db: Session = Depends(get_db)):
    """Lấy kết quả analysis gần nhất của user."""
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")

    analysis = (
        db.query(UserAnalysis)
        .filter(UserAnalysis.user_id == uuid.UUID(user_id))
        .order_by(UserAnalysis.created_at.desc())
        .first()
    )

    if not analysis:
        return None

    return analysis.result_json or {}


@app.get("/analysis/user/history")
async def get_user_analysis_history(
    request: Request,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """
    Spec 4.2: Lấy lịch sử tất cả analysis của user.
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")

    analyses = (
        db.query(UserAnalysis)
        .filter(UserAnalysis.user_id == uuid.UUID(user_id))
        .order_by(UserAnalysis.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": str(a.id),
            "cv_id": str(a.cv_id),
            "job_id": str(a.job_id) if a.job_id else None,
            "match_score": a.match_score,
            "created_at": a.created_at.isoformat() if a.created_at else None,
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


@app.get("/analysis/user/cv/{cv_id}")
async def get_cv_analysis(cv_id: str, request: Request, db: Session = Depends(get_db)):
    """Lấy kết quả analysis cho 1 CV cụ thể."""
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")

    analysis = (
        db.query(UserAnalysis)
        .filter(
            UserAnalysis.user_id == uuid.UUID(user_id),
            UserAnalysis.cv_id == uuid.UUID(cv_id),
        )
        .order_by(UserAnalysis.created_at.desc())
        .first()
    )

    if not analysis:
        raise HTTPException(
            status_code=404,
            detail="No analysis found for this CV. Start a new analysis.",
        )

    return analysis.result_json or {}


@app.get("/analysis/recommendations")
async def get_recommendations(request: Request, db: Session = Depends(get_db)):
    """
    Lấy danh sách gợi ý công việc dựa trên phân tích mới nhất.
    Ánh xạ từ result_json sang format RecommendedJob của frontend.
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")

    analysis = (
        db.query(UserAnalysis)
        .filter(UserAnalysis.user_id == uuid.UUID(user_id))
        .order_by(UserAnalysis.created_at.desc())
        .first()
    )

    if not analysis or not analysis.result_json:
        return []

    # Giả định result_json có key 'job_recommendations' hoặc dữ liệu tương tự
    # Nếu không có, return danh sách mẫu hoặc trending (mock logic)
    raw_recs = analysis.result_json.get(
        "job_recommendations"
    ) or analysis.result_json.get("recommendations", [])

    return [
        {
            "title": r.get("title") or r.get("job_title", "Software Engineer"),
            "match_score": int(r.get("match_score", 85)),
            "market_demand": r.get("market_demand", "high"),
            "top_skillsRequired": r.get("top_skills") or r.get("required_skills", []),
            "career_path": r.get("career_path", "Senior Level"),
        }
        for r in raw_recs
    ]


@app.get("/analysis/market-fit")
async def get_market_fit(request: Request, db: Session = Depends(get_db)):
    """
    Dashboard API: Trả về tóm tắt sự tương thích của user với thị trường.
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")

    # 1. Tổng số jobs đang active
    total_jobs = db.query(Job).filter(Job.status == "active").count()

    # 2. Lấy analysis mới nhất cho user này
    latest = (
        db.query(UserAnalysis)
        .filter(UserAnalysis.user_id == uuid.UUID(user_id))
        .order_by(UserAnalysis.created_at.desc())
        .first()
    )

    if not latest or not latest.result_json:
        return {"matched_jobs": 0, "market_fit_pct": 0, "total_jobs": total_jobs}

    # 3. Trích xuất matched_jobs và market_fit_pct
    # Hệ thống mới: dùng course_recommendations từ gap analysis v3
    # (job_recommendations không còn được tạo trong pipeline v3)
    course_recommendations = latest.result_json.get("course_recommendations") or []
    matched_jobs = len(course_recommendations)

    # market_fit_pct: lấy từ overall_match_pct hoặc tính từ rank_score
    market_fit_pct = int(float(latest.result_json.get("overall_match_pct") or 0))

    # Fallback: nếu không có overall_match_pct, tính từ course rank_scores
    if market_fit_pct == 0 and course_recommendations:
        fit_scores = [
            int(float(c.get("rank_score") or 0) * 100)
            for c in course_recommendations
            if c.get("rank_score")
        ]
        market_fit_pct = max(fit_scores) if fit_scores else 0

    return {
        "matched_jobs": matched_jobs,
        "market_fit_pct": market_fit_pct,
        "total_jobs": total_jobs,
        "courses": course_recommendations,  # Forward full course data to frontend
    }


@app.get("/analysis/admin/cvs", response_model=PaginatedResponse[dict])
async def admin_get_all_cvs(
    request: Request, 
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(None)
):
    """Admin only: Xem tất cả CV trong hệ thống với phân trang."""
    check_admin(request)

    query = db.query(UserCV, User.email).join(User, User.id == UserCV.user_id)
    
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
            "created_at": cv.created_at.isoformat(),
            "file_url": f"/api/cv/download/{cv.id}",
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


@app.delete("/analysis/admin/cvs/{cv_id}")
async def admin_delete_cv(
    cv_id: uuid.UUID, request: Request, db: Session = Depends(get_db)
):
    """Admin only: Xóa CV bất kỳ."""
    check_admin(request)

    cv = db.query(UserCV).filter(UserCV.id == cv_id).first()
    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")

    db.delete(cv)
    db.commit()
    return {"message": "CV deleted"}


# ─── 2.1 + 2.2: Feedback Loop ─────────────────────────────────────────


@app.post("/analysis/feedback")
async def submit_feedback(
    req: FeedbackRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Spec 2.1: Thu thập phản hồi.
    Spec 2.2: Cải thiện hệ thống — lưu feedback để recalibrate weights.
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")

    # Validate rating 1-5
    if not (1 <= req.rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be 1-5")

    fb = UserFeedback(
        user_id=uuid.UUID(user_id),
        analysis_id=req.analysis_id,
        rating=req.rating,
        is_accurate=req.is_accurate,
        missing_skills=req.missing_skills,
        comment=req.comment,
    )
    db.add(fb)
    db.commit()

    logger.info(
        f"Feedback saved: analysis={req.analysis_id} rating={req.rating} "
        f"accurate={req.is_accurate} missing={req.missing_skills}"
    )

    return {"message": "Feedback submitted successfully", "feedback_id": str(fb.id)}


@app.get("/analysis/user/feedback-history")
async def get_feedback_history(
    request: Request,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Lịch sử feedback của user (spec 2.1)."""
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")

    feedbacks = (
        db.query(UserFeedback)
        .filter(UserFeedback.user_id == uuid.UUID(user_id))
        .order_by(UserFeedback.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": str(fb.id),
            "analysis_id": fb.analysis_id,
            "rating": fb.rating,
            "is_accurate": fb.is_accurate,
            "missing_skills": fb.missing_skills or [],
            "comment": fb.comment,
            "created_at": fb.created_at.isoformat() if fb.created_at else None,
        }
        for fb in feedbacks
    ]


# ─── 1.11: Simulation ─────────────────────────────────────────────────


@app.post("/analysis/simulate")
async def simulate_roadmap(
    req: SimulateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Spec 1.11: Tạo career roadmap dựa trên khóa học đã chọn.
    Ưu tiên: LLM synthesizer (v3) → fallback basic stages.
    """
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

    unique_skills = list(set(gained_skills))

    # Ưu tiên: LLM roadmap synthesis
    try:
        import asyncio
        from worker.langgraph_agents.gap_v3.nodes.finalize_nodes import (
            roadmap_synthesis_node,
        )

        gap_state = {
            "cv_id": str(req.cv_id),
            "user_id": user_id,
            "gap_analysis": {
                "skill_gaps": [
                    {
                        "skill": tag,
                        "severity": "MEDIUM",
                        "estimated_months": 1.0,
                        "learning_effort": "MEDIUM",
                        "learning_path": "",
                    }
                    for tag in unique_skills[:5]
                ],
                "jd_context": "Custom learning path",
            },
            "course_recommendations": [
                {
                    "course_id": str(c.id),
                    "title": c.title,
                    "platform": c.platform,
                    "url": c.url,
                    "level": c.level,
                    "provider": c.provider,
                    "duration_hours": c.duration_hours or 0,
                    "is_certification": c.is_certification,
                    "cost_usd": c.cost_usd or 0,
                    "tags": c.tags or [],
                    "gap_skill": (c.tags[0] if c.tags else "General"),
                    "gap_severity": "MEDIUM",
                    "gap_learning_path": "",
                    "gap_estimated_months": 1,
                    "is_critical": False,
                    "selection_reason": "",
                    "similarity": 0.7,
                }
                for c in courses
            ],
            "db": db,
            "status": "started",
            "error": None,
        }

        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(roadmap_synthesis_node(gap_state))

        roadmap = result.get("career_roadmap") or {}
        if roadmap:
            return {
                "virtual_skills_gained": unique_skills,
                "estimated_duration_hours": total_hours,
                "estimated_duration_weeks": round(total_hours / 10),
                "career_roadmap": roadmap,
                "method": "llm_synthesized",
            }

    except Exception as e:
        logger.warning(f"LLM roadmap failed, using basic fallback: {e}")

    # Fallback: basic stages
    roadmap_stages = []
    for i, c in enumerate(courses[:4]):
        course_skills = list(set(c.tags)) if c.tags else []
        roadmap_stages.append(
            {
                "stage": i + 1,
                "focus": c.title,
                "duration_weeks": max(1, round((c.duration_hours or 10) / 10)),
                "courses": [c.title],
                "skills_acquired": course_skills,
                "milestones": [{"week": 1, "milestone": f"Hoàn thành khóa {c.title}"}],
            }
        )

    total_weeks = sum(s["duration_weeks"] for s in roadmap_stages)

    return {
        "virtual_skills_gained": unique_skills,
        "estimated_duration_hours": total_hours,
        "estimated_duration_weeks": total_weeks,
        "career_roadmap": {
            "stages": roadmap_stages,
            "total_weeks": total_weeks,
            "total_hours": total_hours,
            "summary": f"Lộ trình tự học {len(courses)} khóa học trong ~{total_weeks} tuần",
        },
        "method": "basic_fallback",
    }


@app.post("/analysis/simulate-boost")
async def simulate_boost(
    req: SimulateBoostRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Giả lập tăng trưởng (What-if): Tính toán điểm tiềm năng khi hoàn thành các khóa học.
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")

    # 1. Lấy analysis hiện tại
    latest = (
        db.query(UserAnalysis)
        .filter(
            UserAnalysis.user_id == uuid.UUID(user_id),
            UserAnalysis.cv_id == req.cv_id,
        )
        .order_by(UserAnalysis.created_at.desc())
        .first()
    )

    if not latest or not latest.result_json:
        raise HTTPException(status_code=404, detail="No base analysis found to simulate boost")

    from shared.models import Course, Skill
    courses = db.query(Course).filter(Course.id.in_(req.selected_course_ids)).all()
    
    # Lấy tất cả skills/tags từ các khóa học được chọn
    boost_skills = set()
    for c in courses:
        if c.tags:
            for tag in c.tags:
                boost_skills.add(tag.strip())

    # Map categories for boost_skills
    skill_entities = db.query(Skill).filter(Skill.name.in_(list(boost_skills))).all()
    skill_to_cat = {s.name.lower(): s.category for s in skill_entities}

    # Duyệt qua các gap trong analysis hiện tại và giả lập lấp đầy
    result = latest.result_json.copy()
    gaps = result.get("skill_gaps", [])
    
    virtual_gaps = []
    filled_count = 0
    for g in gaps:
        skill_name = g.get("skill", "").lower()
        is_filled = False
        for bs in boost_skills:
            if bs.lower() == skill_name:
                is_filled = True
                break
        
        if is_filled:
            # Giả lập lấp đầy gap này
            new_gap = g.copy()
            new_gap["is_virtual_filled"] = True
            new_gap["severity"] = "LOW" # Giảm mức độ nghiêm trọng xuống thấp nhất
            virtual_gaps.append(new_gap)
            filled_count += 1
        else:
            virtual_gaps.append(g)

    # Tính toán điểm tiềm năng (Virtual Match Score)
    base_score = float(result.get("overall_match_pct", 0))
    boost_amount = 0
    if gaps:
        boost_per_gap = (100 - base_score) / max(len(gaps), 1)
        boost_amount = filled_count * boost_per_gap * 0.8 

    potential_score = min(98.5, base_score + boost_amount)

    return {
        "base_score": base_score,
        "potential_score": round(potential_score, 1),
        "boost_amount": round(boost_amount, 1),
        "filled_skills": [
            {"name": s, "category": skill_to_cat.get(s.lower(), "Technology")} 
            for s in boost_skills
        ],
        "virtual_gaps": virtual_gaps,
        "is_simulated": True
    }



# ─── Admin Taxonomy Routes ───────────────────────────────────────────────


def check_admin(request: Request):
    if request.headers.get("X-Is-Admin") != "true":
        raise HTTPException(status_code=403, detail="Admin privileges required")


@app.get("/analysis/admin/stats")
async def admin_get_stats(request: Request, db: Session = Depends(get_db)):
    """Admin only: Lấy thống kê tổng quan hệ thống."""
    check_admin(request)
    
    user_count = db.query(User).count()
    cv_count = db.query(UserCV).count()
    job_count = db.query(Job).filter(Job.status == "active").count()
    
    # Tính điểm market fit trung bình
    avg_fit = db.query(func.avg(UserAnalysis.match_score)).scalar() or 0.0
    
    return {
        "users": user_count,
        "cvs": cv_count,
        "jobs": job_count,
        "marketFits": round(float(avg_fit), 1)
    }


class SkillCreate(BaseModel):
    name: str
    category: str = "Technology"
    type: str = "Skill"
    aliases: List[str] = []


class LinkRequest(BaseModel):
    parent: str
    child: str
    rel_type: str = "COMPRISED_OF"


@app.get("/analysis/admin/taxonomy/skills")
async def get_taxonomy_skills(request: Request, limit: int = 100, skip: int = 0):
    check_admin(request)
    return taxonomy_service.get_all_skills(limit, skip)


@app.post("/analysis/admin/taxonomy/skills")
async def manage_skill(skill: SkillCreate, request: Request):
    check_admin(request)
    taxonomy_service.create_or_update_skill(
        name=skill.name,
        category=skill.category,
        skill_type=skill.type,
        aliases=skill.aliases,
    )
    return {"message": "Skill managed", "name": skill.name}


@app.delete("/analysis/admin/taxonomy/skills/{name}")
async def delete_skill(name: str, request: Request):
    check_admin(request)
    taxonomy_service.delete_skill(name)
    return {"message": f"Skill {name} deleted"}


@app.post("/analysis/admin/taxonomy/link")
async def link_skills(req: LinkRequest, request: Request):
    check_admin(request)
    taxonomy_service.link_skills(req.parent, req.child, req.rel_type)
    return {"message": f"Linked {req.parent} → {req.child}"}


@app.get("/analysis/admin/taxonomy/relationships/grouped")
async def get_relationships_grouped(
    request: Request, limit: int = 200, type: Optional[str] = None
):
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
    return {"message": f"Deleted {rel_type} {parent} → {child}"}


# ─── Frontend Entity Alignment ───────────────────────────────────────────


@app.get("/analysis/admin/taxonomy/entities")
async def admin_get_entities(request: Request):
    """Alignment với TaxonomyAdminPage của frontend."""
    check_admin(request)
    skills = taxonomy_service.get_all_skills(limit=500, skip=0)
    # Map Skill -> TaxonomyEntity {id, reference_name, aliases}
    return [
        {
            "id": s["name"],  # Sử dụng name làm ID cho graph mapping
            "reference_name": s["name"],
            "aliases": s.get("aliases", []),
        }
        for s in skills
    ]


@app.post("/analysis/admin/taxonomy/entities")
async def admin_create_entity(req: dict, request: Request):
    check_admin(request)
    name = req.get("reference_name")
    aliases = req.get("aliases", [])
    if not name:
        raise HTTPException(status_code=400, detail="Missing reference_name")

    taxonomy_service.create_or_update_skill(name=name, aliases=aliases)
    return {"id": name, "reference_name": name, "aliases": aliases}


@app.put("/analysis/admin/taxonomy/entities/{entity_id}")
async def admin_update_entity(entity_id: str, req: dict, request: Request):
    check_admin(request)
    # Trong Neo4j, update thường là create_or_update
    name = req.get("reference_name") or entity_id
    aliases = req.get("aliases", [])
    taxonomy_service.create_or_update_skill(name=name, aliases=aliases)
    return {"id": name, "reference_name": name, "aliases": aliases}


@app.delete("/analysis/admin/taxonomy/entities/{entity_id}")
async def admin_delete_entity(entity_id: str, request: Request):
    check_admin(request)
    taxonomy_service.delete_skill(entity_id)
    return {"message": "Entity deleted"}
