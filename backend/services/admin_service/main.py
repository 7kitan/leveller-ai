from fastapi import FastAPI, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from shared.database import get_db, SessionLocal
from shared.models import SystemSetting, User, LLMLog, SystemLog, YouTubeCourse
from shared.config_utils import config_manager
from shared.ai_service import AI_REGISTRY
from shared.admin_auth import get_current_admin_user, require_admin
from shared.redis_client import auth_cache, config_cache
from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Any, Dict
from datetime import datetime
from uuid import UUID
import logging
import json

app = FastAPI(title="Admin Service")
logger = logging.getLogger("admin_service")

# System settings that should be synced to Redis for gateway access
# These use special "system:" prefix for gateway middleware
GATEWAY_SETTINGS = {"MAINTENANCE_MODE", "MAINTENANCE_DURATION"}

def sync_setting_to_redis(key: str, value: Any):
    """
    Sync a system setting to Redis for hot-reload support.
    
    - Gateway settings (MAINTENANCE_MODE, MAINTENANCE_DURATION) use "system:" prefix
    - All other settings use direct key for ConfigManager compatibility
    """
    key_upper = key.upper()
    
    try:
        if key_upper in GATEWAY_SETTINGS:
            # Gateway settings: Use "system:" prefix for auth_middleware
            redis_key = f"system:{key_upper}"
            auth_cache.set(redis_key, str(value))
            logger.info(f"[ADMIN] Synced gateway setting {redis_key} to Redis: {value}")
        
        # ALWAYS sync to ConfigManager cache (no prefix)
        config_cache.set(key_upper, json.dumps(value), ex=3600)
        logger.info(f"[ADMIN] Synced config setting {key_upper} to Redis cache")
        
    except Exception as e:
        logger.error(f"[ADMIN] Failed to sync {key} to Redis: {e}")

@app.on_event("startup")
def load_settings_to_redis():
    """
    Load ALL system settings from database to Redis on startup.
    This ensures hot-reload works immediately without DB queries.
    """
    try:
        db = SessionLocal()
        
        # Load ALL settings from database
        all_settings = db.query(SystemSetting).all()
        
        if all_settings:
            for setting in all_settings:
                sync_setting_to_redis(setting.key, setting.value)
            logger.info(f"[ADMIN] Loaded {len(all_settings)} settings to Redis")
        else:
            logger.warning("[ADMIN] No settings found in database")
            
            # Set default gateway settings if DB is empty
            for key in GATEWAY_SETTINGS:
                if key == "MAINTENANCE_MODE":
                    sync_setting_to_redis(key, "false")
                elif key == "MAINTENANCE_DURATION":
                    sync_setting_to_redis(key, "Không xác định")
        
        db.close()
        logger.info("[ADMIN] Settings preload completed")
        
    except Exception as e:
        logger.error(f"[ADMIN] Failed to load settings to Redis: {e}")

# --- Pydantic Schemas ---

class SettingUpdate(BaseModel):
    value: Any

class BulkSettingUpdate(BaseModel):
    settings: List[dict]  # List of {"key": "input_key", "value": "input_value"}

class SettingResponse(BaseModel):
    key: str
    value: Any
    description: Optional[str] = None
    updated_at: datetime

    class Config:
        from_attributes = True

# --- NEW: LLM & System Log Schemas ---

class LLMLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Any
    user_id: Optional[Any] = None
    user_email: Optional[str] = None
    model_id: str
    provider: Optional[str] = None
    call_type: str
    prompt_tokens: Optional[int] = 0
    completion_tokens: Optional[int] = 0
    total_tokens: Optional[int] = 0
    latency_ms: Optional[int] = 0
    status: str
    error_message: Optional[str] = None
    created_at: datetime

class SystemLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Any
    level: str
    module: str
    message: str
    details: Optional[Any] = None
    created_at: datetime

class LLMUsageSummary(BaseModel):
    summary: Dict[str, Any] # For total_calls etc.
    total_tokens: int
    total_cost_usd: float
    avg_latency_ms: float
    success_rate: float
    model_breakdown: List[Dict[str, Any]]
    top_users: List[Dict[str, Any]]

