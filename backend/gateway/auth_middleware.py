import json
import hashlib
import os
import logging
import httpx
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from shared.redis_client import auth_cache
from shared.auth_utils import hash_token
from shared.config_utils import config_manager

AUTH_SVC_URL = os.getenv("AUTH_SVC_URL", "http://auth-service:8000")

async def auth_middleware(request: Request, call_next):
    # Public endpoints & preflight requests
    public_paths = ["/health", "/auth/login", "/auth/register", "/user/login", "/user/register", "/jd/list", "/auth/verify", "/auth/forgot-password", "/auth/reset-password"]
    
    path = request.url.path
    if path.startswith("/api"):
        path = path[4:]
        if not path:
            path = "/"

    is_public = path == "/" or any(path.startswith(p) for p in public_paths)
    
    # Preflight requests should always pass
    if request.method == "OPTIONS":
        return await call_next(request)
    
    # 1. Maintenance Mode Check (High Priority)
    maintenance_mode = config_manager.get_setting("maintenance_mode", False)
    
    # Critical paths that should always be accessible to allow admins to login and fix things
    critical_paths = ["/health", "/auth/login", "/user/login", "/admin/settings"]
    is_critical = any(path.startswith(p) for p in critical_paths)

    if maintenance_mode and not is_critical:
        # If public but not critical, or restricted, we must check if user is admin
        # Proceed to extract token and check admin status
        pass
    elif is_public:
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
            
            # --- Maintenance Mode Enforcement ---
            if maintenance_mode:
                is_admin_user = user_data.get("is_admin", False)
                if not is_admin_user and not is_critical:
                    logging.warning(f"Maintenance Mode: Blocking non-admin user {user_id} for path {request.url.path}")
                    return JSONResponse(
                        status_code=503, 
                        content={
                            "detail": "Hệ thống đang bảo trì để nâng cấp. Vui lòng quay lại sau.",
                            "maintenance": True,
                            "duration": config_manager.get_setting("maintenance_duration", "Không xác định")
                        }
                    )

            return await call_next(request)
            
    except Exception as e:
        logging.error(f"DEBUG Gateway: Error processing token: {str(e)}")
        return JSONResponse(status_code=401, content={"detail": "Invalid token format"})

    # If we fall through and maintenance is ON, block unauthenticated requests to non-critical paths
    if maintenance_mode and not is_critical:
        return JSONResponse(
            status_code=503, 
            content={
                "detail": "Hệ thống đang bảo trì. Vui lòng đăng nhập bằng tài khoản Quản trị.",
                "maintenance": True,
                "duration": config_manager.get_setting("maintenance_duration", "Không xác định")
            }
        )

    return JSONResponse(status_code=401, content={"detail": "Token expired or session invalid"})
