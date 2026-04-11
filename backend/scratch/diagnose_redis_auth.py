import redis
import os
import hashlib
from dotenv import load_dotenv

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
if REDIS_HOST == "advisor_redis":
    # Nếu chạy từ host máy thật, advisor_redis phải là localhost
    REDIS_HOST = "localhost"

REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def diagnose_redis():
    print(f"--- DIAGNOSING REDIS CONNECTIVITY ---")
    print(f"Target: {REDIS_HOST}:{REDIS_PORT} (DB=0)")
    
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
        ping = r.ping()
        print(f"Ping result: {ping}")
        
        all_keys = r.keys("*")
        print(f"Total keys in DB 0: {len(all_keys)}")
        
        token_keys = [k for k in all_keys if k.startswith("token:")]
        session_keys = [k for k in all_keys if k.startswith("user_session:")]
        
        print(f"Token keys found: {len(token_keys)}")
        print(f"Session pointer keys found: {len(session_keys)}")
        
        if token_keys:
            sample_key = token_keys[0]
            val = r.get(sample_key)
            ttl = r.ttl(sample_key)
            print(f"Sample token key: {sample_key}")
            print(f"Value (clipped): {val[:50]}...")
            print(f"TTL: {ttl} seconds")
            
    except Exception as e:
        print(f"CRITICAL ERROR: Could not connect to Redis: {e}")

if __name__ == "__main__":
    diagnose_redis()
