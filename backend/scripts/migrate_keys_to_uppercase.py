#!/usr/bin/env python3
"""
Migration script to convert all system_settings keys to UPPERCASE.
This ensures consistency with environment variable naming conventions.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.database import SessionLocal
from shared.models import SystemSetting
from shared.redis_client import config_cache

def migrate_keys_to_uppercase():
    """Convert all system_settings keys to UPPERCASE."""
    db = SessionLocal()
    
    try:
        # Get all settings
        settings = db.query(SystemSetting).all()
        
        print(f"Found {len(settings)} settings to migrate")
        print("-" * 60)
        
        updated_count = 0
        for setting in settings:
            old_key = setting.key
            new_key = old_key.upper()
            
            if old_key != new_key:
                print(f"Migrating: {old_key} → {new_key}")
                
                # Check if uppercase key already exists
                existing = db.query(SystemSetting).filter(
                    SystemSetting.key == new_key
                ).first()
                
                if existing:
                    print(f"  ⚠️  WARNING: {new_key} already exists, skipping...")
                    continue
                
                # Update key
                setting.key = new_key
                updated_count += 1
                
                # Invalidate old cache key
                try:
                    config_cache.delete(old_key)
                    config_cache.delete(new_key)
                except Exception as e:
                    print(f"  ⚠️  Cache invalidation error: {e}")
            else:
                print(f"Already uppercase: {old_key}")
        
        # Commit changes
        db.commit()
        
        print("-" * 60)
        print(f"✅ Migration complete: {updated_count} keys updated")
        
        # List final keys
        print("\nFinal keys in database:")
        settings = db.query(SystemSetting).order_by(SystemSetting.key).all()
        for s in settings:
            print(f"  - {s.key}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("System Settings Key Migration: lowercase → UPPERCASE")
    print("=" * 60)
    migrate_keys_to_uppercase()
