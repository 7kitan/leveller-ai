import sys
import os
import uuid
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

def create_test_users(count=10):
    db = SessionLocal()
    try:
        password = "Password@123"
        hashed_pw = get_password_hash(password)
        
        for i in range(1, count + 1):
            email = f"testuser_{i}@lumix.ai"
            user = db.query(User).filter(User.email == email).first()
            if not user:
                print(f"Creating user {email}...")
                user = User(
                    id=uuid.uuid4(),
                    email=email,
                    username=f"testuser_{i}",
                    hashed_password=hashed_pw,
                    full_name=f"Test User {i}",
                    role=UserRole.USER,
                    is_active=True
                )
                db.add(user)
            else:
                user.hashed_password = hashed_pw
                print(f"User {email} already exists, updated password.")
        
        db.commit()
        print(f"Successfully created/updated {count} test users.")
    finally:
        db.close()

if __name__ == "__main__":
    create_test_users(10)
