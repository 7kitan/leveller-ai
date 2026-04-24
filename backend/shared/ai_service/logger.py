import logging
import time
from typing import Optional, Dict, Any
from shared.database import SessionLocal
from shared.models import LLMLog

logger = logging.getLogger("ai_service_logger")

def log_llm_call(
    user_id: Optional[str],
    model_id: str,
    provider: str,
    call_type: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    latency_ms: int = 0,
    status: str = "success",
    error_message: Optional[str] = None,
    request_metadata: Optional[Dict[str, Any]] = None
):
    """
    Saves an LLM call log entry to the database.
    """
    try:
        with SessionLocal() as db:
            log_entry = LLMLog(
                user_id=user_id,
                model_id=model_id,
                provider=provider,
                call_type=call_type,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                latency_ms=latency_ms,
                status=status,
                error_message=error_message,
                request_metadata=request_metadata
            )
            db.add(log_entry)
            db.commit()
            logger.info(f"[LLM LOG] Saved log for {model_id} | user={user_id} | tokens={prompt_tokens + completion_tokens}")
    except Exception as e:
        logger.error(f"[LLM LOG] Failed to save log entry: {e}")
