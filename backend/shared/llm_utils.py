import os
import logging
from typing import List, Optional
import openai

logger = logging.getLogger("llm_utils")

# Load Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize Client
openai_client = None
if LLM_PROVIDER == "openai" and OPENAI_API_KEY:
    openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)

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
    if not texts or not openai_client:
        return []
        
    try:
        # Làm sạch text nhẹ nhàng
        clean_texts = [t.replace("\n", " ").strip() for t in texts if t]
        if not clean_texts: return []

        response = openai_client.embeddings.create(
            input=clean_texts,
            model="text-embedding-3-small"
        )
        return [d.embedding for d in response.data]
    except Exception as e:
        logger.error(f"Error generating batch embeddings: {e}")
        return []

def get_chat_completion(prompt: str, system_prompt: str = "You are a helpful assistant.", json_mode: bool = False) -> Optional[str]:
    """
    Hàm dùng chung để gọi Chat Completion.
    """
    if not openai_client:
        return None
        
    try:
        response = openai_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"} if json_mode else None
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error calling LLM: {e}")
        return None

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
