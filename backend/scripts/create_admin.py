import os
import sys
import uuid
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to sys.path to import shared modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.models import User, UserRole
from shared.auth_utils import get_password_hash

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("create_admin")

# DB Setup from environment variables
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "career_advisor")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")  # Default to 'db' for Docker, can override for local
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

logger.info(f"Connecting to database at {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_admin(email, password, full_name="System Admin"):
    email = email.lower().strip()
    db = SessionLocal()
    try:
        # Check if user exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            logger.info(f"User {email} already exists. Updating to admin...")
            existing_user.role = UserRole.ADMIN
            existing_user.hashed_password = get_password_hash(password)
            db.commit()
            logger.info(f"Successfully updated {email} to Admin.")
            return

        # Create new admin
        new_user = User(
            id=uuid.uuid4(),
            email=email,
            hashed_password=get_password_hash(password),
            full_name=full_name,
            role=UserRole.ADMIN,
            is_active=True
        )
        db.add(new_user)
        db.commit()
        logger.info(f"--- [SUCCESS] Admin created: {email} ---")
        
    except Exception as e:
        logger.error(f"Error creating admin: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Create an administrative user.")
    parser.add_argument("--email", default="admin@Leveller.ai", help="Admin email")
    parser.add_argument("--password", default="Admin@123", help="Admin password")
    parser.add_argument("--name", default="System Admin", help="Admin full name")
    
    args = parser.parse_args()
    create_admin(args.email, args.password, args.name)
