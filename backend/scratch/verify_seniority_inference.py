
import asyncio
import os
import sys
import uuid
import json

# Add path to import shared and services
sys.path.append("/app")

from shared.database import SessionLocal
from shared.models import UserSkillProfile, Skill, UserCV
from services.analysis_service.gap_calculator import GapCalculator

async def verify_seniority_inference():
    db = SessionLocal()
    calculator = GapCalculator(db)
    
    cv_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    # 1. Setup Mock User: Senior Java (10 years)
    # We'll create a single skill in PG
    java_skill = db.query(Skill).filter(Skill.name == "Java").first()
    if not java_skill:
        java_skill = Skill(id=uuid.uuid4(), name="Java", category="Backend")
        db.add(java_skill)
        db.commit()
    
    # Clean up old profiles for this test uuid just in case
    db.query(UserSkillProfile).filter(UserSkillProfile.cv_id == uuid.UUID(cv_id)).delete()
    
    db.add(UserSkillProfile(
        id=uuid.uuid4(),
        cv_id=uuid.UUID(cv_id),
        skill_id=java_skill.id,
        level="Senior",
        years_exp=10.0
    ))
    db.commit()
    
    # 2. Requirements: Mandatory Clean Code and Modularization
    jd_reqs = [
        {"skill_name": "Clean code", "importance_weight": 8, "required_level": "Senior", "is_mandatory": True},
        {"skill_name": "Modularization", "importance_weight": 8, "required_level": "Senior", "is_mandatory": True}
    ]
    
    print(f"--- [VERIFY] Seniority Inference: User (Java 10y) vs Requirements (Clean Code & Modularization) ---")
    
    try:
        report = await calculator.calculate_gap_v2(user_id, cv_id, jd_reqs)
        # print(json.dumps(report, indent=2))
        
        # Check breakdown
        met_skills = [m["skill"] for m in report["breakdown"]["met"]]
        scores = {m["skill"]: m["score"] for m in report["breakdown"]["met"]}
        
        print(f"Skills classified as MET/INFERRED: {met_skills}")
        
        passed = True
        for s in ["Clean code", "Modularization"]:
            if s not in met_skills:
                print(f"❌ FAILURE: {s} was not inferred.")
                passed = False
            elif scores[s] < 90:
                print(f"❌ FAILURE: {s} score too low ({scores[s]}%).")
                passed = False
            else:
                print(f"✅ SUCCESS: {s} inferred correctly with {scores[s]}% score.")
        
        if passed:
            print("\n🎉 Overall Verdict: Seniority Inference Logic is working perfectly!")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(verify_seniority_inference())
