import json
import hashlib
import os
import logging
import httpx
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from shared.redis_client import auth_cache
from shared.auth_utils import hash_token
from shared.models import UserRole

AUTH_SVC_URL = os.getenv("AUTH_SVC_URL", "http://auth-service:8000")

def get_maintenance_mode() -> tuple[bool, str]:
    """
    Get maintenance mode status from Redis cache (centralized at gateway).
    Redis is populated by admin service when settings are updated.
    Returns: (is_maintenance, duration_message)
    """
    try:
        # Check Redis cache first (fast path)
        mode = auth_cache.get("system:MAINTENANCE_MODE")
        duration = auth_cache.get("system:MAINTENANCE_DURATION")
        
        if mode is not None:
            # Handle both bytes and string (redis-py version compatibility)
            mode_str = mode.decode('utf-8') if isinstance(mode, bytes) else str(mode)
            duration_str = duration.decode('utf-8') if isinstance(duration, bytes) else str(duration) if duration else "Không xác định"
            
            is_maintenance = mode_str.lower() == 'true'
            return is_maintenance, duration_str
        
        # Redis miss - this shouldn't happen if admin service is working correctly
        # Fail-safe: assume NOT in maintenance
        logging.warning("Maintenance mode not found in Redis cache, assuming disabled")
        return False, "Không xác định"
        
    except Exception as e:
        logging.error(f"Failed to get maintenance mode from Redis: {e}")
        # Fail-safe: if Redis is down, assume NOT in maintenance
        return False, "Không xác định"

def get_cors_headers(request: Request) -> dict:
    """Get CORS headers for JSONResponse to allow browser access to response body."""
    origin = request.headers.get("origin", "*")
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
        "Access-Control-Allow-Headers": "Authorization, Content-Type, Accept, Origin, X-Requested-With",
    }

async def auth_middleware(request: Request, call_next):
    # Public endpoints & preflight requests
    public_paths = ["/health", "/auth/login", "/auth/register", "/user/login", "/user/register", "/jd/list", "/auth/forgot-password", "/auth/reset-password", "/auth/captcha-status", "/user/captcha-status"]
    
    path = request.url.path
    if path.startswith("/api"):
        path = path[4:]
        if not path:
            path = "/"

    # Allow all health endpoints (gateway + all services)
    is_health_endpoint = path.endswith("/health") or path == "/health"
    is_public = path == "/" or is_health_endpoint or any(path.startswith(p) for p in public_paths)
    
    # Preflight requests should always pass
    if request.method == "OPTIONS":
        return await call_next(request)
    
    # Always-accessible paths (even during maintenance mode)
    always_accessible = ["/health", "/auth/captcha-status", "/user/captcha-status"]
    is_always_accessible = any(path.startswith(p) for p in always_accessible)
    
    if is_always_accessible:
        return await call_next(request)
    
    # 1. Maintenance Mode Check (Centralized at Gateway via Redis)
    maintenance_mode, maintenance_duration = get_maintenance_mode()
    
    # Critical paths that should always be accessible to allow admins to login and fix things
    # These paths will handle maintenance mode logic internally (e.g., auth-service checks role after login)
    critical_paths = ["/auth/login", "/user/login"]
    is_critical = any(path.startswith(p) for p in critical_paths)

    # Allow critical paths to pass through (they handle maintenance internally)
    if is_critical:
        return await call_next(request)

    # If maintenance mode is ON and path is NOT critical, block for public paths
    if maintenance_mode and is_public:
        return JSONResponse(
            status_code=503, 
            content={
                "detail": "Hệ thống đang bảo trì để nâng cấp. Vui lòng quay lại sau.",
                "maintenance": True,
                "duration": maintenance_duration
            },
            headers=get_cors_headers(request)
        )
    
    # If public and NOT in maintenance, allow through
    if is_public:
        return await call_next(request)

    # Extract Token (for protected endpoints or critical paths during maintenance)
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
                verify_url = f"{AUTH_SVC_URL}/auth/me"
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
            user_role = user_data.get("role", UserRole.USER)
            # Inject user info into headers for microservices
            request.scope["headers"].append((b"x-user-id", str(user_id).encode()))
            request.scope["headers"].append((b"x-user-role", str(user_role).encode()))
            
            request.state.user = user_data
            
            # --- Maintenance Mode Enforcement (Centralized) ---
            if maintenance_mode:
                # SECURITY: Use the new role-based check for maintenance bypass
                is_admin_user = (user_role == UserRole.ADMIN)
                if not is_admin_user and not is_critical:
                    logging.warning(f"Maintenance Mode: Blocking non-admin user {user_id} for path {request.url.path}")
                    return JSONResponse(
                        status_code=503, 
                        content={
                            "detail": "Hệ thống đang bảo trì để nâng cấp. Vui lòng quay lại sau.",
                            "maintenance": True,
                            "duration": maintenance_duration
                        },
                        headers=get_cors_headers(request)
                    )

            return await call_next(request)
            
    except Exception as e:
        logging.error(f"DEBUG Gateway: Error processing token: {str(e)}")
        return JSONResponse(
            status_code=401, 
            content={"detail": "Invalid token format"},
            headers=get_cors_headers(request)
        )

    # If we fall through and maintenance is ON, block unauthenticated requests to non-critical paths
    if maintenance_mode and not is_critical:
        return JSONResponse(
            status_code=503, 
            content={
                "detail": "Hệ thống đang bảo trì. Vui lòng đăng nhập bằng tài khoản Quản trị.",
                "maintenance": True,
                "duration": maintenance_duration
            },
            headers=get_cors_headers(request)
        )

    return JSONResponse(
        status_code=401, 
        content={"detail": "Token expired or session invalid"},
        headers=get_cors_headers(request)
    )
