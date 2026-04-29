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
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))  # 7 days default
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

def get_client_ip(request) -> str:
    """
    Extract real client IP from request, handling proxy/gateway scenarios.
    
    Priority order:
    1. CF-Connecting-IP (Cloudflare-specific, most reliable)
    2. X-Real-IP (set by gateway with actual client IP)
    3. X-Forwarded-For (first IP in the chain)
    4. request.client.host (fallback, may be gateway IP in Docker)
    
    Args:
        request: FastAPI Request object
        
    Returns:
        str: Client IP address
    """
    # Check CF-Connecting-IP header (Cloudflare-specific, most reliable)
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip
    
    # Check X-Real-IP header (set by our gateway)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Check X-Forwarded-For header (may contain multiple IPs)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For format: "client, proxy1, proxy2"
        # We want the first IP (original client)
        return forwarded_for.split(",")[0].strip()
    
    # Fallback to direct connection IP (may be gateway IP in Docker)
    return request.client.host if request.client else "unknown"

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Create a short-lived access token (default: 15 minutes).
    
    Args:
        data: Token payload (user_id, email, role)
        expires_delta: Optional custom expiration time
        
    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "type": "access",  # Token type for validation
        "iat": datetime.now(timezone.utc)  # Issued at
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    """
    Decode and validate an access token.
    
    Args:
        token: JWT token string
        
    Returns:
        dict: Token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Validate token type
        if payload.get("type") != "access":
            logger.warning("Token type mismatch: expected 'access', got '%s'", payload.get("type"))
            return None
            
        return payload
    except JWTError as e:
        logger.debug("JWT decode failed: %s", str(e))
        return None
