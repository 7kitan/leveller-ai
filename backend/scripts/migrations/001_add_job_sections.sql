-- Migration: Add structured job sections to jobs table
-- Date: 2026-04-24
-- Description: Add job_description, requirements, and benefits columns to store parsed sections from TopCV crawler
-- This allows LLM to access specific sections without parsing raw_text, saving tokens

-- Add job_description column (Mô tả công việc)
ALTER TABLE jobs 
ADD COLUMN IF NOT EXISTS job_description TEXT;

-- Add requirements column (Yêu cầu ứng viên)
ALTER TABLE jobs 
ADD COLUMN IF NOT EXISTS requirements TEXT;

-- Add benefits column (Quyền lợi)
ALTER TABLE jobs 
ADD COLUMN IF NOT EXISTS benefits TEXT;

-- Create indexes for better search performance (optional, uncomment if needed)
-- CREATE INDEX IF NOT EXISTS idx_jobs_job_description ON jobs USING gin(to_tsvector('english', job_description));
-- CREATE INDEX IF NOT EXISTS idx_jobs_requirements ON jobs USING gin(to_tsvector('english', requirements));

-- Verify columns were added
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'jobs' 
  AND column_name IN ('job_description', 'requirements', 'benefits')
ORDER BY column_name;
