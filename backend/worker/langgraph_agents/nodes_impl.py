from datetime import datetime
import fitz  # PyMuPDF
import os
import json
import logging
import re
from typing import Dict, Any
from dotenv import load_dotenv
from shared.taxonomy_service import taxonomy_service
import httpx

load_dotenv()

# Initialize logging
logger = logging.getLogger("cv_parsing")
logger.setLevel(logging.DEBUG)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# Initialize the chosen provider
if LLM_PROVIDER == "openai":
    import openai
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
elif LLM_PROVIDER == "gemini":
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    gemini_model = genai.GenerativeModel(LLM_MODEL)

def get_current_date() -> str:
    """Trả về ngày hiện tại dưới định dạng YYYY-MM-DD."""
    return datetime.now().strftime("%Y-%m-%d")

def extract_from_pdf(file_path: str) -> str:
    """Trích xuất text thô bằng PyMuPDF và làm sạch ký tự lạ."""
    text = ""
    try:
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text()
        doc.close()
        
        # Làm sạch văn bản
        text = "".join(char for char in text if char.isprintable() or char in "\n\t")
        text = re.sub(r'\n\s*\n', '\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        
    except Exception as e:
        logger.error(f"Error extracting PDF: {e}")
    return text.strip()

def mask_pii(text: str) -> str:
    """Ẩn danh thông tin nhạy cảm (PII) bằng Regex."""
    if not text: return ""
    
    # 1. Mask Emails
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    masked_text = re.sub(email_pattern, "[EMAIL_MASKED]", text)
    
    # 2. Mask Phone numbers
    phone_pattern = r'(\+84|0|84)\s?([35789]|1[2689])([0-9]{8})\b'
    masked_text = re.sub(phone_pattern, "[PHONE_MASKED]", masked_text)

    # 3. Mask potential specific address patterns
    address_starters = [r"địa chỉ:", r"address:", r"thường trú:"]
    for starter in address_starters:
        masked_text = re.sub(f"({starter}).*$", r"\1 [ADDRESS_MASKED]", masked_text, flags=re.IGNORECASE | re.MULTILINE)

    return masked_text

def normalize_terms(text: str) -> str:
    """
    Sử dụng Từ điển (Graph Taxonomy) để chuẩn hóa thuật ngữ trước khi xử lý.
    Giúp ánh xạ các cụm từ Tiếng Việt chuyên ngành sang Tiếng Anh chuẩn.
    """
    if not text: return ""
    
    # Lấy bảng ánh xạ từ Graph (Aliases -> Canonical Name)
    mapping = taxonomy_service.get_canonical_mapping()
    if not mapping: return text
    
    normalized_text = text
    # Sắp xếp bí danh theo độ dài giảm dần để tránh thay thế các cụm từ con trước
    sorted_aliases = sorted(mapping.keys(), key=len, reverse=True)
    
    for alias in sorted_aliases:
        canonical = mapping[alias]
        # Sử dụng regex word boundary \b để tránh thay thế sai giữa các cụm từ
        # Lưu ý: Word boundary với tiếng Việt có thể hơi phức tạp, dùng pattern linh hoạt hơn
        pattern = re.compile(re.escape(alias), re.IGNORECASE)
        # Chúng ta đính kèm Canonical name thay vì thay thế hoàn toàn để LLM vẫn thấy ngữ cảnh gốc
        normalized_text = pattern.sub(f"{alias} [{canonical}]", normalized_text)
        
    logger.debug("Term normalization complete via Knowledge Graph.")
    return normalized_text

async def parse_with_llm(text: str) -> Dict[str, Any]:
    """Sử dụng LLM (OpenAI/Gemini) để chuyển đổi text CV sang JSON."""
    
    current_date = get_current_date()
    
    system_instruction = f"""
    You are a highly precise AI HR CV data extractor.
    Extract structured candidate information from CV text.
    Today's date is {current_date}.

    STRICT RULES:
    - Return ONLY factual information explicitly present in CV.
    - If you see terms like 'X [CanonicalName]', use 'CanonicalName' as the standard skill name.
    - Normalize technical skill names to standard industry names.

    EXPERIENCE CALCULATION RULES:
    1. Extract all work periods.
    2. If end date is Present, use {current_date}.
    3. Merge overlapping periods.
    4. Return total years rounded to 1 decimal.
    5. For each job in 'work_history', return 'years' (duration in that specific role).

    ROLE INFERENCE RULES:
    1. Determine 'primary_role' and 'seniority_level' based on context.
    2. Identify skills used specifically within each work experience entry.
    """

    prompt = f"""
    Extract the following information in JSON format from the CV text below:
    ---
    {text}
    ---
    JSON structure:
    - full_name: String
    - primary_role: String
    - seniority_level: String
    - summary: Text
    - experience_years_total: Float
    - skills: List of strings (unique technical skills)
    - work_history: List of objects:
        - position: String
        - company: String
        - years: Float (duration in this role)
        - skills: List of strings (skills used in THIS specific role)
        - description: Text
    - education: List of objects
    
    IMPORTANT: Return ONLY valid JSON.
    """
    
    logger.debug(f"--- [LLM REQUEST (CV PARSING)] ---")
    
    try:
        if LLM_PROVIDER == "openai":
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0
            )
            raw_content = response.choices[0].message.content
            return json.loads(raw_content)
        
        elif LLM_PROVIDER == "gemini":
            response = gemini_model.generate_content(
                system_instruction + "\n" + prompt,
                generation_config={"response_mime_type": "application/json", "temperature": 0}
            )
            return json.loads(response.text)
            
    except Exception as e:
        logger.error(f"{LLM_PROVIDER.upper()} parsing error: {e}")
        return {}

async def compute_bert_score(text1: str, text2: str) -> Dict[str, Any]:
    """
    Gọi BERTScore API để đánh giá mức độ tương đồng ngữ nghĩa giữa 2 văn bản.
    Sử dụng BERTSCORE_API_URL và BERTSCORE_API_KEY từ .env.
    """
    api_url = os.getenv("BERTSCORE_API_URL")
    api_key = os.getenv("BERTSCORE_API_KEY")

    if not api_url:
        logger.warning("BERTSCORE_API_URL not set. Skipping BERTScore calculation.")
        return {"f1": 0, "precision": 0, "recall": 0, "error": "API URL not set"}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "text1": text1,
                "text2": text2
            }
            headers = {}
            if api_key:
                headers["X-AI-Key"] = api_key

            response = await client.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Error calling BERTScore API: {e}")
        return {"f1": 0, "error": str(e)}
