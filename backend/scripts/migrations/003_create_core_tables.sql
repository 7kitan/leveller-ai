-- Migration 003: Create core tables (users, user_cvs, jobs, skills)
-- Run this AFTER 000_create_prompt_schema.sql
-- Requires: pgvector extension for vector columns

-- =============================================================================
-- ENABLE EXTENSIONS
-- =============================================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";

-- =============================================================================
-- CREATE CORE TABLES
-- =============================================================================

-- System Settings table
CREATE TABLE IF NOT EXISTS system_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) NOT NULL UNIQUE,
    value TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_system_settings_key ON system_settings(key);

COMMENT ON TABLE system_settings IS 'Global system configuration settings';

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(100) UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    role VARCHAR(50) DEFAULT 'user',
    daily_token_limit INTEGER DEFAULT 0,
    daily_analysis_limit INTEGER DEFAULT 0,
    is_flagged BOOLEAN DEFAULT false,
    
    -- Security & Tracking
    registration_ip VARCHAR(50),
    registration_user_agent TEXT,
    last_login_ip VARCHAR(50),
    last_login_user_agent TEXT,
    
    -- Market Fit Cache
    market_fit_score FLOAT DEFAULT 0.0,
    market_fit_last_updated TIMESTAMP WITH TIME ZONE,
    market_fit_data JSONB,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at DESC);

COMMENT ON TABLE users IS 'User accounts with security tracking and market fit cache';
COMMENT ON COLUMN users.role IS 'User role: user, admin';
COMMENT ON COLUMN users.daily_token_limit IS '0 means use global default';
COMMENT ON COLUMN users.market_fit_data IS 'Cached market fit analysis (matched_jobs_count, percentile, etc.)';

-- Skills table (must be created before jobs for foreign keys)
CREATE TABLE IF NOT EXISTS skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL UNIQUE,
    category VARCHAR(100),
    parent_skill_id UUID REFERENCES skills(id) ON DELETE SET NULL,
    vector vector(1536)
);

CREATE INDEX IF NOT EXISTS idx_skills_name ON skills(name);
CREATE INDEX IF NOT EXISTS idx_skills_category ON skills(category);
CREATE INDEX IF NOT EXISTS idx_skills_parent_skill_id ON skills(parent_skill_id);
CREATE INDEX IF NOT EXISTS idx_skills_vector ON skills USING ivfflat (vector vector_cosine_ops) WITH (lists = 100);

COMMENT ON TABLE skills IS 'Technical skills with vector embeddings for semantic search';
COMMENT ON COLUMN skills.vector IS 'OpenAI text-embedding-3-small (1536 dimensions)';

-- Jobs table
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id VARCHAR(100) NOT NULL UNIQUE,
    title_raw VARCHAR(500) NOT NULL,
    title_category VARCHAR(100),
    domain_role VARCHAR(100),
    company_name VARCHAR(255),
    source_url TEXT,
    source_label VARCHAR(100),
    raw_text TEXT,
    
    -- Parsed sections
    job_description TEXT,
    requirements TEXT,
    benefits TEXT,
    
    -- Salary & Experience
    min_salary_vnd BIGINT,
    max_salary_vnd BIGINT,
    required_exp_years FLOAT,
    employment_type VARCHAR(50),
    
    -- Location
    location_raw VARCHAR(500),
    location_normalized VARCHAR(100),
    location_district VARCHAR(100),
    
    -- Benefits flags
    has_insurance BOOLEAN DEFAULT false,
    has_13th_month BOOLEAN DEFAULT false,
    remote_friendly BOOLEAN DEFAULT false,
    
    -- Status & Analysis
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    indexed_at TIMESTAMP WITH TIME ZONE,
    last_analyzed_at TIMESTAMP WITH TIME ZONE,
    extracted_requirements_json JSONB,
    
    -- Job Classification
    is_tech_job BOOLEAN DEFAULT true NOT NULL,
    job_classification_confidence FLOAT,
    job_primary_domain VARCHAR(100),
    job_classification_reason TEXT,
    classified_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_jobs_source_id ON jobs(source_id);
