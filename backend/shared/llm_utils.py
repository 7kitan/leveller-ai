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
    if not text or not openai_client:
        return None
        
    try:
        # Làm sạch text nhẹ nhàng
        clean_text = text.replace("\n", " ").strip()
        
        response = openai_client.embeddings.create(
            input=[clean_text],
            model="text-embedding-3-small"
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return None

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
