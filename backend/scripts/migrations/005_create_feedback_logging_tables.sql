-- Migration 005: Create feedback and logging tables
-- Run this AFTER 003_create_core_tables.sql
-- Requires: users, user_analysis tables

-- =============================================================================
-- CREATE FEEDBACK & LOGGING TABLES
-- =============================================================================

-- User Feedback table
CREATE TABLE IF NOT EXISTS user_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    analysis_id VARCHAR(100) NOT NULL,
    rating INTEGER,
    is_accurate BOOLEAN,
    missing_skills JSONB,
    comment VARCHAR(1000),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_feedback_user_id ON user_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_analysis_id ON user_feedback(analysis_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_created_at ON user_feedback(created_at DESC);

COMMENT ON TABLE user_feedback IS 'User feedback on analysis results';
COMMENT ON COLUMN user_feedback.rating IS 'User rating (1-5)';
COMMENT ON COLUMN user_feedback.is_accurate IS 'Whether analysis was accurate';
COMMENT ON COLUMN user_feedback.missing_skills IS 'Skills that were missed in analysis';

-- LLM Logs table
CREATE TABLE IF NOT EXISTS llm_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    model_id VARCHAR(100) NOT NULL,
    provider VARCHAR(50),
    call_type VARCHAR(50),
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    latency_ms INTEGER,
    status VARCHAR(20),
    error_message TEXT,
    request_metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_llm_logs_user_id ON llm_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_llm_logs_model_id ON llm_logs(model_id);
CREATE INDEX IF NOT EXISTS idx_llm_logs_call_type ON llm_logs(call_type);
CREATE INDEX IF NOT EXISTS idx_llm_logs_status ON llm_logs(status);
CREATE INDEX IF NOT EXISTS idx_llm_logs_created_at ON llm_logs(created_at DESC);

COMMENT ON TABLE llm_logs IS 'LLM usage logs for monitoring and debugging';
COMMENT ON COLUMN llm_logs.call_type IS 'Call type: cv_parsing, gap_analysis, general, etc.';
COMMENT ON COLUMN llm_logs.status IS 'Status: success, failed';
COMMENT ON COLUMN llm_logs.request_metadata IS 'Additional info like call_id, cv_id, job_id, etc.';

-- System Logs table
CREATE TABLE IF NOT EXISTS system_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    level VARCHAR(20),
    module VARCHAR(100),
    message TEXT,
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level);
CREATE INDEX IF NOT EXISTS idx_system_logs_module ON system_logs(module);
CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs(created_at DESC);

COMMENT ON TABLE system_logs IS 'System-level logs for debugging and monitoring';
COMMENT ON COLUMN system_logs.level IS 'Log level: INFO, WARNING, ERROR, CRITICAL';
COMMENT ON COLUMN system_logs.module IS 'Module: Email, AI, DB, Worker, Crawler';
COMMENT ON COLUMN system_logs.details IS 'Stacktrace, metadata, etc.';

-- =============================================================================
-- VERIFY TABLES CREATION
-- =============================================================================

SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_name IN ('user_feedback', 'llm_logs', 'system_logs')
ORDER BY table_name;

SELECT 'Feedback and logging tables created successfully' AS status;
