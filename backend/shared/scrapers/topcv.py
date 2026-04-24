import re
import time
import logging
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from curl_cffi import requests

logger = logging.getLogger("topcv_scraper")

class TopCVScraper:
    def __init__(self):
        self.base_url = "https://www.topcv.vn"
        self.headers = {
            "authority": "www.topcv.vn",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "accept-language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "referer": "https://www.topcv.vn/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.session = requests.Session()

    def _init_session(self):
        """Khởi tạo JA3 fingerprint qua trang chủ."""
        try:
            self.session.get(self.base_url + "/", headers=self.headers, impersonate="chrome120", timeout=15)
            time.sleep(1)
            return True
        except Exception as e:
            logger.error(f"[TOPCV] Failed to init session: {e}")
            return False

    def get_latest_job_urls(self, search_url: Optional[str] = None, limit: int = 20) -> List[str]:
        """Lấy danh sách link job mới nhất từ trang tìm kiếm."""
        if not search_url:
            # Mặc định Tech sector, sort=new
            search_url = f"{self.base_url}/tim-viec-lam-cong-nghe-thong-tin-cr257?sort=new&type_keyword=1&category_family=r257"

        if not self._init_session():
            return []

        try:
            logger.info(f"[TOPCV] Fetching list from: {search_url}")
            resp = self.session.get(search_url, headers=self.headers, impersonate="chrome120", timeout=20)
            if resp.status_code != 200:
                logger.error(f"[TOPCV] Search page returned {resp.status_code}")
                return []

            soup = BeautifulSoup(resp.text, 'html.parser')
            job_links = []
            # TopCV thường đặt link job trong thẻ a có href chứa /viec-lam/
            for a in soup.find_all('a', href=True):
                href = a['href']
                if '/viec-lam/' in href and 'topcv.vn/viec-lam' in href and href not in job_links:
                    job_links.append(href)
            
            return job_links[:limit]
        except Exception as e:
            logger.error(f"[TOPCV] Error getting job list: {e}")
            return []

    def scrape_job_details(self, job_url: str) -> Optional[Dict[str, Any]]:
        """Cào chi tiết 1 job và trả về dict map với Job model."""
        try:
            logger.info(f"[TOPCV] Scraping job: {job_url}")
            resp = self.session.get(job_url, headers=self.headers, impersonate="chrome120", timeout=15)
            if resp.status_code != 200:
                logger.error(f"[TOPCV] Job detail page returned {resp.status_code}")
                return None

            soup = BeautifulSoup(resp.text, 'html.parser')
            html = resp.text
            
            # Extract tracking data (very accurate for basic info)
            qg_data = self._extract_qg_tracking(html)
            
            title = qg_data.get('job_title') if qg_data else None
            company = qg_data.get('recruiter_company') if qg_data else None
            salary_text = qg_data.get('salary_range') if qg_data else "Thỏa thuận"
            location_text = qg_data.get('work_location') if qg_data else "N/A"

            # Fallbacks
            if not title:
                title_tag = soup.find('h1')
                title = title_tag.get_text(strip=True) if title_tag else "N/A"
            
            if not company:
                company_tag = soup.find(['h2', 'div', 'a', 'p'], class_=re.compile('company-name|name-company-detail|recruiter-name'))
                company = company_tag.get_text(strip=True) if company_tag else "N/A"

            # Detailed content extraction
            content_div = soup.find('div', class_=re.compile('job-detail__information-detail|job-data'))
            raw_text = content_div.get_text("\n", strip=True) if content_div else ""
            
            # Parse structured sections
            sections = self._parse_job_sections(raw_text)
            
            # Extract Job ID
            job_id_match = re.search(r'/(\d+)\.html', job_url)
            external_id = job_id_match.group(1) if job_id_match else str(time.time())

            # Salary normalization
            salary_data = self._parse_salary(salary_text)
            
            # Location normalization
            location_data = self._parse_location(location_text)

            return {
                "source_id": f"TOPCV_{external_id}",
                "title_raw": title,
                "company_name": company,
                "source_url": job_url,
                "source_label": "topcv",
                "raw_text": raw_text,
                "job_description": sections.get("job_description", ""),
                "requirements": sections.get("requirements", ""),
                "benefits": sections.get("benefits", ""),
                "min_salary_vnd": salary_data["min"],
                "max_salary_vnd": salary_data["max"],
                "location_raw": location_text,
                "location_normalized": location_data["city"],
                "location_district": location_data["district"],
                "status": "active"
            }
        except Exception as e:
            logger.error(f"[TOPCV] Error scraping job {job_url}: {e}")
            return None

    def _extract_qg_tracking(self, html: str) -> Dict[str, str]:
        try:
            match = re.search(r'window\.qgTracking\s*=\s*({.*?});', html, re.DOTALL)
            if match:
                json_str = match.group(1)
                data = {}
                for key in ['job_title', 'recruiter_company', 'experience', 'work_location', 'salary_range']:
                    # Use regex instead of json.loads because it's a JS object, not pure JSON
                    key_match = re.search(f'"{key}"\s*:\s*"(.*?)"', json_str)
                    if key_match:
                        try:
                            val = key_match.group(1).encode('utf-8').decode('unicode_escape')
                            data[key] = val
                        except:
                            data[key] = key_match.group(1)
                return data
        except: pass
        return {}

    def _parse_salary(self, text: str) -> Dict[str, int]:
        clean_text = text.replace('.', '').replace(',', '')
        numbers = re.findall(r'\d+', clean_text)
        res = {"min": 0, "max": 0}
        
        multiplier = 1000000 if "triệu" in text.lower() else (1000 if "nghìn" in text.lower() or "k" in text.lower() else 1)
        
        if len(numbers) >= 2:
            res["min"] = int(numbers[0]) * multiplier
            res["max"] = int(numbers[1]) * multiplier
        elif len(numbers) == 1:
            if any(x in text.lower() for x in ["tới", "đến", "lên đến"]):
                res["max"] = int(numbers[0]) * multiplier
            else:
                res["min"] = int(numbers[0]) * multiplier
        
        # Currency check (USD to VND approximation if needed, but TopCV usually VND)
        if "usd" in text.lower() or "$" in text.lower():
            res["min"] *= 25000
            res["max"] *= 25000
            
        return res

    def _parse_location(self, text: str) -> Dict[str, str]:
        parts = [p.strip() for p in text.split(',')]
        city = parts[0] if parts else "N/A"
        district = "N/A"
        if len(parts) > 1:
            district = parts[1].split('-')[0].strip()
        elif '-' in text:
            city = text.split('-')[0].strip()
            district = text.split('-')[1].strip()
            
        # Clean up common cities
        if "Hà Nội" in city: city = "Hà Nội"
        if "Hồ Chí Minh" in city or "TP.HCM" in city: city = "Hồ Chí Minh"
        if "Đà Nẵng" in city: city = "Đà Nẵng"
        
        return {"city": city, "district": district}

    def _parse_job_sections(self, full_text: str) -> Dict[str, str]:
        """Parse job posting into structured sections."""
        sections = {
            "job_description": "",
            "requirements": "",
            "benefits": "",
        }
        
        # Section anchors (Vietnamese)
        anchors = [
            ("Mô tả công việc", "job_description"),
            ("Yêu cầu ứng viên", "requirements"),
            ("Quyền lợi", "benefits"),
            ("Cách thức ứng tuyển", None),  # Stop parsing here
        ]
        
        lines = full_text.split('\n')
        current_section = None
        
        for line in lines:
            clean_line = line.strip()
            found_anchor = False
            
            # Check if this line is a section header
            for anchor_text, key in anchors:
                if anchor_text.lower() in clean_line.lower() and len(clean_line) < 50:
                    current_section = key
                    found_anchor = True
                    break
            
            # Add content to current section
            if not found_anchor and current_section and clean_line:
                sections[current_section] += line + "\n"
        
        # Clean up sections
        for key in sections:
            sections[key] = sections[key].strip()
        
        return sections
