import logging
import os
import httpx
import base64
import asyncio
from typing import Dict, Any
from pathlib import Path

logger = logging.getLogger("cv_parsing")

CHANDRA_API_URL = os.getenv("CHANDRA_API_URL")
if not CHANDRA_API_URL:
    logger.error("CHANDRA_API_URL is not set!")
CHANDRA_API_KEY = os.getenv("CHANDRA_API_KEY")

async def poll_task_result(task_id: str) -> Dict[str, Any]:
    """Hỏi thăm trạng thái task cho đến khi hoàn thành."""
    # Build URL: base_url/tasks/{task_id}
    # CHANDRA_API_URL thường là .../tasks/ocr
    base_url = CHANDRA_API_URL.rsplit('/', 1)[0] # Cắt bỏ /ocr
    poll_url = f"{base_url}/{task_id}"
    
    headers = {"X-AI-Key": CHANDRA_API_KEY} if CHANDRA_API_KEY else {}

    max_retries = 60 # 60 * 2s = 2 phút tối đa
    for i in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(poll_url, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                status = data.get("status")
                if status == "completed":
                    ocr_text = data.get("result", {}).get("text", "")
                    logger.info(f"Task {task_id} completed. Extracted text ({len(ocr_text)} chars): \n{ocr_text[:500]}...\n[...]")
                    return {"status": "success", "text": ocr_text}
                elif status == "failed":
                    logger.error(f"Task {task_id} failed on Hub: {data.get('error')}")
                    return {"status": "failed", "error": data.get("error")}
                
                # Vẫn đang xử lý (pending/processing)
                if i % 5 == 0:
                    logger.info(f"Task {task_id} status: {status}. Waiting...")
                await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Error polling task {task_id}: {e}")
            await asyncio.sleep(2)

    return {"status": "timeout", "error": "Polling timed out after 2 minutes"}

async def ocr_node_func(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node xử lý OCR: Gửi toàn bộ file sang AI Inference Hub.
    Hub sẽ tự động nhận diện PDF và thực hiện OCR đa trang.
    """
    file_path = state["file_path"]
    logger.info(f"--- [OCR NODE] Sending file to AI Hub: {file_path} ---")

    if not CHANDRA_API_KEY:
        logger.warning("CHANDRA_API_KEY not set. Ensure Hub authentication is configured.")

    try:
        # 1. Đọc file và chuyển sang Base64
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        
        file_base64 = base64.b64encode(file_bytes).decode("utf-8")
        file_ext = Path(file_path).suffix.lower()

        # 2. Tạo task OCR trên Hub
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"X-AI-Key": CHANDRA_API_KEY} if CHANDRA_API_KEY else {}
            payload = {
                "file_base64": file_base64,
                "file_ext": file_ext
            }
            response = await client.post(CHANDRA_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            
            task_data = response.json()
            task_id = task_data.get("task_id")
            
            if not task_id:
                return {"error": "Hub did not return a task_id", "status": "failed"}

        # 3. Poll kết quả
        logger.info(f"Task created: {task_id}. Polling for results...")
        result = await poll_task_result(task_id)

        if result["status"] == "success":
            full_text = result["text"]
            logger.info(f"OCR completed successfully. Extracted {len(full_text)} characters.")
            return {"raw_text": full_text, "is_ocr": True, "status": "extracted"}
        else:
            return {"error": result.get("error", "Unknown Hub error"), "status": "failed"}

    except Exception as e:
        logger.error(f"OCR Node Error: {e}")
        return {"error": f"Lỗi kết nối tới AI Hub: {str(e)}", "status": "failed"}
