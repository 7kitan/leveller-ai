-- Migration 004: Create relationship tables
-- Run this AFTER 003_create_core_tables.sql
-- Requires: users, jobs, skills, user_cvs tables

-- =============================================================================
-- CREATE RELATIONSHIP TABLES
-- =============================================================================

-- Job Skill Requirements table
CREATE TABLE IF NOT EXISTS job_skill_requirement (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    importance_weight INTEGER,
    required_level VARCHAR(20),
    min_years_exp FLOAT,
    is_mandatory BOOLEAN DEFAULT true,
    
    -- Alternative skill groups support
    is_group BOOLEAN DEFAULT false,
    group_strategy VARCHAR(20),
    alternative_skills TEXT[],
    min_required INTEGER DEFAULT 1,
    
    -- Vector search
    embedding_context TEXT,
    vector vector(1536)
);

CREATE INDEX IF NOT EXISTS idx_job_skill_requirement_job_id ON job_skill_requirement(job_id);
CREATE INDEX IF NOT EXISTS idx_job_skill_requirement_skill_id ON job_skill_requirement(skill_id);
CREATE INDEX IF NOT EXISTS idx_job_skill_requirement_is_mandatory ON job_skill_requirement(is_mandatory);
CREATE INDEX IF NOT EXISTS idx_job_skill_requirement_vector ON job_skill_requirement USING ivfflat (vector vector_cosine_ops) WITH (lists = 100);

COMMENT ON TABLE job_skill_requirement IS 'Skills required by jobs with importance weights and alternative skill groups';
COMMENT ON COLUMN job_skill_requirement.group_strategy IS 'Strategy: any_one, at_least_n, all';
COMMENT ON COLUMN job_skill_requirement.alternative_skills IS 'Array of alternative skill names for flexible matching';

-- User Skill Profile table
CREATE TABLE IF NOT EXISTS user_skill_profile (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    cv_id UUID NOT NULL REFERENCES user_cvs(id) ON DELETE CASCADE,
    years_exp FLOAT DEFAULT 0,
    level VARCHAR(20),
    last_used_year INTEGER,
    skill_context TEXT,
    vector vector(1536),
    confidence_score FLOAT DEFAULT 1.0,
    source VARCHAR(50) DEFAULT 'cv',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_skill_profile_user_id ON user_skill_profile(user_id);
CREATE INDEX IF NOT EXISTS idx_user_skill_profile_skill_id ON user_skill_profile(skill_id);
CREATE INDEX IF NOT EXISTS idx_user_skill_profile_cv_id ON user_skill_profile(cv_id);
CREATE INDEX IF NOT EXISTS idx_user_skill_profile_created_at ON user_skill_profile(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_skill_profile_vector ON user_skill_profile USING ivfflat (vector vector_cosine_ops) WITH (lists = 100);

COMMENT ON TABLE user_skill_profile IS 'User skills extracted from CVs with experience levels and confidence scores';
COMMENT ON COLUMN user_skill_profile.source IS 'Source: cv, manual, linkedin, etc.';
COMMENT ON COLUMN user_skill_profile.confidence_score IS 'Confidence in skill extraction (0-1)';

-- User Work Experiences table
CREATE TABLE IF NOT EXISTS user_work_experiences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cv_id UUID NOT NULL REFERENCES user_cvs(id) ON DELETE CASCADE,
    position_name VARCHAR(255) NOT NULL,
    company_name VARCHAR(255),
    duration_years FLOAT DEFAULT 0,
    description VARCHAR(2000),
    skills_context JSONB,
    is_primary BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_work_experiences_cv_id ON user_work_experiences(cv_id);
CREATE INDEX IF NOT EXISTS idx_user_work_experiences_is_primary ON user_work_experiences(is_primary);
CREATE INDEX IF NOT EXISTS idx_user_work_experiences_created_at ON user_work_experiences(created_at DESC);

COMMENT ON TABLE user_work_experiences IS 'User work history extracted from CVs';
COMMENT ON COLUMN user_work_experiences.skills_context IS 'Skills related to this position (JSON array)';
COMMENT ON COLUMN user_work_experiences.is_primary IS 'Primary/most relevant work experience';

-- =============================================================================
-- CREATE UPDATED_AT TRIGGERS
-- =============================================================================
-- Note: user_work_experiences does not have updated_at column in the model

-- =============================================================================
-- VERIFY TABLES CREATION
-- =============================================================================

SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_name IN ('job_skill_requirement', 'user_skill_profile', 'user_work_experiences')
ORDER BY table_name;

SELECT 'Relationship tables created successfully' AS status;
