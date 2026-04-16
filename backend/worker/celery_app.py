from celery import Celery
import os
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
        # NOTE: gap_analysis_v3_task.py bị DEPRECATE — dùng analysis_tasks thay thế
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Ho_Chi_Minh",
    enable_utc=True,
)

if __name__ == "__main__":
    celery_app.start()
