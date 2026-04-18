from curl_cffi import requests
import time

def test_bypass_curl_cffi():
    url = "https://www.topcv.vn/viec-lam/java-developer/2119168.html"
    
    headers = {
        "authority": "www.topcv.vn",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "accept-language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "cache-control": "max-age=0",
        "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    print("Attempting bypass with curl_cffi (Chrome Impersonation)...")
    try:
        # Step 1: Visit homepage to get cookies
        print("1. Visiting homepage...")
        session = requests.Session()
        session.get("https://www.topcv.vn/", headers=headers, impersonate="chrome120")
        time.sleep(2)
        
        # Step 2: Request Job
        print("2. Requesting Job Detail...")
        resp = session.get(url, headers=headers, impersonate="chrome120")
        print(f"Status Code: {resp.status_code}")
        
        if resp.status_code == 200:
            print("SUCCESS! Bypass working.")
            if "Attention Required! | Cloudflare" in resp.text:
                print("Wait... HTML content says Cloudflare block.")
            else:
                print("HTML looks legitimate.")
                with open("bypass_success.html", "w", encoding="utf-8") as f:
                    f.write(resp.text)
                print("Saved HTML to bypass_success.html")
        else:
            print(f"FAILED. Status {resp.status_code}")
            print(resp.text[:500])
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    test_bypass_curl_cffi()
