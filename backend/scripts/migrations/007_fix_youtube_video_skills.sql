-- Migration 007: Fix missing skill_id in youtube_video_skills
-- This handles cases where the table was created by an older version of migration 006

DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='youtube_video_skills' AND column_name='skill_id') THEN
        ALTER TABLE youtube_video_skills ADD COLUMN skill_id UUID REFERENCES skills(id) ON DELETE SET NULL;
        CREATE INDEX IF NOT EXISTS idx_youtube_video_skills_skill_id ON youtube_video_skills(skill_id);
    END IF;
END $$;

COMMENT ON COLUMN youtube_video_skills.skill_id IS 'Link to standardized skills table';
