"""
Market Stats Utility Functions
Provides time-series aggregation and trend analysis for market data.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from shared.models import MarketSkillHistory, MarketSkillStats


def get_skill_trend_weekly(db: Session, skill_name: str, weeks: int = 4) -> List[Dict]:
    """
    Get weekly aggregated demand for a skill.
    
    Args:
        db: Database session
        skill_name: Name of the skill
        weeks: Number of weeks to look back (default: 4)
    
    Returns:
        List of dicts with week_start, avg_demand, avg_job_count
    """
    cutoff = datetime.now() - timedelta(weeks=weeks)
    
    results = db.query(
        func.date_trunc('week', MarketSkillHistory.snapshot_date).label('week_start'),
        func.avg(MarketSkillHistory.demand_score).label('avg_demand'),
        func.avg(MarketSkillHistory.job_count).label('avg_job_count')
    ).filter(
        MarketSkillHistory.skill_name == skill_name,
        MarketSkillHistory.snapshot_date >= cutoff
    ).group_by(
        func.date_trunc('week', MarketSkillHistory.snapshot_date)
    ).order_by('week_start').all()
    
    return [
        {
            "week_start": r.week_start.isoformat() if r.week_start else None,
            "avg_demand": round(r.avg_demand, 2) if r.avg_demand else 0,
            "avg_job_count": round(r.avg_job_count, 1) if r.avg_job_count else 0
        }
        for r in results
    ]


def get_skill_trend_monthly(db: Session, skill_name: str, months: int = 6) -> List[Dict]:
    """
    Get monthly aggregated demand for a skill.
    
    Args:
        db: Database session
        skill_name: Name of the skill
        months: Number of months to look back (default: 6)
    
    Returns:
        List of dicts with month, avg_demand, max_demand, min_demand, avg_job_count
    """
    cutoff = datetime.now() - timedelta(days=months*30)
    
    results = db.query(
        func.date_trunc('month', MarketSkillHistory.snapshot_date).label('month_start'),
        func.avg(MarketSkillHistory.demand_score).label('avg_demand'),
        func.avg(MarketSkillHistory.job_count).label('avg_job_count'),
        func.max(MarketSkillHistory.demand_score).label('max_demand'),
        func.min(MarketSkillHistory.demand_score).label('min_demand')
    ).filter(
        MarketSkillHistory.skill_name == skill_name,
        MarketSkillHistory.snapshot_date >= cutoff
    ).group_by(
        func.date_trunc('month', MarketSkillHistory.snapshot_date)
    ).order_by('month_start').all()
    
    return [
        {
            "month": r.month_start.strftime("%Y-%m") if r.month_start else None,
            "avg_demand": round(r.avg_demand, 2) if r.avg_demand else 0,
            "max_demand": round(r.max_demand, 2) if r.max_demand else 0,
            "min_demand": round(r.min_demand, 2) if r.min_demand else 0,
            "avg_job_count": round(r.avg_job_count, 1) if r.avg_job_count else 0
        }
        for r in results
    ]


def get_top_trending_skills(
    db: Session, 
    period_days: int = 30, 
    limit: int = 10,
    min_current_demand: float = 5.0
) -> List[Dict]:
    """
    Get skills with highest growth rate in the period.
    
    Args:
        db: Database session
        period_days: Number of days to calculate growth over (default: 30)
        limit: Maximum number of skills to return (default: 10)
        min_current_demand: Minimum current demand % to be considered (default: 5%)
    
    Returns:
        List of dicts with skill_name, current_demand, growth_rate, trend
    """
    # Get skills with positive growth and sufficient current demand
    results = db.query(MarketSkillStats).filter(
        MarketSkillStats.growth_rate_30d > 0,
        MarketSkillStats.demand_score >= min_current_demand
    ).order_by(
        MarketSkillStats.growth_rate_30d.desc()
    ).limit(limit).all()
    
    trending = []
    for skill in results:
        trend = "stable"
        if skill.growth_rate_30d > 0.5:
            trend = "explosive"
        elif skill.growth_rate_30d > 0.2:
            trend = "high"
        elif skill.growth_rate_30d > 0.1:
            trend = "moderate"
        
        trending.append({
            "skill_name": skill.skill_name,
            "current_demand": round(skill.demand_score, 2),
            "growth_rate": round(skill.growth_rate_30d * 100, 1),  # Convert to %
            "job_count": skill.job_count_30d,
            "trend": trend
        })
    
    return trending


def get_skill_comparison(db: Session, skill_names: List[str]) -> Dict:
    """
    Compare multiple skills side-by-side.
    
    Args:
        db: Database session
        skill_names: List of skill names to compare
    
    Returns:
        Dict with comparison data for each skill
    """
    skills_data = []
    
    for skill_name in skill_names:
        stat = db.query(MarketSkillStats).filter(
            MarketSkillStats.skill_name == skill_name
        ).first()
        
        if stat:
            skills_data.append({
                "skill_name": skill_name,
                "demand_score": round(stat.demand_score, 2) if stat.demand_score else 0,
                "growth_rate": round(stat.growth_rate_30d * 100, 1) if stat.growth_rate_30d else 0,
                "job_count": stat.job_count_30d,
                "avg_salary_min": stat.avg_salary_min,
                "avg_salary_max": stat.avg_salary_max,
                "salary_premium_pct": round(stat.salary_premium_pct * 100, 1) if stat.salary_premium_pct else 0
            })
        else:
            skills_data.append({
                "skill_name": skill_name,
                "error": "Skill not found in market data"
            })
    
    return {
        "skills": skills_data,
        "comparison_date": datetime.now().isoformat()
    }


def get_market_overview(db: Session) -> Dict:
    """
    Get overall market statistics.
    
    Returns:
        Dict with market overview metrics
    """
    # Total skills tracked
    total_skills = db.query(func.count(MarketSkillStats.skill_name)).scalar()
    
    # Average demand
    avg_demand = db.query(func.avg(MarketSkillStats.demand_score)).filter(
        MarketSkillStats.demand_score.isnot(None)
    ).scalar()
    
    # Skills with high demand (>10%)
    high_demand_count = db.query(func.count(MarketSkillStats.skill_name)).filter(
        MarketSkillStats.demand_score > 10
    ).scalar()
    
    # Skills with positive growth
    growing_skills = db.query(func.count(MarketSkillStats.skill_name)).filter(
        MarketSkillStats.growth_rate_30d > 0
    ).scalar()
    
    # Top 5 most demanded skills
    top_skills = db.query(MarketSkillStats).order_by(
        MarketSkillStats.demand_score.desc()
    ).limit(5).all()
    
    return {
        "total_skills_tracked": total_skills,
        "avg_market_demand": round(avg_demand, 2) if avg_demand else 0,
        "high_demand_skills_count": high_demand_count,
        "growing_skills_count": growing_skills,
        "top_5_skills": [
            {
                "skill_name": s.skill_name,
                "demand": round(s.demand_score, 2)
            }
            for s in top_skills
        ],
        "snapshot_date": datetime.now().isoformat()
    }


def get_skill_trend_daily(db: Session, skill_name: str, days: int = 7) -> List[Dict]:
    """
    Get daily demand data for a skill (not aggregated by week/month).
    
    Args:
        db: Database session
        skill_name: Name of the skill
        days: Number of days to look back (default: 7)
    
    Returns:
        List of dicts with date, demand_score, job_count for each day
    """
    cutoff = datetime.now() - timedelta(days=days)
    
    results = db.query(MarketSkillHistory).filter(
        MarketSkillHistory.skill_name == skill_name,
        MarketSkillHistory.snapshot_date >= cutoff
    ).order_by(MarketSkillHistory.snapshot_date).all()
    
    # Group by date (in case multiple snapshots per day, take the latest)
    daily_data = {}
    for r in results:
        date_key = r.snapshot_date.date().isoformat()
        # Keep the latest snapshot for each day
        if date_key not in daily_data or r.snapshot_date > daily_data[date_key]['_timestamp']:
            daily_data[date_key] = {
                "date": date_key,
                "demand_score": round(r.demand_score, 2) if r.demand_score else 0,
                "job_count": r.job_count or 0,
                "_timestamp": r.snapshot_date  # Internal field for comparison
            }
    
    # Remove internal timestamp field and return sorted by date
    result = []
    for date_key in sorted(daily_data.keys()):
        data = daily_data[date_key].copy()
        del data['_timestamp']
        result.append(data)
    
    return result
