import logging
import json
import traceback
import concurrent.futures
from typing import Any, Optional, Dict
from sqlalchemy.orm import Session
from shared.database import SessionLocal
from shared.models import SystemLog

logger = logging.getLogger("system_logger")
log_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

def mask_sensitive_data(data: Any) -> Any:
    """
    Recursively mask sensitive keys in a dictionary or list.
    """
    SENSITIVE_KEYS = {
        "api_key", "secret", "password", "token", "access_token", 
        "authorization", "hashed_password", "old_password",
        "raw_text", "cv_text", "file_content", "details"
    }
    
    if isinstance(data, dict):
        return {
            k: ("******" if k.lower() in SENSITIVE_KEYS else mask_sensitive_data(v))
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [mask_sensitive_data(item) for item in data]
    return data

class SystemLogger:
    @staticmethod
    def log(level: str, module: str, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Ghi log vào Database. Sử dụng session riêng để không ảnh hưởng đến transaction chính.
        """
        # Log ra console trước
        log_msg = f"[{module}][{level}] {message}"
        if level == "ERROR" or level == "CRITICAL":
            logger.error(log_msg)
        elif level == "WARNING":
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

        db = SessionLocal()
        try:
            # Mask details before saving
            masked_details = mask_sensitive_data(details) if details else None
            
            new_log = SystemLog(
                level=level,
                module=module,
                message=message,
                details=masked_details
            )
            db.add(new_log)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to persist system log: {e}")
        finally:
            db.close()

    @classmethod
    def log(cls, level: str, module: str, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Ghi log vào Database (Async via ThreadPool). 
        Sử dụng session riêng để không ảnh hưởng đến transaction chính.
        """
        # Log ra console trước (Sync)
        log_msg = f"[{module}][{level}] {message}"
        if level == "ERROR" or level == "CRITICAL":
            logger.error(log_msg)
        elif level == "WARNING":
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

        # Đẩy việc ghi DB vào background thread
        log_executor.submit(cls._persist_log, level, module, message, details)

    @staticmethod
    def _persist_log(level: str, module: str, message: str, details: Optional[Dict[str, Any]] = None):
        """Thực hiện ghi vào DB thực tế."""
        db = SessionLocal()
        try:
            masked_details = mask_sensitive_data(details) if details else None
            new_log = SystemLog(
                level=level,
                module=module,
                message=message,
                details=masked_details
            )
            db.add(new_log)
            db.commit()
        except Exception as e:
            # Ở đây không raise nữa vì đang ở background thread
            pass
        finally:
            db.close()

    @classmethod
    def info(cls, module: str, message: str, details: Optional[Dict[str, Any]] = None):
        cls.log("INFO", module, message, details)

    @classmethod
    def warning(cls, module: str, message: str, details: Optional[Dict[str, Any]] = None):
        cls.log("WARNING", module, message, details)

    @classmethod
    def error(cls, module: str, message: str, details: Optional[Dict[str, Any]] = None, include_traceback: bool = True):
        if include_traceback and not details:
            details = {"traceback": traceback.format_exc()}
        elif include_traceback and details:
            details["traceback"] = traceback.format_exc()
            
        cls.log("ERROR", module, message, details)

    @classmethod
    def critical(cls, module: str, message: str, details: Optional[Dict[str, Any]] = None):
        cls.log("CRITICAL", module, message, details)

    @staticmethod
    def cleanup_old_logs(days: int = 30):
        """
        Dọn dẹp các log cũ hơn 'days' ngày.
        """
        from datetime import datetime, timedelta
        from sqlalchemy import delete
        
        db = SessionLocal()
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            stmt = delete(SystemLog).where(SystemLog.created_at < cutoff_date)
            result = db.execute(stmt)
            db.commit()
            logger.info(f"Cleaned up {result.rowcount} old system logs (older than {days} days).")
            return result.rowcount
        except Exception as e:
            logger.error(f"Failed to cleanup old logs: {e}")
            return 0
        finally:
            db.close()

# Singleton instance
system_logger = SystemLogger()
