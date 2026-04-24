from fastapi import FastAPI, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from shared.database import get_db, engine, Base
import shared.models # Ensure all models are registered
from shared.models import User
# Ensure tables are created
# Base.metadata.create_all(bind=engine) - Moved to startup event
from shared.auth_utils import get_password_hash, verify_password, create_access_token, hash_token, decode_access_token, ACCESS_TOKEN_EXPIRE_SECONDS
from shared.config_utils import config_manager
from shared.redis_client import auth_cache
from shared.email_utils import send_password_reset_email
from shared.schemas import PaginatedResponse
from pydantic import BaseModel, EmailStr
import json
import logging
import uuid
import os
import httpx
from typing import Optional, List
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Google reCAPTCHA Secret Key
RECAPTCHA_SECRET_KEY = os.getenv("GOOGLE_RECAPTCHA_SECRET_KEY")

async def verify_google_captcha(token: str):
    """Verify Google reCAPTCHA v2/v3 token."""
    if not RECAPTCHA_SECRET_KEY:
        logging.error("SECURITY ALERT: GOOGLE_RECAPTCHA_SECRET_KEY not set. Cannot verify captcha. Failing securely.")
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
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    is_admin: bool
    full_name: Optional[str] = None

class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class AdminUserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    is_admin: bool
    is_active: bool
    is_flagged: bool
    daily_token_limit: int
    today_usage: Optional[int] = 0
    created_at: Optional[str] # Will be stringified

class AdminUserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    full_name: Optional[str] = None
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None
    is_flagged: Optional[bool] = None
    daily_token_limit: Optional[int] = None

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    old_password: Optional[str] = None
    password: Optional[str] = None

class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    captcha_token: Optional[str] = None

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

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
    
    # Generate a secure token
    reset_token = str(uuid.uuid4())
    reset_key = f"pwd_reset:{reset_token}"
    
    # Store in Redis for 1 hour
    auth_cache.setex(reset_key, 3600, str(user.id))
    
    # TODO: Integrate with Email Service (SendGrid/SMTP)
    reset_link = f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/auth/reset-password?token={reset_token}"
    logging.info(f"PASSWORD RESET LINK for {user.email}: {reset_link}")
    
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

    return {"detail": "Password has been reset successfully. Please login with your new password."}

@app.on_event("startup")
async def startup_event():
    from shared.database import init_db
    init_db()

def is_admin(request: Request) -> bool:
    return request.headers.get("X-Is-Admin") == "true"

@app.post("/auth/register", response_model=AuthResponse)
@limiter.limit("5/day")
async def register(request: Request, user_in: UserCreate, captcha_token: Optional[str] = None, db: Session = Depends(get_db)):
    # 1. Check registration limit per IP
    ip_addr = request.client.host if request.client else "unknown"
    reg_key = f"reg_attempts:{ip_addr}"
    reg_count = auth_cache.incr_with_expire(reg_key, 86400)
    if reg_count > 5:
        raise HTTPException(status_code=429, detail="Too many registrations from this IP. Please try again in 24 hours.")

    # 2. Always require Captcha for Register
    if not captcha_token:
        raise HTTPException(status_code=400, detail="Captcha required for registration", headers={"X-Requires-Captcha": "true"})
    
    is_valid = await verify_google_captcha(captcha_token)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid Captcha. Please try again.")

    db_user = db.query(User).filter(User.email == user_in.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        is_admin=False,
        registration_ip=ip_addr,
        registration_user_agent=request.headers.get("User-Agent"),
        last_login_ip=ip_addr,
        last_login_user_agent=request.headers.get("User-Agent")
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token = create_access_token(data={"sub": str(new_user.id), "email": new_user.email})
    
    user_data = {
        "id": str(new_user.id), 
        "email": new_user.email, 
        "is_admin": new_user.is_admin,
        "full_name": new_user.full_name
    }
    token_key = f"token:{hash_token(access_token)}"
    session_pointer = f"user_session:{new_user.id}"

    old_token_key = auth_cache.get(session_pointer)
    if old_token_key:
        auth_cache.delete(old_token_key)

    auth_cache.setex(token_key, ACCESS_TOKEN_EXPIRE_SECONDS, json.dumps(user_data))
    auth_cache.setex(session_pointer, ACCESS_TOKEN_EXPIRE_SECONDS, token_key)

    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": user_data
    }

