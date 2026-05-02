# Market Stats API Endpoints

## Overview

Public API endpoints for accessing market demand data and skill trends. No authentication required.

---

## Endpoints

### 1. GET `/market/overview`

Get overall market statistics and overview.

**Response:**
```json
{
  "total_skills_tracked": 1210,
  "avg_market_demand": 1.73,
  "high_demand_skills_count": 44,
  "growing_skills_count": 37,
  "top_5_skills": [
    {"skill_name": "Python", "demand": 13.14}
  ],
  "snapshot_date": "2026-05-01T11:34:52.889780"
}
```

---

### 2. GET `/market/skill-trend/{skill_name}`

Get historical demand trend for a specific skill.

**Parameters:**
- `skill_name` (path): Name of the skill (e.g., "Python", "Docker")
- `period` (query): "weekly" or "monthly" (default: weekly)
- `duration` (query): Number of periods to look back, 1-12 (default: 4)

**Example:**
```bash
GET /market/skill-trend/Python?period=weekly&duration=4
```

**Response:**
```json
{
  "skill_name": "Python",
  "period": "weekly",
  "duration": 4,
  "data": [
    {
      "week_start": "2026-04-27T00:00:00+00:00",
      "avg_demand": 13.14,
      "avg_job_count": 18.0
    }
  ]
}
```

---

### 3. GET `/market/trending-skills`

Get top trending skills by growth rate.

**Parameters:**
- `period_days` (query): Period to calculate growth over, 7-90 (default: 30)
- `limit` (query): Max skills to return, 1-50 (default: 10)
- `min_demand` (query): Minimum demand % threshold, 0-100 (default: 5.0)

**Example:**
```bash
GET /market/trending-skills?limit=5&min_demand=10
```

**Response:**
```json
{
  "period_days": 30,
  "min_demand_threshold": 10.0,
  "trending_skills": [
    {
      "skill_name": "Python",
      "current_demand": 13.14,
      "growth_rate": 25.5,
      "job_count": 18,
      "trend": "high"
    }
  ]
}
```

**Trend Categories:**
- `explosive`: growth > 50%
- `high`: growth > 20%
- `moderate`: growth > 10%
- `stable`: growth > 0%

---

### 4. POST `/market/compare`

Compare multiple skills side-by-side.

**Request Body:**
```json
{
  "skill_names": ["Python", "Java", "Docker"]
}
```

**Response:**
```json
{
  "skills": [
    {
      "skill_name": "Python",
      "demand_score": 13.14,
      "growth_rate": 0,
      "job_count": 18,
      "avg_salary_min": 21562500,
      "avg_salary_max": 32555555,
      "salary_premium_pct": 38.6
    },
    {
      "skill_name": "Java",
      "demand_score": 8.76,
      "growth_rate": 0,
      "job_count": 12,
      "avg_salary_min": 17800000,
      "avg_salary_max": 32571428,
      "salary_premium_pct": 14.4
    }
  ],
  "comparison_date": "2026-05-01T11:34:42.955067"
}
```

---

### 5. GET `/analysis/market-stats` (Legacy)

Get market statistics including top trending skills.

**Parameters:**
- `limit` (query): Max skills to return, 1-50 (default: 10)

**Response:**
```json
{
  "total_skills": 1210,
  "last_updated": "2026-05-01T11:34:52.889780",
  "top_skills": [
    {
      "skill_name": "Python",
      "demand_score": 13.14,
      "avg_salary_min": 21562500,
      "job_count_30d": 18,
      "growth_rate_30d": 0.0,
      "category": "Programming Language"
    }
  ]
}
```

---

## Understanding Demand Score

**New Calculation (Correct):**
```
demand_score = (skill_appears_in_jobs / total_jobs_in_market) * 100
```

**Interpretation:**
- `13.14%` = Skill appears in 13.14% of all jobs
- `50%` = Skill appears in half of all jobs
- `0.73%` = Rare skill, appears in less than 1% of jobs

**Example:**
- Python: 18 jobs out of 137 total = **13.14% demand**
- Docker: 17 jobs out of 137 total = **12.41% demand**

---

## Rate Limits

- **Public endpoints**: 30 requests/minute
- **Authenticated users**: 100 requests/minute

---

## Error Responses

**404 Not Found:**
```json
{
  "detail": "No historical data found for skill 'InvalidSkill'"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Failed to retrieve market stats: <error message>"
}
```

---

## Usage Examples

### JavaScript/Fetch
```javascript
// Get Python trend
const response = await fetch('http://localhost:8000/market/skill-trend/Python?period=weekly&duration=4');
const data = await response.json();
console.log(data);

// Compare skills
const compareResponse = await fetch('http://localhost:8000/market/compare', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({skill_names: ['Python', 'Java', 'Docker']})
});
const comparison = await compareResponse.json();
```

### Python
```python
import requests

# Get market overview
response = requests.get('http://localhost:8000/market/overview')
data = response.json()
print(f"Total skills tracked: {data['total_skills_tracked']}")

# Get trending skills
trending = requests.get('http://localhost:8000/market/trending-skills?limit=5')
print(trending.json())
```

### cURL
```bash
# Get skill trend
curl "http://localhost:8000/market/skill-trend/Python?period=weekly&duration=4"

# Compare skills
curl -X POST "http://localhost:8000/market/compare" \
  -H "Content-Type: application/json" \
  -d '{"skill_names": ["Python", "Java", "Docker"]}'
```

---

## Notes

- All endpoints are **public** (no authentication required)
- Data is updated **daily at 2:00 AM**
- Historical data available for **4+ days**
- Demand scores represent **actual market penetration rates**
- Growth rates calculated over **30-day periods**
