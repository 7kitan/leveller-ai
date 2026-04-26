#!/usr/bin/env python3
"""
Database Migration Runner

Automatically runs all pending migrations on startup.
Safe to run multiple times (idempotent).
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, text
from shared.config_utils import config_manager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migrations")

def run_migrations():
    """Run all SQL migrations in order."""
    db_url = config_manager.get_setting("DATABASE_URL")
    if not db_url:
        logger.error("❌ DATABASE_URL not found")
        return False
    
    engine = create_engine(db_url)
    
    migrations = [
        ("001_add_job_sections.sql", "Add job sections columns"),
        ("add_missing_indexes.sql", "Add performance indexes"),
    ]
    
    logger.info("🚀 Starting database migrations...")
    
    with engine.connect() as conn:
        # Create migrations tracking table if not exists
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                migration_name VARCHAR(255) UNIQUE NOT NULL,
                applied_at TIMESTAMP DEFAULT NOW()
            )
        """))
        conn.commit()
        
        for filename, description in migrations:
            # Check if already applied
            result = conn.execute(
                text("SELECT COUNT(*) FROM schema_migrations WHERE migration_name = :name"),
                {"name": filename}
            )
            
            if result.scalar() > 0:
                logger.info(f"⏭️  Skipping {filename} (already applied)")
                continue
            
            # Read and execute migration
            migration_path = os.path.join(
                os.path.dirname(__file__), 
                "migrations" if "001_" in filename else "",
                filename
            )
            
            if not os.path.exists(migration_path):
                migration_path = os.path.join(os.path.dirname(__file__), filename)
            
            if not os.path.exists(migration_path):
                logger.warning(f"⚠️  Migration file not found: {filename}")
                continue
            
            logger.info(f"📝 Running {filename}: {description}")
            
            try:
                with open(migration_path, 'r') as f:
                    sql = f.read()
                
                # Execute migration
                conn.execute(text(sql))
                
                # Mark as applied
                conn.execute(
                    text("INSERT INTO schema_migrations (migration_name) VALUES (:name)"),
                    {"name": filename}
                )
                conn.commit()
                
                logger.info(f"✅ {filename} applied successfully")
                
            except Exception as e:
                logger.error(f"❌ Failed to apply {filename}: {e}")
                conn.rollback()
                return False
    
    logger.info("✅ All migrations completed successfully")
    return True

if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)
