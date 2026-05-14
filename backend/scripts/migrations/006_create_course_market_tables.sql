-- Migration 006: Create course and market tables
-- Run this AFTER 003_create_core_tables.sql
-- Requires: users, skills tables

-- =============================================================================
-- CREATE COURSE TABLES
-- =============================================================================

-- Courses table (Coursera, Udemy, etc.)
CREATE TABLE IF NOT EXISTS courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    
    -- Source Info
    source_platform VARCHAR(100),
    source_id VARCHAR(255),
    external_uuid VARCHAR(100),
    provider VARCHAR(100),
    platform VARCHAR(100),
    url TEXT,
    
    -- Metadata
    languages JSONB,
    language VARCHAR(10),
    level VARCHAR(50),
    is_certification BOOLEAN DEFAULT false,
    duration_hours FLOAT,
    duration_raw VARCHAR(100),
    cost_usd FLOAT DEFAULT 0,
    
    -- Rich Content
    skills_raw JSONB,
    tools_raw JSONB,
    outcomes JSONB,
    modules JSONB,
    tags TEXT[],
    
    -- Vector Search
    embedding_context TEXT,
    vector vector(1536),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    
    CONSTRAINT uq_course_source UNIQUE (source_platform, source_id)
);

CREATE INDEX IF NOT EXISTS idx_courses_source_platform ON courses(source_platform);
CREATE INDEX IF NOT EXISTS idx_courses_source_id ON courses(source_id);
CREATE INDEX IF NOT EXISTS idx_courses_external_uuid ON courses(external_uuid);
CREATE INDEX IF NOT EXISTS idx_courses_level ON courses(level);
CREATE INDEX IF NOT EXISTS idx_courses_is_active ON courses(is_active);
CREATE INDEX IF NOT EXISTS idx_courses_created_at ON courses(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_courses_vector ON courses USING ivfflat (vector vector_cosine_ops) WITH (lists = 100);

COMMENT ON TABLE courses IS 'Online courses from Coursera, Udemy, etc. with vector search';
COMMENT ON COLUMN courses.embedding_context IS 'Text used for vector embedding generation';
COMMENT ON COLUMN courses.tags IS 'Standardized tags for filtering';

-- YouTube Courses table
CREATE TABLE IF NOT EXISTS youtube_courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id VARCHAR(50) NOT NULL UNIQUE,
    title TEXT NOT NULL,
    description TEXT,
    thumbnail VARCHAR(255),
    channel_name VARCHAR(255),
    url TEXT,
    
    -- Vector Search
    embedding_context TEXT,
    vector vector(1536),
    
    -- Metadata
    duration_raw VARCHAR(50),
    published_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    last_verified_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Curation fields
    language VARCHAR(10),
    skill_level VARCHAR(50),
    is_curated BOOLEAN DEFAULT false,
    quality_score FLOAT,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_youtube_courses_video_id ON youtube_courses(video_id);
CREATE INDEX IF NOT EXISTS idx_youtube_courses_expires_at ON youtube_courses(expires_at);
CREATE INDEX IF NOT EXISTS idx_youtube_courses_last_verified_at ON youtube_courses(last_verified_at);
CREATE INDEX IF NOT EXISTS idx_youtube_courses_language ON youtube_courses(language);
CREATE INDEX IF NOT EXISTS idx_youtube_courses_skill_level ON youtube_courses(skill_level);
CREATE INDEX IF NOT EXISTS idx_youtube_courses_is_curated ON youtube_courses(is_curated);
CREATE INDEX IF NOT EXISTS idx_youtube_courses_vector ON youtube_courses USING ivfflat (vector vector_cosine_ops) WITH (lists = 100);

COMMENT ON TABLE youtube_courses IS 'YouTube video courses with curation and quality scoring';
COMMENT ON COLUMN youtube_courses.expires_at IS 'Cache expiration timestamp';
COMMENT ON COLUMN youtube_courses.is_curated IS 'Manually added by admin';
COMMENT ON COLUMN youtube_courses.quality_score IS 'Quality metric (0-100)';

-- YouTube Video Skills junction table
CREATE TABLE IF NOT EXISTS youtube_video_skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id VARCHAR(50) NOT NULL REFERENCES youtube_courses(video_id) ON DELETE CASCADE,
    skill_id UUID REFERENCES skills(id) ON DELETE SET NULL,
    skill_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_youtube_video_skill UNIQUE (video_id, skill_name)
);

