import json
import time
from curl_cffi import requests
from bs4 import BeautifulSoup

def scrape_topcv_links(base_url, max_urls=500):
    """
    Crawl danh sách link công việc từ TopCV bằng curl_cffi để bypass Cloudflare.
    """
    urls = set()
    page = 1
    
    import random

    # Sử dụng curl_cffi với impersonate để giả lập browser (Chrome), giúp bypass anti-bot
    session = requests.Session(impersonate="chrome120")
    
    # Thiết lập headers đầy đủ để giống trình duyệt thật nhất có thể
    session.headers.update({
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "max-age=0",
        "Referer": "https://www.topcv.vn/",
        "Sec-Ch-Ua": '"Not A(Brand";v="99", "Google Chrome";v="110", "Chromium";v="110"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1"
    })
    
    print(f"Bắt đầu crawl từ: {base_url}")
    
    while len(urls) < max_urls:
        # Xử lý URL phân trang
        if '?' in base_url:
            url = f"{base_url}&page={page}"
        else:
            url = f"{base_url}?page={page}"
            
        print(f"Đang xử lý trang {page}... (Đã lấy được {len(urls)} links)")
        
        try:
            # Gửi request
            response = session.get(url, timeout=20)
            
            if response.status_code != 200:
                print(f"Lỗi: HTTP {response.status_code} tại trang {page}. Có thể bị block.")
                # Nếu bị block, có thể cần nghỉ lâu hơn hoặc dừng lại
                time.sleep(10)
                break
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Selector cho các link chi tiết công việc
            job_items = soup.select('.job-item-search-result h3 a')
            
            if not job_items:
                print(f"Không tìm thấy job nào ở trang {page}. Có thể đã hết dữ liệu hoặc bị bot-detection.")
                break
                
            for item in job_items:
                link = item.get('href')
                if link:
                    clean_link = link.split('?')[0] if '?' in link else link
                    if clean_link not in urls:
                        urls.add(clean_link)
                    
                    if len(urls) >= max_urls:
                        break
                        
            page += 1
            
            # Nghỉ ngẫu nhiên từ 3 đến 7 giây để giả lập người dùng thật, tránh bị khóa IP
            delay = random.uniform(3, 7)
            print(f"Nghỉ {delay:.2f} giây...")
            time.sleep(delay)
            
        except Exception as e:
            print(f"Lỗi ngoại lệ ở trang {page}: {e}")
            break
            
    # Chuyển set thành list để lưu
    result_list = list(urls)
    
    # Lưu ra file JSON
    output_file = "topcv_it_jobs.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result_list, f, indent=2, ensure_ascii=False)
        
    print(f"\n[THÀNH CÔNG] Đã crawl được {len(urls)} links.")
    print(f"Dữ liệu đã được lưu vào file: {output_file}")
    
    return result_list

if __name__ == "__main__":
    # URL tìm kiếm ngành CNTT mới nhất theo yêu cầu
    TARGET_URL = "https://www.topcv.vn/tim-viec-lam-cong-nghe-thong-tin-cr257?sort=new&type_keyword=1&category_family=r257&saturday_status=0"
    
    scrape_topcv_links(TARGET_URL, max_urls=500)
