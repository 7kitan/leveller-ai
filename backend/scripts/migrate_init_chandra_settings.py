import os
import sys
import logging
from sqlalchemy import text

# Add parent directory to sys.path to import shared modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.database import engine, Base
from shared.models import SystemSetting
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration")

def migrate():
    logger.info("🚀 Initializing Chandra OCR settings in database...")
    try:
        # Ensure table exists
        Base.metadata.create_all(engine)
        
        # Get current values from .env
        chandra_url = os.getenv("CHANDRA_API_URL", "")
        chandra_key = os.getenv("CHANDRA_API_KEY", "")
        
        with engine.connect() as conn:
            # Initialize chandra_api_url
            check_url = conn.execute(
                text("SELECT key FROM system_settings WHERE key = 'chandra_api_url'")
            ).fetchone()
            
            if not check_url:
                conn.execute(
                    text("INSERT INTO system_settings (key, value, description) VALUES (:key, :value, :desc)"),
                    {
                        "key": "chandra_api_url", 
                        "value": f'"{chandra_url}"',  # JSON string format
                        "desc": "Chandra OCR Hub API URL for CV parsing"
                    }
                )
                logger.info(f"  [OK] Initialized 'chandra_api_url' = {chandra_url}")
            else:
                logger.info("  [INFO] 'chandra_api_url' already exists")
            
            # Initialize chandra_api_key
            check_key = conn.execute(
                text("SELECT key FROM system_settings WHERE key = 'chandra_api_key'")
            ).fetchone()
            
            if not check_key:
                conn.execute(
                    text("INSERT INTO system_settings (key, value, description) VALUES (:key, :value, :desc)"),
                    {
                        "key": "chandra_api_key", 
                        "value": f'"{chandra_key}"',  # JSON string format
                        "desc": "Chandra OCR Hub API Key for authentication"
                    }
                )
                masked_key = f"{chandra_key[:8]}...{chandra_key[-4:]}" if len(chandra_key) > 12 else "***"
                logger.info(f"  [OK] Initialized 'chandra_api_key' = {masked_key}")
            else:
                logger.info("  [INFO] 'chandra_api_key' already exists")
            
            conn.commit()
            logger.info("✅ Chandra settings migration completed!")
                
    except Exception as e:
        logger.error(f"  [ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    migrate()
