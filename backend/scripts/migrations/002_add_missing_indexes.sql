-- ============================================================================
-- Add Missing Indexes for Performance Optimization
-- ============================================================================
-- Run this script to add critical missing indexes across all tables
-- Estimated time: 2-5 minutes depending on data size
-- ============================================================================

BEGIN;

-- ============================================================================
-- COURSES TABLE - Critical for search performance
-- ============================================================================

-- 1. GIN index for tags array (for ANY() operator)
CREATE INDEX IF NOT EXISTS idx_courses_tags_gin 
ON courses USING GIN (tags);

-- 2. GIN index for skills_raw JSON (for JSON search)
-- Note: Cast JSON to JSONB for GIN index support
CREATE INDEX IF NOT EXISTS idx_courses_skills_raw_gin 
ON courses USING GIN ((skills_raw::jsonb));

-- 3. Index on is_active (frequently used in WHERE clauses)
CREATE INDEX IF NOT EXISTS idx_courses_is_active 
ON courses (is_active) WHERE is_active = true;

-- 4. Index on level (frequently used for filtering)
CREATE INDEX IF NOT EXISTS idx_courses_level 
ON courses (level);

-- 5. Composite index for common query pattern (is_active + created_at)
CREATE INDEX IF NOT EXISTS idx_courses_active_created 
ON courses (is_active, created_at DESC) WHERE is_active = true;

-- 6. Text search indexes using pg_trgm for ILIKE performance
-- Enable pg_trgm extension if not already enabled
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_courses_title_trgm 
ON courses USING GIN (title gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_courses_platform_trgm 
ON courses USING GIN (platform gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_courses_provider_trgm 
ON courses USING GIN (provider gin_trgm_ops);

-- 7. Vector index for pgvector similarity search (HNSW for fast ANN search)
-- Note: HNSW is faster than IVFFlat for most use cases
CREATE INDEX IF NOT EXISTS idx_courses_vector_hnsw 
ON courses USING hnsw (vector vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

COMMENT ON INDEX idx_courses_vector_hnsw IS 'HNSW index for fast vector similarity search using cosine distance';


-- ============================================================================
-- JOB_SKILL_REQUIREMENT TABLE - Critical for joins
-- ============================================================================

-- Foreign key indexes (critical for JOIN performance)
CREATE INDEX IF NOT EXISTS idx_job_skill_req_job_id 
ON job_skill_requirement (job_id);

CREATE INDEX IF NOT EXISTS idx_job_skill_req_skill_id 
ON job_skill_requirement (skill_id);

-- Composite index for common query pattern
CREATE INDEX IF NOT EXISTS idx_job_skill_req_job_mandatory 
ON job_skill_requirement (job_id, is_mandatory);

-- Index on required_level for filtering
CREATE INDEX IF NOT EXISTS idx_job_skill_req_level 
ON job_skill_requirement (required_level);


-- ============================================================================
-- JOBS TABLE - Add missing indexes
-- ============================================================================

-- Index on status (frequently filtered)
CREATE INDEX IF NOT EXISTS idx_jobs_status 
ON jobs (status) WHERE status = 'active';

-- Index on created_at for time-based queries
CREATE INDEX IF NOT EXISTS idx_jobs_created_at 
ON jobs (created_at DESC);

-- Composite index for common query pattern (status + created_at)
CREATE INDEX IF NOT EXISTS idx_jobs_status_created 
ON jobs (status, created_at DESC) WHERE status = 'active';


-- ============================================================================
-- USER_SKILL_PROFILE TABLE - Critical for user queries
-- ============================================================================

-- Index on user_id (frequently filtered)
CREATE INDEX IF NOT EXISTS idx_user_skill_profile_user_id 
ON user_skill_profile (user_id);

-- Index on skill_id (FK, frequently joined)
CREATE INDEX IF NOT EXISTS idx_user_skill_profile_skill_id 
ON user_skill_profile (skill_id);

-- Index on cv_id (FK, frequently joined)
CREATE INDEX IF NOT EXISTS idx_user_skill_profile_cv_id 
ON user_skill_profile (cv_id);

-- Index on level for filtering
CREATE INDEX IF NOT EXISTS idx_user_skill_profile_level 
ON user_skill_profile (level);

-- Composite index for common query pattern
CREATE INDEX IF NOT EXISTS idx_user_skill_profile_user_skill 
ON user_skill_profile (user_id, skill_id);


-- ============================================================================
-- USER_WORK_EXPERIENCES TABLE
-- ============================================================================

-- Index on cv_id (FK, frequently joined)
CREATE INDEX IF NOT EXISTS idx_user_work_exp_cv_id 
ON user_work_experiences (cv_id);


-- ============================================================================
-- USER_CVS TABLE - Add missing indexes
-- ============================================================================

-- Index on user_id for filtering
CREATE INDEX IF NOT EXISTS idx_user_cvs_user_id 
ON user_cvs (user_id);

-- Index on created_at for sorting
CREATE INDEX IF NOT EXISTS idx_user_cvs_created_at 
ON user_cvs (created_at DESC);


-- ============================================================================
-- SKILLS TABLE - Add vector index
-- ============================================================================

-- Vector index for skill similarity search
CREATE INDEX IF NOT EXISTS idx_skills_vector_hnsw 
ON skills USING hnsw (vector vector_cosine_ops)
WITH (m = 16, ef_construction = 64)
WHERE vector IS NOT NULL;


COMMIT;

-- ============================================================================
-- Performance Tips:
-- ============================================================================
-- 1. Run ANALYZE after creating indexes to update statistics
-- 2. Monitor query performance with EXPLAIN ANALYZE
-- 3. Consider REINDEX if indexes become bloated over time
-- 4. Use pg_stat_user_indexes to monitor index usage
-- 
-- To verify indexes were created, run:
-- SELECT schemaname, tablename, indexname 
-- FROM pg_indexes 
-- WHERE schemaname = 'public' AND indexname LIKE 'idx_%'
-- ORDER BY tablename, indexname;
-- ============================================================================
