-- Migration 000: Create prompt_templates table
-- Run this FIRST on fresh database

-- =============================================================================
-- CREATE PROMPT_TEMPLATES TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS prompt_templates (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) NOT NULL,  -- Auto-set to category value (for backward compatibility)
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,  -- Primary identifier for prompt type
    prompt_text TEXT NOT NULL,
    parameters JSONB NOT NULL DEFAULT '[]'::jsonb,
    model_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT false,
    admin_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_prompt_templates_key ON prompt_templates(key);
CREATE INDEX IF NOT EXISTS idx_prompt_templates_category ON prompt_templates(category);
CREATE INDEX IF NOT EXISTS idx_prompt_templates_is_active ON prompt_templates(is_active);
CREATE INDEX IF NOT EXISTS idx_prompt_templates_created_at ON prompt_templates(created_at DESC);

-- Create unique constraint: only one active prompt per category
CREATE UNIQUE INDEX IF NOT EXISTS unique_active_category_idx 
ON prompt_templates(category) WHERE is_active = true;

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_prompt_templates_updated_at ON prompt_templates;
CREATE TRIGGER update_prompt_templates_updated_at
    BEFORE UPDATE ON prompt_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add comments
COMMENT ON TABLE prompt_templates IS 'LLM prompt templates with versioning and activation control';
COMMENT ON COLUMN prompt_templates.key IS 'Auto-set to category value (for backward compatibility)';
COMMENT ON COLUMN prompt_templates.name IS 'Human-readable name for admin UI (e.g., "CV Parsing v2 - Detailed")';
COMMENT ON COLUMN prompt_templates.category IS 'Primary identifier for prompt type (e.g., cv_parsing, gap_analysis)';
COMMENT ON COLUMN prompt_templates.prompt_text IS 'Template text with {{parameter}} placeholders';
COMMENT ON COLUMN prompt_templates.parameters IS 'JSON array of parameter names';
COMMENT ON COLUMN prompt_templates.model_config IS 'LLM configuration (temperature, max_tokens, etc.)';
COMMENT ON COLUMN prompt_templates.is_active IS 'Only one prompt per category can be active';
COMMENT ON COLUMN prompt_templates.admin_notes IS 'Notes for admins (quality, test results, etc.)';

-- Verify table creation
SELECT 
    table_name, 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'prompt_templates' 
ORDER BY ordinal_position;

SELECT 'prompt_templates table created successfully' AS status;
