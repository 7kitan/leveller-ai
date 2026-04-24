"""
Legacy CV Parsing Task — DEPRECATED.
Chỉ dùng khi USE_LLM_GAP_AGENT_V3=false (không recommend).
Giữ lại để tránh worker crash khi feature flag chuyển sang legacy.
"""

from celery import Task
from worker.celery_app import celery_app
from shared.database import SessionLocal
import logging

logger = logging.getLogger("worker.tasks.parse_cv_task")


class LegacyCVTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"[LEGACY] CV task failed: {exc}")


@celery_app.task(
    name="worker.tasks.parse_cv_task.parse_cv",
    bind=True,
    base=LegacyCVTask,
    max_retries=0,
)
def parse_cv(self, user_id: str, cv_id: str, file_path: str):
    """
    Legacy entry point — DEPRECATED.
    Use worker.tasks.cv_parsing_v3_task.run_cv_parsing instead.
    """
    logger.warning(
        f"[LEGACY parse_cv] called — this task is deprecated!\n"
        f"  user_id={user_id} | cv_id={cv_id} | file_path={file_path}\n"
        f"  This task does nothing. Set USE_LLM_GAP_AGENT_V3=true to use v3 pipeline."
    )
    
    # ── Cleanup physical file even for deprecated task ─────────────────────
    import os
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.info(f"[LEGACY] ✓ Deleted CV file: {file_path}")
        except Exception as e:
            logger.warning(f"[LEGACY] ⚠ Failed to delete CV file {file_path}: {e}")

    return {"status": "deprecated", "message": "Use v3 pipeline instead"}
