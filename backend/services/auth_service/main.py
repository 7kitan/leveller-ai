from fastapi import FastAPI, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from shared.database import get_db, engine, Base
import shared.models # Ensure all models are registered
from shared.models import User, UserRole
# Ensure tables are created
# Base.metadata.create_all(bind=engine) - Moved to startup event
from shared.auth_utils import get_password_hash, verify_password, create_access_token, hash_token, decode_access_token, ACCESS_TOKEN_EXPIRE_SECONDS
from shared.config_utils import config_manager
from shared.redis_client import auth_cache
from shared.email_utils import send_password_reset_email
from shared.schemas import PaginatedResponse
from shared.system_logger import system_logger
from pydantic import BaseModel, EmailStr, Field
import json
import logging
from shared.logging_utils import setup_logger
import uuid
import secrets
import os
import httpx
from typing import Optional, List
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logger = setup_logger("auth_service", log_file="auth.log")

# Google reCAPTCHA Secret Key
RECAPTCHA_SECRET_KEY = os.getenv("GOOGLE_RECAPTCHA_SECRET_KEY")

async def verify_google_captcha(token: str):
    """Verify Google reCAPTCHA v2/v3 token."""
    if not RECAPTCHA_SECRET_KEY:
        logger.error("SECURITY ALERT: GOOGLE_RECAPTCHA_SECRET_KEY not set. Cannot verify captcha. Failing securely.")
        return False
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={
                "secret": RECAPTCHA_SECRET_KEY,
                "response": token
            }
        )
        result = response.json()
        return result.get("success", False)

class UserCreate(BaseModel):
    email: EmailStr = Field(..., max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=255)  # Required for registration
    captcha_token: Optional[str] = None

class AdminUserCreate(UserCreate):
    role: Optional[str] = UserRole.USER

class UserLogin(BaseModel):
    email: EmailStr = Field(..., max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    captcha_token: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    full_name: Optional[str] = None

class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class AdminUserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    is_flagged: bool
    daily_token_limit: int
    today_usage: Optional[int] = 0
    created_at: Optional[str] # Will be stringified

class AdminUserUpdate(BaseModel):
    email: Optional[EmailStr] = Field(None, max_length=255)
    password: Optional[str] = Field(None, min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=255)
    role: Optional[str] = None
    is_active: Optional[bool] = None
    is_flagged: Optional[bool] = None
    daily_token_limit: Optional[int] = None

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=255)
    old_password: Optional[str] = Field(None, max_length=128)
    password: Optional[str] = Field(None, min_length=8, max_length=128)

class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    captcha_token: Optional[str] = None

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)

app = FastAPI(title="Auth Service")

# Initialize Limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- Password Reset Endpoints ---

