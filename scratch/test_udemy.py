from curl_cffi import requests
import json

def test_udemy_fetch():
    url = "https://www.udemy.com/api-2.0/courses/?page=1&page_size=1&search=python"
    
    # Try with impersonation
    print("Testing Udemy API with curl_cffi (impersonate='chrome120')...")
    try:
        response = requests.get(
            url, 
            impersonate="chrome120",
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("Successfully fetched data!")
            print(json.dumps(data, indent=2)[:500] + "...")
        else:
            print("Failed to fetch. Might need more headers or a fresh cookie.")
            print(f"Response text snippet: {response.text[:200]}")
            
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    test_udemy_fetch()
