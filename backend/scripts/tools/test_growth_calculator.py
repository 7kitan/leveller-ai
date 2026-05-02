"""
Test growth_calculator with real DB data.
"""
import sys
import io
sys.path.insert(0, 'backend')

# Fix Windows console encoding for Vietnamese
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from shared.database import SessionLocal
from shared.models import Job
from services.analysis_service.growth_calculator import calculate_skill_impact, calculate_market_sentiment

def test_calculator():
    db = SessionLocal()
    try:
        # Find a job with skill requirements
        job = db.query(Job).filter(Job.extracted_requirements_json.isnot(None)).first()
        if not job:
            print("No jobs with requirements found!")
            return
        
        print(f"Testing with job: {job.title_raw}")
        print(f"Job ID: {job.id}")
        print("-" * 80)
        
        # Extract skills from extracted_requirements_json
        requirements = job.extracted_requirements_json
        if not requirements:
            print("No requirements found!")
            return
        
        print(f"\nFound {len(requirements)} requirement groups/skills")
        
        # Create mock skill_gaps for testing
        skill_gaps = []
        for req in requirements[:5]:  # Test first 5
            if req.get("type") == "skill":
                skill_gaps.append({
                    "skill": req.get("skill"),
                    "severity": "high" if req.get("is_primary") else "medium",
                    "estimated_months": 3
                })
            elif req.get("type") == "group":
                # Take first skill from group
                skills = req.get("skills", [])
                if skills:
                    skill_gaps.append({
                        "skill": skills[0].get("skill"),
                        "severity": "high" if req.get("is_primary") else "medium",
                        "estimated_months": 3
                    })
        
        print(f"\nTesting with {len(skill_gaps)} skill gaps:")
        for gap in skill_gaps:
            print(f"  - {gap['skill']} ({gap['severity']})")
        
        # Test calculate_skill_impact
        print("\n" + "=" * 80)
        print("Testing calculate_skill_impact()...")
        print("=" * 80)
        
        current_match = 65.0
        potential_match, salary_growth, enriched_gaps = calculate_skill_impact(
            skill_gaps=skill_gaps,
            job_id=str(job.id),
            current_match_pct=current_match,
            db=db
        )
        
        print(f"\nResults:")
        print(f"  Current Match: {current_match}%")
        print(f"  Potential Match: {potential_match}%")
        print(f"  Salary Growth: {salary_growth}%")
        
        print(f"\nEnriched Skill Gaps:")
        for gap in enriched_gaps:
            print(f"  {gap['skill']}:")
            print(f"    Match Impact: +{gap.get('match_impact', 0)}%")
            print(f"    Salary Impact: +{gap.get('salary_impact', 0)}%")
            print(f"    Market Demand: {gap.get('market_demand', 'N/A')}")
        
        # Test market sentiment
        print("\n" + "=" * 80)
        print("Testing calculate_market_sentiment()...")
        print("=" * 80)
        
        sentiment = calculate_market_sentiment(skill_gaps, db)
        print(f"Market Sentiment: {sentiment}")
        
        print("\n" + "=" * 80)
        print("Growth Calculator Test PASSED!")
        print("=" * 80)
        
    except Exception as e:
        print(f"Test FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_calculator()
