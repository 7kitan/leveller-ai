# Match Calculation Update - Technical Skills Only

**Date**: 2026-05-01  
**Status**: ✅ Deployed  
**Breaking Change**: Yes - `overall_match_pct` calculation changed

## Summary

Updated gap analysis to calculate `overall_match_pct` based on **technical skills only**, excluding soft skills. Soft skills now have a separate metric `soft_skills_match_pct`.

## Problem Statement

**Before**: `overall_match_pct` included both technical and soft skills (calculated by LLM)
- Mixed technical skills (Python, React, Docker) with soft skills (Communication, Leadership)
- Made it unclear what the percentage actually represented
- Soft skills inflated/deflated technical match scores

**After**: `overall_match_pct` = technical skills match only
- Clear separation: technical skills vs soft skills
- More accurate representation of technical fit
- Soft skills tracked separately for holistic view

## Changes Made

### 1. Match Calculation Logic

**File**: `backend/worker/langgraph_agents/gap_v3/nodes/finalize_nodes.py`

```python
# Calculate final match percentages
llm_match_pct = float(gap_analysis.get("overall_match_pct") or 0)
technical_match_pct = radar_chart_data["overall_match"] if radar_chart_data else llm_match_pct
soft_skills_match_pct = soft_skills_comparison["match_percentage"] if soft_skills_comparison else None

final_report = {
    "overall_match_pct": float(technical_match_pct),  # Technical skills only
    "soft_skills_match_pct": float(soft_skills_match_pct) if soft_skills_match_pct is not None else None,
    "llm_overall_match_pct": float(llm_match_pct),  # Original LLM (for reference)
    ...
}
```

### 2. Soft Skills Filtering

Soft skills are explicitly excluded from technical match calculation:

```python
SOFT_SKILL_CATEGORIES = {
    "Soft Skill", "soft skill", "Soft Skills", "soft skills",
    "Communication", "Leadership", "Teamwork", "Problem Solving",
    "Time Management", "Critical Thinking", "Adaptability"
}
```

### 3. Response Structure

**New fields in gap analysis response**:

```json
{
  "overall_match_pct": 76.0,           // Technical skills only (from radar chart)
  "soft_skills_match_pct": 66.7,      // Soft skills only (separate calculation)
  "llm_overall_match_pct": 72.5,      // Original LLM match (for reference/debugging)
  
  "radar_chart": {
    "overall_match": 76.0,             // Same as overall_match_pct
    "dimensions": [...],
    "cv_scores": [85, 70, 95, 80, 50],
    "priority_gaps": [...]
  },
  
  "soft_skills": {
    "cv_soft_skills": ["communication", "teamwork"],
    "jd_soft_skills": ["communication", "teamwork", "leadership"],
    "matched": ["communication", "teamwork"],
    "missing": ["leadership"],
    "match_percentage": 66.7,          // Same as soft_skills_match_pct
    "skill_count": {
      "cv": 2,
      "jd": 3,
      "matched": 2,
      "missing": 1
    }
  }
}
```

## Impact Analysis

### Frontend Changes Required

#### 1. Display Overall Match

**Before**:
```javascript
const matchScore = result.overall_match_pct; // Mixed technical + soft
```

**After**:
```javascript
const technicalMatch = result.overall_match_pct;      // Technical only
const softSkillsMatch = result.soft_skills_match_pct; // Soft skills only

// Display separately
console.log(`Technical Skills: ${technicalMatch}%`);
console.log(`Soft Skills: ${softSkillsMatch}%`);
```

#### 2. Combined Score (Optional)

If you want to show a combined score:

```javascript
// Weighted average (70% technical, 30% soft skills)
const combinedScore = (technicalMatch * 0.7) + (softSkillsMatch * 0.3);

// Or simple average
const avgScore = (technicalMatch + softSkillsMatch) / 2;
```

#### 3. UI Recommendations

**Option A: Separate Display**
```
Technical Skills Match: 76% ████████░░
Soft Skills Match:      67% ███████░░░
```

**Option B: Radar Chart + Badges**
```
[Radar Chart showing 5 technical dimensions]

Soft Skills:
✅ Communication
✅ Teamwork  
❌ Leadership (missing)
```

**Option C: Two Progress Circles**
```
┌─────────────┐  ┌─────────────┐
│ Technical   │  │ Soft Skills │
│    76%      │  │    67%      │
└─────────────┘  └─────────────┘
```

### Backend Impact

#### Database (UserAnalysis table)

- `match_score` column: Now stores **technical match only**
- Historical data: Old records have mixed scores (cannot retroactively fix)
- **Recommendation**: Add migration note or version flag

#### Growth Calculator

**File**: `services/analysis_service/growth_calculator.py`

Current implementation uses `overall_match_pct` for salary/potential calculations:
```python
def calculate_skill_impact(skill_gaps, job_id, current_match_pct, db):
    # Uses current_match_pct (now technical only)
    potential_match = current_match_pct + boost_from_courses
    ...
```

**Impact**: Growth calculations now based on technical skills only (correct behavior)

#### Market Fit Service

**File**: `services/analysis_service/market_fit_service.py`

Uses `match_score` from UserAnalysis:
```python
avg_match = db.query(func.avg(UserAnalysis.match_score)).scalar()
```

**Impact**: Market fit now reflects technical match only (more accurate)

## Migration Guide

