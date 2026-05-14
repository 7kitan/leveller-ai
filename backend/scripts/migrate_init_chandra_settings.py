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
    import json
    logger.info("🚀 Initializing Chandra OCR settings in database...")
    try:
        # Ensure table exists
        Base.metadata.create_all(engine)
        
        # Get current values from .env
        chandra_url = os.getenv("CHANDRA_OCR_URL", "")
        chandra_key = os.getenv("CHANDRA_OCR_API_KEY", "")
        
        with engine.connect() as conn:
            # Initialize or Update CHANDRA_OCR_URL
            check_url = conn.execute(
                text("SELECT value FROM system_settings WHERE key = 'CHANDRA_OCR_URL'")
            ).fetchone()
            
            new_url_json = json.dumps(chandra_url)
            
            if not check_url:
                conn.execute(
                    text("INSERT INTO system_settings (key, value, description) VALUES (:key, :value, :desc)"),
                    {
                        "key": "CHANDRA_OCR_URL", 
                        "value": new_url_json,
                        "desc": "Chandra OCR Hub API URL for CV parsing"
                    }
                )
                logger.info(f"  [OK] Inserted 'CHANDRA_OCR_URL' = {chandra_url}")
            else:
                # Compare JSON values
                current_val_json = check_url[0]
                # Handle cases where current_val might be a string or already JSON-encoded string
                try:
                    if isinstance(current_val_json, str):
                        current_val = json.loads(current_val_json)
                    else:
                        current_val = current_val_json
                except:
                    current_val = str(current_val_json).strip('"')

                if current_val != chandra_url:
                    conn.execute(
                        text("UPDATE system_settings SET value = :value WHERE key = 'CHANDRA_OCR_URL'"),
                        {"value": new_url_json}
                    )
                    logger.info(f"  [OK] Updated 'CHANDRA_OCR_URL' from '{current_val}' to '{chandra_url}'")
                else:
                    logger.info(f"  [INFO] 'CHANDRA_OCR_URL' already up to date: {chandra_url}")
            
            # Initialize or Update CHANDRA_OCR_API_KEY
            check_key = conn.execute(
                text("SELECT value FROM system_settings WHERE key = 'CHANDRA_OCR_API_KEY'")
            ).fetchone()
            
            new_key_json = json.dumps(chandra_key)
            
            if not check_key:
                conn.execute(
                    text("INSERT INTO system_settings (key, value, description) VALUES (:key, :value, :desc)"),
                    {
                        "key": "CHANDRA_OCR_API_KEY", 
                        "value": new_key_json,
                        "desc": "Chandra OCR Hub API Key for authentication"
                    }
                )
                logger.info("  [OK] Inserted 'CHANDRA_OCR_API_KEY'")
            else:
                current_val_json = check_key[0]
                try:
                    if isinstance(current_val_json, str):
                        current_val = json.loads(current_val_json)
                    else:
                        current_val = current_val_json
                except:
                    current_val = str(current_val_json).strip('"')

                if current_val != chandra_key:
                    conn.execute(
                        text("UPDATE system_settings SET value = :value WHERE key = 'CHANDRA_OCR_API_KEY'"),
                        {"value": new_key_json}
                    )
                    logger.info("  [OK] Updated 'CHANDRA_OCR_API_KEY'")
                else:
                    logger.info("  [INFO] 'CHANDRA_OCR_API_KEY' already up to date")
            
            conn.commit()
            logger.info("✅ Chandra settings migration completed!")
                
    except Exception as e:
        logger.error(f"  [ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    migrate()
