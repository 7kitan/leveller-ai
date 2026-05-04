-- Migration 002: Create benchmark tables
-- Run this AFTER 001_setup_prompts.sql

-- =============================================================================
-- CREATE BENCHMARK TABLES
-- =============================================================================

-- Test Sets table
CREATE TABLE IF NOT EXISTS lm_test_sets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    flow_type VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_lm_test_sets_flow_type ON lm_test_sets(flow_type);
CREATE INDEX IF NOT EXISTS idx_lm_test_sets_created_at ON lm_test_sets(created_at DESC);

COMMENT ON TABLE lm_test_sets IS 'Benchmark test sets for different flows';
COMMENT ON COLUMN lm_test_sets.flow_type IS 'Flow type: cv_parsing, jd_parsing, gap_analysis, etc.';

-- Test Cases table
CREATE TABLE IF NOT EXISTS lm_test_cases (
    id SERIAL PRIMARY KEY,
    test_set_id INTEGER NOT NULL REFERENCES lm_test_sets(id) ON DELETE CASCADE,
    input_data JSONB NOT NULL,
    reference_output JSONB,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_lm_test_cases_test_set_id ON lm_test_cases(test_set_id);
CREATE INDEX IF NOT EXISTS idx_lm_test_cases_created_at ON lm_test_cases(created_at DESC);

COMMENT ON TABLE lm_test_cases IS 'Individual test cases within test sets';
COMMENT ON COLUMN lm_test_cases.input_data IS 'Input parameters for the prompt';
COMMENT ON COLUMN lm_test_cases.reference_output IS 'Expected output (optional for reference-free evaluation)';
COMMENT ON COLUMN lm_test_cases.metadata IS 'Additional metadata (cv_id, job_id, etc.)';

-- Benchmark Runs table
CREATE TABLE IF NOT EXISTS lm_benchmark_runs (
    id SERIAL PRIMARY KEY,
    test_set_id INTEGER NOT NULL REFERENCES lm_test_sets(id) ON DELETE CASCADE,
    prompt_key VARCHAR(100) NOT NULL,
    prompt_version INTEGER,
    strategy VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    total_cases INTEGER NOT NULL DEFAULT 0,
    completed_cases INTEGER NOT NULL DEFAULT 0,
    failed_cases INTEGER NOT NULL DEFAULT 0,
    avg_score FLOAT,
    avg_latency_ms FLOAT,
    total_cost_usd FLOAT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_lm_benchmark_runs_test_set_id ON lm_benchmark_runs(test_set_id);
CREATE INDEX IF NOT EXISTS idx_lm_benchmark_runs_prompt_key ON lm_benchmark_runs(prompt_key);
CREATE INDEX IF NOT EXISTS idx_lm_benchmark_runs_status ON lm_benchmark_runs(status);
CREATE INDEX IF NOT EXISTS idx_lm_benchmark_runs_created_at ON lm_benchmark_runs(created_at DESC);

COMMENT ON TABLE lm_benchmark_runs IS 'Benchmark execution runs';
COMMENT ON COLUMN lm_benchmark_runs.strategy IS 'Evaluation strategy: single_judge, dual_judge, ensemble';
COMMENT ON COLUMN lm_benchmark_runs.status IS 'Status: pending, running, completed, failed';

-- Benchmark Results table
CREATE TABLE IF NOT EXISTS lm_benchmark_results (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES lm_benchmark_runs(id) ON DELETE CASCADE,
    test_case_id INTEGER NOT NULL REFERENCES lm_test_cases(id) ON DELETE CASCADE,
    model_output JSONB,
    evaluation_scores JSONB,
    overall_score FLOAT,
    latency_ms INTEGER,
    cost_usd FLOAT,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_lm_benchmark_results_run_id ON lm_benchmark_results(run_id);
CREATE INDEX IF NOT EXISTS idx_lm_benchmark_results_test_case_id ON lm_benchmark_results(test_case_id);
CREATE INDEX IF NOT EXISTS idx_lm_benchmark_results_overall_score ON lm_benchmark_results(overall_score);
CREATE INDEX IF NOT EXISTS idx_lm_benchmark_results_created_at ON lm_benchmark_results(created_at DESC);

COMMENT ON TABLE lm_benchmark_results IS 'Individual test case results';
COMMENT ON COLUMN lm_benchmark_results.evaluation_scores IS 'Detailed scores from judges';
COMMENT ON COLUMN lm_benchmark_results.overall_score IS 'Aggregated score (0-1)';

-- Create updated_at triggers for all tables
DROP TRIGGER IF EXISTS update_lm_test_sets_updated_at ON lm_test_sets;
CREATE TRIGGER update_lm_test_sets_updated_at
    BEFORE UPDATE ON lm_test_sets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_lm_test_cases_updated_at ON lm_test_cases;
CREATE TRIGGER update_lm_test_cases_updated_at
    BEFORE UPDATE ON lm_test_cases
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_lm_benchmark_runs_updated_at ON lm_benchmark_runs;
CREATE TRIGGER update_lm_benchmark_runs_updated_at
    BEFORE UPDATE ON lm_benchmark_runs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Verify tables creation
SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_name IN ('lm_test_sets', 'lm_test_cases', 'lm_benchmark_runs', 'lm_benchmark_results')
ORDER BY table_name;

SELECT 'Benchmark tables created successfully' AS status;
