-- Migration: Setup all prompt templates for deployment
-- Created: 2026-05-04
-- Purpose: Initialize all 5 prompt templates with correct configuration

-- =============================================================================
-- 1. CV PARSING PROMPT
-- =============================================================================
INSERT INTO prompt_templates (key, name, category, prompt_text, parameters, model_config, is_active, admin_notes) VALUES
(
    'cv_parsing',
    'CV Parsing',
    'cv_parsing',
    'You are a Senior CV Parser. Extract structured information from the candidate''s CV.

## MASKED CV TEXT:
{{masked_text}}

## CURRENT DATE:
{{current_date}}

## INSTRUCTIONS:

1. **PERSONAL INFORMATION:**
   - Extract name, email, phone (if not masked)
   - Calculate age from date of birth if available
   - Extract location/address

2. **EDUCATION:**
   - Extract all degrees with institution, field, graduation year
   - Calculate years since graduation using current_date
   - Identify highest degree level

3. **WORK EXPERIENCE:**
   - Extract all positions with company, title, duration
   - Calculate total years of experience using current_date
   - Identify current position and seniority level

4. **SKILLS:**
   - Extract technical skills (programming languages, frameworks, tools)
   - Extract soft skills (communication, leadership, etc.)
   - Categorize skills by proficiency if mentioned

5. **CERTIFICATIONS & ACHIEVEMENTS:**
   - Extract certifications with issuing organization and date
   - Extract notable achievements and awards

6. **OUTPUT LANGUAGE:**
   - Keep names, titles, and technical terms in original language
   - Use Vietnamese for descriptions and notes

## OUTPUT JSON SCHEMA:
{
  "personal_info": {
    "name": "string",
    "email": "string or null",
    "phone": "string or null",
    "location": "string or null",
    "age": 0
  },
  "education": [
    {
      "degree": "string",
      "field": "string",
      "institution": "string",
      "graduation_year": 0,
      "years_since_graduation": 0
    }
  ],
  "experience": [
    {
      "title": "string",
      "company": "string",
      "start_date": "string",
      "end_date": "string or null",
      "duration_years": 0,
      "responsibilities": ["string"]
    }
  ],
  "skills": {
    "technical": ["string"],
    "soft": ["string"],
    "languages": ["string"]
  },
  "certifications": [
    {
      "name": "string",
      "issuer": "string",
      "date": "string or null"
    }
  ],
  "total_experience_years": 0,
  "seniority_level": "junior|mid|senior|lead"
}

IMPORTANT: Return ONLY valid JSON. Use current_date to calculate years and durations.',
    '["masked_text", "current_date"]',
    '{"temperature": 0.5, "max_tokens": 2500}',
    true,
    'CV parsing with PII masking. Extracts structured candidate information.'
)
ON CONFLICT (category) WHERE is_active = true DO UPDATE
SET 
    key = EXCLUDED.category,  -- Keep key in sync with category
    name = EXCLUDED.name,
    prompt_text = EXCLUDED.prompt_text,
    parameters = EXCLUDED.parameters,
    model_config = EXCLUDED.model_config,
    admin_notes = EXCLUDED.admin_notes,
    updated_at = CURRENT_TIMESTAMP;

-- =============================================================================
-- 2. JD PARSING PROMPT (NO current_date - not needed)
-- =============================================================================
INSERT INTO prompt_templates (key, name, category, prompt_text, parameters, model_config, is_active, admin_notes) VALUES
(
    'jd_parsing',
    'JD Parsing',
    'jd_parsing',
    'You are an expert Job Description Analyzer. Extract structured requirements from the job posting.

## JOB DESCRIPTION:
{{jd_text}}

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
    '["jd_text"]',
    '{"temperature": 0.5, "max_tokens": 2500}',
    true,
    'Standalone JD parsing for benchmark and analysis flows. Extracts structured requirements from raw job descriptions.'
)
ON CONFLICT (category) WHERE is_active = true DO UPDATE
SET 
    key = EXCLUDED.category,  -- Keep key in sync with category
    name = EXCLUDED.name,
    prompt_text = EXCLUDED.prompt_text,
    parameters = EXCLUDED.parameters,
    model_config = EXCLUDED.model_config,
    admin_notes = EXCLUDED.admin_notes,
    updated_at = CURRENT_TIMESTAMP;

