-- Database migration: Add job classification fields
-- Run this migration to add classification fields to jobs table

-- Add classification columns to jobs table
ALTER TABLE jobs 
ADD COLUMN IF NOT EXISTS is_tech_job BOOLEAN DEFAULT TRUE NOT NULL,
ADD COLUMN IF NOT EXISTS job_classification_confidence FLOAT,
ADD COLUMN IF NOT EXISTS job_primary_domain VARCHAR(100),
ADD COLUMN IF NOT EXISTS job_classification_reason TEXT,
ADD COLUMN IF NOT EXISTS classified_at TIMESTAMP WITH TIME ZONE;

-- Add index for filtering by tech/non-tech
CREATE INDEX IF NOT EXISTS idx_jobs_is_tech ON jobs(is_tech_job);

-- Add index for classification confidence (for quality monitoring)
CREATE INDEX IF NOT EXISTS idx_jobs_classification_confidence ON jobs(job_classification_confidence) WHERE job_classification_confidence IS NOT NULL;

-- Add comment to document the fields
COMMENT ON COLUMN jobs.is_tech_job IS 'Whether this job is in tech domain (true) or non-tech (false)';
COMMENT ON COLUMN jobs.job_classification_confidence IS 'Confidence score (0.0-1.0) of the classification';
COMMENT ON COLUMN jobs.job_primary_domain IS 'Primary domain of the job (e.g., Software Engineering, Sales, Marketing)';
COMMENT ON COLUMN jobs.job_classification_reason IS 'Explanation of why the job was classified as tech or non-tech';
COMMENT ON COLUMN jobs.classified_at IS 'Timestamp when the job was classified';

-- Show statistics
SELECT 
    is_tech_job,
    COUNT(*) as job_count,
    AVG(job_classification_confidence) as avg_confidence
FROM jobs
GROUP BY is_tech_job;
