import logging
import json
from datetime import datetime, timedelta
from sqlalchemy import func, and_
from worker.celery_app import celery_app
from shared.database import SessionLocal
from shared.models import Job, MarketSkillStats
from collections import defaultdict

logger = logging.getLogger("market_stats_worker")

@celery_app.task(name="worker.tasks.market_stats_tasks.aggregate_market_data")
def aggregate_market_data():
    """
    Tác vụ tổng hợp dữ liệu thị trường hàng ngày.
    Tính toán:
    1. Lương trung bình cho mỗi Skill.
    2. Tần suất xuất hiện (Demand).
    3. Tỷ lệ tăng trưởng (Growth).
    """
    db = SessionLocal()
    try:
        logger.info("[MARKET STATS] Starting daily aggregation...")
        
        now = datetime.now()
        thirty_days_ago = now - timedelta(days=30)
        sixty_days_ago = now - timedelta(days=60)

        # 1. Lấy tất cả Job trong 60 ngày qua
        jobs_60d = db.query(Job).filter(
            Job.created_at >= sixty_days_ago
        ).all()

        if not jobs_60d:
            logger.warning("[MARKET STATS] No jobs found in the last 60 days. Skipping.")
            return

        # 2. Phân tích dữ liệu theo 2 giai đoạn: 0-30d và 31-60d
        stats_current = defaultdict(lambda: {"count": 0, "salaries_min": [], "salaries_max": []})
        stats_previous = defaultdict(lambda: {"count": 0})

        for job in jobs_60d:
            reqs = job.extracted_requirements_json or []
            if not isinstance(reqs, list):
                continue
                
            is_current = job.created_at >= thirty_days_ago
            
            for req in reqs:
                skill_name = req.get("skill")
                if not skill_name:
                    continue
                
                if is_current:
                    stats_current[skill_name]["count"] += 1
                    if job.min_salary_vnd:
                        stats_current[skill_name]["salaries_min"].append(job.min_salary_vnd)
                    if job.max_salary_vnd:
                        stats_current[skill_name]["salaries_max"].append(job.max_salary_vnd)
                else:
                    stats_previous[skill_name]["count"] += 1

        # 3. Tính toán Salary Premium (so sánh với lương trung bình toàn thị trường)
        all_salaries_min = [j.min_salary_vnd for j in jobs_60d if j.min_salary_vnd and j.created_at >= thirty_days_ago]
        avg_market_salary = sum(all_salaries_min) / len(all_salaries_min) if all_salaries_min else 0

        # 4. Cập nhật vào DB
        for skill_name, data in stats_current.items():
            count_current = data["count"]
            count_prev = stats_previous[skill_name]["count"]
            
            avg_min = sum(data["salaries_min"]) / len(data["salaries_min"]) if data["salaries_min"] else 0
            avg_max = sum(data["salaries_max"]) / len(data["salaries_max"]) if data["salaries_max"] else 0
            
            # Tính Growth Rate
            growth = 0.0
            if count_prev > 0:
                growth = (count_current - count_prev) / count_prev
            elif count_current > 0:
                growth = 1.0 # New skill trending
            
            # Tính Salary Premium
            premium_pct = 0.0
            if avg_market_salary > 0 and avg_min > 0:
                premium_pct = (avg_min - avg_market_salary) / avg_market_salary
            
            # Tính Demand Score (0-100)
            # Giả sử 100 jobs/tháng là cực cao (max score)
            demand_score = min(100, (count_current / 100) * 80 + (max(0, growth) * 20))

            # Upsert
            stat_record = db.query(MarketSkillStats).filter(MarketSkillStats.skill_name == skill_name).first()
            if not stat_record:
                stat_record = MarketSkillStats(skill_name=skill_name)
                db.add(stat_record)
            
            stat_record.avg_salary_min = int(avg_min)
            stat_record.avg_salary_max = int(avg_max)
            stat_record.salary_premium_pct = premium_pct
            stat_record.job_count_30d = count_current
            stat_record.growth_rate_30d = growth
            stat_record.demand_score = demand_score
            stat_record.updated_at = now

        db.commit()
        logger.info(f"[MARKET STATS] Aggregation completed for {len(stats_current)} skills.")

    except Exception as e:
        db.rollback()
        logger.error(f"[MARKET STATS] Aggregation failed: {str(e)}", exc_info=True)
    finally:
        db.close()


@celery_app.task(name="worker.tasks.market_stats_tasks.cleanup_expired_youtube_courses")
def cleanup_expired_youtube_courses():
    """
    Xóa các video YouTube đã hết hạn khỏi database để giải phóng dung lượng.
    """
    db = SessionLocal()
    try:
        now = datetime.now()
        from shared.models import YouTubeCourse
        
        deleted = db.query(YouTubeCourse).filter(YouTubeCourse.expires_at < now).delete()
        db.commit()
        
        if deleted > 0:
            logger.info(f"[CLEANUP] Deleted {deleted} expired YouTube courses.")
    except Exception as e:
        db.rollback()
        logger.error(f"[CLEANUP] Failed to cleanup expired YouTube courses: {e}")
    finally:
        db.close()


@celery_app.task(name="worker.tasks.market_stats_tasks.cleanup_system_logs")
def cleanup_system_logs():
    """
    Dọn dẹp nhật ký hệ thống định kỳ dựa trên cấu hình TTL.
    """
    from shared.system_logger import system_logger
    from shared.config_utils import config_manager
    
    # Lấy số ngày lưu trữ từ config, mặc định 30 ngày
    ttl_days = int(config_manager.get_setting("system_log_ttl_days") or 30)
    
    logger.info(f"[CLEANUP] Starting system log cleanup (TTL: {ttl_days} days)...")
    count = system_logger.cleanup_old_logs(days=ttl_days)
    
    if count > 0:
        logger.info(f"[CLEANUP] Successfully removed {count} old system logs.")
