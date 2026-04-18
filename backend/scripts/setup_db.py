import os
import sys
import logging
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Add parent directory to sys.path to import shared modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.database import Base, engine
from shared.models import User, Course, Skill, Job # Import all to ensure Base knows them
from scripts.create_admin import create_admin
from scripts.seed_all import seed_base_data
from scripts.seed_import_worker import seed_courses

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("setup_db")

def setup_db(skip_extended=True, skip_embed=False):
    logger.info("🚀 Starting Full Database Setup...")

    # 1. Initialize Extensions
    logger.info("Step 1: Initializing Extensions (pgvector)...")
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
            logger.info("  [OK] pgvector extension ready")
    except Exception as e:
        logger.warning(f"  [WARN] Could not create extension (might already exist or permission issue): {e}")

    # 2. Create Schema
    logger.info("Step 2: Creating Tables & Constraints...")
    try:
        # This will create all tables including the new unique constraints and columns
        # defined in models.py (username, composite unique index on courses, etc.)
        Base.metadata.create_all(engine)
        logger.info("  [OK] Database schema created successfully")
    except Exception as e:
        logger.error(f"  [ERROR] Schema creation failed: {e}")
        return

    # 3. Create Admin User
    logger.info("Step 3: Creating System Admin...")
    try:
        admin_email = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@lumix.ai")
        admin_pass = os.getenv("DEFAULT_ADMIN_PASSWORD", "Admin@123")
        create_admin(admin_email, admin_pass, "System Admin")
        logger.info(f"  [OK] Admin user ensured: {admin_email}")
    except Exception as e:
        logger.error(f"  [ERROR] Admin creation failed: {e}")

    logger.info("✅ Database Setup Completed Successfully! (Seeding skipped - use crawlers/seed_all.py)")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Full Database Setup: Schema creation + Seeding")
    parser.add_argument("--extended", action="store_true", help="Seed the full 300+ courses dataset")
    parser.add_argument("--skip-embed", action="store_true", help="Skip OpenAI embeddings for faster setup")
    
    args = parser.parse_args()
    
    # Run setup
    setup_db(skip_extended=not args.extended, skip_embed=args.skip_embed)
