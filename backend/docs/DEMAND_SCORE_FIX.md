# 🔧 Fix Demand Score Calculation

## Vấn Đề

### Cách tính SAI (hiện tại):
```python
demand_score = min(100, (count_current / 100) * 80 + max(0, growth) * 20)
```

**Vấn đề:**
- Chia cho 100 (magic number không liên quan gì đến thị trường thực tế)
- Nếu có 137 jobs trong thị trường, nhưng vẫn chia cho 100
- Python xuất hiện trong 18/137 jobs (13.1%) nhưng được tính là 34.4 điểm
- Không phản ánh đúng market penetration

### Cách tính ĐÚNG:
```python
# Demand = % jobs yêu cầu skill này
demand_score = (skill_appears_in_jobs / total_jobs_in_market) * 100
```

**Ví dụ:**
- Python: 18/137 = **13.1%** demand
- ReactJS: 50/100 = **50%** demand
- Rare skill: 1/137 = **0.7%** demand

---

## Giải Pháp

### 1. Tách Demand và Growth thành 2 metrics riêng

**Demand Score (0-100%):**
- Đo lường: Tỷ lệ % jobs yêu cầu skill
- Công thức: `(count / total_jobs) * 100`
- Ý nghĩa: Skill phổ biến đến mức nào trong thị trường

**Growth Rate (-100% to +∞):**
- Đo lường: Tốc độ tăng/giảm nhu cầu
- Công thức: `(current - previous) / previous`
- Ý nghĩa: Skill đang trending up/down

### 2. Code Changes

**File: `worker/tasks/market_stats_tasks.py`**

```python
# OLD (WRONG):
demand_score = min(100, (count_current / 100) * 80 + max(0, growth) * 20)

# NEW (CORRECT):
# Calculate total jobs in current period
total_jobs_current = len([j for j in jobs_60d if j.created_at >= thirty_days_ago])

# Demand = Market Penetration Rate
demand_score = (count_current / total_jobs_current) * 100 if total_jobs_current > 0 else 0.0

# Growth stays separate
growth_rate = 0.0
if count_prev > 0:
    growth_rate = (count_current - count_prev) / count_prev
# Don't set growth=1.0 for new skills, keep it 0.0
```

### 3. Database Schema (no changes needed)

Existing columns work fine:
- `demand_score`: Now stores true penetration % (0-100)
- `growth_rate_30d`: Already stores growth rate

### 4. Update Market Sentiment Logic

**File: `services/analysis_service/growth_calculator.py`**

```python
# OLD thresholds (based on wrong scores):
if avg_demand > 70:  # Never reached because max was 39.2
    return "Tăng trưởng cao"

# NEW thresholds (based on penetration %):
if avg_demand > 15 and avg_growth > 0.2:  # >15% penetration + 20% growth
    return "Tăng trưởng cao"
elif avg_demand > 8 or avg_growth > 0.1:  # >8% penetration or 10% growth
    return "Tăng trưởng ổn định"
elif avg_growth < -0.1:  # Declining 10%+
    return "Giảm nhu cầu"
else:
    return "Ổn định"
```

---

## Expected Results After Fix

### Before (Wrong):
| Skill | Jobs | Wrong Score | Meaning |
|-------|------|-------------|---------|
| Python | 18/137 | 34.4 | ??? |
| Teamwork | 24/137 | 39.2 | ??? |
| Rare | 1/137 | 20.8 | ??? |

### After (Correct):
| Skill | Jobs | Correct Score | Meaning |
|-------|------|---------------|---------|
| Python | 18/137 | **13.1%** | 13% of jobs need Python |
| Teamwork | 24/137 | **17.5%** | 18% of jobs need Teamwork |
| Rare | 1/137 | **0.7%** | Less than 1% of jobs need this |

---

## Benefits

1. ✅ **Intuitive**: 50% demand = skill appears in half of all jobs
2. ✅ **Comparable**: Can compare across different time periods
3. ✅ **Actionable**: "Learn Python (13% demand) vs Rare Skill (0.7% demand)"
4. ✅ **Accurate**: Reflects true market penetration
5. ✅ **No magic numbers**: Uses actual market data

---

## Implementation Priority

**HIGH PRIORITY** - This affects:
- Gap analysis recommendations
- Market fit scoring
- Skill prioritization
- Career path suggestions

Should be fixed ASAP.
