from fastapi import FastAPI, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from shared.database import get_db
from shared.models import User
from shared.auth_utils import get_password_hash, verify_password, create_access_token, hash_token, decode_access_token, ACCESS_TOKEN_EXPIRE_SECONDS
from shared.redis_client import auth_cache
from pydantic import BaseModel, EmailStr
import json
import logging
import uuid
from typing import Optional, List

app = FastAPI(title="Auth Service")

def is_admin(request: Request) -> bool:
    return request.headers.get("X-Is-Admin") == "true"

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

class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class AdminUserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    is_admin: bool
    created_at: Optional[str] # Will be stringified

class AdminUserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    full_name: Optional[str] = None
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None

@app.post("/auth/register", response_model=AuthResponse)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user_in.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        is_admin=False # Default
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token = create_access_token(data={"sub": str(new_user.id), "email": new_user.email})
    
    user_data = {"id": str(new_user.id), "email": new_user.email, "is_admin": new_user.is_admin}
    token_key = f"token:{hash_token(access_token)}"
    session_pointer = f"user_session:{new_user.id}"

    # Thu hồi token cũ nếu có (Single Session)
    old_token_key = auth_cache.get(session_pointer)
    if old_token_key:
        auth_cache.delete(old_token_key)

    # Lưu token mới và cập nhật con trỏ session (Đồng bộ TTL)
    auth_cache.setex(token_key, ACCESS_TOKEN_EXPIRE_SECONDS, json.dumps(user_data))
    auth_cache.setex(session_pointer, ACCESS_TOKEN_EXPIRE_SECONDS, token_key)

    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": user_data
    }

@app.post("/auth/login", response_model=AuthResponse)
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_in.email).first()
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    
    user_data = {"id": str(user.id), "email": user.email, "is_admin": user.is_admin}
    token_key = f"token:{hash_token(access_token)}"
    session_pointer = f"user_session:{user.id}"

    # Thu hồi token cũ nếu có (Single Session)
    old_token_key = auth_cache.get(session_pointer)
    if old_token_key:
        logging.info(f"Revoking old token for user {user.id}: {old_token_key}")
        auth_cache.delete(old_token_key)

    # Lưu token mới và cập nhật con trỏ session (Đồng bộ TTL)
    logging.info(f"Setting new token in Redis: {token_key}")
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
        return json.loads(cached)
    
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
        user_data = {"id": str(user.id), "email": user.email, "is_admin": user.is_admin}
        auth_cache.setex(token_key, ACCESS_TOKEN_EXPIRE_SECONDS, json.dumps(user_data))
        logging.info(f"DEBUG Auth: Deep verification successful for user {user.email}")
        
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
        "is_admin": user.is_admin
    }

@app.get("/auth/admin/users", response_model=List[AdminUserResponse])
def admin_list_users(request: Request, db: Session = Depends(get_db)):
    """Admin only: Lấy danh sách toàn bộ người dùng."""
    if not is_admin(request):
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "full_name": u.full_name,
            "is_admin": u.is_admin,
            "created_at": u.created_at.isoformat() if u.created_at else None
        }
        for u in users
    ]

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
        
    db.commit()
    db.refresh(user)
    
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "is_admin": user.is_admin,
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
