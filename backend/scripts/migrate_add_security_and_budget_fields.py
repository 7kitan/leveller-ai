import sys
import os

# Thêm đường dẫn tới backend để có thể import shared
sys.path.append(os.getcwd())

from shared.database import engine
from sqlalchemy import text

def migrate():
    with engine.connect() as conn:
        print("Starting migration: Security and Budget fields...")
        
        # 1. Thêm các trường bảo mật cho bảng users
        security_fields = [
            ("registration_ip", "VARCHAR(50)"),
            ("registration_user_agent", "TEXT"),
            ("last_login_ip", "VARCHAR(50)"),
            ("last_login_user_agent", "TEXT")
        ]
        
        for col_name, col_type in security_fields:
            try:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
                print(f"  [+] Added column '{col_name}' to users table.")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"  [.] Column '{col_name}' already exists in users table.")
                else:
                    print(f"  [!] Error adding '{col_name}': {e}")

        # 2. Đảm bảo bảng system_settings đã có (Base.metadata.create_all thường lo việc này)
        # 3. Seeding mặc định cho các settings mới (optional, config_manager handles defaults)
        
        conn.commit()
        print("Migration finished successfully.")

if __name__ == "__main__":
    migrate()
