import logging
import os
from datetime import datetime
from sqlalchemy.orm import Session
from shared.models import User, UserRole
from shared.config_utils import config_manager
from shared.redis_client import quota_cache

logger = logging.getLogger("quota_manager")

class QuotaManager:
    @staticmethod
    def get_analysis_limit(user: User) -> int:
        """Lấy giới hạn phân tích: Ưu tiên User > Global Config > Env."""
        if user.daily_analysis_limit > 0:
            return user.daily_analysis_limit
        
        return int(
            config_manager.get_setting("DAILY_ANALYSIS_LIMIT") or 
            os.getenv("DAILY_ANALYSIS_LIMIT", "10")
        )

    @staticmethod
    def get_token_limit(user: User) -> int:
        """Lấy giới hạn tokens: Ưu tiên User > Global Config > Env."""
        if user.daily_token_limit > 0:
            return user.daily_token_limit
        
        return int(
            config_manager.get_setting("USER_DAILY_TOKEN_LIMIT") or 
            os.getenv("DAILY_TOKEN_LIMIT", "50000")
        )

    @classmethod
    def check_analysis_quota(cls, user: User, db: Session) -> bool:
        """
        BUG-021 FIX: Kiểm tra và tăng số lượng phân tích (Atomic via Redis Lua script).
        Uses atomic check-and-increment to prevent race conditions.
        Returns True nếu còn quota, False nếu hết.
        """
        if user.role == UserRole.ADMIN:
            return True

        limit = cls.get_analysis_limit(user)
        today = datetime.now().strftime("%Y%m%d")
        quota_key = f"analysis_count:{user.id}:{today}"
        
        # BUG-021 FIX: Use Lua script for atomic check-and-increment
        # This prevents race condition where user can exceed quota by 1 on concurrent requests
        lua_script = """
        local key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local ttl = tonumber(ARGV[2])
        
        local current = redis.call('GET', key)
        if current == false then
            current = 0
        else
            current = tonumber(current)
        end
        
        if current >= limit then
            return -1
        end
        
        local new_val = redis.call('INCR', key)
        if new_val == 1 then
            redis.call('EXPIRE', key, ttl)
        end
        
        return new_val
        """
        
        try:
            result = quota_cache.eval(lua_script, 1, quota_key, limit, 86400)
            
            if result == -1:
                logger.warning(f"User {user.id} analysis quota exceeded: limit={limit}")
                return False
            
            logger.info(f"User {user.id} analysis quota check passed: {result}/{limit}")
            return True
            
        except Exception as e:
            logger.error(f"Quota check failed for user {user.id}: {e}")
            # Fallback to non-atomic check (less secure but prevents blocking)
            current = quota_cache.incr_with_expire(quota_key, 86400)
            if current > limit:
                return False
            return True

    @classmethod
    def check_token_quota(cls, user: User, db: Session) -> bool:
        """
        Kiểm tra giới hạn token hàng ngày.
        (Usage được tính từ DB logs thực tế).
        """
        if user.role == UserRole.ADMIN:
            return True

        from shared.token_manager import get_user_daily_usage
        
        limit = cls.get_token_limit(user)
        usage = get_user_daily_usage(str(user.id), db)
        
        if usage >= limit:
            logger.warning(f"User {user.id} token quota exceeded: {usage}/{limit}")
            return False
            
        return True

quota_manager = QuotaManager()
