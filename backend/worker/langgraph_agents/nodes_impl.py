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

import hashlib
from shared.redis_client import cv_parsed_cache

async def parse_with_llm(text: str) -> Dict[str, Any]:
    """Sử dụng LLM (OpenAI/Gemini) để chuyển đổi text CV sang JSON (kèm caching)."""
    if not text:
        return {}
        
    # 1. Check Cache
    text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
    cache_key = f"cv_parse:{text_hash}"
    
    cached_result = cv_parsed_cache.get(cache_key)
    if cached_result:
        logger.info(f"CV Parsed JSON Cache Hit for hash: {text_hash}")
        try:
            return json.loads(cached_result)
        except:
            logger.warning("Failed to parse cached JSON, re-calculating...")

    # 2. Extract context
    current_date = get_current_date()
    
    system_instruction = f"""
    You are a highly precise AI HR Data Architect. Your mission is to transform unstructured CV/JD text into a structured data schema to support a Skill Gap Analysis system.

    STRICT RULES:
    1. Factual Integrity: Extract ONLY information explicitly present in the text. Do not infer skills that do not exist.
    2. Context Retention: For each skill, keep the short sentence/phrase (context) where it appeared to help determine proficiency level later.
    3. No Premature Normalization: Do not force a 'CanonicalName' if uncertain. Keep the 'raw_name' to match against the system's tech_taxonomy.json.
    4. Date Precision: Use Today's Date: {current_date} for any "Present" or "Current" end dates.

    EXPERIENCE CALCULATION LOGIC:
    1. Extract all work periods (Start Date - End Date).
    2. Merge overlapping periods to avoid double-counting.
    3. Calculate 'duration_years' for each role and 'total_years_exp' for the entire career (rounded to 1 decimal).
    4. Determine 'seniority_level' (Intern, Junior, Middle, Senior, Lead) based on job titles and years of experience.
    5. For each skill, identify the most recent year it was used ('last_used_year').

    THINKING PROCESS (Internal):
    Before generating the JSON, follow these steps:
    1. List all time intervals found in the text. 
    2. Identify any overlaps.
    3. Sum unique duration for 'total_years_exp'.
    4. For each skill:
       - Find the 'last_used_year' from associated roles.
       - Infer 'proficiency_level' (Junior, Mid-level, Senior, Expert) based on complexity of tasks and years.
       - Extract the 'context' (how it was used).
    """

    prompt = f"""
    Extract the following information in JSON format from the CV text below:
    ---
    {text}
    ---
    EXTRACTION SCHEMA (JSON):
    {{
    "candidate_summary": {{
        "full_name": "Candidate's legal name",
        "primary_role": "Current or target industry title",
        "seniority_level": "Level based on total years (Intern, Junior, etc.)",
        "experience_years_total": 0.0,
        "summary": "Short professional profile"
    }},
    "work_history": [
        {{
        "company": "Company Name",
        "position": "Job Title",
        "years": 0.0,
        "description": "Short summary of responsibilities",
        "skills": ["List of raw skill names mentioned in this role"],
        "key_achievements": ["Main achievements bullet points"]
        }}
    ],
    "skills": [
        {{
            "skill_name": "Python", 
            "level": "Mid-level", 
            "years_exp": 3, 
            "last_used_year": 2024,
            "context": "3 years of backend dev in Python building REST APIs"
        }}
    ]
    }}
    
    IMPORTANT: Return ONLY valid JSON.
    """
    
    logger.debug(f"--- [LLM REQUEST (CV PARSING)] ---")
    logger.debug(f"PROMPT SENT:\n{prompt}")
    
    try:
        parsed_result = {}
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
            logger.debug(f"LLM RAW RESPONSE:\n{raw_content}")
            parsed_result = json.loads(raw_content)
        
        elif LLM_PROVIDER == "gemini":
            response = gemini_model.generate_content(
                system_instruction + "\n" + prompt,
                generation_config={"response_mime_type": "application/json", "temperature": 0}
            )
            logger.debug(f"LLM RAW RESPONSE:\n{response.text}")
            parsed_result = json.loads(response.text)
            
        # 3. Store in Cache
        if parsed_result:
            cv_parsed_cache.setex(cache_key, 3600*24, json.dumps(parsed_result))
            logger.info("Saved CV parsed JSON to cache.")
            
        return parsed_result
            
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
