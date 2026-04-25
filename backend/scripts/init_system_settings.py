#!/usr/bin/env python3
"""
Initialize System Settings in Database

This script ensures all necessary system settings are present in the database
with proper default values from environment variables.

Usage:
    python scripts/init_system_settings.py [--force]
    
Options:
    --force    Overwrite existing settings with env var values
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.models import SystemSetting
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("init_settings")

# Database connection
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "career_advisor")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

logger.info(f"Connecting to database at {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Settings to initialize (key, env_var, default_value, description)
SETTINGS_CONFIG = [
    # AI/LLM Configuration
    ("llm_provider", "LLM_PROVIDER", "openai", "LLM provider (openai, gemini, etc.)"),
    ("ai_model", "LLM_MODEL", "gpt-4o-mini", "Default AI model name"),
    ("fallback_ai_model", "FALLBACK_AI_MODEL", "gpt-4o-mini", "Fallback AI model"),
    
    # Gap Analysis
    ("gap_llm_model", "GAP_LLM_MODEL", "gpt-4o-mini", "Model for gap analysis"),
    ("gap_pii_masking", "GAP_PII_MASKING", "true", "Enable PII masking in gap analysis"),
    ("gap_redis_cache", "GAP_REDIS_CACHE", "true", "Enable Redis caching for gap analysis"),
    ("use_llm_gap_agent_v3", "USE_LLM_GAP_AGENT_V3", "true", "Use LLM-based gap agent v3"),
    ("gap_vector_sim_threshold", "GAP_VECTOR_SIM_THRESHOLD", "0.35", "Vector similarity threshold for gap analysis"),
    
    # CV Parsing
    ("cv_parser_strategy", "CV_PARSER_STRATEGY", "chandra", "CV parser strategy: direct or chandra"),
    ("ocr_dpi", "OCR_DPI", "200", "OCR DPI setting"),
    
    # Recommendations
    ("similarity_threshold", "SIMILARITY_THRESHOLD", "0.60", "Course similarity threshold"),
    
    # Queue & Rate Limiting
    ("queue_threshold", "QUEUE_THRESHOLD", "5", "Queue threshold for analysis"),
    ("daily_analysis_limit", "DAILY_ANALYSIS_LIMIT", "10", "Daily analysis limit per user"),
    ("user_daily_token_limit", "USER_DAILY_TOKEN_LIMIT", "50000", "Daily token limit per user"),
    ("user_token_limit", "USER_TOKEN_LIMIT", "100000", "General user token limit"),
    
    # System Maintenance
    ("maintenance_mode", "MAINTENANCE_MODE", "false", "System maintenance mode flag"),
    ("maintenance_duration", "MAINTENANCE_DURATION", "~ 2 giờ", "Maintenance duration message"),
    ("system_log_ttl_days", "SYSTEM_LOG_TTL_DAYS", "30", "System log retention days"),
    ("system_broadcast", "SYSTEM_BROADCAST", "", "System broadcast message"),
    
    # Crawling
    ("topcv_crawl_enabled", "TOPCV_CRAWL_ENABLED", "true", "Enable TopCV job crawling"),
]

def init_settings(force=False):
    """Initialize system settings from environment variables."""
    db = SessionLocal()
    try:
        created = 0
        updated = 0
        skipped = 0
        
        for key, env_var, default_value, description in SETTINGS_CONFIG:
            # Get value from env var or use default
            value = os.getenv(env_var, default_value)
            
            # Check if setting exists
            existing = db.query(SystemSetting).filter(SystemSetting.key == key).first()
            
            if existing:
                if force:
                    # Update with env var value
                    existing.value = value
                    existing.description = description
                    db.commit()
                    logger.info(f"  [UPDATED] {key} = {value}")
                    updated += 1
                else:
                    logger.info(f"  [SKIP] {key} already exists (use --force to update)")
                    skipped += 1
            else:
                # Create new setting
                new_setting = SystemSetting(
                    key=key,
                    value=value,
                    description=description
                )
                db.add(new_setting)
                db.commit()
                logger.info(f"  [CREATED] {key} = {value}")
                created += 1
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Settings initialization complete!")
        logger.info(f"  Created: {created}")
        logger.info(f"  Updated: {updated}")
        logger.info(f"  Skipped: {skipped}")
        logger.info(f"{'='*60}\n")
        
    except Exception as e:
        logger.error(f"Error initializing settings: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def verify_settings():
    """Verify all settings are present in database."""
    db = SessionLocal()
    try:
        logger.info("\nVerifying settings in database...")
        all_settings = db.query(SystemSetting).order_by(SystemSetting.key).all()
        
        logger.info(f"\nFound {len(all_settings)} settings in database:")
        for setting in all_settings:
            # Mask sensitive values
            display_value = setting.value
            if 'key' in setting.key.lower() or 'pass' in setting.key.lower():
                display_value = "***MASKED***"
            logger.info(f"  ✓ {setting.key} = {display_value}")
        
        # Check for missing settings
        existing_keys = {s.key for s in all_settings}
        expected_keys = {key for key, _, _, _ in SETTINGS_CONFIG}
        missing_keys = expected_keys - existing_keys
        
        if missing_keys:
            logger.warning(f"\n⚠️  Missing settings: {', '.join(missing_keys)}")
            logger.warning("Run with --force to create them")
        else:
            logger.info(f"\n✅ All {len(SETTINGS_CONFIG)} expected settings are present!")
            
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Initialize system settings")
    parser.add_argument("--force", action="store_true", help="Overwrite existing settings")
    parser.add_argument("--verify", action="store_true", help="Only verify settings, don't create")
    
    args = parser.parse_args()
    
    if args.verify:
        verify_settings()
    else:
        logger.info("="*60)
        logger.info("System Settings Initialization")
        logger.info("="*60)
        init_settings(force=args.force)
        verify_settings()
