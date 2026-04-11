from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")

class Neo4jSeeder:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def close(self):
        self.driver.close()

    def seed_data(self):
        with self.driver.session() as session:
            # 1. Xóa dữ liệu cũ (Cẩn thận khi dùng trong production)
            session.run("MATCH (n) DETACH DELETE n")
            
            # 2. Tạo Categories
            categories = ["Backend", "Frontend", "Cloud & DevOps", "Mobile", "AI/ML", "Data Science", "Database"]
            for cat in categories:
                session.run("CREATE (:Category {name: $name})", name=cat)
            
            # 3. Tạo Skills và quan hệ BELONGS_TO
            skills_data = [
                # Backend
                ("Node.js", "Backend"), ("Python", "Backend"), ("Java", "Backend"), ("PHP", "Backend"),
                ("FastAPI", "Backend"), ("NestJS", "Backend"), ("ExpressJS", "Backend"), ("Django", "Backend"),
                ("Laravel", "Backend"), ("Go", "Backend"), ("Spring Boot", "Backend"),
                # Frontend
                ("React", "Frontend"), ("Vue", "Frontend"), ("Angular", "Frontend"), ("Next.js", "Frontend"),
                ("HTML5 & CSS3", "Frontend"), ("JavaScript", "Frontend"), ("TypeScript", "Frontend"),
                # DevOps
                ("Docker", "Cloud & DevOps"), ("Kubernetes", "Cloud & DevOps"), ("AWS", "Cloud & DevOps"),
                ("Azure", "Cloud & DevOps"), ("GCP", "Cloud & DevOps"), ("CI/CD", "Cloud & DevOps"),
                ("Terraform", "Cloud & DevOps"), ("Git", "Cloud & DevOps"),
                # AI/ML
                ("HuggingFace", "AI/ML"), ("LangChain", "AI/ML"), ("PyTorch", "AI/ML"), ("TensorFlow", "AI/ML"),
                ("NLP", "AI/ML"), ("Computer Vision", "AI/ML"), ("RAG", "AI/ML"),
                # Database
                ("PostgreSQL", "Database"), ("MongoDB", "Database"), ("Redis", "Database"), ("MySQL", "Database"),
                ("Neo4j", "Database"), ("SQL", "Database"), ("NoSQL", "Database")
            ]
            
            for skill, cat in skills_data:
                session.run("""
                    MATCH (c:Category {name: $cat_name})
                    MERGE (s:Skill {name: $skill_name})
                    MERGE (s)-[:BELONGS_TO]->(c)
                """, skill_name=skill, cat_name=cat)
                
            print(f"Successfully seeded {len(categories)} categories and {len(skills_data)} skills with relationships.")

if __name__ == "__main__":
    seeder = Neo4jSeeder()
    try:
        seeder.seed_data()
    finally:
        seeder.close()