@app.post("/auth/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(req: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    # Verify Captcha
    if not req.captcha_token:
        raise HTTPException(status_code=400, detail="Captcha required", headers={"X-Requires-Captcha": "true"})
    
    is_valid = await verify_google_captcha(req.captcha_token)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid Captcha. Please try again.")

    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        # Avoid user enumeration: still return success but don't do anything
        return {"detail": "If this email is registered, a reset link will be sent."}
    
    # SECURITY FIX: Generate cryptographically secure token (not UUID)
    reset_token = secrets.token_urlsafe(32)
    reset_key = f"pwd_reset:{reset_token}"
    
    # Store in Redis for 1 hour
    auth_cache.setex(reset_key, 3600, str(user.id))
    
    # SECURITY FIX: Never log password reset links or tokens
    reset_link = f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/auth/reset-password?token={reset_token}"
    logger.info(f"Password reset requested for user: {user.id}")  # Log user ID only, not email or link
    
    # Send email
    send_password_reset_email(user.email, reset_link)
    
    return {"detail": "If this email is registered, a reset link will be sent."}

@app.post("/auth/reset-password")
async def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    reset_key = f"pwd_reset:{req.token}"
    user_id = auth_cache.get(reset_key)
    
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User no longer exists")
        
    # Update password
    user.hashed_password = get_password_hash(req.new_password)
    db.commit()
    
    # Invalidate token
    auth_cache.delete(reset_key)
    
    # Revoke all current sessions for security
    session_pointer = f"user_session:{user.id}"
    old_token_key = auth_cache.get(session_pointer)
    if old_token_key:
        auth_cache.delete(old_token_key)
        auth_cache.delete(session_pointer)

    # LOG: Password reset (security event)
    system_logger.info(
        "Auth",
        f"Password reset: {user.email}",
        {
            "user_id": str(user.id),
            "sessions_revoked": bool(old_token_key)
        }
    )

    return {"detail": "Password has been reset successfully. Please login with your new password."}

@app.on_event("startup")
async def startup_event():
    from shared.database import init_db
    init_db()

def is_admin(request: Request) -> bool:
    role = request.headers.get("X-User-Role")
    return role == UserRole.ADMIN

@app.post("/auth/register", response_model=AuthResponse)
@limiter.limit("5/day")
async def register(request: Request, user_in: UserCreate, db: Session = Depends(get_db)):
    # 1. Check registration limit per IP
    ip_addr = request.client.host if request.client else "unknown"
    reg_key = f"reg_attempts:{ip_addr}"
    reg_count = auth_cache.incr_with_expire(reg_key, 86400)
    if reg_count > 5:
        raise HTTPException(status_code=429, detail="Too many registrations from this IP. Please try again in 24 hours.")

    # 2. Always require Captcha for Register
    if not user_in.captcha_token:
        raise HTTPException(status_code=400, detail="Captcha required for registration", headers={"X-Requires-Captcha": "true"})
    
    is_valid = await verify_google_captcha(user_in.captcha_token)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid Captcha. Please try again.")

    db_user = db.query(User).filter(User.email == user_in.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=UserRole.USER,
        registration_ip=ip_addr,
        registration_user_agent=request.headers.get("User-Agent"),
        last_login_ip=ip_addr,
        last_login_user_agent=request.headers.get("User-Agent")
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Include is_admin in JWT token for security
    access_token = create_access_token(data={
        "sub": str(new_user.id), 
        "email": new_user.email,
        "role": new_user.role
    })
    
    user_data = {
        "id": str(new_user.id), 
        "email": new_user.email, 
        "role": new_user.role,
        "full_name": new_user.full_name
    }
    token_key = f"token:{hash_token(access_token)}"
    session_pointer = f"user_session:{new_user.id}"

    old_token_key = auth_cache.get(session_pointer)
    if old_token_key:
        auth_cache.delete(old_token_key)

    auth_cache.setex(token_key, ACCESS_TOKEN_EXPIRE_SECONDS, json.dumps(user_data))
    auth_cache.setex(session_pointer, ACCESS_TOKEN_EXPIRE_SECONDS, token_key)

    # LOG: User registration (audit trail)
    system_logger.info(
        "Auth",
        f"User registered: {new_user.email}",
        {
            "user_id": str(new_user.id),
            "full_name": new_user.full_name,
            "ip": ip_addr,
            "user_agent": request.headers.get("User-Agent")
        }
    )

    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": user_data
    }

@app.get("/auth/captcha-status")
@limiter.limit("10/minute")
async def get_captcha_status(request: Request):
    """Check if the current IP requires a captcha based on previous failed attempts."""
    ip_addr = request.client.host if request.client else "unknown"
    ip_attempt_key = f"login_attempts_ip:{ip_addr}"
    
    attempts = auth_cache.get(ip_attempt_key)
    # If there is at least 1 failed attempt, require captcha for the next one
    requires_captcha = int(attempts) >= 1 if attempts else False
    
    return {"requires_captcha": requires_captcha}

@app.post("/auth/login")
@limiter.limit("20/minute")
async def login(request: Request, user_in: UserLogin, db: Session = Depends(get_db)):
    ip_addr = request.client.host if request.client else "unknown"
    lockout_key = f"lockout:{ip_addr}"
    
    if auth_cache.exists(lockout_key):
        raise HTTPException(status_code=403, detail="Account locked due to too many failed attempts. Please try again in 24 hours.")

    attempt_key = f"login_attempts:{user_in.email}"
    ip_attempt_key = f"login_attempts_ip:{ip_addr}"
    
    # SECURITY: Atomic increment first to prevent Race Condition
    email_attempts = auth_cache.incr_with_expire(attempt_key, 3600)
    ip_attempts = auth_cache.incr_with_expire(ip_attempt_key, 3600)
    max_attempts = max(email_attempts, ip_attempts)

    # SECURITY FIX: Lockout check (reduced from 10 to 5 attempts)
    if max_attempts >= 5:
        auth_cache.setex(lockout_key, 86400, "locked")
        raise HTTPException(status_code=403, detail="Too many failed attempts. Your IP has been locked for 24 hours.")

    # SECURITY FIX: Check for Captcha (from 2nd attempt for better protection)
    if max_attempts >= 2:
        if not user_in.captcha_token:
            raise HTTPException(status_code=400, detail="Captcha required", headers={"X-Requires-Captcha": "true"})
        
        is_valid = await verify_google_captcha(user_in.captcha_token)
        if not is_valid:
            raise HTTPException(status_code=400, detail="Invalid Captcha. Please try again.")

    user = db.query(User).filter(User.email == user_in.email).first()

    if not user or not verify_password(user_in.password, user.hashed_password):
        headers = {"X-Attempts-Left": str(5 - max_attempts)}
        # If this is the 1st failure, the next attempt will be the 2nd one (max_attempts >= 2), 
        # so we notify the client to show captcha now to avoid a "wasted" attempt.
        if max_attempts >= 1:
            headers["X-Requires-Captcha"] = "true"
        
        # LOG: Failed login attempt (security monitoring)
        system_logger.warning(
            "Auth",
            f"Failed login attempt: {user_in.email}",
            {
                "email": user_in.email,
                "ip": ip_addr,
                "attempts": max_attempts,
                "reason": "invalid_credentials"
            }
        )
            
        raise HTTPException(
            status_code=401, 
            detail="Incorrect email or password",
            headers=headers
        )
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled. Please contact administrator.")

    # SECURITY: Check maintenance mode BEFORE creating token
    # This prevents token creation for non-admin users during maintenance
    try:
        mode = auth_cache.get("system:MAINTENANCE_MODE")
        duration = auth_cache.get("system:MAINTENANCE_DURATION")
        
        if mode:
            # Handle both bytes and string (redis-py version compatibility)
            mode_str = mode.decode('utf-8') if isinstance(mode, bytes) else str(mode)
            duration_str = duration.decode('utf-8') if isinstance(duration, bytes) else str(duration) if duration else "Không xác định"
            
            if mode_str.lower() == 'true':
                # Maintenance mode is ON
                if user.role != UserRole.ADMIN:
                    # Non-admin users cannot login during maintenance
                    system_logger.warning(
                        "Auth",
                        f"Blocked non-admin login during maintenance: {user.email}",
                        {"user_id": str(user.id), "ip": ip_addr}
                    )
                    raise HTTPException(
                        status_code=503,
                        detail=f"Hệ thống đang bảo trì để nâng cấp. Thời gian dự kiến: {duration_str}. Chỉ admin mới có thể đăng nhập trong thời gian này."
                    )
                # Admin users can login during maintenance
                logger.info(f"Admin user {user.email} logging in during maintenance mode")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to check maintenance mode: {e}")
        # Fail-safe: allow login if Redis check fails

    # SECURITY FIX: Clear failed attempts on successful login
    auth_cache.delete(attempt_key)
    auth_cache.delete(ip_attempt_key)
    
    user.last_login_ip = ip_addr
    user.last_login_user_agent = request.headers.get("User-Agent")
    db.commit()
    db.refresh(user)
    
    # SECURITY FIX: Session Fixation Prevention - Generate new token after successful login
    # Include session version to allow invalidation of all sessions
    session_version = secrets.token_hex(8)
    
    # Include is_admin in JWT token for security
    access_token = create_access_token(data={
        "sub": str(user.id), 
        "email": user.email,
        "role": user.role,
        "session_version": session_version
    })
    
    user_data = {
        "id": str(user.id), 
        "email": user.email, 
        "role": user.role,
        "full_name": user.full_name,
        "session_version": session_version
    }
    token_key = f"token:{hash_token(access_token)}"
    session_pointer = f"user_session:{user.id}"

    # SECURITY FIX: Invalidate old session on new login (session fixation prevention)
    old_token_key = auth_cache.get(session_pointer)
    if old_token_key:
        auth_cache.delete(old_token_key)
        logger.info(f"Invalidated old session for user {user.id}")

    auth_cache.setex(token_key, ACCESS_TOKEN_EXPIRE_SECONDS, json.dumps(user_data))
    auth_cache.setex(session_pointer, ACCESS_TOKEN_EXPIRE_SECONDS, token_key)

    # LOG: Successful login (audit trail)
    system_logger.info(
        "Auth",
        f"User login: {user.email}",
        {
            "user_id": str(user.id),
            "ip": ip_addr,
            "user_agent": request.headers.get("User-Agent")
        }
    )

    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": user_data
    }


    if cached:
        user_data = json.loads(cached)
        return user_data
    
    # Cache miss -> Deep Verification (JWT Decode + DB Check)
    logger.info(f"DEBUG Auth: Cache miss for token. Performing deep verification...")
    payload = decode_access_token(token)
    if not payload:
        logger.error("DEBUG Auth: JWT decode failed or token expired.")
        raise HTTPException(status_code=401, detail="Invalid or expired token (JWT decode failed)")
        
    if "sub" not in payload:
        logger.error(f"DEBUG Auth: JWT payload missing 'sub' claim: {payload}")
        raise HTTPException(status_code=401, detail="Invalid token payload (missing sub)")

    try:
        user_id_str = payload["sub"]
        # Safe UUID conversion
        try:
            user_uuid = uuid.UUID(user_id_str) if isinstance(user_id_str, str) else user_id_str
        except (ValueError, TypeError):
            logger.error(f"DEBUG Auth: Invalid UUID format in JWT sub: {user_id_str}")
            raise HTTPException(status_code=401, detail="Invalid user ID format in token")

        user = db.query(User).filter(User.id == user_uuid).first()
        if not user:
            logger.error(f"DEBUG Auth: User {user_uuid} not found in database.")
            raise HTTPException(status_code=401, detail="User not found")
            
        if not user.is_active:
            logger.error(f"DEBUG Auth: User {user_uuid} is inactive.")
            raise HTTPException(status_code=401, detail="User found but inactive")
            
        # Re-cache user data for subsequent requests (if caching is enabled)
        user_data = {
            "id": str(user.id), 
            "email": user.email, 
            "role": user.role,
            "full_name": user.full_name
        }
        auth_cache.setex(token_key, ACCESS_TOKEN_EXPIRE_SECONDS, json.dumps(user_data))
        logger.info(f"DEBUG Auth: Deep verification successful for user {user.email}")
        
        return user_data
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"DEBUG Auth: Unexpected error during deep verification: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal error during verification")

