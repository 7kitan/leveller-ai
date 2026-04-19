"""
Migration: Thêm is_verified vào bảng user_cvs
Chạy: python -m scripts.migrate_add_is_verified
"""

import sys
import os

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
            WHERE table_name = 'user_cvs' AND column_name = 'is_verified'
        """)
        ).fetchone()

        if result:
            logger.info("Column 'is_verified' already exists. Migration skipped.")
            return

        # Add is_verified column
        logger.info("Adding column 'is_verified' to 'user_cvs' table...")
        conn.execute(
            text("""
            ALTER TABLE user_cvs
            ADD COLUMN is_verified BOOLEAN DEFAULT FALSE
        """)
        )
        conn.commit()
        logger.info(
            "Migration successful: Added is_verified to user_cvs"
        )


if __name__ == "__main__":
    migrate()
