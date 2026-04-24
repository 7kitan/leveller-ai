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
from datetime import datetime, timezone
from worker.celery_app import celery_app
from celery.result import AsyncResult

from shared.database import init_db
from services.analysis_service.growth_calculator import (
    calculate_skill_impact,
    calculate_market_sentiment
)

app = FastAPI(title="Analysis Service")

@app.on_event("startup")
async def startup_event():
    init_db()
logger = logging.getLogger("analysis_service")


# ─── Pydantic Schemas ────────────────────────────────────────────────


class GapRequest(BaseModel):
    cv_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    jd_text: Optional[str] = None
    force: bool = False  # If true, bypass ALL caches and recompute


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


class InterviewPrepRequest(BaseModel):
    cv_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    jd_text: Optional[str] = None


class OptimizeCVRequest(BaseModel):
    cv_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    jd_text: Optional[str] = None


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

    # ── Check Daily Quota (Unified QuotaManager) ──────────────────
    from shared.queue_utils import get_queue_length
    from shared.email_utils import notify_queue_delay
    from shared.config_utils import config_manager
    from shared.quota_manager import quota_manager
    
    user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not quota_manager.check_analysis_quota(user, db):
        limit = quota_manager.get_analysis_limit(user)
        raise HTTPException(
            status_code=429, 
            detail=f"Bạn đã đạt giới hạn phân tích trong ngày ({limit} lượt). Vui lòng quay lại vào ngày mai hoặc liên hệ Admin."
        )

    # Check queue length
    q_len = get_queue_length("analysis_queue")
    threshold = int(config_manager.get_setting("queue_threshold") or os.getenv("QUEUE_THRESHOLD", "5"))
    
    if q_len >= threshold:
        user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
        if user and user.email:
            logger.info(f"[ANALYSIS GAP] Queue length {q_len} >= {threshold}. Notifying user {user.email}")
            notify_queue_delay(user.email, q_len)

    try:
        task = celery_app.send_task(
            "worker.tasks.analysis_tasks.run_gap_analysis",
            args=[
                str(user_id),
                str(req.cv_id),
                str(req.job_id) if req.job_id else None,
                req.jd_text,
            ],
            kwargs={"force": req.force}
        )
        logger.info(
            f"[ANALYSIS GAP] Task dispatched — task_id={task.id} | "
            f"cv_id={req.cv_id} | job_id={req.job_id}"
        )
        return {"task_id": task.id, "status": "processing", "queue_position": q_len + 1}
    except Exception as e:
        from shared.system_logger import system_logger
        system_logger.error("Worker", f"Failed to dispatch analysis task: {e}", {"user_id": user_id, "cv_id": str(req.cv_id)})
        raise HTTPException(status_code=500, detail="Hệ thống đang bận, vui lòng thử lại sau.")


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

    # Inject cv_id and job_id into the result for frontend redirection/auto-loading
    result = analysis.result_json or {}
    if isinstance(result, dict):
        result["cv_id"] = str(analysis.cv_id)
        result["job_id"] = str(analysis.job_id) if analysis.job_id else None
        
        # Calculate growth metrics using DB data (NEW ALGORITHM)
        skill_gaps = result.get("skill_gaps") or []
        current_match = float(result.get("overall_match_pct") or 0)
        
        if skill_gaps and analysis.job_id:
            try:
                potential_match, salary_growth, enriched_gaps = calculate_skill_impact(
                    skill_gaps=skill_gaps,
                    job_id=str(analysis.job_id),
                    current_match_pct=current_match,
                    db=db
                )
                
                # Update result with calculated values
                result["potential_match_pct"] = round(potential_match, 1)
                result["salary_growth_pct"] = round(salary_growth, 1)
                result["skill_gaps"] = enriched_gaps  # Now includes match_impact & salary_impact
                
                # Calculate market sentiment from DB data
                if not result.get("market_sentiment"):
                    result["market_sentiment"] = calculate_market_sentiment(skill_gaps, db)
                    
                logger.info(
                    f"Growth calculated from DB: potential={potential_match}%, "
                    f"salary={salary_growth}%, sentiment={result['market_sentiment']}"
                )
            except Exception as e:
                logger.error(f"Error calculating growth metrics: {e}", exc_info=True)
                # Fallback to simple heuristic if calculation fails
                course_count = len(result.get("course_recommendations") or [])
                if course_count > 0:
                    import math
                    result["potential_match_pct"] = min(98, current_match + math.log2(course_count + 1) * 6.5)
                    result["salary_growth_pct"] = min(35, math.log2(course_count + 1) * 5.5 + 5)
                    result["market_sentiment"] = "Ổn định"

    return result


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
    Tối ưu hóa: Chỉ cập nhật 1 lần mỗi ngày khi user truy cập, 
    hoặc khi được trigger từ background worker sau khi phân tích gap.
    """
    user_id_str = request.headers.get("X-User-ID")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    user_id = uuid.UUID(user_id_str)
    from shared.models import User
    from services.analysis_service.market_fit_service import update_user_market_fit

    # 1. Lấy thông tin User và kiểm tra cache
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.now(timezone.utc)
    is_stale = True
    
    if user.market_fit_last_updated:
        # Kiểm tra xem đã qua ngày mới chưa
        last_update = user.market_fit_last_updated
        if last_update.date() == now.date():
            is_stale = False

    # 2. Nếu cache còn hạn, trả về dữ liệu cũ ngay lập tức
    if not is_stale and user.market_fit_data:
        cached_data = user.market_fit_data
        # Migration check: Ensure new growth metrics are present
        has_new_fields = (
            "courses" in cached_data and 
            "top_trending_skills" in cached_data and
            "potential_match_pct" in cached_data
        )
        
        if has_new_fields:
            logger.info(f"[MARKET FIT] Returning cached data for user {user_id}")
            return cached_data
        else:
            logger.info(f"[MARKET FIT] Cache missing new fields for user {user_id}. Forcing recompute...")
            is_stale = True

    # 3. Nếu cache hết hạn, thực hiện tính toán mới thông qua service
    return await update_user_market_fit(user_id, db)


@app.get("/analysis/market-trends")
async def get_market_trends(
    limit: int = 10, 
    category: Optional[str] = None, 
    db: Session = Depends(get_db)
):
    """Lấy danh sách các kỹ năng đang trending trên thị trường."""
    from shared.models import MarketSkillStats
    query = db.query(MarketSkillStats)
    if category:
        query = query.filter(MarketSkillStats.category == category)
        
    trends = query.order_by(MarketSkillStats.growth_rate_30d.desc()).limit(limit).all()
    
    return [
        {
            "skill": t.skill_name,
            "category": t.category,
            "avg_salary": (t.avg_salary_min + t.avg_salary_max) / 2 if t.avg_salary_min else 0,
            "growth": round(t.growth_rate_30d * 100, 1),
            "demand_score": t.demand_score,
            "job_count": t.job_count_30d
        }
        for t in trends
    ]


@app.get("/analysis/skill-value")
async def get_skills_valuation(
    skills: List[str] = Query(...), 
    db: Session = Depends(get_db)
):
    """Ước tính giá trị (mức lương tăng thêm) cho một danh sách kỹ năng."""
    from shared.models import MarketSkillStats
    stats = db.query(MarketSkillStats).filter(MarketSkillStats.skill_name.in_(skills)).all()
    
    valuation = []
    total_premium = 0.0
    
    for s in stats:
        premium_vnd = (s.avg_salary_min * s.salary_premium_pct) if s.avg_salary_min and s.salary_premium_pct else 0
        valuation.append({
            "skill": s.skill_name,
            "premium_pct": round(s.salary_premium_pct * 100, 1) if s.salary_premium_pct else 0,
            "premium_vnd": int(premium_vnd),
            "avg_salary_min": s.avg_salary_min,
            "demand_score": s.demand_score
        })
        total_premium += premium_vnd

    return {
        "skills": valuation,
        "total_estimated_premium_vnd": int(total_premium),
        "note": "Ước tính dựa trên dữ liệu tuyển dụng 30 ngày gần nhất."
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
    if gaps and filled_count > 0:
        # Use a non-linear boost: filling first gaps gives more score (diminishing returns)
        import math
        total_possible_boost = (100 - base_score) * 0.85 # Cap at 85% of the remaining gap
        fill_ratio = filled_count / len(gaps)
        # Apply square root to reward the first few filled gaps more
        boost_amount = total_possible_boost * math.sqrt(fill_ratio)

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


# ─── Admin Testing Endpoints ─────────────────────────────────────────────


@app.post("/analysis/admin/test-email")
async def admin_test_email(request: Request, db: Session = Depends(get_db)):
    """Admin only: Gửi email test để kiểm tra cấu hình SMTP."""
    check_admin(request)
    user_id = request.headers.get("X-User-ID")
    user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    
    if not user or not user.email:
        raise HTTPException(status_code=400, detail="Admin user must have an email address")

    from shared.email_utils import send_email
    success = send_email(
        to_email=user.email,
        subject="[Test] Cấu hình SMTP - Team078",
        content=f"Xin chào {user.email},\n\nĐây là email kiểm tra tính năng SMTP từ hệ thống Admin Dashboard.\nNếu bạn nhận được email này, cấu hình SMTP của bạn đã hoạt động chính xác.\n\nThời gian: {datetime.now().isoformat()}"
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send test email. Check server logs/configs.")
    
    return {"message": f"Test email sent to {user.email}"}


@app.post("/analysis/admin/test-llm")
async def admin_test_llm(request: Request):
    """Admin only: Gọi thử AI Model để kiểm tra cấu hình."""
    check_admin(request)
    from shared.ai_service import generate_completion
    
    t0 = datetime.now()
    response = generate_completion(
        prompt="Say 'AI configuration is working correctly!' in Vietnamese.",
        system_prompt="You are a system tester.",
        call_name="admin_test_call"
    )
    duration = (datetime.now() - t0).total_seconds()
    
    if not response:
        raise HTTPException(status_code=500, detail="AI Model failed to respond. Check API keys and Model IDs.")
    
    return {
        "message": "AI Model is working correctly!",
        "response": response,
        "latency_sec": round(duration, 2)
    }



# ─── Admin Taxonomy Routes ───────────────────────────────────────────────


def check_admin(request: Request):
    if request.headers.get("X-Is-Admin") != "true":
        raise HTTPException(status_code=403, detail="Admin privileges required")


@app.get("/analysis/admin/llm-logs", response_model=PaginatedResponse[dict])
async def admin_get_llm_logs(
    request: Request,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    model_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    """Admin only: Xem lịch sử gọi LLM."""
    check_admin(request)
    from shared.models import LLMLog

    query = db.query(LLMLog, User.email).outerjoin(User, User.id == LLMLog.user_id)
    
    if model_id:
        query = query.filter(LLMLog.model_id == model_id)
    if user_id:
        query = query.filter(LLMLog.user_id == uuid.UUID(user_id))
    if status:
        query = query.filter(LLMLog.status == status)

    total = query.count()
    results = query.order_by(LLMLog.created_at.desc()).offset(offset).limit(limit).all()

    items = [
        {
            "id": str(log.id),
            "user_email": email or "System/Guest",
            "model_id": log.model_id,
            "provider": log.provider,
            "call_type": log.call_type,
            "prompt_tokens": log.prompt_tokens,
            "completion_tokens": log.completion_tokens,
            "total_tokens": log.total_tokens,
            "latency_ms": log.latency_ms,
            "status": log.status,
            "error_message": log.error_message,
            "created_at": log.created_at.isoformat(),
        }
        for log, email in results
    ]
    
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "page": (offset // limit) + 1,
        "pages": (total + limit - 1) // limit
    }


@app.get("/analysis/admin/system-logs", response_model=PaginatedResponse[dict])
async def admin_get_system_logs(
    request: Request,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    level: Optional[str] = Query(None),
    module: Optional[str] = Query(None)
):
    """Admin only: Xem nhật ký hệ thống tập trung."""
    check_admin(request)
    from shared.models import SystemLog

    query = db.query(SystemLog)
    
    if level:
        query = query.filter(SystemLog.level == level)
    if module:
        query = query.filter(SystemLog.module == module)

    total = query.count()
    results = query.order_by(SystemLog.created_at.desc()).offset(offset).limit(limit).all()

    from shared.system_logger import mask_sensitive_data
    items = [
        {
            "id": str(log.id),
            "level": log.level,
            "module": log.module,
            "message": log.message,
            "details": mask_sensitive_data(log.details),
            "created_at": log.created_at.isoformat(),
        }
        for log in results
    ]
    
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "page": (offset // limit) + 1,
        "pages": (total + limit - 1) // limit
    }


@app.get("/analysis/admin/llm-stats")
async def admin_get_llm_stats(request: Request, db: Session = Depends(get_db)):
    """Admin only: Thống kê sử dụng LLM."""
    check_admin(request)
    from shared.models import LLMLog

    # Tổng tokens
    stats = db.query(
        func.sum(LLMLog.prompt_tokens).label("total_prompt"),
        func.sum(LLMLog.completion_tokens).label("total_completion"),
        func.sum(LLMLog.total_tokens).label("total_tokens"),
        func.avg(LLMLog.latency_ms).label("avg_latency"),
        func.count(LLMLog.id).label("total_calls")
    ).first()

    # Tokens theo model
    model_stats = db.query(
        LLMLog.model_id,
        func.sum(LLMLog.total_tokens).label("tokens"),
        func.count(LLMLog.id).label("calls")
    ).group_by(LLMLog.model_id).all()

    # Tokens theo user (top 10)
    user_stats = db.query(
        User.email,
        func.sum(LLMLog.total_tokens).label("tokens"),
        func.count(LLMLog.id).label("calls")
    ).join(User, User.id == LLMLog.user_id).group_by(User.email).order_by(func.sum(LLMLog.total_tokens).desc()).limit(10).all()

    return {
        "summary": {
            "total_calls": stats.total_calls or 0,
            "total_prompt_tokens": int(stats.total_prompt or 0),
            "total_completion_tokens": int(stats.total_completion or 0),
            "total_tokens": int(stats.total_tokens or 0),
            "avg_latency_ms": int(stats.avg_latency or 0),
        },
        "by_model": [
            {"model_id": m.model_id, "tokens": int(m.tokens or 0), "calls": m.calls}
            for m in model_stats
        ],
        "top_users": [
            {"email": u.email, "tokens": int(u.tokens or 0), "calls": u.calls}
            for u in user_stats
        ]
    }


@app.get("/analysis/admin/llm-usage-series")
async def admin_get_llm_usage_series(
    request: Request, 
    period: str = Query("day", regex="^(day|hour)$"),
    days: int = Query(7, ge=1, le=90), # Tăng lên tối đa 90 ngày
    db: Session = Depends(get_db)
):
    """Admin only: Lấy chuỗi dữ liệu sử dụng LLM theo thời gian."""
    check_admin(request)
    from shared.models import LLMLog
    from datetime import timedelta
    
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    if period == "hour":
        time_func = func.date_trunc('hour', LLMLog.created_at)
    else:
        time_func = func.date_trunc('day', LLMLog.created_at)
        
    usage = db.query(
        time_func.label("timestamp"),
        func.sum(LLMLog.total_tokens).label("tokens"),
        func.count(LLMLog.id).label("calls")
    ).filter(LLMLog.created_at >= start_date)\
     .group_by("timestamp")\
     .order_by("timestamp")\
     .all()
     
    return [
        {
            "timestamp": u.timestamp.isoformat(),
            "tokens": int(u.tokens or 0),
            "calls": u.calls
        }
        for u in usage
    ]


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


# ─── New Advanced Features: Mock Interview & CV Optimizer ───────────────


@app.post("/analysis/interview-prep")
async def get_interview_prep(req: InterviewPrepRequest, request: Request, db: Session = Depends(get_db)):
    """
    Tạo bộ câu hỏi phỏng vấn thử dựa trên CV và JD.
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")

    # Verify CV
    cv = db.query(UserCV).filter(UserCV.id == req.cv_id, UserCV.user_id == uuid.UUID(user_id)).first()
    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")

    # Fetch JD
    jd_content = req.jd_text
    if req.job_id:
        job = db.query(Job).filter(Job.id == req.job_id).first()
        if job:
            jd_content = job.raw_text

    from shared.ai_service import generate_completion
    
    prompt = f"""
    Bạn là một chuyên gia tuyển dụng Senior. Dựa trên CV của ứng viên và mô tả công việc (JD) dưới đây, hãy tạo ra 5 câu hỏi phỏng vấn quan trọng nhất tập trung vào các "khoảng cách kỹ năng" (gaps) và các kinh nghiệm then chốt.
    
    CV ỨNG VIÊN:
    {cv.raw_text[:2000]}
    
    MÔ TẢ CÔNG VIỆC:
    {jd_content[:2000] if jd_content else "Thông tin chung cho vị trí này"}
    
    YÊU CẦU:
    Trả về định dạng JSON với danh sách các câu hỏi. Mỗi câu hỏi gồm:
    - question: Nội dung câu hỏi.
    - category: Loại câu hỏi (Technical, Behavioral, Situation).
    - intent: Mục đích của người phỏng vấn khi hỏi câu này.
    - star_hint: Gợi ý cách trả lời theo phương pháp STAR (Situation, Task, Action, Result).
    - ideal_answer_keywords: Các từ khóa nên có trong câu trả lời.
    """

    response = generate_completion(
        prompt=prompt,
        system_prompt="Bạn là một AI Interview Coach chuyên nghiệp. Chỉ trả về JSON.",
        json_mode=True,
        model_key="career_advisor_model",
        call_name="interview_questions",
        user_id=user_id
    )

    try:
        data = json.loads(response)
        return data
    except:
        return {"error": "Failed to parse AI response", "raw": response}


