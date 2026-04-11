import os
import sys
import uuid

# Add backend to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if backend_path not in sys.path:
    sys.path.append(backend_path)

from sqlalchemy.orm import joinedload
from shared.database import SessionLocal
from shared.models import JobSkillRequirement, Skill, Job

def verify_relationships():
    db = SessionLocal()
    try:
        print("--- Testing JobSkillRequirement -> Skill relationship ---")
        # Try to query with joinedload
        req = db.query(JobSkillRequirement).options(joinedload(JobSkillRequirement.skill)).first()
        
        if req:
            print(f"Successfully loaded requirement ID: {req.id}")
            if req.skill:
                print(f"Successfully accessed skill: {req.skill.name}")
            else:
                print("Requirement found but has no associated skill (skill_id might be null or invalid).")
        else:
            print("No JobSkillRequirement records found to test.")
            
        print("\n--- Testing Job -> JobSkillRequirement relationship ---")
        job = db.query(Job).options(joinedload(Job.skills_required)).first()
        if job:
            print(f"Successfully loaded job: {job.title_raw[:50]}...")
            print(f"Number of skills required: {len(job.skills_required)}")
        else:
            print("No Job records found to test.")

    except Exception as e:
        print(f"VERIFICATION FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    # Add backend to sys.path
    backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.append(backend_path)
    verify_relationships()