### For Existing Data

**Problem**: Historical analyses have mixed technical+soft scores in `match_score`

**Solutions**:

1. **Accept inconsistency** (recommended for MVP)
   - New analyses: technical only
   - Old analyses: mixed scores
   - Add note in UI: "Match calculation updated on 2026-05-01"

2. **Recompute historical data** (optional)
   - Run migration script to recalculate all UserAnalysis records
   - Expensive: requires re-running radar chart for all records

3. **Add version flag** (best practice)
   ```python
   class UserAnalysis:
       match_calculation_version = Column(String, default="v2")
       # v1 = mixed, v2 = technical only
   ```

### For Frontend

**Step 1**: Update match display logic
```javascript
// Check if new fields exist
if (result.soft_skills_match_pct !== undefined) {
  // New format: separate technical and soft
  displayTechnicalMatch(result.overall_match_pct);
  displaySoftSkillsMatch(result.soft_skills_match_pct);
} else {
  // Old format: mixed score
  displayMixedMatch(result.overall_match_pct);
}
```

**Step 2**: Update dashboard/charts
- Change "Overall Match" label to "Technical Skills Match"
- Add separate soft skills indicator

**Step 3**: Update tooltips/help text
```
Technical Skills Match: How well your technical skills (programming, 
tools, frameworks) match the job requirements.

Soft Skills Match: How well your soft skills (communication, leadership, 
teamwork) match the job requirements.
```

## Testing

### Test Cases

1. **Technical skills only**
   - CV: Python, React, Docker
   - JD: Python, React, Docker, Kubernetes
   - Expected: `overall_match_pct = 75%` (3/4)

2. **Soft skills only**
   - CV: Communication, Teamwork
   - JD: Communication, Teamwork, Leadership
   - Expected: `soft_skills_match_pct = 66.7%` (2/3)

3. **Mixed skills**
   - CV: Python (tech), Communication (soft)
   - JD: Python, React (tech), Communication, Leadership (soft)
   - Expected: 
     - `overall_match_pct = 50%` (1/2 technical)
     - `soft_skills_match_pct = 50%` (1/2 soft)

4. **No soft skills in JD**
   - CV: Python, Communication
   - JD: Python, React (no soft skills)
   - Expected:
     - `overall_match_pct = 50%` (1/2 technical)
     - `soft_skills_match_pct = null` (no soft skills required)

### Manual Testing

```bash
# 1. Trigger gap analysis
POST /analysis/gap
{
  "cv_id": "...",
  "job_id": "..."
}

# 2. Check result
GET /analysis/status/{task_id}

# 3. Verify fields
{
  "overall_match_pct": 76.0,        // Should be technical only
  "soft_skills_match_pct": 66.7,   // Should exist if JD has soft skills
  "llm_overall_match_pct": 72.5,   // Original LLM (for comparison)
  "radar_chart": {
    "overall_match": 76.0           // Should match overall_match_pct
  }
}
```

## Rollback Plan

If issues arise, rollback by reverting this change:

```python
# Revert to LLM match
final_report = {
    "overall_match_pct": float(gap_analysis.get("overall_match_pct") or 0),
    # Remove soft_skills_match_pct and llm_overall_match_pct
    ...
}
```

Then rebuild and redeploy:
```bash
docker-compose build worker_crawler
docker-compose up -d worker_crawler
```

## Benefits

✅ **Clearer metrics**: Technical and soft skills separated  
✅ **More accurate**: Technical match not diluted by soft skills  
✅ **Better UX**: Users understand what percentage means  
✅ **Actionable insights**: Can focus on technical gaps separately  
✅ **Flexible display**: Frontend can show combined or separate  

## Potential Issues

⚠️ **Historical data inconsistency**: Old analyses have mixed scores  
⚠️ **Frontend compatibility**: Requires frontend updates  
⚠️ **User confusion**: Match percentages may change for same CV/JD  
⚠️ **Documentation**: All docs need to reflect new calculation  

## Next Steps

1. ✅ Deploy backend changes (completed)
2. ⬜ Update frontend to display separate metrics
3. ⬜ Update API documentation
4. ⬜ Add migration notes for historical data
5. ⬜ Update user-facing help text/tooltips
6. ⬜ Monitor for issues in production

## Related Files

- `backend/worker/langgraph_agents/gap_v3/nodes/finalize_nodes.py` - Match calculation
- `backend/shared/radar_dimensions.py` - Technical skills grouping
- `backend/docs/API_RADAR_CHART.md` - API documentation
- `backend/docs/RADAR_CHART_INTEGRATION_COMPLETE.md` - Integration guide

## Questions & Answers

**Q: Why not keep the mixed score?**  
A: Mixed scores are ambiguous. A 70% match could mean strong technical + weak soft, or vice versa. Separation provides clarity.

**Q: Should we weight technical vs soft skills?**  
A: That's a frontend decision. Backend provides both metrics separately. Frontend can display as-is or create weighted average.

**Q: What if JD has no soft skills?**  
A: `soft_skills_match_pct` will be `null`. Frontend should handle gracefully (e.g., show "N/A" or hide soft skills section).

**Q: What about historical analyses?**  
A: They retain mixed scores. Consider adding version flag or recomputing if needed.

---

**Status**: ✅ Production Ready  
**Last Updated**: 2026-05-01 19:23 UTC+7
