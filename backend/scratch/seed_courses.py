import sys
import os
import uuid

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.orm import Session
from shared.database import SessionLocal, Base
from shared.models import Course

def seed_courses():
    db = SessionLocal()
    
    mock_courses = [
        {
            "title": "Complete NodeJS Developer in 2026",
            "description": "Master Node.js by building real-world RESTful APIs and GraphQL.",
            "platform": "Udemy",
            "url": "https://udemy.com/nodejs",
            "language": "en",
            "level": "Intermediate",
            "is_certification": False,
            "provider": "Andrei Neagoie",
            "duration_hours": 45.5,
            "cost_usd": 15.0,
            "tags": ["Node.js", "Express", "REST API", "Backend", "JavaScript", "GraphQL"]
        },
        {
            "title": "Docker & Kubernetes: The Practical Guide",
            "description": "Learn Docker & Kubernetes from scratch and deploy applications.",
            "platform": "Udemy",
            "url": "https://udemy.com/docker-kubernetes",
            "language": "en",
            "level": "Intermediate",
            "is_certification": False,
            "provider": "Maximilian Schwarzmüller",
            "duration_hours": 23.0,
            "cost_usd": 12.0,
            "tags": ["Docker", "Kubernetes", "DevOps", "Containerization"]
        },
        {
            "title": "AWS Certified Solutions Architect - Associate",
            "description": "Pass the AWS Certified Solutions Architect Associate Certification.",
            "platform": "Coursera",
            "url": "https://coursera.org/aws",
            "language": "en",
            "level": "Advanced",
            "is_certification": True,
            "provider": "Amazon Web Services",
            "duration_hours": 60.0,
            "cost_usd": 49.0,
            "tags": ["AWS", "Cloud Computing", "Architecture", "EC2", "S3"]
        },
        {
            "title": "React - The Complete Guide (incl Hooks, React Router, Redux)",
            "description": "Dive in and learn React.js from scratch!",
            "platform": "Udemy",
            "url": "https://udemy.com/react",
            "language": "en",
            "level": "Beginner",
            "is_certification": False,
            "provider": "Academind",
            "duration_hours": 50.5,
            "cost_usd": 14.0,
            "tags": ["React", "JavaScript", "Frontend", "Redux", "Hooks"]
        },
        {
            "title": "Data Structures and Algorithms: Deep Dive Using Java",
            "description": "Learn about Arrays, Linked Lists, Trees, Hashtables, Stacks, Queues, Heaps, Sort algorithms.",
            "platform": "Udemy",
            "url": "https://udemy.com/dsa-java",
            "language": "en",
            "level": "Intermediate",
            "is_certification": False,
            "provider": "Tim Buchalka",
            "duration_hours": 16.0,
            "cost_usd": 10.0,
            "tags": ["Java", "Data Structures", "Algorithms", "Core CS"]
        },
        {
            "title": "The Complete SQL Bootcamp 2026: Go from Zero to Hero",
            "description": "Become an expert at SQL!",
            "platform": "Udemy",
            "url": "https://udemy.com/sql-bootcamp",
            "language": "en",
            "level": "Beginner",
            "is_certification": False,
            "provider": "Jose Portilla",
            "duration_hours": 9.0,
            "cost_usd": 9.0,
            "tags": ["SQL", "Database", "PostgreSQL"]
        },
        {
            "title": "Microservices with Node JS and React",
            "description": "Build, deploy, and scale an E-Commerce app using Microservices.",
            "platform": "Udemy",
            "url": "https://udemy.com/microservices",
            "language": "en",
            "level": "Advanced",
            "is_certification": False,
            "provider": "Stephen Grider",
            "duration_hours": 54.0,
            "cost_usd": 20.0,
            "tags": ["Microservices", "Node.js", "React", "Docker", "Kubernetes", "Architecture"]
        },
        {
            "title": "Professional Leadership & Team Management",
            "description": "Learn essential skills for leading engineering teams.",
            "platform": "Coursera",
            "url": "https://coursera.org/leadership",
            "language": "en",
            "level": "Intermediate",
            "is_certification": True,
            "provider": "University of Michigan",
            "duration_hours": 15.0,
            "cost_usd": 39.0,
            "tags": ["Leadership", "Management", "Agile", "Scrum", "Soft Skills"]
        },
        {
            "title": "Mastering Go Programming",
            "description": "In-depth guide to developing applications with Go.",
            "platform": "Pluralsight",
            "url": "https://pluralsight.com/go",
            "language": "en",
            "level": "Intermediate",
            "is_certification": False,
            "provider": "Pluralsight",
            "duration_hours": 30.0,
            "cost_usd": 29.0,
            "tags": ["Go", "Golang", "Backend", "Concurrency"]
        },
        {
            "title": "System Design Interview Course",
            "description": "Prepare for distributed systems design interview questions.",
            "platform": "Educative.io",
            "url": "https://educative.io/system-design",
            "language": "en",
            "level": "Advanced",
            "is_certification": False,
            "provider": "Educative",
            "duration_hours": 20.0,
            "cost_usd": 50.0,
            "tags": ["System Design", "Architecture", "Scalability", "Distributed Systems", "Cloud"]
        }
    ]

    try:
        count = db.query(Course).count()
        if count > 0:
            print(f"Bảng courses đã chứa {count} bản ghi. Không cần seed thêm.")
            return
            
        print("Đang tiến hành insert mock data cho Bảng courses...")
        inserted = 0
        for data in mock_courses:
            course = Course(
                id=uuid.uuid4(),
                title=data["title"],
                description=data["description"],
                platform=data["platform"],
                url=data["url"],
                language=data["language"],
                level=data["level"],
                is_certification=data["is_certification"],
                provider=data["provider"],
                duration_hours=data["duration_hours"],
                cost_usd=data["cost_usd"],
                tags=data["tags"],
                embedding_context=f"{data['title']}. {data['description']}"
            )
            db.add(course)
            inserted += 1
            
        db.commit()
        print(f"✅ Đã seed thành công {inserted} khóa học lập trình mồi.")
    except Exception as e:
        db.rollback()
        print(f"Lỗi thao tác DB: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_courses()
