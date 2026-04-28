"""
API Gateway - Cổng vào chính của hệ thống Lumix AI

Module này đóng vai trò là reverse proxy, điều hướng tất cả requests từ frontend
đến các microservices phía sau. Nó cũng xử lý:
- Xác thực JWT token
- Rate limiting (giới hạn số request)
- CORS (Cross-Origin Resource Sharing)
- Header injection (inject user info vào requests)

Author: Lumix AI Team
Date: 2026-04-25
# CRITICAL: Force rebuild to ensure code sync
"""
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
from shared.logging_utils import setup_logger

# Khởi tạo logger cho Gateway
logger = setup_logger("gateway", log_file="gateway.log")

# ContextVar để lưu request hiện tại cho slowapi rate limiter
# Cần thiết vì slowapi cần access request object trong decorator
request_var: ContextVar[Request] = ContextVar("request")

# Khởi tạo FastAPI app
app = FastAPI(title="AI Career Advisor Gateway")

# ============================================================================
# CORS CONFIGURATION - Cấu hình Cross-Origin Resource Sharing
# ============================================================================
# SECURITY FIX: Chỉ cho phép origins cụ thể, không dùng wildcard "*"
# Trong production, set ALLOWED_ORIGINS trong .env file
# Ví dụ: ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]

# SECURITY FIX: Chỉ cho phép các headers cần thiết, không dùng ["*"]
# Giảm thiểu attack surface và tăng bảo mật
allowed_headers = [
    "Authorization",      # JWT token
    "Content-Type",       # Loại nội dung (JSON, form-data, etc.)
    "Accept",            # Loại response mong muốn
    "Origin",            # Origin của request
    "X-Requested-With",  # Để phát hiện AJAX requests
    "X-User-ID",         # User ID được inject bởi gateway
    "X-User-Role"        # User role (user/admin) - TRUSTED, injected by gateway only
]

# Thêm CORS middleware vào app
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,           # Danh sách origins được phép
    allow_credentials=True,                  # Cho phép gửi cookies/credentials
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],  # HTTP methods
    allow_headers=allowed_headers,           # Headers được phép
    expose_headers=["X-Total-Count", "X-Attempts-Left", "X-Requires-Captcha"]  # Headers trả về client
)

# ============================================================================
# RATE LIMITING - Giới hạn số lượng requests
# ============================================================================
# Custom key function for rate limiter to use real client IP
def get_real_client_ip_for_limiter(request: Request) -> str:
    """
    Get real client IP for rate limiting (not Docker internal IP).
    
    Checks X-Real-IP and X-Forwarded-For headers before falling back
    to request.client.host.
    """
    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Check X-Forwarded-For header (first IP in chain)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    # Fallback to direct connection IP
    return request.client.host if request.client else "unknown"

