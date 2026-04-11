import sys
import os

# Thêm thư mục backend vào path để import shared
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared.database import SessionLocal
from shared.models import User
from shared.auth_utils import get_password_hash
import uuid

def seed_admin():
    db = SessionLocal()
    try:
        admin_email = "admin@advisor.com"
        admin_pass = "admin123"
        
        # Kiểm tra xem admin đã tồn tại chưa
        existing_admin = db.query(User).filter(User.email == admin_email).first()
        if existing_admin:
            print(f"User {admin_email} already exists. Promoting to admin...")
            existing_admin.is_admin = True
            db.commit()
            print("Successfully promoted existing user to Admin.")
            return

        # Tạo admin mới
        new_admin = User(
            id=uuid.uuid4(),
            email=admin_email,
            hashed_password=get_password_hash(admin_pass),
            full_name="System Administrator",
            is_admin=True,
            is_active=True
        )
        
        db.add(new_admin)
        db.commit()
        print(f"Successfully created Admin user: {admin_email}")
        print(f"Password: {admin_pass}")
        
    except Exception as e:
        print(f"Error seeding admin: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_admin()
