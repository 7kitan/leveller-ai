
import os
import uuid
import json
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shared.models import Course, Skill, Base
import openai

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_advisor")

# DB Setup
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres") # Changed from password123 to postgres
POSTGRES_DB = os.getenv("POSTGRES_DB", "career_advisor") # Changed from advisor_db to career_advisor
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "advisor_db")
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/{POSTGRES_DB}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# OpenAI Setup
openai.api_key = os.getenv("OPENAI_API_KEY")

def get_embedding(text):
    if not text: return None
    try:
        response = openai.embeddings.create(
            input=text.replace("\n", " "),
            model="text-embedding-3-small"
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        return None

def seed_data():
    db = SessionLocal()
    try:
        logger.info("--- [CLEAN] Removing old course data ---")
        db.query(Course).delete()
        db.commit()

        courses_to_seed = [
            # Backend Stack
            {"title": "Java Programming Masterclass", "platform": "Udemy", "level": "Middle", "is_certification": False, "provider": "Tim Buchalka", "tags": ["Java", "Backend"]},
            {"title": "Spring Boot 3 & Spring Framework 6", "platform": "Udemy", "level": "Middle", "is_certification": False, "provider": "Chad Darby", "tags": ["Spring Boot", "Java"]},
            {"title": "The Rust Programming Language", "platform": "Coursera", "level": "Beginner", "is_certification": False, "provider": "Rust Org", "tags": ["Rust", "Backend"]},
            {"title": "Mastering Go (Golang)", "platform": "Udemy", "level": "Middle", "is_certification": False, "provider": "Google Team", "tags": ["Go", "Backend"]},
            {"title": "Advanced C++ Programming", "platform": "Pluralsight", "level": "Senior", "is_certification": False, "provider": "Professional CPP", "tags": ["C++", "Backend"]},
            
            # Frontend Stack
            {"title": "React - The Complete Guide", "platform": "Udemy", "level": "Middle", "is_certification": False, "provider": "Maximilian Schwarzmüller", "tags": ["React", "Frontend"]},
            {"title": "TypeScript Masterclass", "platform": "Frontend Masters", "level": "Middle", "is_certification": False, "provider": "Frontend Masters", "tags": ["TypeScript", "Frontend"]},
            {"title": "Modern Web Development with Vite", "platform": "Pluralsight", "level": "Beginner", "is_certification": False, "provider": "Pluralsight", "tags": ["Vite", "Frontend"]},
            {"title": "Mastering State Management (Redux/Zustand)", "platform": "Udemy", "level": "Senior", "is_certification": False, "provider": "JS Expert", "tags": ["Redux", "Zustand", "State Management"]},
            
            # Universal / Standards
            {"title": "Clean Code: A Handbook of Agile Software Craftsmanship", "platform": "Book/O'Reilly", "level": "Senior", "is_certification": False, "provider": "Robert C. Martin", "tags": ["Clean code", "Methodology"]},
            {"title": "Refactoring: Improving the Design of Existing Code", "platform": "Book/O'Reilly", "level": "Senior", "is_certification": False, "provider": "Martin Fowler", "tags": ["Refactoring", "Clean code"]},
            {"title": "Modular Architecture in Large Scale Apps", "platform": "O'Reilly", "level": "Senior", "is_certification": False, "provider": "Arch Expert", "tags": ["Modularization", "Architecture"]},
            
            # Certifications
            {"title": "AWS Certified Developer Associate", "platform": "AWS Training", "level": "Middle", "is_certification": True, "provider": "Amazon Web Services", "tags": ["AWS", "Cloud", "Backend"]},
            {"title": "Google Cloud Professional Cloud Architect", "platform": "Google Cloud", "level": "Expert", "is_certification": True, "provider": "Google Cloud", "tags": ["GCP", "Cloud", "System Design"]},
            {"title": "HashiCorp Certified: Terraform Associate", "platform": "HashiCorp", "level": "Middle", "is_certification": True, "provider": "HashiCorp", "tags": ["Terraform", "DevOps", "IaC"]},
            
            # Protocols & Concepts
            {"title": "Web Protocols: HTTP/2, REST, and WebSockets", "platform": "Udemy", "level": "Middle", "is_certification": False, "provider": "Networking Pro", "tags": ["HTTP", "REST", "WebSocket"]},
            {"title": "API Design & Implementation Guide", "platform": "Coursera", "level": "Middle", "is_certification": False, "provider": "API University", "tags": ["API Design", "JSON"]}
        ]

        logger.info(f"--- [SEEDING] Seeding {len(courses_to_seed)} items with embeddings ---")
        
        for c in courses_to_seed:
            context = f"{c['title']} {c['provider']} {' '.join(c['tags'])}"
            embedding = get_embedding(context)
            
            new_course = Course(
                id=uuid.uuid4(),
                title=c['title'],
                platform=c['platform'],
                level=c['level'],
                is_certification=c['is_certification'],
                provider=c['provider'],
                tags=c['tags'],
                embedding_context=context,
                vector=embedding
            )
            db.add(new_course)
            logger.info(f"  > Seeded: {c['title']}")
        
        db.commit()
        logger.info("--- [SUCCESS] Course and Certification Data Seeded! ---")

    except Exception as e:
        logger.error(f"Seeding error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
