import fitz  # PyMuPDF
import logging
import re
import os
from typing import Dict, Any

logger = logging.getLogger("cv_parsing")

def is_image_file(file_path: str) -> bool:
    """Kiểm tra xem file có phải là định dạng ảnh không."""
    ext = os.path.splitext(file_path)[1].lower()
    return ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"]

def extract_from_pdf(file_path: str) -> str:
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
        logger.error(f"Error extracting PDF: {e}")
    return text.strip()

def extract_node_func(state: Dict[str, Any]) -> Dict[str, Any]:
    """Node xử lý trích xuất văn bản ban đầu."""
    file_path = state["file_path"]
    logger.info(f"--- [EXTRACT NODE] Processing file: {file_path} ---")

    # 1. Nếu là file ảnh -> Chuyển thẳng sang OCR
    if is_image_file(file_path):
        logger.info("Detected image file. Routing to OCR node.")
        return {"status": "needs_ocr"}

    # 2. Nếu là PDF -> Thử trích xuất text trực tiếp
    text = extract_from_pdf(file_path)
    
    # 3. Kiểm tra nếu text rỗng hoặc quá ngắn (có khả năng là PDF scan)
    # Ngưỡng 100 ký tự là con số an toàn để xác định PDF có chứa text thật hay không
    if not text or len(text) < 100:
        logger.info(f"Extracted text too short ({len(text)} chars). Triggering OCR fallback.")
        return {"status": "needs_ocr"}

    logger.info(f"Successfully extracted {len(text)} characters directly from PDF.")
    return {"raw_text": text, "is_ocr": False, "status": "extracted"}
