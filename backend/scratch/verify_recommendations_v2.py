import sys
import os
import uuid
from sqlalchemy.orm import Session

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.database import SessionLocal
from services.analysis_service.recommender import CourseRecommender
import os
os.environ["POSTGRES_HOST"] = "localhost" # Override for local runner

def test_recommendation_quality():
    db = SessionLocal()
    recommender = CourseRecommender(db)
    
    test_cases = [
        "React / TypeScript",      # Phức tạp (slash)
        "Clean Code",               # Kỹ năng mềm/kỹ thuật kết hợp
        "System Design",            # Kỹ năng cấp cao
        "Xây dựng API với Node.js"  # Tiếng Việt
    ]
    
    print("=== STARTING RECOMMENDATION TEST ===")
    for skill in test_cases:
        print(f"\nTesting Skill: {skill}")
        recs = recommender.recommend_for_gap(skill, target_level_score=60, limit=3)
        
        if not recs:
            print("  [!] No recommendations found.")
        else:
            for i, r in enumerate(recs):
                print(f"  [{i+1}] {r['title']} ({r['platform']}) - Level: {r['level']}")
    
    db.close()

if __name__ == "__main__":
    test_recommendation_quality()
