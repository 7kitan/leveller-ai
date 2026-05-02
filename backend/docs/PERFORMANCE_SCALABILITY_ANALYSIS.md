# Market Stats Performance & Scalability Analysis

## Current Implementation Analysis

### ✅ What's Working Well

1. **Deduplication** - 1 snapshot/skill/day (perfect)
2. **Daily schedule** - Runs at 2 AM (low traffic time)
3. **Query speed** - Currently 0.240ms for 137 jobs (very fast)
4. **Memory usage** - Low with current data volume

---

## ⚠️ Critical Issues Found

### 1. **Missing Index on `jobs.created_at`**

**Current:**
```sql
-- Query uses Sequential Scan (slow for large tables)
Seq Scan on jobs  (cost=0.00..47.45 rows=140 width=2291)
Filter: (created_at >= (now() - '60 days'::interval))
```

**Problem:**
- No index on `created_at` column
- Sequential scan = reads ENTIRE table
- Performance degrades linearly with table size

**Impact at scale:**
| Jobs | Current (no index) | With index |
|------|-------------------|------------|
| 137 | 0.24ms ✅ | 0.1ms |
| 1,000 | ~2ms ✅ | 0.1ms |
| 10,000 | ~20ms ⚠️ | 0.2ms |
| 100,000 | ~200ms ❌ | 0.5ms |
| 1,000,000 | ~2s ❌❌ | 1ms |

**Solution:**
```sql
CREATE INDEX idx_jobs_created_at ON jobs (created_at DESC);
```

---

### 2. **Not Truly "Daily" Calculation**

**Current behavior:**
```python
# Uses rolling 30-day window
thirty_days_ago = now - timedelta(days=30)
jobs_60d = db.query(Job).filter(Job.created_at >= sixty_days_ago).all()

# Splits into two periods
is_current = job.created_at >= thirty_days_ago  # Last 30 days
else:  # 31-60 days ago
```

**What this means:**
- ❌ NOT "jobs added today" vs "jobs added yesterday"
- ✅ "Jobs in last 30 days" vs "jobs 31-60 days ago"
- Demand = skill_count_last_30d / total_jobs_last_30d

**Example:**
- Day 1: 100 jobs (0-30d), 50 jobs (31-60d)
- Day 2: 101 jobs (0-30d), 50 jobs (31-60d) ← Only 1 new job, but recalculates ALL
- Day 30: 130 jobs (0-30d), 80 jobs (31-60d)

**Is this a problem?**
- For demand score: ✅ OK - Rolling window is correct approach
- For growth rate: ⚠️ Needs more data points for accuracy
- For daily tracking: ❌ Not designed for "jobs per day" breakdown

---

### 3. **Memory & Processing Inefficiency**

**Current code:**
```python
# Loads ALL 60 days of jobs into memory
jobs_60d = db.query(Job).filter(...).all()  # ← Loads everything

# Then iterates through ALL jobs
for job in jobs_60d:  # O(n)
    for req in job.extracted_requirements_json:  # O(m)
        for skill_name in all_skills:  # O(k)
            stats_current[skill_name]["count"] += 1
```

**Time complexity:** O(jobs × skills_per_job × unique_skills)

**Memory usage:**
| Jobs | Avg size/job | Total memory |
|------|--------------|--------------|
| 137 | ~2KB | 274 KB ✅ |
| 1,000 | ~2KB | 2 MB ✅ |
| 10,000 | ~2KB | 20 MB ✅ |
| 100,000 | ~2KB | 200 MB ⚠️ |
| 1,000,000 | ~2KB | 2 GB ❌ |

**Processing time estimate:**
| Jobs | Skills/job | Processing time |
|------|-----------|-----------------|
| 137 | 10 | ~10ms ✅ |
| 1,000 | 10 | ~50ms ✅ |
| 10,000 | 10 | ~500ms ✅ |
| 100,000 | 10 | ~5s ⚠️ |
| 1,000,000 | 10 | ~50s ❌ |

