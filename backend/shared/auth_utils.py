import os
import hashlib
import sys
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

# JWT Config
SECRET_KEY = os.getenv("JWT_SECRET", "super_secret_key_change_me")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
ACCESS_TOKEN_EXPIRE_SECONDS = ACCESS_TOKEN_EXPIRE_MINUTES * 60

# SECURITY: Enforce strong JWT secret in production
if SECRET_KEY == "super_secret_key_change_me":
    import logging
    logger = logging.getLogger(__name__)
    logger.critical("=" * 80)
    logger.critical("SECURITY WARNING: Using default JWT_SECRET!")
    logger.critical("This is a CRITICAL security vulnerability in production.")
    logger.critical("Please set a strong JWT_SECRET in your .env file.")
    logger.critical("Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'")
    logger.critical("=" * 80)
    
    # In production mode, refuse to start
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        logger.critical("FATAL: Cannot start in production with default JWT_SECRET!")
        sys.exit(1)

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
