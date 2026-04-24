import os
import logging
from typing import List, Optional, Dict, Any
import openai
import tiktoken
from shared.config_utils import config_manager
from shared.ai_service import generate_completion

logger = logging.getLogger("llm_utils")

# ─── Token Counting & Cost Tracking ──────────────────────────────────────────

# Embedding model pricing (per 1M tokens)
EMBEDDING_COSTS = {
    "text-embedding-3-small": 0.02,  # $0.02 per 1M tokens
    "text-embedding-3-large": 0.13,  # $0.13 per 1M tokens
    "text-embedding-ada-002": 0.10,  # $0.10 per 1M tokens
}

def count_tokens(text: str, model: str = "text-embedding-3-small") -> int:
    """Count tokens in text using tiktoken."""
    try:
        # Use cl100k_base encoding for embedding models
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception as e:
        logger.warning(f"Failed to count tokens: {e}. Using character estimate.")
        # Fallback: rough estimate (1 token ≈ 4 characters)
        return len(text) // 4

def calculate_embedding_cost(token_count: int, model: str = "text-embedding-3-small") -> float:
    """Calculate cost in USD for embedding tokens."""
    cost_per_million = EMBEDDING_COSTS.get(model, 0.02)
    return (token_count / 1_000_000) * cost_per_million

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

def get_embedding(text: str, log_cost: bool = True) -> Optional[List[float]]:
    """
    Tạo vector nhúng (embedding) cho một đoạn văn bản.
    Sử dụng model text-embedding-3-small mặc định của OpenAI.
    
    Args:
        text: Text to embed
        log_cost: Whether to log token usage and cost
    """
    res = get_embeddings_batch([text], log_cost=log_cost)
    return res[0] if res else None

def get_embeddings_batch(texts: List[str], log_cost: bool = True) -> List[List[float]]:
    """
    Tạo vector nhúng (embedding) cho danh sách các đoạn văn bản (Batch).
    
    Args:
        texts: List of texts to embed
        log_cost: Whether to log token usage and cost
    """
    client = LLMFactory.get_openai_client()
    if not texts or not client:
        return []
        
    try:
        # Resolve embedding model from environment variable
        model_id = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        
        # Làm sạch text nhẹ nhàng
        clean_texts = [t.replace("\n", " ").strip() for t in texts if t]
        if not clean_texts: return []

        # Count tokens before sending
        total_tokens = 0
        if log_cost:
            for text in clean_texts:
                total_tokens += count_tokens(text, model_id)
            
            cost = calculate_embedding_cost(total_tokens, model_id)
            logger.info(f"[EMBED] Sending {len(clean_texts)} texts | model={model_id} | tokens={total_tokens:,} | cost=${cost:.6f}")
        else:
            logger.info(f"[EMBED] Sending {len(clean_texts)} texts | model={model_id}")

        response = client.embeddings.create(
            input=clean_texts,
            model=model_id
        )
        
        # Log actual usage from API response
        if hasattr(response, 'usage') and response.usage:
            actual_tokens = response.usage.total_tokens
            actual_cost = calculate_embedding_cost(actual_tokens, model_id)
            logger.info(f"[EMBED] ✓ Success | vectors={len(response.data)} | actual_tokens={actual_tokens:,} | actual_cost=${actual_cost:.6f}")
        else:
            logger.info(f"[EMBED] ✓ Success | vectors={len(response.data)}")
        
        return [d.embedding for d in response.data]
    except Exception as e:
        logger.error(f"[EMBED] ❌ Error generating batch embeddings: {e}")
        return []

# ─── Chat Completion Functions ──────────────────────────────────────────────

