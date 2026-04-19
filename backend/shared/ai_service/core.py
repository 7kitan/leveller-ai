import os
import logging
import time
import uuid
from typing import Optional, Dict, Any
from .registry import get_model_info
from .factory import AIProviderFactory
from shared.config_utils import config_manager

logger = logging.getLogger("ai_service")

def get_active_model_id(override_model: Optional[str] = None) -> str:
    """
    Resolve the model ID to use.
    Hierarchy: 
    1. Explicit override passed to function.
    2. Dynamic setting from Database (via ConfigManager).
    3. Environment variable `LLM_MODEL`.
    4. Default fallback: 'gpt-4o-mini'.
    """
    if override_model:
        return override_model
    
    db_setting = config_manager.get_setting("ai_model")
    if db_setting:
        return db_setting
        
    return os.getenv("LLM_MODEL", "gpt-4o-mini")

def generate_completion(
    prompt: str,
    system_prompt: str = "You are a helpful assistant.",
    model: Optional[str] = None,
    json_mode: bool = False,
    temperature: float = 0.1,
    call_name: str = "ai_service_call"
) -> Optional[str]:
    """
    Unified entry point for AI text/JSON completions.
    Handles routing, logging, and performance tracking.
    """
    model_id = get_active_model_id(model)
    model_info = get_model_info(model_id)
    
    # Simple fallback if model not in registry (assume OpenAI-compatible)
    provider = model_info.provider if model_info else "openai"
    
    call_id = str(uuid.uuid4())[:8]
    logger.info(f"[AI SERVICE][{call_id}] Calling completion | model={model_id} | provider={provider} | name={call_name}")
    
    t0 = time.monotonic()
    
    try:
        if provider == "openai":
            return _call_openai(call_id, model_id, system_prompt, prompt, json_mode, temperature)
        elif provider == "google":
            return _call_google(call_id, model_id, system_prompt, prompt, json_mode, temperature)
        else:
            logger.error(f"[AI SERVICE][{call_id}] Provider {provider} not supported.")
            return None
    except Exception as e:
        duration = int((time.monotonic() - t0) * 1000)
        logger.error(f"[AI SERVICE][{call_id}] ❌ Failed ({provider}) after {duration}ms: {e}")
        return None

def _call_openai(call_id: str, model: str, system: str, prompt: str, json_mode: bool, temp: float) -> Optional[str]:
    client = AIProviderFactory.get_openai_client()
    if not client: return None
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"} if json_mode else None,
        temperature=temp
    )
    return response.choices[0].message.content

def _call_google(call_id: str, model: str, system: str, prompt: str, json_mode: bool, temp: float) -> Optional[str]:
    genai = AIProviderFactory.get_google_sdk()
    if not genai: return None
    
    # Map model name for SDK if needed
    full_model_name = model if model.startswith("models/") else f"models/{model}"
    
    gen_model = genai.GenerativeModel(
        model_name=full_model_name,
        system_instruction=system if system else None
    )
    
    response = gen_model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            response_mime_type="application/json" if json_mode else "text/plain",
            temperature=temp
        )
    )
    return response.text
