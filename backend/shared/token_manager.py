import logging
from datetime import datetime, time
from sqlalchemy import func, and_
from sqlalchemy.orm import Session
from shared.models import LLMLog, User
from shared.config_utils import config_manager

logger = logging.getLogger("token_manager")

def get_user_daily_usage(user_id: str, db: Session) -> int:
    """
    Tính tổng số tokens một user đã sử dụng trong ngày hôm nay.
    """
    today_start = datetime.combine(datetime.now().date(), time.min)
    
    total_tokens = db.query(func.sum(LLMLog.total_tokens))\
        .filter(
            and_(
                LLMLog.user_id == user_id,
                LLMLog.created_at >= today_start,
                LLMLog.status == "success"
            )
        ).scalar() or 0
    
    return int(total_tokens)

def is_user_over_limit(user_id: str, db: Session) -> bool:
    """
    Kiểm tra xem user có vượt quá giới hạn token hàng ngày không.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    
    # 1. Lấy giới hạn: Ưu tiên override trên user, nếu không dùng global setting
    limit = user.daily_token_limit
    if limit <= 0:
        limit = int(config_manager.get_setting("USER_DAILY_TOKEN_LIMIT", 50000))
    
    # 2. Lấy usage hiện tại
    usage = get_user_daily_usage(user_id, db)
    
    if usage >= limit:
        logger.warning(f"User {user_id} over limit: {usage}/{limit}")
        return True
    
    return False