# Khởi tạo rate limiter với Redis làm storage backend
# Redis lưu trữ số lượng requests của mỗi IP address
redis_url = f"redis://{f':{REDIS_PASSWORD}@' if REDIS_PASSWORD else ''}{REDIS_HOST}:{REDIS_PORT}/0"
limiter = Limiter(
    key_func=get_real_client_ip_for_limiter,  # Use real client IP, not Docker gateway IP
    storage_uri=redis_url          # Lưu counters trong Redis
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

def get_dynamic_limit():
    """
    Xác định hạn mức rate limit động dựa trên URL path và authentication status.
    
    Logic:
    - Status/polling endpoints: 120 requests/phút (cần polling thường xuyên)
    - Authenticated users: 100 requests/phút (đã login, tin cậy hơn)
    - Public APIs: 30 requests/phút (chưa login, hạn chế hơn)
    
    Returns:
        str: Rate limit string (ví dụ: "30/minute", "100/minute")
    """
    try:
        request = request_var.get()
    except LookupError:
        # Nếu không lấy được request, trả về limit mặc định
        return "30/minute"
        
    path = request.url.path
    
    # 1. Các API polling hoặc kiểm tra trạng thái -> Hạn mức cao
    # Những endpoints này cần được gọi thường xuyên để check status
    if any(p in path for p in ["/status", "/polling", "/health", "/analysis/status"]):
        return "120/minute"
    
    # 2. User đã đăng nhập -> Hạn mức trung bình
    # Kiểm tra Authorization header có JWT token không
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return "100/minute"
    
    # 3. Public APIs (chưa login) -> Hạn mức thấp
    # Bảo vệ hệ thống khỏi abuse từ anonymous users
    return "30/minute"

# ============================================================================
# AUTHENTICATION MIDDLEWARE - Xác thực JWT token
# ============================================================================
@app.middleware("http")
async def add_auth_middleware(request: Request, call_next):
    """
    Middleware xác thực JWT token và inject user info vào request.
    
    Flow:
    1. Lấy JWT token từ Authorization header
    2. Verify token (check signature, expiration)
    3. Extract user info từ token payload
    4. Inject user info vào request.state.user
    5. Forward request đến service phía sau
    
    Args:
        request: FastAPI Request object
        call_next: Next middleware/handler trong chain
        
    Returns:
        Response từ service phía sau
    """
    # DEBUG: Log all incoming requests with headers
    origin = request.headers.get("origin", "NO_ORIGIN")
    if request.method == "OPTIONS":
        req_headers = request.headers.get("access-control-request-headers", "NONE")
        req_method = request.headers.get("access-control-request-method", "NONE")
        logger.info(f"[MIDDLEWARE] OPTIONS {request.url.path} | Origin: {origin} | Req-Headers: {req_headers} | Req-Method: {req_method}")
    else:
        client_ip = get_client_ip(request)
        logger.info(f"[MIDDLEWARE] {request.method} {request.url.path} | Origin: {origin} | Client: {client_ip}")
    
    # Set request vào ContextVar để rate limiter có thể access
    token = request_var.set(request)
    try:
        # Gọi auth_middleware để xác thực token
        return await auth_middleware(request, call_next)
    finally:
        # Reset ContextVar sau khi xử lý xong
        request_var.reset(token)

# ============================================================================
# SERVICE ROUTING - Cấu hình URLs của các microservices
# ============================================================================
# Map service name -> service URL
# Trong Docker Compose, service names được resolve thành container IPs
SERVICES = {
    "auth": os.getenv("AUTH_SVC_URL", "http://auth-service:8000"),
    "user": os.getenv("AUTH_SVC_URL", "http://auth-service:8000"),  # user endpoints cũng ở auth service
    "cv": os.getenv("CV_SVC_URL", "http://cv-service:8000"),
    "jd": os.getenv("JD_SVC_URL", "http://jd-service:8000"),
    "analysis": os.getenv("ANALYSIS_SVC_URL", "http://analysis-service:8000"),
    "recommend": os.getenv("RECOMMEND_SVC_URL", "http://recommender-service:8000"),
    "admin": os.getenv("ADMIN_SVC_URL", "http://admin-service:8000"),
}

# HTTP client để forward requests đến services
# Sử dụng AsyncClient để support async/await
client = httpx.AsyncClient()

# ============================================================================
# PROXY ENDPOINT - Điều hướng requests đến các microservices
# ============================================================================
@app.api_route("/{service_name}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy(service_name: str, path: str, request: Request):
    """
    Reverse proxy chính - điều hướng requests đến đúng microservice.
    """
    # CORSMiddleware handles OPTIONS automatically, no need for manual handling
    logger.info(f"[PROXY] {request.method} /{service_name}/{path} | Origin: {request.headers.get('origin', 'NO_ORIGIN')}")
    
    # Kiểm tra service có tồn tại không
    if service_name not in SERVICES:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")

    # Xử lý path mapping đặc biệt
    # /user/login -> auth-service/auth/login (vì user endpoints nằm trong auth service)
    target_prefix = "auth" if service_name == "user" else service_name
    url = f"{SERVICES[service_name]}/{target_prefix}/{path}"
    
    # Chuẩn bị headers để forward
    headers = dict(request.headers)
    
    # SECURITY: Forward real client IP to backend services
    # This is critical for rate limiting, login attempts tracking, and audit logs
    
    # Determine the real client IP using helper function
    real_client_ip = get_client_ip(request)
    
    # Build X-Forwarded-For chain
    direct_client = request.client.host if request.client else "unknown"
    if "x-forwarded-for" in headers:
        # Append our direct client to the existing chain
        headers["X-Forwarded-For"] = f"{headers['x-forwarded-for']}, {direct_client}"
    else:
        # Start the chain with direct client
        headers["X-Forwarded-For"] = direct_client
    
    # Set X-Real-IP to the actual client (first IP in proxy chain)
    headers["X-Real-IP"] = real_client_ip
    
    # Xóa các hop-by-hop headers (không được forward qua proxy)
    # Những headers này chỉ có ý nghĩa giữa client-gateway, không phải gateway-service
    headers.pop("host", None)
    headers.pop("content-length", None)
    
    # SECURITY: Inject user info vào headers nếu user đã đăng nhập
    # Middleware đã verify JWT và lưu user info vào request.state.user
    # Services phía sau có thể trust những headers này vì đã qua gateway verify
    if hasattr(request.state, "user"):
        headers["X-User-ID"] = request.state.user["id"]
        headers["X-User-Email"] = request.state.user["email"]
        headers["X-User-Role"] = request.state.user.get("role", "user")

    try:
        # Lấy request body
        content = await request.body()
        
        # Forward request đến service
        response = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=content,
            params=dict(request.query_params),
            timeout=60.0  # Timeout 60 giây
        )
        
        # Lọc bỏ các headers có thể gây conflict
        # Những headers này do service backend tự generate, không nên forward về client
        excluded_headers = [
            "content-length",      # Sẽ được tính lại
            "transfer-encoding",   # Có thể conflict với proxy
            "connection",          # Connection-specific
            "keep-alive",          # Connection-specific
            "proxy-authenticate",  # Proxy-specific
            "proxy-authorization", # Proxy-specific
            "te",                  # Transfer encoding
            "trailers",            # Chunked transfer
            "upgrade"              # Protocol upgrade
        ]
        # Tạo response rỗng
        proxy_response = Response(
            content=response.content,
            status_code=response.status_code,
        )
        
        # Dùng multi_items() để giữ lại TẤT CẢ các header trùng tên (vd: Set-Cookie)
        for k, v in response.headers.multi_items():
            if k.lower() not in excluded_headers:
                proxy_response.headers.append(k, v)
                
        return proxy_response
    except httpx.RequestError as exc:
        # Service không available hoặc network error
        raise HTTPException(status_code=502, detail=f"Service unavailable: {str(exc)}")

# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================
@app.get("/")
async def root():
    """
    Root endpoint - kiểm tra gateway có hoạt động không.
    
    Returns:
        dict: Message xác nhận gateway đang chạy
    """
    return {"message": "AI Career Advisor Gateway is operational"}

@app.get("/health")
async def health_check():
    """
    Health check endpoint for Docker health checks and monitoring.
    
    Returns:
        dict: Service status
    """
    return {"status": "ok", "service": "gateway"}
