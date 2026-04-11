import redis
import os
from dotenv import load_dotenv

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")

# Có 3 DB index như trong blueprint:
# db=0: Auth Cache
# db=1: Celery Broker (thường chỉnh trong celery config, nhưng có thể dùng ở đây)
# db=2: Result Cache

class RedisClient:
    def __init__(self, db=0):
        self.pool = redis.ConnectionPool(
            host=REDIS_HOST, 
            port=REDIS_PORT, 
            db=db, 
            decode_responses=True
        )

    def get_client(self):
        return redis.Redis(connection_pool=self.pool)

# Singletons for common use cases
auth_cache = RedisClient(db=0).get_client()
result_cache = RedisClient(db=2).get_client()