-- =============================================================================
-- 3. GAP ANALYSIS PROMPT (Pre-parsed inputs)
-- =============================================================================
INSERT INTO prompt_templates (key, name, category, prompt_text, parameters, model_config, is_active, admin_notes) VALUES
(
    'gap_analysis',
    'Gap Analysis',
    'gap_analysis',
    'You are a Senior Career Advisor. Analyze skill gaps between candidate CV and job requirements.

## JOB TITLE:
{{job_title}}

## JOB REQUIREMENTS (Pre-parsed JSON):
{{requirements_json}}

## CANDIDATE CV (Pre-parsed JSON):
{{cv_json_str}}

## INSTRUCTIONS:

1. **SKILL GAP ANALYSIS:**
   - Compare candidate skills vs required skills
   - Identify missing required skills (critical gaps)
   - Identify missing preferred skills (nice-to-have gaps)
   - Identify matching skills with proficiency assessment

2. **EXPERIENCE GAP:**
   - Compare candidate experience vs required experience
   - Calculate experience gap in years
   - Assess seniority level match

3. **EDUCATION GAP:**
   - Compare candidate education vs required education
   - Identify any education gaps

4. **RECOMMENDATIONS:**
   - Prioritize gaps by importance (critical > important > nice-to-have)
   - Suggest learning resources for each gap
   - Estimate time needed to close each gap

5. **OUTPUT LANGUAGE:**
   - Keep skill names in original language
   - Use Vietnamese for analysis and recommendations

## OUTPUT JSON SCHEMA:
{
  "skill_gaps": [
    {
      "skill": "string",
      "gap_type": "missing|weak|strong",
      "importance": "critical|important|nice-to-have",
      "current_level": "none|beginner|intermediate|advanced",
      "required_level": "beginner|intermediate|advanced|expert",
      "learning_time_weeks": 0,
      "recommendation": "Vietnamese recommendation"
    }
  ],
  "experience_gap": {
    "required_years": 0,
    "candidate_years": 0,
    "gap_years": 0,
    "assessment": "Vietnamese assessment"
  },
  "education_gap": {
    "required": "string or null",
    "candidate": "string or null",
    "gap_exists": false,
    "assessment": "Vietnamese assessment"
  },
  "overall_match_score": 0,
  "summary": "Vietnamese summary of gaps and recommendations"
}

IMPORTANT: Return ONLY valid JSON. Be specific and actionable in recommendations.',
    '["job_title", "requirements_json", "cv_json_str"]',
    '{"temperature": 0.6, "max_tokens": 3000}',
    true,
    'Gap analysis when both CV and JD are already parsed. Compares pre-parsed JSON data.'
)
ON CONFLICT (category) WHERE is_active = true DO UPDATE
SET 
    key = EXCLUDED.category,  -- Keep key in sync with category
    name = EXCLUDED.name,
    prompt_text = EXCLUDED.prompt_text,
    parameters = EXCLUDED.parameters,
    model_config = EXCLUDED.model_config,
    admin_notes = EXCLUDED.admin_notes,
    updated_at = CURRENT_TIMESTAMP;

-- =============================================================================
-- 4. GAP ANALYSIS MERGED PROMPT (JD Extract + Analysis in one call)
-- =============================================================================
INSERT INTO prompt_templates (key, name, category, prompt_text, parameters, model_config, is_active, admin_notes) VALUES
(
    'gap_analysis_merged',
    'Gap Analysis Merged (JD Extract + Analysis)',
    'gap_analysis_merged',
    'You are a Senior Career Advisor. Extract job requirements from JD and analyze skill gaps with candidate CV.

## RAW JOB DESCRIPTION:
{{jd_text}}

## CANDIDATE CV (Pre-parsed JSON):
{{cv_text}}

## INSTRUCTIONS:

**STEP 1: EXTRACT JD REQUIREMENTS**
- Extract required and preferred skills from raw JD text
- Extract experience requirements
- Extract education requirements

**STEP 2: SKILL GAP ANALYSIS**
- Compare candidate skills vs extracted requirements
- Identify missing required skills (critical gaps)
- Identify missing preferred skills (nice-to-have gaps)
- Identify matching skills with proficiency assessment

**STEP 3: EXPERIENCE & EDUCATION GAP**
- Compare candidate experience vs required experience
- Compare candidate education vs required education

**STEP 4: RECOMMENDATIONS**
- Prioritize gaps by importance
- Suggest learning resources for each gap
- Estimate time needed to close each gap

**OUTPUT LANGUAGE:**
- Keep skill names in original language
- Use Vietnamese for analysis and recommendations

## OUTPUT JSON SCHEMA:
{
  "extracted_requirements": {
    "job_title": "string",
    "required_skills": ["string"],
    "preferred_skills": ["string"],
    "experience_years": 0,
    "education": "string or null"
  },
  "skill_gaps": [
    {
      "skill": "string",
      "gap_type": "missing|weak|strong",
      "importance": "critical|important|nice-to-have",
      "current_level": "none|beginner|intermediate|advanced",
      "required_level": "beginner|intermediate|advanced|expert",
      "learning_time_weeks": 0,
      "recommendation": "Vietnamese recommendation"
    }
  ],
  "experience_gap": {
    "required_years": 0,
    "candidate_years": 0,
    "gap_years": 0,
    "assessment": "Vietnamese assessment"
  },
  "education_gap": {
    "required": "string or null",
    "candidate": "string or null",
    "gap_exists": false,
    "assessment": "Vietnamese assessment"
  },
  "overall_match_score": 0,
  "summary": "Vietnamese summary of gaps and recommendations"
}

IMPORTANT: Return ONLY valid JSON. Extract requirements first, then analyze gaps.',
    '["jd_text", "cv_text"]',
    '{"temperature": 0.6, "max_tokens": 3500}',
    true,
    'Gap analysis when JD is raw text. Extracts JD requirements and performs gap analysis in one call.'
)
ON CONFLICT (category) WHERE is_active = true DO UPDATE
SET 
    key = EXCLUDED.category,  -- Keep key in sync with category
    name = EXCLUDED.name,
    prompt_text = EXCLUDED.prompt_text,
    parameters = EXCLUDED.parameters,
    model_config = EXCLUDED.model_config,
    admin_notes = EXCLUDED.admin_notes,
    updated_at = CURRENT_TIMESTAMP;