CREATE INDEX IF NOT EXISTS idx_jobs_title_category ON jobs(title_category);
CREATE INDEX IF NOT EXISTS idx_jobs_domain_role ON jobs(domain_role);
CREATE INDEX IF NOT EXISTS idx_jobs_company_name ON jobs(company_name);
CREATE INDEX IF NOT EXISTS idx_jobs_min_salary_vnd ON jobs(min_salary_vnd);
CREATE INDEX IF NOT EXISTS idx_jobs_max_salary_vnd ON jobs(max_salary_vnd);
CREATE INDEX IF NOT EXISTS idx_jobs_location_normalized ON jobs(location_normalized);
CREATE INDEX IF NOT EXISTS idx_jobs_location_district ON jobs(location_district);
CREATE INDEX IF NOT EXISTS idx_jobs_is_tech_job ON jobs(is_tech_job);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC);

COMMENT ON TABLE jobs IS 'Job postings with classification and parsed requirements';
COMMENT ON COLUMN jobs.is_tech_job IS 'Tech vs non-tech classification';
COMMENT ON COLUMN jobs.extracted_requirements_json IS 'LLM-extracted requirements';

-- User Analysis table (needed for users.last_analysis_id foreign key)
CREATE TABLE IF NOT EXISTS user_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    cv_id UUID,
    job_id UUID REFERENCES jobs(id) ON DELETE SET NULL,
    analysis_type VARCHAR(50) NOT NULL,
    gap_analysis_json JSONB,
    recommendations_json JSONB,
    overall_match_score FLOAT,
    status VARCHAR(20) DEFAULT 'completed',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_analysis_user_id ON user_analysis(user_id);
CREATE INDEX IF NOT EXISTS idx_user_analysis_cv_id ON user_analysis(cv_id);
CREATE INDEX IF NOT EXISTS idx_user_analysis_job_id ON user_analysis(job_id);
CREATE INDEX IF NOT EXISTS idx_user_analysis_analysis_type ON user_analysis(analysis_type);
CREATE INDEX IF NOT EXISTS idx_user_analysis_created_at ON user_analysis(created_at DESC);

COMMENT ON TABLE user_analysis IS 'Gap analysis results and recommendations';
COMMENT ON COLUMN user_analysis.analysis_type IS 'Type: gap_analysis, market_fit, etc.';

-- Add last_analysis_id foreign key to users (circular reference)
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_analysis_id UUID REFERENCES user_analysis(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_users_last_analysis_id ON users(last_analysis_id);

-- User CVs table
CREATE TABLE IF NOT EXISTS user_cvs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file_id VARCHAR(100) UNIQUE,
    full_name VARCHAR(255),
    summary VARCHAR(2000),
    raw_text TEXT,
    experience_years_total FLOAT DEFAULT 0,
    file_hash VARCHAR(64),
    
    -- Status
    status VARCHAR(20) DEFAULT 'processing',
    error_message TEXT,
    
    -- CV Parsed Data (v3)
    cv_parsed_json JSONB,
    cv_parsed_at TIMESTAMP WITH TIME ZONE,
    is_verified BOOLEAN DEFAULT false,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_user_cvs_user_id ON user_cvs(user_id);
CREATE INDEX IF NOT EXISTS idx_user_cvs_file_hash ON user_cvs(file_hash);
CREATE INDEX IF NOT EXISTS idx_user_cvs_created_at ON user_cvs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_cvs_deleted_at ON user_cvs(deleted_at);

COMMENT ON TABLE user_cvs IS 'User CV files with parsed data and soft delete support';
COMMENT ON COLUMN user_cvs.cv_parsed_json IS 'Structured CV data (skills, work_history, etc.)';
COMMENT ON COLUMN user_cvs.deleted_at IS 'Soft delete timestamp';

-- =============================================================================
-- CREATE UPDATED_AT TRIGGERS
-- =============================================================================

DROP TRIGGER IF EXISTS update_system_settings_updated_at ON system_settings;
CREATE TRIGGER update_system_settings_updated_at
    BEFORE UPDATE ON system_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_jobs_updated_at ON jobs;
CREATE TRIGGER update_jobs_updated_at
    BEFORE UPDATE ON jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_cvs_updated_at ON user_cvs;
CREATE TRIGGER update_user_cvs_updated_at
    BEFORE UPDATE ON user_cvs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_analysis_updated_at ON user_analysis;
CREATE TRIGGER update_user_analysis_updated_at
    BEFORE UPDATE ON user_analysis
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- VERIFY TABLES CREATION
-- =============================================================================

SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_name IN ('system_settings', 'users', 'skills', 'jobs', 'user_cvs', 'user_analysis')
ORDER BY table_name;

SELECT 'Core tables created successfully' AS status;
