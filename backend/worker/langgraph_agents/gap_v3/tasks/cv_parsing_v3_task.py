"""
CV Parsing Task v3 — Celery task entry point.
Thay thế parse_cv_task.py cũ bằng LangGraph pipeline.
"""

from celery import Task
from worker.celery_app import celery_app
from shared.database import SessionLocal
import asyncio
import time
import sys
import logging
import os
import glob


# ── FORCE all loggers to propagate to stderr with correct level ─────────────
# Celery by default only configures its own logger.
# Without this, custom loggers (cv_parsing_v3, cv_parsing_graph, etc.)
# inherit root logger level=WARNING and silently drop all .info() / .debug().
def _configure_worker_logging():
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter(
                "[%(asctime)s] %(name)-30s %(levelname)-8s %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        root.addHandler(handler)
    root.setLevel(logging.INFO)

    # Also set explicit level on all our custom loggers
    for name in [
        "cv_parsing_v3_task",
        "cv_parsing_graph",
        "cv_parsing_v3",
    ]:
        lg = logging.getLogger(name)
        lg.setLevel(logging.INFO)
        # Ensure it has a handler
        if not lg.handlers:
            lg.addHandler(logging.StreamHandler(sys.stderr))


_configure_worker_logging()
logger = logging.getLogger("cv_parsing_v3_task")


class CVParsingTask(Task):
    """Custom Task class — handles on_failure lifecycle."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        cv_id = args[0] if args else "unknown"
        logger.error(
            "=" * 60 + "\n"
            f"[CELERY on_failure] cv_id={cv_id} | task_id={task_id}\n"
            f"  Exception : {type(exc).__name__}: {exc}\n"
            f"  Retries   : {self.max_retries - self.request.retries}/{self.max_retries}\n"
            f"  Traceback : {einfo}\n" + "=" * 60
        )
        self._update_cv_status(cv_id, status="failed", error_msg=str(exc)[:500])

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        cv_id = args[0] if args else "unknown"
        logger.warning(
            f"[CELERY on_retry] cv_id={cv_id} | retry={self.request.retries}/{self.max_retries} "
            f"| countdown=60s | exc={type(exc).__name__}: {exc}"
        )
        self._update_cv_status(
            cv_id,
            status="processing",
            error_msg=f"Retry {self.request.retries}: {str(exc)[:200]}",
        )

    def on_success(self, retval, task_id, args, kwargs):
        cv_id = args[0] if args else "unknown"
        logger.info(
            f"[CELERY on_success] cv_id={cv_id} | task_id={task_id} | retval={retval}"
        )

    # ── Internal ──────────────────────────────────────────────────────────────

    def _update_cv_status(self, cv_id: str, status: str, error_msg: str = ""):
        """Update UserCV record status + error_message in DB."""
        try:
            db = SessionLocal()
            from shared.models import UserCV
            from datetime import datetime

            cv_record = db.query(UserCV).filter(UserCV.id == cv_id).first()
            if cv_record:
                cv_record.status = status
                cv_record.error_message = error_msg
                cv_record.updated_at = datetime.now()
                db.commit()
                logger.info(f"[DB] Updated UserCV {cv_id} status='{status}'")
            else:
                logger.warning(f"[DB] UserCV {cv_id} not found — cannot update status")
            db.close()
        except Exception as db_err:
            logger.error(f"[DB] Failed to update CV status on failure: {db_err}")


@celery_app.task(
    name="worker.tasks.cv_parsing_v3_task.run_cv_parsing",
    bind=True,
    base=CVParsingTask,
    max_retries=2,
    default_retry_delay=60,
    acks_late=True,
    reject_on_worker_lost=True,
)
def run_cv_parsing(self, cv_id: str, user_id: str = None):
    """
    Celery task: Parse CV file → structured data → save to DB.

    Lifecycle:
      [TASK START]  → receive task, validate cv_id
      [GRAPH START]  → invoke LangGraph pipeline
      [STEP 1→4]     each node logs progress
      [TASK END]     success or retry / failure
    """
    t0 = time.monotonic()

    logger.info(
        "\n" + "=" * 60 + "\n"
        f"[TASK START] run_cv_parsing | cv_id={cv_id} | user_id={user_id or 'N/A'}\n"
        f"  retry     : #{self.request.retries}/{self.max_retries}\n"
        f"  task_id   : {self.request.id}\n"
        f"  queue     : {getattr(self.request, 'delivery_info', {}).get('routing_key', 'default')}\n"
        + "="
        * 60
    )

    # ── Validate cv_id upfront ───────────────────────────────────────────────
    try:
        import uuid as _uuid

        _uuid.UUID(cv_id)
    except Exception as e:
        logger.error(f"[TASK ABORT] Invalid cv_id={cv_id}: {e}")
        self._update_cv_status(cv_id, status="failed", error_msg=f"Invalid cv_id: {e}")
        return {"status": "failed", "error": f"Invalid cv_id: {cv_id}", "cv_id": cv_id}

    db = SessionLocal()
    files_to_cleanup = []  # Store ALL matching files, not just first one

    try:
        # ── Step 0: Get file path early for guaranteed cleanup ───────────────
        # CRITICAL: Get file path BEFORE pipeline runs so cleanup works even if pipeline fails
        from shared.models import UserCV
        
        cv_record = db.query(UserCV).filter(UserCV.id == cv_id).first()
        if cv_record and cv_record.file_id:
            # Find ALL files with any extension matching the file_id
            env_dir = os.getenv("CV_UPLOAD_DIR", "data/cv_uploads")
            UPLOAD_DIR = env_dir if os.path.isabs(env_dir) else os.path.join("/app", env_dir)
            pattern = os.path.join(UPLOAD_DIR, f"{cv_record.file_id}.*")
            matching_files = glob.glob(pattern)
            if matching_files:
                files_to_cleanup = matching_files  # Store ALL files for cleanup
                logger.info(f"[TASK] Found {len(files_to_cleanup)} file(s) for cleanup: {files_to_cleanup}")
        
        # ── Step 1: Ensure async event loop ──────────────────────────────────
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("event loop is closed")
        except RuntimeError:
            logger.info("[TASK] Creating new event loop for async pipeline")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # ── Step 2: Invoke LangGraph pipeline ─────────────────────────────────
        from worker.langgraph_agents.gap_v3.cv_parsing_graph import (
            run_cv_parsing_pipeline,
        )

        logger.info(f"[GRAPH START] Invoking cv_parsing_pipeline | cv_id={cv_id}")
        t_graph = time.monotonic()
        result = loop.run_until_complete(
            run_cv_parsing_pipeline(cv_id=cv_id, user_id=user_id, db=db)
        )
        graph_elapsed = time.monotonic() - t_graph

        # ── Step 2: Interpret result ─────────────────────────────────────────
        if result.get("status") == "success":
            cv_parsed = result.get("cv_parsed", {})
            skill_count = len(cv_parsed.get("skills", []))
            work_count = len(cv_parsed.get("work_history", []))
            total_elapsed = time.monotonic() - t0

            logger.info(
                "\n" + "=" * 60 + "\n"
                f"[TASK SUCCESS] cv_id={cv_id} | elapsed={total_elapsed:.1f}s\n"
                f"  full_name      : {cv_parsed.get('full_name', 'N/A')}\n"
                f"  seniority      : {cv_parsed.get('seniority', 'N/A')}\n"
                f"  skills found   : {skill_count}\n"
                f"  work entries   : {work_count}\n"
                f"  experience_yrs : {cv_parsed.get('experience_years_total', 0)}\n"
                f"  is_ocr         : {cv_parsed.get('is_ocr', False)}\n"
                f"  ocr_confidence : {cv_parsed.get('ocr_confidence', 0):.2f}\n"
                f"  graph time     : {graph_elapsed:.1f}s\n" + "=" * 60
            )
            self._update_cv_status(cv_id, status="completed", error_msg="")

            return result

        else:
            error = result.get("error", "Unknown pipeline error")
            total_elapsed = time.monotonic() - t0
            logger.warning(
                f"[TASK PIPELINE FAILED] cv_id={cv_id} | elapsed={total_elapsed:.1f}s\n"
                f"  error: {error}"
            )
            raise Exception(error)

    except Exception as e:
        total_elapsed = time.monotonic() - t0
        retry_count = self.request.retries + 1
        logger.error(
            f"[TASK EXCEPTION] cv_id={cv_id} | elapsed={total_elapsed:.1f}s\n"
            f"  exc_type : {type(e).__name__}\n"
            f"  message  : {e}\n"
            f"  retry    : {retry_count}/{self.max_retries}"
        )
        
        # Decide if we should retry
        # Logic: Don't retry if it's a validation error (e.g. Not a CV) or if it's the last attempt
        non_retryable_msgs = ["Validation failed", "Invalid cv_id", "CV not found", "Raw text too short", "is empty or unreadable"]
        is_retryable = not any(msg in str(e) for msg in non_retryable_msgs)

        if is_retryable and self.request.retries < self.max_retries - 1:
            logger.info(f"[TASK] Scheduling retry {retry_count}/{self.max_retries} in 60s...")
            raise self.retry(exc=e, countdown=60)
        else:
            if not is_retryable:
                logger.warning(f"[TASK] Skipping retry due to non-retryable error: {e}")
            raise e

    finally:
        # ── Cleanup: Delete ALL physical files (success or failure) ──────────
        env_dir = os.getenv("CV_UPLOAD_DIR", "data/cv_uploads")
        UPLOAD_DIR = env_dir if os.path.isabs(env_dir) else os.path.join("/app", env_dir)
        if files_to_cleanup:
            for file_path in files_to_cleanup:
                if os.path.exists(file_path):
                    try:
                        # SECURITY: Prevent Path Traversal
                        abs_f_path = os.path.abspath(file_path)
                        abs_upload_dir = os.path.abspath(UPLOAD_DIR)
                        if abs_f_path.startswith(abs_upload_dir + os.sep) or abs_f_path == abs_upload_dir:
                            os.remove(abs_f_path)
                            logger.info(f"[TASK CLEANUP] ✓ Deleted CV file: {abs_f_path}")
                        else:
                            logger.warning(f"[SECURITY] Attempted to delete file outside upload directory: {abs_f_path}")
                    except Exception as e:
                        logger.warning(f"[TASK CLEANUP] ⚠ Failed to delete CV file {file_path}: {e}")
        
        db.close()
        logger.info(f"[TASK CLEANUP] db closed | cv_id={cv_id}")
