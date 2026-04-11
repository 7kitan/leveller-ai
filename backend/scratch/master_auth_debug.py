import requests
import hashlib
import redis
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Cấu hình
AUTH_URL = "http://localhost:8000/auth/login"
GATEWAY_URL = "http://localhost:8000"
REDIS_HOST = "localhost" # Giả định chạy từ host
REDIS_PORT = 6379

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def master_debug_auth():
    print("=== MASTER AUTH DEBUGGER ===")
    
    # 1. Thử Login lấy Token
    payload = {"email": "admin@example.com", "password": "admin"}
    print(f"1. Attempting login for {payload['email']}...")
    try:
        login_res = requests.post(AUTH_URL, json=payload)
        if login_res.status_code != 200:
            print(f"   FAILED: Login returned {login_res.status_code}")
            print(f"   Detail: {login_res.text}")
            return
            
        data = login_res.json()
        token = data["access_token"]
        print(f"   SUCCESS: Received Token (first 15 chars): {token[:15]}...")
        
        # 2. Tính toán Key Gateway sẽ dùng
        expected_key = f"token:{hash_token(token)}"
        print(f"2. Calculated Gateway Redis Key: {expected_key}")
        
        # 3. Kiểm tra trực tiếp trong Redis
        print("3. Checking Redis directly...")
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
        redis_val = r.get(expected_key)
        
        if redis_val:
            print(f"   FOUND in Redis! Value: {redis_val}")
        else:
            print(f"   NOT FOUND in Redis! This is the issue.")
            # Liệt kê 5 keys gần nhất
            all_keys = r.keys("token:*")
            print(f"   Available token keys in Redis: {all_keys[:5]}")
            
        # 4. Thử gọi Gateway cv/list
        print(f"4. Attempting Gateway call to /cv/list...")
        headers = {"Authorization": f"Bearer {token}"}
        cv_res = requests.get(f"{GATEWAY_URL}/cv/list", headers=headers)
        print(f"   Result: Status {cv_res.status_code}")
        print(f"   Response Body: {cv_res.text}")

    except Exception as e:
        print(f"   ERROR: {e}")

if __name__ == "__main__":
    master_debug_auth()