@app.post("/analysis/optimize-cv")
async def optimize_cv_suggestions(req: OptimizeCVRequest, request: Request, db: Session = Depends(get_db)):
    """
    Gợi ý tối ưu hóa CV để tăng điểm khớp với JD.
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")

    cv = db.query(UserCV).filter(UserCV.id == req.cv_id, UserCV.user_id == uuid.UUID(user_id)).first()
    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")

    jd_content = req.jd_text
    if req.job_id:
        job = db.query(Job).filter(Job.id == req.job_id).first()
        if job:
            jd_content = job.raw_text

    from shared.ai_service import generate_completion
    
    prompt = f"""
    Dựa trên CV và JD dưới đây, hãy đưa ra các đề xuất cụ thể để tối ưu hóa CV nhằm đạt điểm tương thích cao nhất.
    
    CV HIỆN TẠI:
    {cv.raw_text[:2000]}
    
    MÔ TẢ CÔNG VIỆC MỤC TIÊU:
    {jd_content[:2000] if jd_content else "Thông tin chung cho vị trí này"}
    
    YÊU CẦU:
    Trả về định dạng JSON gồm:
    - overall_strategy: Chiến lược tổng thể để sửa CV.
    - keyword_suggestions: Các từ khóa/kỹ năng quan trọng nên bổ sung vào CV.
    - content_improvements: Danh sách các đề xuất sửa đổi cụ thể cho từng phần (Summary, Experience, Skills). Mỗi mục gồm 'section', 'original_text' (nếu có), và 'suggested_improvement'.
    - match_score_projection: Dự báo điểm khớp sau khi sửa (+% tăng thêm).
    """

    response = generate_completion(
        prompt=prompt,
        system_prompt="Bạn là một chuyên gia viết CV chuyên nghiệp. Chỉ trả về JSON.",
        json_mode=True,
        model_key="career_advisor_model",
        call_name="cv_optimization",
        user_id=user_id
    )

    try:
        data = json.loads(response)
        return data
    except:
        return {"error": "Failed to parse AI response", "raw": response}
