# Daily Data API Endpoint

## New Endpoint for Daily Granularity

### GET `/market/skill-trend-daily/{skill_name}`

Get daily demand data for a specific skill (not aggregated by week/month).

**Parameters:**
- `skill_name` (path): Name of the skill
- `days` (query): Number of days to look back, 1-90 (default: 7)

**Example:**
```bash
GET /market/skill-trend-daily/Python?days=7
```

**Response:**
```json
{
  "skill_name": "Python",
  "days": 7,
  "data": [
    {
      "date": "2026-04-25",
      "demand_score": 12.8,
      "job_count": 17
    },
    {
      "date": "2026-04-26",
      "demand_score": 13.0,
      "job_count": 18
    },
    {
      "date": "2026-04-27",
      "demand_score": 13.1,
      "job_count": 18
    },
    {
      "date": "2026-04-28",
      "demand_score": 13.1,
      "job_count": 18
    },
    {
      "date": "2026-04-29",
      "demand_score": 13.1,
      "job_count": 18
    },
    {
      "date": "2026-04-30",
      "demand_score": 13.1,
      "job_count": 18
    },
    {
      "date": "2026-05-01",
      "demand_score": 13.1,
      "job_count": 18
    }
  ]
}
```

**Use cases:**
- 7-day chart: `?days=7`
- 30-day chart: `?days=30`
- 90-day chart: `?days=90`

---

## Understanding the Data

### What Each Daily Snapshot Represents

Each day's `demand_score` is calculated using a **30-day rolling window**:

```
April 28 demand = (Python jobs from Mar 29 - Apr 28) / (Total jobs Mar 29 - Apr 28) × 100
April 29 demand = (Python jobs from Mar 30 - Apr 29) / (Total jobs Mar 30 - Apr 29) × 100
April 30 demand = (Python jobs from Mar 31 - Apr 30) / (Total jobs Mar 31 - Apr 30) × 100
```

**Why rolling window?**
- ✅ Smooths out daily fluctuations
- ✅ More stable signal
- ✅ Better for trend analysis
- ✅ Industry standard

**Example:**
- Monday: 10 jobs posted, 2 need Python → 20% (noisy!)
- Tuesday: 2 jobs posted, 0 need Python → 0% (noisy!)
- **30-day average: 137 jobs, 18 need Python → 13.1%** (stable!)

---

## Implementation

### Add to `shared/market_stats_utils.py`:

```python
def get_skill_trend_daily(db: Session, skill_name: str, days: int = 7) -> List[Dict]:
    """
    Get daily demand data for a skill (not aggregated).
    
    Args:
        db: Database session
        skill_name: Name of the skill
        days: Number of days to look back (default: 7)
    
    Returns:
        List of dicts with date, demand_score, job_count
    """
    cutoff = datetime.now() - timedelta(days=days)
    
    results = db.query(MarketSkillHistory).filter(
        MarketSkillHistory.skill_name == skill_name,
        MarketSkillHistory.snapshot_date >= cutoff
    ).order_by(MarketSkillHistory.snapshot_date).all()
    
    # Group by date (in case multiple snapshots per day)
    daily_data = {}
    for r in results:
        date_key = r.snapshot_date.date().isoformat()
        if date_key not in daily_data:
            daily_data[date_key] = {
                "date": date_key,
                "demand_score": round(r.demand_score, 2) if r.demand_score else 0,
                "job_count": r.job_count or 0
            }
    
    return list(daily_data.values())
```

### Add to `services/analysis_service/main.py`:

```python
@app.get("/market/skill-trend-daily/{skill_name}")
def get_skill_trend_daily_endpoint(
    skill_name: str,
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """
    Get daily demand data for a specific skill.
    
    Args:
        skill_name: Name of the skill
        days: Number of days to look back (1-90, default: 7)
    
    Returns:
        Daily data points with demand scores
    """
    try:
        from shared.market_stats_utils import get_skill_trend_daily
        
        data = get_skill_trend_daily(db, skill_name, days=days)
        
        if not data:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for skill '{skill_name}' in the last {days} days"
            )
        
        return {
            "skill_name": skill_name,
            "days": days,
            "data": data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get daily trend for {skill_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve daily trend: {str(e)}")
```

### Add to `gateway/auth_middleware.py`:

```python
public_paths = [
    # ... existing paths
    "/market/skill-trend-daily",  # Daily granularity data
]
```

---

## Chart Examples

### 7-Day Chart (Daily Points)

```javascript
// Fetch 7 days of daily data
const response = await fetch('/market/skill-trend-daily/Python?days=7');
const data = await response.json();

// data.data = [
//   {date: "2026-04-25", demand_score: 12.8, job_count: 17},
//   {date: "2026-04-26", demand_score: 13.0, job_count: 18},
//   ...
// ]

// Plot with Chart.js
new Chart(ctx, {
  type: 'line',
  data: {
    labels: data.data.map(d => d.date),
    datasets: [{
      label: 'Python Demand (%)',
      data: data.data.map(d => d.demand_score)
    }]
  }
});
```

### 30-Day Chart (Daily Points)

```javascript
const response = await fetch('/market/skill-trend-daily/Python?days=30');
// Returns 30 daily data points
```

### Comparison: Daily vs Weekly vs Monthly

| Granularity | Data Points | Use Case |
|-------------|-------------|----------|
| **Daily** | 7 points for 7 days | Short-term trends, recent changes |
| **Weekly** | 4 points for 4 weeks | Medium-term trends, smoother |
| **Monthly** | 6 points for 6 months | Long-term trends, very smooth |

---

## Data Availability

Current system has:
- ✅ Daily snapshots since April 28, 2026
- ✅ 1,177 skills tracked daily
- ✅ Perfect deduplication (1 snapshot/skill/day)

**Coverage:**
- Last 7 days: ✅ Available (4 days currently, will grow)
- Last 30 days: ⏳ Growing (4 days currently)
- Last 90 days: ⏳ Will be available after 90 days

---

## Summary

**You are correct!** For 7-day charts, you need 7 daily data points.

**Good news:** The system ALREADY has this!
- ✅ Daily snapshots stored in `market_skill_history`
- ✅ One snapshot per skill per day
- ✅ Just need to add API endpoint to expose it

**Next step:** Implement `/market/skill-trend-daily` endpoint (15 minutes of work)
