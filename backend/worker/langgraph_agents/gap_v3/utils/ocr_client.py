import os
import httpx
import logging
import asyncio
from typing import Dict, Any, Optional

logger = logging.getLogger("cv_parsing_v3.ocr_client")

class ChandraOCRClient:
    def __init__(self):
        self.api_url = os.getenv("CHANDRA_API_URL")
        self.api_key = os.getenv("CHANDRA_API_KEY")
        self.timeout = float(os.getenv("OCR_TIMEOUT", "60.0"))

    async def ocr_file(self, file_path: str) -> Dict[str, Any]:
        """
        Gửi file CV tới Chandra OCR API để bóc tách text.
        """
        if not self.api_url:
            logger.error("[OCR] CHANDRA_API_URL is not set")
            return {"status": "error", "error": "CHANDRA_API_URL not configured"}

        if not os.path.exists(file_path):
            logger.error(f"[OCR] File not found: {file_path}")
            return {"status": "error", "error": "File not found"}

        logger.info(f"[OCR] Sending file to Chandra: {file_path} | URL: {self.api_url}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                with open(file_path, "rb") as f:
                    files = {"file": (os.path.basename(file_path), f)}
                    headers = {"X-AI-Key": self.api_key} if self.api_key else {}
                    
                    t0 = asyncio.get_event_loop().time()
                    resp = await client.post(self.api_url, files=files, headers=headers)
                    elapsed = asyncio.get_event_loop().time() - t0
                    
                if resp.status_code != 200:
                    logger.error(f"[OCR] Chandra API failed with status {resp.status_code}: {resp.text}")
                    return {"status": "error", "error": f"API returned status {resp.status_code}"}

                data = resp.json()
                logger.info(f"[OCR] Chandra success in {elapsed:.1f}s | result_len={len(data.get('text', ''))}")
                
                return {
                    "status": "success",
                    "text": data.get("text", ""),
                    "confidence": float(data.get("confidence", 0.95)), # Default to high if not provided
                    "is_ocr": True,
                    "elapsed": elapsed
                }

        except Exception as e:
            logger.error(f"[OCR] Exception during Chandra call: {e}")
            return {"status": "error", "error": str(e)}

ocr_client = ChandraOCRClient()
