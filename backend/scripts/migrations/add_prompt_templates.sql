-- Migration: Add prompt_templates table for LLM prompt management
-- Created: 2026-05-03
-- Description: Allow admins to manage and test multiple LLM prompts per function

CREATE TABLE IF NOT EXISTS prompt_templates (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) NOT NULL,              -- Function key: 'cv_parsing', 'gap_analysis', etc.
    name VARCHAR(255) NOT NULL,             -- Display name: 'CV Parsing v1', 'CV Parsing v2 - Detailed'
    category VARCHAR(50) NOT NULL,          -- Category for grouping: 'cv_parsing', 'gap_analysis', 'recommendation'
    prompt_text TEXT NOT NULL,              -- Template with {{parameter}} placeholders
    parameters JSONB NOT NULL DEFAULT '[]', -- Array of parameter names: ["cv_text", "current_date"]
    model_config JSONB NOT NULL DEFAULT '{"temperature": 0.7, "max_tokens": 2000}',
    is_active BOOLEAN DEFAULT false,        -- Only one active prompt per key
    admin_notes TEXT,                       -- Quality evaluation notes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast lookups by key and active status
CREATE INDEX IF NOT EXISTS idx_prompt_key_active ON prompt_templates(key, is_active);
CREATE INDEX IF NOT EXISTS idx_prompt_category ON prompt_templates(category);

-- Partial unique constraint: Only one active prompt per key
CREATE UNIQUE INDEX IF NOT EXISTS unique_active_per_key 
ON prompt_templates(key) 
WHERE is_active = true;

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_prompt_template_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_prompt_template_timestamp
BEFORE UPDATE ON prompt_templates
FOR EACH ROW
EXECUTE FUNCTION update_prompt_template_timestamp();

-- Insert default prompts
INSERT INTO prompt_templates (key, name, category, prompt_text, parameters, model_config, is_active, admin_notes) VALUES
(
    'cv_parsing',
    'CV Parsing v1 - Standard',
    'cv_parsing',
    'Bạn là chuyên gia phân tích CV. Hôm nay là {{current_date}}.

Phân tích CV sau và trích xuất thông tin theo định dạng JSON:

{{cv_text}}

Trả về JSON với các trường:
- personal_info: {name, email, phone, location}
- education: [{degree, institution, year, gpa}]
- experience: [{title, company, duration, responsibilities}]
- skills: [{skill_name, proficiency}]
- certifications: [{name, issuer, year}]

Chỉ trả về JSON hợp lệ, không thêm text khác.',
    '["cv_text", "current_date"]',
    '{"temperature": 0.3, "max_tokens": 2000}',
    true,
    'Baseline prompt - accuracy ~85%'
),
(
    'gap_analysis',
    'Gap Analysis v1 - Standard',
    'gap_analysis',
    'Bạn là chuyên gia tư vấn nghề nghiệp. Phân tích khoảng cách giữa hồ sơ ứng viên và yêu cầu công việc.

Hồ sơ ứng viên:
{{candidate_profile}}

Yêu cầu công việc:
{{job_requirements}}

Phân tích chi tiết:
1. Kỹ năng phù hợp và điểm mạnh
2. Kỹ năng còn thiếu và khoảng cách kiến thức
3. Khoảng cách kinh nghiệm
4. Lộ trình học tập đề xuất
5. Điểm phù hợp tổng thể (0-100)

Trả về JSON có cấu trúc rõ ràng.',
    '["candidate_profile", "job_requirements"]',
    '{"temperature": 0.5, "max_tokens": 3000}',
    true,
    'Standard gap analysis prompt'
),
(
    'job_recommendation',
    'Job Recommendation v1 - Standard',
    'recommendation',
    'Bạn là hệ thống gợi ý việc làm thông minh. Dựa trên hồ sơ ứng viên, đề xuất các công việc phù hợp.

Hồ sơ ứng viên:
{{candidate_profile}}

Danh sách công việc khả dụng:
{{available_jobs}}

Xem xét:
- Độ phù hợp kỹ năng
- Cấp độ kinh nghiệm
- Phát triển sự nghiệp
- Phù hợp ngành nghề

Trả về top {{top_k}} công việc với điểm phù hợp và lý do.',
    '["candidate_profile", "available_jobs", "top_k"]',
    '{"temperature": 0.6, "max_tokens": 2500}',
    true,
    'Standard recommendation prompt'
);

COMMENT ON TABLE prompt_templates IS 'LLM prompt templates with parameter support and version management';
COMMENT ON COLUMN prompt_templates.key IS 'Function identifier - multiple prompts can share same key';
COMMENT ON COLUMN prompt_templates.is_active IS 'Only one prompt per key can be active at a time';
COMMENT ON COLUMN prompt_templates.parameters IS 'JSON array of parameter names used in template';
COMMENT ON COLUMN prompt_templates.admin_notes IS 'Quality evaluation and testing notes';
