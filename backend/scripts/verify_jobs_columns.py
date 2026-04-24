import os
import sys
import logging
from sqlalchemy import text

# Add parent directory to sys.path to import shared modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_columns")

def verify():
    query = text("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'jobs'
        ORDER BY column_name;
    """)
    
    try:
        with engine.connect() as conn:
            results = conn.execute(query).fetchall()
            logger.info("Columns in 'jobs' table:")
            for row in results:
                logger.info(f"  - {row[0]} ({row[1]})")
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")

if __name__ == "__main__":
    verify()
