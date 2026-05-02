"""
Migration: Add BM25 Full-Text Search to YouTube Videos

This migration adds:
1. search_vector tsvector column for BM25 full-text search
2. GIN index for fast text search
3. Trigger to auto-update search_vector on insert/update
4. Populate existing videos with search vectors

PostgreSQL full-text search with ts_rank provides BM25-like scoring.

Run with: python -m scripts.migrate_add_youtube_bm25
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import text
from shared.database import SessionLocal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    db = SessionLocal()
    
    try:
        logger.info("=" * 70)
        logger.info("Starting YouTube BM25 Full-Text Search Migration...")
        logger.info("=" * 70)
        
        # Step 1: Add search_vector column
        logger.info("\nStep 1: Adding search_vector tsvector column...")
        
        db.execute(text("""
            ALTER TABLE youtube_courses
            ADD COLUMN IF NOT EXISTS search_vector tsvector;
        """))
        
        logger.info("✓ Added search_vector column")
        
        # Step 2: Create function to generate search vector
        logger.info("\nStep 2: Creating search vector generation function...")
        
        db.execute(text("""
            CREATE OR REPLACE FUNCTION youtube_courses_search_vector_update() 
            RETURNS trigger AS $$
            BEGIN
                -- Weighted text search vector:
                -- A (highest): title
                -- B (medium): description
                -- C (lower): channel_name
                NEW.search_vector := 
                    setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
                    setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'B') ||
                    setweight(to_tsvector('english', COALESCE(NEW.channel_name, '')), 'C');
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """))
        
        logger.info("✓ Created search vector generation function")
        
        # Step 3: Create trigger
        logger.info("\nStep 3: Creating trigger for auto-update...")
        
        db.execute(text("""
            DROP TRIGGER IF EXISTS youtube_courses_search_vector_trigger 
            ON youtube_courses;
        """))
        
        db.execute(text("""
            CREATE TRIGGER youtube_courses_search_vector_trigger
            BEFORE INSERT OR UPDATE ON youtube_courses
            FOR EACH ROW
            EXECUTE FUNCTION youtube_courses_search_vector_update();
        """))
        
        logger.info("✓ Created trigger for auto-update")
        
        # Step 4: Populate existing videos
        logger.info("\nStep 4: Populating search vectors for existing videos...")
        
        result = db.execute(text("SELECT COUNT(*) FROM youtube_courses")).scalar()
        logger.info(f"Found {result} existing videos to process...")
        
        db.execute(text("""
            UPDATE youtube_courses
            SET search_vector = 
                setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(description, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(channel_name, '')), 'C')
            WHERE search_vector IS NULL;
        """))
        
        updated = db.execute(text("""
            SELECT COUNT(*) FROM youtube_courses WHERE search_vector IS NOT NULL
        """)).scalar()
        
        logger.info(f"✓ Populated search vectors for {updated} videos")
        
        # Step 5: Create GIN index for fast search
        logger.info("\nStep 5: Creating GIN index for full-text search...")
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_youtube_courses_search_vector 
            ON youtube_courses USING GIN(search_vector);
        """))
        
        logger.info("✓ Created GIN index")
        
        # Step 6: Verify setup
        logger.info("\nStep 6: Verifying setup...")
        
        # Test query
        test_result = db.execute(text("""
            SELECT 
                video_id, 
                title,
                ts_rank(search_vector, to_tsquery('english', 'python')) as rank
            FROM youtube_courses
            WHERE search_vector @@ to_tsquery('english', 'python')
            ORDER BY rank DESC
            LIMIT 3;
        """)).fetchall()
        
        if test_result:
            logger.info(f"✓ Test query successful - found {len(test_result)} matches for 'python'")
            for i, r in enumerate(test_result, 1):
                logger.info(f"  {i}. {r.title[:50]}... (rank: {r.rank:.4f})")
        else:
            logger.info("✓ Test query successful (no matches found - database may be empty)")
        
        # Commit all changes
        db.commit()
        
        logger.info("\n" + "=" * 70)
        logger.info("✓ Migration completed successfully!")
        logger.info("=" * 70)
        logger.info("\nNext steps:")
        logger.info("1. Update youtube_service.py to use hybrid search (vector + BM25)")
        logger.info("2. Adjust scoring weights: vector (0.5) + BM25 (0.3) + boosts (0.2)")
        logger.info("3. Test search quality with real queries")
        logger.info("\nBM25 Features:")
        logger.info("- Title matches: highest weight (A)")
        logger.info("- Description matches: medium weight (B)")
        logger.info("- Channel name matches: lower weight (C)")
        logger.info("- Automatic stemming (e.g., 'programming' matches 'program', 'programmer')")
        logger.info("- Stop word removal (e.g., 'the', 'a', 'an')")
        
    except Exception as e:
        db.rollback()
        logger.error(f"✗ Migration failed: {e}", exc_info=True)
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
