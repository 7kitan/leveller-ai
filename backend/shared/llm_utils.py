import os
import logging
from typing import List, Optional, Dict, Any
import openai
from shared.config_utils import config_manager
from shared.ai_service import generate_completion

logger = logging.getLogger("llm_utils")

# ─── Mapping & Configuration ──────────────────────────────────────────────────

# Mapping từ Model ID sang Provider
MODEL_PROVIDER_MAP = {
    # Google Gemini
    "gemini-1.5-pro": "google",
    "gemini-1.5-flash": "google",
    # OpenAI
    "gpt-4o": "openai",
    "gpt-4o-mini": "openai",
    "gpt-4-turbo": "openai",
    # Anthropic
    "claude-3-5-sonnet": "anthropic",
    "claude-3-opus": "anthropic",
}

# ─── Clients Factory ─────────────────────────────────────────────────────────

class LLMFactory:
    """
    Factory class quản lý singleton clients cho các LLM providers khác nhau.
    """
    _clients = {}

    @classmethod
    def get_provider(cls, model_name: str) -> str:
        return MODEL_PROVIDER_MAP.get(model_name, "openai")

    @classmethod
    def get_openai_client(cls):
        if "openai" not in cls._clients:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                cls._clients["openai"] = openai.OpenAI(api_key=api_key)
            else:
                logger.warning("OPENAI_API_KEY is not set.")
                return None
        return cls._clients["openai"]

    @classmethod
    def get_google_client(cls):
        # Lưu ý: Google GenAI SDK sử dụng hàm khởi tạo khác, 
        # nhưng ở đây ta có thể dùng LangChain wrapper để đồng bộ.
        if "google" not in cls._clients:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                api_key = os.getenv("GEMINI_API_KEY")
                if api_key:
                    cls._clients["google"] = ChatGoogleGenerativeAI(
                        model="gemini-1.5-flash", # Default, sẽ override khi gọi
                        google_api_key=api_key
                    )
                else:
                    logger.warning("GEMINI_API_KEY is not set.")
                    return None
            except ImportError:
                logger.error("langchain-google-genai not installed.")
                return None
        return cls._clients["google"]

# Initialize default OpenAI client for legacy support (embeddings)
openai_client = LLMFactory.get_openai_client()

# ─── Embedding Functions ────────────────────────────────────────────────────

def get_embedding(text: str) -> Optional[List[float]]:
    """
    Tạo vector nhúng (embedding) cho một đoạn văn bản.
    Sử dụng model text-embedding-3-small mặc định của OpenAI.
    """
    res = get_embeddings_batch([text])
    return res[0] if res else None

def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Tạo vector nhúng (embedding) cho danh sách các đoạn văn bản (Batch).
    """
    client = LLMFactory.get_openai_client()
    if not texts or not client:
        return []
        
    try:
        # Làm sạch text nhẹ nhàng
        clean_texts = [t.replace("\n", " ").strip() for t in texts if t]
        if not clean_texts: return []

        logger.info(f"[LLM BATCH EMBED] Sending {len(clean_texts)} texts to OpenAI...")
        response = client.embeddings.create(
            input=clean_texts,
            model="text-embedding-3-small"
        )
        logger.info(f"[LLM BATCH EMBED] ✓ Success | vectors={len(response.data)}")
        return [d.embedding for d in response.data]
    except Exception as e:
        logger.error(f"[LLM BATCH EMBED] ❌ Error generating batch embeddings: {e}")
        return []

# ─── Chat Completion Functions ──────────────────────────────────────────────

def get_chat_completion(
    prompt: str, 
    system_prompt: str = "You are a helpful assistant.", 
    json_mode: bool = False,
    model: Optional[str] = None
) -> Optional[str]:
    """
    [LEGACY] Wrapper for the new AI Service completion core.
    This function is maintained for backward compatibility.
    """
    return generate_completion(
        prompt=prompt,
        system_prompt=system_prompt,
        json_mode=json_mode,
        model=model,
        call_name="legacy_llm_utils"
    )

# ─── Utility Functions ───────────────────────────────────────────────────────

def build_cv_skill_context(skill_name: str, level: str, years: float, last_used: int = None, context: str = "") -> str:
    parts = [f"Skill: {skill_name}"]
    if level: parts.append(f"Proficiency: {level}")
    if years > 0: parts.append(f"Experience: {years} years")
    if last_used: parts.append(f"Last used: {last_used}")
    if context: parts.append(f"Context: {context}")
    return ". ".join(parts)

def build_jd_skill_context(skill_name: str, level: str, years: float, domain: str = "") -> str:
    parts = [f"Required skill: {skill_name}"]
    if years > 0: parts.append(f"Experience: {years} years of professional use")
    if level and level != "Junior": parts.append(f"Seniority: {level} level")
    if domain: parts.append(f"Domain: {domain}")
    return ". ".join(parts)

def get_current_date() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d")

def truncate_for_prompt(text: str, max_chars: int = 4000) -> str:
    """Cắt bớt text để tránh quá giới hạn token của LLM, ưu tiên lấy phần đầu."""
    if not text: return ""
    if len(text) <= max_chars: return text
    return text[:max_chars] + "... [TRUNCATED]"
