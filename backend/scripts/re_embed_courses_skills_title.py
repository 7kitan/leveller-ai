"""
Re-embed all courses with optimized format: SKILLS + TITLE only.
Level will be filtered via SQL WHERE clause, not embedding.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.database import SessionLocal
from shared.models import Course
from shared.llm_utils import get_embedding
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def re_embed_all_courses():
    """
    Re-embed all courses with optimized format:
    SKILLS: skill1, skill2, skill3. TITLE: course title.
    """
    db = SessionLocal()
    try:
        courses = db.query(Course).all()
        total = len(courses)
        logger.info(f"Found {total} courses to re-embed")
        
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for idx, course in enumerate(courses, 1):
            try:
                # Build new embedding context: SKILLS first, then TITLE
                skills_text = ", ".join(course.skills_raw or [])
                
                if not skills_text and not course.title:
                    logger.warning(f"[{idx}/{total}] Skipping course {course.id} - no skills or title")
                    skip_count += 1
                    continue
                
                # New format: SKILLS first (most important), then TITLE
                if skills_text:
                    context = f"SKILLS: {skills_text}. TITLE: {course.title or 'Unknown'}."
                else:
                    context = f"TITLE: {course.title}."
                
                # Generate new embedding
                new_vector = get_embedding(context)
                
                if not new_vector:
                    logger.warning(f"[{idx}/{total}] Failed to generate embedding for course {course.id}")
                    error_count += 1
                    continue
                
                # Update course
                course.embedding_context = context
                course.vector = new_vector
                
                success_count += 1
                
                if idx % 100 == 0:
                    db.commit()
                    logger.info(f"[{idx}/{total}] Progress: {success_count} success, {skip_count} skipped, {error_count} errors")
            
            except Exception as e:
                logger.error(f"[{idx}/{total}] Error processing course {course.id}: {e}")
                error_count += 1
                continue
        
        # Final commit
        db.commit()
        
        logger.info(
            f"\n{'='*60}\n"
            f"Re-embedding completed!\n"
            f"  Total:   {total}\n"
            f"  Success: {success_count}\n"
            f"  Skipped: {skip_count}\n"
            f"  Errors:  {error_count}\n"
            f"{'='*60}"
        )
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("Starting course re-embedding with SKILLS + TITLE format...")
    re_embed_all_courses()
