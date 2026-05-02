import uuid
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from shared.models import User, UserCV, UserAnalysis, Job, MarketSkillStats
from datetime import datetime, timezone
import logging
from services.analysis_service.growth_calculator import (
    calculate_skill_impact,
    calculate_market_sentiment
)

logger = logging.getLogger("market_fit_service")

async def update_user_market_fit(user_id: uuid.UUID, db: Session, cv_id: uuid.UUID = None) -> dict:
    """
    Tính toán và cập nhật dữ liệu Market Fit cho User.
    Hàm này có thể được gọi từ API hoặc từ Background Worker sau khi phân tích Gap.
    """
    logger.info(f"[MARKET FIT] Updating data for user {user_id} | cv_id={cv_id}...")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.error(f"[MARKET FIT] User {user_id} not found")
        return {}

    now = datetime.now(timezone.utc)
    
    # 1. Lấy CV (Ưu tiên cv_id nếu truyền vào, không thì lấy cái mới nhất)
    if cv_id:
        latest_cv = db.query(UserCV).filter(UserCV.id == cv_id).first()
    else:
        latest_cv = db.query(UserCV).filter(
            UserCV.user_id == user_id, 
            UserCV.status == "completed"
        ).order_by(UserCV.created_at.desc()).first()

    total_jobs = db.query(Job).filter(Job.status == "active").count()
    
    # Get Trending Skills (for all users, regardless of CV status)
    trends = db.query(MarketSkillStats).filter(
        MarketSkillStats.demand_score.isnot(None)
    ).order_by(
        MarketSkillStats.demand_score.desc()
    ).limit(5).all()
    
    trending_skills = [
        {
            "name": t.skill_name, 
            "growth": round(t.growth_rate_30d * 100, 1) if t.growth_rate_30d else 0, 
            "demand": t.demand_score,
            "avg_salary": (t.avg_salary_min + t.avg_salary_max) / 2 if t.avg_salary_min and t.avg_salary_max else (t.avg_salary_min or t.avg_salary_max or 0)
        }
        for t in trends
    ]
    
    if not latest_cv:
        market_fit_data = {
            "matched_jobs": 0,
            "market_fit_pct": 0,
            "potential_match_pct": 0,
            "salary_growth_pct": 0,
            "market_sentiment": "",
            "total_jobs": total_jobs,
            "percentile": 0,
            "top_trending_skills": trending_skills,
            "last_updated": now.isoformat()
        }
    else:
        # 2. Lấy analysis mới nhất cho CV này (Ưu tiên last_analysis_id nếu khớp CV)
        latest_analysis = None
        if user.last_analysis_id:
            latest_analysis = db.query(UserAnalysis).filter(
                UserAnalysis.id == user.last_analysis_id,
                UserAnalysis.cv_id == latest_cv.id
            ).first()
            
        if not latest_analysis:
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
            from services.analysis_service.result_normalizer import normalize_analysis_result
            res = normalize_analysis_result(latest_analysis.result_json)
            course_recs = res.get("course_recommendations") or []
            matched_jobs_count = len(course_recs)
            market_fit_pct = int(float(res.get("overall_match_pct") or 0))
            
            # Calculate growth metrics using DB data (NO SALARY)
            skill_gaps = res.get("skill_gaps") or []
            
            if skill_gaps and latest_analysis.job_id:
                try:
                    potential_match_pct, _ = calculate_skill_impact(
                        skill_gaps=skill_gaps,
                        job_id=str(latest_analysis.job_id),
                        current_match_pct=market_fit_pct,
                        db=db
                    )
                    
                    market_sentiment = calculate_market_sentiment(skill_gaps, db)
                    
                    logger.info(
                        f"Market fit calculated from DB: potential={potential_match_pct}%"
                    )
                except Exception as e:
                    logger.error(f"Error calculating market fit: {e}", exc_info=True)
                    # Fallback to simple heuristic
                    potential_match_pct = min(98, market_fit_pct + (matched_jobs_count * 5))
                    market_sentiment = "Tăng trưởng cao" if matched_jobs_count > 3 else "Ổn định"
            else:
                # Fallback if no skill_gaps or job_id
                potential_match_pct = int(float(res.get("potential_match_pct") or 0))
                market_sentiment = res.get("market_sentiment") or ""
                
                if potential_match_pct == 0 and matched_jobs_count > 0:
                    potential_match_pct = min(98, market_fit_pct + (matched_jobs_count * 5))
                if not market_sentiment and matched_jobs_count > 0:
                    market_sentiment = "Tăng trưởng cao" if matched_jobs_count > 3 else "Ổn định"
            
            courses_to_return = course_recs

        # 4. Tính Percentile
        percentile = min(99, int((matched_jobs_count / 10) * 100)) if matched_jobs_count > 0 else 0

        market_fit_data = {
            "matched_jobs": matched_jobs_count,
            "market_fit_pct": market_fit_pct,
            "potential_match_pct": potential_match_pct,
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


async def get_market_trends(db: Session, period: str = "month") -> dict:
    """
    Tính toán xu hướng thị trường theo ngày/tuần/tháng.
    period: 'day', 'week', 'month'
    """
    from shared.models import MarketSkillHistory, MarketSkillStats
    from sqlalchemy import func
    from datetime import timedelta

    now = datetime.now()
    if period == "day":
        start_date = now - timedelta(days=2) # So sánh hôm nay vs hôm qua
        days_to_show = 2
    elif period == "week":
        start_date = now - timedelta(days=8) # So sánh tuần này vs tuần trước
        days_to_show = 7
    else: # month
        start_date = now - timedelta(days=31)
        days_to_show = 30

    # 1. Lấy Top 10 skills có demand cao nhất hiện tại
    top_stats = db.query(MarketSkillStats).order_by(MarketSkillStats.demand_score.desc()).limit(10).all()
    top_skill_names = [s.skill_name for s in top_stats]

    # 2. Lấy lịch sử của các skill này trong period
    history = db.query(MarketSkillHistory).filter(
        MarketSkillHistory.skill_name.in_(top_skill_names),
        MarketSkillHistory.snapshot_date >= start_date
    ).order_by(MarketSkillHistory.snapshot_date.asc()).all()

    # Nhóm history theo skill
    skill_hist = {}
    for h in history:
        if h.skill_name not in skill_hist:
            skill_hist[h.skill_name] = []
        skill_hist[h.skill_name].append({
            "date": h.snapshot_date.strftime("%Y-%m-%d"),
            "demand": h.demand_score,
            "count": h.job_count
        })

    # 3. Tính toán top tăng/giảm
    trending_results = []
    for s in top_stats:
        s_name = s.skill_name
        import hashlib
        name_hash = int(hashlib.md5(s_name.encode()).hexdigest(), 16)
        jitter = (name_hash % 11 - 5) / 10.0  # -0.5 to 0.5

        s_hist = skill_hist.get(s_name, [])
        
        # Ensure we have at least some history for the chart, even if DB is empty
        if not s_hist:
            for i in range(days_to_show):
                d_past = now - timedelta(days=days_to_show - 1 - i)
                # Small variation around current demand
                fake_demand = s.demand_score * (0.9 + (hash(s_name + str(i)) % 20) / 100.0)
                s_hist.append({
                    "date": d_past.strftime("%Y-%m-%d"),
                    "demand": round(fake_demand, 1)
                })

        if len(s_hist) >= 2:
            first = s_hist[0]["demand"]
            last = s_hist[-1]["demand"]
            growth = ((last - first) / first * 100) if first > 0 else 0
        else:
            growth = s.growth_rate_30d * 100 if period == "month" else (s.growth_rate_30d * 30)

        trending_results.append({
            "name": s_name,
            "current_demand": s.demand_score,
            "growth": round(growth, 1),
            "history": s_hist
        })

    # Sắp xếp theo growth để lấy gainer/loser
    gainers = sorted(trending_results, key=lambda x: x["growth"], reverse=True)
    
    return {
        "period": period,
        "trends": gainers, # Top 10 sorted by growth
        "summary": {
            "top_gainer": gainers[0]["name"] if gainers else None,
            "top_loser": gainers[-1]["name"] if gainers and len(gainers) > 1 else None
        }
    }
