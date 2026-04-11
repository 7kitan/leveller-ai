import json
import hashlib
import os
import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from shared.redis_client import auth_cache
from shared.auth_utils import hash_token

# AUTH_SVC_URL không thay đổi logic băm nhưng vẫn giữ để dùng nếu cần

AUTH_SVC_URL = os.getenv("AUTH_SVC_URL", "http://auth-service:8001")

async def auth_middleware(request: Request, call_next):
    # Public endpoints
    public_paths = ["/health", "/auth/login", "/auth/register", "/user/login", "/user/register", "/jd/list"]
    
    # Khớp chính xác cho root, hoặc startswith cho các path công khai khác
    is_public = request.url.path == "/" or any(request.url.path.startswith(path) for path in public_paths)
    
    if is_public:
        return await call_next(request)

    # Extract Token
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        logging.error(f"DEBUG Gateway: Missing or invalid Authorization header for path {request.url.path}")
        return JSONResponse(status_code=401, content={"detail": "Missing or invalid token"})
    
    try:
        # Tách token và làm sạch
        token = auth_header.split(" ", 1)[1].strip()
        # Loại bỏ dấu ngoặc kép nếu bị bao quanh (thường gặp khi dev)
        if (token.startswith('"') and token.endswith('"')) or (token.startswith("'") and token.endswith("'")):
            token = token[1:-1]
            
        token_key = f"token:{hash_token(token)}"
        user_data_str = auth_cache.get(token_key)
        
        if user_data_str:
            user_data = json.loads(user_data_str)
            user_id = user_data.get("id")
            
            # Inject user info into headers for microservices
            # Note: We must update the headers in the request object directly
            request.scope["headers"].append((b"x-user-id", str(user_id).encode()))
            request.state.user = user_data
            
            logging.info(f"DEBUG Gateway: Injected X-User-ID: {user_id} for {request.url.path}")
            return await call_next(request)
        else:
            logging.error(f"DEBUG Gateway: Token key not found in Redis: {token_key}")
            
    except Exception as e:
        logging.error(f"DEBUG Gateway: Error processing token: {str(e)}")
        return JSONResponse(status_code=401, content={"detail": "Invalid token format"})

    # 2. Redis Cache Miss -> Call Auth Service /verify (Optional fallback)
    # For MVP, we assume Redis cache is populated during login. 
    # If not, the token is considered invalid or expired.
    
    return JSONResponse(status_code=401, content={"detail": "Token expired or session invalid"})
