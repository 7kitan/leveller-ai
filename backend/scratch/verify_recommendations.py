
import asyncio
import os
import sys
import uuid
import json

# Add path to import shared and services
sys.path.append("/app")

from shared.database import SessionLocal
from services.analysis_service.recommender import CourseRecommender

async def verify_recommendations():
    db = SessionLocal()
    recommender = CourseRecommender(db)
    
    test_cases = [
        {"skill": "Java", "level": 3, "gap": "MISSING"},
        {"skill": "AWS", "level": 4, "gap": "UPLEVEL_GAP"},
        {"skill": "Clean Code", "level": 5, "gap": "FRAMEWORK_GAP"},
        {"skill": "React", "level": 2, "gap": "MISSING"}
    ]
    
    print(f"--- [VERIFY] Course & Certification Recommendations ---")
    
    for tc in test_cases:
        print(f"\nQuery: {tc['skill']} (Target Level: {tc['level']}, Gap: {tc['gap']})")
        recs = recommender.recommend_for_gap(tc['skill'], tc['level'], tc['gap'])
        
        if not recs:
            print("  ❌ No recommendations found!")
            continue
            
        for i, r in enumerate(recs):
            cert_flag = "[CERT]" if r.get('is_certification') else "[COURSE]"
            print(f"  {i+1}. {cert_flag} {r['title']} | Platform: {r['platform']} | Provider: {r['provider']}")

    db.close()

if __name__ == "__main__":
    asyncio.run(verify_recommendations())