def get_chat_completion(
    prompt: str, 
    system_prompt: str = "You are a helpful assistant.", 
    json_mode: bool = False,
    model: Optional[str] = None,
    model_key: str = "career_advisor_model",
    call_name: str = "chat_completion",
    user_id: Optional[str] = None
) -> Optional[str]:
    """
    [LEGACY] Wrapper for the new AI Service completion core.
    This function is maintained for backward compatibility.
    """
    # Use career_advisor_model as default for general chat completions if model is not override
    m_key = model_key if model_key else "ai_model"
    
    return generate_completion(
        prompt=prompt,
        system_prompt=system_prompt,
        json_mode=json_mode,
        model=model,
        model_key=m_key,
        call_name=call_name,
        user_id=user_id
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

def clean_json_response(response: str) -> str:
    """
    SECURITY & STABILITY: Loại bỏ markdown code blocks từ LLM response.
    Đảm bảo json.loads() có thể parse được kể cả khi LLM bao bọc trong ```json.
    """
    if not response:
        return ""
    # Remove ```json ... ``` or ``` ... ```
    import re
    cleaned = re.sub(r'^```(?:json)?\s*', '', response, flags=re.MULTILINE)
    cleaned = re.sub(r'\s*```$', '', cleaned, flags=re.MULTILINE)
    return cleaned.strip()

# ─── Skill Extraction ────────────────────────────────────────────────────────

def extract_skills_from_requirements(requirements_text: str, model_key: str = "ai_model") -> Optional[List[Dict[str, Any]]]:
    """
    Extract structured skills from job requirements text using LLM.
    
    Returns list of skills with metadata:
    [
        {
            "skill_name": "Python",
            "category": "Programming Language",
            "required_level": "Senior",
            "min_years_exp": 5.0,
            "is_mandatory": true,
            "importance_weight": 10
        },
        ...
    ]
    """
    if not requirements_text or len(requirements_text.strip()) < 20:
        logger.warning("[SKILL EXTRACT] Requirements text too short, skipping extraction")
        return None
    
    prompt = f"""Extract all technical and professional skills from the following job requirements.

Job Requirements:
{requirements_text}

For each skill, identify:
1. skill_name: The specific skill (e.g., "Python", "React", "Project Management")
2. category: Type of skill (e.g., "Programming Language", "Framework", "Soft Skill", "Tool", "Methodology")
3. required_level: Seniority level if mentioned (e.g., "Junior", "Mid", "Senior", "Expert") or null
4. min_years_exp: Minimum years of experience required (extract number, or 0 if not specified)
5. is_mandatory: true if explicitly required, false if "nice to have" or "plus"
6. importance_weight: Rate 1-10 based on emphasis in text (10 = critical, 1 = minor)

Return ONLY a JSON array of skills. Example:
[
  {{"skill_name": "Python", "category": "Programming Language", "required_level": "Senior", "min_years_exp": 5, "is_mandatory": true, "importance_weight": 10}},
  {{"skill_name": "Django", "category": "Framework", "required_level": null, "min_years_exp": 3, "is_mandatory": true, "importance_weight": 8}},
  {{"skill_name": "Docker", "category": "Tool", "required_level": null, "min_years_exp": 0, "is_mandatory": false, "importance_weight": 5}}
]

Important:
- Extract ONLY skills explicitly mentioned in the text
- Do NOT infer or add skills not mentioned
- Include both technical skills (languages, frameworks, tools) and soft skills (communication, leadership)
- Be specific: "React" not "JavaScript frameworks"
- Return empty array [] if no clear skills found
"""

    system_prompt = "You are a technical recruiter expert at analyzing job requirements and extracting structured skill data. Always return valid JSON."
    
    try:
        logger.info(f"[SKILL EXTRACT] Extracting skills from {len(requirements_text)} chars of requirements...")
        
        response = get_chat_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            json_mode=True,
            model_key=model_key,
            call_name="extract_skills"
        )
        
        if not response:
            logger.error("[SKILL EXTRACT] No response from LLM")
            return None
        
        # Parse JSON response with cleaning
        import json
        cleaned_response = clean_json_response(response)
        skills = json.loads(cleaned_response)
        
        if not isinstance(skills, list):
            logger.error(f"[SKILL EXTRACT] Expected list, got {type(skills)}")
            return None
        
        logger.info(f"[SKILL EXTRACT] ✓ Extracted {len(skills)} skills")
        
        # Log extracted skills for monitoring
        for skill in skills[:5]:  # Log first 5
            logger.debug(f"[SKILL EXTRACT]   - {skill.get('skill_name')} ({skill.get('category')}) | Level: {skill.get('required_level')} | Years: {skill.get('min_years_exp')}")
        
        return skills
        
    except json.JSONDecodeError as e:
        logger.error(f"[SKILL EXTRACT] Failed to parse JSON response: {e}")
        logger.debug(f"[SKILL EXTRACT] Raw response: {response[:200]}...")
        return None
    except Exception as e:
        logger.error(f"[SKILL EXTRACT] Error extracting skills: {e}", exc_info=True)
        return None
