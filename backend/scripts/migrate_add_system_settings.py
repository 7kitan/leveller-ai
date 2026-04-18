import os
import sys
import logging
from sqlalchemy import text

# Add parent directory to sys.path to import shared modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.database import engine, Base
from shared.models import SystemSetting

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration")

def migrate():
    logger.info("🚀 Creating system_settings table...")
    try:
        # This will create any missing tables
        Base.metadata.create_all(engine)
        logger.info("  [OK] system_settings table created (if missing)")
        
        # Initialize default settings
        with engine.connect() as conn:
            # Check if setting exists
            check = conn.execute(text("SELECT key FROM system_settings WHERE key = 'topcv_crawl_enabled'")).fetchone()
            if not check:
                conn.execute(
                    text("INSERT INTO system_settings (key, value, description) VALUES (:key, :value, :desc)"),
                    {"key": "topcv_crawl_enabled", "value": 'true', "desc": "Toggle automatic background crawl for TopCV (every 30 mins)"}
                )
                conn.commit()
                logger.info("  [OK] Initialized 'topcv_crawl_enabled' = true")
            else:
                logger.info("  [INFO] 'topcv_crawl_enabled' setting already exists")
                
    except Exception as e:
        logger.error(f"  [ERROR] Migration failed: {e}")

if __name__ == "__main__":
    migrate()
