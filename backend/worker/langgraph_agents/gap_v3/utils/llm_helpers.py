"""
LLM Helper utilities — wrapper cho LLM JSON completions.
Enhanced with full data logging: call_id, duration, token usage,
complete prompt/response dump for debugging.
"""

import json
import os
import logging
import asyncio
import time
import uuid
import re
from typing import Dict, Any, Optional, List
from shared.config_utils import config_manager
from shared.ai_service import generate_completion
from worker.langgraph_agents.gap_v3.config import GAP_LLM_MODEL as LLM_MODEL

logger = logging.getLogger(__name__)

# ─── Prompt Size Limits ────────────────────────────────────────────────────────
# SECURITY: Prevent prompt overflow and excessive token usage
MAX_PROMPT_CHARS = 100000  # ~25K tokens - safe for GPT-4o-mini (128K context)
MAX_PROMPT_TOKENS_ESTIMATE = 25000  # Conservative estimate (4 chars per token)

# ─── Prompt Injection Detection ────────────────────────────────────────────────
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"disregard\s+(all\s+)?previous",
    r"forget\s+(all\s+)?previous",
    r"new\s+instructions?:",
    r"system\s*:\s*you\s+are",
    r"override\s+system",
    r"bypass\s+security",
]


def validate_prompt_size(messages: List[Dict[str, str]], call_name: str = "llm_call") -> None:
    """
    SECURITY: Validate total prompt size to prevent overflow and excessive costs.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        call_name: Name of the calling function for logging
        
    Raises:
        ValueError: If prompt exceeds size limits
    """
    total_chars = sum(len(m.get("content", "")) for m in messages)
    
    if total_chars > MAX_PROMPT_CHARS:
        error_msg = (
            f"[{call_name}] Prompt too large: {total_chars:,} chars "
            f"(max {MAX_PROMPT_CHARS:,}). "
            f"Estimated {total_chars // 4:,} tokens (max {MAX_PROMPT_TOKENS_ESTIMATE:,}). "
            f"Please reduce input size (shorter JD, fewer skills, etc.)"
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


# ─── JSON Completion ───────────────────────────────────────────────────────────


async def llm_json_completion(
    prompt: str,
    context: str = "",
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    model_key: Optional[str] = None,
    temperature: float = 0.1,
    call_name: str = "llm_json_completion",
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Wrapper async cho LLM JSON completion.
    Hỗ trợ đa provider (OpenAI, Gemini) và cấu hình động từ DB.
    """
    # 1. Xác định Model: Ưu tiên tham số -> Setting DB -> Env -> Default
    m_key = model_key or "AI_MODEL"
    effective_model = (
        model or 
        config_manager.get_setting(m_key) or 
        LLM_MODEL
    )
    
    call_id = str(uuid.uuid4())[:8]
    provider = "unknown" # Provider is now managed inside generate_completion
    
    # ── Build messages ────────────────────────────────────────────────────────
    default_sys = (
        "You are a career and learning expert. "
        "Return ONLY valid JSON. No markdown, no explanation outside JSON."
    )
    sys_msg = system_prompt or default_sys
    messages = [{"role": "system", "content": sys_msg}]

    if context:
        messages.append(
            {"role": "system", "content": f"Additional context:\n{context}"}
        )
    messages.append({"role": "user", "content": prompt})

    # ── SECURITY: Validate prompt size ───────────────────────────────────────
    try:
        validate_prompt_size(messages, call_name)
    except ValueError as e:
        logger.error(f"[LLM][{call_id}] Prompt size validation failed: {e}")
        return {"error": str(e), "error_type": "prompt_too_large"}

    # ── Log BUILDING (prompt stats) ──────────────────────────────────────────
    _log_llm_input(call_id, effective_model, messages, prompt, context, call_name)

    # ── Call LLM ─────────────────────────────────────────────────────────────
    t0 = time.monotonic()
    raw = None
    try:
        # Gọi generate_completion từ ai_service
        raw = generate_completion(
            prompt=prompt,
            system_prompt=f"{sys_msg}\nAdditional context: {context}" if context else sys_msg,
            json_mode=True,
            model=effective_model,
            temperature=temperature,
            call_name=call_name,
            user_id=user_id
        )
        duration_ms = int((time.monotonic() - t0) * 1000)

        if not raw:
            raise ValueError("Empty response from LLM")

        # Log output (Token usage temporarily None for Gemini until we map its response)
        _log_llm_output(
            call_id,
            raw,
            "SUCCESS",
            duration_ms,
            None, None, None # Usage stats
        )

    except Exception as call_err:
        duration_ms = int((time.monotonic() - t0) * 1000)
        logger.error(
            f"[LLM][{call_id}] ❌ LLM call failed ({provider}) after {duration_ms}ms: "
            f"{type(call_err).__name__}: {call_err}"
        )
        return {}

    # ── Parse JSON ────────────────────────────────────────────────────────────
    result = _try_parse_json(raw)
    if result is not None:
        _log_parsed_result(call_id, result, "direct")
        return result

    # Attempt 2: strip markdown fences ```json ... ```
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        if len(lines) >= 2 and lines[0].strip().lstrip("`").strip().startswith("json"):
            cleaned = "\n".join(lines[1:])
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()

    result = _try_parse_json(cleaned)
    if result is not None:
        _log_parsed_result(call_id, result, "fence-stripped")
        return result

    # All attempts failed
    logger.error(
        f"[LLM][{call_id}] ❌ JSON parse failed for raw response:\n{raw[:500]}"
    )
    _log_parse_failure(call_id, raw)
    return {}


# ─── Helpers ───────────────────────────────────────────────────────────────


def _try_parse_json(raw: Optional[str]) -> Optional[Dict[str, Any]]:
    """Parse string as JSON. Return None if fails."""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _log_llm_input(
    call_id: str,
    model: str,
    messages: list,
    prompt: str,
    context: str,
    call_name: str,
):
    """Log full LLM INPUT before the call."""
    total_chars = sum(len(m["content"]) for m in messages)
    sep = "═" * 70
    logger.info(
        f"\n{sep}\n"
        f"[LLM INPUT] ┌─── {call_name}\n"
        f"            │ call_id : {call_id}\n"
        f"            │ model   : {model}\n"
        f"            │ msgs    : {len(messages)}\n"
        f"            │ ~chars  : {total_chars}\n"
        f"            │ context : {context or '(none)'}\n"
        f"            └─────────\n"
    )
    for i, msg in enumerate(messages):
        role = msg["role"].upper()
        content = msg["content"]
        logger.info(f"[LLM INPUT] ── [{i}] {role} ──\n{_indent(content, 4)}\n")
    logger.info(f"{sep}")


def _log_llm_output(
    call_id: str,
    raw: str,
    status: str,
    duration_ms: int,
    prompt_tokens: Optional[int],
    completion_tokens: Optional[int],
    total_tokens: Optional[int],
):
    """Log full LLM OUTPUT after the call."""
    raw_len = len(raw) if raw else 0
    sep = "─" * 70
    token_line = ""
    if total_tokens is not None:
        token_line = (
            f"  │ prompt_tokens : {prompt_tokens}\n"
            f"  │ completion_tokens : {completion_tokens}\n"
            f"  │ total_tokens  : {total_tokens}\n"
        )

    logger.info(
        f"\n{sep}\n"
        f"[LLM OUTPUT] ┌─── {call_id}\n"
        f"             │ status      : {status}\n"
        f"             │ duration_ms : {duration_ms}\n"
        f"             │ raw_chars   : {raw_len}\n"
        f"{token_line}"
        f"             └─────────\n"
        f"[LLM OUTPUT] RAW RESPONSE:\n{_indent(raw or '(none)', 4)}\n"
        f"{sep}\n"
    )


def _log_parsed_result(call_id: str, result: Dict, source: str):
    """Log successfully parsed JSON result."""
    keys = list(result.keys())
    logger.info(
        f"[LLM PARSED][{call_id}] ✓ Parsed ({source}) — call_id={call_id} keys={keys}"
    )
    try:
        formatted = json.dumps(result, ensure_ascii=False, indent=2)
        logger.info(
            f"[LLM PARSED][{call_id}] FULL RESULT:\n{_indent(formatted, 4)}"
        )
    except Exception:
        logger.info(f"[LLM PARSED][{call_id}] Result preview: {str(result)[:1000]}")


def _log_parse_failure(call_id: str, raw: str):
    """Log parse failure details."""
    preview = raw[:200] if raw else "(none)"
    logger.error(f"[LLM PARSE FAIL][{call_id}] Raw that failed:\n{_indent(preview, 4)}")


def _indent(text: str, spaces: int) -> str:
    pad = " " * spaces
    return "\n".join(pad + line for line in text.split("\n"))


# ─── Text Completion (non-JSON) ──────────────────────────────────────────────


async def llm_text_completion(
    prompt: str,
    context: str = "",
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    model_key: Optional[str] = None,
    temperature: float = 0.3,
    call_name: str = "llm_text_completion",
    user_id: Optional[str] = None
) -> str:
    """Wrapper cho LLM text (non-JSON) completion with full logging."""
    # 1. Xác định Model: Ưu tiên tham số -> Setting DB -> Env -> Default
    m_key = model_key or "CAREER_ADVISOR_MODEL"
    effective_model = (
        model or 
        config_manager.get_setting(m_key) or 
        LLM_MODEL
    )
    
    call_id = str(uuid.uuid4())[:8]
    provider = "unknown"
    
    messages = [{"role": "system", "content": system_prompt or "You are a helpful career advisor."}]
    if context:
        messages.append({"role": "system", "content": context})
    messages.append({"role": "user", "content": prompt})

    # ── SECURITY: Validate prompt size ───────────────────────────────────────
    try:
        validate_prompt_size(messages, call_name)
    except ValueError as e:
        logger.error(f"[LLM][{call_id}] Prompt size validation failed: {e}")
        return ""

    _log_llm_input(call_id, effective_model, messages, prompt, context, call_name)

    t0 = time.monotonic()
    try:
        raw = generate_completion(
            prompt=prompt,
            system_prompt=f"{system_prompt or 'You are a helpful career advisor.'}\n{context}" if context else system_prompt,
            model=effective_model,
            temperature=temperature,
            call_name=call_name,
            user_id=user_id
        )
        duration_ms = int((time.monotonic() - t0) * 1000)
        
        _log_llm_output(
            call_id,
            raw,
            "SUCCESS",
            duration_ms,
            None, None, None
        )
        return raw or ""
    except Exception as e:
        duration_ms = int((time.monotonic() - t0) * 1000)
        logger.error(
            f"[LLM][{call_id}] ❌ text completion failed ({provider}) after {duration_ms}ms: {e}"
        )
        return ""
