import logging
import json
import traceback
from typing import Any, Optional, Dict
from sqlalchemy.orm import Session
from shared.database import SessionLocal
from shared.models import SystemLog

logger = logging.getLogger("system_logger")

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
            new_log = SystemLog(
                level=level,
                module=module,
                message=message,
                details=details
            )
            db.add(new_log)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to persist system log: {e}")
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
