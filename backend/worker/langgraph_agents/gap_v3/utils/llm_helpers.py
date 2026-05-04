"""
LLM Helper utilities — wrapper cho LLM JSON completions.
Delegates to shared.ai_service for unified logging and token tracking.
"""

import json
import os
import logging
import asyncio
import time
import uuid
from typing import Dict, Any, Optional
from shared.config_utils import config_manager
from shared.ai_service import generate_completion
from worker.langgraph_agents.gap_v3.config import GAP_LLM_MODEL as LLM_MODEL

logger = logging.getLogger(__name__)


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
    Delegates to ai_service.generate_completion() for unified logging and security.
    """
    # 1. Xác định Model: Ưu tiên tham số -> Setting DB -> Env -> Default
    m_key = model_key or "AI_MODEL"
    effective_model = (
        model or 
        config_manager.get_setting(m_key) or 
        LLM_MODEL
    )
    
    call_id = str(uuid.uuid4())[:8]
    
    # ── Build system prompt ───────────────────────────────────────────────────
    default_sys = (
        "You are a career and learning expert. "
        "Return ONLY valid JSON. No markdown, no explanation outside JSON."
    )
    sys_msg = system_prompt or default_sys
    
    # Append context to system prompt if provided
    if context:
        sys_msg = f"{sys_msg}\n\nAdditional context:\n{context}"

    # ── Call LLM (security validation happens in generate_completion) ─────────
    try:
        raw = generate_completion(
            prompt=prompt,
            system_prompt=sys_msg,
            json_mode=True,
            model=effective_model,
            temperature=temperature,
            call_name=call_name,
            user_id=user_id
        )

        if not raw:
            logger.error(f"[LLM][{call_id}] Empty response from LLM")
            return {}

    except Exception as call_err:
        logger.error(
            f"[LLM][{call_id}] ❌ LLM call failed: "
            f"{type(call_err).__name__}: {call_err}"
        )
        return {}

    # ── Parse JSON ────────────────────────────────────────────────────────────
    result = _try_parse_json(raw)
    if result is not None:
        logger.debug(f"[LLM][{call_id}] ✓ Parsed JSON directly")
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
        logger.debug(f"[LLM][{call_id}] ✓ Parsed JSON after fence-stripping")
        return result

    # All attempts failed
    logger.error(
        f"[LLM][{call_id}] ❌ JSON parse failed for raw response:\n{raw[:500]}"
    )
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
    """
    Wrapper cho LLM text (non-JSON) completion.
    Delegates to ai_service.generate_completion() for unified logging and security.
    """
    # 1. Xác định Model: Ưu tiên tham số -> Setting DB -> Env -> Default
    m_key = model_key or "CAREER_ADVISOR_MODEL"
    effective_model = (
        model or 
        config_manager.get_setting(m_key) or 
        LLM_MODEL
    )
    
    call_id = str(uuid.uuid4())[:8]
    
    # ── Build system prompt ───────────────────────────────────────────────────
    sys_msg = system_prompt or "You are a helpful career advisor."
    
    # Append context to system prompt if provided
    if context:
        sys_msg = f"{sys_msg}\n\n{context}"

    # ── Call LLM (security validation happens in generate_completion) ─────────
    try:
        raw = generate_completion(
            prompt=prompt,
            system_prompt=sys_msg,
            model=effective_model,
            temperature=temperature,
            call_name=call_name,
            user_id=user_id
        )
        return raw or ""
    except Exception as e:
        logger.error(
            f"[LLM][{call_id}] ❌ text completion failed: {e}"
        )
        return ""
