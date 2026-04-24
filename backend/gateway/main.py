from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
from contextvars import ContextVar
from gateway.auth_middleware import auth_middleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from shared.redis_client import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD

# ContextVar to store the current request for slowapi
request_var: ContextVar[Request] = ContextVar("request")

app = FastAPI(title="AI Career Advisor Gateway")

# SECURITY: Configure allowed origins from environment variable
# In production, set ALLOWED_ORIGINS to your frontend domain(s)
# Example: ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# Initialize Limiter with Redis Storage
redis_url = f"redis://{f':{REDIS_PASSWORD}@' if REDIS_PASSWORD else ''}{REDIS_HOST}:{REDIS_PORT}/0"
limiter = Limiter(key_func=get_remote_address, storage_uri=redis_url)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

def get_dynamic_limit():
    """Xác định hạn mức dựa trên URL path."""
    try:
        request = request_var.get()
    except LookupError:
        return "30/minute"
        
    path = request.url.path
    
    # 1. Các API polling hoặc kiểm tra trạng thái (Status/Polling) -> Hạn mức cao
    if any(p in path for p in ["/status", "/polling", "/health", "/analysis/status"]):
        return "120/minute"
    
    # 2. Kiểm tra nếu là user đã login (đã qua middleware và inject request.state.user)
    # Tuy nhiên slowapi decorator chạy trước middleware hoặc độc lập, nên ta dựa vào Header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return "100/minute"
    
    # 3. Mặc định cho Public APIs
    return "30/minute"

# Thêm Auth Middleware
@app.middleware("http")
async def add_auth_middleware(request: Request, call_next):
    token = request_var.set(request)
    try:
        return await auth_middleware(request, call_next)
    finally:
        request_var.reset(token)

# Cấu hình Service URLs
SERVICES = {
    "auth": os.getenv("AUTH_SVC_URL", "http://auth-service:8000"),
    "user": os.getenv("AUTH_SVC_URL", "http://auth-service:8000"), # Map user to auth service
    "cv": os.getenv("CV_SVC_URL", "http://cv-service:8000"),
    "jd": os.getenv("JD_SVC_URL", "http://jd-service:8000"),
    "analysis": os.getenv("ANALYSIS_SVC_URL", "http://analysis-service:8000"),
    "recommend": os.getenv("RECOMMEND_SVC_URL", "http://recommender-service:8000"),
    "admin": os.getenv("ADMIN_SVC_URL", "http://admin-service:8000"),
}

client = httpx.AsyncClient()

@app.api_route("/{service_name}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
@limiter.limit(get_dynamic_limit)
async def proxy(service_name: str, path: str, request: Request):
    # Handle /api prefix if present (strip it and shift service_name/path)
    if service_name == "api":
        parts = path.split("/", 1)
        service_name = parts[0]
        path = parts[1] if len(parts) > 1 else ""

    if service_name not in SERVICES:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")

    # Xử lý path ánh xạ: Nếu gọi /user/login -> forward tới auth-service/auth/login
    target_prefix = "auth" if service_name == "user" else service_name
    url = f"{SERVICES[service_name]}/{target_prefix}/{path}"
    
    # Forward headers and body
    headers = dict(request.headers)
    # Remove hop-by-hop headers
    headers.pop("host", None)
    headers.pop("content-length", None)
    
    # Inject authenticated user ID if available from middleware
    if hasattr(request.state, "user"):
        headers["X-User-ID"] = request.state.user["id"]
        headers["X-User-Email"] = request.state.user["email"]
        # Thống nhất forward role admin
        headers["X-Is-Admin"] = "true" if request.state.user.get("is_admin") else "false"

    try:
        content = await request.body()
        response = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=content,
            params=dict(request.query_params),
            timeout=60.0
        )
        # Lọc bỏ các header nhạy cảm có thể gây xung đột với Proxy của Next.js
        excluded_headers = ["content-length", "transfer-encoding", "connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers", "upgrade"]
        resp_headers = {k: v for k, v in response.headers.items() if k.lower() not in excluded_headers}
        
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=resp_headers
        )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Service unavailable: {str(exc)}")

@app.get("/")
async def root():
    return {"message": "AI Career Advisor Gateway is operational"}
