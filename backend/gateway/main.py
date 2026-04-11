from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
from gateway.auth_middleware import auth_middleware

app = FastAPI(title="AI Career Advisor Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thêm Auth Middleware
@app.middleware("http")
async def add_auth_middleware(request: Request, call_next):
    return await auth_middleware(request, call_next)

# Cấu hình Service URLs
SERVICES = {
    "auth": os.getenv("AUTH_SVC_URL", "http://auth-service:8000"),
    "user": os.getenv("AUTH_SVC_URL", "http://auth-service:8000"), # Map user to auth service
    "cv": os.getenv("CV_SVC_URL", "http://cv-service:8000"),
    "jd": os.getenv("JD_SVC_URL", "http://jd-service:8000"),
    "analysis": os.getenv("ANALYSIS_SVC_URL", "http://analysis-service:8000"),
}

client = httpx.AsyncClient()

@app.api_route("/{service_name}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(service_name: str, path: str, request: Request):
    if service_name not in SERVICES:
        raise HTTPException(status_code=404, detail="Service not found")

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
