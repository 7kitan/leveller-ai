import uuid
import sys
import os

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), "backend")))

from shared.database import SessionLocal, engine
from shared.models import Skill, UserSkillProfile, UserCV
from sqlalchemy.orm import Session

def test_transaction_behavior():
    db = SessionLocal()
    cv_id = uuid.uuid4()
    
    try:
        # 1. Create a dummy CV
        cv = UserCV(id=cv_id, status="processing")
        db.add(cv)
        db.commit()
        print(f"Created CV {cv_id}")

        # 2. Simulate the skill upsert with a failure
        # We'll try to insert a skill that violates a constraint (if any) or just force an error
        
        # First, ensure a skill exists
        skill_name = "Python_" + str(uuid.uuid4())[:8]
        s1 = Skill(id=uuid.uuid4(), name=skill_name)
        db.add(s1)
        db.commit()
        print(f"Created Skill {skill_name}")

        # Now start a transaction
        try:
            # Simulate the loop in persist_cv_data_node
            # Suppose we try to add a duplicate skill name which should fail at flush
            s2 = Skill(id=uuid.uuid4(), name=skill_name) # Duplicate name
            db.add(s2)
            db.flush() # This will throw IntegrityError
        except Exception as e:
            print(f"Caught expected error: {type(e).__name__}")
            db.rollback()
            print("Rollback performed.")

        # 3. Verify session is usable again
        # This was the failing part in the old code -- if no rollback was done, this would fail
        try:
            profiles = db.query(UserSkillProfile).filter(UserSkillProfile.cv_id == cv_id).all()
            print(f"Query successful! Found {len(profiles)} profiles.")
        except Exception as e:
            print(f"Query FAILED with: {e}")
            
    finally:
        # Cleanup
        db.close()
        # Clean up DB if needed, but for scratch we just test the session state
        print("Test complete.")

if __name__ == "__main__":
    test_transaction_behavior()
