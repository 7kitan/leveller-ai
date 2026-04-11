import os
import logging
from typing import Dict, Any

logger = logging.getLogger("cv_parsing")

def cleanup_node_func(state: Dict[str, Any]) -> Dict[str, Any]:
    """Node dọn dẹp file tạm sau khi xử lý."""
    file_path = state.get("file_path")
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.info(f"--- [CLEANUP NODE] Deleted file: {file_path} ---")
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
    
    return {"status": "completed"}
