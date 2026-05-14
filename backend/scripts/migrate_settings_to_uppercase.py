#!/usr/bin/env python3
"""
Migration script to convert all setting keys from lowercase to UPPERCASE.
This ensures consistency across the entire system.

Usage:
    python scripts/migrate_settings_to_uppercase.py
"""

import os
import sys
import logging
from sqlalchemy import text

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.database import engine
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration")

# Mapping of old lowercase keys to new UPPERCASE keys
KEY_MAPPING = {
    "llm_provider": "LLM_PROVIDER",
    "ai_model": "AI_MODEL",
    "fallback_ai_model": "FALLBACK_AI_MODEL",
    "gap_llm_model": "GAP_LLM_MODEL",
    "gap_pii_masking": "GAP_PII_MASKING",
    "gap_redis_cache": "GAP_REDIS_CACHE",
    "use_llm_gap_agent_v3": "USE_LLM_GAP_AGENT_V3",
    "gap_vector_sim_threshold": "GAP_VECTOR_SIM_THRESHOLD",
    "cv_parser_strategy": "CV_PARSER_STRATEGY",
    "ocr_dpi": "OCR_DPI",
    "similarity_threshold": "SIMILARITY_THRESHOLD",
    "queue_threshold": "QUEUE_THRESHOLD",
    "daily_analysis_limit": "DAILY_ANALYSIS_LIMIT",
    "user_daily_token_limit": "USER_DAILY_TOKEN_LIMIT",
    "user_token_limit": "USER_TOKEN_LIMIT",
    "maintenance_mode": "MAINTENANCE_MODE",
    "maintenance_duration": "MAINTENANCE_DURATION",
    "system_log_ttl_days": "SYSTEM_LOG_TTL_DAYS",
    "system_broadcast": "SYSTEM_BROADCAST",
    "topcv_crawl_enabled": "TOPCV_CRAWL_ENABLED",
    "smtp_host": "SMTP_HOST",
    "smtp_port": "SMTP_PORT",
    "smtp_user": "SMTP_USER",
    "smtp_pass": "SMTP_PASS",
    "smtp_from": "SMTP_FROM",
    "chandra_api_url": "CHANDRA_API_URL",
    "chandra_api_key": "CHANDRA_API_KEY",
}

def migrate():
    logger.info("🚀 Starting migration: Converting setting keys to UPPERCASE...")
    
    try:
        with engine.connect() as conn:
            # Get all existing settings
            result = conn.execute(text("SELECT key, value, description FROM system_settings"))
            settings = result.fetchall()
            
            updated_count = 0
            skipped_count = 0
            
            for old_key, value, description in settings:
                # Check if this key needs to be converted
                if old_key in KEY_MAPPING:
                    new_key = KEY_MAPPING[old_key]
                    
                    # Check if UPPERCASE version already exists
                    check = conn.execute(
                        text("SELECT key FROM system_settings WHERE key = :key"),
                        {"key": new_key}
                    ).fetchone()
                    
                    if check:
                        # UPPERCASE version exists, delete the lowercase one
                        conn.execute(
                            text("DELETE FROM system_settings WHERE key = :key"),
                            {"key": old_key}
                        )
                        logger.info(f"  [DELETED] Removed duplicate lowercase key: {old_key}")
                        updated_count += 1
                    else:
                        # Update the key to UPPERCASE
                        conn.execute(
                            text("UPDATE system_settings SET key = :new_key WHERE key = :old_key"),
                            {"new_key": new_key, "old_key": old_key}
                        )
                        logger.info(f"  [UPDATED] {old_key} → {new_key}")
                        updated_count += 1
                elif old_key.isupper():
                    # Already uppercase, skip
                    skipped_count += 1
                else:
                    # Unknown lowercase key, warn
                    logger.warning(f"  [WARNING] Unknown lowercase key found: {old_key}")
            
            conn.commit()
            
            logger.info(f"\n✅ Migration completed!")
            logger.info(f"   Updated: {updated_count}")
            logger.info(f"   Skipped: {skipped_count}")
            
            # Clear Redis cache to force refresh
            logger.info("\n🔄 Clearing Redis cache...")
            try:
                from shared.redis_client import config_cache
                config_cache.flushdb()
                logger.info("   [OK] Redis config cache cleared")
            except Exception as e:
                logger.warning(f"   [WARNING] Could not clear Redis cache: {e}")
                
    except Exception as e:
        logger.error(f"  [ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    migrate()
