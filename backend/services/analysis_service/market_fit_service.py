import uuid
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from shared.models import User, UserCV, Job, UserAnalysis, MarketSkillStats

logger = logging.getLogger("market_fit_service")

async def update_user_market_fit(user_id: uuid.UUID, db: Session) -> dict:
    """
    Tính toán và cập nhật dữ liệu Market Fit cho User.
    Hàm này có thể được gọi từ API hoặc từ Background Worker sau khi phân tích Gap.
    """
    logger.info(f"[MARKET FIT] Updating data for user {user_id}...")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.error(f"[MARKET FIT] User {user_id} not found")
        return {}

    now = datetime.now(timezone.utc)
    
    # 1. Lấy CV mới nhất của user
    latest_cv = db.query(UserCV).filter(
        UserCV.user_id == user_id, 
        UserCV.status == "completed"
    ).order_by(UserCV.created_at.desc()).first()

    total_jobs = db.query(Job).filter(Job.status == "active").count()
    
    if not latest_cv:
        market_fit_data = {
            "matched_jobs": 0,
            "market_fit_pct": 0,
            "potential_match_pct": 0,
            "salary_growth_pct": 0,
            "market_sentiment": "",
            "total_jobs": total_jobs,
            "percentile": 0,
            "top_trending_skills": [],
            "last_updated": now.isoformat()
        }
    else:
        # 2. Lấy analysis mới nhất cho CV này
        latest_analysis = db.query(UserAnalysis).filter(
            UserAnalysis.cv_id == latest_cv.id
        ).order_by(UserAnalysis.created_at.desc()).first()

        matched_jobs_count = 0
        market_fit_pct = 0
        potential_match_pct = 0
        salary_growth_pct = 0
        market_sentiment = ""
        courses_to_return = []
        
        if latest_analysis and latest_analysis.result_json:
            res = latest_analysis.result_json
            course_recs = res.get("course_recommendations") or []
            matched_jobs_count = len(course_recs)
            market_fit_pct = int(float(res.get("overall_match_pct") or 0))
            
            # Get from LLM or fallback to heuristic
            potential_match_pct = int(float(res.get("potential_match_pct") or 0))
            salary_growth_pct = int(float(res.get("salary_growth_pct") or 0))
            market_sentiment = res.get("market_sentiment") or ""
            courses_to_return = course_recs
            
            # Heuristic fallback if LLM hasn't provided these yet (e.g. old analysis)
            if potential_match_pct == 0 and matched_jobs_count > 0:
                potential_match_pct = min(98, market_fit_pct + (matched_jobs_count * 5))
            if salary_growth_pct == 0 and matched_jobs_count > 0:
                salary_growth_pct = matched_jobs_count * 8
            if not market_sentiment and matched_jobs_count > 0:
                market_sentiment = "Tăng trưởng cao" if matched_jobs_count > 3 else "Ổn định"

        # 3. Lấy Trending Skills
        trends = db.query(MarketSkillStats).order_by(MarketSkillStats.growth_rate_30d.desc()).limit(5).all()
        trending_skills = [
            {"name": t.skill_name, "growth": round(t.growth_rate_30d * 100, 1), "demand": t.demand_score}
            for t in trends
        ]

        # 4. Tính Percentile
        percentile = min(99, int((matched_jobs_count / 10) * 100)) if matched_jobs_count > 0 else 0

        market_fit_data = {
            "matched_jobs": matched_jobs_count,
            "market_fit_pct": market_fit_pct,
            "potential_match_pct": potential_match_pct,
            "salary_growth_pct": salary_growth_pct,
            "market_sentiment": market_sentiment,
            "courses": courses_to_return[:6],
            "total_jobs": total_jobs,
            "percentile": percentile,
            "top_trending_skills": trending_skills,
            "last_updated": now.isoformat()
        }

    # 5. Lưu vào Cache (Database)
    user.market_fit_score = float(market_fit_data.get("market_fit_pct", 0))
    user.market_fit_last_updated = now
    user.market_fit_data = market_fit_data
    
    db.commit()
    logger.info(f"[MARKET FIT] Successfully updated data for user {user_id}")
    return market_fit_data
