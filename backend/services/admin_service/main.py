from fastapi import FastAPI, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from shared.database import get_db
from shared.models import SystemSetting
from shared.config_utils import config_manager
from shared.ai_service import AI_REGISTRY
from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime
import logging

app = FastAPI(title="Admin Service")
logger = logging.getLogger("admin_service")

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

# --- Endpoints ---

@app.get("/admin/settings", response_model=List[SettingResponse])
def admin_list_settings(request: Request, db: Session = Depends(get_db)):
    """Admin only: Lấy danh sách settings hệ thống."""
    if request.headers.get("X-Is-Admin") != "true":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    settings = db.query(SystemSetting).all()
    return settings

@app.get("/admin/settings/{key}", response_model=SettingResponse)
def admin_get_setting(key: str, request: Request, db: Session = Depends(get_db)):
    """Admin only: Lấy một setting cụ thể."""
    if request.headers.get("X-Is-Admin") != "true":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
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
    key: str, setting_in: SettingUpdate, request: Request, db: Session = Depends(get_db)
):
    """Admin only: Cập nhật hoặc tạo một setting."""
    if request.headers.get("X-Is-Admin") != "true":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
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
    return setting

@app.post("/admin/settings/bulk", response_model=List[SettingResponse])
def admin_bulk_update_settings(
    bulk_in: BulkSettingUpdate, 
    request: Request, 
    db: Session = Depends(get_db)
):
    """Admin only: Cập nhật nhiều settings cùng lúc."""
    if request.headers.get("X-Is-Admin") != "true":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    updated_settings = []
    for item in bulk_in.settings:
        key = item.get("key")
        value = item.get("value")
        
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
    
    db.commit()
    for s in updated_settings:
        db.refresh(s)
        
    return updated_settings

@app.get("/admin/ai-models")
def admin_list_ai_models(request: Request):
    """Admin only: Lấy danh sách các AI model và provider được hỗ trợ."""
    if request.headers.get("X-Is-Admin") != "true":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return AI_REGISTRY

@app.post("/admin/cache/clear")
def admin_clear_cache(request: Request):
    """Admin only: Clear Redis cache (all databases)."""
    if request.headers.get("X-Is-Admin") != "true":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
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
def admin_sync_vector(request: Request, db: Session = Depends(get_db)):
    """Admin only: Trigger VectorDB sync (rebuild skill/job/course vectors)."""
    if request.headers.get("X-Is-Admin") != "true":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
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


@app.get("/admin/health")
def health_check():
    return {"status": "ok", "service": "admin_service"}
