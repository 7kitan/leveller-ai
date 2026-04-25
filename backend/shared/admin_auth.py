"""
Secure Admin Authorization Module
Provides cryptographically secure admin verification without relying on HTTP headers.
"""
import logging
from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session
from shared.database import get_db
from shared.models import User, UserRole
from shared.auth_utils import decode_access_token
import uuid

logger = logging.getLogger(__name__)


def get_current_user_from_token(request: Request, db: Session = Depends(get_db)) -> User:
    """
    Extract and verify user from JWT token.
    Does NOT trust X-User-ID header - re-verifies from token.
    
    Returns:
        User object from database
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    try:
        token = auth_header.split(" ", 1)[1].strip()
        # Remove quotes if present
        if (token.startswith('"') and token.endswith('"')) or (token.startswith("'") and token.endswith("'")):
            token = token[1:-1]
        
        # Decode JWT token
        payload = decode_access_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        if "sub" not in payload:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        user_id_str = payload["sub"]
        try:
            user_uuid = uuid.UUID(user_id_str) if isinstance(user_id_str, str) else user_id_str
        except (ValueError, TypeError):
            raise HTTPException(status_code=401, detail="Invalid user ID in token")
        
        # Query database for user
        user = db.query(User).filter(User.id == user_uuid).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        if not user.is_active:
            raise HTTPException(status_code=403, detail="User account is disabled")
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting user from token: {str(e)}")
        raise HTTPException(status_code=401, detail="Token verification failed")


def get_current_admin_user(
    request: Request, 
    db: Session = Depends(get_db)
) -> User:
    """
    Secure admin verification dependency.
    
    Verifies admin status by:
    1. Extracting JWT token from Authorization header
    2. Decoding JWT and checking role claim
    3. Re-verifying against database
    
    Does NOT trust X-Is-Admin header alone.
    
    Returns:
        User object if user is admin
        
    Raises:
        HTTPException 403: If user is not admin
        HTTPException 401: If token is invalid
    """
    user = get_current_user_from_token(request, db)
    
    # Verify admin status from database (source of truth)
    if user.role != UserRole.ADMIN:
        logger.warning(f"Non-admin user {user.email} attempted to access admin endpoint")
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    return user


def require_admin(request: Request, db: Session = Depends(get_db)) -> bool:
    """
    Simple boolean check for admin status.
    Use this as a dependency when you just need to verify admin access.
    
    Returns:
        True if user is admin
        
    Raises:
        HTTPException: If not admin or invalid token
    """
    get_current_admin_user(request, db)
    return True


def get_user_id_from_header(request: Request) -> str:
    """
    Legacy function for backward compatibility.
    Extracts user ID from X-User-ID header (set by gateway).
    
    WARNING: This should only be used for non-admin endpoints.
    For admin endpoints, use get_current_admin_user() instead.
    
    Returns:
        User ID string
        
    Raises:
        HTTPException: If header is missing
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user_id
