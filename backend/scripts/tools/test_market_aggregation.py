"""
Test script to manually run market stats aggregation without Celery.
"""
import sys
sys.path.insert(0, 'backend')

from datetime import datetime, timedelta, timezone
from collections import defaultdict
from shared.database import SessionLocal
from shared.models import Job, MarketSkillStats

def run_aggregation():
    db = SessionLocal()
    try:
        print("[MARKET STATS] Starting aggregation...")
        
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        sixty_days_ago = now - timedelta(days=60)

        # 1. Get all jobs in last 60 days
        jobs_60d = db.query(Job).filter(
            Job.created_at >= sixty_days_ago
        ).all()

        print(f"Found {len(jobs_60d)} jobs in last 60 days")

        if not jobs_60d:
            print("No jobs found. Exiting.")
            return

        # 2. Analyze data in 2 periods: 0-30d and 31-60d
        stats_current = defaultdict(lambda: {"count": 0, "salaries_min": [], "salaries_max": []})
        stats_previous = defaultdict(lambda: {"count": 0})

        for job in jobs_60d:
            reqs = job.extracted_requirements_json or []
            if not isinstance(reqs, list):
                continue
                
            is_current = job.created_at >= thirty_days_ago
            
            # Extract all skills (handle both type="skill" and type="group")
            all_skills = []
            for req in reqs:
                if req.get("type") == "skill":
                    skill_name = req.get("skill")
                    if skill_name:
                        all_skills.append(skill_name)
                elif req.get("type") == "group":
                    # Extract skills from nested group
                    group_skills = req.get("skills", [])
                    for skill_obj in group_skills:
                        skill_name = skill_obj.get("skill")
                        if skill_name:
                            all_skills.append(skill_name)
            
            # Aggregate stats for each skill
            for skill_name in all_skills:
                if is_current:
                    stats_current[skill_name]["count"] += 1
                    if job.min_salary_vnd:
                        stats_current[skill_name]["salaries_min"].append(job.min_salary_vnd)
                    if job.max_salary_vnd:
                        stats_current[skill_name]["salaries_max"].append(job.max_salary_vnd)
                else:
                    stats_previous[skill_name]["count"] += 1

        print(f"Found {len(stats_current)} unique skills in current period")

        # 3. Calculate Salary Premium (compare with market average)
        all_salaries_min = [j.min_salary_vnd for j in jobs_60d if j.min_salary_vnd and j.created_at >= thirty_days_ago]
        avg_market_salary = sum(all_salaries_min) / len(all_salaries_min) if all_salaries_min else 0
        print(f"Average market salary: {avg_market_salary:,.0f} VND")

        # 4. Update DB
        updated_count = 0
        for skill_name, data in stats_current.items():
            count_current = data["count"]
            count_prev = stats_previous[skill_name]["count"]
            
            avg_min = sum(data["salaries_min"]) / len(data["salaries_min"]) if data["salaries_min"] else 0
            avg_max = sum(data["salaries_max"]) / len(data["salaries_max"]) if data["salaries_max"] else 0
            
            # Calculate Growth Rate
            growth = 0.0
            if count_prev > 0:
                growth = (count_current - count_prev) / count_prev
            elif count_current > 0:
                growth = 1.0  # New skill trending
            
            # Calculate Salary Premium
            premium_pct = 0.0
            if avg_market_salary > 0 and avg_min > 0:
                premium_pct = (avg_min - avg_market_salary) / avg_market_salary
            
            # Calculate Demand Score (0-100)
            demand_score = min(100, (count_current / 100) * 80 + (max(0, growth) * 20))

            # Upsert
            stat_record = db.query(MarketSkillStats).filter(MarketSkillStats.skill_name == skill_name).first()
            if not stat_record:
                stat_record = MarketSkillStats(skill_name=skill_name)
                db.add(stat_record)
            
            stat_record.avg_salary_min = int(avg_min) if avg_min else None
            stat_record.avg_salary_max = int(avg_max) if avg_max else None
            stat_record.salary_premium_pct = premium_pct
            stat_record.job_count_30d = count_current
            stat_record.growth_rate_30d = growth
            stat_record.demand_score = demand_score
            stat_record.updated_at = now
            
            updated_count += 1
            
            if updated_count <= 5:  # Print first 5 as sample
                print(f"  {skill_name}: count={count_current}, demand={demand_score:.1f}, premium={premium_pct*100:.1f}%")

        db.commit()
        print(f"\n[OK] Aggregation completed for {updated_count} skills.")
        
        # Verify
        total = db.query(MarketSkillStats).count()
        print(f"Total MarketSkillStats records: {total}")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Aggregation failed: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    run_aggregation()
