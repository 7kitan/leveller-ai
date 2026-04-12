import asyncio
import os
import sys
import json
import uuid
import logging

# Add current directory to path
sys.path.append(os.getcwd())

# Override DB host for local execution if running outside docker
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["REDIS_HOST"] = "localhost"

from shared.database import SessionLocal
from shared.models import User
from shared.auth_utils import create_access_token, hash_token
from shared.redis_client import auth_cache
from services.auth_service.main import verify

# Configure logging
logging.basicConfig(level=logging.INFO)

async def test_auth_fallback():
    db = SessionLocal()
    try:
        # 1. Find a test user
        user = db.query(User).first()
        if not user:
            print("[FAIL] No users found in database. Skip test.")
            return
        
        user_id = str(user.id)
        print(f"--- [AUTH FALLBACK TEST] ---")
        print(f"User: {user.email} (ID: {user_id})")
        
        # 2. Create a token
        token = create_access_token(data={"sub": user_id, "email": user.email})
        token_key = f"token:{hash_token(token)}"
        
        # 3. Ensure token is NOT in Redis
        auth_cache.delete(token_key)
        print(f"Token deleted from Redis: {token_key}")
        
        # 4. Call verify (Deep Verification)
        print("Executing Deep Verification (Redis Miss -> DB Fetch)...")
        result = verify(token=token, db=db)
        
        print(f"Verification Result: {json.dumps(result, indent=2)}")
        
        # 5. Verify it's now in Redis
        cached = auth_cache.get(token_key)
        if cached:
            print(f"[SUCCESS] Data found in Redis after fallback")
            cached_data = json.loads(cached)
            if str(cached_data.get("id")) == str(user_id):
                print("[SUCCESS] Cached data matches User ID.")
            else:
                print(f"[FAILURE] Cached data mismatch. Expected {user_id}, got {cached_data.get('id')}")
        else:
            print("[FAILURE] Token NOT found in Redis after verification.")
            
    except Exception as e:
        import traceback
        print(f"[ERROR] during test: {e}")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_auth_fallback())
