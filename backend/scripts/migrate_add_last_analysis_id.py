"""
Migration: Thêm last_analysis_id vào bảng users
Chạy: python -m scripts.migrate_add_last_analysis_id
"""

import sys
import os
import uuid

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.database import engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    with engine.connect() as conn:
        # Check if column already exists
        result = conn.execute(
            text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'last_analysis_id'
        """)
        ).fetchone()

        if result:
            logger.info("Column 'last_analysis_id' already exists in 'users'. Migration skipped.")
            return

        logger.info("Adding column 'last_analysis_id' to table 'users'...")
        
        try:
            # Add last_analysis_id column
            conn.execute(
                text("""
                ALTER TABLE users
                ADD COLUMN last_analysis_id UUID;
                
                -- Also add constraint if possible, but SET NULL depends on user_analysis table existing
                ALTER TABLE users
                ADD CONSTRAINT fk_last_analysis
                FOREIGN KEY (last_analysis_id)
                REFERENCES user_analysis(id)
                ON DELETE SET NULL;
            """)
            )
            conn.commit()
            logger.info(
                "Migration successful: Added last_analysis_id to users"
            )
        except Exception as e:
            conn.rollback()
            logger.error(f"Migration failed: {e}")
            raise e

if __name__ == "__main__":
    migrate()
