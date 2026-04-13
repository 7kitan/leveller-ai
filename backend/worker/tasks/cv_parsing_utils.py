import fitz  # PyMuPDF
import re
import logging
import os
import base64
import httpx
import asyncio
import json
from typing import Dict, Any, Tuple
from pathlib import Path

logger = logging.getLogger("cv_parsing")

CHANDRA_API_URL = os.getenv("CHANDRA_API_URL")
CHANDRA_API_KEY = os.getenv("CHANDRA_API_KEY")
CV_PARSING_STRATEGY = os.getenv("CV_PARSING_STRATEGY", "hybrid").lower()
CV_PARSING_OCR_THRESHOLD = int(os.getenv("CV_PARSING_OCR_THRESHOLD", "200"))

def extract_text_direct(file_path: str) -> str:
    """Trích xuất text thô bằng PyMuPDF."""
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
        logger.error(f"Error extracting PDF via PyMuPDF: {e}")
    return text.strip()

async def poll_ocr_task(task_id: str) -> Dict[str, Any]:
    """Hỏi thăm trạng thái task cho đến khi hoàn thành."""
    if not CHANDRA_API_URL:
        return {"status": "failed", "error": "CHANDRA_API_URL not set"}
        
    base_url = CHANDRA_API_URL.rsplit('/', 1)[0]
    poll_url = f"{base_url}/{task_id}"
    headers = {"X-AI-Key": CHANDRA_API_KEY} if CHANDRA_API_KEY else {}

    # Sử dụng cấu hình retry từ env nếu có
    max_retries = int(os.getenv("CV_PARSING_MAX_RETRIES", "60"))

    for i in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(poll_url, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                status = data.get("status")
                if status == "completed":
                    return {"status": "success", "text": data.get("result", {}).get("text", "")}
                elif status == "failed":
                    return {"status": "failed", "error": data.get("error")}
                
                await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Error polling OCR task {task_id}: {e}")
            await asyncio.sleep(2)

    return {"status": "timeout", "error": "Polling timed out"}

async def extract_text_ocr(file_path: str) -> Tuple[str, bool]:
    """Gửi file sang AI Hub để OCR."""
    if not CHANDRA_API_URL:
        logger.error("CHANDRA_API_URL is not set!")
        return "", False

    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        
        file_base64 = base64.b64encode(file_bytes).decode("utf-8")
        file_ext = Path(file_path).suffix.lower()

        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"X-AI-Key": CHANDRA_API_KEY} if CHANDRA_API_KEY else {}
            payload = {"file_base64": file_base64, "file_ext": file_ext}
            response = await client.post(CHANDRA_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            task_id = response.json().get("task_id")
            
        if not task_id:
            return "", False

        result = await poll_ocr_task(task_id)
        if result["status"] == "success":
            return result["text"], True
        return "", False
    except Exception as e:
        logger.error(f"OCR Extraction Exception: {e}")
        return "", False

import hashlib
from shared.redis_client import result_cache

async def extract_cv_hybrid(file_path: str) -> Dict[str, Any]:
    """
    Chiến lược Trích xuất CV: 
    Hỗ trợ 3 chế độ từ .env: hybrid, direct, chandra (ocr).
    Kèm theo bộ bộ nhớ đệm (Cache) cho kết quả trích xuất text thô.
    """
    # 0. Xác định strategy thực tế từ hệ thống (.env)
    active_strategy = CV_PARSING_STRATEGY
    if active_strategy == "chandra": 
        active_strategy = "ocr" # Map chandra to ocr internal logic

    # 1. Kiểm tra cache trước (nếu được bật)
    cache_enabled = os.getenv("CACHE_CV_RAW_TEXT_ENABLED", "true").lower() == "true"
    cache_key = None
    
    if cache_enabled:
        # Dùng hash của nội dung file làm key cache để đảm bảo tính duy nhất
        try:
            with open(file_path, "rb") as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
            cache_key = f"cv_raw_text:{file_hash}:{active_strategy}" # Cache theo strategy
            cached_data = result_cache.get(cache_key)
            if cached_data:
                logger.info(f"Cache Hit for Raw Text (hash: {file_hash}, strategy: {active_strategy})")
                return json.loads(cached_data)
        except Exception as e:
            logger.warning(f"Cache check failed: {e}")

    logger.info(f"CV Extraction Strategy (System Decided): {active_strategy}")
    extraction_result = {}

    # Chế độ 1: Chỉ Chandra (OCR)
    if active_strategy == "ocr":
        ocr_text, success = await extract_text_ocr(file_path)
        if success:
            extraction_result = {"raw_text": ocr_text, "is_ocr": True, "method": "chandra_forced"}
        else:
            return {"error": "Chandra OCR failed (forced mode)", "status": "failed"}

    # Chế độ 2: Trực tiếp (Direct)
    elif active_strategy == "direct":
        direct_text = extract_text_direct(file_path)
        extraction_result = {"raw_text": direct_text, "is_ocr": False, "method": "direct_forced"}

    # Chế độ 3: Hybrid (Mặc định)
    else:
        direct_text = extract_text_direct(file_path)
        if len(direct_text) > CV_PARSING_OCR_THRESHOLD:
            logger.info(f"Direct extraction sufficient (> {CV_PARSING_OCR_THRESHOLD} chars).")
            extraction_result = {"raw_text": direct_text, "is_ocr": False, "method": "direct_hybrid"}
        else:
            logger.info(f"Direct text too sparse ({len(direct_text)} chars). Falling back to OCR...")
            ocr_text, success = await extract_text_ocr(file_path)
            if success and len(ocr_text) > 0:
                extraction_result = {"raw_text": ocr_text, "is_ocr": True, "method": "ocr_hybrid"}
            else:
                extraction_result = {
                    "raw_text": direct_text, 
                    "is_ocr": False, 
                    "method": "direct_fallback",
                    "warning": "OCR failed (hybrid fallback)"
                }
    
    # 2. Lưu vào cache nếu thành công
    if cache_enabled and cache_key and extraction_result.get("raw_text"):
        try:
            result_cache.set(cache_key, json.dumps(extraction_result))
            logger.info(f"Saved extracted text to cache (key: {cache_key})")
        except Exception as e:
            logger.warning(f"Failed to save to cache: {e}")

    return extraction_result
