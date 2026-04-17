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
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

LLM_MODEL = os.getenv("GAP_LLM_MODEL", os.getenv("LLM_MODEL", "gpt-4o-mini"))

# Lazy client init
_openai_client = None


def _get_client():
    global _openai_client
    if _openai_client is not None:
        return _openai_client

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error(
            "[LLM] ❌ OPENAI_API_KEY is NOT SET — LLM calls will fail. "
            "Set OPENAI_API_KEY in your .env file."
        )
        return None

    try:
        import openai

        _openai_client = openai.OpenAI(api_key=api_key)
        logger.info(f"[LLM] ✓ OpenAI client initialized — model={LLM_MODEL}")
        return _openai_client
    except Exception as e:
        logger.error(f"[LLM] ❌ Failed to init OpenAI client: {e}")
        return None


# ─── JSON Completion ───────────────────────────────────────────────────────────


async def llm_json_completion(
    prompt: str,
    context: str = "",
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.1,
    call_name: str = "llm_json_completion",
) -> Dict[str, Any]:
    """
    Wrapper async cho LLM JSON completion.

    Args:
        prompt: User prompt text
        context: Job/analysis context for logging
        system_prompt: Optional system prompt
        model: Override model (default: GAP_LLM_MODEL)
        temperature: Sampling temperature
        call_name: Human-readable name for this call (for logging, e.g. "extract_jd")

    Retry logic:
      1. Parse raw response
      2. Strip ```json ... ``` fences and retry
      3. Return {} on failure (caller must handle gracefully)

    Logging:
      - call_id: unique UUID per LLM call
      - duration_ms: time taken for API round-trip
      - token usage: prompt_tokens, completion_tokens, total_tokens
      - full prompt dump (all messages)
      - raw response dump (before JSON parse)
    """
    effective_model = model or LLM_MODEL
    call_id = str(uuid.uuid4())[:8]
    client = _get_client()
    if not client:
        logger.error(
            f"[LLM][{call_id}] ❌ llm_json_completion: client is None — "
            "OPENAI_API_KEY missing or init failed"
        )
        return {}

    # ── Build messages ────────────────────────────────────────────────────────
    default_sys = (
        "You are a career and learning expert. "
        "Return ONLY valid JSON. No markdown, no explanation outside JSON."
    )
    messages = [{"role": "system", "content": system_prompt or default_sys}]

    if context:
        messages.append(
            {"role": "system", "content": f"Additional context:\n{context}"}
        )

    messages.append({"role": "user", "content": prompt})

    # ── Log BUILDING (prompt stats) ──────────────────────────────────────────
    _log_llm_input(call_id, effective_model, messages, prompt, context, call_name)

    # ── Call LLM ─────────────────────────────────────────────────────────────
    t0 = time.monotonic()
    raw = None
    usage = None
    try:
        response = client.chat.completions.create(
            model=effective_model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=temperature,
        )
        duration_ms = int((time.monotonic() - t0) * 1000)
        raw = response.choices[0].message.content

        # Extract token usage
        usage = getattr(response, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", None)
        completion_tokens = getattr(usage, "completion_tokens", None)
        total_tokens = getattr(usage, "total_tokens", None)

        _log_llm_output(
            call_id,
            raw,
            "SUCCESS",
            duration_ms,
            prompt_tokens,
            completion_tokens,
            total_tokens,
        )

    except Exception as call_err:
        duration_ms = int((time.monotonic() - t0) * 1000)
        logger.error(
            f"[LLM][{call_id}] ❌ API call failed after {duration_ms}ms: "
            f"{type(call_err).__name__}: {call_err}"
        )
        return {}

    # ── Parse JSON ────────────────────────────────────────────────────────────
    # Attempt 1: parse as-is
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
    """
    Log full LLM INPUT before the call.
    Shows call metadata + every message role/content in full.
    """
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
        # Always show full content — it's already formatted by callers
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
    """
    Log full LLM OUTPUT after the call.
    Shows call metadata + raw response in full.
    """
    raw_len = len(raw)
    preview = raw[:500] + "\n[...]" if raw_len > 500 else raw
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
        f"[LLM OUTPUT] RAW RESPONSE:\n{_indent(raw, 4)}\n"
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
    preview = raw[:200]
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
    temperature: float = 0.3,
    call_name: str = "llm_text_completion",
) -> str:
    """Wrapper cho LLM text (non-JSON) completion with full logging."""
    effective_model = model or LLM_MODEL
    call_id = str(uuid.uuid4())[:8]
    client = _get_client()
    if not client:
        logger.error(f"[LLM][{call_id}] ❌ llm_text_completion: client is None")
        return ""

    default_sys = "You are a helpful career advisor."
    messages = [{"role": "system", "content": system_prompt or default_sys}]
    if context:
        messages.append({"role": "system", "content": context})
    messages.append({"role": "user", "content": prompt})

    _log_llm_input(call_id, effective_model, messages, prompt, context, call_name)

    t0 = time.monotonic()
    try:
        response = client.chat.completions.create(
            model=effective_model,
            messages=messages,
            temperature=temperature,
        )
        duration_ms = int((time.monotonic() - t0) * 1000)
        raw = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)
        _log_llm_output(
            call_id,
            raw,
            "SUCCESS",
            duration_ms,
            getattr(usage, "prompt_tokens", None),
            getattr(usage, "completion_tokens", None),
            getattr(usage, "total_tokens", None),
        )
        return raw
    except Exception as e:
        duration_ms = int((time.monotonic() - t0) * 1000)
        logger.error(
            f"[LLM][{call_id}] ❌ text completion failed after {duration_ms}ms: {e}"
        )
        return ""
