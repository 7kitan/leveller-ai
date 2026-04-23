import sys
import os

# Add backend to path to import shared
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text, inspect
from shared.database import engine, Base
# Import all models to ensure Base.metadata is fully populated
from shared import models

def migrate():
    print("--- Starting Database Schema Update (v3 -> v4) ---")
    
    # 0. Initialize Extensions
    print("Initializing extensions...")
    with engine.connect() as conn:
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            print("  [OK] pgvector extension ready")
        except Exception as e:
            print(f"  [WARN] Could not create extension: {e}")

    # 1. Create missing tables
    print("\nCreating missing tables...")
    Base.metadata.create_all(bind=engine)
    print("  Done creating tables.")
    
    # 2. Define schema updates for existing tables
    updates = {
        "users": [
            ("market_fit_score", "FLOAT DEFAULT 0.0"),
            ("market_fit_last_updated", "TIMESTAMP WITH TIME ZONE"),
            ("market_fit_data", "JSON"),
            ("last_analysis_id", "UUID REFERENCES user_analysis(id) ON DELETE SET NULL")
        ],
        "youtube_courses": [
            ("expires_at", "TIMESTAMP WITH TIME ZONE"),
            ("last_verified_at", "TIMESTAMP WITH TIME ZONE")
        ],
        "user_cvs": [
            ("is_verified", "BOOLEAN DEFAULT FALSE")
        ],
        "jobs": [
            ("has_insurance", "BOOLEAN DEFAULT FALSE"),
            ("has_13th_month", "BOOLEAN DEFAULT FALSE"),
            ("remote_friendly", "BOOLEAN DEFAULT FALSE"),
            ("extracted_requirements_json", "JSON")
        ]
    }
    
    inspector = inspect(engine)
    
    with engine.connect() as conn:
        for table_name, columns in updates.items():
            print(f"\nChecking '{table_name}' table...")
            
            # Get existing columns
            existing_columns = [c['name'] for c in inspector.get_columns(table_name)]
            
            for col_name, col_type in columns:
                if col_name in existing_columns:
                    print(f"  Column '{col_name}' already exists in '{table_name}'")
                    continue
                
                try:
                    print(f"  Adding column '{col_name}' to '{table_name}'...")
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}"))
                    conn.commit()
                    print(f"    [OK] Added '{col_name}'")
                except Exception as e:
                    conn.rollback()
                    print(f"    [ERROR] adding '{col_name}': {e}")
        
        # 3. Add unique constraint to courses if missing
        print("\nChecking 'courses' constraints...")
        try:
            # Check if constraint exists (approximate check via catch)
            conn.execute(text("ALTER TABLE courses ADD CONSTRAINT uq_course_source UNIQUE (source_platform, source_id)"))
            conn.commit()
            print("  [OK] Added unique constraint 'uq_course_source' to 'courses'")
        except Exception as e:
            conn.rollback()
            if "already exists" in str(e).lower():
                print("  Constraint 'uq_course_source' already exists")
            else:
                print(f"  [ERROR] adding constraint: {e}")
        
        print("\n--- Migration Completed ---")

if __name__ == "__main__":
    migrate()
