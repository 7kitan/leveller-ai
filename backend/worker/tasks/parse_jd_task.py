"""
Legacy JD Parsing Task — STUB.
Phase 4 placeholder — tránh worker crash khi thiếu module.
"""

from celery import Task
from worker.celery_app import celery_app
import logging

logger = logging.getLogger("worker.tasks.parse_jd_task")


class LegacyJDTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"[LEGACY JD] task failed: {exc}")


@celery_app.task(
    name="worker.tasks.parse_jd_task.parse_jd",
    bind=True,
    base=LegacyJDTask,
    max_retries=0,
)
def parse_jd(self, job_id: str, jd_text: str):
    """
    Legacy entry point — STUB.
    JD parsing hiện do jd_service xử lý trực tiếp.
    """
    logger.warning(f"[LEGACY parse_jd] called — stub task\n  job_id={job_id}")
    return {"status": "stub", "message": "JD parsing is handled by jd_service"}