@app.post("/auth/login")
@limiter.limit("20/minute")
async def login(request: Request, user_in: UserLogin, captcha_token: Optional[str] = None, db: Session = Depends(get_db)):
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

    # Lockout check (10 attempts)
    if max_attempts >= 10:
        auth_cache.setex(lockout_key, 86400, "locked")
        raise HTTPException(status_code=403, detail="Too many failed attempts. Your IP has been locked for 24 hours.")

    # 3. Check for Captcha (from 3rd attempt since we already incremented)
    if max_attempts >= 3:
        if not captcha_token:
            raise HTTPException(status_code=400, detail="Captcha required", headers={"X-Requires-Captcha": "true"})
        
        is_valid = await verify_google_captcha(captcha_token)
        if not is_valid:
            raise HTTPException(status_code=400, detail="Invalid Captcha. Please try again.")

    user = db.query(User).filter(User.email == user_in.email).first()
    
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=401, 
            detail="Incorrect email or password",
            headers={"X-Attempts-Left": str(10 - max_attempts)}
        )
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled. Please contact administrator.")

    auth_cache.delete(attempt_key)
    auth_cache.delete(ip_attempt_key)
    
    user.last_login_ip = ip_addr
    user.last_login_user_agent = request.headers.get("User-Agent")
    db.commit()
    db.refresh(user)
    
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    
    user_data = {
        "id": str(user.id), 
        "email": user.email, 
        "is_admin": user.is_admin,
        "full_name": user.full_name
    }
    token_key = f"token:{hash_token(access_token)}"
    session_pointer = f"user_session:{user.id}"

    old_token_key = auth_cache.get(session_pointer)
    if old_token_key:
        auth_cache.delete(old_token_key)

    auth_cache.setex(token_key, ACCESS_TOKEN_EXPIRE_SECONDS, json.dumps(user_data))
    auth_cache.setex(session_pointer, ACCESS_TOKEN_EXPIRE_SECONDS, token_key)
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": user_data
    }

@app.get("/auth/verify")
def verify(token: str, db: Session = Depends(get_db)):
    token_key = f"token:{hash_token(token)}"
    cached = auth_cache.get(token_key)
    
    if cached:
        user_data = json.loads(cached)
        user_data["maintenance_mode"] = config_manager.get_setting("maintenance_mode", False)
        user_data["maintenance_duration"] = config_manager.get_setting("maintenance_duration", "Không xác định")
        return user_data
    
    # Cache miss -> Deep Verification (JWT Decode + DB Check)
    logging.info(f"DEBUG Auth: Cache miss for token. Performing deep verification...")
    payload = decode_access_token(token)
    if not payload:
        logging.error("DEBUG Auth: JWT decode failed or token expired.")
        raise HTTPException(status_code=401, detail="Invalid or expired token (JWT decode failed)")
        
    if "sub" not in payload:
        logging.error(f"DEBUG Auth: JWT payload missing 'sub' claim: {payload}")
        raise HTTPException(status_code=401, detail="Invalid token payload (missing sub)")

    try:
        user_id_str = payload["sub"]
        # Safe UUID conversion
        try:
            user_uuid = uuid.UUID(user_id_str) if isinstance(user_id_str, str) else user_id_str
        except (ValueError, TypeError):
            logging.error(f"DEBUG Auth: Invalid UUID format in JWT sub: {user_id_str}")
            raise HTTPException(status_code=401, detail="Invalid user ID format in token")

        user = db.query(User).filter(User.id == user_uuid).first()
        if not user:
            logging.error(f"DEBUG Auth: User {user_uuid} not found in database.")
            raise HTTPException(status_code=401, detail="User not found")
            
        if not user.is_active:
            logging.error(f"DEBUG Auth: User {user_uuid} is inactive.")
            raise HTTPException(status_code=401, detail="User found but inactive")
            
        # Re-cache user data for subsequent requests (if caching is enabled)
        user_data = {
            "id": str(user.id), 
            "email": user.email, 
            "is_admin": user.is_admin,
            "full_name": user.full_name
        }
        auth_cache.setex(token_key, ACCESS_TOKEN_EXPIRE_SECONDS, json.dumps(user_data))
        logging.info(f"DEBUG Auth: Deep verification successful for user {user.email}")
        
        # Thêm system status vào response
        user_data["maintenance_mode"] = config_manager.get_setting("maintenance_mode", False)
        user_data["maintenance_duration"] = config_manager.get_setting("maintenance_duration", "Không xác định")
        return user_data
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logging.error(f"DEBUG Auth: Unexpected error during deep verification: {str(e)}")
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
        "is_admin": user.is_admin,
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
        "is_admin": user.is_admin,
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
            "is_admin": u.is_admin,
            "is_active": u.is_active,
            "is_flagged": getattr(u, "is_flagged", False),
            "daily_token_limit": getattr(u, "daily_token_limit", 0),
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
def admin_create_user(request: Request, user_in: UserCreate, db: Session = Depends(get_db)):
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
        is_admin=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "id": str(new_user.id),
        "email": new_user.email,
        "full_name": new_user.full_name,
        "is_admin": new_user.is_admin,
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
    if user_in.is_admin is not None:
        user.is_admin = user_in.is_admin
    if user_in.is_active is not None:
        user.is_active = user_in.is_active
        if not user.is_active:
            # Revoke active session if banned
            session_pointer = f"user_session:{user.id}"
            old_token_key = auth_cache.get(session_pointer)
            if old_token_key:
                logging.info(f"Revoking session for banned user {user.id}")
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
        "is_admin": user.is_admin,
        "is_active": user.is_active,
        "is_flagged": user.is_flagged,
        "daily_token_limit": user.daily_token_limit,
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
