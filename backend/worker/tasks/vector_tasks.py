import logging
from worker.celery_app import celery_app
from shared.database import SessionLocal
from shared.models import Skill, Job, Course
from shared.llm_utils import get_embedding
from sqlalchemy import text

logger = logging.getLogger("vector_tasks")


@celery_app.task(name="worker.tasks.vector_tasks.rebuild_all_vectors")
def rebuild_all_vectors():
    """
    Rebuild all vector embeddings for Skills, Jobs, and Courses.
    This is a long-running task that should be triggered manually by admin.
    """
    logger.info("[VECTOR SYNC] Starting full vector rebuild...")
    
    with SessionLocal() as db:
        try:
            # 1. Rebuild Skill Vectors
            skills_updated = rebuild_skill_vectors(db)
            
            # 2. Rebuild Job Vectors
            jobs_updated = rebuild_job_vectors(db)
            
            # 3. Rebuild Course Vectors
            courses_updated = rebuild_course_vectors(db)
            
            db.commit()
            
            logger.info(
                f"[VECTOR SYNC] Completed! "
                f"Skills: {skills_updated}, Jobs: {jobs_updated}, Courses: {courses_updated}"
            )
            
            return {
                "status": "success",
                "skills_updated": skills_updated,
                "jobs_updated": jobs_updated,
                "courses_updated": courses_updated
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"[VECTOR SYNC] Failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


def rebuild_skill_vectors(db) -> int:
    """Rebuild vector embeddings for all skills."""
    logger.info("[VECTOR SYNC] Rebuilding skill vectors...")
    
    skills = db.query(Skill).all()
    updated = 0
    
    for skill in skills:
        try:
            # Generate embedding from skill name
            vector = get_embedding(skill.name)
            if vector:
                skill.vector = vector
                updated += 1
        except Exception as e:
            logger.error(f"[VECTOR SYNC] Failed to generate vector for skill {skill.name}: {e}")
    
    logger.info(f"[VECTOR SYNC] Updated {updated}/{len(skills)} skill vectors")
    return updated


def rebuild_job_vectors(db) -> int:
    """Rebuild vector embeddings for all jobs."""
    logger.info("[VECTOR SYNC] Rebuilding job vectors...")
    
    jobs = db.query(Job).filter(Job.status == "active").all()
    updated = 0
    
    for job in jobs:
        try:
            # Generate embedding from job title + description
            text = f"{job.title_raw or ''} {job.raw_text[:500] if job.raw_text else ''}"
            vector = get_embedding(text.strip())
            if vector:
                job.vector = vector
                updated += 1
        except Exception as e:
            logger.error(f"[VECTOR SYNC] Failed to generate vector for job {job.id}: {e}")
    
    logger.info(f"[VECTOR SYNC] Updated {updated}/{len(jobs)} job vectors")
    return updated


def rebuild_course_vectors(db) -> int:
    """Rebuild vector embeddings for all courses."""
    logger.info("[VECTOR SYNC] Rebuilding course vectors...")
    
    courses = db.query(Course).all()
    updated = 0
    
    for course in courses:
        try:
            # Generate embedding from course title + description
            text = f"{course.title} {course.description[:300] if course.description else ''}"
            vector = get_embedding(text.strip())
            if vector:
                course.vector = vector
                updated += 1
        except Exception as e:
            logger.error(f"[VECTOR SYNC] Failed to generate vector for course {course.id}: {e}")
    
    logger.info(f"[VECTOR SYNC] Updated {updated}/{len(courses)} course vectors")
    return updated
