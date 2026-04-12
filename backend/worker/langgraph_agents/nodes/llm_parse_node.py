import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("cv_parsing")

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

if LLM_PROVIDER == "openai":
    import openai
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
elif LLM_PROVIDER == "gemini":
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    gemini_model = genai.GenerativeModel(LLM_MODEL)

def get_current_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")

async def llm_parse_node_func(state: Dict[str, Any]) -> Dict[str, Any]:
    """Node sử dụng LLM để phân tích text sang JSON."""
    text = state.get("raw_text")
    if not text:
        return {"error": "No text to parse", "status": "failed"}
    
    logger.info(f"--- [LLM PARSE NODE] Parsing with {LLM_PROVIDER.upper()} ---")

    current_date = get_current_date()
    system_instruction = f"""
    You are a highly precise AI HR CV data extractor.
    Extract structured candidate information from CV text.
    Today's date is {current_date}.

    STRICT RULES:
    - Return ONLY factual information explicitly present in CV.
    - If you see terms like 'X [CanonicalName]', use 'CanonicalName' as the standard skill name.
    - Normalize technical skill names to standard industry names.
    - IMPORTANT: If experience years are not mentioned, infer reasonably or set to 0.
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

    try:
        logger.info(f"\n{'='*50}\n[LLM REQUEST - {LLM_PROVIDER.upper()}]\nSYSTEM INSTRUCTION:\n{system_instruction}\n\nUSER PROMPT:\n{prompt}\n{'='*50}")
        
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
            raw_response_text = response.choices[0].message.content
            logger.info(f"\n{'='*50}\n[LLM RAW RESPONSE - OPENAI]\n{raw_response_text}\n{'='*50}")
            parsed_data = json.loads(raw_response_text)
            
        elif LLM_PROVIDER == "gemini":
            response = await gemini_model.generate_content_async(
                system_instruction + "\n" + prompt,
                generation_config={"response_mime_type": "application/json", "temperature": 0}
            )
            raw_response_text = response.text
            logger.info(f"\n{'='*50}\n[LLM RAW RESPONSE - GEMINI]\n{raw_response_text}\n{'='*50}")
            parsed_data = json.loads(raw_response_text)
            
        else:
            return {"error": f"Unsupported LLM provider: {LLM_PROVIDER}", "status": "failed"}

        return {"parsed_data": parsed_data, "status": "parsed"}

    except Exception as e:
        logger.error(f"LLM Parsing Error: {e}")
        return {"error": f"AI không thể phân tích nội dung CV: {str(e)}", "status": "failed"}
