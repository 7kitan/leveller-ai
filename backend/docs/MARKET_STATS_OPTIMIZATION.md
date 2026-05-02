# Market Stats Optimization Plan

## Current Issues

### 1. **Too Frequent Aggregation**
```python
# Current: Runs every 1 hour
"hourly-market-aggregation": {
    "task": "worker.tasks.market_stats_tasks.aggregate_market_data",
    "schedule": 3600.0,  # ❌ 1 hour
}
```

**Problem:**
- Creates 24 snapshots per day per skill
- Database bloat: 3,523 snapshots/day × 1,210 skills = 4.2M rows/year
- Unnecessary computation
- No deduplication logic

**Evidence:**
```sql
-- Snapshots per day
2026-05-01: 3,523 snapshots
2026-04-30: 3,531 snapshots
2026-04-29: 7,062 snapshots (2x - why?)
```

### 2. **Missing Indexes for Time-Series Queries**

**Current indexes:**
```sql
-- market_skill_history
ix_market_skill_history_skill_name (skill_name)
ix_market_skill_history_snapshot_date (snapshot_date)
```

**Problem:**
- No composite index for common query pattern: `WHERE skill_name = ? AND snapshot_date BETWEEN ? AND ?`
- Queries like "get Python demand for last 30 days" require index scan + filter

### 3. **No Aggregation by Week/Month**

**Current:**
- Only daily snapshots
- No built-in functions to get weekly/monthly trends
- Frontend/API must aggregate on-the-fly

---

## Solution

### 1. **Change to Daily Aggregation**

**File: `worker/celery_app.py`**

```python
beat_schedule={
    # Change from hourly to daily at 2 AM
    "daily-market-aggregation": {
        "task": "worker.tasks.market_stats_tasks.aggregate_market_data",
        "schedule": crontab(hour=2, minute=0),  # 2:00 AM daily
    },
}
```

**Benefits:**
- 1 snapshot/day/skill instead of 24
- Reduces storage by 96%
- Consistent snapshot time for comparisons

### 2. **Add Deduplication Logic**

**File: `worker/tasks/market_stats_tasks.py`**

```python
# Before saving history snapshot
# Check if we already have a snapshot today
existing_today = db.query(MarketSkillHistory).filter(
    MarketSkillHistory.skill_name == skill_name,
    func.date(MarketSkillHistory.snapshot_date) == func.date(now)
).first()

if existing_today:
    # Update existing snapshot instead of creating new one
    existing_today.job_count = count_current
    existing_today.avg_salary = int(avg_salary_val)
    existing_today.demand_score = demand_score
    existing_today.snapshot_date = now
else:
    # Create new snapshot
    history_record = MarketSkillHistory(...)
    db.add(history_record)
```

### 3. **Add Composite Index**

**Migration SQL:**

```sql
-- Composite index for time-series queries
CREATE INDEX idx_skill_history_skill_date 
ON market_skill_history (skill_name, snapshot_date DESC);

-- Partial index for recent data (most queried)
CREATE INDEX idx_skill_history_recent 
ON market_skill_history (skill_name, snapshot_date DESC)
WHERE snapshot_date >= NOW() - INTERVAL '90 days';

-- Index for demand score queries
CREATE INDEX idx_skill_stats_demand 
ON market_skill_stats (demand_score DESC) 
WHERE demand_score IS NOT NULL;
```

### 4. **Add Time-Period Aggregation Functions**

**New file: `shared/market_stats_utils.py`**

```python
from datetime import datetime, timedelta
from sqlalchemy import func
from shared.models import MarketSkillHistory

def get_skill_trend_weekly(db, skill_name: str, weeks: int = 4):
    """
    Get weekly aggregated demand for a skill.
    Returns: [{week_start, avg_demand, avg_job_count}, ...]
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
            "week_start": r.week_start,
            "avg_demand": round(r.avg_demand, 2),
            "avg_job_count": round(r.avg_job_count, 1)
        }
        for r in results
    ]

def get_skill_trend_monthly(db, skill_name: str, months: int = 6):
    """
    Get monthly aggregated demand for a skill.
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
            "month": r.month_start.strftime("%Y-%m"),
            "avg_demand": round(r.avg_demand, 2),
            "max_demand": round(r.max_demand, 2),
            "min_demand": round(r.min_demand, 2),
            "avg_job_count": round(r.avg_job_count, 1)
        }
        for r in results
    ]

def get_top_trending_skills(db, period_days: int = 30, limit: int = 10):
    """
    Get skills with highest growth rate in the period.
    """
    cutoff = datetime.now() - timedelta(days=period_days)
    
    # Get first and last snapshot for each skill in period
    subq_first = db.query(
        MarketSkillHistory.skill_name,
        func.min(MarketSkillHistory.snapshot_date).label('first_date')
    ).filter(
        MarketSkillHistory.snapshot_date >= cutoff
    ).group_by(MarketSkillHistory.skill_name).subquery()
    
    subq_last = db.query(
        MarketSkillHistory.skill_name,
        func.max(MarketSkillHistory.snapshot_date).label('last_date')
    ).filter(
        MarketSkillHistory.snapshot_date >= cutoff
    ).group_by(MarketSkillHistory.skill_name).subquery()
    
    # Calculate growth rate
    # ... (complex query, can be optimized)
    
    return results
```

### 5. **API Endpoints for Time-Series Data**

**File: `services/analysis_service/main.py`**

```python
@router.get("/market/skill-trend/{skill_name}")
def get_skill_market_trend(
    skill_name: str,
    period: str = "weekly",  # weekly, monthly
    duration: int = 4,  # 4 weeks or 4 months
    db: Session = Depends(get_db)
):
    """
    Get historical demand trend for a skill.
    """
    from shared.market_stats_utils import get_skill_trend_weekly, get_skill_trend_monthly
    
    if period == "weekly":
        data = get_skill_trend_weekly(db, skill_name, weeks=duration)
    elif period == "monthly":
        data = get_skill_trend_monthly(db, skill_name, months=duration)
    else:
        raise HTTPException(400, "Invalid period. Use 'weekly' or 'monthly'")
    
    return {
        "skill_name": skill_name,
        "period": period,
        "data": data
    }

@router.get("/market/trending-skills")
def get_trending_skills(
    period_days: int = 30,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get top trending skills by growth rate.
    """
    from shared.market_stats_utils import get_top_trending_skills
    
    return {
        "period_days": period_days,
        "trending_skills": get_top_trending_skills(db, period_days, limit)
    }
```

---

## Implementation Priority

### Phase 1: Immediate (Fix Data Quality)
1. ✅ Change schedule to daily (2 AM)
2. ✅ Add deduplication logic
3. ✅ Clean up duplicate snapshots

### Phase 2: Performance (This Week)
1. ✅ Add composite indexes
2. ✅ Test query performance

### Phase 3: Features (Next Week)
1. ✅ Implement weekly/monthly aggregation functions
2. ✅ Add API endpoints
3. ✅ Update frontend to show trends

---

## Expected Impact

### Storage Reduction:
- Before: 3,523 snapshots/day × 365 days = 1.3M rows/year
- After: 1,210 skills × 365 days = 441K rows/year
- **Savings: 66% reduction**

### Query Performance:
- Before: Full table scan on 1.3M rows
- After: Index-only scan on 441K rows with composite index
- **Improvement: 10-50x faster**

### Data Quality:
- Before: Inconsistent snapshot times, duplicates
- After: 1 snapshot/day at 2 AM, no duplicates
- **Improvement: Consistent, reliable trends**
