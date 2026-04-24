"""
Growth Calculator - Tính potential_match và salary_growth dựa trên DB data thực tế
Thay thế logic đoán mò bằng thuật toán chính xác từ JobSkillRequirement và MarketSkillStats
"""

from sqlalchemy.orm import Session
from shared.models import Job, JobSkillRequirement, MarketSkillStats, Skill
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger("growth_calculator")


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
                # Handle type="skill"
                if req.get("type") == "skill":
                    skill_name = req.get("skill", "").lower()
                    importance = req.get("importance_weight", 5)
                    if skill_name:
                        skill_weights[skill_name] = importance
                # Handle type="group"
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
        
        # 1. Tính match impact từ importance_weight
        match_impact = 0.0
        if skill_name in skill_weights:
            # importance_weight thường là 1-10, normalize về %
            match_impact = min(skill_weights[skill_name] * 2, 20)  # Cap ở 20%
        else:
            # Fallback: estimate dựa trên severity
            severity = gap.get("severity", "medium").lower()
            if severity == "high":
                match_impact = 15.0
            elif severity == "medium":
                match_impact = 8.0
            else:
                match_impact = 3.0
        
        # 2. Tính salary impact từ MarketSkillStats
        salary_impact = 0.0
        # SECURITY: Sanitize skill_name for ILIKE query
        safe_skill_name = skill_name.replace("%", "\\%").replace("_", "\\_")
        market_stat = db.query(MarketSkillStats).filter(
            MarketSkillStats.skill_name.ilike(f"%{safe_skill_name}%")
        ).first()
        
        if market_stat and market_stat.salary_premium_pct:
            salary_impact = market_stat.salary_premium_pct
        else:
            # Fallback: estimate dựa trên severity và demand
            severity = gap.get("severity", "medium").lower()
            if severity == "high":
                salary_impact = 12.0
            elif severity == "medium":
                salary_impact = 6.0
            else:
                salary_impact = 2.0
        
        # 3. Enrich skill gap với impact values
        enriched_gap = {
            **gap,
            "match_impact": round(match_impact, 1),
            "salary_impact": round(salary_impact, 1),
            "market_demand": market_stat.demand_score if market_stat else None,
            "avg_salary_range": {
                "min": market_stat.avg_salary_min if market_stat else None,
                "max": market_stat.avg_salary_max if market_stat else None
            } if market_stat else None
        }
        enriched_gaps.append(enriched_gap)
        
        total_match_gain += match_impact
        total_salary_gain += salary_impact
        
        logger.info(
            f"Skill '{skill_name}': match_impact={match_impact}%, "
            f"salary_impact={salary_impact}%"
        )
    
    # 4. Tính potential_match_pct
    potential_match_pct = min(98, current_match_pct + total_match_gain)
    
    # 5. Tính salary_growth_pct (cap ở 40% để realistic)
    salary_growth_pct = min(40, total_salary_gain)
    
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
    Tính market sentiment dựa trên growth_rate và demand_score của các skills thiếu.
    """
    if not skill_gaps:
        return "Ổn định"
    
    total_growth = 0.0
    total_demand = 0.0
    count = 0
    
    for gap in skill_gaps:
        skill_name = gap.get("skill", "").lower()
        # SECURITY: Sanitize skill_name for ILIKE query
        safe_skill_name = skill_name.replace("%", "\\%").replace("_", "\\_")
        market_stat = db.query(MarketSkillStats).filter(
            MarketSkillStats.skill_name.ilike(f"%{safe_skill_name}%")
        ).first()
        
        if market_stat:
            if market_stat.growth_rate_30d:
                total_growth += market_stat.growth_rate_30d
            if market_stat.demand_score:
                total_demand += market_stat.demand_score
            count += 1
    
    if count == 0:
        return "Ổn định"
    
    avg_growth = total_growth / count
    avg_demand = total_demand / count
    
    # Phân loại sentiment
    if avg_growth > 0.15 and avg_demand > 70:
        return "Tăng trưởng cao"
    elif avg_growth > 0.08 or avg_demand > 50:
        return "Tăng trưởng ổn định"
    elif avg_growth < 0:
        return "Giảm nhu cầu"
    else:
        return "Ổn định"
