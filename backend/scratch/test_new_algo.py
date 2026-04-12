import asyncio
import sys
import os

# Add the backend directory to sys.path for imports to work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.analysis_service.engine.advanced_gap_engine import AdvancedGapEngine

async def test_algorithm():
    engine = AdvancedGapEngine()
    
    cv_skills = ["Python", "Node.js", "React", "PostgreSQL", "AWS"]
    
    jd_requirements = [
        {"skill_name": "Python", "is_mandatory": True},        # Tier 1 - Exact
        {"skill_name": "nodejs", "is_mandatory": True},        # Tier 1 - Alias
        {"skill_name": "TypeScript", "is_mandatory": True},    # Missing -> Tier 2 (Semantic)
        {"skill_name": "Docker", "is_mandatory": False},       # Missing
        {"skill_name": "Postgres", "is_mandatory": False},     # Tier 1 - Alias
    ]
    
    print("\n--- Testing 3-Tier Algorithm ---")
    print(f"CV Skills: {cv_skills}")
    print(f"JD Requirements: {[r['skill_name'] for r in jd_requirements]}")
    
    result = await engine.calculate_match(cv_skills, jd_requirements)
    
    print("\n--- RESULTS ---")
    print(f"Overall Match Pct: {result['overall_match_pct']}%")
    print(f"Must-have Score: {result['must_have_score']}%")
    print(f"Nice-to-have Score: {result['nice_to_have_score']}%")
    
    print("\nBreakdown:")
    for cat in ["met", "partial", "gap"]:
        print(f"  {cat.upper()}: {[s['skill'] for s in result['breakdown'][cat]]}")

    # Verify weighting logic
    # Must: Python (1.0), nodejs (1.0), TypeScript (0.0?) -> avg = 2/3 = 66.6
    # Nice: Docker (0.0), Postgres (1.0) -> avg = 1/2 = 50.0
    # Total = 66.6 * 0.7 + 50.0 * 0.3 = 46.62 + 15 = 61.62
    
if __name__ == "__main__":
    asyncio.run(test_algorithm())
