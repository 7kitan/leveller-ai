"""
Migration: Add Alternative Skill Groups Support

This migration adds simple support for alternative skill groups:
- "Proficient in Blender, Maya, or 3ds Max" → Group with any_one strategy
- "At least 2 of: Python, Java, C++, Go" → Group with at_least_n strategy

Changes:
1. Add 4 columns to job_skill_requirement table
2. No new tables needed - keeps it simple!

Run with: python -m scripts.migrate_add_alternative_skill_groups
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
        logger.info("=" * 80)
        logger.info("ALTERNATIVE SKILL GROUPS MIGRATION")
        logger.info("=" * 80)
        
        # Step 1: Add columns to job_skill_requirement
        logger.info("\nStep 1: Adding columns to job_skill_requirement table...")
        
        db.execute(text("""
            ALTER TABLE job_skill_requirement
            ADD COLUMN IF NOT EXISTS is_group BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS group_strategy VARCHAR(20),
            ADD COLUMN IF NOT EXISTS alternative_skills TEXT[],
            ADD COLUMN IF NOT EXISTS min_required INTEGER DEFAULT 1;
        """))
        
        logger.info("✓ Added columns: is_group, group_strategy, alternative_skills, min_required")
        
        # Step 2: Add index for performance
        logger.info("\nStep 2: Creating index...")
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_job_skill_requirement_is_group 
            ON job_skill_requirement(is_group) 
            WHERE is_group = TRUE;
        """))
        
        logger.info("✓ Created index on is_group")
        
        # Step 3: Add check constraint
        logger.info("\nStep 3: Adding check constraints...")
        
        db.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'check_group_strategy'
                ) THEN
                    ALTER TABLE job_skill_requirement
                    ADD CONSTRAINT check_group_strategy CHECK (
                        group_strategy IS NULL OR 
                        group_strategy IN ('any_one', 'at_least_n', 'all')
                    );
                END IF;
            END $$;
        """))
        
        logger.info("✓ Added check constraint for group_strategy")
        
        # Step 4: Verify structure
        logger.info("\nStep 4: Verifying table structure...")
        
        result = db.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'job_skill_requirement'
            AND column_name IN ('is_group', 'group_strategy', 'alternative_skills', 'min_required')
            ORDER BY column_name;
        """)).fetchall()
        
        logger.info("✓ Verified columns:")
        for col in result:
            logger.info(f"  - {col.column_name}: {col.data_type} (nullable: {col.is_nullable})")
        
        # Commit all changes
        db.commit()
        
        logger.info("\n" + "=" * 80)
        logger.info("✓ Migration completed successfully!")
        logger.info("=" * 80)
        logger.info("\nNew structure:")
        logger.info("  Individual skill: is_group=FALSE (default)")
        logger.info("  Skill group: is_group=TRUE + group_strategy + alternative_skills[]")
        logger.info("\nGroup strategies:")
        logger.info("  - 'any_one': User needs ANY ONE skill from alternatives")
        logger.info("  - 'at_least_n': User needs at least N skills (use min_required)")
        logger.info("  - 'all': User needs ALL skills (rare)")
        logger.info("\nExample:")
        logger.info("  skill_name: '3D Modeling Software'")
        logger.info("  is_group: TRUE")
        logger.info("  group_strategy: 'any_one'")
        logger.info("  alternative_skills: ['Blender', 'Maya', '3ds Max']")
        logger.info("  min_required: 1")
        
    except Exception as e:
        db.rollback()
        logger.error(f"✗ Migration failed: {e}", exc_info=True)
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
