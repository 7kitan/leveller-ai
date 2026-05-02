#!/usr/bin/env python3
"""
Complete Production Database Setup Script

This script orchestrates the full database setup for production:
1. Enable PostgreSQL extensions (pgvector, pg_trgm)
2. Create all tables and constraints
3. Run all migrations (indexes, soft delete, vector cleanup)
4. Create admin user
5. Verify setup

Safe to run multiple times (idempotent).
"""

import sys
import os
import logging

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, text
from shared.config_utils import config_manager
from shared.database import Base, engine
from scripts.create_admin import create_admin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("production_setup")



def create_schema():
    """Step 1: Create all tables and constraints."""
    logger.info("=" * 70)
    logger.info("STEP 1: Creating Database Schema")
    logger.info("=" * 70)
    
    try:
        # Import all models to ensure they're registered with Base
        from shared.models import (
            User, UserCV, UserSkillProfile, UserWorkExperience, UserAnalysis,
            Job, Skill, JobSkillRequirement,
            Course, SystemSetting, LLMLog, SystemLog, UserFeedback,
            MarketSkillStats, MarketSkillHistory,
            YouTubeCourse, YouTubeVideoSkill
        )
        
        # Create all tables
        Base.metadata.create_all(engine)
        logger.info("  ✓ All tables created")
        logger.info("  ✓ Foreign keys configured")
        logger.info("  ✓ Unique constraints applied")
        logger.info("✅ Schema created successfully\n")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create schema: {e}\n")
        return False


def apply_tuning():
    """Step 2: Apply database performance tuning (Indexes, Triggers)."""
    logger.info("=" * 70)
    logger.info("STEP 2: Applying Database Tuning")
    logger.info("=" * 70)
    
    try:
        tuning_path = os.path.join(os.path.dirname(__file__), "production_tuning.sql")
        
        if not os.path.exists(tuning_path):
            logger.error(f"❌ Tuning file not found: {tuning_path}")
            return False
            
        with engine.connect() as conn:
            logger.info("  📝 Executing production_tuning.sql...")
            with open(tuning_path, 'r', encoding='utf-8') as f:
                sql = f.read()
            
            # Execute the entire script
            conn.execute(text(sql))
            conn.commit()
            
            logger.info("  ✅ Database tuning applied successfully")
            return True
            
    except Exception as e:
        logger.error(f"❌ Tuning failed: {e}\n")
        return False


def init_settings():
    """Step 2.5: Initialize system settings."""
    logger.info("=" * 70)
    logger.info("STEP 2.5: Initializing System Settings")
    logger.info("=" * 70)
    
    try:
        from scripts.init_system_settings import init_settings as run_init
        run_init(force=False)
        logger.info("✅ System settings initialized\n")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize settings: {e}\n")
        return False


def create_admin_user():
    """Step 3: Create system admin user."""
    logger.info("=" * 70)
    logger.info("STEP 3: Creating Admin User")
    logger.info("=" * 70)
    
    try:
        admin_email = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@lumix.ai")
        admin_pass = os.getenv("DEFAULT_ADMIN_PASSWORD", "Admin@123")
        admin_name = os.getenv("DEFAULT_ADMIN_NAME", "System Admin")
        
        create_admin(admin_email, admin_pass, admin_name)
        logger.info(f"  ✓ Admin user: {admin_email}")
        logger.info("✅ Admin user ready\n")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create admin: {e}\n")
        return False


def verify_setup():
    """Step 4: Verify production setup."""
    logger.info("=" * 70)
    logger.info("STEP 4: Verifying Setup")
    logger.info("=" * 70)
    
    try:
        with engine.connect() as conn:
            # Check extensions
            result = conn.execute(text("""
                SELECT extname FROM pg_extension 
                WHERE extname IN ('vector', 'pg_trgm')
                ORDER BY extname
            """))
            extensions = [row[0] for row in result]
            logger.info(f"  ✓ Extensions: {', '.join(extensions)}")
            
            # Check tables
            result = conn.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            table_count = result.scalar()
            logger.info(f"  ✓ Tables: {table_count} created")
            
            # Check if tuning was applied (check for search_vector)
            result = conn.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'youtube_courses' AND column_name = 'search_vector'
            """))
            if result.scalar():
                logger.info("  ✓ Database tuning: search_vector present")
            else:
                logger.warning("  ⚠️  Database tuning: search_vector MISSING")
            
            # Check jobs table (no vector columns)
            result = conn.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'jobs' AND column_name IN ('vector', 'embedding_context')
            """))
            vector_cols = [row[0] for row in result]
            if vector_cols:
                logger.warning(f"  ⚠️  Jobs table still has vector columns: {vector_cols}")
            else:
                logger.info("  ✓ Jobs table: vector columns removed")
            
            # Check user_cvs soft delete
            result = conn.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'user_cvs' AND column_name = 'deleted_at'
            """))
            has_soft_delete = result.scalar() is not None
            if has_soft_delete:
                logger.info("  ✓ User CVs: soft delete enabled")
            else:
                logger.warning("  ⚠️  User CVs: soft delete NOT enabled")
            
            # Check admin user
            result = conn.execute(text("""
                SELECT COUNT(*) FROM users WHERE role = 'admin'
            """))
            admin_count = result.scalar()
            logger.info(f"  ✓ Admin users: {admin_count}")
            
            logger.info("\n✅ Verification completed\n")
            return True
            
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}\n")
        return False


def main():
    """Main production setup orchestration."""
    logger.info("\n" + "=" * 70)
    logger.info("🚀 PRODUCTION DATABASE SETUP")
    logger.info("=" * 70)
    logger.info("This script will set up the complete database for production.")
    logger.info("Safe to run multiple times (idempotent).\n")
    
    steps = [
        ("Create Schema", create_schema),
        ("Apply Tuning", apply_tuning),
        ("Init System Settings", init_settings),
        ("Create Admin User", create_admin_user),
        ("Verify Setup", verify_setup),
    ]
    
    for step_name, step_func in steps:
        success = step_func()
        if not success:
            logger.error(f"\n❌ SETUP FAILED at step: {step_name}")
            logger.error("Please fix the error and run again.\n")
            sys.exit(1)
    
    logger.info("=" * 70)
    logger.info("🎉 PRODUCTION SETUP COMPLETED SUCCESSFULLY")
    logger.info("=" * 70)
    logger.info("\nYour database is ready for production!")
    logger.info("\nNext steps:")
    logger.info("  1. Start services: docker compose -f docker-compose.prod.yml up -d")
    logger.info("  2. Check logs: docker compose -f docker-compose.prod.yml logs -f")
    logger.info("  3. Access API: http://localhost:8000/docs\n")


if __name__ == "__main__":
    main()
