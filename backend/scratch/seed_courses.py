from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
import uuid
import json
from shared.models import Course, Skill
from shared.database import SessionLocal, engine
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_embedding(text_content: str):
    response = client.embeddings.create(
        input=text_content,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

COURSES_DATA = [
    # Java
    {"title": "Java Programming: Solving Problems with Software", "platform": "Coursera", "level": "Basic", "url": "https://coursera.org/learn/java-programming", "duration": 20},
    {"title": "Spring Framework Specialization", "platform": "Coursera", "level": "Middle", "url": "https://coursera.org/specializations/spring-framework", "duration": 60},
    {"title": "Advanced Java and Microservices", "platform": "Udemy", "level": "Senior", "url": "https://udemy.com/advanced-java", "duration": 40},
    
    # Python
    {"title": "Python for Everybody Specialization", "platform": "Coursera", "level": "Basic", "url": "https://coursera.org/specializations/python", "duration": 50},
    {"title": "Django for Beginners", "platform": "Udemy", "level": "Junior", "url": "https://udemy.com/django-beginners", "duration": 15},
    {"title": "Machine Learning with Python", "platform": "EdX", "level": "Middle", "url": "https://edx.org/course/ml-python", "duration": 30},
    
    # Frontend/Web
    {"title": "Modern React with Redux", "platform": "Udemy", "level": "Junior", "url": "https://udemy.com/react-redux", "duration": 52},
    {"title": "Frontend Web Development Bootcamp", "platform": "Udemy", "level": "Basic", "url": "https://udemy.com/frontend-bootcamp", "duration": 80},
    {"title": "Next.js 14 & Enterprise Architecture", "platform": "Pluralsight", "level": "Senior", "url": "https://pluralsight.com/nextjs-advanced", "duration": 25},
    
    # Infrastructure/SQL
    {"title": "SQL for Data Science", "platform": "Coursera", "level": "Basic", "url": "https://coursera.org/learn/sql-for-data-science", "duration": 14},
    {"title": "Docker and Kubernetes: The Complete Guide", "platform": "Udemy", "level": "Middle", "url": "https://udemy.com/docker-and-kubernetes", "duration": 22},
    {"title": "AWS Certified Solutions Architect", "platform": "A Cloud Guru", "level": "Middle", "url": "https://acloudguru.com/aws-csa", "duration": 35}
]

def seed_courses():
    db = SessionLocal()
    try:
        print("--- [CLEAN] Clearing old courses ---")
        db.execute(text("DELETE FROM courses"))
        db.commit()

        print(f"--- [SEED] Planting {len(COURSES_DATA)} high-quality courses ---")
        for c in COURSES_DATA:
            print(f"  > Processing: {c['title']}")
            # Tạo embedding cho title để hỗ trợ Semantic Search
            vector = get_embedding(c['title'])
            
            course = Course(
                id=uuid.uuid4(),
                title=c['title'],
                platform=c['platform'],
                level=c['level'],
                url=c['url'],
                duration_hours=c['duration'],
                vector=vector
            )
            db.add(course)
        
        db.commit()
        print("--- [SUCCESS] Course recommendation pool is ready! ---")
    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_courses()
