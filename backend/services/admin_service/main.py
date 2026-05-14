from fastapi import FastAPI, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from shared.database import get_db, SessionLocal
from shared.models import SystemSetting, User, LLMLog, SystemLog, YouTubeCourse, Skill
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

# Import and include prompt management routes
from services.admin_service.routes.prompt_routes import router as prompt_router
app.include_router(prompt_router)

# ============================================================================
# BENCHMARK EXTENSION (Optional - Can be disabled in production)
# ============================================================================
# Import and include benchmark routes ONLY if enabled
ENABLE_BENCHMARK = config_manager.get_setting("ENABLE_BENCHMARK", default=True, cast=bool)

if ENABLE_BENCHMARK:
    try:
        from services.admin_service.routes.benchmark_routes import router as benchmark_router
        app.include_router(benchmark_router)
        logger.info("[ADMIN] ✅ Benchmark extension ENABLED - Routes registered")
    except ImportError as e:
        logger.warning(f"[ADMIN] Benchmark routes extension not found: {e}")
    except Exception as e:
        logger.error(f"[ADMIN] Error registering benchmark routes: {e}")
else:
    logger.info("[ADMIN] ⚠️ Benchmark extension DISABLED - Skipping route registration")

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
    
    # Initialize prompt manager and load active prompts
    try:
        from shared.prompt_manager import init_prompt_manager
        init_prompt_manager(config_cache, SessionLocal)
        logger.info("[ADMIN] Prompt manager initialized and prompts loaded to Redis")
    except Exception as e:
        logger.error(f"[ADMIN] Failed to initialize prompt manager: {e}")

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
    
    # Curation fields
    language: Optional[str] = None
    skill_level: Optional[str] = None
    is_curated: Optional[bool] = False
    quality_score: Optional[float] = None
    skills: Optional[List[str]] = []

class VideoMetadataRequest(BaseModel):
    video_id: str

class AddCuratedVideoRequest(BaseModel):
    video_id: str
    skills: List[str]
    skill_level: str
    language: str

# --- Skill Management Schemas ---

class SkillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: Any
    name: str
    category: Optional[str] = None
    parent_skill_id: Optional[Any] = None

class SkillCreateRequest(BaseModel):
    name: str
    category: Optional[str] = None
    parent_skill_id: Optional[str] = None

