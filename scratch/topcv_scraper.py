from curl_cffi import requests
from bs4 import BeautifulSoup
import time
import os
import sys
import re
import json

# Ensure stdout uses utf-8 for printing Vietnamese characters
if sys.stdout.encoding.lower() != 'utf-8':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    else:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def extract_job_id(url: str) -> str:
    match = re.search(r'/(\d+)\.html', url)
    return match.group(1) if match else ""

def build_source_id(platform: str, job_id: str) -> str:
    return f"{platform}_{job_id}"

def extract_qg_tracking(html: str):
    """Trích xuất dữ liệu từ window.qgTracking trong script tag (Rất chính xác)."""
    try:
        match = re.search(r'window\.qgTracking\s*=\s*({.*?});', html, re.DOTALL)
        if match:
            # Làm sạch JSON (thay thế single quotes bằng double quotes, loại bỏ trailing commas nếu có)
            json_str = match.group(1)
            # TopCV sử dụng format JS object, không hẳn là JSON chuẩn, nhưng thường là key-value đơn giản
            # Ta dùng regex để lấy các trường cần thiết thay vì json.loads nếu không chuẩn
            data = {}
            for key in ['job_title', 'recruiter_company', 'experience', 'work_location', 'salary_range']:
                key_match = re.search(f'"{key}"\s*:\s*"(.*?)"', json_str)
                if key_match:
                    # Unescape unicode
                    val = key_match.group(1).encode('utf-8').decode('unicode_escape')
                    data[key] = val
            return data
    except Exception:
        pass
    return None

def parse_salary_structured(text: str):
    """Tiện ích tách lương thành số để tìm kiếm."""
    text = text.replace('.', '').replace(',', '')
    numbers = re.findall(r'\d+', text)
    res = {"raw": text, "min": 0, "max": 0, "currency": "VND"}
    
    # Xác định nhân tử (Triệu/Nghìn)
    multiplier = 1000000 if "triệu" in text.lower() else (1000 if "nghìn" in text.lower() or "k" in text.lower() else 1)
    
    if len(numbers) >= 2:
        res["min"] = int(numbers[0]) * multiplier
        res["max"] = int(numbers[1]) * multiplier
    elif len(numbers) == 1:
        if "tới" in text.lower() or "đến" in text.lower() or "lên đến" in text.lower():
            res["min"] = 0
            res["max"] = int(numbers[0]) * multiplier
        elif "từ" in text.lower() or "trên" in text.lower():
            res["min"] = int(numbers[0]) * multiplier
            res["max"] = 0 # Không giới hạn
        else:
            res["min"] = int(numbers[0]) * multiplier
            res["max"] = res["min"]
            
    res["currency"] = "USD" if "usd" in text.lower() or "$" in text.lower() else "VND"
    return res

