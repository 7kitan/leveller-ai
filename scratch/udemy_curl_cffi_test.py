from curl_cffi import requests
import xml.etree.ElementTree as ET
import json
import re

def test_udemy_sitemap_with_curl_cffi():
    """Thử nghiệm fetch Udemy Sitemap bằng curl_cffi để bypass 403"""
    url = "https://www.udemy.com/sitemap/topic.xml"
    print(f"[*] Trying curl_cffi for: {url}")
    
    try:
        # Sử dụng impersonate='chrome' để giả lập vân tay trình duyệt Chrome
        response = requests.get(url, impersonate="safari15_5", timeout=60)
        print(f"[+] Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("[+] Success! Bypass 403 thành công.")
            # Parse một vài URL để chứng minh
            root = ET.fromstring(response.content)
            ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            urls = [url_tag.find('ns:loc', ns).text for url_tag in root.findall('ns:url', ns)[:5]]
            print("First 5 URLs from sitemap:")
            for u in urls: print(f" - {u}")
            return True
    except Exception as e:
        print(f"[!] Error: {e}")
    return False

def test_udemy_topic_page_parsing(topic_url):
    """Thử nghiệm lấy link khóa học từ trang Topic"""
    print(f"\n[*] Parsing topic page: {topic_url}")
    try:
        response = requests.get(topic_url, impersonate="safari15_5", timeout=60)
        if response.status_code == 200:
            html = response.text
            # Tìm các link khóa học (thường có pattern /course/course-slug/)
            # Lưu ý: Udemy thường load khóa học qua JSON/API sau khi load trang, 
            # nhưng một số link vẫn nằm trong HTML server-side render.
            course_links = re.findall(r'href="/course/([^/"]+)/"', html)
            unique_links = list(set(course_links))
            
            print(f"[+] Found {len(unique_links)} potential course links in HTML:")
            for link in unique_links[:10]:
                print(f" - https://www.udemy.com/course/{link}/")
            
            if not unique_links:
                print("[!] Không tìm thấy link khóa học trực tiếp trong HTML. Có khả năng Udemy dùng GraphQL/API để load danh sách.")
    except Exception as e:
        print(f"[!] Error: {e}")

if __name__ == "__main__":
    if test_udemy_sitemap_with_curl_cffi():
        # Thử lấy link khóa học từ trang topic Python
        test_udemy_topic_page_parsing("https://www.udemy.com/topic/python/")
