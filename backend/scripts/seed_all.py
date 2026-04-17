import os
import sys
import argparse
import logging

# Add parent directory to sys.path to import shared modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.seed_data import seed_base_data
from scripts.seed_coursera_300 import seed_coursera_300

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("seed_all")

def main():
    parser = argparse.ArgumentParser(description="Master script to seed all data (Skills, Jobs, Courses)")
    parser.add_argument("--force", action="store_true", help="Re-seed even if data exists")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be inserted (no writes)")
    parser.add_argument("--skip-embed", action="store_true", help="Skip OpenAI embeddings (dev/fast mode)")
    parser.add_argument("--skip-extended", action="store_true", help="Skip seeding the 300+ Coursera courses")
    args = parser.parse_args()

    logger.info("🚀 Starting Master Seeding Process...")
    if args.dry_run:
        logger.info("🧪 DRY RUN MODE ENABLED")

    try:
        # 1. Seed base data (Skills, Jobs, some basic courses)
        logger.info("Step 1: Seeding Base Data (Skills & Jobs)...")
        if not args.dry_run:
            seed_base_data()
        else:
            logger.info("  [DRY] Skipped base data seeding (not supported in dry-run for now)")

        # 2. Seed extended Coursera dataset
        if not args.skip_extended:
            logger.info("Step 2: Seeding Extended Coursera Dataset (300 courses)...")
            seed_coursera_300(force=args.force, dry_run=args.dry_run, skip_embed=args.skip_embed)
        else:
            logger.info("Step 2: Skipped (extended Coursera dataset)")

        logger.info("✅ All seeding tasks completed successfully!")
    except Exception as e:
        logger.error(f"❌ Master seeding process failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
