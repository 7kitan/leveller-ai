import sys
import os
import uuid
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Mocking and setting up environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.models import Skill, UserCV, UserSkillProfile
from shared.database import Base, engine as db_engine
from services.analysis_service.gap_calculator import GapCalculator

Session = sessionmaker(bind=db_engine)
db = Session()

def test_seniority_ignoring():
    print("Testing Seniority Ignoring...")
    calc = GapCalculator(db)
    
    # Mock requirement: Python, 10 years, Senior
    req = {
        "skill": "Python",
        "target_level": "Senior",
        "years_required": 10,
        "is_primary": True
    }
    
    # Mock user skill: Python, 1 year, Senior
    user_skill_map = {
        "python": {"level": "Senior", "years": 1}
    }
    
    res = calc.matcher.match_skill(req, user_skill_map, ["Python"])
    print(f"Match Result: {res['score']} (Should be 1.0 because years are ignored)")
    assert res['score'] == 1.0

def test_platform_matching():
    print("\nTesting Platform Matching (Android -> Kotlin)...")
    calc = GapCalculator(db)
    
    # Mock requirement: Android Development
    req = {"skill": "Android Development", "target_level": "Mid-level"}
    
    # Mock user skill: Kotlin
    user_skills_list = ["Kotlin"]
    user_skill_map = {"kotlin": {"level": "Mid-level", "years": 2}}
    
    res = calc.matcher.match_skill(req, user_skill_map, user_skills_list)
    print(f"Match Found: {res['match_found']}, Gap Type: {res['gap_type']}, Reason: {res['details'].get('reason')}")
    assert res['match_found'] == True

if __name__ == "__main__":
    try:
        test_seniority_ignoring()
        test_platform_matching()
        print("\nALL TESTS PASSED!")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
