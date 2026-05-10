import sys
import os
import json
import uuid
import redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from shared.models import User, UserRole
from shared.auth_utils import get_password_hash

# Direct connection for host machine (not Docker network)
POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "1234567891abcdef"
POSTGRES_DB = "career_advisor"
POSTGRES_HOST = "localhost"
POSTGRES_PORT = "5432"

SQLALCHEMY_DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def check_and_create_user():
    db = SessionLocal()
    try:
        # 1. Check admin@leveller.ai
        email = "admin@leveller.ai"
        password = "Admin@123"
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            print(f"Creating user {email}...")
            user = User(
                id=uuid.uuid4(),
                email=email,
                username="admin",
                hashed_password=get_password_hash(password),
                full_name="System Administrator",
                role=UserRole.ADMIN,
                is_active=True
            )
            db.add(user)
            db.commit()
            print("User created.")
        else:
            print(f"User {email} exists.")
            # Ensure password is correct for our test
            user.hashed_password = get_password_hash(password)
            db.commit()
            print("Password updated to Admin@123.")

        # 2. Clear Redis lockout
        try:
            # Note: Redis might have a password too based on backend/.env
            REDIS_PASSWORD = "1234567891abcdef"
            r = redis.Redis(host='localhost', port=6379, db=0, password=REDIS_PASSWORD)
            # Clear lockout and attempts
            keys_to_delete = [
                f"lockout:127.0.0.1",
                f"login_attempts:{email}",
                f"login_attempts_ip:127.0.0.1"
            ]
            for key in keys_to_delete:
                if r.delete(key):
                    print(f"Cleared Redis key: {key}")
                else:
                    print(f"Key not found or already cleared: {key}")
        except Exception as e:
            print(f"Redis clear failed: {e}")

    finally:
        db.close()

if __name__ == "__main__":
    check_and_create_user()
