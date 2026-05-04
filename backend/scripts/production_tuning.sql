-- Production Database Tuning
-- This script applies advanced PostgreSQL features (Indexes, Triggers, Functions)
-- that are not fully captured in SQLAlchemy models.
-- Safe to run multiple times (idempotent).

BEGIN;

-- ============================================================================
-- STEP 1: Enable Extensions
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================================
-- STEP 2: Advanced Indexes for Jobs (Full-Text & Performance)
-- ============================================================================

-- GIN indexes for fast ILIKE/Trigram search
CREATE INDEX IF NOT EXISTS idx_jobs_title_raw_trgm ON jobs USING GIN (title_raw gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_jobs_company_name_trgm ON jobs USING GIN (company_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_jobs_requirements_trgm ON jobs USING GIN (requirements gin_trgm_ops);

-- Composite indexes for common dashboard/listing queries
CREATE INDEX IF NOT EXISTS idx_jobs_status_location_created 
ON jobs (status, location_normalized, created_at DESC) 
WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_jobs_salary_range 
ON jobs (min_salary_vnd, max_salary_vnd) 
WHERE status = 'active' AND min_salary_vnd IS NOT NULL;

-- ============================================================================
-- STEP 3: YouTube Search Optimization (BM25 / Full-Text Search)
-- ============================================================================

-- 1. Add search_vector column if missing
ALTER TABLE youtube_courses ADD COLUMN IF NOT EXISTS search_vector tsvector;

-- 2. Function to generate search vector with weights
CREATE OR REPLACE FUNCTION youtube_courses_search_vector_update() 
RETURNS trigger AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.channel_name, '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3. Auto-update Trigger
DROP TRIGGER IF EXISTS youtube_courses_search_vector_trigger ON youtube_courses;
CREATE TRIGGER youtube_courses_search_vector_trigger
BEFORE INSERT OR UPDATE ON youtube_courses
FOR EACH ROW
EXECUTE FUNCTION youtube_courses_search_vector_update();

-- 4. GIN Index for Search Vector
CREATE INDEX IF NOT EXISTS idx_youtube_courses_search_vector ON youtube_courses USING GIN(search_vector);

-- ============================================================================
-- STEP 4: General Performance Composite Indexes
-- ============================================================================

-- UserCV listing
CREATE INDEX IF NOT EXISTS idx_user_cv_user_status ON user_cvs (user_id, status);

-- Analysis history
CREATE INDEX IF NOT EXISTS idx_user_analysis_user_created ON user_analysis (user_id, created_at DESC);

-- Course filtering
CREATE INDEX IF NOT EXISTS idx_courses_active_level ON courses (is_active, level) WHERE is_active = true;

-- Usage tracking
CREATE INDEX IF NOT EXISTS idx_llm_logs_user_created ON llm_logs (user_id, created_at DESC);

COMMIT;
