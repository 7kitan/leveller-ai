import json
import hashlib
import os
import logging
import httpx
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from shared.redis_client import auth_cache
from shared.auth_utils import hash_token

AUTH_SVC_URL = os.getenv("AUTH_SVC_URL", "http://auth-service:8000")

async def auth_middleware(request: Request, call_next):
    # Public endpoints
    public_paths = ["/health", "/auth/login", "/auth/register", "/user/login", "/user/register", "/jd/list"]
    
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
        if (token.startswith('"') and token.endswith('"')) or (token.startswith("'") and token.endswith("'")):
            token = token[1:-1]
            
        token_key = f"token:{hash_token(token)}"
        
        # 1. Check Redis Cache
        user_data_str = auth_cache.get(token_key)
        
        user_data = None
        if user_data_str:
            user_data = json.loads(user_data_str)
        else:
            # 2. Redis Cache Miss -> Fallback to Auth Service /verify
            logging.info(f"DEBUG Gateway: Redis miss for token. Falling back to Auth Service...")
            async with httpx.AsyncClient(timeout=10.0) as client:
                verify_url = f"{AUTH_SVC_URL}/auth/verify"
                try:
                    # Use params for safe encoding of the JWT token
                    response = await client.get(verify_url, params={"token": token})
                    if response.status_code == 200:
                        user_data = response.json()
                        logging.info(f"DEBUG Gateway: Fallback success for user {user_data.get('id')}")
                    else:
                        try:
                            error_detail = response.json().get("detail", "No detail provided")
                        except:
                            error_detail = response.text[:100]
                        logging.error(f"DEBUG Gateway: Auth Service verify failed with status {response.status_code}: {error_detail}")
                except Exception as svc_err:
                    logging.error(f"DEBUG Gateway: Auth Service unreachable or error: {str(svc_err)}")

        if user_data:
            user_id = user_data.get("id")
            # Inject user info into headers for microservices
            request.scope["headers"].append((b"x-user-id", str(user_id).encode()))
            
            # Inject Admin status if applicable
            if user_data.get("is_admin"):
                request.scope["headers"].append((b"x-is-admin", b"true"))
                
            request.state.user = user_data
            return await call_next(request)
            
    except Exception as e:
        logging.error(f"DEBUG Gateway: Error processing token: {str(e)}")
        return JSONResponse(status_code=401, content={"detail": "Invalid token format"})

    return JSONResponse(status_code=401, content={"detail": "Token expired or session invalid"})