class SkillUpdateRequest(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    parent_skill_id: Optional[str] = None

class PendingSkillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: Any
    skill_name: str
    source: str
    suggested_by: Optional[Any] = None
    suggested_at: datetime
    status: str
    reviewed_by: Optional[Any] = None
    reviewed_at: Optional[datetime] = None
    merged_into: Optional[Any] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

class PendingSkillActionRequest(BaseModel):
    notes: Optional[str] = None

class PendingSkillMergeRequest(BaseModel):
    target_skill_id: str
    notes: Optional[str] = None



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
            
    db.commit()
    
    # After successful commit, sync ALL updated settings to Redis
    logger.info(f"[ADMIN] Bulk update committed to DB. Syncing {len(updated_settings)} settings to Redis...")
    for s in updated_settings:
        db.refresh(s)
        sync_setting_to_redis(s.key, s.value)
        
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
    language: Optional[str] = None,
    level: Optional[str] = None,
    skill: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Admin only: Danh sách các video YouTube được lưu trong cache với filters."""
    query = db.query(YouTubeCourse)
    
    # Search filter
    if search:
        query = query.filter(
            (YouTubeCourse.title.ilike(f"%{search}%")) | 
            (YouTubeCourse.channel_name.ilike(f"%{search}%"))
        )
    
    # Language filter
    if language and language != "all":
        query = query.filter(YouTubeCourse.language == language)
    
    # Level filter
    if level and level != "all":
        query = query.filter(YouTubeCourse.skill_level == level)
    
    # Skill filter - need to join with youtube_video_skills
    if skill and skill != "all":
        query = query.join(
            text("youtube_video_skills"),
            text("youtube_courses.video_id = youtube_video_skills.video_id")
        ).filter(text("youtube_video_skills.skill_name = :skill")).params(skill=skill)
    
    courses = query.order_by(YouTubeCourse.created_at.desc()).offset(offset).limit(limit).all()
    
    # Fetch skills for each course
    result = []
    for c in courses:
        # Get skills from junction table
        skills_result = db.execute(
            text("SELECT skill_name FROM youtube_video_skills WHERE video_id = :vid"),
            {"vid": c.video_id}
        ).fetchall()
        
        course_dict = {
            "id": str(c.id),
            "video_id": c.video_id,
            "title": c.title,
            "description": c.description,
            "channel_name": c.channel_name,
            "thumbnail": c.thumbnail,
            "url": c.url,
            "embedding_context": c.embedding_context,
            "duration_raw": c.duration_raw,
            "published_at": c.published_at,
            "expires_at": c.expires_at,
            "last_verified_at": c.last_verified_at,
            "created_at": c.created_at,
            "language": c.language,
            "skill_level": c.skill_level,
            "is_curated": c.is_curated,
            "quality_score": c.quality_score,
            "skills": [row[0] for row in skills_result]
        }
        result.append(course_dict)
        
    return result

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

@app.get("/admin/youtube/skills")
def admin_get_available_skills(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Admin only: Get list of all skills used in curated videos."""
    result = db.execute(
        text("""
            SELECT DISTINCT skill_name 
            FROM youtube_video_skills 
            ORDER BY skill_name ASC
        """)
    ).fetchall()
    
    skills = [row[0] for row in result]
    return skills

@app.post("/admin/youtube/fetch-metadata")
async def admin_fetch_video_metadata(
    data: VideoMetadataRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Admin only: Fetch video metadata from YouTube API."""
    import httpx
    import os
    
    api_key = os.getenv("YOUTUBE_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="YouTube API key not configured")
    
    video_id = data.video_id
    
    try:
        async with httpx.AsyncClient() as client:
            # Fetch video details
            response = await client.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={
                    "part": "snippet,contentDetails",
                    "id": video_id,
                    "key": api_key
                }
            )
            response.raise_for_status()
            video_data = response.json()
        
        items = video_data.get("items", [])
        if not items:
            raise HTTPException(status_code=404, detail="Video not found")
        
        item = items[0]
        snippet = item.get("snippet", {})
        content_details = item.get("contentDetails", {})
        
        # Parse duration (ISO 8601 format: PT1H2M10S)
        duration_raw = content_details.get("duration", "")
        
        return {
            "video_id": video_id,
            "title": snippet.get("title"),
            "description": snippet.get("description"),
            "channel_name": snippet.get("channelTitle"),
            "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url"),
            "published_at": snippet.get("publishedAt"),
            "duration_raw": duration_raw
        }
        
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="Failed to fetch video metadata")
    except Exception as e:
        logger.error(f"Error fetching video metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/youtube/curated")
async def admin_add_curated_video(
    data: AddCuratedVideoRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Admin only: Add a curated video with skills, level, and language."""
    from shared.llm_utils import get_embedding
    from datetime import timedelta, timezone
    
    video_id = data.video_id
    
    # Check if video already exists
    existing = db.query(YouTubeCourse).filter(YouTubeCourse.video_id == video_id).first()
    if existing:
        # Update existing video with curation data
        existing.language = data.language
        existing.skill_level = data.skill_level
        existing.is_curated = True
        existing.created_by = admin_user.id
        
        # Delete old skills
        db.execute(
            text("DELETE FROM youtube_video_skills WHERE video_id = :vid"),
            {"vid": video_id}
        )
        
        # Add new skills - match case-insensitively with master skills table
        for skill_name in data.skills:
            # Try to find skill in master table (case-insensitive)
            skill = db.query(Skill).filter(
                text("LOWER(name) = LOWER(:name)")
            ).params(name=skill_name).first()
            
            if skill:
                # Use the canonical name from master table
                db.execute(
                    text("""
                        INSERT INTO youtube_video_skills (video_id, skill_id, skill_name)
                        VALUES (:vid, :sid, :skill)
                        ON CONFLICT (video_id, skill_name) DO UPDATE SET skill_id = :sid
                    """),
                    {"vid": video_id, "sid": str(skill.id), "skill": skill.name}
                )
            else:
                # Skill not in master table - insert with just name
                db.execute(
                    text("""
                        INSERT INTO youtube_video_skills (video_id, skill_name)
                        VALUES (:vid, :skill)
                        ON CONFLICT (video_id, skill_name) DO NOTHING
                    """),
                    {"vid": video_id, "skill": skill_name}
                )
        
        db.commit()
        return {"message": "Video updated successfully", "video_id": video_id}
    
    # Fetch video metadata from YouTube API
    import httpx
    import os
    
    api_key = os.getenv("YOUTUBE_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="YouTube API key not configured")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={
                    "part": "snippet,contentDetails",
                    "id": video_id,
                    "key": api_key
                }
            )
            response.raise_for_status()
            video_data = response.json()
        
        items = video_data.get("items", [])
        if not items:
            raise HTTPException(status_code=404, detail="Video not found on YouTube")
        
        item = items[0]
        snippet = item.get("snippet", {})
        content_details = item.get("contentDetails", {})
        
        title = snippet.get("title")
        description = snippet.get("description")
        channel_name = snippet.get("channelTitle")
        thumbnail = snippet.get("thumbnails", {}).get("high", {}).get("url")
        published_at_str = snippet.get("publishedAt")
        duration_raw = content_details.get("duration", "")
        
        # Parse published_at
        published_at = None
        if published_at_str:
            published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
        
        # Create embedding context
        context = f"Title: {title}. Channel: {channel_name}. Description: {description}"
        vector = get_embedding(context)
        
        now = datetime.now(timezone.utc)
        
        # Create new video
        new_video = YouTubeCourse(
            video_id=video_id,
            title=title,
            description=description,
            thumbnail=thumbnail,
            channel_name=channel_name,
            url=f"https://www.youtube.com/watch?v={video_id}",
            embedding_context=context,
            vector=vector,
            published_at=published_at,
            duration_raw=duration_raw,
            expires_at=now + timedelta(days=365),  # Curated videos cached for 1 year
            last_verified_at=now,
            language=data.language,
            skill_level=data.skill_level,
            is_curated=True,
            created_by=admin_user.id
        )
        
        db.add(new_video)
        db.flush()
        
        # Add skills - match case-insensitively with master skills table
        for skill_name in data.skills:
            # Try to find skill in master table (case-insensitive)
            skill = db.query(Skill).filter(
                text("LOWER(name) = LOWER(:name)")
            ).params(name=skill_name).first()
            
            if skill:
                # Use the canonical name from master table
                db.execute(
                    text("""
                        INSERT INTO youtube_video_skills (video_id, skill_id, skill_name)
                        VALUES (:vid, :sid, :skill)
                    """),
                    {"vid": video_id, "sid": str(skill.id), "skill": skill.name}
                )
            else:
                # Skill not in master table - insert with just name
                db.execute(
                    text("""
                        INSERT INTO youtube_video_skills (video_id, skill_name)
                        VALUES (:vid, :skill)
                    """),
                    {"vid": video_id, "skill": skill_name}
                )
        
        db.commit()
        
        return {
            "message": "Curated video added successfully",
            "video_id": video_id,
            "title": title
        }
        
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="Failed to fetch video from YouTube")
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding curated video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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


