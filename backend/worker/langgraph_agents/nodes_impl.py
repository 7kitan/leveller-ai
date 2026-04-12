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

    THINKING PROCESS (Internal):
    Before generating the JSON, follow these steps:
    1. List all time intervals found in the text. 
    2. Identify any overlaps (e.g., Job A and Job B occurring at the same time).
    3. Sum the unique duration to get 'total_years_exp'.
    4. For the 'inferred_level_raw' (1-5):
       - 1: Mentioned only.
       - 2: Basic use in a project.
       - 3: Core responsibility in a role.
       - 4: Expert/Lead usage.
       - 5: Extensive years or architectural leadership in that skill.
    5. Verify that every 'raw_name' in the skills section can be traced back to a specific sentence in the CV.
    """

    prompt = f"""
    Extract the following information in JSON format from the CV text below:
    ---
    {text}
    ---
    EXTRACTION SCHEMA (JSON):
    {{
    "candidate_summary": {{
        "primary_role": "Standard industry title",
        "seniority_level": "Level based on context",
        "total_years_exp": 0.0
    }},
    "work_history": [
        {{
        "company": "Company Name",
        "role": "Job Title",
        "duration_years": 0.0,
        "skills_used": ["List of raw skill names mentioned in this role"],
        "key_achievements": ["Bullet points of main responsibilities"]
        }}
    ],
    "skills": {{
        "hard_skills": [
        {{"raw_name": "Python", "context": "3 years of backend dev in Python", "inferred_level_raw": 1-5}}
        ],
        "soft_skills": [
        {{"raw_name": "Team Management", "context": "Led a team of 5", "inferred_level_raw": 1-5}}
        ],
        "domain_skills": [
        {{"raw_name": "Fintech", "context": "Worked on payment gateway", "inferred_level_raw": 1-5}}
        ]
    }}
    }}
    
    IMPORTANT: Return ONLY valid JSON.
    """
    
    logger.debug(f"--- [LLM REQUEST (CV PARSING)] ---")
    
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
            parsed_result = json.loads(raw_content)
        
        elif LLM_PROVIDER == "gemini":
            response = gemini_model.generate_content(
                system_instruction + "\n" + prompt,
                generation_config={"response_mime_type": "application/json", "temperature": 0}
            )
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
