import os
import sys
import logging
from sqlalchemy import text

# Determine backend directory (works both locally and in Docker)
if os.path.exists('/app'):  # Docker environment
    backend_dir = '/app'
else:  # Local environment
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add to sys.path if not already there
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Change to backend directory to ensure relative imports work
original_dir = os.getcwd()
os.chdir(backend_dir)

try:
    from shared.database import engine, Base
    from shared.models import SystemSetting
    from dotenv import load_dotenv
    
    load_dotenv()
except ImportError as e:
    print(f"Import error: {e}")
    print(f"sys.path: {sys.path}")
    print(f"Current dir: {os.getcwd()}")
    raise
finally:
    # Restore original directory
    os.chdir(original_dir)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration")

def migrate():
    logger.info("🚀 Initializing Chandra OCR settings in database...")
    try:
        # Ensure table exists
        Base.metadata.create_all(engine)
        
        # Get current values from .env
        chandra_url = os.getenv("CHANDRA_OCR_URL", "")
        chandra_key = os.getenv("CHANDRA_OCR_API_KEY", "")
        
        with engine.connect() as conn:
            # Initialize CHANDRA_OCR_URL (UPPERCASE for consistency)
            check_url = conn.execute(
                text("SELECT key FROM system_settings WHERE key = 'CHANDRA_OCR_URL'")
            ).fetchone()
            
            if not check_url:
                conn.execute(
                    text("INSERT INTO system_settings (key, value, description) VALUES (:key, :value, :desc)"),
                    {
                        "key": "CHANDRA_OCR_URL", 
                        "value": f'"{chandra_url}"',  # JSON string format
                        "desc": "Chandra OCR Hub API URL for CV parsing"
                    }
                )
                logger.info(f"  [OK] Initialized 'CHANDRA_OCR_URL' = {chandra_url}")
            else:
                logger.info("  [INFO] 'CHANDRA_OCR_URL' already exists")
            
            # Initialize CHANDRA_OCR_API_KEY (UPPERCASE for consistency)
            check_key = conn.execute(
                text("SELECT key FROM system_settings WHERE key = 'CHANDRA_OCR_API_KEY'")
            ).fetchone()
            
            if not check_key:
                conn.execute(
                    text("INSERT INTO system_settings (key, value, description) VALUES (:key, :value, :desc)"),
                    {
                        "key": "CHANDRA_OCR_API_KEY", 
                        "value": f'"{chandra_key}"',  # JSON string format
                        "desc": "Chandra OCR Hub API Key for authentication"
                    }
                )
                masked_key = f"{chandra_key[:8]}...{chandra_key[-4:]}" if len(chandra_key) > 12 else "***"
                logger.info(f"  [OK] Initialized 'CHANDRA_OCR_API_KEY' = {masked_key}")
            else:
                logger.info("  [INFO] 'CHANDRA_OCR_API_KEY' already exists")
            
            conn.commit()
            logger.info("✅ Chandra settings migration completed!")
                
    except Exception as e:
        logger.error(f"  [ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    migrate()
