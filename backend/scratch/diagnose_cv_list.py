import sys
import os
import uuid
import logging

# Thêm đường dẫn backend vào sys.path để import shared
sys.path.append(os.getcwd())

from shared.database import SessionLocal
from shared.models import UserCV, User

def diagnose():
    db = SessionLocal()
    user_id_str = "4c34a8c6-cd3c-4c72-94cf-bf4fb9ad352c"
    
    try:
        print(f"DEBUG: Diagnosing for user_id={user_id_str}")
        user_id = uuid.UUID(user_id_str)
        
        cvs = (
            db.query(UserCV)
            .filter(UserCV.user_id == user_id)
            .order_by(UserCV.created_at.desc())
            .all()
        )
        
        print(f"DEBUG: Found {len(cvs)} CVs")
        
        results = []
        for cv in cvs:
            item = {
                "id": str(cv.id),
                "file_name": cv.full_name or f"CV_{str(cv.id)[:8]}",
                "full_name": cv.full_name,
                "status": cv.status,
                "error_message": cv.error_message,
                "created_at": str(cv.created_at), # Thử convert string để xem có lỗi serialization không
            }
            results.append(item)
            print(f"DEBUG: Parsed CV {cv.id}")
            
        print("DEBUG: All CVs parsed successfully")
        print(f"RESULTS: {results}")

    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    diagnose()
