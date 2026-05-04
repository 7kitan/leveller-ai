-- Migration 002: Create benchmark tables
-- Run this AFTER 000_create_prompt_schema.sql

-- =============================================================================
-- CREATE BENCHMARK TABLES
-- =============================================================================

-- Test Sets table
CREATE TABLE IF NOT EXISTS llm_test_sets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    flow_type VARCHAR(100) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_llm_test_sets_flow_type ON llm_test_sets(flow_type);
CREATE INDEX IF NOT EXISTS idx_llm_test_sets_is_active ON llm_test_sets(is_active);
CREATE INDEX IF NOT EXISTS idx_llm_test_sets_created_at ON llm_test_sets(created_at DESC);

COMMENT ON TABLE llm_test_sets IS 'Benchmark test sets for different flows';
COMMENT ON COLUMN llm_test_sets.flow_type IS 'Flow type: cv_parsing_v3, jd_parsing, gap_analysis, etc.';

-- Test Cases table
CREATE TABLE IF NOT EXISTS llm_test_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_set_id UUID NOT NULL REFERENCES llm_test_sets(id) ON DELETE CASCADE,
    input_data JSONB NOT NULL,
    reference_output JSONB,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_llm_test_cases_test_set_id ON llm_test_cases(test_set_id);
CREATE INDEX IF NOT EXISTS idx_llm_test_cases_created_at ON llm_test_cases(created_at DESC);

COMMENT ON TABLE llm_test_cases IS 'Individual test cases within test sets';
COMMENT ON COLUMN llm_test_cases.input_data IS 'Input parameters for the test (cv_id, job_id, etc.)';
COMMENT ON COLUMN llm_test_cases.reference_output IS 'Expected output (optional for reference-free evaluation)';
COMMENT ON COLUMN llm_test_cases.metadata IS 'Additional metadata (difficulty, tags, etc.)';

-- Benchmark Sessions table (renamed from runs)
CREATE TABLE IF NOT EXISTS llm_benchmark_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_set_id UUID NOT NULL REFERENCES llm_test_sets(id) ON DELETE CASCADE,
    model_config JSONB NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    overall_score FLOAT,
    total_latency_ms INTEGER,
    total_tokens INTEGER,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_llm_benchmark_sessions_test_set_id ON llm_benchmark_sessions(test_set_id);
CREATE INDEX IF NOT EXISTS idx_llm_benchmark_sessions_status ON llm_benchmark_sessions(status);
CREATE INDEX IF NOT EXISTS idx_llm_benchmark_sessions_created_at ON llm_benchmark_sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_llm_benchmark_sessions_overall_score ON llm_benchmark_sessions(overall_score);

COMMENT ON TABLE llm_benchmark_sessions IS 'Benchmark execution sessions';
COMMENT ON COLUMN llm_benchmark_sessions.model_config IS 'LLM configuration used (model, temperature, judge strategy, etc.)';
COMMENT ON COLUMN llm_benchmark_sessions.status IS 'Status: pending, running, completed, failed';

-- Benchmark Results table
CREATE TABLE IF NOT EXISTS llm_benchmark_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES llm_benchmark_sessions(id) ON DELETE CASCADE,
    test_case_id UUID NOT NULL REFERENCES llm_test_cases(id) ON DELETE CASCADE,
    actual_output JSONB,
    score FLOAT,
    metrics JSONB,
    latency_ms INTEGER,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_llm_benchmark_results_session_id ON llm_benchmark_results(session_id);
CREATE INDEX IF NOT EXISTS idx_llm_benchmark_results_test_case_id ON llm_benchmark_results(test_case_id);
CREATE INDEX IF NOT EXISTS idx_llm_benchmark_results_score ON llm_benchmark_results(score);
CREATE INDEX IF NOT EXISTS idx_llm_benchmark_results_status ON llm_benchmark_results(status);
CREATE INDEX IF NOT EXISTS idx_llm_benchmark_results_created_at ON llm_benchmark_results(created_at DESC);

COMMENT ON TABLE llm_benchmark_results IS 'Individual test case results';
COMMENT ON COLUMN llm_benchmark_results.metrics IS 'Detailed scores from judges (faithfulness, relevancy, completeness)';
COMMENT ON COLUMN llm_benchmark_results.score IS 'Aggregated score (0-1)';

-- Create updated_at triggers for all tables
DROP TRIGGER IF EXISTS update_llm_test_sets_updated_at ON llm_test_sets;
CREATE TRIGGER update_llm_test_sets_updated_at
    BEFORE UPDATE ON llm_test_sets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_llm_test_cases_updated_at ON llm_test_cases;
CREATE TRIGGER update_llm_test_cases_updated_at
    BEFORE UPDATE ON llm_test_cases
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_llm_benchmark_sessions_updated_at ON llm_benchmark_sessions;
CREATE TRIGGER update_llm_benchmark_sessions_updated_at
    BEFORE UPDATE ON llm_benchmark_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_llm_benchmark_results_updated_at ON llm_benchmark_results;
CREATE TRIGGER update_llm_benchmark_results_updated_at
    BEFORE UPDATE ON llm_benchmark_results
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Verify tables creation
SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_name IN ('llm_test_sets', 'llm_test_cases', 'llm_benchmark_sessions', 'llm_benchmark_results')
ORDER BY table_name;

SELECT 'Benchmark tables created successfully' AS status;
