import os
import sys
import uuid
import json
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import openai
from dotenv import load_dotenv

# Add parent directory to sys.path to import shared modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.models import Course, Job, Skill, Base
from shared.database import SessionLocal as SharedSessionLocal

# Loading environment
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_data")

# DB Setup
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "career_advisor")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/{POSTGRES_DB}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# OpenAI Setup
openai.api_key = os.getenv("OPENAI_API_KEY")

def get_embedding(text):
    if not text or not openai.api_key: return None
    try:
        response = openai.embeddings.create(
            input=text.replace("\n", " "),
            model="text-embedding-3-small"
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        return None

def seed_skills():
    """Seed skills from tech_taxonomy.json into Postgres."""
    db = SessionLocal()
    taxonomy_path = os.path.join(os.path.dirname(__file__), "../../dataset/tech_taxonomy.json")
    try:
        with open(taxonomy_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        logger.info("--- [SKILLS] Seeding taxonomy into Postgres ---")
        added_count = 0
        
        # Flatten ecosystems into skills
        for ecosystem, skills in data.get("ecosystems", {}).items():
            for s_name in skills:
                existing = db.query(Skill).filter(Skill.name == s_name).first()
                if not existing:
                    new_skill = Skill(id=uuid.uuid4(), name=s_name, category=ecosystem)
                    db.add(new_skill)
                    added_count += 1
        
        db.commit()
        logger.info(f"--- [SUCCESS] Added {added_count} new skills to Postgres ---")
    except Exception as e:
        logger.error(f"Skills seeding error: {e}")
        db.rollback()
    finally:
        db.close()

def seed_jobs():
    """Seed jobs from jobs_dataset.json."""
    db = SessionLocal()
    jobs_path = os.path.join(os.path.dirname(__file__), "../../dataset/jobs_dataset.json")
    try:
        if not os.path.exists(jobs_path):
            logger.warning(f"Jobs dataset not found at {jobs_path}")
            return

        with open(jobs_path, "r", encoding="utf-8") as f:
            jobs_data = json.load(f)
            
        logger.info(f"--- [JOBS] Seeding {len(jobs_data)} jobs ---")
        for j in jobs_data:
            existing = db.query(Job).filter(Job.source_id == j['source_id']).first()
            if existing: continue
            
            context = f"{j['title']} {j['company']} {j['mo_ta_cong_viec'][:200]}"
            embedding = get_embedding(context)
            
            new_job = Job(
                id=uuid.uuid4(),
                source_id=j['source_id'],
                title_raw=j['title'],
                company_name=j['company'],
                source_url=j['url'],
                raw_text=j['mo_ta_cong_viec'],
                embedding_context=context,
                vector=embedding,
                status="active"
            )
            db.add(new_job)
            logger.info(f"  > Seeded Job: {j['title']}")
        
        db.commit()
        logger.info("--- [SUCCESS] Jobs seeded! ---")
    except Exception as e:
        logger.error(f"Jobs seeding error: {e}")
        db.rollback()
    finally:
        db.close()

def seed_courses():
    """Seed standard courses with embeddings."""
    db = SessionLocal()
    try:
        courses = [
            {"title": "Java Programming Masterclass", "platform": "Udemy", "level": "Middle", "provider": "Tim Buchalka", "tags": ["Java", "Backend"]},
            {"title": "React - The Complete Guide", "platform": "Udemy", "level": "Middle", "provider": "Maximilian Schwarz", "tags": ["React", "Frontend"]},
            {"title": "Fullstack Web Dev with Next.js", "platform": "Vercel", "level": "Senior", "provider": "Next.js Team", "tags": ["Next.js", "React", "TypeScript"]},
            {"title": "AI & Machine Learning Foundations", "platform": "Coursera", "level": "Beginner", "provider": "Stanford", "tags": ["AI", "Python", "ML"]},
            {"title": "AWS Certified Developer", "platform": "AWS", "level": "Middle", "provider": "Amazon", "tags": ["AWS", "Cloud", "DevOps"]},
            {"title": "System Design Interview Guide", "platform": "ByteByteGo", "level": "Senior", "provider": "Alex Xu", "tags": ["System Design", "Architecture"]},
            {"title": "NestJS Progressive Node.js Framework", "platform": "Udemy", "level": "Middle", "provider": "NestJS", "tags": ["NestJS", "Node.js", "Backend"]}
        ]

        logger.info(f"--- [COURSES] Seeding {len(courses)} courses ---")
        for c in courses:
            existing = db.query(Course).filter(Course.title == c['title']).first()
            if existing: continue
            
            context = f"{c['title']} {c['provider']} {' '.join(c['tags'])}"
            embedding = get_embedding(context)
            
            new_course = Course(
                id=uuid.uuid4(),
                title=c['title'],
                platform=c['platform'],
                level=c['level'],
                provider=c['provider'],
                tags=c['tags'],
                embedding_context=context,
                vector=embedding
            )
            db.add(new_course)
            logger.info(f"  > Seeded Course: {c['title']}")
        
        db.commit()
        logger.info("--- [SUCCESS] Courses seeded! ---")
    except Exception as e:
        logger.error(f"Courses seeding error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_skills()
    seed_jobs()
    seed_courses()
