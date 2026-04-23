import os
import logging
from celery import Celery
from celery.signals import after_setup_logger
from dotenv import load_dotenv

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")

# Celery using Redis DB 1 as broker/backend
CELERY_BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/1"
CELERY_RESULT_BACKEND = f"redis://{REDIS_HOST}:{REDIS_PORT}/1"

celery_app = Celery(
    "worker",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        "worker.tasks.parse_cv_task",  # Legacy CV parsing (khi USE_LLM_GAP_AGENT_V3=false)
        "worker.tasks.parse_jd_task",  # JD stub (Phase 4)
        "worker.tasks.analysis_tasks",  # Main analysis entry (v3 khi flag=true, legacy khi flag=false)
        "worker.langgraph_agents.gap_v3.tasks.cv_parsing_v3_task",  # CV parsing v3 (khi USE_LLM_GAP_AGENT_V3=true)
        "worker.tasks.crawler_tasks",  # Course metadata crawler
        "worker.tasks.market_stats_tasks", # Daily market data aggregation
        # NOTE: gap_analysis_v3_task.py bị DEPRECATE — dùng analysis_tasks thay thế
    ],
)

@after_setup_logger.connect
def setup_logging(logger, *args, **kwargs):
    """
    Ensure our custom loggers are visible in the Celery worker logs.
    By default, Celery's logging setup might swallow logs from other loggers.
    """
    formatter = logging.Formatter(
        "[%(asctime)s: %(levelname)s/%(processName)s] %(name)s: %(message)s"
    )

    # List of loggers to force to stdout
    loggers_to_config = [
        "worker",
        "analysis_worker",
        "crawler_worker",
        "gap_analysis_v3",
        "llm_utils",
        "gap_calculator",
        "market_stats_worker",
    ]

    for logger_name in loggers_to_config:
        l = logging.getLogger(logger_name)
        l.setLevel(logging.INFO)
        # Ensure it has a handler if it's not propagating to a configured root
        if not l.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            l.addHandler(handler)
        l.propagate = True

    logger.info("✓ Celery logging heartbeat — custom loggers configured.")


celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Ho_Chi_Minh",
    enable_utc=True,
    task_routes={
        "worker.tasks.analysis_tasks.*": {"queue": "analysis_queue"},
        "worker.langgraph_agents.gap_v3.tasks.cv_parsing_v3_task.*": {"queue": "parsing_queue"},
        "worker.tasks.crawler_tasks.*": {"queue": "crawler_queue"},
    },
    beat_schedule={
        "auto-crawl-topcv-every-30-mins": {
            "task": "worker.tasks.crawler_tasks.crawl_topcv_jobs_task",
            "schedule": 1800.0,  # 30 minutes
            "args": (20,),
        },
        "daily-market-aggregation": {
            "task": "worker.tasks.market_stats_tasks.aggregate_market_data",
            "schedule": 86400.0, # 24 hours
        },
        "daily-youtube-cleanup": {
            "task": "worker.tasks.market_stats_tasks.cleanup_expired_youtube_courses",
            "schedule": 86400.0, # 24 hours
        },
    },
)

if __name__ == "__main__":
    celery_app.start()