---

## 📊 Scalability Thresholds

### Current Setup (No Optimization):

**✅ Works well up to:**
- 10,000 jobs (~500ms processing)
- 100 skills per job
- Daily aggregation

**⚠️ Starts to slow down:**
- 50,000 jobs (~2-3s processing)
- Memory usage: ~100MB
- Still acceptable for daily batch

**❌ Becomes problematic:**
- 100,000+ jobs (~5-10s processing)
- Memory usage: 200MB+
- Risk of timeout

---

## 🔧 Optimization Recommendations

### Priority 1: Add Index (CRITICAL)

```sql
-- Add index on created_at for fast date filtering
CREATE INDEX idx_jobs_created_at ON jobs (created_at DESC);

-- Add composite index for common query pattern
CREATE INDEX idx_jobs_created_status ON jobs (created_at DESC, status);

-- Analyze table to update statistics
ANALYZE jobs;
```

**Impact:**
- 10-100x faster queries at scale
- Reduces query time from O(n) to O(log n)

---

### Priority 2: Batch Processing (for 100k+ jobs)

```python
def aggregate_market_data_batched():
    """Process jobs in batches to reduce memory usage."""
    batch_size = 1000
    offset = 0
    
    stats_current = defaultdict(lambda: {"count": 0, "salaries_min": [], "salaries_max": []})
    
    while True:
        # Fetch batch
        jobs_batch = db.query(Job).filter(
            Job.created_at >= thirty_days_ago
        ).offset(offset).limit(batch_size).all()
        
        if not jobs_batch:
            break
        
        # Process batch
        for job in jobs_batch:
            # ... same logic
        
        offset += batch_size
    
    # Continue with aggregation
```

**Benefits:**
- Constant memory usage (~2MB per batch)
- Can handle millions of jobs
- Prevents OOM errors

---

### Priority 3: Incremental Updates (Advanced)

**Concept:** Only process NEW jobs since last run

```python
def aggregate_market_data_incremental():
    """Only process jobs added since last aggregation."""
    
    # Get last aggregation timestamp
    last_run = get_last_aggregation_time()
    
    # Only fetch NEW jobs
    new_jobs = db.query(Job).filter(
        Job.created_at >= last_run
    ).all()
    
    # Load existing stats
    existing_stats = load_current_stats()
    
    # Update stats with new jobs only
    for job in new_jobs:
        update_stats(existing_stats, job)
    
    # Recalculate demand scores
    recalculate_demand_scores(existing_stats)
```

**Benefits:**
- 100x faster for daily runs (only processes ~100 new jobs vs 10,000 total)
- Scales to millions of jobs
- Near real-time updates possible

**Tradeoffs:**
- More complex logic
- Need to track last run time
- Need to handle job updates/deletions

---

### Priority 4: Database-Level Aggregation

**Use SQL for aggregation instead of Python:**

```sql
-- Calculate skill counts directly in database
WITH skill_counts AS (
    SELECT 
        jsonb_array_elements(extracted_requirements_json)->>'skill_name' as skill_name,
        COUNT(*) as job_count
    FROM jobs
    WHERE created_at >= NOW() - INTERVAL '30 days'
    GROUP BY skill_name
),
total_jobs AS (
    SELECT COUNT(*) as total FROM jobs 
    WHERE created_at >= NOW() - INTERVAL '30 days'
)
SELECT 
    skill_name,
    job_count,
    (job_count::float / total.total * 100) as demand_score
FROM skill_counts, total_jobs as total;
```

**Benefits:**
- 10-50x faster (database optimized for aggregation)
- No memory issues (streaming results)
- Can leverage database indexes

**Tradeoffs:**
- More complex SQL
- Harder to debug
- Less flexible

---

## 📈 Recommended Implementation Plan

### Phase 1: Immediate (This Week)

