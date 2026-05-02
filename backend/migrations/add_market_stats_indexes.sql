-- Market Stats Performance Optimization
-- Add indexes for time-series queries

-- 1. Composite index for common query pattern: skill + date range
CREATE INDEX IF NOT EXISTS idx_skill_history_skill_date 
ON market_skill_history (skill_name, snapshot_date DESC);

-- 2. Partial index for recent data (most frequently queried)
CREATE INDEX IF NOT EXISTS idx_skill_history_recent 
ON market_skill_history (skill_name, snapshot_date DESC)
WHERE snapshot_date >= NOW() - INTERVAL '90 days';

-- 3. Index for demand score queries (top skills, trending)
CREATE INDEX IF NOT EXISTS idx_skill_stats_demand 
ON market_skill_stats (demand_score DESC NULLS LAST)
WHERE demand_score IS NOT NULL;

-- 4. Index for growth rate queries
CREATE INDEX IF NOT EXISTS idx_skill_stats_growth 
ON market_skill_stats (growth_rate_30d DESC NULLS LAST)
WHERE growth_rate_30d IS NOT NULL;

-- 5. Composite index for category + demand queries
CREATE INDEX IF NOT EXISTS idx_skill_stats_category_demand 
ON market_skill_stats (category, demand_score DESC NULLS LAST)
WHERE category IS NOT NULL AND demand_score IS NOT NULL;

-- Analyze tables to update statistics
ANALYZE market_skill_stats;
ANALYZE market_skill_history;