CREATE INDEX IF NOT EXISTS idx_youtube_video_skills_video_id ON youtube_video_skills(video_id);
CREATE INDEX IF NOT EXISTS idx_youtube_video_skills_skill_id ON youtube_video_skills(skill_id);
CREATE INDEX IF NOT EXISTS idx_youtube_video_skills_skill_name ON youtube_video_skills(skill_name);

COMMENT ON TABLE youtube_video_skills IS 'Skills taught in YouTube videos (many-to-many)';

-- =============================================================================
-- CREATE MARKET TABLES
-- =============================================================================

-- Market Skill Stats table
CREATE TABLE IF NOT EXISTS market_skill_stats (
    skill_name VARCHAR(200) PRIMARY KEY,
    category VARCHAR(100),
    
    -- Salary data
    avg_salary_min BIGINT,
    avg_salary_max BIGINT,
    salary_premium_pct FLOAT,
    
    -- Demand data
    job_count_30d INTEGER DEFAULT 0,
    growth_rate_30d FLOAT DEFAULT 0.0,
    demand_score FLOAT,
    
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_market_skill_stats_category ON market_skill_stats(category);
CREATE INDEX IF NOT EXISTS idx_market_skill_stats_demand_score ON market_skill_stats(demand_score DESC);
CREATE INDEX IF NOT EXISTS idx_market_skill_stats_job_count_30d ON market_skill_stats(job_count_30d DESC);
CREATE INDEX IF NOT EXISTS idx_market_skill_stats_updated_at ON market_skill_stats(updated_at DESC);

COMMENT ON TABLE market_skill_stats IS 'Current market statistics for skills (salary, demand, growth)';
COMMENT ON COLUMN market_skill_stats.salary_premium_pct IS 'Salary premium vs category average';
COMMENT ON COLUMN market_skill_stats.growth_rate_30d IS 'Growth rate vs 30 days ago';
COMMENT ON COLUMN market_skill_stats.demand_score IS 'Demand score (0-100) based on job_count and growth';

-- Market Skill History table
CREATE TABLE IF NOT EXISTS market_skill_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_name VARCHAR(200) NOT NULL,
    job_count INTEGER DEFAULT 0,
    avg_salary BIGINT DEFAULT 0,
    demand_score FLOAT DEFAULT 0.0,
    snapshot_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_market_skill_history_skill_name ON market_skill_history(skill_name);
CREATE INDEX IF NOT EXISTS idx_market_skill_history_snapshot_date ON market_skill_history(snapshot_date DESC);
CREATE INDEX IF NOT EXISTS idx_market_skill_history_skill_date ON market_skill_history(skill_name, snapshot_date DESC);

COMMENT ON TABLE market_skill_history IS 'Historical snapshots of market skill statistics (daily)';
COMMENT ON COLUMN market_skill_history.snapshot_date IS 'Daily snapshot timestamp';

-- =============================================================================
-- CREATE UPDATED_AT TRIGGERS
-- =============================================================================

DROP TRIGGER IF EXISTS update_courses_updated_at ON courses;
CREATE TRIGGER update_courses_updated_at
    BEFORE UPDATE ON courses
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_market_skill_stats_updated_at ON market_skill_stats;
CREATE TRIGGER update_market_skill_stats_updated_at
    BEFORE UPDATE ON market_skill_stats
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- VERIFY TABLES CREATION
-- =============================================================================

SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_name IN ('courses', 'youtube_courses', 'youtube_video_skills', 'market_skill_stats', 'market_skill_history')
ORDER BY table_name;

SELECT 'Course and market tables created successfully' AS status;