def crawl_topcv():
    # 1. Danh sách URL trang search
    url = "https://www.topcv.vn/tim-viec-lam-cong-nghe-thong-tin-cr257?sort=new&type_keyword=1&category_family=r257&saturday_status=0"
    
    # Header mô phỏng Chrome 120
    headers = {
        "authority": "www.topcv.vn",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "accept-language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "referer": "https://www.topcv.vn/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # Thư mục lưu HTML để test
    save_dir = "samples"
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    print(f"Bắt đầu phân tích và bypass TopCV: {url}")
    try:
        # Sử dụng curl_cffi để giả lập TLS Fingerprint (JA3) của Chrome 120
        session = requests.Session()
        
        # Bước 1: Khởi tạo session qua trang chủ
        print("Đang khởi tạo session qua trang chủ...")
        session.get("https://www.topcv.vn/", headers=headers, impersonate="chrome120")
        time.sleep(1)
        
        # Bước 2: Lấy danh sách job
        print("Đang lấy danh sách công việc...")
        response = session.get(url, headers=headers, impersonate="chrome120")
    except Exception as e:
        print(f"Lỗi kết nối: {e}")
        return

    if response.status_code != 200:
        print(f"Không thể bypass thành công (Mã lỗi: {response.status_code}).")
        return
        
    soup = BeautifulSoup(response.text, 'html.parser')
    job_links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '/viec-lam/' in href and 'topcv.vn/viec-lam' in href and href not in job_links:
            job_links.append(href)
            
    if not job_links:
        print("Không tìm thấy link, Cloudflare có thể vẫn đang chặn nội dung.")
        return
        
    print(f"Bypass thành công! Đã tìm thấy {len(job_links)} link công việc.")
    
    # Chỉ lấy 5 bài đầu tiên để test nhanh
    jobs_to_crawl = job_links[:5]
    dataset = []

    for idx, job_url in enumerate(jobs_to_crawl):
        print(f"[{idx+1}/{len(jobs_to_crawl)}] Đang xử lý: {job_url}")
        try:
            time.sleep(2) # Nghỉ để tránh bị phát hiện bot
            job_resp = session.get(job_url, headers=headers, impersonate="chrome120")
            
            if job_resp.status_code != 200: 
                print(f"Lỗi truy cập chi tiết: {job_resp.status_code}")
                continue
            
            # Lưu HTML để test theo yêu cầu
            job_id = extract_job_id(job_url)
            with open(f"{save_dir}/job_{job_id}.html", "w", encoding="utf-8") as f:
                f.write(job_resp.text)
                
            job_soup = BeautifulSoup(job_resp.text, 'html.parser')
            
            # --- CHIẾN THUẬT RÚT TRÍCH MỚI ---
            job_html = job_resp.text
            qg_data = extract_qg_tracking(job_html)
            
            # Khởi tạo giá trị từ qg_tracking (nếu có)
            title = qg_data.get('job_title') if qg_data else None
            company = qg_data.get('recruiter_company') if qg_data else None
            salary_text = qg_data.get('salary_range') if qg_data else "Thỏa thuận"
            location_text = qg_data.get('work_location') if qg_data else "N/A"

            # 1. Fallback Title/Company từ DOM nếu qg_tracking thiếu
            if not title:
                title_tag = job_soup.find('h1')
                title = title_tag.get_text(strip=True) if title_tag else "N/A"
            
            if not company:
                company_tag = job_soup.find(['h2', 'div', 'a', 'p'], class_=re.compile('company-name|name-company-detail|recruiter-name'))
                if company_tag: company = company_tag.get_text(strip=True)
            
            # 2. Fallback Location/Salary từ DOM nếu N/A hoặc Thỏa thuận
            if location_text == "N/A" or salary_text == "Thỏa thuận":
                info_items = job_soup.find_all('div', class_=re.compile('job-detail__info--item|item-job-detail|box-item'))
                for item in info_items:
                    txt = item.get_text().strip()
                    # Kiểm tra label bên trong item
                    label_tag = item.find(['strong', 'span', 'p'], class_=re.compile('label|title'))
                    label = label_tag.get_text().lower() if label_tag else txt.lower()
                    
                    if 'mức lương' in label and salary_text == "Thỏa thuận":
                        # Lấy text sạch (loại bỏ label)
                        val = txt.replace(label_tag.get_text() if label_tag else '', '').strip()
                        if not val: val = item.find(['span', 'p', 'div'], class_='value').get_text(strip=True) if item.find(class_='value') else txt
                        salary_text = val.split('\n')[0].replace(':', '').strip()
                    
                    if ('địa điểm' in label or 'địa chỉ' in label) and (location_text == "N/A" or len(location_text) > 100):
                        val = txt.replace(label_tag.get_text() if label_tag else '', '').strip()
                        if not val: val = item.find(['span', 'p', 'div'], class_='value').get_text(strip=True) if item.find(class_='value') else txt
                        # Làm sạch location
                        loc_val = val.split('\n')[0].replace(':', '').strip()
                        if 5 < len(loc_val) < 150: location_text = loc_val

            # 3. Cấu trúc hóa location
            city = "N/A"
            district = "N/A"
            if location_text != "N/A":
                # Thường có dạng: "Hà Nội, Phường Láng - Hà Nội" hoặc "Hà Nội"
                parts = [p.strip() for p in location_text.split(',')]
                city = parts[0] if parts else "N/A"
                if len(parts) > 1:
                    # Lấy phần đầu của part 2 (ví dụ: "Phường Láng")
                    district = parts[1].split('-')[0].strip()
                elif '-' in location_text:
                    # Fallback cho dạng "Hà Nội - Thanh Xuân"
                    city = location_text.split('-')[0].strip()
                    district = location_text.split('-')[1].strip()

            # Cấu trúc hóa dữ liệu
            salary_data = parse_salary_structured(salary_text)
            location_data = {"full": location_text, "city": city, "district": district}

            # Lấy nội dung chi tiết (Mô tả, Yêu cầu...)
            content_div = job_soup.find('div', class_=re.compile('job-detail__information-detail|job-data'))
            full_text = content_div.get_text("\n", strip=True) if content_div else ""
            
            sections = {
                "job_id": job_id,
                "source_id": build_source_id("topcv", job_id),
                "url": job_url,
                "title": title,
                "company": company,
                "salary": salary_data,
                "location": {
                    "full": location_text,
                    "city": city,
                    "district": district
                },
                "mo_ta_cong_viec": "",
                "yeu_cau_ung_vien": "",
                "quyen_loi": "",
            }

            # Tách section bằng anchors
            anchors = [
                ("Mô tả công việc", "mo_ta_cong_viec"),
                ("Yêu cầu ứng viên", "yeu_cau_ung_vien"),
                ("Quyền lợi", "quyen_loi"),
                ("Cách thức ứng tuyển", None)
            ]
            
            lines = full_text.split('\n')
            current_section = None
            for line in lines:
                clean_line = line.strip()
                found_anchor = False
                for anchor_text, key in anchors:
                    if anchor_text.lower() in clean_line.lower() and len(clean_line) < 50:
                        current_section = key
                        found_anchor = True
                        break
                if not found_anchor and current_section:
                    sections[current_section] += line + " "

            dataset.append(sections)
            print(f"Thành công: {title} ({salary_text})")
            
        except Exception as e:
            print(f"Lỗi khi crawl {job_url}: {e}")

    # Lưu kết quả
    with open("jobs_dataset.json", "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=4)
                
    print(f"\n✅ Hoàn tất! Đã bypass và lấy dữ liệu thành công cho {len(dataset)} jobs.")
    print(f"📂 HTML đã được lưu vào thư mục '{save_dir}/' để bạn kiểm tra.")

if __name__ == "__main__":
    crawl_topcv()
