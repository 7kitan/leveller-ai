import logging
import os
from datetime import datetime
from sqlalchemy.orm import Session
from shared.models import User
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
            config_manager.get_setting("daily_analysis_limit") or 
            os.getenv("DAILY_ANALYSIS_LIMIT", "10")
        )

    @staticmethod
    def get_token_limit(user: User) -> int:
        """Lấy giới hạn tokens: Ưu tiên User > Global Config > Env."""
        if user.daily_token_limit > 0:
            return user.daily_token_limit
        
        return int(
            config_manager.get_setting("user_daily_token_limit") or 
            os.getenv("DAILY_TOKEN_LIMIT", "50000")
        )

    @classmethod
    def check_analysis_quota(cls, user: User, db: Session) -> bool:
        """
        Kiểm tra và tăng số lượng phân tích (Atomic via Redis).
        Returns True nếu còn quota, False nếu hết.
        """
        if user.is_admin:
            return True

        limit = cls.get_analysis_limit(user)
        today = datetime.now().strftime("%Y%m%d")
        quota_key = f"analysis_count:{user.id}:{today}"
        
        # Increment atomic (using Lua script to ensure TTL)
        current = quota_cache.incr_with_expire(quota_key, 86400)
            
        if current > limit:
            logger.warning(f"User {user.id} analysis quota exceeded: {current}/{limit}")
            return False
            
        return True

    @classmethod
    def check_token_quota(cls, user: User, db: Session) -> bool:
        """
        Kiểm tra giới hạn token hàng ngày.
        (Usage được tính từ DB logs thực tế).
        """
        if user.is_admin:
            return True

        from shared.token_manager import get_user_daily_usage
        
        limit = cls.get_token_limit(user)
        usage = get_user_daily_usage(str(user.id), db)
        
        if usage >= limit:
            logger.warning(f"User {user.id} token quota exceeded: {usage}/{limit}")
            return False
            
        return True

quota_manager = QuotaManager()
