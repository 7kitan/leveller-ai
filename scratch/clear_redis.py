import redis

def clear_lockout():
    try:
        # Redis is on localhost DB 0
        REDIS_PASSWORD = "1234567891abcdef"
        r = redis.Redis(host='localhost', port=6379, db=0, password=REDIS_PASSWORD, decode_responses=True)
        
        # We found the IP is 172.20.0.1 from the logs
        # The prefix is "advisor:"
        prefix = "advisor:"
        ips = ["127.0.0.1", "172.20.0.1"]
        emails = ["admin@leveller.ai", "admin@example.com"]
        
        for ip in ips:
            keys = [f"{prefix}lockout:{ip}", f"{prefix}login_attempts_ip:{ip}"]
            for k in keys:
                if r.delete(k):
                    print(f"Cleared Redis key: {k}")
                else:
                    print(f"Key not found: {k}")
            
        for email in emails:
            k = f"{prefix}login_attempts:{email}"
            if r.delete(k):
                print(f"Cleared Redis key: {k}")
            else:
                print(f"Key not found: {k}")
            
        print("Redis cleanup complete.")
    except Exception as e:
        print(f"Redis clear failed: {e}")

if __name__ == "__main__":
    clear_lockout()
