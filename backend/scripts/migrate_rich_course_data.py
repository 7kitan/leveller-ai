import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Add parent directory to path to import shared
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

load_dotenv()

POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "career_advisor")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

SQLALCHEMY_DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
engine = create_engine(SQLALCHEMY_DATABASE_URL)

def migrate():
    print(f"Connecting to {POSTGRES_DB} at {POSTGRES_HOST}...")
    
    with engine.connect() as conn:
        print("--- Migrating USERS table ---")
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(100);"))
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_user_username ON users(username);"))
            print("[OK] Added username column to users")
        except Exception as e:
            print(f"[ERROR] Users migration: {e}")

        print("\n--- Migrating COURSES table ---")
        columns_to_add = [
            ("source_platform", "VARCHAR(100)"),
            ("source_id", "VARCHAR(255)"),
            ("external_uuid", "VARCHAR(100)"),
            ("languages", "JSON"),
            ("duration_raw", "VARCHAR(100)"),
            ("skills_raw", "JSON"),
            ("tools_raw", "JSON"),
            ("outcomes", "JSON"),
            ("modules", "JSON"),
        ]
        
        for col_name, col_type in columns_to_add:
            try:
                conn.execute(text(f"ALTER TABLE courses ADD COLUMN IF NOT EXISTS {col_name} {col_type};"))
                print(f"[OK] Added {col_name} to courses")
            except Exception as e:
                print(f"[ERROR] Adding {col_name}: {e}")

        # Add unique constraint index
        try:
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_course_source_idx ON courses(source_platform, source_id);"))
            print("[OK] Added unique index uq_course_source_idx to courses")
        except Exception as e:
            print(f"[ERROR] Adding unique index: {e}")

        conn.commit()
        print("\nMigration completed successfully!")

if __name__ == "__main__":
    migrate()
