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
    # Use environment variable if provided (for Docker), otherwise fallback to relative path (for local)
    dataset_dir = os.getenv("DATASET_DIR", os.path.join(os.path.dirname(__file__), "../../dataset"))
    taxonomy_path = os.path.join(dataset_dir, "tech_taxonomy.json")
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

def seed_base_data():
    """Seed base data (Currently empty as seeding is now via crawlers)."""
    logger.info("=== BASE DATA SEEDING (SKIPPED - USE CRAWLERS) ===")

if __name__ == "__main__":
    seed_base_data()
