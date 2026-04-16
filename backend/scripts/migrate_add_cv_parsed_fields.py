"""
Migration: Thêm cv_parsed_json và cv_parsed_at vào bảng user_cvs
Chạy: python -m scripts.migrate_add_cv_parsed_fields
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
            WHERE table_name = 'user_cvs' AND column_name = 'cv_parsed_json'
        """)
        ).fetchone()

        if result:
            logger.info("Column 'cv_parsed_json' already exists. Migration skipped.")
            return

        # Add cv_parsed_json column
        conn.execute(
            text("""
            ALTER TABLE user_cvs
            ADD COLUMN cv_parsed_json JSONB
            ADD COLUMN cv_parsed_at TIMESTAMP WITH TIME ZONE
        """)
        )
        conn.commit()
        logger.info(
            "Migration successful: Added cv_parsed_json and cv_parsed_at to user_cvs"
        )


if __name__ == "__main__":
    migrate()
