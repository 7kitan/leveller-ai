
import asyncio
import os
import sys
import uuid
import json

# Add path to import shared and services
sys.path.append("/app")

from shared.database import SessionLocal
from shared.models import UserSkillProfile, Skill
from services.analysis_service.gap_calculator import GapCalculator

async def verify_logical_groups():
    db = SessionLocal()
    calculator = GapCalculator(db)
    
    cv_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    # 1. Setup Mock User: Senior Java (10 years)
    java_skill = db.query(Skill).filter(Skill.name == "Java").first()
    if not java_skill:
        java_skill = Skill(id=uuid.uuid4(), name="Java", category="Backend")
        db.add(java_skill)
        db.commit()
    
    db.add(UserSkillProfile(
        id=uuid.uuid4(),
        cv_id=uuid.UUID(cv_id),
        skill_id=java_skill.id,
        level="Senior",
        years_exp=10.0
    ))
    db.commit()
    
    # 2. Setup Logical Group Requirement: Java OR Rust
    # Note: Rust is NOT in the user's profile.
    jd_reqs = [
        {
            "group_name": "Backend Language (Java/Rust)",
            "is_mandatory": True,
            "logic": "OR",
            "importance_weight": 10,
            "skills": [
                {"skill_name": "Java", "required_level": "Senior"},
                {"skill_name": "Rust", "required_level": "Senior"}
            ]
        }
    ]
    
    print(f"--- [VERIFY] Logical OR Grouping: Java (User has) OR Rust (User lacks) ---")
    
    try:
        report = await calculator.calculate_gap_v2(user_id, cv_id, jd_reqs)
        
        print(f"\nOverall Match: {report['overall_match_pct']}%")
        
        met_skills = [m["skill"] for m in report["breakdown"]["met"]]
        gap_skills = [g["skill"] for g in report["breakdown"]["gap"]]
        
        print(f"MET Skills: {met_skills}")
        print(f"GAP Skills: {gap_skills}")
        
        if "Backend Language (Java/Rust)" in met_skills and report['overall_match_pct'] >= 90:
            print("\n✅ SUCCESS: The group was satisfied by matching only one language!")
        else:
            print("\n❌ FAILURE: Group logic failed or user was penalized.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(verify_logical_groups())
