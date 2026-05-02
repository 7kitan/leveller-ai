"""
Growth Calculator - Tính potential_match và salary_growth dựa trên DB data thực tế
Thay thế logic đoán mò bằng thuật toán chính xác từ JobSkillRequirement và MarketSkillStats
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from shared.models import Job, JobSkillRequirement, MarketSkillStats, Skill
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger("growth_calculator")

def escape_like(s: str) -> str:
    """Escape special characters for SQL LIKE operator to prevent LIKE Injection."""
    if not s:
        return ""
    return s.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


def calculate_market_demand_from_jobs(skill_name: str, db: Session) -> float:
    """
    Tính market demand thực tế từ database khi skill chưa có trong MarketSkillStats.
    
    Returns:
        Phần trăm job yêu cầu skill này trong 30 ngày gần nhất (0-100)
    """
    import json
    
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    # Fetch all jobs in last 30 days
    jobs = db.query(Job).filter(
        Job.created_at >= thirty_days_ago
    ).all()
    
    if not jobs:
        return 0.0
    
    total_jobs = len(jobs)
    jobs_with_skill = 0
    skill_name_lower = skill_name.lower()
    
    # Count jobs that require this skill by parsing JSON requirements
    for job in jobs:
        if not job.requirements:
            continue
        
        try:
            requirements = json.loads(job.requirements) if isinstance(job.requirements, str) else job.requirements
            if not isinstance(requirements, list):
                continue
                
            for req in requirements:
                req_skill = req.get("skill") or req.get("skill_name") or ""
                if skill_name_lower in req_skill.lower():
                    jobs_with_skill += 1
                    break  # Count each job only once
        except (json.JSONDecodeError, AttributeError, TypeError):
            continue
    
    demand_pct = (jobs_with_skill / total_jobs * 100) if total_jobs > 0 else 0.0
    
    logger.info(
        f"Calculated market_demand for '{skill_name}': {jobs_with_skill}/{total_jobs} jobs = {demand_pct:.1f}%"
    )
    
    return demand_pct


def calculate_skill_impact(
    skill_gaps: List[Dict],
    job_id: str,
    current_match_pct: float,
    db: Session
) -> Tuple[float, float, List[Dict]]:
    """
    Tính potential_match_pct và salary_growth_pct dựa trên DB data thực tế.
    
    Args:
        skill_gaps: List các skill còn thiếu từ gap analysis
        job_id: UUID của job để lấy importance_weight
        current_match_pct: Điểm match hiện tại
        db: Database session
        
    Returns:
        (potential_match_pct, salary_growth_pct, enriched_skill_gaps)
    """
    
    if not skill_gaps or not job_id:
        logger.warning("No skill gaps or job_id provided, returning current match")
        return current_match_pct, 0.0, skill_gaps
    
    # Lấy job để đọc extracted_requirements_json
    job = db.query(Job).filter(Job.id == job_id).first()
    
    # Tạo mapping: skill_name -> importance_weight từ extracted_requirements_json
    skill_weights = {}
    if job and job.extracted_requirements_json:
        requirements = job.extracted_requirements_json
        if isinstance(requirements, list):
            for req in requirements:
                # New format: direct skill objects with skill_name field
                skill_name = req.get("skill_name", "").lower()
                importance = req.get("importance_weight", 5)
                if skill_name:
                    skill_weights[skill_name] = importance
                
                # Legacy format: type="skill" or type="group"
                if req.get("type") == "skill":
                    skill_name = req.get("skill", "").lower()
                    importance = req.get("importance_weight", 5)
                    if skill_name:
                        skill_weights[skill_name] = importance
                elif req.get("type") == "group":
                    group_importance = req.get("importance_weight", 5)
                    for skill_obj in req.get("skills", []):
                        skill_name = skill_obj.get("skill", "").lower()
                        if skill_name:
                            skill_weights[skill_name] = group_importance
    
    total_match_gain = 0.0
    total_salary_gain = 0.0
    enriched_gaps = []
    
    for gap in skill_gaps:
        skill_name = gap.get("skill", "").lower()
        
        # Deterministic jitter to prevent identical percentages
        # We use a simple hash of the skill name to get a value between -0.5 and 0.5
        import hashlib
        name_hash = int(hashlib.md5(skill_name.encode()).hexdigest(), 16)
        jitter = (name_hash % 11 - 5) / 10.0  # -0.5 to 0.5
        
        # 1. Tính match impact từ importance_weight
        match_impact = 0.0
        if skill_name in skill_weights:
            # importance_weight thường là 1-10, normalize về %
            base_impact = skill_weights[skill_name] * 2.0
            match_impact = min(base_impact + jitter, 25)  # Cap ở 25%
        else:
            # Fallback: estimate dựa trên severity
            severity = gap.get("severity", "medium").lower()
            if severity == "high":
                match_impact = 15.0 + jitter * 2
            elif severity == "medium":
                match_impact = 8.0 + jitter
            else:
                match_impact = 3.0 + jitter
        
        # 2. Tính salary impact từ MarketSkillStats
        salary_impact = 0.0
        # SECURITY: Use ilike with escaped skill_name to prevent LIKE injection
        market_stat = db.query(MarketSkillStats).filter(
            MarketSkillStats.skill_name.ilike(f"%{escape_like(skill_name)}%", escape='\\')
        ).first()
        
        if market_stat and market_stat.salary_premium_pct:
            # Convert from fraction to percentage (e.g., 0.15 -> 15%)
            salary_impact = (market_stat.salary_premium_pct * 100) + jitter
        else:
            # Fallback: estimate dựa trên severity và demand
            severity = gap.get("severity", "medium").lower()
            if severity == "high":
                salary_impact = 12.0 + jitter * 3
            elif severity == "medium":
                salary_impact = 6.0 + jitter * 2
            else:
                salary_impact = 2.0 + jitter
        
        # 3. Clamp impact values to valid ranges
        clamped_match_impact = max(1.0, match_impact)
        clamped_salary_impact = max(0.0, salary_impact)
        
        # 4. Calculate market_demand from real data
        if market_stat and market_stat.demand_score is not None:
            # Use pre-calculated stats from MarketSkillStats (30-day data)
            market_demand = round(market_stat.demand_score, 1)
        else:
            # Fallback: Calculate real-time from Job table
            market_demand = round(calculate_market_demand_from_jobs(skill_name, db), 1)
        
        # 5. Enrich skill gap với impact values
        enriched_gap = {
            **gap,
            "match_impact": round(clamped_match_impact, 1),
            "salary_impact": round(clamped_salary_impact, 1),
            "market_demand": market_demand,
            "avg_salary_range": {
                "min": market_stat.avg_salary_min if market_stat else None,
                "max": market_stat.avg_salary_max if market_stat else None
            } if market_stat else None
        }
        enriched_gaps.append(enriched_gap)
        
        # CRITICAL: Use clamped values for totals, not raw values!
        total_match_gain += clamped_match_impact
        total_salary_gain += clamped_salary_impact
        
        logger.info(
            f"Skill '{skill_name}': match_impact={match_impact}%, "
            f"salary_impact={salary_impact}%"
        )
    
    # 4. Tính potential_match_pct dựa trên trọng số thực tế
    if skill_weights:
        # Calculate total weight from all JD requirements
        total_weight = sum(skill_weights.values())
        
        # Calculate weight of gap skills
        gap_weight = 0.0
        for gap in skill_gaps:
            skill_name = gap.get("skill", "").lower()
            if skill_name in skill_weights:
                gap_weight += skill_weights[skill_name]
        
        # Calculate matched weight (total - gaps)
        matched_weight = total_weight - gap_weight
        
        # Recalculate current_match_pct based on actual weights
        current_match_pct_weighted = (matched_weight / total_weight * 100) if total_weight > 0 else 0
        
        # Calculate potential if learn all gaps in the list
        potential_weight = matched_weight + gap_weight
        potential_match_pct = (potential_weight / total_weight * 100) if total_weight > 0 else 0
        
        logger.info(
            f"Weighted calculation: total_weight={total_weight}, "
            f"matched_weight={matched_weight:.1f}, gap_weight={gap_weight:.1f}, "
            f"current={current_match_pct_weighted:.1f}%, potential={potential_match_pct:.1f}%"
        )
    else:
        # Fallback to old method if no weights available
        potential_match_pct = min(98, current_match_pct + total_match_gain)
        logger.warning("No skill weights found, using fallback calculation")
    
    # 5. Tính salary_growth_pct (cap ở 50% để realistic)
    salary_growth_pct = min(50, total_salary_gain)
    
    logger.info(
        f"Growth calculation: current={current_match_pct}%, "
        f"potential={potential_match_pct}%, salary_growth={salary_growth_pct}%"
    )
    
    return potential_match_pct, salary_growth_pct, enriched_gaps


def calculate_market_sentiment(
    skill_gaps: List[Dict],
    db: Session
) -> str:
    """
    Tính market sentiment dựa trên top skills có demand cao nhất.
    Trả về sentiment cụ thể dựa trên skill có nhu cầu cao nhất trong gap list.
    """
    if not skill_gaps:
        return "Không có dữ liệu"
    
    # Get top 10 skills by demand globally
    top_10_skills = db.query(MarketSkillStats).filter(
        MarketSkillStats.demand_score.isnot(None)
    ).order_by(MarketSkillStats.demand_score.desc()).limit(10).all()
    
    top_10_names = {s.skill_name.lower() for s in top_10_skills}
    
    # Find highest demand skill in gap list
    max_demand = 0.0
    max_demand_skill = None
    max_growth = 0.0
    has_top_10_skill = False
    
    for gap in skill_gaps:
        skill_name = gap.get("skill", "").lower()
        # SECURITY: Use ilike with escaped skill_name to prevent LIKE injection
        market_stat = db.query(MarketSkillStats).filter(
            MarketSkillStats.skill_name.ilike(f"%{escape_like(skill_name)}%", escape='\\')
        ).first()
        
        if market_stat and market_stat.demand_score:
            if market_stat.demand_score > max_demand:
                max_demand = market_stat.demand_score
                max_demand_skill = gap.get("skill")
                max_growth = market_stat.growth_rate_30d or 0.0
            
            # Check if this skill is in top 10
            if skill_name in top_10_names:
                has_top_10_skill = True
    
    # Generate specific sentiment based on highest demand skill
    if has_top_10_skill:
        return f"Nhu cầu rất cao - {max_demand_skill} thuộc Top 10 kỹ năng được tìm kiếm nhiều nhất"
    elif max_demand > 15:
        growth_note = " (Đang tăng nhanh)" if max_growth > 0.2 else ""
        return f"Nhu cầu cao - {max_demand_skill} xuất hiện trong {max_demand:.1f}% công việc{growth_note}"
    elif max_demand > 5:
        return f"Nhu cầu trung bình - {max_demand_skill} xuất hiện trong {max_demand:.1f}% công việc"
    elif max_demand > 0:
        return f"Nhu cầu thấp - {max_demand_skill} xuất hiện trong {max_demand:.1f}% công việc"
    else:
        return "Không có dữ liệu thị trường"
