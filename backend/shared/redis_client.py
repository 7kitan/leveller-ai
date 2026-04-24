import redis
import os
from dotenv import load_dotenv
import logging

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
CACHE_KEY_PREFIX = os.getenv("CACHE_KEY_PREFIX", "advisor:")
CACHE_DEFAULT_TTL = int(os.getenv("CACHE_DEFAULT_TTL", "3600"))

logger = logging.getLogger(__name__)

class NoOpRedis:
    """Mock Redis client for when cache is disabled."""
    def get(self, *args, **kwargs): return None
    def set(self, *args, **kwargs): return True
    def setex(self, *args, **kwargs): return True
    def delete(self, *args, **kwargs): return True
    def exists(self, *args, **kwargs): return False
    def flushdb(self, *args, **kwargs): return True
    def __getitem__(self, key): return None
    def __setitem__(self, key, value): pass

class PrefixedRedis:
    """Wrapper for Redis client to automatically handle key prefixing and default TTLs."""
    def __init__(self, client, prefix, default_ttl):
        self._client = client
        self._prefix = prefix
        self._default_ttl = default_ttl

    def _prefix_key(self, key):
        if not key.startswith(self._prefix):
            return f"{self._prefix}{key}"
        return key

    def get(self, key):
        return self._client.get(self._prefix_key(key))

    def set(self, key, value, ex=None):
        ttl = ex if ex is not None else self._default_ttl
        return self._client.set(self._prefix_key(key), value, ex=ttl)

    def setex(self, key, time, value):
        return self._client.setex(self._prefix_key(key), time, value)

    def delete(self, key):
        return self._client.delete(self._prefix_key(key))

    def exists(self, key):
        return self._client.exists(self._prefix_key(key))

    def flushdb(self):
        # flushdb remains global to the DB index
        return self._client.flushdb()

    def incr(self, key):
        return self._client.incr(self._prefix_key(key))

    def expire(self, key, time):
        return self._client.expire(self._prefix_key(key), time)

class RedisManager:
    def __init__(self):
        self.clients = {}
        self.pools = {}

    def is_layer_enabled(self, layer: str) -> bool:
        """Kiểm tra lớp cache có được bật không qua CACHE_{LAYER}_ENABLED=true/false."""
        if not CACHE_ENABLED:
            return False
        
        env_key = f"CACHE_{layer.upper()}_ENABLED"
        return os.getenv(env_key, "true").lower() == "true"

    def get_client(self, db_env_key: str, layer_name: str):
        # Get DB index and TTL from env
        db = int(os.getenv(f"CACHE_DB_{layer_name.upper()}", "0"))
        ttl = int(os.getenv(f"CACHE_TTL_{layer_name.upper()}", str(CACHE_DEFAULT_TTL)))

        if not self.is_layer_enabled(layer_name):
            logger.debug(f"Cache layer '{layer_name}' is disabled. Using NoOpRedis.")
            return NoOpRedis()

        if db not in self.clients:
            logger.info(f"Initializing Redis client for layer '{layer_name}' (db={db}, prefix={CACHE_KEY_PREFIX})")
            try:
                pool = redis.ConnectionPool(
                    host=REDIS_HOST, 
                    port=REDIS_PORT, 
                    db=db, 
                    decode_responses=True
                )
                self.pools[db] = pool
                real_client = redis.Redis(connection_pool=pool)
                self.clients[db] = PrefixedRedis(real_client, CACHE_KEY_PREFIX, ttl)
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}. Falling back to NoOpRedis.")
                return NoOpRedis()
        
        return self.clients[db]

# Unified Cache Interface
cache_manager = RedisManager()

# Pre-defined clients for common use cases
auth_cache = cache_manager.get_client("CACHE_DB_AUTH", "auth")
result_cache = cache_manager.get_client("CACHE_DB_RESULT", "result")
llm_cache = cache_manager.get_client("CACHE_DB_LLM", "llm")
taxonomy_cache = cache_manager.get_client("CACHE_DB_TAXONOMY", "taxonomy")
cv_parsed_cache = cache_manager.get_client("CACHE_DB_LLM", "cv_parsed_json")
config_cache = cache_manager.get_client("CACHE_DB_CONFIG", "config")
quota_cache = cache_manager.get_client("CACHE_DB_QUOTA", "quota")
