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

def debug_job(url):
    scraper = TopCVScraper()
    print(f"--- Debugging URL: {url} ---")
    
    result = scraper.scrape_job_details(url)
    
    if result:
        print("\n[SUCCESS] Extraction Result:")
        print(f"Title: {result.get('title_raw')}")
        print(f"Location Raw: {result.get('location_raw')}")
        print(f"City (Normalized): {result.get('location_normalized')}")
        print(f"District (Parsed): {result.get('location_district')}")
        
        # In thêm qgTracking data để so sánh nếu có log
    else:
        print("\n[FAILED] Could not scrape job details.")

if __name__ == "__main__":
    test_url = "https://www.topcv.vn/viec-lam/chuyen-vien-trien-khai-phan-mem-quan-ly-khach-san-oracle-opera-pms-opera-cloud-opera-pms-implementation-consultant-nhan-viec-ngay/2114007.html"
    debug_job(test_url)