1. ✅ **Add index on jobs.created_at**
   ```sql
   CREATE INDEX idx_jobs_created_at ON jobs (created_at DESC);
   ```

2. ✅ **Monitor performance**
   - Add timing logs to aggregation task
   - Track memory usage
   - Set up alerts for slow queries

### Phase 2: When reaching 10k jobs

1. ✅ **Implement batch processing**
   - Process 1,000 jobs at a time
   - Reduces memory footprint

2. ✅ **Add query timeout**
   - Prevent runaway queries
   - Fail gracefully

### Phase 3: When reaching 100k jobs

1. ✅ **Implement incremental updates**
   - Only process new jobs
   - 100x performance improvement

2. ✅ **Consider database-level aggregation**
   - Move heavy lifting to PostgreSQL
   - Use materialized views

### Phase 4: When reaching 1M jobs

1. ✅ **Distributed processing**
   - Use Celery task queue
   - Process skills in parallel

2. ✅ **Data partitioning**
   - Partition jobs table by date
   - Archive old data

---

## 🎯 Current Status & Recommendations

### Current State:
- ✅ Works perfectly for current scale (137 jobs)
- ✅ Daily aggregation stable
- ✅ Deduplication working
- ⚠️ Missing critical index
- ⚠️ Not optimized for scale

### Immediate Action Required:
```sql
-- Run this NOW to prepare for scale
CREATE INDEX idx_jobs_created_at ON jobs (created_at DESC);
ANALYZE jobs;
```

### Expected Performance After Index:
| Jobs | Query time | Processing time | Total time |
|------|-----------|-----------------|------------|
| 1,000 | 0.1ms | 50ms | **50ms** ✅ |
| 10,000 | 0.2ms | 500ms | **500ms** ✅ |
| 100,000 | 0.5ms | 5s | **5s** ⚠️ |

### When to Optimize Further:
- **Now:** Add index (critical)
- **At 10k jobs:** Add batch processing
- **At 50k jobs:** Consider incremental updates
- **At 100k+ jobs:** Database-level aggregation

---

## 💡 Answer to Your Questions

### 1. "Hiện tại cách update data stats đã ổn định chưa?"

**Answer:** ✅ Ổn định cho quy mô hiện tại (137 jobs)

**But:**
- ⚠️ Thiếu index quan trọng (cần add ngay)
- ⚠️ Chưa tối ưu cho scale lớn (10k+ jobs)

### 2. "Có tính theo ngày và job của ngày không nhỉ?"

**Answer:** ❌ KHÔNG tính theo từng ngày

**Thực tế:**
- Tính theo **rolling 30-day window**
- Demand = skills trong 30 ngày gần nhất / tổng jobs 30 ngày
- Growth = so sánh 0-30d vs 31-60d

**Có cần tính theo ngày không?**
- Cho demand score: ❌ Không cần (rolling window đúng)
- Cho trend analysis: ✅ Có thể cần (đã có trong history table)

### 3. "Scale up job lên thì có bị chậm không?"

**Answer:** ⚠️ CÓ, nhưng có thể fix

**Performance dự đoán:**
- 1,000 jobs: ✅ Fast (~50ms)
- 10,000 jobs: ✅ OK (~500ms)
- 100,000 jobs: ⚠️ Slow (~5s) - cần optimize
- 1,000,000 jobs: ❌ Very slow (~50s) - cần redesign

**Solution:** Add index NOW, optimize later when needed

---

## ✅ Action Items

1. **Immediate (Today):**
   ```sql
   CREATE INDEX idx_jobs_created_at ON jobs (created_at DESC);
   ```

2. **This Week:**
   - Add performance monitoring
   - Document current benchmarks

3. **When reaching 10k jobs:**
   - Implement batch processing
   - Add query timeouts

4. **When reaching 100k jobs:**
   - Incremental updates
   - Database-level aggregation