@app.get("/auth/me", response_model=UserResponse)
def get_me(request: Request, db: Session = Depends(get_db)):
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="X-User-ID header missing")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "full_name": user.full_name
    }

@app.patch("/auth/profile", response_model=AdminUserResponse)
def patch_profile(request: Request, user_in: UserProfileUpdate, db: Session = Depends(get_db)):
    """User self-service: Cập nhật thông tin cá nhân (tên, mật khẩu)."""
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="X-User-ID header missing")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user_in.full_name is not None:
        user.full_name = user_in.full_name
    
    if user_in.password:
        if not user_in.old_password:
            raise HTTPException(status_code=400, detail="Mật khẩu hiện tại là bắt buộc để thay đổi mật khẩu")
        
        if not verify_password(user_in.old_password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không chính xác")
            
        user.hashed_password = get_password_hash(user_in.password)
        
    db.commit()
    db.refresh(user)
    
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "created_at": user.created_at.isoformat() if user.created_at else None
    }

@app.get("/auth/admin/users", response_model=PaginatedResponse[AdminUserResponse])
def admin_list_users(
    request: Request, 
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(None)
):
    """Admin only: Lấy danh sách toàn bộ người dùng với phân trang."""
    from shared.token_manager import get_user_daily_usage
    if not is_admin(request):
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    query = db.query(User)
    
    if q:
        query = query.filter(
            (User.email.ilike(f"%{q}%")) | (User.full_name.ilike(f"%{q}%"))
        )
    
    total = query.count()
    users = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    
    items = [
        {
            "id": str(u.id),
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "is_flagged": u.is_flagged if u.is_flagged is not None else False,
            "daily_token_limit": u.daily_token_limit if u.daily_token_limit is not None else 0,
            "today_usage": get_user_daily_usage(str(u.id), db),
            "created_at": u.created_at.isoformat() if u.created_at else None
        }
        for u in users
    ]
    
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "page": (offset // limit) + 1,
        "pages": (total + limit - 1) // limit
    }

