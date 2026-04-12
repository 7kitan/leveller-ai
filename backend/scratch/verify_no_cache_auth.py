import os
import asyncio
import sys
import json
import uuid
import logging

# Set env var before any imports that might use it
os.environ["CACHE_ENABLED"] = "false"
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["REDIS_HOST"] = "localhost"

# Add current directory to path
sys.path.append(os.getcwd())

from shared.database import SessionLocal
from shared.models import User
from shared.auth_utils import create_access_token
from shared.redis_client import auth_cache, CACHE_ENABLED
from services.auth_service.main import verify

# Configure logging
logging.basicConfig(level=logging.INFO)

async def test_no_cache_auth():
    print(f"--- [NO-CACHE AUTH TEST] ---")
    print(f"CACHE_ENABLED in redis_client: {CACHE_ENABLED}")
    
    db = SessionLocal()
    try:
        # 1. Find a test user (using vanbachpkc4@gmail.com if possible)
        user = db.query(User).filter(User.email == "vanbachpkc4@gmail.com").first()
        if not user:
            user = db.query(User).first()
            
        if not user:
            print("[FAIL] No users found in database.")
            return
        
        user_id = str(user.id)
        print(f"Testing with User: {user.email} (ID: {user_id})")
        
        # 2. Create a token
        token = create_access_token(data={"sub": user_id, "email": user.email})
        
        # 3. Call verify()
        # This should trigger "Deep Verification" because CACHE_ENABLED is False, 
        # so auth_cache.get() will return None (NoOpRedis).
        print("Executing Deep Verification (Cache is Disabled)...")
        result = verify(token=token, db=db)
        
        print(f"Verification Result: {json.dumps(result, indent=2)}")
        
        if result.get("id") == user_id:
            print("[SUCCESS] Deep verification worked perfectly with CACHE_ENABLED=false!")
        else:
            print(f"[FAILURE] Verification returned wrong ID: {result.get('id')}")
            
    except Exception as e:
        import traceback
        print(f"[ERROR] during test: {e}")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_no_cache_auth())
