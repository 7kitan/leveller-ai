import os
import sys
import argparse
import logging

# Add parent directory to sys.path to import shared modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.seed_data import seed_base_data
from scripts.seed_import_worker import seed_courses

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
        # 1. Seed base data (Placeholder for skills/basic setup)
        logger.info("Step 1: Initializing Base Data (Minimal)...")
        if not args.dry_run:
            seed_base_data()
        
        # 2. Seed extended Coursera dataset
        if not args.skip_extended:
            logger.info("Step 2: Scrapping & Seeding Coursera Dataset (306 courses)...")
            # Calculate absolute path to Project Root
            # From backend/scripts/seed_all.py -> backend/scripts -> backend -> Project Root
            base_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(base_dir, '..', '..'))
            
            # Use DATASET_DIR from env or default to 'dataset' folder at root
            rel_dataset_dir = os.getenv("DATASET_DIR", "dataset")
            # If rel_dataset_dir is relative, make it relative to project root
            if not os.path.isabs(rel_dataset_dir):
                abs_dataset_dir = os.path.abspath(os.path.join(project_root, rel_dataset_dir))
            else:
                abs_dataset_dir = rel_dataset_dir
                
            source_path = os.path.join(abs_dataset_dir, 'coursera_links.txt')
            
            # If explicit link file doesn't exist, try just the dir name (as fallback if env points to file)
            if not os.path.exists(source_path) and os.path.exists(abs_dataset_dir) and os.path.isfile(abs_dataset_dir):
                source_path = abs_dataset_dir

            seed_courses(source_path, force=args.force, dry_run=args.dry_run)
        else:
            logger.info("Step 2: Skipped (extended Coursera dataset)")

        logger.info("✅ All seeding tasks completed successfully!")
    except Exception as e:
        logger.error(f"❌ Master seeding process failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
