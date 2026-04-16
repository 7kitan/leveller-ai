"""
CV Parsing Task v3 — Celery task entry point.
Thay thế parse_cv_task.py cũ bằng LangGraph pipeline.
"""

from celery import Task
from worker.celery_app import celery_app
from shared.database import SessionLocal
import logging
import asyncio

logger = logging.getLogger("cv_parsing_v3_task")


class CVParsingTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"CV Parsing task {task_id} failed: {exc}")


@celery_app.task(
    name="worker.tasks.cv_parsing_v3_task.run_cv_parsing",
    bind=True,
    base=CVParsingTask,
    max_retries=2,
)
def run_cv_parsing(self, cv_id: str, user_id: str = None):
    """
    Celery task: Parse CV file → structured data → save to DB.
    Gọi LangGraph CV Parsing Pipeline (gap_v3).
    """
    db = SessionLocal()
    logger.info(f"CV Parsing v3 Task: cv_id={cv_id}, user_id={user_id}")

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        from worker.langgraph_agents.gap_v3.cv_parsing_graph import (
            run_cv_parsing_pipeline,
        )

        result = loop.run_until_complete(
            run_cv_parsing_pipeline(cv_id=cv_id, user_id=user_id or "", db=db)
        )

        if result.get("status") == "success":
            cv_parsed = result.get("cv_parsed", {})
            skill_count = len(cv_parsed.get("skills", []))
            logger.info(f"CV Parsing SUCCESS: {cv_id} | {skill_count} skills parsed")
            return result
        else:
            logger.warning(f"CV Parsing FAILED: {cv_id} | {result.get('error')}")
            raise Exception(result.get("error", "Unknown error"))

    except Exception as e:
        logger.error(f"CV Parsing v3 task error for {cv_id}: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60)

    finally:
        db.close()
