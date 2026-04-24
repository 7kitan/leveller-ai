import os
import sys
import logging
from sqlalchemy import text

# Add parent directory to sys.path to import shared modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("run_migration")

def run_migration():
    migration_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "migrations", "001_add_job_sections.sql"))
    
    if not os.path.exists(migration_file):
        logger.error(f"Migration file not found: {migration_file}")
        return

    logger.info(f"Reading migration from {migration_file}...")
    with open(migration_file, "r", encoding="utf-8") as f:
        sql = f.read()

    logger.info("Executing migration...")
    try:
        with engine.connect() as conn:
            # SQLAlchemy text() can only execute one statement at a time in some drivers, 
            # or it might fail with complex SQL. Let's split by semicolon if needed, 
            # but simple ALTER TABLEs usually work.
            # However, psycopg2 allows multiple statements.
            conn.execute(text(sql))
            conn.commit()
        logger.info("✅ Migration completed successfully!")
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")

if __name__ == "__main__":
    run_migration()
