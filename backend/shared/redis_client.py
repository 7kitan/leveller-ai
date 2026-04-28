import redis
import os
from dotenv import load_dotenv
import logging

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)  # SECURITY: Support password authentication
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
CACHE_KEY_PREFIX = os.getenv("CACHE_KEY_PREFIX", "advisor:")
CACHE_DEFAULT_TTL = int(os.getenv("CACHE_DEFAULT_TTL", "3600"))

logger = logging.getLogger(__name__)

# SECURITY: Warn if Redis password is not set in production
if not REDIS_PASSWORD and os.getenv("ENVIRONMENT", "development").lower() == "production":
    logger.warning("=" * 80)
    logger.warning("SECURITY WARNING: Redis password is not set in production!")
    logger.warning("Please set REDIS_PASSWORD in your .env file.")
    logger.warning("=" * 80)

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
    def incr(self, key): return 1
    def incr_with_expire(self, key, ttl): return 1

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

    def delete(self, *keys):
        """Delete one or more keys."""
        if not keys:
            return 0
        prefixed_keys = [self._prefix_key(k) for k in keys]
        return self._client.delete(*prefixed_keys)

    def exists(self, key):
        return self._client.exists(self._prefix_key(key))

    def flushdb(self):
        # flushdb remains global to the DB index
        return self._client.flushdb()

    def incr(self, key):
        return self._client.incr(self._prefix_key(key))

    def expire(self, key, time):
        return self._client.expire(self._prefix_key(key), time)
    
    def ttl(self, key):
        """Get the time to live for a key in seconds."""
        return self._client.ttl(self._prefix_key(key))
    
    def scan(self, cursor=0, match=None, count=None):
        """
        Scan keys with automatic prefix handling.
        
        Args:
            cursor: The cursor position (0 to start)
            match: Pattern to match (will be prefixed automatically)
            count: Number of keys to return per iteration
            
        Returns:
            Tuple of (next_cursor, list_of_keys)
        """
        # Prefix the match pattern if provided
        if match:
            prefixed_match = self._prefix_key(match)
        else:
            prefixed_match = f"{self._prefix}*"
        
        # Call the underlying Redis scan
        kwargs = {"match": prefixed_match}
        if count is not None:
            kwargs["count"] = count
            
        cursor, keys = self._client.scan(cursor=cursor, **kwargs)
        
        # Return keys as-is (with prefix) for consistency
        return cursor, keys
    
    def eval(self, script, numkeys, *keys_and_args):
        """Execute Lua script with automatic key prefixing."""
        # Prefix the keys (first numkeys arguments after script)
        prefixed_keys = [self._prefix_key(k) for k in keys_and_args[:numkeys]]
        # Keep the rest of arguments as-is
        args = keys_and_args[numkeys:]
        return self._client.eval(script, numkeys, *prefixed_keys, *args)

    def incr_with_expire(self, key, ttl):
        """Atomic increment with expire (via Lua script)."""
        lua = """
        local current = redis.call('INCR', KEYS[1])
        if current == 1 then
            redis.call('EXPIRE', KEYS[1], ARGV[1])
        end
        return current
        """
        # Note: If self._client is NoOpRedis, this won't work, but NoOpRedis doesn't have register_script.
        # However, for NoOpRedis, we should just return 1 or something.
        if hasattr(self._client, 'register_script'):
            script = self._client.register_script(lua)
            return script(keys=[self._prefix_key(key)], args=[ttl])
        return 1 # Fallback for NoOpRedis

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
                    password=REDIS_PASSWORD,  # SECURITY: Use password if configured
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
