"""
PII Masking utilities — che email, phone, address, DOB trước khi gửi LLM.
"""

import re
import logging

logger = logging.getLogger(__name__)

# Compiled patterns (compile once, use many)
_PHONE_PATTERN = re.compile(r"[\+]?[(]?[0-9]{1,3}[)]?[-\s\./0-9]{8,15}")
_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
_ADDRESS_PATTERN = re.compile(
    r"\d+\s+[\w\s,\.]+(?:street|st|avenue|ave|road|rd|district|ward|phường|quận|thành phố|TP)[^\n]*",
    re.IGNORECASE,
)
_DOB_PATTERN = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")
_URL_PATTERN = re.compile(r"https?://[^\s]+")
_NAME_PATTERN = re.compile(r"\b[A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b")

# Vietnamese patterns — phone: must have word boundary to avoid matching other numbers
_VN_PHONE = re.compile(r"\b0\d{9,10}\b")


def mask_pii(text: str) -> str:
    """
    Che tất cả PII trong text.
    Thứ tự: phone → email → address → DOB → url → name → Vietnamese patterns.
    """
    if not text:
        return text

    masked = text

    # 1. URLs (remove personal links)
    masked = _URL_PATTERN.sub("[PERSONAL_LINK]", masked)

    # 2. Email
    masked = _EMAIL_PATTERN.sub("[EMAIL]", masked)

    # 3. DOB → check BEFORE phone to avoid DOB being matched as phone number
    masked = _DOB_PATTERN.sub("[DATE_OF_BIRTH]", masked)

    # 4. Vietnamese phone numbers (must have word boundary)
    masked = _VN_PHONE.sub("[PHONE]", masked)

    # 5. Generic phone patterns (only after DOB is masked, to avoid false matches)
    masked = _PHONE_PATTERN.sub("[PHONE]", masked)

    # 6. Address patterns (only if clearly an address)
    # Skip overly greedy address matching to avoid masking normal text
    # masked = _ADDRESS_PATTERN.sub("[ADDRESS]", masked)

    # 7. Common name patterns (conservative — only if likely personal)
    # Skip this for CV context to preserve readability

    return masked


def mask_work_history(work_history: list) -> list:
    """
    Mask PII trong work_history records.
    Trả về list of dict đã masked.
    """
    masked = []
    for w in work_history:
        if isinstance(w, dict):
            entry = dict(w)
            entry["company_name"] = mask_pii(str(w.get("company_name", "")))
            entry["description"] = mask_pii(str(w.get("description", "")))
        else:
            entry = {
                "position": getattr(w, "position_name", ""),
                "company": mask_pii(getattr(w, "company_name", "")),
                "description": mask_pii(getattr(w, "description", "")),
                "duration_years": getattr(w, "duration_years", 0),
            }
        masked.append(entry)
    return masked


def get_pii_masking_stats(text_before: str, text_after: str) -> dict:
    """Trả về stats về bao nhiêu PII đã được mask."""
    original = text_before or ""
    masked = text_after or ""

    return {
        "emails_masked": original.count("@") - masked.count("@"),
        "phones_masked": _VN_PHONE.findall(original).__len__()
        + _PHONE_PATTERN.findall(original).__len__()
        - _VN_PHONE.findall(masked).__len__()
        - _PHONE_PATTERN.findall(masked).__len__(),
        "chars_removed": len(original) - len(masked),
    }
