import re
import logging
from typing import Dict, Any
from shared.taxonomy_service import taxonomy_service

logger = logging.getLogger("cv_parsing")

def normalize_terms(text: str) -> str:
    """Chuẩn hóa thuật ngữ kỹ thuật bằng Taxonomy Service."""
    if not text: return ""
    
    mapping = taxonomy_service.get_canonical_mapping()
    if not mapping: return text
    
    normalized_text = text
    # Sắp xếp bí danh theo độ dài để xử lý cụm từ dài trước
    sorted_aliases = sorted(mapping.keys(), key=len, reverse=True)
    
    for alias in sorted_aliases:
        canonical = mapping[alias]
        # Skip if alias is too short to avoid over-matching (common in OCR noise)
        if len(alias) < 2: continue
        
        pattern = re.compile(re.escape(alias), re.IGNORECASE)
        # Gắn kèm Canonical Name để LLM dễ nhận diện
        normalized_text = pattern.sub(f"{alias} [{canonical}]", normalized_text)
        
    return normalized_text

def normalization_node_func(state: Dict[str, Any]) -> Dict[str, Any]:
    """Node chuẩn hóa thuật ngữ trước khi Parse."""
    text = state.get("raw_text")
    if not text:
        return {"status": "failed", "error": "No text to normalize"}
    
    logger.info("--- [NORMALIZATION NODE] ---")
    normalized_text = normalize_terms(text)
    return {"raw_text": normalized_text, "status": "normalized"}
