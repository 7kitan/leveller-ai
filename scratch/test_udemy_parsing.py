from curl_cffi import requests
import re
import json

def test_udemy_html_parsing():
    url = "https://www.udemy.com/courses/search/?q=python"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
    }

    print("Fetching Udemy HTML and looking for embedded JSON data...")
    try:
        response = requests.get(
            url, 
            headers=headers,
            impersonate="chrome120",
            timeout=15
        )
        
        if response.status_code == 200:
            html = response.text
            print(f"Successfully fetched HTML ({len(html)} bytes)")
            
            # Look for JSON in scripts. Udemy often uses a specific class or ID for their data script.
            # Common patterns: window.__PRELOADED_STATE__, window.UD.visiting_user, etc.
            
            # Let's search for "courses" or "results" in the scripts
            data_match = re.search(r'id="schema-course-list">\s*({.*?})\s*</script>', html, re.DOTALL)
            if data_match:
                print("Found schema-course-list JSON!")
                data = json.loads(data_match.group(1))
                print(json.dumps(data, indent=2)[:500] + "...")
            else:
                # Try another common pattern for Udemy
                # Udemy often stores data in a script tag with data-purpose="seo-data" or similar
                print("Searching for alternative data patterns...")
                if "course" in html.lower():
                    print("Page contains 'course' text, but JSON script not found by regex.")
                    # Let's save a snippet of script tags for inspection
                    scripts = re.findall(r'<script.*?>.*?</script>', html, re.DOTALL)
                    print(f"Found {len(scripts)} script tags.")
                    for i, s in enumerate(scripts):
                        if "course" in s.lower() and len(s) > 1000:
                            print(f"Script {i} looks promising (length {len(s)})")
                            print(s[:200] + "...")
        else:
            print(f"Failed. Status: {response.status_code}")
            
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    test_udemy_html_parsing()
