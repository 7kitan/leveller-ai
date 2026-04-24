import logging
from shared.redis_client import config_cache # config_cache uses DB 0, but broker is DB 1
import redis
import os

logger = logging.getLogger("queue_utils")

def get_queue_length(queue_name: str) -> int:
    """
    Returns the number of tasks currently in the specified Celery queue.
    """
    try:
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        # Celery broker is usually on DB 1 (as seen in celery_app.py)
        r = redis.Redis(host=host, port=port, db=1)
        return r.llen(queue_name)
    except Exception as e:
        logger.error(f"Error checking queue length for {queue_name}: {e}")
        return 0

def is_queue_overloaded(queue_name: str, threshold: int = 5) -> bool:
    """
    Returns True if the queue length exceeds the threshold.
    """
    length = get_queue_length(queue_name)
    logger.info(f"Queue {queue_name} length: {length}")
    return length >= threshold
