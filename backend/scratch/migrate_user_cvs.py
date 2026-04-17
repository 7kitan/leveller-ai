import sys
import os
from sqlalchemy import text

# Add backend to path
sys.path.append(os.getcwd())

from shared.database import engine

def migrate():
    print("DEBUG: Starting migration for user_cvs table...")
    try:
        with engine.connect() as conn:
            # PostgreSQL syntax to add columns IF NOT EXISTS
            print("DEBUG: Adding cv_parsed_json...")
            conn.execute(text("ALTER TABLE user_cvs ADD COLUMN IF NOT EXISTS cv_parsed_json JSON;"))
            
            print("DEBUG: Adding cv_parsed_at...")
            conn.execute(text("ALTER TABLE user_cvs ADD COLUMN IF NOT EXISTS cv_parsed_at TIMESTAMP WITH TIME ZONE;"))
            
            conn.commit()
            print("SUCCESS: Schema updated successfully.")
    except Exception as e:
        print(f"FAILED: Migration failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    migrate()
