import os
import hashlib
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

# JWT Config - NO DEFAULT VALUES FOR SECURITY
SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
ACCESS_TOKEN_EXPIRE_SECONDS = ACCESS_TOKEN_EXPIRE_MINUTES * 60

# SECURITY: Enforce JWT secret in ALL environments
if not SECRET_KEY:
    logger.critical("=" * 80)
    logger.critical("FATAL: JWT_SECRET environment variable is not set!")
    logger.critical("This is a CRITICAL security requirement.")
    logger.critical("Please set a strong JWT_SECRET in your .env file.")
    logger.critical("Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'")
    logger.critical("=" * 80)
    sys.exit(1)

# Validate JWT secret strength (minimum 32 characters)
if len(SECRET_KEY) < 32:
    logger.critical("=" * 80)
    logger.critical("FATAL: JWT_SECRET is too short (minimum 32 characters required)!")
    logger.critical("Current length: %d characters", len(SECRET_KEY))
    logger.critical("Generate a strong secret with: python -c 'import secrets; print(secrets.token_urlsafe(32))'")
    logger.critical("=" * 80)
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
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
