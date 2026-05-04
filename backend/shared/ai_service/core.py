import os
import logging
import time
import uuid
import re
import litellm
from typing import Optional, Dict, Any, List
from .registry import get_model_info
from shared.config_utils import config_manager
from .logger import log_llm_call
from shared.database import SessionLocal
from shared.models import User

logger = logging.getLogger("ai_service")

# ─── Security Constants ──────────────────────────────────────────────────────
MAX_PROMPT_CHARS = 100000  # ~25K tokens - safe for GPT-4o-mini (128K context)
MAX_PROMPT_TOKENS_ESTIMATE = 25000  # Conservative estimate (4 chars per token)

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"disregard\s+(all\s+)?previous",
    r"forget\s+(all\s+)?previous",
    r"new\s+instructions?:",
    r"system\s*:\s*you\s+are",
    r"override\s+system",
    r"bypass\s+security",
]

# ─── Benchmark Extension Hook ────────────────────────────────────────────────
# Integrated directly in generate_completion for performance

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

def validate_prompt_size(prompt: str, system_prompt: str, call_name: str = "ai_service") -> None:
    """
    SECURITY: Validate total prompt size to prevent overflow and excessive costs.
    
    Args:
        prompt: User prompt text
        system_prompt: System prompt text
        call_name: Name of the calling function for logging
        
    Raises:
        ValueError: If prompt exceeds size limits
    """
    total_chars = len(prompt) + len(system_prompt)
    
    if total_chars > MAX_PROMPT_CHARS:
        error_msg = (
            f"[{call_name}] Prompt too large: {total_chars:,} chars "
            f"(max {MAX_PROMPT_CHARS:,}). "
            f"Estimated {total_chars // 4:,} tokens (max {MAX_PROMPT_TOKENS_ESTIMATE:,}). "
            f"Please reduce input size."
        )
        logger.error(f"[PROMPT SIZE VIOLATION] {error_msg}")
        raise ValueError(error_msg)
    
    # Log warning if approaching limit (>80%)
    if total_chars > MAX_PROMPT_CHARS * 0.8:
        logger.warning(
            f"[{call_name}] Prompt size approaching limit: {total_chars:,} chars "
            f"({total_chars / MAX_PROMPT_CHARS * 100:.1f}% of max)"
        )

def detect_prompt_injection(text: str) -> bool:
    """
    SECURITY: Detect potential prompt injection attempts.
    
    Args:
        text: User-provided text to check
        
    Returns:
        True if suspicious patterns detected, False otherwise
    """
    if not text:
        return False
    
    text_lower = text.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text_lower):
            logger.warning(
                f"[PROMPT INJECTION DETECTED] Pattern matched: {pattern} "
                f"in text: {text[:200]}..."
            )
            return True
    
    return False

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
    Handles routing, automatic fallback, logging, security validation, and performance tracking.
    """
    # ── SECURITY: Validate prompt size ───────────────────────────────────────
    try:
        validate_prompt_size(prompt, system_prompt, call_name)
    except ValueError as e:
        logger.error(f"[AI SERVICE] Prompt validation failed: {e}")
        return None
    
    # ── SECURITY: Detect prompt injection ────────────────────────────────────
    if detect_prompt_injection(prompt):
        logger.error(f"[AI SERVICE] Potential prompt injection detected in user prompt. Blocking call.")
        return None
    
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
    elif "claude" in model_id and "/" not in model_id:
        litellm_model = f"anthropic/{model_id}"
    
    # Get fallback list from config
    fallback_model = config_manager.get_setting("FALLBACK_AI_MODEL", "gpt-4o-mini")
    fallbacks = [fallback_model] if fallback_model and fallback_model != model_id else []
    
    # Map fallbacks to LiteLLM format
    litellm_fallbacks = []
    for f in fallbacks:
        if "gemini" in f and "/" not in f:
            litellm_fallbacks.append(f"gemini/{f}")
        elif "claude" in f and "/" not in f:
            litellm_fallbacks.append(f"anthropic/{f}")
        else:
            litellm_fallbacks.append(f)

    call_id = str(uuid.uuid4())[:8]
    t0 = time.monotonic()
    
    # ── Log INPUT (full prompt) ──────────────────────────────────────────────
    logger.info(
        f"\n{'='*70}\n"
        f"[AI SERVICE][{call_id}] 📤 SENDING TO LLM\n"
        f"  Model: {litellm_model}\n"
        f"  Fallbacks: {litellm_fallbacks}\n"
        f"  Call: {call_name}\n"
        f"  Temperature: {temperature}\n"
        f"  JSON Mode: {json_mode}\n"
        f"{'='*70}\n"
        f"[SYSTEM PROMPT]:\n{system_prompt}\n"
        f"{'-'*70}\n"
        f"[USER PROMPT]:\n{prompt[:2000]}{'...(truncated)' if len(prompt) > 2000 else ''}\n"
        f"{'='*70}"
    )
    
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
        
        # ── Log OUTPUT (full response) ───────────────────────────────────────────
        logger.info(
            f"\n{'='*70}\n"
            f"[AI SERVICE][{call_id}] 📥 RECEIVED FROM LLM\n"
            f"  Model Used: {response.model}\n"
            f"  Duration: {duration}ms\n"
            f"  Prompt Tokens: {getattr(usage, 'prompt_tokens', 0)}\n"
            f"  Completion Tokens: {getattr(usage, 'completion_tokens', 0)}\n"
            f"  Total Tokens: {getattr(usage, 'total_tokens', 0)}\n"
            f"{'='*70}\n"
            f"[RESPONSE]:\n{content[:2000]}{'...(truncated)' if len(content) > 2000 else ''}\n"
            f"{'='*70}"
        )
        
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

        # --- Benchmark Extension Hook ---
        try:
            from worker.extensions.benchmark.interceptor import benchmark_data
            bench_data = benchmark_data.get()
            if bench_data is not None:
                if "calls" not in bench_data: bench_data["calls"] = []
                bench_data["calls"].append({
                    "prompt_tokens": getattr(usage, 'prompt_tokens', 0),
                    "completion_tokens": getattr(usage, 'completion_tokens', 0),
                    "latency_ms": duration,
                    "model": response.model
                })
        except Exception:
            pass
        
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
