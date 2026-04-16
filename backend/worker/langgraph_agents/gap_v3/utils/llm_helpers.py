"""
LLM Helper utilities — wrapper cho LLM JSON completions.
"""

import json
import os
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Lazy client init
_openai_client = None


def _get_client():
    global _openai_client
    if _openai_client is None:
        import openai

        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            _openai_client = openai.OpenAI(api_key=api_key)
    return _openai_client


LLM_MODEL = os.getenv("GAP_LLM_MODEL", os.getenv("LLM_MODEL", "gpt-4o-mini"))


async def llm_json_completion(
    prompt: str,
    context: str = "",
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.1,
) -> Dict[str, Any]:
    """
    Wrapper async cho LLM JSON completion.
    Tự động retry 1 lần nếu JSON parse fail.

    Args:
        prompt: User prompt
        context: Additional context (job context, etc.)
        system_prompt: Custom system prompt. Nếu None → dùng default.
        model: Override model name
        temperature: Randomness (0.1 = consistent)

    Returns:
        Parsed JSON dict hoặc {} nếu fail
    """
    client = _get_client()
    if not client:
        logger.warning("OpenAI client not initialized. Returning empty result.")
        return {}

    # Build messages
    if system_prompt is None:
        system_prompt = (
            "You are a career and learning expert. "
            "Return ONLY valid JSON. No markdown, no explanation outside JSON."
        )

    messages = [
        {"role": "system", "content": system_prompt},
    ]

    if context:
        messages.append(
            {"role": "system", "content": f"Additional context:\n{context}"}
        )

    messages.append({"role": "user", "content": prompt})

    # Call LLM
    try:
        response = client.chat.completions.create(
            model=model or LLM_MODEL,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=temperature,
        )
        raw = response.choices[0].message.content

        # First try: parse as-is
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # Second try: strip markdown code fences
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1] if cleaned.endswith("```") else lines[1:])
        result = json.loads(cleaned)
        logger.debug(f"LLM JSON parsed after cleaning. Model: {model or LLM_MODEL}")
        return result

    except json.JSONDecodeError as e:
        logger.error(
            f"LLM JSON parse failed (2 attempts): {e}. Raw: {raw[:200] if raw else 'empty'}"
        )
        return {}

    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return {}


async def llm_text_completion(
    prompt: str,
    context: str = "",
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.3,
) -> str:
    """Wrapper cho LLM text (non-JSON) completion."""
    client = _get_client()
    if not client:
        return ""

    if system_prompt is None:
        system_prompt = "You are a helpful career advisor."

    messages = [
        {"role": "system", "content": system_prompt},
    ]
    if context:
        messages.append({"role": "system", "content": context})
    messages.append({"role": "user", "content": prompt})

    try:
        response = client.chat.completions.create(
            model=model or LLM_MODEL,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        logger.error(f"LLM text completion failed: {e}")
        return ""