@app.post("/auth/admin/users", response_model=AdminUserResponse)
def admin_create_user(request: Request, user_in: AdminUserCreate, db: Session = Depends(get_db)):
    """Admin only: Tạo người dùng mới."""
    if not is_admin(request):
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    new_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role or UserRole.USER
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "id": str(new_user.id),
        "email": new_user.email,
        "full_name": new_user.full_name,
        "role": new_user.role,
        "is_active": new_user.is_active,
        "is_flagged": False,
        "daily_token_limit": 0,
        "created_at": new_user.created_at.isoformat() if new_user.created_at else None
    }

@app.patch("/auth/admin/users/{user_id}", response_model=AdminUserResponse)
def admin_update_user(user_id: str, user_in: AdminUserUpdate, request: Request, db: Session = Depends(get_db)):
    """Admin only: Cập nhật thông tin người dùng."""
    if not is_admin(request):
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user_in.email:
        user.email = user_in.email
    if user_in.password:
        user.hashed_password = get_password_hash(user_in.password)
    if user_in.full_name is not None:
        user.full_name = user_in.full_name
    if user_in.role is not None:
        user.role = user_in.role
    if user_in.is_active is not None:
        user.is_active = user_in.is_active
        if not user.is_active:
            # Revoke active session if banned
            session_pointer = f"user_session:{user.id}"
            old_token_key = auth_cache.get(session_pointer)
            if old_token_key:
                logger.info(f"Revoking session for banned user {user.id}")
                auth_cache.delete(old_token_key)
                auth_cache.delete(session_pointer)
    
    if user_in.is_flagged is not None:
        user.is_flagged = user_in.is_flagged
    if user_in.daily_token_limit is not None:
        user.daily_token_limit = user_in.daily_token_limit
        
    db.commit()
    db.refresh(user)
    
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "is_flagged": user.is_flagged if user.is_flagged is not None else False,
        "daily_token_limit": user.daily_token_limit if user.daily_token_limit is not None else 0,
        "created_at": user.created_at.isoformat() if user.created_at else None
    }

@app.delete("/auth/admin/users/{user_id}")
def admin_delete_user(user_id: str, request: Request, db: Session = Depends(get_db)):
    """Admin only: Xóa người dùng."""
    if not is_admin(request):
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Cascade delete is handled by database level constraints defined in models.py
    db.delete(user)
    db.commit()
    
    return {"detail": "User deleted successfully"}

# ─── Health Check ───────────────────────────────────────────────────────────

@app.get("/auth/health")
def health_check():
    """Health check endpoint for Docker and monitoring."""
    return {"status": "ok", "service": "auth_service"}
