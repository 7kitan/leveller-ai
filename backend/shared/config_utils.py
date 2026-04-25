import os
import json
import logging
from typing import Any, Optional, Type, TypeVar
from shared.redis_client import config_cache
from shared.models import SystemSetting
from shared.database import SessionLocal
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

T = TypeVar("T")

class ConfigManager:
    """
    Centralized configuration manager with 4-layer hierarchy:
    1. Redis Cache (Hot)
    2. Database (Source of Truth for dynamic settings)
    3. Environment Variables (Default/Static)
    4. Hardcoded Default
    
    NOTE: All keys are normalized to UPPERCASE for consistency with env vars.
    """
    
    @staticmethod
    def get_setting(key: str, default: Any = None, cast: Optional[Type[T]] = None) -> Any:
        # Normalize key to UPPERCASE for consistency
        key = key.upper()
        
        # 1. Check Redis Cache
        try:
            cached_val = config_cache.get(key)
            if cached_val is not None:
                val = json.loads(cached_val)
                return ConfigManager._cast_value(val, cast)
        except Exception as e:
            logger.error(f"Error fetching setting '{key}' from Redis: {e}")

        # 2. Check Database
        db_val = None
        try:
            with SessionLocal() as db:
                setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
                if setting:
                    db_val = setting.value
                    # Update cache for next time
                    config_cache.set(key, json.dumps(db_val), ex=3600)
        except Exception as e:
            logger.error(f"Error fetching setting '{key}' from DB: {e}")

        if db_val is not None:
            return ConfigManager._cast_value(db_val, cast)

        # 3. Check Environment Variables
        env_val = os.getenv(key)  # Already uppercase
        if env_val is not None:
            return ConfigManager._cast_value(env_val, cast)

        # 4. Fallback to hardcoded default
        return ConfigManager._cast_value(default, cast)

    @staticmethod
    def invalidate_cache(key: str):
        """Remove a key from Redis to force a refresh from DB."""
        # Normalize key to UPPERCASE
        key = key.upper()
        try:
            config_cache.delete(key)
        except Exception as e:
            logger.error(f"Error invalidating cache for '{key}': {e}")

    @staticmethod
    def _cast_value(value: Any, cast: Optional[Type[T]]) -> Any:
        if value is None or cast is None:
            return value
        
        try:
            if cast == bool:
                if isinstance(value, str):
                    return value.lower() in ("true", "1", "yes", "on")
                return bool(value)
            return cast(value)
        except (ValueError, TypeError):
            logger.warning(f"Failed to cast value {value} to {cast}")
            return value

config_manager = ConfigManager()
