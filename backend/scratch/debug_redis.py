import redis
import os
import sys
from dotenv import load_dotenv

# Thêm đường dẫn để import shared
sys.path.append(os.getcwd())

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")

def diagnose():
    print("--- REDIS DIAGNOSTIC REPORT ---")
    print(f"Configured Host: {REDIS_HOST}")
    print(f"Configured Port: {REDIS_PORT}")
    
    try:
        # Thử kết nối tới db 0 (Auth)
        r0 = redis.Redis(host=REDIS_HOST, port=int(REDIS_PORT), db=0, decode_responses=True)
        print(f"Connection DB 0: {'OK' if r0.ping() else 'FAILED'}")
        
        keys = r0.keys("token:*")
        print(f"Tokens found in DB 0: {len(keys)}")
        for k in keys:
            print(f" - {k}")
            
        # Thử kiểm tra xem có phải đang chạy local redis không
        print("\nChecking for 'Ghost' Redis on localhost:6379...")
        try:
            r_local = redis.Redis(host='127.0.0.1', port=6379, db=0)
            if r_local.ping():
                print("Found a Redis server on 127.0.0.1:6379")
                # Kiểm tra xem đây có phải là Docker Redis không bằng cách xem info
                info = r_local.info()
                print(f"Redis Type: {'Docker/Linux' if 'linux' in info['os'].lower() else 'Windows/Native'}")
                print(f"Redis OS: {info['os']}")
        except:
            print("No local Redis found on 127.0.0.1")

    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")

if __name__ == "__main__":
    diagnose()
