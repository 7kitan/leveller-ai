import sys
import os
import json

# Fix encoding for Windows terminal
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


# Thêm đường dẫn để import được TopCVScraper
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from topcv import TopCVScraper

def debug_job(url, proxy_list=None):
    """
    Debug a single job URL with optional proxy list.
    
    Args:
        url: Job URL to scrape
        proxy_list: List of proxies in format ["IP:PORT:USER:PASS", ...]
    """
    scraper = TopCVScraper(proxy_list=proxy_list)
    print(f"--- Debugging URL: {url} ---")
    if proxy_list:
        print(f"--- Using {len(proxy_list)} proxies ---")
    
    result = scraper.scrape_job_details(url)
    
    if result:
        print("\n[SUCCESS] Extraction Result:")
        print(f"Title: {result.get('title_raw')}")
        print(f"Company: {result.get('company_name')}")
        print(f"Location Raw: {result.get('location_raw')}")
        print(f"City (Normalized): {result.get('location_normalized')}")
        print(f"District (Parsed): {result.get('location_district')}")
        print(f"Employment Type: {result.get('employment_type')}")
        print(f"Salary: {result.get('min_salary_vnd')} - {result.get('max_salary_vnd')} VND")
        print(f"\nJob Description Length: {len(result.get('job_description', ''))}")
        print(f"Requirements Length: {len(result.get('requirements', ''))}")
        print(f"Benefits Length: {len(result.get('benefits', ''))}")
    else:
        print("\n[FAILED] Could not scrape job details.")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Debug TopCV job scraping")
    parser.add_argument("--url", type=str, help="Job URL to scrape")
    parser.add_argument("--proxy", type=str, help="Comma-separated proxy list (IP:PORT:USER:PASS)")
    
    args = parser.parse_args()
    
    # Default test URL
    test_url = args.url or "https://www.topcv.vn/viec-lam/fullstack-developer-java-springboot-javascript/2139018.html"
    
    # Parse proxy list if provided
    proxy_list = None
    if args.proxy:
        proxy_list = [p.strip() for p in args.proxy.split(',') if p.strip()]
        print(f"Loaded {len(proxy_list)} proxies from command line")
    
    debug_job(test_url, proxy_list=proxy_list)
