"""
Clear gap_v3 cache from Redis.

Usage:
    python scripts/clear_gap_cache.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared.redis_client import result_cache
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clear_gap_cache():
    """Clear all gap_v3 cache keys from Redis."""
    
    logger.info("Starting gap_v3 cache cleanup...")
    
    # Scan for all gap_v3 keys
    cursor = 0
    total_deleted = 0
    batch_size = 100
    
    while True:
        cursor, keys = result_cache.scan(cursor=cursor, match="gap_v3*", count=batch_size)
        
        if keys:
            # Remove prefix from keys for deletion
            keys_to_delete = [k.replace("advisor:", "") for k in keys]
            deleted = result_cache.delete(*keys_to_delete)
            total_deleted += deleted
            logger.info(f"Deleted {deleted} keys (batch)")
        
        if cursor == 0:
            break
    
    logger.info(f"✓ Cache cleanup complete. Total keys deleted: {total_deleted}")
    return total_deleted


if __name__ == "__main__":
    try:
        count = clear_gap_cache()
        print(f"\n✓ Successfully cleared {count} gap_v3 cache keys")
    except Exception as e:
        logger.error(f"✗ Failed to clear cache: {e}")
        sys.exit(1)
