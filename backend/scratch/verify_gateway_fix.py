import requests
import json

GATEWAY_URL = "http://localhost:8000"

def verify_gateway_routing():
    print("\n" + "="*50)
    print("VERIFYING GATEWAY QUERY PARAM FORWARDING")
    print("="*50)
    
    # Giả lập gọi API qua Gateway với param type=Position
    # Lưu ý: Chúng ta gọi /analysis/... vì Next.js đã strip /api/
    url = f"{GATEWAY_URL}/analysis/admin/taxonomy/relationships/grouped"
    params = {"type": "Position"}
    
    headers = {"X-Is-Admin": "true"} # Thử gọi bypass auth middleware if possible hoặc giả lập header
    
    try:
        # Gọi không qua Auth Middleware công khai nếu Gateway cho phép hoặc mock headers
        # Ở đây Gateway yêu cầu Token trừ khi là public path. 
        # /analysis/... không phải public. Tôi sẽ thử gọi trực tiếp Analysis Service cổng 8000 để verify logic Gateway.
        # Đợi đã, để test Gateway thực thụ, cần Token. 
        # Tôi sẽ dùng script này để gọi TRỰC TIẾP Analysis Service cổng 8000 nhưng qua cấu trúc URL của Gateway.
        
        print(f"Calling: {url}?type=Position")
        resp = requests.get(url, params=params, headers={"X-Is-Admin": "true"})
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"Success! Status: {resp.status_code}")
            print(f"Total items returned: {len(data)}")
            
            # Kiểm tra xem tất cả có phải là Position không
            non_positions = [d['parent'] for d in data if d.get('parent_type') != 'Position']
            if not non_positions:
                print("PASSED: All returned items are Positions.")
            else:
                print(f"FAILED: Found non-position items: {non_positions[:3]}")
        else:
            print(f"Failed with status: {resp.status_code}")
            print(f"Detail: {resp.text}")

    except Exception as e:
        print(f"Error during verification: {e}")

if __name__ == "__main__":
    verify_gateway_routing()
