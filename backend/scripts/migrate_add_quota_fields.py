import sys
import os

# Add backend to path to import shared
sys.path.append(os.getcwd())

from shared.database import engine
from sqlalchemy import text

def migrate():
    with engine.connect() as conn:
        print("Starting migration: Quota and Security fields for Users...")
        
        # Fields to add to users table
        fields = [
            ("daily_token_limit", "INTEGER DEFAULT 0"),
            ("daily_analysis_limit", "INTEGER DEFAULT 0"),
            ("is_flagged", "BOOLEAN DEFAULT FALSE"),
            ("registration_ip", "VARCHAR(50)"),
            ("registration_user_agent", "TEXT"),
            ("last_login_ip", "VARCHAR(50)"),
            ("last_login_user_agent", "TEXT")
        ]

        for col_name, col_type in fields:
            try:
                # Mỗi câu lệnh trong một block commit riêng để tránh hỏng transaction
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
                conn.commit()
                print(f"  [+] Added column '{col_name}' to users table.")
            except Exception as e:
                conn.rollback() # Rollback để có thể tiếp tục với cột khác
                if "already exists" in str(e).lower():
                    print(f"  [.] Column '{col_name}' already exists in users table.")
                else:
                    print(f"  [!] Error adding '{col_name}': {e}")
        
        conn.commit()
        print("Migration finished successfully.")

if __name__ == "__main__":
    migrate()
