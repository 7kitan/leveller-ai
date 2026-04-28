-- Setup Indexes for Career Advisor Database
-- Run this script on VPS to ensure all indexes are created
-- This script is idempotent (safe to run multiple times)

-- Enable pgvector extension if not already enabled
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================
-- JOBS TABLE INDEXES
-- ============================================

-- Primary key and unique constraints (auto-created by SQLAlchemy)
-- jobs_pkey, jobs_source_id_key

-- B-tree indexes for filtering
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs USING btree (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs USING btree (status) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_jobs_status_created ON jobs USING btree (status, created_at DESC) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS ix_jobs_company_name ON jobs USING btree (company_name);
CREATE INDEX IF NOT EXISTS ix_jobs_domain_role ON jobs USING btree (domain_role);
CREATE INDEX IF NOT EXISTS ix_jobs_location_district ON jobs USING btree (location_district);
CREATE INDEX IF NOT EXISTS ix_jobs_location_normalized ON jobs USING btree (location_normalized);
CREATE INDEX IF NOT EXISTS ix_jobs_min_salary_vnd ON jobs USING btree (min_salary_vnd);
CREATE INDEX IF NOT EXISTS ix_jobs_max_salary_vnd ON jobs USING btree (max_salary_vnd);
CREATE INDEX IF NOT EXISTS ix_jobs_title_category ON jobs USING btree (title_category);

-- CRITICAL: Vector index for similarity search
CREATE INDEX IF NOT EXISTS idx_jobs_vector_hnsw ON jobs 
USING hnsw (vector vector_cosine_ops) 
WITH (m = 16, ef_construction = 64) 
WHERE vector IS NOT NULL;

-- ============================================
-- COURSES TABLE INDEXES
-- ============================================

-- Vector index for similarity search
CREATE INDEX IF NOT EXISTS idx_courses_vector_hnsw ON courses 
USING hnsw (vector vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);

-- Full-text search indexes
CREATE INDEX IF NOT EXISTS idx_courses_title_trgm ON courses USING gin (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_courses_platform_trgm ON courses USING gin (platform gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_courses_provider_trgm ON courses USING gin (provider gin_trgm_ops);

-- JSONB indexes
CREATE INDEX IF NOT EXISTS idx_courses_skills_raw_gin ON courses USING gin (skills_raw);
CREATE INDEX IF NOT EXISTS idx_courses_tags_gin ON courses USING gin (tags);

-- B-tree indexes
CREATE INDEX IF NOT EXISTS idx_courses_is_active ON courses USING btree (is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_courses_active_created ON courses USING btree (is_active, created_at DESC) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_courses_level ON courses USING btree (level);
CREATE INDEX IF NOT EXISTS ix_courses_source_platform ON courses USING btree (source_platform);
CREATE INDEX IF NOT EXISTS ix_courses_source_id ON courses USING btree (source_id);
CREATE INDEX IF NOT EXISTS ix_courses_external_uuid ON courses USING btree (external_uuid);

-- ============================================
-- SKILLS TABLE INDEXES
-- ============================================

-- Vector index for similarity search
CREATE INDEX IF NOT EXISTS idx_skills_vector_hnsw ON skills 
USING hnsw (vector vector_cosine_ops) 
WITH (m = 16, ef_construction = 64) 
WHERE vector IS NOT NULL;

-- ============================================
-- JOB_SKILL_REQUIREMENT TABLE INDEXES
-- ============================================

CREATE INDEX IF NOT EXISTS idx_job_skill_req_job_id ON job_skill_requirement USING btree (job_id);
CREATE INDEX IF NOT EXISTS idx_job_skill_req_skill_id ON job_skill_requirement USING btree (skill_id);
CREATE INDEX IF NOT EXISTS idx_job_skill_req_level ON job_skill_requirement USING btree (required_level);
CREATE INDEX IF NOT EXISTS idx_job_skill_req_job_mandatory ON job_skill_requirement USING btree (job_id, is_mandatory);

-- ============================================
-- USER_SKILL_PROFILE TABLE INDEXES
-- ============================================

CREATE INDEX IF NOT EXISTS idx_user_skill_profile_user_id ON user_skill_profile USING btree (user_id);
CREATE INDEX IF NOT EXISTS idx_user_skill_profile_skill_id ON user_skill_profile USING btree (skill_id);
CREATE INDEX IF NOT EXISTS idx_user_skill_profile_cv_id ON user_skill_profile USING btree (cv_id);
CREATE INDEX IF NOT EXISTS idx_user_skill_profile_level ON user_skill_profile USING btree (level);
CREATE INDEX IF NOT EXISTS idx_user_skill_profile_user_skill ON user_skill_profile USING btree (user_id, skill_id);

-- ============================================
-- USER_CVS TABLE INDEXES
-- ============================================

CREATE INDEX IF NOT EXISTS idx_user_cvs_user_id ON user_cvs USING btree (user_id);
CREATE INDEX IF NOT EXISTS idx_user_cvs_created_at ON user_cvs USING btree (created_at DESC);
CREATE INDEX IF NOT EXISTS ix_user_cvs_file_hash ON user_cvs USING btree (file_hash);

-- ============================================
-- USER_ANALYSIS TABLE INDEXES
-- ============================================

CREATE INDEX IF NOT EXISTS ix_user_analysis_user_id ON user_analysis USING btree (user_id);
CREATE INDEX IF NOT EXISTS ix_user_analysis_cv_id ON user_analysis USING btree (cv_id);

-- ============================================
-- USER_WORK_EXPERIENCES TABLE INDEXES
-- ============================================

CREATE INDEX IF NOT EXISTS idx_user_work_exp_cv_id ON user_work_experiences USING btree (cv_id);

-- ============================================
-- MARKET_SKILL_STATS TABLE INDEXES
-- ============================================

CREATE INDEX IF NOT EXISTS ix_market_skill_stats_category ON market_skill_stats USING btree (category);

-- ============================================
-- MARKET_SKILL_HISTORY TABLE INDEXES
-- ============================================

CREATE INDEX IF NOT EXISTS ix_market_skill_history_skill_name ON market_skill_history USING btree (skill_name);
CREATE INDEX IF NOT EXISTS ix_market_skill_history_snapshot_date ON market_skill_history USING btree (snapshot_date);

-- ============================================
-- LLM_LOGS TABLE INDEXES
-- ============================================

CREATE INDEX IF NOT EXISTS ix_llm_logs_created_at ON llm_logs USING btree (created_at);

-- ============================================
-- SYSTEM_LOGS TABLE INDEXES
-- ============================================

CREATE INDEX IF NOT EXISTS ix_system_logs_created_at ON system_logs USING btree (created_at);
CREATE INDEX IF NOT EXISTS ix_system_logs_level ON system_logs USING btree (level);
CREATE INDEX IF NOT EXISTS ix_system_logs_module ON system_logs USING btree (module);

-- ============================================
-- USER_FEEDBACK TABLE INDEXES
-- ============================================

CREATE INDEX IF NOT EXISTS ix_user_feedback_user_id ON user_feedback USING btree (user_id);

-- ============================================
-- YOUTUBE_COURSES TABLE INDEXES
-- ============================================

CREATE INDEX IF NOT EXISTS ix_youtube_courses_last_verified_at ON youtube_courses USING btree (last_verified_at);
CREATE INDEX IF NOT EXISTS ix_youtube_courses_expires_at ON youtube_courses USING btree (expires_at);

-- ============================================
-- VERIFY INDEXES
-- ============================================

-- Show all vector indexes
SELECT 
    schemaname, 
    tablename, 
    indexname, 
    indexdef 
FROM pg_indexes 
WHERE schemaname = 'public' 
    AND indexname LIKE '%vector%' 
ORDER BY tablename;

-- Show index count by table
SELECT 
    tablename, 
    COUNT(*) as index_count 
FROM pg_indexes 
WHERE schemaname = 'public' 
GROUP BY tablename 
ORDER BY index_count DESC;