# ============================================================================
# Skill Management Endpoints
# ============================================================================

@app.get("/admin/skills")
def admin_list_skills(
    search: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Admin only: List all skills with search and filter."""
    try:
        query = db.query(Skill)
        
        # Search filter
        if search:
            query = query.filter(Skill.name.ilike(f"%{search}%"))
        
        # Category filter
        if category and category != "all":
            query = query.filter(Skill.category == category)
        
        # Get total count
        total = query.count()
        
        # Get paginated results
        skills = query.order_by(Skill.name).offset(offset).limit(limit).all()
        
        # Format response
        result = []
        for skill in skills:
            # Count usage in youtube_video_skills
            usage_count = db.execute(
                text("SELECT COUNT(*) FROM youtube_video_skills WHERE skill_id = :sid"),
                {"sid": skill.id}
            ).scalar()
            
            result.append({
                "id": str(skill.id),
                "name": skill.name,
                "category": skill.category,
                "parent_skill_id": str(skill.parent_skill_id) if skill.parent_skill_id else None,
                "usage_count": usage_count
            })
        
        return {
            "total": total,
            "skills": result
        }
        
    except Exception as e:
        logger.error(f"Error listing skills: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/skills")
def admin_create_skill(
    data: SkillCreateRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Admin only: Create new skill."""
    try:
        # Check if skill already exists
        existing = db.query(Skill).filter(Skill.name == data.name).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Skill '{data.name}' already exists")
        
        # Create new skill
        new_skill = Skill(
            name=data.name,
            category=data.category,
            parent_skill_id=data.parent_skill_id if data.parent_skill_id else None
        )
        
        db.add(new_skill)
        db.commit()
        db.refresh(new_skill)
        
        logger.info(f"[ADMIN] Created skill: {data.name} by {admin_user.email}")
        
        return {
            "message": "Skill created successfully",
            "skill": {
                "id": str(new_skill.id),
                "name": new_skill.name,
                "category": new_skill.category
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating skill: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/admin/skills/{skill_id}")
def admin_update_skill(
    skill_id: str,
    data: SkillCreateRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Admin only: Update existing skill."""
    try:
        # Find the skill
        skill = db.query(Skill).filter(Skill.id == skill_id).first()
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")
        
        # Check if new name conflicts with another skill
        if data.name != skill.name:
            existing = db.query(Skill).filter(
                Skill.name == data.name,
                Skill.id != skill_id
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail=f"Skill '{data.name}' already exists")
        
        # Update skill
        skill.name = data.name
        skill.category = data.category
        skill.parent_skill_id = data.parent_skill_id if data.parent_skill_id else None
        
        db.commit()
        db.refresh(skill)
        
        logger.info(f"[ADMIN] Updated skill {skill_id}: {data.name} by {admin_user.email}")
        
        return {
            "message": "Skill updated successfully",
            "skill": {
                "id": str(skill.id),
                "name": skill.name,
                "category": skill.category
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating skill: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/admin/skills/{skill_id}")
def admin_delete_skill(
    skill_id: str,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Admin only: Delete skill."""
    try:
        # Find the skill
        skill = db.query(Skill).filter(Skill.id == skill_id).first()
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")
        
        # Check if skill is being used in youtube_video_skills
        usage_count = db.execute(
            text("SELECT COUNT(*) FROM youtube_video_skills WHERE skill_id = :sid"),
            {"sid": skill_id}
        ).scalar()
        
        if usage_count > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot delete skill. It is used in {usage_count} YouTube video(s). Please remove those associations first."
            )
        
        # Check if skill is a parent of other skills
        children_count = db.query(Skill).filter(Skill.parent_skill_id == skill_id).count()
        if children_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete skill. It is a parent of {children_count} other skill(s). Please update those skills first."
            )
        
        # Delete the skill
        skill_name = skill.name
        db.delete(skill)
        db.commit()
        
        logger.info(f"[ADMIN] Deleted skill {skill_id}: {skill_name} by {admin_user.email}")
        
        return {"message": f"Skill '{skill_name}' deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting skill: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/skills/categories")
def admin_list_skill_categories(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Admin only: List all skill categories."""
    try:
        result = db.execute(
            text("""
                SELECT DISTINCT category, COUNT(*) as count
                FROM skills
                WHERE category IS NOT NULL
                GROUP BY category
                ORDER BY category
            """)
        ).fetchall()
        
        categories = [{"name": row[0], "count": row[1]} for row in result]
        
        return {"categories": categories}
        
    except Exception as e:
        logger.error(f"Error listing categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/skills/pending")
def admin_list_pending_skills(
    status: Optional[str] = "pending",
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Admin only: List pending skills for review."""
    try:
        query = text("""
            SELECT 
                ps.id, ps.skill_name, ps.source, ps.suggested_by,
                ps.suggested_at, ps.status, ps.reviewed_by, ps.reviewed_at,
                ps.merged_into, ps.notes, ps.metadata, ps.created_at, ps.updated_at,
                u.full_name as suggested_by_name
            FROM pending_skills ps
            LEFT JOIN users u ON ps.suggested_by = u.id
            WHERE ps.status = :status
            ORDER BY ps.suggested_at DESC
            LIMIT :limit OFFSET :offset
        """)
        
        result = db.execute(query, {"status": status, "limit": limit, "offset": offset}).fetchall()
        
        # Get total count
        count_query = text("SELECT COUNT(*) FROM pending_skills WHERE status = :status")
        total = db.execute(count_query, {"status": status}).scalar()
        
        pending_skills = []
        for row in result:
            pending_skills.append({
                "id": str(row[0]),
                "skill_name": row[1],
                "source": row[2],
                "suggested_by": str(row[3]) if row[3] else None,
                "suggested_at": row[4].isoformat() if row[4] else None,
                "status": row[5],
                "reviewed_by": str(row[6]) if row[6] else None,
                "reviewed_at": row[7].isoformat() if row[7] else None,
                "merged_into": str(row[8]) if row[8] else None,
                "notes": row[9],
                "metadata": row[10],
                "created_at": row[11].isoformat() if row[11] else None,
                "updated_at": row[12].isoformat() if row[12] else None,
                "suggested_by_name": row[13]
            })
        
        return {
            "total": total,
            "pending_skills": pending_skills
        }
        
    except Exception as e:
        logger.error(f"Error listing pending skills: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/skills/pending/{pending_id}/approve")
def admin_approve_pending_skill(
    pending_id: str,
    data: PendingSkillActionRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Admin only: Approve pending skill and add to master skills table."""
    try:
        # Get pending skill
        pending = db.execute(
            text("SELECT * FROM pending_skills WHERE id = :id AND status = 'pending'"),
            {"id": pending_id}
        ).fetchone()
        
        if not pending:
            raise HTTPException(status_code=404, detail="Pending skill not found or already processed")
        
        skill_name = pending[1]  # skill_name column
        
        # Check if skill already exists
        existing = db.query(Skill).filter(Skill.name == skill_name).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Skill '{skill_name}' already exists in master table")
        
        # Create new skill in master table
        new_skill = Skill(name=skill_name, category="Technology")  # Default category
        db.add(new_skill)
        db.flush()
        
        # Update youtube_video_skills with skill_id
        db.execute(
            text("""
                UPDATE youtube_video_skills
                SET skill_id = :skill_id
                WHERE skill_name = :skill_name AND skill_id IS NULL
            """),
            {"skill_id": new_skill.id, "skill_name": skill_name}
        )
        
        # Update pending skill status
        db.execute(
            text("""
                UPDATE pending_skills
                SET status = 'approved',
                    reviewed_by = :reviewer,
                    reviewed_at = NOW(),
                    notes = :notes
                WHERE id = :id
            """),
            {"reviewer": admin_user.id, "notes": data.notes, "id": pending_id}
        )
        
        db.commit()
        
        logger.info(f"[ADMIN] Approved skill: {skill_name} by {admin_user.email}")
        
        return {
            "message": "Skill approved and added to master table",
            "skill_id": str(new_skill.id),
            "skill_name": skill_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error approving skill: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/skills/pending/{pending_id}/reject")
def admin_reject_pending_skill(
    pending_id: str,
    data: PendingSkillActionRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Admin only: Reject pending skill."""
    try:
        # Update pending skill status
        result = db.execute(
            text("""
                UPDATE pending_skills
                SET status = 'rejected',
                    reviewed_by = :reviewer,
                    reviewed_at = NOW(),
                    notes = :notes
                WHERE id = :id AND status = 'pending'
            """),
            {"reviewer": admin_user.id, "notes": data.notes, "id": pending_id}
        )
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Pending skill not found or already processed")
        
        db.commit()
        
        logger.info(f"[ADMIN] Rejected pending skill: {pending_id} by {admin_user.email}")
        
        return {"message": "Skill rejected"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error rejecting skill: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/skills/pending/{pending_id}/merge")
def admin_merge_pending_skill(
    pending_id: str,
    data: PendingSkillMergeRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Admin only: Merge pending skill into existing skill."""
    try:
        # Get pending skill
        pending = db.execute(
            text("SELECT skill_name FROM pending_skills WHERE id = :id AND status = 'pending'"),
            {"id": pending_id}
        ).fetchone()
        
        if not pending:
            raise HTTPException(status_code=404, detail="Pending skill not found or already processed")
        
        skill_name = pending[0]
        
        # Verify target skill exists
        target_skill = db.query(Skill).filter(Skill.id == data.target_skill_id).first()
        if not target_skill:
            raise HTTPException(status_code=404, detail="Target skill not found")
        
        # Update youtube_video_skills to use target skill_id
        db.execute(
            text("""
                UPDATE youtube_video_skills
                SET skill_id = :target_id
                WHERE skill_name = :skill_name AND skill_id IS NULL
            """),
            {"target_id": target_skill.id, "skill_name": skill_name}
        )
        
        # Update pending skill status
        db.execute(
            text("""
                UPDATE pending_skills
                SET status = 'merged',
                    reviewed_by = :reviewer,
                    reviewed_at = NOW(),
                    merged_into = :target_id,
                    notes = :notes
                WHERE id = :id
            """),
            {"reviewer": admin_user.id, "target_id": target_skill.id, "notes": data.notes, "id": pending_id}
        )
        
        db.commit()
        
        logger.info(f"[ADMIN] Merged skill '{skill_name}' into '{target_skill.name}' by {admin_user.email}")
        
        return {
            "message": f"Skill merged into '{target_skill.name}'",
            "target_skill_id": str(target_skill.id),
            "target_skill_name": target_skill.name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error merging skill: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/health")
def health_check():
    return {"status": "ok", "service": "admin_service"}
