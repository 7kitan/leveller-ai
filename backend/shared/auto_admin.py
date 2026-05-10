"""
Auto-create admin user on first startup if not exists.
Safe to run multiple times (idempotent).
"""

import os
import uuid
import logging
from sqlalchemy.orm import Session

logger = logging.getLogger("auto_admin")

def ensure_admin_exists(db: Session):
    """
    Ensure at least one admin user exists in the database.
    Creates default admin if none found.
    
    Safe to call on every startup - only creates if missing.
    """
    try:
        from shared.models import User, UserRole
        from shared.auth_utils import get_password_hash
        
        # Check if any admin exists
        admin_count = db.query(User).filter(User.role == UserRole.ADMIN).count()
        
        if admin_count > 0:
            logger.info(f"✅ Admin user(s) already exist ({admin_count} found)")
            return True
        
        # No admin found - create default admin
        admin_email = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@leveller.ai")
        admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "Admin@123")
        admin_name = os.getenv("DEFAULT_ADMIN_NAME", "System Administrator")
        
        logger.info(f"🔧 No admin found. Creating default admin: {admin_email}")
        
        new_admin = User(
            id=uuid.uuid4(),
            email=admin_email,
            username=admin_email.split('@')[0],  # Use email prefix as username
            hashed_password=get_password_hash(admin_password),
            full_name=admin_name,
            role=UserRole.ADMIN,
            is_active=True
        )
        
        db.add(new_admin)
        db.commit()
        
        logger.info(f"✅ Default admin created successfully")
        logger.info(f"   Email: {admin_email}")
        logger.info(f"   Password: {admin_password}")
        logger.info(f"   ⚠️  CHANGE PASSWORD AFTER FIRST LOGIN!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create admin: {e}")
        db.rollback()
        return False
