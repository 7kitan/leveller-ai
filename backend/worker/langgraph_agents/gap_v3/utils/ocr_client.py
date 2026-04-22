import os
import httpx
import logging
import asyncio
import base64
import time
from typing import Dict, Any, Optional

logger = logging.getLogger("cv_parsing_v3.ocr_client")

from shared.config_utils import config_manager

class ChandraOCRClient:
    def __init__(self):
        # We'll fetch these dynamically in each call to ensure they're up-to-date
        self.default_api_url = os.getenv("CHANDRA_API_URL")
        self.default_api_key = os.getenv("CHANDRA_API_KEY")
        self.timeout = float(os.getenv("OCR_TIMEOUT", "300.0"))
        self.poll_interval = 5.0

    @property
    def api_url(self):
        return config_manager.get_setting("chandra_api_url") or self.default_api_url

    @property
    def api_key(self):
        return config_manager.get_setting("chandra_api_key") or self.default_api_key

    async def ocr_file(self, file_path: str) -> Dict[str, Any]:
        """
        Gửi file CV tới Chandra OCR Hub qua cơ chế Polling.
        Dữ liệu được gửi dưới dạng Base64 JSON.
        """
        if not self.api_url:
            logger.error("[OCR] CHANDRA_API_URL is not set")
            return {"status": "error", "error": "CHANDRA_API_URL not configured"}



        if not os.path.exists(file_path):
            logger.error(f"[OCR] File not found: {file_path}")
            return {"status": "error", "error": "File not found"}

        # Normalize URL: remove trailing slashes
        api_url = self.api_url.strip().rstrip('/')
        status_url_base = api_url.rsplit('/', 1)[0]
        
        logger.info(f"[OCR] Target URL: {api_url}")
        logger.info(f"[OCR] Sending file to Chandra: {os.path.basename(file_path)}...")
        
        try:
            # 1. Prepare Base64 Payload
            file_ext = os.path.splitext(file_path)[1].lower()
            with open(file_path, "rb") as f:
                file_bytes = f.read()
                file_b64 = base64.b64encode(file_bytes).decode("utf-8")
            
            payload = {
                "file_base64": file_b64,
                "file_ext": file_ext
            }
            
            headers = {"X-AI-Key": self.api_key} if self.api_key else {}
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                # 2. Submit Task
                logger.debug(f"[OCR] POSTing to {api_url}...")
                resp = await client.post(api_url, json=payload, headers=headers)
                
                if resp.status_code != 200:
                    # Log the full response body to debug 404/500
                    resp_body = resp.text[:1000] # Limit log size
                    logger.error(f"[OCR] Task submission FAILED (Status {resp.status_code})\n"
                                 f"  URL: {api_url}\n"
                                 f"  Body: {resp_body}")
                    return {"status": "error", "error": f"Submission failed: {resp.status_code}"}
                
                init_data = resp.json()
                task_id = init_data.get("task_id")
                if not task_id:
                    logger.error(f"[OCR] No task_id received: {init_data}")
                    return {"status": "error", "error": "No task_id received from server"}
                
                logger.info(f"[OCR] Task {task_id} queued. Starting polling...")
                
                # 3. Polling Loop
                start_time = time.time()
                while time.time() - start_time < self.timeout:
                    status_url = f"{status_url_base}/{task_id}"
                    status_resp = await client.get(status_url, headers=headers)
                    
                    if status_resp.status_code == 200:
                        task_data = status_resp.json()
                        status = task_data.get("status")
                        
                        if status == "completed":
                            result = task_data.get("result", {})
                            logger.info(f"[OCR] Task {task_id} completed in {time.time() - start_time:.1f}s")
                            return {
                                "status": "success",
                                "text": result.get("text", ""),
                                "confidence": float(result.get("metadata", {}).get("confidence", 0.95)),
                                "is_ocr": True,
                                "elapsed": time.time() - start_time
                            }
                        elif status == "failed":
                            error_msg = task_data.get("error", "Unknown error")
                            logger.error(f"[OCR] Task {task_id} FAILED: {error_msg}")
                            return {"status": "error", "error": f"Task failed: {error_msg}"}
                        
                        # Still pending/processing
                        logger.debug(f"[OCR] Task {task_id} status: {status}...")
                    else:
                        logger.warning(f"[OCR] Polling error ({status_resp.status_code}): {status_resp.text}")
                    
                    await asyncio.sleep(self.poll_interval)
                
                logger.error(f"[OCR] Polling timed out for task {task_id} after {self.timeout}s")
                return {"status": "error", "error": "Polling timeout"}


        except Exception as e:
            logger.error(f"[OCR] Exception during Chandra call: {e}")
            return {"status": "error", "error": str(e)}

ocr_client = ChandraOCRClient()

