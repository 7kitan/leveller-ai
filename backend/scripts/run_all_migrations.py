#!/usr/bin/env python3
"""
Database Migration Runner
Runs all migration scripts in the correct order for production deployment.

Usage:
    python scripts/run_all_migrations.py

Environment:
    Requires database connection via environment variables (POSTGRES_*)
"""

import os
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Migration scripts in order (CRITICAL: Order matters!)
MIGRATIONS = [
    "migrate_add_security_and_budget_fields.py",
    "migrate_add_quota_fields.py",
    "migrate_add_system_settings.py",
    "migrate_add_is_verified.py",
    "migrate_add_last_analysis_id.py",
    "migrate_add_cv_parsed_fields.py",
    "migrate_v3_v4.py",
    "migrate_rich_course_data.py",
    "migrate_hnsw_jobs.py",
    "migrate_add_performance_indexes.py",
]

def run_migration(script_name):
    """Run a single migration script."""
    script_path = os.path.join("scripts", script_name)
    
    if not os.path.exists(script_path):
        logger.error(f"❌ Migration script not found: {script_path}")
        return False
    
    logger.info(f"🔄 Running migration: {script_name}")
    
    try:
        # Run the migration script
        exit_code = os.system(f"python {script_path}")
        
        if exit_code == 0:
            logger.info(f"✅ Migration completed: {script_name}")
            return True
        else:
            logger.error(f"❌ Migration failed: {script_name} (exit code: {exit_code})")
            return False
            
    except Exception as e:
        logger.error(f"❌ Migration error: {script_name} - {str(e)}")
        return False

def verify_database_connection():
    """Verify database connection before running migrations."""
    try:
        from shared.database import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        logger.info("✅ Database connection verified")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        logger.error("Please ensure database is running and environment variables are set")
        return False

def main():
    """Run all migrations in order."""
    logger.info("=" * 70)
    logger.info("🚀 Starting Database Migrations")
    logger.info("=" * 70)
    logger.info(f"Total migrations to run: {len(MIGRATIONS)}")
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")
    
    # Verify database connection first
    if not verify_database_connection():
        logger.error("❌ Cannot proceed without database connection")
        sys.exit(1)
    
    # Run migrations
    success_count = 0
    failed_count = 0
    
    for i, migration in enumerate(MIGRATIONS, 1):
        logger.info(f"\n[{i}/{len(MIGRATIONS)}] Processing: {migration}")
        logger.info("-" * 70)
        
        if run_migration(migration):
            success_count += 1
        else:
            failed_count += 1
            logger.error(f"\n❌ Migration failed: {migration}")
            logger.error("Stopping migration process to prevent data corruption")
            logger.error(f"Completed: {success_count}/{len(MIGRATIONS)}")
            logger.error(f"Failed at: {migration}")
            sys.exit(1)
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("🎉 All Migrations Completed Successfully!")
    logger.info("=" * 70)
    logger.info(f"Total: {len(MIGRATIONS)}")
    logger.info(f"Success: {success_count}")
    logger.info(f"Failed: {failed_count}")
    logger.info(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")
    logger.info("✅ Database is ready for production!")
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.error("\n❌ Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)
