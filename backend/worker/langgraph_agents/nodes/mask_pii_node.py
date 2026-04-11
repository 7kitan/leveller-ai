import re
import logging
from typing import Dict, Any

logger = logging.getLogger("cv_parsing")

def mask_pii(text: str) -> str:
    """Ẩn danh thông tin nhạy cảm (PII) bằng Regex."""
    if not text: return ""
    
    # 1. Mask Emails
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    masked_text = re.sub(email_pattern, "[EMAIL_MASKED]", text)
    
    # 2. Mask Phone numbers (Vietnam formats)
    phone_pattern = r'(\+84|0|84)\s?([35789]|1[2689])([0-9]{8})\b'
    masked_text = re.sub(phone_pattern, "[PHONE_MASKED]", masked_text)

    # 3. Mask potential specific address patterns
    address_starters = [r"địa chỉ:", r"address:", r"thường trú:"]
    for starter in address_starters:
        masked_text = re.sub(f"({starter}).*$", r"\1 [ADDRESS_MASKED]", masked_text, flags=re.IGNORECASE | re.MULTILINE)

    return masked_text

def mask_pii_node_func(state: Dict[str, Any]) -> Dict[str, Any]:
    """Node ẩn danh thông tin PII."""
    text = state.get("raw_text")
    if not text:
        return {"status": "failed", "error": "No text to mask"}
    
    logger.info("--- [PII MASKING NODE] ---")
    masked_text = mask_pii(text)
    return {"raw_text": masked_text, "status": "masked"}