-- =============================================================================
-- 5. COURSE RECOMMENDATION PROMPT
-- =============================================================================
INSERT INTO prompt_templates (key, name, category, prompt_text, parameters, model_config, is_active, admin_notes) VALUES
(
    'course_recommendation',
    'Course Recommendation',
    'course_recommendation',
    'You are a Senior Learning Path Advisor. Your mission is to select the best learning resources (paid courses + free YouTube videos) and build a personalized career roadmap for the candidate.

## SKILL GAPS TO ADDRESS:
{{gaps_context}}

## PAID COURSE CANDIDATES:
{{candidates_context}}

## FREE YOUTUBE VIDEO CANDIDATES:
{{yt_context}}

## INSTRUCTIONS:

1. **COURSE SELECTION RULES:**
   - RELEVANCE FIRST: Only select courses/videos that directly teach the gap skills
   - NO HALLUCINATIONS: Only select from the provided candidates (do not invent course IDs)
   - PREFER PAID COURSES: For critical gaps, prioritize comprehensive paid courses
   - USE YOUTUBE: For supplementary learning or quick introductions
   - AVOID DUPLICATES: Don''t select multiple courses teaching the same skill

2. **ROADMAP CONSTRUCTION:**
   - LOGICAL PROGRESSION: Start with foundational skills, then advanced
   - REALISTIC TIMELINE: 2-4 weeks per major skill, 1-2 weeks for minor skills
   - CLEAR MILESTONES: Define specific achievements for each week
   - STAGE GROUPING: Group related skills into learning stages

3. **SELECTION REASONING:**
   - Explain WHY each course/video was selected
   - Link each resource to specific gap_skills it addresses
   - Be specific about what the learner will gain

4. **OUTPUT LANGUAGE:**
   - selection_reason: Vietnamese
   - career_roadmap.summary: Vietnamese
   - milestones: Vietnamese
   - Keep course titles and skill names in original language

## OUTPUT JSON SCHEMA:
{
  "selected_courses": [
    {
      "course_id": "uuid or null",
      "video_id": "youtube_id or null",
      "gap_skills": ["skill1", "skill2"],
      "selection_reason": "Vietnamese explanation",
      "stage": 1
    }
  ],
  "career_roadmap": {
    "stages": [
      {
        "stage": 1,
        "focus": "Stage focus area",
        "duration_weeks": 4,
        "skills_acquired": ["skill1", "skill2"],
        "courses_taken": ["Course Title 1"],
        "milestones": [
          {"week": 1, "milestone": "Vietnamese milestone description"},
          {"week": 2, "milestone": "Vietnamese milestone description"}
        ]
      }
    ],
    "total_weeks": 12,
    "total_hours": 120,
    "summary": "Vietnamese summary of the learning path"
  }
}

IMPORTANT: Return ONLY valid JSON. Do not select courses/videos not in the candidates list.',
    '["gaps_context", "candidates_context", "yt_context"]',
    '{"temperature": 0.6, "max_tokens": 3000}',
    true,
    'Course recommendation with paid courses + YouTube videos. Builds personalized learning roadmap.'
)
ON CONFLICT (category) WHERE is_active = true DO UPDATE
SET 
    key = EXCLUDED.category,  -- Keep key in sync with category
    name = EXCLUDED.name,
    prompt_text = EXCLUDED.prompt_text,
    parameters = EXCLUDED.parameters,
    model_config = EXCLUDED.model_config,
    admin_notes = EXCLUDED.admin_notes,
    updated_at = CURRENT_TIMESTAMP;

-- =============================================================================
-- CLEANUP: Remove old/unused prompts
-- =============================================================================
DELETE FROM prompt_templates WHERE key = 'job_recommendation';

-- =============================================================================
-- VERIFICATION
-- =============================================================================
SELECT 
    key, 
    name, 
    category, 
    jsonb_array_length(parameters) as param_count,
    is_active
FROM prompt_templates 
WHERE is_active = true 
ORDER BY category;

COMMENT ON TABLE prompt_templates IS 'Updated: All 5 prompts configured for production deployment';
