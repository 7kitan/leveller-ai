"""
Migration: Add Skill Management System
- Create pending_skills table for review workflow
- Add skill_id to youtube_video_skills (keep skill_name for transition)
- Add indexes and constraints
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
        logger.info("=" * 60)
        logger.info("Starting Skill Management System Migration...")
        logger.info("=" * 60)
        
        # Step 1: Create pending_skills table
        logger.info("\nStep 1: Creating pending_skills table...")
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS pending_skills (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                skill_name VARCHAR(200) NOT NULL UNIQUE,
                source VARCHAR(50) NOT NULL,  -- 'youtube', 'job_posting', 'manual', 'gap_analysis'
                suggested_by UUID REFERENCES users(id) ON DELETE SET NULL,
                suggested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'approved', 'rejected', 'merged'
                reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
                reviewed_at TIMESTAMP WITH TIME ZONE,
                merged_into UUID REFERENCES skills(id) ON DELETE SET NULL,
                notes TEXT,
                metadata JSONB,  -- Store additional context (e.g., video_id, job_id)
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """))
        logger.info("✓ Created pending_skills table")
        
        # Step 2: Add indexes for pending_skills
        logger.info("\nStep 2: Adding indexes for pending_skills...")
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_pending_skills_status 
            ON pending_skills(status);
        """))
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_pending_skills_source 
            ON pending_skills(source);
        """))
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_pending_skills_suggested_at 
            ON pending_skills(suggested_at DESC);
        """))
        logger.info("✓ Added indexes for pending_skills")
        
        # Step 3: Add check constraint for status
        logger.info("\nStep 3: Adding check constraints...")
        db.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'check_pending_skill_status'
                ) THEN
                    ALTER TABLE pending_skills
                    ADD CONSTRAINT check_pending_skill_status 
                    CHECK (status IN ('pending', 'approved', 'rejected', 'merged'));
                END IF;
            END $$;
        """))
        logger.info("✓ Added check constraints")
        
        # Step 4: Add skill_id to youtube_video_skills (keep skill_name for transition)
        logger.info("\nStep 4: Adding skill_id to youtube_video_skills...")
        db.execute(text("""
            ALTER TABLE youtube_video_skills
            ADD COLUMN IF NOT EXISTS skill_id UUID REFERENCES skills(id) ON DELETE CASCADE;
        """))
        logger.info("✓ Added skill_id column")
        
        # Step 5: Populate skill_id from skill_name where possible
        logger.info("\nStep 5: Populating skill_id from existing skill_name...")
        result = db.execute(text("""
            UPDATE youtube_video_skills yvs
            SET skill_id = s.id
            FROM skills s
            WHERE yvs.skill_name = s.name
              AND yvs.skill_id IS NULL;
        """))
        logger.info(f"✓ Updated {result.rowcount} rows with skill_id")
        
        # Step 6: Find skills that don't exist in master table
        logger.info("\nStep 6: Finding orphaned skills...")
        orphaned = db.execute(text("""
            SELECT DISTINCT yvs.skill_name
            FROM youtube_video_skills yvs
            LEFT JOIN skills s ON yvs.skill_name = s.name
            WHERE s.id IS NULL AND yvs.skill_id IS NULL;
        """)).fetchall()
        
        if orphaned:
            logger.info(f"⚠️  Found {len(orphaned)} skills not in master table:")
            for row in orphaned:
                logger.info(f"   - {row[0]}")
                # Add to pending_skills for review
                db.execute(text("""
                    INSERT INTO pending_skills (skill_name, source, status, notes)
                    VALUES (:name, 'youtube', 'pending', 'Auto-detected from existing YouTube videos')
                    ON CONFLICT (skill_name) DO NOTHING;
                """), {"name": row[0]})
            logger.info(f"✓ Added {len(orphaned)} skills to pending_skills for review")
        else:
            logger.info("✓ No orphaned skills found")
        
        # Step 7: Add index for skill_id
        logger.info("\nStep 7: Adding index for skill_id...")
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_youtube_video_skills_skill_id 
            ON youtube_video_skills(skill_id);
        """))
        logger.info("✓ Added index for skill_id")
        
        # Step 8: Create function to auto-update updated_at
        logger.info("\nStep 8: Creating trigger for updated_at...")
        db.execute(text("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """))
        
        db.execute(text("""
            DROP TRIGGER IF EXISTS update_pending_skills_updated_at ON pending_skills;
            CREATE TRIGGER update_pending_skills_updated_at
            BEFORE UPDATE ON pending_skills
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """))
        logger.info("✓ Created trigger for updated_at")
        
        # Commit all changes
        db.commit()
        
        # Step 9: Verify migration
        logger.info("\nStep 9: Verifying migration...")
        
        # Check pending_skills table
        result = db.execute(text("SELECT COUNT(*) FROM pending_skills;")).fetchone()
        logger.info(f"✓ pending_skills table: {result[0]} rows")
        
        # Check youtube_video_skills with skill_id
        result = db.execute(text("""
            SELECT 
                COUNT(*) as total,
                COUNT(skill_id) as with_skill_id,
                COUNT(*) - COUNT(skill_id) as without_skill_id
            FROM youtube_video_skills;
        """)).fetchone()
        logger.info(f"✓ youtube_video_skills: {result[0]} total, {result[1]} with skill_id, {result[2]} without")
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ Migration completed successfully!")
        logger.info("=" * 60)
        logger.info("\nNext steps:")
        logger.info("1. Implement admin taxonomy page (/admin/taxonomy)")
        logger.info("2. Implement pending skills review page (/admin/taxonomy/pending)")
        logger.info("3. Update YouTube video modal with tag input")
        logger.info("4. Add API endpoints for skill management")
        
    except Exception as e:
        db.rollback()
        logger.error(f"\n✗ Migration failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
