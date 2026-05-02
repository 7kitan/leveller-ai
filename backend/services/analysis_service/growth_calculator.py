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
) -> Tuple[float, List[Dict]]:
    """
    Tính potential_match_pct dựa trên DB data thực tế.
    
    Args:
        skill_gaps: List các skill còn thiếu từ gap analysis
        job_id: UUID của job để lấy importance_weight
        current_match_pct: Điểm match hiện tại
        db: Database session
        
    Returns:
        (potential_match_pct, enriched_skill_gaps)
    """
    
    if not skill_gaps:
        logger.warning("No skill gaps provided, returning current match")
        return current_match_pct, skill_gaps
    
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
    enriched_gaps = []
    
    for gap in skill_gaps:
        skill_name = gap.get("skill", "").lower()
        
        # Deterministic jitter to prevent identical percentages
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
        
        # 2. Clamp match impact to valid range
        clamped_match_impact = max(1.0, match_impact)
        
        # 3. Calculate market_demand from real data
        # SECURITY: Use ilike with escaped skill_name to prevent LIKE injection
        market_stat = db.query(MarketSkillStats).filter(
            MarketSkillStats.skill_name.ilike(f"%{escape_like(skill_name)}%", escape='\\')
        ).first()
        
        if market_stat and market_stat.demand_score is not None:
            # Use pre-calculated stats from MarketSkillStats (30-day data)
            market_demand = round(market_stat.demand_score, 1)
        else:
            # Fallback: Calculate real-time from Job table
            market_demand = round(calculate_market_demand_from_jobs(skill_name, db), 1)
        
        # 4. Enrich skill gap với impact values (NO SALARY)
        enriched_gap = {
            **gap,
            "match_impact": round(clamped_match_impact, 1),
            "market_demand": market_demand,
        }
        enriched_gaps.append(enriched_gap)
        
        total_match_gain += clamped_match_impact
        
        logger.info(
            f"Skill '{skill_name}': match_impact={match_impact}%, "
            f"market_demand={market_demand}%"
        )
    
    # 5. Tính potential_match_pct dựa trên trọng số thực tế
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
    
    logger.info(
        f"Growth calculation: current={current_match_pct}%, "
        f"potential={potential_match_pct}%"
    )
    
    return potential_match_pct, enriched_gaps


def calculate_market_sentiment(
    skill_gaps: List[Dict],
    db: Session
) -> str:
    """
    Tính market sentiment dựa trên top skills có demand cao nhất và số lượng job thực tế.
    Trả về sentiment cụ thể dựa trên số lượng cơ hội việc làm thực tế trong DB.
    """
    if not skill_gaps:
        return "Thị trường ổn định"
    
    # 1. Lấy tổng số job tech để tính context
    total_tech_jobs = db.query(Job).filter(Job.is_tech_job == True).count()
    
    # 2. Lấy top 10 skills toàn hệ thống
    top_10_skills = db.query(MarketSkillStats).filter(
        MarketSkillStats.demand_score.isnot(None)
    ).order_by(MarketSkillStats.demand_score.desc()).limit(10).all()
    
    top_10_names = {s.skill_name.lower() for s in top_10_skills}
    
    # 3. Tìm skill có "tín hiệu" mạnh nhất trong danh sách gap
    best_stat = None
    best_skill_name = None
    is_in_top_10 = False
    
    for gap in skill_gaps:
        skill_name = gap.get("skill", "").lower()
        market_stat = db.query(MarketSkillStats).filter(
            MarketSkillStats.skill_name.ilike(f"%{escape_like(skill_name)}%", escape='\\')
        ).first()
        
        if market_stat and (market_stat.job_count_30d or 0) > 0:
            # Ưu tiên skill có job_count lớn nhất
            if not best_stat or market_stat.job_count_30d > best_stat.job_count_30d:
                best_stat = market_stat
                best_skill_name = gap.get("skill")
                if skill_name in top_10_names:
                    is_in_top_10 = True
    
    if not best_stat:
        return "Nhu cầu thị trường đang thay đổi"

    count = best_stat.job_count_30d
    pct = best_stat.demand_score or 0.0
    growth = best_stat.growth_rate_30d or 0.0
    
    # 4. Phân loại dựa trên số lượng tuyệt đối và tương đối
    # Ngưỡng: > 50 jobs hoặc > 15% là Rất cao
    #         > 20 jobs hoặc > 5% là Cao
    #         Còn lại là Ổn định/Trung bình
    
    if is_in_top_10 or count > 50 or pct > 15:
        msg = f"Nhu cầu rất cao — {best_skill_name} xuất hiện trong {count} vị trí tuyển dụng ({pct:.1f}%)"
        if is_in_top_10:
            msg += " (Top 10 Hot Skills)"
        return msg
    elif count > 20 or pct > 5:
        growth_note = " (Đang tăng trưởng)" if growth > 0.1 else ""
        return f"Nhu cầu cao — {best_skill_name} đang được yêu cầu tại {count} doanh nghiệp{growth_note}"
    elif count > 5:
        return f"Nhu cầu ổn định — Có {count} cơ hội việc làm mới cho kỹ năng {best_skill_name}"
    else:
        return f"Tín hiệu mới — {best_skill_name} bắt đầu xuất hiện trong các JD gần đây"
