import os
import logging
import time
import uuid
import litellm
from typing import Optional, Dict, Any
from .registry import get_model_info
from shared.config_utils import config_manager
from .logger import log_llm_call
from shared.database import SessionLocal
from shared.models import User

logger = logging.getLogger("ai_service")

# Ensure LiteLLM uses our environment variables
# LiteLLM looks for GOOGLE_API_KEY for gemini models by default
os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY", "")

# Suppress litellm logging unless needed for debugging
litellm.set_verbose = False

def get_active_model_id(override_model: Optional[str] = None, setting_key: str = "ai_model") -> str:
    """
    Resolve the model ID to use.
    """
    if override_model:
        return override_model
    
    db_setting = config_manager.get_setting(setting_key)
    if db_setting:
        return db_setting

    if setting_key != "ai_model":
        general_setting = config_manager.get_setting("AI_MODEL")
        if general_setting:
            return general_setting
        
    return os.getenv("LLM_MODEL", "gpt-4o-mini")

def generate_completion(
    prompt: str,
    system_prompt: str = "You are a helpful assistant.",
    model: Optional[str] = None,
    model_key: str = "ai_model",
    json_mode: bool = False,
    temperature: float = 0.1,
    call_name: str = "ai_service_call",
    user_id: Optional[str] = None
) -> Optional[str]:
    """
    Unified entry point using LiteLLM.
    Handles routing, automatic fallback, logging, and performance tracking.
    """
    if user_id is not None:
        logger.info(f"[AI SERVICE] Received user_id: {user_id} (type: {type(user_id)})")
        with SessionLocal() as db:
            from shared.quota_manager import quota_manager
            # Convert to UUID if it's a string, to be safe
            u_id = user_id
            if isinstance(user_id, str) and user_id.strip():
                try:
                    import uuid as _uuid
                    u_id = _uuid.UUID(user_id)
                except ValueError:
                    pass
            
            user = db.query(User).filter(User.id == u_id).first()
            if user and not quota_manager.check_token_quota(user, db):
                logger.error(f"User {user_id} has exceeded daily token limit. Blocking call.")
                return None

    model_id = get_active_model_id(model, setting_key=model_key)
    
    # Map model ID to LiteLLM format if needed
    # (e.g., gemini-1.5-flash -> gemini/gemini-1.5-flash)
    litellm_model = model_id
    if "gemini" in model_id and "/" not in model_id:
        litellm_model = f"gemini/{model_id}"
    
    # Get fallback list from config
    fallback_model = config_manager.get_setting("FALLBACK_AI_MODEL", "gpt-4o-mini")
    fallbacks = [fallback_model] if fallback_model and fallback_model != model_id else []
    
    # Map fallbacks to LiteLLM format
    litellm_fallbacks = []
    for f in fallbacks:
        if "gemini" in f and "/" not in f:
            litellm_fallbacks.append(f"gemini/{f}")
        else:
            litellm_fallbacks.append(f)

    call_id = str(uuid.uuid4())[:8]
    t0 = time.monotonic()
    
    try:
        logger.info(f"[AI SERVICE][{call_id}] Calling LiteLLM | model={litellm_model} | fallbacks={litellm_fallbacks}")
        
        response = litellm.completion(
            model=litellm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            response_format={"type": "json_object"} if json_mode else None,
            fallbacks=litellm_fallbacks if litellm_fallbacks else None
        )
        
        duration = int((time.monotonic() - t0) * 1000)
        content = response.choices[0].message.content
        usage = response.usage
        
        # Log success to DB
        log_llm_call(
            user_id=user_id,
            model_id=response.model, # Model actually used (could be fallback)
            provider=get_model_info(response.model.split("/")[-1]).provider if get_model_info(response.model.split("/")[-1]) else "unknown",
            call_type=call_name,
            prompt_tokens=getattr(usage, 'prompt_tokens', 0),
            completion_tokens=getattr(usage, 'completion_tokens', 0),
            latency_ms=duration,
            status="success",
            request_metadata={"call_id": call_id, "original_model": model_id}
        )
        
        return content

    except Exception as e:
        duration = int((time.monotonic() - t0) * 1000)
        logger.error(f"[AI SERVICE][{call_id}] ❌ LiteLLM failed all attempts: {e}")
        
        # Log failure to DB
        log_llm_call(
            user_id=user_id,
            model_id=model_id,
            provider="unknown",
            call_type=call_name,
            latency_ms=duration,
            status="failed",
            error_message=str(e),
            request_metadata={"call_id": call_id}
        )
        return None
