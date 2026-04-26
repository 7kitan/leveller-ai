#!/usr/bin/env python3
"""
Re-embed all existing courses with new minimal embedding context.

New format: TITLE + LEVEL + SKILLS only (no platform, provider, description, modules, outcomes)

Usage:
    python scripts/re_embed_courses.py [--dry-run] [--batch-size 50]

Cost estimate: ~303 courses × 30 tokens × $0.02/1M = $0.0002 (negligible)
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from shared.models import Course
from shared.llm_utils import get_embedding
from shared.config_utils import config_manager
import argparse
import time

def main():
    parser = argparse.ArgumentParser(description='Re-embed all courses with new minimal context')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without updating database')
    parser.add_argument('--batch-size', type=int, default=50, help='Number of courses to process in each batch')
    args = parser.parse_args()

    # Database connection
    db_url = config_manager.get_setting("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not found in environment")
        return 1

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # Count total courses
        total = db.query(Course).filter(Course.is_active == True).count()
        print(f"📊 Found {total} active courses to re-embed")
        
        if args.dry_run:
            print("🔍 DRY RUN MODE - No changes will be made")
        
        # Estimate cost
        avg_tokens_per_course = 30  # Title + Level + Skills ≈ 30 tokens
        total_tokens = total * avg_tokens_per_course
        cost = (total_tokens / 1_000_000) * 0.02  # text-embedding-3-small pricing
        print(f"💰 Estimated cost: ~${cost:.4f} ({total_tokens:,} tokens)")
        
        if not args.dry_run:
            confirm = input(f"\n⚠️  This will re-embed {total} courses. Continue? (yes/no): ")
            if confirm.lower() != 'yes':
                print("❌ Aborted by user")
                return 0
        
        # Process in batches
        batch_size = args.batch_size
        offset = 0
        updated_count = 0
        error_count = 0
        
        print(f"\n🚀 Starting re-embedding (batch size: {batch_size})...\n")
        
        while True:
            # Fetch batch
            courses = db.query(Course).filter(
                Course.is_active == True
            ).offset(offset).limit(batch_size).all()
            
            if not courses:
                break
            
            for course in courses:
                try:
                    # Generate new minimal context
                    new_context = (
                        f"TITLE: {course.title}. "
                        f"LEVEL: {course.level or 'Unknown'}. "
                        f"SKILLS: {', '.join(course.skills_raw or [])}."
                    )
                    
                    # Show preview
                    old_context_preview = (course.embedding_context or "")[:100]
                    new_context_preview = new_context[:100]
                    
                    print(f"[{updated_count + 1}/{total}] {course.title[:50]}")
                    print(f"  OLD: {old_context_preview}...")
                    print(f"  NEW: {new_context_preview}...")
                    
                    if not args.dry_run:
                        # Generate new embedding
                        new_vector = get_embedding(new_context, log_cost=False)
                        
                        if new_vector:
                            course.embedding_context = new_context
                            course.vector = new_vector
                            updated_count += 1
                            print(f"  ✅ Updated")
                        else:
                            error_count += 1
                            print(f"  ❌ Failed to generate embedding")
                    else:
                        updated_count += 1
                        print(f"  🔍 Would update (dry-run)")
                    
                    print()
                    
                except Exception as e:
                    error_count += 1
                    print(f"  ❌ Error: {e}\n")
            
            # Commit batch
            if not args.dry_run:
                db.commit()
                print(f"💾 Committed batch {offset // batch_size + 1}\n")
            
            offset += batch_size
            
            # Rate limiting (avoid hitting OpenAI rate limits)
            if not args.dry_run:
                time.sleep(1)
        
        # Summary
        print("\n" + "="*60)
        print(f"✅ Re-embedding complete!")
        print(f"   Total processed: {updated_count}")
        print(f"   Errors: {error_count}")
        if args.dry_run:
            print(f"   Mode: DRY RUN (no changes made)")
        print("="*60)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        db.rollback()
        return 1
    finally:
        db.close()

if __name__ == "__main__":
    sys.exit(main())
