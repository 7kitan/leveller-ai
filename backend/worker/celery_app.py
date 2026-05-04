import os
import logging
from celery import Celery
from celery.signals import after_setup_logger
from celery.schedules import crontab
from dotenv import load_dotenv
from shared.database import engine, Base
import shared.models # Ensure all models are registered
# Ensure tables are created on worker start
from celery.signals import worker_ready, worker_process_init

@worker_ready.connect
def init_db_on_start(sender, **kwargs):
    from shared.database import init_db
    init_db()
    logging.info("✅ Database initialized in main worker process")

@worker_process_init.connect
def init_worker_process(**kwargs):
    """Initialize PromptManager in each forked worker process"""
    from shared.database import SessionLocal
    from shared.redis_client import config_cache
    from shared.prompt_manager import init_prompt_manager
    
    try:
        init_prompt_manager(config_cache, SessionLocal)
        logging.info("✅ PromptManager initialized in worker child process")
    except Exception as e:
        logging.error(f"❌ Failed to initialize PromptManager in worker process: {e}")
        import traceback
        traceback.print_exc()

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")

# Celery using Redis DB 1 as broker/backend
CELERY_BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/1"
CELERY_RESULT_BACKEND = f"redis://{REDIS_HOST}:{REDIS_PORT}/1"

# ============================================================================
# BENCHMARK EXTENSION (Optional - Can be disabled in production)
# ============================================================================
# Build task list conditionally based on ENABLE_BENCHMARK setting
from shared.config_utils import config_manager

CORE_TASKS = [
    "worker.tasks.parse_cv_task",  # Legacy CV parsing (khi USE_LLM_GAP_AGENT_V3=false)
    "worker.tasks.parse_jd_task",  # JD stub (Phase 4)
    "worker.tasks.analysis_tasks",  # Main analysis entry (v3 khi flag=true, legacy khi flag=false)
    "worker.langgraph_agents.gap_v3.tasks.cv_parsing_v3_task",  # CV parsing v3 (khi USE_LLM_GAP_AGENT_V3=true)
    "worker.tasks.crawler_tasks",  # Course metadata crawler
    "worker.tasks.market_stats_tasks", # Daily market data aggregation
    "worker.tasks.vector_tasks",  # Vector embedding rebuild (admin-triggered)
]

ENABLE_BENCHMARK = config_manager.get_setting("ENABLE_BENCHMARK", default=True, cast=bool)
if ENABLE_BENCHMARK:
    CELERY_TASKS = CORE_TASKS + ["worker.extensions.benchmark.tasks"]
    logging.info("[WORKER] ✅ Benchmark extension ENABLED - Tasks registered")
else:
    CELERY_TASKS = CORE_TASKS
    logging.info("[WORKER] ⚠️ Benchmark extension DISABLED - Tasks skipped")

celery_app = Celery(
    "worker",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=CELERY_TASKS,
)

@after_setup_logger.connect
def setup_logging(logger, *args, **kwargs):
    """
    Ensure our custom loggers are visible in the Celery worker logs.
    """
    formatter = logging.Formatter(
        "[%(asctime)s: %(levelname)s/%(processName)s] %(name)s: %(message)s"
    )

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
        if not l.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            l.addHandler(handler)
        l.propagate = True

    logger.info("✓ Celery logging heartbeat — custom loggers configured.")


# Build task routes conditionally
CORE_TASK_ROUTES = {
    # Analysis tasks → analysis queue
    "worker.tasks.analysis_tasks.*": {"queue": "analysis"},
    
    # CV parsing tasks → cv_parsing queue
    "worker.tasks.cv_parsing_v3_task.*": {"queue": "cv_parsing"},
    "worker.tasks.parse_cv_task.*": {"queue": "cv_parsing"},
    
    # Crawler tasks → market_stats queue (reuse existing worker)
    "worker.tasks.crawler_tasks.*": {"queue": "market_stats"},
    
    # Market stats tasks → market_stats queue
    "worker.tasks.market_stats_tasks.*": {"queue": "market_stats"},
    
    # Vector tasks → market_stats queue (low priority, admin-triggered)
    "worker.tasks.vector_tasks.*": {"queue": "market_stats"},
    
    # Email tasks → email queue (if implemented)
    "worker.tasks.email_tasks.*": {"queue": "email"},
}

# Add benchmark routing only if enabled
if ENABLE_BENCHMARK:
    CORE_TASK_ROUTES["worker.extensions.benchmark.tasks.*"] = {"queue": "benchmark"}

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Ho_Chi_Minh",
    enable_utc=True,
    task_routes=CORE_TASK_ROUTES,
    beat_schedule={
        "auto-crawl-topcv-every-30-mins": {
            "task": "worker.tasks.crawler_tasks.crawl_topcv_jobs_task",
            "schedule": 1800.0,  # 30 minutes
            "args": (20,),
        },
        "daily-market-aggregation": {
            "task": "worker.tasks.market_stats_tasks.aggregate_market_data",
            "schedule": crontab(hour=2, minute=0),  # Daily at 2:00 AM
        },
        "daily-youtube-cleanup": {
            "task": "worker.tasks.market_stats_tasks.cleanup_expired_youtube_courses",
            "schedule": 86400.0, # 24 hours
        },
        "daily-system-log-cleanup": {
            "task": "worker.tasks.market_stats_tasks.cleanup_system_logs",
            "schedule": 86400.0, # 24 hours
        },
    },
)

if __name__ == "__main__":
    celery_app.start()
