#!/usr/bin/env python3
"""
Cleanup orphaned CV files that were not deleted after processing.

This script finds CV files in the upload directory that don't have
corresponding active records in the database and deletes them.

Usage:
    python scripts/cleanup_orphaned_cv_files.py [--dry-run]
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shared.config_utils import config_manager
from shared.models import UserCV
import logging
import argparse
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cleanup_cv")

UPLOAD_DIR = "/app/data/cv_uploads"

def cleanup_orphaned_files(dry_run=False, older_than_days=7):
    """
    Find and delete CV files that:
    1. Don't have a corresponding database record, OR
    2. Have status='completed' or 'failed' and are older than X days
    
    Args:
        dry_run: If True, only report what would be deleted
        older_than_days: Only delete files older than this many days
    """
    db_url = config_manager.get_setting("DATABASE_URL")
    if not db_url:
        logger.error("❌ DATABASE_URL not found")
        return False
    
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        # Get all CV file_ids from database
        cv_records = db.query(UserCV.file_id, UserCV.status, UserCV.created_at).all()
        db_file_ids = {str(cv.file_id): (cv.status, cv.created_at) for cv in cv_records}
        
        logger.info(f"📊 Found {len(db_file_ids)} CV records in database")
        
        # Get all files in upload directory
        if not os.path.exists(UPLOAD_DIR):
            logger.error(f"❌ Upload directory not found: {UPLOAD_DIR}")
            return False
        
        all_files = os.listdir(UPLOAD_DIR)
        logger.info(f"📁 Found {len(all_files)} files in upload directory")
        
        if dry_run:
            logger.info("🔍 DRY RUN MODE - No files will be deleted\n")
        
        cutoff_date = datetime.now() - timedelta(days=older_than_days)
        
        deleted_count = 0
        kept_count = 0
        total_size = 0
        
        for filename in all_files:
            file_path = os.path.join(UPLOAD_DIR, filename)
            
            # Extract file_id (filename without extension)
            file_id = os.path.splitext(filename)[0]
            file_size = os.path.getsize(file_path)
            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            should_delete = False
            reason = ""
            
            if file_id not in db_file_ids:
                should_delete = True
                reason = "No database record"
            else:
                status, created_at = db_file_ids[file_id]
                
                # Delete if completed/failed and old enough
                if status in ['completed', 'failed'] and created_at < cutoff_date:
                    should_delete = True
                    reason = f"Status={status}, created {(datetime.now() - created_at).days} days ago"
            
            if should_delete:
                size_mb = file_size / (1024 * 1024)
                logger.info(f"{'[DRY RUN] Would delete' if dry_run else 'Deleting'}: {filename} ({size_mb:.2f}MB) - {reason}")
                
                if not dry_run:
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                        total_size += file_size
                    except Exception as e:
                        logger.error(f"  ❌ Failed to delete {filename}: {e}")
                else:
                    deleted_count += 1
                    total_size += file_size
            else:
                kept_count += 1
        
        total_size_mb = total_size / (1024 * 1024)
        
        logger.info("\n" + "="*60)
        logger.info(f"{'DRY RUN ' if dry_run else ''}CLEANUP SUMMARY")
        logger.info("="*60)
        logger.info(f"Files {'would be ' if dry_run else ''}deleted: {deleted_count}")
        logger.info(f"Files kept: {kept_count}")
        logger.info(f"Space {'would be ' if dry_run else ''}freed: {total_size_mb:.2f} MB")
        logger.info("="*60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error during cleanup: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Cleanup orphaned CV files')
    parser.add_argument('--dry-run', action='store_true', help='Preview what would be deleted without actually deleting')
    parser.add_argument('--older-than-days', type=int, default=7, help='Only delete completed/failed CVs older than this many days (default: 7)')
    
    args = parser.parse_args()
    
    success = cleanup_orphaned_files(dry_run=args.dry_run, older_than_days=args.older_than_days)
    sys.exit(0 if success else 1)
