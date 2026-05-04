-- Migration: Add jd_parsing prompt template
-- Created: 2026-05-04
-- Purpose: Add missing jd_parsing prompt used in benchmark flows

INSERT INTO prompt_templates (key, name, category, prompt_text, parameters, model_config, is_active, admin_notes) VALUES
(
    'jd_parsing',
    'JD Parsing v1 - Standard',
    'jd_parsing',
    'You are an expert Job Description Analyzer. Extract structured requirements from the job posting.

## JOB DESCRIPTION:
{{jd_text}}

## CURRENT DATE:
{{current_date}}

## INSTRUCTIONS:

1. **EXTRACT REQUIREMENTS:**
   - Required skills (technical and soft skills)
   - Preferred skills (nice-to-have)
   - Experience level required (years)
   - Education requirements
   - Responsibilities and duties
   - Benefits and perks

2. **SKILL CATEGORIZATION:**
   - Technical skills: Programming languages, frameworks, tools
   - Soft skills: Communication, leadership, teamwork
   - Domain knowledge: Industry-specific expertise

3. **EXPERIENCE ANALYSIS:**
   - Calculate minimum years of experience required
   - Identify seniority level (Junior/Mid/Senior)
   - Note any specific experience requirements

4. **OUTPUT LANGUAGE:**
   - Keep skill names in original language from JD
   - Use Vietnamese for descriptions and notes

## OUTPUT JSON SCHEMA:
{
  "job_title": "string",
  "company": "string or null",
  "location": "string or null",
  "required_skills": [
    {
      "skill": "skill name",
      "category": "technical|soft|domain",
      "importance": "required|preferred"
    }
  ],
  "experience": {
    "min_years": 0,
    "max_years": 0,
    "level": "junior|mid|senior|lead"
  },
  "education": {
    "degree": "string or null",
    "field": "string or null"
  },
  "responsibilities": ["string"],
  "benefits": ["string"],
  "notes": "Vietnamese notes about special requirements"
}

IMPORTANT: Return ONLY valid JSON. Extract all skills mentioned in the JD.',
    '["jd_text", "current_date"]',
    '{"temperature": 0.5, "max_tokens": 2500}',
    true,
    'Standalone JD parsing for benchmark and analysis flows. Extracts structured requirements from raw job descriptions.'
)
ON CONFLICT (key) WHERE is_active = true DO UPDATE
SET 
    prompt_text = EXCLUDED.prompt_text,
    parameters = EXCLUDED.parameters,
    model_config = EXCLUDED.model_config,
    category = EXCLUDED.category,
    admin_notes = EXCLUDED.admin_notes,
    updated_at = CURRENT_TIMESTAMP;

COMMENT ON TABLE prompt_templates IS 'Updated: Added jd_parsing prompt for standalone JD analysis';
