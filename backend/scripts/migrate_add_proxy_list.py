#!/usr/bin/env python3
"""
Migration: Add PROXY_LIST to SystemSettings

This migration adds the global PROXY_LIST setting to enable proxy rotation
for all crawlers (TopCV, future crawlers, etc.). The setting stores a 
comma-separated list of proxies in format: IP:PORT:USER:PASS

Usage:
    python scripts/migrate_add_proxy_list.py
"""

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
    logger.info("🚀 Adding PROXY_LIST to system_settings...")
    try:
        # Ensure table exists
        Base.metadata.create_all(engine)
        
        # Add PROXY_LIST setting
        with engine.connect() as conn:
            # Check if setting exists
            check = conn.execute(
                text("SELECT key FROM system_settings WHERE key = 'PROXY_LIST'")
            ).fetchone()
            
            if not check:
                conn.execute(
                    text("INSERT INTO system_settings (key, value, description) VALUES (:key, :value, :desc)"),
                    {
                        "key": "PROXY_LIST", 
                        "value": '', 
                        "desc": "Global proxy list for all crawlers (format: IP:PORT:USER:PASS, comma-separated)"
                    }
                )
                conn.commit()
                logger.info("  ✅ [OK] Added 'PROXY_LIST' setting")
            else:
                logger.info("  ℹ️  [INFO] 'PROXY_LIST' setting already exists")
        
        logger.info("✅ Migration completed successfully!")
        logger.info("\n📝 Next steps:")
        logger.info("  1. Go to Admin Settings UI → Automation tab")
        logger.info("  2. Find 'Proxy List (Global)' field")
        logger.info("  3. Enter proxy list (supports 2 formats):")
        logger.info("     - One per line: IP:PORT:USER:PASS (recommended)")
        logger.info("     - Comma-separated: IP:PORT:USER:PASS,IP2:PORT2:USER2:PASS2")
        logger.info("  4. Example: 107.150.110.153:4157:1tkPxigNT4YM:5MH6SNHd6r5g")
        logger.info("  5. This proxy list will be used by all crawlers (TopCV, future crawlers)")
        
    except Exception as e:
        logger.error(f"  ❌ [ERROR] Migration failed: {e}")
        raise

if __name__ == "__main__":
    migrate()