# --- YouTube Schemas ---

class YouTubeCourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Any
    video_id: str
    title: str
    description: Optional[str] = None
    channel_name: Optional[str] = None
    thumbnail: Optional[str] = None
    url: str
    embedding_context: Optional[str] = None
    duration_raw: Optional[str] = None

    published_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    last_verified_at: Optional[datetime] = None
    created_at: datetime



# --- Endpoints ---

@app.get("/admin/settings", response_model=List[SettingResponse])
def admin_list_settings(
    request: Request, 
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Admin only: Lấy danh sách settings hệ thống."""
    settings = db.query(SystemSetting).all()
    return settings

@app.get("/admin/settings/{key}", response_model=SettingResponse)
def admin_get_setting(
    key: str, 
    request: Request, 
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Admin only: Lấy một setting cụ thể."""
    
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not setting:
        # Fallback check in config_manager (env/default)
        val = config_manager.get_setting(key)
        if val is not None:
            # Return a transient response or create it?
            # Let's return a virtual setting for the UI to show
            return {
                "key": key,
                "value": val,
                "description": "Default from System / Env",
                "updated_at": datetime.now()
            }
        raise HTTPException(status_code=404, detail="Setting not found")
    return setting

@app.patch("/admin/settings/{key}", response_model=SettingResponse)
def admin_update_setting(
    key: str, 
    setting_in: SettingUpdate, 
    request: Request, 
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Admin only: Cập nhật hoặc tạo một setting.
    
    NOTE: Key will be automatically normalized to UPPERCASE for consistency.
    Gateway-level settings (MAINTENANCE_MODE, MAINTENANCE_DURATION) are synced to Redis.
    """
    # Normalize key to UPPERCASE
    key = key.upper()
    
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not setting:
        setting = SystemSetting(key=key, value=setting_in.value)
        db.add(setting)
    else:
        setting.value = setting_in.value
    
    db.commit()
    db.refresh(setting)
    
    # Invalidate Cache
    config_manager.invalidate_cache(key)
    
    # Sync to Redis if it's a gateway setting
    sync_setting_to_redis(key, setting_in.value)
    
    return setting

@app.post("/admin/settings/bulk", response_model=List[SettingResponse])
def admin_bulk_update_settings(
    bulk_in: BulkSettingUpdate, 
    request: Request, 
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Admin only: Cập nhật nhiều settings cùng lúc.
    
    NOTE: All keys will be automatically normalized to UPPERCASE for consistency.
    Gateway-level settings (MAINTENANCE_MODE, MAINTENANCE_DURATION) are synced to Redis.
    """
    
    updated_settings = []
    for item in bulk_in.settings:
        key = item.get("key")
        value = item.get("value")
        
        # Normalize key to UPPERCASE
        key = key.upper()
        
        setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if not setting:
            # Create if not exists (Optional, depending on policy)
            setting = SystemSetting(key=key, value=value)
            db.add(setting)
        else:
            setting.value = value
            
        updated_settings.append(setting)
        # Invalidate Cache for each key
        config_manager.invalidate_cache(key)
        
        # Sync to Redis if it's a gateway setting
        sync_setting_to_redis(key, value)
    
    db.commit()
    for s in updated_settings:
        db.refresh(s)
        
    return updated_settings

@app.get("/admin/ai-models")
def admin_list_ai_models(
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Admin only: Lấy danh sách các AI model và provider được hỗ trợ."""
    return AI_REGISTRY

@app.post("/admin/cache/clear")
def admin_clear_cache(
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Admin only: Clear Redis cache (all databases)."""
    try:
        from shared.redis_client import config_cache, result_cache, quota_cache
        
        cleared = []
        
        # Clear config cache (DB 0)
        try:
            config_cache.flushdb()
            cleared.append("config_cache")
        except Exception as e:
            logger.error(f"Failed to clear config_cache: {e}")
        
        # Clear result cache (DB 2)
        try:
            result_cache.flushdb()
            cleared.append("result_cache")
        except Exception as e:
            logger.error(f"Failed to clear result_cache: {e}")
        
        # Clear quota cache (DB 3)
        try:
            quota_cache.flushdb()
            cleared.append("quota_cache")
        except Exception as e:
            logger.error(f"Failed to clear quota_cache: {e}")
        
        logger.info(f"[ADMIN] Redis cache cleared: {cleared}")
        return {
            "status": "success",
            "message": f"Cleared {len(cleared)} cache databases",
            "cleared": cleared
        }
    except Exception as e:
        logger.error(f"[ADMIN] Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")


@app.post("/admin/vector/sync")
def admin_sync_vector(
    request: Request, 
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Admin only: Trigger VectorDB sync (rebuild skill/job/course vectors)."""
    try:
        from worker.celery_app import celery_app
        
        # Dispatch async task to rebuild vectors
        task = celery_app.send_task(
            "worker.tasks.vector_tasks.rebuild_all_vectors",
            kwargs={}
        )
        
        logger.info(f"[ADMIN] VectorDB sync task dispatched: {task.id}")
        return {
            "status": "processing",
            "message": "VectorDB sync started",
            "task_id": task.id
        }
    except Exception as e:
        logger.error(f"[ADMIN] Failed to dispatch vector sync: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start vector sync: {str(e)}")


# --- LLM Stats & Logs ---

@app.get("/admin/stats/llm/summary", response_model=LLMUsageSummary)
def admin_get_llm_summary(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Admin only: Tổng hợp chi phí và hiệu suất LLM."""
    logs = db.query(LLMLog).all()
    if not logs:
        return {
            "summary": {"total_calls": 0},
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "avg_latency_ms": 0.0,
            "success_rate": 0.0,
            "model_breakdown": [],
            "top_users": []
        }

    total_calls = len(logs)
    total_tokens = sum(l.total_tokens for l in logs)
    total_latency = sum(l.latency_ms for l in logs)
    success_count = sum(1 for l in logs if l.status == "success")
    
    total_cost = 0.0
    model_stats = {}
    user_stats = {} # {user_id: {"email": "...", "calls": 0, "tokens": 0}}

    for l in logs:
        # Model stats
        m = l.model_id.lower()
        if m not in model_stats:
            model_stats[m] = {"count": 0, "tokens": 0, "cost": 0.0}
        
        cost = 0.0
        if "gpt-4o-mini" in m:
            cost = (l.prompt_tokens * 0.15 / 1_000_000) + (l.completion_tokens * 0.6 / 1_000_000)
        elif "gpt-4o" in m:
            cost = (l.prompt_tokens * 5.0 / 1_000_000) + (l.completion_tokens * 15.0 / 1_000_000)
        elif "gemini" in m:
            cost = (l.prompt_tokens * 0.075 / 1_000_000) + (l.completion_tokens * 0.3 / 1_000_000)
            
        total_cost += cost
        model_stats[m]["count"] += 1
        model_stats[m]["tokens"] += l.total_tokens
        model_stats[m]["cost"] += cost

        # User stats
        u_id = str(l.user_id) if l.user_id else "Anonymous"
        if u_id not in user_stats:
            user_stats[u_id] = {"calls": 0, "tokens": 0}
        user_stats[u_id]["calls"] += 1
        user_stats[u_id]["tokens"] += l.total_tokens

    breakdown = []
    for model_name, stats in model_stats.items():
        breakdown.append({
            "model": model_name,
            "calls": stats["count"],
            "tokens": stats["tokens"],
            "cost_usd": round(stats["cost"], 6)
        })

    # Enrich user stats with emails
    user_breakdown = []
    # Get user emails for the IDs we found
    valid_uids = [u for u in user_stats.keys() if u != "Anonymous"]
    email_map = {}
    if valid_uids:
        users = db.query(User).filter(User.id.in_(valid_uids)).all()
        email_map = {str(u.id): u.email for u in users}

    for u_id, stats in user_stats.items():
        user_breakdown.append({
            "user_id": u_id,
            "email": email_map.get(u_id, "Anonymous"),
            "calls": stats["calls"],
            "tokens": stats["tokens"]
        })
    
    # Sort by calls descending and take top 10
    top_users = user_breakdown
    top_users.sort(key=lambda x: x["calls"], reverse=True)
    top_users = top_users[:10]

    return {
        "summary": {"total_calls": total_calls},
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 4),
        "avg_latency_ms": total_latency / total_calls,
        "success_rate": success_count / total_calls,
        "model_breakdown": breakdown,
        "top_users": top_users
    }

@app.get("/admin/stats/llm/logs", response_model=List[LLMLogResponse])
def admin_list_llm_logs(
    limit: int = 100,
    offset: int = 0,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Admin only: Danh sách chi tiết các cuộc gọi LLM."""
    query = db.query(LLMLog)
    if status:
        query = query.filter(LLMLog.status == status)
    
    logs = query.order_by(LLMLog.created_at.desc()).offset(offset).limit(limit).all()
    
    # Get user emails for logs
    user_ids = {str(log.user_id) for log in logs if log.user_id}
    email_map = {}
    if user_ids:
        users = db.query(User).filter(User.id.in_(list(user_ids))).all()
        email_map = {str(u.id): u.email for u in users}

    # Explicitly stringify UUIDs for safety and add user_email
    for log in logs:
        u_id = str(log.user_id) if log.user_id else None
        if hasattr(log, 'id'): log.id = str(log.id)
        if u_id: log.user_id = u_id
        setattr(log, 'user_email', email_map.get(u_id, "Anonymous") if u_id else "Anonymous")
        
    return logs

# --- System Logs ---

@app.get("/admin/system/logs", response_model=List[SystemLogResponse])
def admin_list_system_logs(
    level: Optional[str] = None,
    module: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Admin only: Xem log hệ thống tập trung."""
    query = db.query(SystemLog)
    if level:
        query = query.filter(SystemLog.level == level.upper())
    if module:
        query = query.filter(SystemLog.module.ilike(f"%{module}%"))
        
    logs = query.order_by(SystemLog.created_at.desc()).offset(offset).limit(limit).all()
    for log in logs:
        if hasattr(log, 'id'): log.id = str(log.id)
    return logs

@app.delete("/admin/system/logs/cleanup")
def admin_cleanup_logs(
    days: int = 30,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Admin only: Dọn dẹp log cũ."""
    from shared.system_logger import system_logger
    count = system_logger.cleanup_old_logs(days=days)
    return {"message": f"Successfully cleaned up {count} logs older than {days} days."}

# --- YouTube Management ---

@app.get("/admin/youtube", response_model=List[YouTubeCourseResponse])
def admin_list_youtube_cache(
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Admin only: Danh sách các video YouTube được lưu trong cache."""
    query = db.query(YouTubeCourse)
    if search:
        query = query.filter(
            (YouTubeCourse.title.ilike(f"%{search}%")) | 
            (YouTubeCourse.channel_name.ilike(f"%{search}%"))
        )
    
    courses = query.order_by(YouTubeCourse.created_at.desc()).offset(offset).limit(limit).all()
    
    # Stringify UUIDs
    for c in courses:
        if hasattr(c, 'id'): c.id = str(c.id)
        
    return courses

@app.delete("/admin/youtube/{video_id}")
def admin_delete_youtube_cache(
    video_id: str,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Admin only: Xóa một video khỏi cache YouTube."""
    course = db.query(YouTubeCourse).filter(YouTubeCourse.video_id == video_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Video not found in cache")
    
    db.delete(course)
    db.commit()
    return {"status": "success", "message": f"Video {video_id} removed from cache"}

@app.post("/admin/youtube/verify-all")
def admin_verify_all_youtube_videos(request: Request):
    """Admin only: Kích hoạt tiến trình kiểm tra lại tính khả dụng của toàn bộ video trong cache."""
    # TODO: Implement youtube_tasks.verify_all_cached_videos task
    # Currently this task module doesn't exist
    raise HTTPException(
        status_code=501, 
        detail="YouTube verification task not implemented yet. Task module 'worker.tasks.youtube_tasks' does not exist."
    )


# ============================================================================
# IP Block Management Endpoints
# ============================================================================

class BlockedIPInfo(BaseModel):
    """Schema for blocked IP information"""
    ip_address: str
    ttl_seconds: int
    blocked_at: Optional[str] = None
    attempts: Optional[int] = None

class UnblockIPRequest(BaseModel):
    """Schema for unblock IP request"""
    ip_address: str

@app.get("/admin/blocked-ips")
def get_blocked_ips(
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """
    Admin only: Get list of all blocked IP addresses.
    
    Returns list of IPs that are currently locked out due to failed login attempts.
    """
    
    try:
        # Get all lockout keys from Redis
        lockout_pattern = "lockout:*"
        blocked_ips = []
        
        # Scan for all lockout keys
        cursor = 0
        while True:
            cursor, keys = auth_cache.scan(cursor, match=lockout_pattern, count=100)
            
            for key in keys:
                # Extract IP from key (format: "lockout:192.168.1.1")
                if isinstance(key, bytes):
                    key = key.decode('utf-8')
                
                ip_address = key.replace("lockout:", "")
                
                # Get TTL (time to live) for this block
                ttl = auth_cache.ttl(key)
                
                # Get login attempts count if available
                attempt_key = f"login_attempts_ip:{ip_address}"
                attempts = auth_cache.get(attempt_key)
                if attempts:
                    attempts = int(attempts) if isinstance(attempts, (str, bytes)) else attempts
                
                blocked_ips.append({
                    "ip_address": ip_address,
                    "ttl_seconds": ttl if ttl > 0 else 0,
                    "ttl_hours": round(ttl / 3600, 2) if ttl > 0 else 0,
                    "attempts": attempts,
                    "expires_in": f"{ttl // 3600}h {(ttl % 3600) // 60}m" if ttl > 0 else "Expired"
                })
            
            if cursor == 0:
                break
        
        logger.info(f"[ADMIN] Listed {len(blocked_ips)} blocked IPs")
        
        return {
            "total": len(blocked_ips),
            "blocked_ips": sorted(blocked_ips, key=lambda x: x['ttl_seconds'], reverse=True)
        }
        
    except Exception as e:
        logger.error(f"[ADMIN] Failed to get blocked IPs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve blocked IPs: {str(e)}")


@app.post("/admin/unblock-ip")
def unblock_ip(
    request: Request,
    data: dict,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """
    Admin only: Unblock a specific IP address.
    
    Removes lockout and clears login attempt counters for the specified IP.
    """
    
    ip_address = data.ip_address
    
    try:
        # Delete lockout key
        lockout_key = f"lockout:{ip_address}"
        deleted_lockout = auth_cache.delete(lockout_key)
        
        # Delete login attempts counter
        attempt_key = f"login_attempts_ip:{ip_address}"
        deleted_attempts = auth_cache.delete(attempt_key)
        
        # Also check for email-based attempts (optional cleanup)
        # Note: We can't easily map IP to email, so we skip this
        
        logger.info(f"[ADMIN] Unblocked IP {ip_address} by admin {request.headers.get('X-User-Email')}")
        
        return {
            "message": f"IP {ip_address} has been unblocked",
            "ip_address": ip_address,
            "lockout_removed": bool(deleted_lockout),
            "attempts_cleared": bool(deleted_attempts),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"[ADMIN] Failed to unblock IP {ip_address}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to unblock IP: {str(e)}")


@app.delete("/admin/blocked-ips")
def clear_all_blocked_ips(
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """
    Admin only: Clear ALL blocked IP addresses.
    
    WARNING: This will unblock all IPs that are currently locked out.
    Use with caution in production.
    """
    
    try:
        # Get all lockout keys
        lockout_pattern = "lockout:*"
        attempt_pattern = "login_attempts_ip:*"
        
        deleted_lockouts = 0
        deleted_attempts = 0
        
        # Delete all lockout keys
        cursor = 0
        while True:
            cursor, keys = auth_cache.scan(cursor, match=lockout_pattern, count=100)
            if keys:
                deleted_lockouts += auth_cache.delete(*keys)
            if cursor == 0:
                break
        
        # Delete all IP-based attempt counters
        cursor = 0
        while True:
            cursor, keys = auth_cache.scan(cursor, match=attempt_pattern, count=100)
            if keys:
                deleted_attempts += auth_cache.delete(*keys)
            if cursor == 0:
                break
        
        logger.warning(f"[ADMIN] Cleared ALL blocked IPs ({deleted_lockouts} lockouts, {deleted_attempts} attempts) by admin {request.headers.get('X-User-Email')}")
        
        return {
            "message": "All blocked IPs have been cleared",
            "lockouts_removed": deleted_lockouts,
            "attempts_cleared": deleted_attempts,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"[ADMIN] Failed to clear all blocked IPs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear blocked IPs: {str(e)}")


@app.get("/admin/ip-status/{ip_address}")
def check_ip_status(
    request: Request,
    ip_address: str,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """
    Admin only: Check the status of a specific IP address.
    
    Returns whether the IP is blocked, number of failed attempts, and TTL.
    """
    
    try:
        lockout_key = f"lockout:{ip_address}"
        attempt_key = f"login_attempts_ip:{ip_address}"
        
        # Check if IP is blocked
        is_blocked = auth_cache.exists(lockout_key)
        
        # Get TTL if blocked
        ttl = auth_cache.ttl(lockout_key) if is_blocked else 0
        
        # Get attempt count
        attempts = auth_cache.get(attempt_key)
        if attempts:
            attempts = int(attempts) if isinstance(attempts, (str, bytes)) else attempts
        else:
            attempts = 0
        
        # Get attempt TTL
        attempt_ttl = auth_cache.ttl(attempt_key) if attempts > 0 else 0
        
        status = {
            "ip_address": ip_address,
            "is_blocked": bool(is_blocked),
            "failed_attempts": attempts,
            "lockout_ttl_seconds": ttl if ttl > 0 else 0,
            "lockout_expires_in": f"{ttl // 3600}h {(ttl % 3600) // 60}m" if ttl > 0 else "Not blocked",
            "attempts_ttl_seconds": attempt_ttl if attempt_ttl > 0 else 0,
            "attempts_reset_in": f"{attempt_ttl // 60}m {attempt_ttl % 60}s" if attempt_ttl > 0 else "No attempts"
        }
        
        logger.info(f"[ADMIN] Checked IP status for {ip_address}: blocked={is_blocked}, attempts={attempts}")
        
        return status
        
    except Exception as e:
        logger.error(f"[ADMIN] Failed to check IP status for {ip_address}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check IP status: {str(e)}")


@app.post("/admin/refresh-market-stats")
def trigger_market_stats_refresh(
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """
    Admin only: Manually trigger market stats aggregation.
    
    This endpoint triggers the Celery task that aggregates market data
    from jobs and updates the market_skill_stats table.
    """
    try:
        from worker.celery_app import celery_app
        
        # Trigger the market stats aggregation task
        task = celery_app.send_task(
            "worker.tasks.market_stats_tasks.aggregate_market_data",
            queue="market_stats"
        )
        
        logger.info(f"[ADMIN] Market stats refresh triggered by {admin_user.email}, task_id={task.id}")
        
        return {
            "message": "Market stats refresh has been triggered",
            "task_id": task.id,
            "status": "queued"
        }
        
    except Exception as e:
        logger.error(f"[ADMIN] Failed to trigger market stats refresh: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger refresh: {str(e)}")


@app.get("/admin/health")
def health_check():
    return {"status": "ok", "service": "admin_service"}
