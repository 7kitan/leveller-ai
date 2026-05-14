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
        return config_manager.get_setting("CHANDRA_API_URL") or self.default_api_url

    @property
    def api_key(self):
        return config_manager.get_setting("CHANDRA_API_KEY") or self.default_api_key

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
        
        logger.info(f"[OCR] Starting OCR process for file: {os.path.basename(file_path)}")
        logger.debug(f"[OCR DEBUG] Full file path: {file_path}")
        logger.debug(f"[OCR DEBUG] Status URL base: {status_url_base}")
        

        try:
            # 1. Prepare Base64 Payload
            file_ext = os.path.splitext(file_path)[1].lower()
            with open(file_path, "rb") as f:
                file_bytes = f.read()
                file_b64 = base64.b64encode(file_bytes).decode("utf-8")
            
            file_size_kb = len(file_bytes) / 1024
            b64_size_kb = len(file_b64) / 1024
            
            logger.debug(f"[OCR DEBUG] File extension: {file_ext}")
            logger.debug(f"[OCR DEBUG] Original file size: {file_size_kb:.2f} KB")
            logger.debug(f"[OCR DEBUG] Base64 payload size: {b64_size_kb:.2f} KB")
            
            payload = {
                "file_base64": file_b64,
                "file_ext": file_ext
            }
            
            headers = {"X-AI-Key": self.api_key} if self.api_key else {}
            masked_key = f"{self.api_key[:8]}...{self.api_key[-4:]}" if self.api_key and len(self.api_key) > 12 else "***"
            logger.debug(f"[OCR DEBUG] Request headers: X-AI-Key={masked_key if self.api_key else 'NOT_SET'}")
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                # 2. Submit Task
                logger.info(f"[OCR] POSTing to {api_url}...")
                logger.debug(f"[OCR DEBUG] Request timeout: 60.0s")
                
                submit_start = time.time()
                resp = await client.post(api_url, json=payload, headers=headers)
                submit_elapsed = time.time() - submit_start
                
                logger.debug(f"[OCR DEBUG] POST response received in {submit_elapsed:.2f}s")
                logger.debug(f"[OCR DEBUG] Response status: {resp.status_code}")
                logger.debug(f"[OCR DEBUG] Response headers: {dict(resp.headers)}")
                
                if resp.status_code != 200:
                    # Log the full response body to debug 404/500
                    resp_body = resp.text[:1000] # Limit log size
                    logger.error(f"[OCR] Task submission FAILED (Status {resp.status_code})\n"
                                 f"  URL: {api_url}\n"
                                 f"  Body: {resp_body}")
                    logger.debug(f"[OCR DEBUG] Failed response headers: {dict(resp.headers)}")
                    return {"status": "error", "error": f"Submission failed: {resp.status_code}"}
                
                init_data = resp.json()
                logger.debug(f"[OCR DEBUG] POST response body: {init_data}")
                
                task_id = init_data.get("task_id")
                if not task_id:
                    logger.error(f"[OCR] No task_id received: {init_data}")
                    return {"status": "error", "error": "No task_id received from server"}
                
                logger.info(f"[OCR] Task {task_id} queued. Starting polling...")
                logger.debug(f"[OCR DEBUG] Polling configuration: interval={self.poll_interval}s, timeout={self.timeout}s")
                
                # 3. Polling Loop
                start_time = time.time()
                poll_count = 0
                
                while time.time() - start_time < self.timeout:
                    poll_count += 1
                    elapsed = time.time() - start_time
                    status_url = f"{status_url_base}/{task_id}"
                    
                    logger.debug(f"[OCR DEBUG] Poll #{poll_count} at {elapsed:.1f}s - GET {status_url}")
                    
                    poll_start = time.time()
                    status_resp = await client.get(status_url, headers=headers)
                    poll_elapsed = time.time() - poll_start
                    
                    logger.debug(f"[OCR DEBUG] Poll #{poll_count} response in {poll_elapsed:.2f}s - Status: {status_resp.status_code}")
                    
                    if status_resp.status_code == 200:
                        task_data = status_resp.json()
                        status = task_data.get("status")
                        
                        logger.debug(f"[OCR DEBUG] Poll #{poll_count} task status: {status}")
                        logger.debug(f"[OCR DEBUG] Poll #{poll_count} full response: {task_data}")
                        
                        if status == "completed":
                            result = task_data.get("result", {})
                            total_time = time.time() - start_time
                            logger.info(f"[OCR] Task {task_id} completed in {total_time:.1f}s after {poll_count} polls")
                            logger.debug(f"[OCR DEBUG] Result metadata: {result.get('metadata', {})}")
                            logger.debug(f"[OCR DEBUG] Text length: {len(result.get('text', ''))} chars")
                            return {
                                "status": "success",
                                "text": result.get("text", ""),
                                "confidence": float(result.get("metadata", {}).get("confidence", 0.95)),
                                "is_ocr": True,
                                "elapsed": total_time
                            }
                        elif status == "failed":
                            error_msg = task_data.get("error", "Unknown error")
                            logger.error(f"[OCR] Task {task_id} FAILED after {poll_count} polls: {error_msg}")
                            logger.debug(f"[OCR DEBUG] Failed task full data: {task_data}")
                            return {"status": "error", "error": f"Task failed: {error_msg}"}
                        
                        # Still pending/processing
                        logger.info(f"[OCR] Task {task_id} status: {status} (poll #{poll_count}, {elapsed:.1f}s elapsed)")
                    else:
                        resp_body = status_resp.text[:500]
                        logger.warning(f"[OCR] Polling error ({status_resp.status_code}) on poll #{poll_count}: {resp_body}")
                        logger.debug(f"[OCR DEBUG] Poll error headers: {dict(status_resp.headers)}")
                        logger.debug(f"[OCR DEBUG] Poll error URL: {status_url}")
                    
                    logger.debug(f"[OCR DEBUG] Sleeping {self.poll_interval}s before next poll...")
                    await asyncio.sleep(self.poll_interval)
                
                total_time = time.time() - start_time
                logger.error(f"[OCR] Polling timed out for task {task_id} after {total_time:.1f}s ({poll_count} polls)")
                logger.debug(f"[OCR DEBUG] Timeout details: configured={self.timeout}s, actual={total_time:.1f}s, polls={poll_count}")
                return {"status": "error", "error": "Polling timeout"}


        except httpx.TimeoutException as e:
            logger.error(f"[OCR] HTTP Timeout during Chandra call: {e}")
            logger.debug(f"[OCR DEBUG] Timeout exception details: {type(e).__name__}, {str(e)}")
            return {"status": "error", "error": f"HTTP Timeout: {str(e)}"}
        except httpx.HTTPError as e:
            logger.error(f"[OCR] HTTP Error during Chandra call: {e}")
            logger.debug(f"[OCR DEBUG] HTTP error details: {type(e).__name__}, {str(e)}")
            if hasattr(e, 'response'):
                logger.debug(f"[OCR DEBUG] Error response status: {e.response.status_code if e.response else 'N/A'}")
                logger.debug(f"[OCR DEBUG] Error response body: {e.response.text[:500] if e.response else 'N/A'}")
            return {"status": "error", "error": f"HTTP Error: {str(e)}"}
        except Exception as e:
            logger.error(f"[OCR] Unexpected exception during Chandra call: {e}")
            logger.debug(f"[OCR DEBUG] Exception type: {type(e).__name__}")
            logger.debug(f"[OCR DEBUG] Exception details: {str(e)}")
            import traceback
            logger.debug(f"[OCR DEBUG] Traceback:\n{traceback.format_exc()}")
            return {"status": "error", "error": str(e)}

ocr_client = ChandraOCRClient()

