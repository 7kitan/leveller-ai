import requests
import re
import json

def analyze_ids(urls):
    results = {}
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    for url in urls:
        print(f"\nAnalysing: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=15)
            html = response.text
            
            # Find the true courseId (Stable across Coursera)
            # Pattern: coursera.courseId = (function() { return '...'; })();
            true_id_match = re.search(r"coursera\.courseId\s*=\s*\(function\(\)\s*\{\s*return\s*'([a-zA-Z0-9_-]+)';\s*\}\)\(\);", html)
            true_id = true_id_match.group(1) if true_id_match else "NOT FOUND"
            
            # Find the wrong ID (5yQWB8cIzkMk6XHvHPADG7) context
            wrong_id_pattern = r"5yQWB8cIzkMk6XHvHPADG7"
            wrong_id_context = ""
            if wrong_id_pattern in html:
                start = max(0, html.find(wrong_id_pattern) - 100)
                end = min(len(html), html.find(wrong_id_pattern) + 150)
                wrong_id_context = html[start:end]
            
            # Find any other potential IDs
            potential_ids = re.findall(r'"courseId":"([a-zA-Z0-9_-]+)"', html)
            
            results[url] = {
                "true_course_id": true_id,
                "wrong_id_found": wrong_id_pattern in html,
                "wrong_id_context_snippet": wrong_id_context,
                "other_course_ids_found": list(set(potential_ids))
            }
            
            print(f"  True Course ID: {true_id}")
            print(f"  Potential IDs in JSON: {potential_ids}")
            
        except Exception as e:
            print(f"  Error: {e}")
            
    with open("id_analysis_logs.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)
    print("\nLogs saved to id_analysis_logs.json")

if __name__ == "__main__":
    urls = [
        "https://www.coursera.org/learn/python-for-applied-data-science-ai",
        "https://www.coursera.org/learn/python"
    ]
    analyze_ids(urls)
