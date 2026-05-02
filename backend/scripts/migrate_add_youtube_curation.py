"""
Migration: Add YouTube Video Curation Support

This migration adds:
1. New columns to youtube_courses table (language, skill_level, is_curated, quality_score, created_by)
2. youtube_video_skills junction table for many-to-many skill relationships
3. Indexes for filtering and performance

Run with: python -m scripts.migrate_add_youtube_curation
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import text
from shared.database import SessionLocal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    db = SessionLocal()
    
    try:
        logger.info("Starting YouTube curation migration...")
        
        # Step 1: Add new columns to youtube_courses
        logger.info("Step 1: Adding new columns to youtube_courses table...")
        
        db.execute(text("""
            ALTER TABLE youtube_courses
            ADD COLUMN IF NOT EXISTS language VARCHAR(10) DEFAULT NULL,
            ADD COLUMN IF NOT EXISTS skill_level VARCHAR(50) DEFAULT NULL,
            ADD COLUMN IF NOT EXISTS is_curated BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS quality_score FLOAT DEFAULT NULL,
            ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES users(id) ON DELETE SET NULL;
        """))
        
        logger.info("✓ Added columns: language, skill_level, is_curated, quality_score, created_by")
        
        # Step 2: Add check constraints
        logger.info("Step 2: Adding check constraints...")
        
        db.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'check_language'
                ) THEN
                    ALTER TABLE youtube_courses
                    ADD CONSTRAINT check_language CHECK (language IN ('en', 'vi') OR language IS NULL);
                END IF;
            END $$;
        """))
        
        db.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'check_skill_level'
                ) THEN
                    ALTER TABLE youtube_courses
                    ADD CONSTRAINT check_skill_level CHECK (
                        skill_level IN ('Junior', 'Mid-level', 'Senior', 'Expert') OR skill_level IS NULL
                    );
                END IF;
            END $$;
        """))
        
        db.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'check_quality_score'
                ) THEN
                    ALTER TABLE youtube_courses
                    ADD CONSTRAINT check_quality_score CHECK (
                        (quality_score >= 0 AND quality_score <= 100) OR quality_score IS NULL
                    );
                END IF;
            END $$;
        """))
        
        logger.info("✓ Added check constraints")
        
        # Step 3: Add indexes for filtering
        logger.info("Step 3: Adding indexes...")
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_youtube_courses_language 
            ON youtube_courses(language);
        """))
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_youtube_courses_skill_level 
            ON youtube_courses(skill_level);
        """))
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_youtube_courses_is_curated 
            ON youtube_courses(is_curated);
        """))
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_youtube_courses_quality_score 
            ON youtube_courses(quality_score DESC NULLS LAST);
        """))
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_youtube_courses_filters 
            ON youtube_courses(language, skill_level, is_curated);
        """))
        
        logger.info("✓ Added indexes for filtering")
        
        # Step 4: Create youtube_video_skills junction table
        logger.info("Step 4: Creating youtube_video_skills junction table...")
        
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS youtube_video_skills (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                video_id VARCHAR(50) NOT NULL REFERENCES youtube_courses(video_id) ON DELETE CASCADE,
                skill_name VARCHAR(100) NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                
                UNIQUE(video_id, skill_name)
            );
        """))
        
        logger.info("✓ Created youtube_video_skills table")
        
        # Step 5: Add indexes for youtube_video_skills
        logger.info("Step 5: Adding indexes for youtube_video_skills...")
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_youtube_video_skills_video_id 
            ON youtube_video_skills(video_id);
        """))
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_youtube_video_skills_skill_name 
            ON youtube_video_skills(skill_name);
        """))
        
        logger.info("✓ Added indexes for youtube_video_skills")
        
        # Commit all changes
        db.commit()
        
        logger.info("=" * 60)
        logger.info("✓ Migration completed successfully!")
        logger.info("=" * 60)
        logger.info("\nNext steps:")
        logger.info("1. Update shared/models.py to add new fields to YouTubeCourse model")
        logger.info("2. Restart backend services to load new schema")
        logger.info("3. Use admin UI to start curating videos")
        
    except Exception as e:
        db.rollback()
        logger.error(f"✗ Migration failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
