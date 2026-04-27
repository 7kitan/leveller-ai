import re
import time
import logging
import os
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from curl_cffi import requests
import json
from datetime import datetime
import random

# Setup detailed file logging
logger = logging.getLogger("topcv_scraper")
logger.setLevel(logging.DEBUG)

# Create logs directory if not exists
# Use data/logs to ensure it's within a persistent volume and avoid root-level conflicts
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
log_dir = os.path.join(backend_dir, "data", "logs")

try:
    if os.path.exists(log_dir) and not os.path.isdir(log_dir):
        os.remove(log_dir)
    os.makedirs(log_dir, exist_ok=True)
except Exception as e:
    # Fallback to a temporary directory if data/logs is inaccessible
    import tempfile
    log_dir = os.path.join(tempfile.gettempdir(), "career_advisor_logs")
    os.makedirs(log_dir, exist_ok=True)

# File handler with detailed format
log_file = os.path.join(log_dir, f"topcv_crawler_{datetime.now().strftime('%Y%m%d')}.log")
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

logger.info(f"=" * 80)
logger.info(f"TopCV Scraper initialized. Logging to: {log_file}")
logger.info(f"=" * 80)


class ProxyRotator:
    """Manages proxy rotation with automatic failover."""
    
    def __init__(self, proxy_list: List[str]):
        """
        Initialize proxy rotator.
        
        Args:
            proxy_list: List of proxies in format "IP:PORT:USER:PASS"
        """
        self.proxies = []
        self.current_index = 0
        self.failed_proxies = set()
        
        for proxy_str in proxy_list:
            if proxy_str and proxy_str.strip():
                try:
                    parts = proxy_str.strip().split(':')
                    if len(parts) == 4:
                        ip, port, user, password = parts
                        proxy_url = f"http://{user}:{password}@{ip}:{port}"
                        self.proxies.append({
                            'url': proxy_url,
                            'raw': proxy_str,
                            'ip': ip,
                            'port': port
                        })
                    elif len(parts) == 2:
                        # Support simple IP:PORT format without auth
                        ip, port = parts
                        proxy_url = f"http://{ip}:{port}"
                        self.proxies.append({
                            'url': proxy_url,
                            'raw': proxy_str,
                            'ip': ip,
                            'port': port
                        })
                except Exception as e:
                    # Sanitize proxy_str to avoid logging credentials
                    safe_proxy = proxy_str.split(':')[:2]  # Only log IP:PORT
                    safe_proxy_str = ':'.join(safe_proxy) if len(safe_proxy) >= 2 else '[invalid]'
                    logger.warning(f"[PROXY] Invalid proxy format: {safe_proxy_str} - {e}")
        
        if self.proxies:
            logger.info(f"[PROXY] Initialized with {len(self.proxies)} proxies")
            # Shuffle to distribute load
            random.shuffle(self.proxies)
        else:
            logger.warning(f"[PROXY] No valid proxies loaded")
    
    def get_next_proxy(self) -> Optional[str]:
        """Get next available proxy URL."""
        if not self.proxies:
            return None
        
        # Try to find a non-failed proxy
        attempts = 0
        while attempts < len(self.proxies):
            proxy = self.proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxies)
            
            if proxy['raw'] not in self.failed_proxies:
                logger.debug(f"[PROXY] Using proxy: {proxy['ip']}:{proxy['port']}")
                return proxy['url']
            
            attempts += 1
        
        # All proxies failed, reset failed list and try again
        logger.warning(f"[PROXY] All proxies failed, resetting failure list")
        self.failed_proxies.clear()
        
        if self.proxies:
            proxy = self.proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxies)
            return proxy['url']
        
        return None
    
    def mark_failed(self, proxy_url: str):
        """Mark a proxy as failed."""
        for proxy in self.proxies:
            if proxy['url'] == proxy_url:
                self.failed_proxies.add(proxy['raw'])
                logger.warning(f"[PROXY] Marked as failed: {proxy['ip']}:{proxy['port']}")
                break
    
    def get_proxy_count(self) -> int:
        """Get total number of proxies."""
        return len(self.proxies)
    
    def get_available_count(self) -> int:
        """Get number of available (non-failed) proxies."""
        return len(self.proxies) - len(self.failed_proxies)


class TopCVScraper:
    def __init__(self, proxy_list: List[str] = None):
        """
        Initialize TopCV scraper with proxy rotation support.
        
        Args:
            proxy_list: List of proxies in format "IP:PORT:USER:PASS" or ["IP:PORT:USER:PASS", ...]
        """
        self.base_url = "https://www.topcv.vn"
        self.headers = {
            "authority": "www.topcv.vn",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "accept-language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "referer": "https://www.topcv.vn/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.session = requests.Session()
        
        # Initialize proxy rotator
        if proxy_list:
            self.proxy_rotator = ProxyRotator(proxy_list)
            logger.info(f"[TOPCV] Proxy rotation enabled with {self.proxy_rotator.get_proxy_count()} proxies")
        else:
            self.proxy_rotator = None
            logger.info(f"[TOPCV] No proxy configured, using direct connection")

    def _init_session(self):
        """Khởi tạo JA3 fingerprint qua trang chủ."""
        try:
            proxy_url = self.proxy_rotator.get_next_proxy() if self.proxy_rotator else None
            proxies = {"https": proxy_url, "http": proxy_url} if proxy_url else None
            
            self.session.get(
                self.base_url + "/", 
                headers=self.headers, 
                impersonate="chrome120", 
                timeout=15,
                proxies=proxies
            )
            time.sleep(1)
            return True
        except Exception as e:
            logger.error(f"[TOPCV] Failed to init session: {e}")
            # Mark proxy as failed if we're using one
            if proxy_url and self.proxy_rotator:
                self.proxy_rotator.mark_failed(proxy_url)
            return False

    def get_latest_job_urls(self, search_url: Optional[str] = None, limit: int = 20) -> List[str]:
        """Lấy danh sách link job mới nhất từ trang tìm kiếm."""
        if not search_url:
            # Mặc định Tech sector, sort=new
            search_url = f"{self.base_url}/tim-viec-lam-cong-nghe-thong-tin-cr257?sort=new&type_keyword=1&category_family=r257"

        logger.info(f"\n{'='*80}")
        logger.info(f"[GET_URLS] Starting job URL collection")
        logger.info(f"[GET_URLS] Search URL: {search_url}")
        logger.info(f"[GET_URLS] Limit: {limit}")

        if not self._init_session():
            logger.error(f"[GET_URLS] Session initialization failed")
            return []

        # Retry with different proxies
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = attempt * 2
                    logger.info(f"[GET_URLS] Retry attempt {attempt}/{max_retries - 1} after {wait_time}s...")
                    time.sleep(wait_time)
                
                logger.info(f"[GET_URLS] Fetching search page (attempt {attempt + 1})...")
                proxy_url = self.proxy_rotator.get_next_proxy() if self.proxy_rotator else None
                proxies = {"https": proxy_url, "http": proxy_url} if proxy_url else None
                
                resp = self.session.get(
                    search_url, 
                    headers=self.headers, 
                    impersonate="chrome120", 
                    timeout=20,
                    proxies=proxies
                )
                logger.info(f"[GET_URLS] Response status: {resp.status_code}")
                logger.info(f"[GET_URLS] Response length: {len(resp.text)} chars")
                
                if resp.status_code != 200:
                    logger.error(f"[GET_URLS] Search page returned {resp.status_code}")
                    if proxy_url and self.proxy_rotator:
                        self.proxy_rotator.mark_failed(proxy_url)
                    continue

                soup = BeautifulSoup(resp.text, 'html.parser')
                job_links = []
                all_links = []
                
                # TopCV thường đặt link job trong thẻ a có href chứa /viec-lam/
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    all_links.append(href)
                    if '/viec-lam/' in href and 'topcv.vn/viec-lam' in href:
                        # Clean URL: Truncate at .html
                        clean_href = href.split('.html')[0] + '.html' if '.html' in href else href
                        if clean_href not in job_links:
                            job_links.append(clean_href)
                            logger.debug(f"[GET_URLS] Found job link: {clean_href}")
                
                logger.info(f"[GET_URLS] Total links found: {len(all_links)}")
                logger.info(f"[GET_URLS] Job links found: {len(job_links)}")
                logger.info(f"[GET_URLS] Returning top {min(limit, len(job_links))} links")
                
                # Log sample of non-job links for debugging
                non_job_links = [l for l in all_links[:20] if '/viec-lam/' not in l]
                logger.debug(f"[GET_URLS] Sample non-job links: {non_job_links[:5]}")
                
                return job_links[:limit]
                
            except Exception as e:
                logger.error(f"[GET_URLS] Error getting job list (attempt {attempt + 1}): {e}", exc_info=True)
                if proxy_url and self.proxy_rotator:
                    self.proxy_rotator.mark_failed(proxy_url)
                if attempt < max_retries - 1:
                    continue
        
        logger.error(f"[GET_URLS] All {max_retries} attempts failed")
        return []

    def scrape_job_details(self, job_url: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """
        Cào chi tiết 1 job và trả về dict map với Job model.
        
        Args:
            job_url: URL of the job posting
            max_retries: Number of retry attempts if request fails (default 3 for proxy rotation)
        """
        proxy_url = None
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    wait_time = attempt * 2  # Exponential backoff: 2s, 4s, 6s
                    logger.info(f"[SCRAPE_JOB] Retry attempt {attempt}/{max_retries} after {wait_time}s...")
                    time.sleep(wait_time)
                
                logger.info(f"\n{'='*80}")
                logger.info(f"[SCRAPE_JOB] Starting job detail scrape (attempt {attempt + 1}/{max_retries + 1})")
                logger.info(f"[SCRAPE_JOB] URL: {job_url}")
                
                # Get next proxy for this attempt
                proxy_url = self.proxy_rotator.get_next_proxy() if self.proxy_rotator else None
                proxies = {"https": proxy_url, "http": proxy_url} if proxy_url else None
                
                if proxy_url:
                    logger.info(f"[SCRAPE_JOB] Using proxy for attempt {attempt + 1}")
                
                resp = self.session.get(
                    job_url, 
                    headers=self.headers, 
                    impersonate="chrome120", 
                    timeout=20,
                    proxies=proxies
                )
                logger.info(f"[SCRAPE_JOB] Response status: {resp.status_code}")
                logger.info(f"[SCRAPE_JOB] Response length: {len(resp.text)} chars")
                
                if resp.status_code != 200:
                    logger.error(f"[SCRAPE_JOB] Job detail page returned {resp.status_code}")
                    if proxy_url and self.proxy_rotator:
                        self.proxy_rotator.mark_failed(proxy_url)
                    if attempt < max_retries:
                        continue  # Retry with different proxy
                    return None

                # Clean URL: Remove tracking parameters after .html
                if '.html' in job_url:
                    job_url = job_url.split('.html')[0] + '.html'

                # Extract Job ID for logging and result
                job_id_match = re.search(r'/(\d+)\.html', job_url)
                job_id = job_id_match.group(1) if job_id_match else str(int(time.time()))


                soup = BeautifulSoup(resp.text, 'html.parser')
                html = resp.text
                
                # Extract tracking data (very accurate for basic info)
                logger.info(f"[SCRAPE_JOB] Extracting qg_tracking data...")
                qg_data = self._extract_qg_tracking(html)
                logger.info(f"[SCRAPE_JOB] qg_tracking data: {qg_data}")
                
                title = qg_data.get('job_title') if qg_data else None
                company = qg_data.get('recruiter_company') if qg_data else None
                salary_text = qg_data.get('salary_range') if qg_data else "Thỏa thuận"
                location_text = qg_data.get('work_location') if qg_data else "N/A"

                # NEW: Robust DOM-based location extraction (often more specific than tracking data)
                dom_location = self._extract_location_from_soup(soup)
                if dom_location and len(dom_location) > 5:
                    # If tracking location is very long (likely a list of all wards), 
                    # or if DOM location is more specific, prefer DOM.
                    if len(location_text) > 200 or location_text == "N/A":
                         logger.info(f"[SCRAPE_JOB] Preferring DOM location: {dom_location} over {location_text[:50]}...")
                         location_text = dom_location
                    elif "Quận" in dom_location or "Huyện" in dom_location:
                         # Specific address in sidebar is usually better than city-level in tracking
                         logger.info(f"[SCRAPE_JOB] Found specific DOM address: {dom_location}")
                         location_text = dom_location

                logger.info(f"[SCRAPE_JOB] Initial extraction - Title: {title}, Company: {company}")
                logger.info(f"[SCRAPE_JOB] Initial extraction - Salary: {salary_text}, Location: {location_text}")

                # Fallbacks
                if not title:
                    title_tag = soup.find('h1')
                    title = title_tag.get_text(strip=True) if title_tag else "N/A"
                    logger.info(f"[SCRAPE_JOB] Fallback title from h1: {title}")
                
                if not company:
                    company_tag = soup.find(['h2', 'div', 'a', 'p'], class_=re.compile('company-name|name-company-detail|recruiter-name'))
                    company = company_tag.get_text(strip=True) if company_tag else "N/A"
                    logger.info(f"[SCRAPE_JOB] Fallback company: {company}")

                # Detailed content extraction - use proper job-description div
                logger.info(f"[SCRAPE_JOB] Looking for job-description div...")
                job_desc_div = soup.find('div', class_='job-description')
                
                if job_desc_div:
                    logger.info(f"[SCRAPE_JOB] Found job-description div")
                    # Extract structured sections directly from HTML
                    sections = self._parse_job_sections_from_html(job_desc_div)
                    
                    # Also get raw text for fallback
                    raw_text = job_desc_div.get_text("\n", strip=True)
                    logger.info(f"[SCRAPE_JOB] Extracted {len(raw_text)} chars of raw text")
                else:
                    logger.warning(f"[SCRAPE_JOB] No job-description div found! Trying fallback...")
                    # Fallback to old method
                    content_div = soup.find('div', class_=re.compile('job-detail__information-detail|job-data'))
                    if content_div:
                        raw_text = content_div.get_text("\n", strip=True)
                        sections = self._parse_job_sections_from_text(raw_text)
                        logger.info(f"[SCRAPE_JOB] Used fallback method, extracted {len(raw_text)} chars")
                    else:
                        raw_text = ""
                        sections = {"job_description": "", "requirements": "", "benefits": "", "working_hours": ""}
                        logger.error(f"[SCRAPE_JOB] Could not find any job content!")
                
                logger.info(f"[SCRAPE_JOB] Parsing complete")
                logger.info(f"[SCRAPE_JOB] Parsed sections:")
                logger.info(f"  - job_description: {len(sections.get('job_description', ''))} chars")
                logger.info(f"  - requirements: {len(sections.get('requirements', ''))} chars")
                logger.info(f"  - benefits: {len(sections.get('benefits', ''))} chars")
                
                # Log section previews
                for section_name, content in sections.items():
                    if content and section_name != 'working_hours':
                        logger.debug(f"[SCRAPE_JOB] {section_name} preview:\n{content[:200]}...")
                
                # Extract Job ID
                external_id = job_id

                # Salary normalization
                logger.info(f"[SCRAPE_JOB] Parsing salary: {salary_text}")
                salary_data = self._parse_salary(salary_text)
                logger.info(f"[SCRAPE_JOB] Parsed salary: min={salary_data['min']}, max={salary_data['max']}")
                
                # Location normalization
                logger.info(f"[SCRAPE_JOB] Parsing location: {location_text}")
                location_data = self._parse_location(location_text)
                logger.info(f"[SCRAPE_JOB] Parsed location: city={location_data['city']}, district={location_data['district']}")
                
                # Extract employment type from "Thông tin chung" section
                logger.info(f"[SCRAPE_JOB] Extracting employment type...")
                employment_type = self._extract_employment_type(soup)
                logger.info(f"[SCRAPE_JOB] Employment type: {employment_type}")

                result = {
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
                    "employment_type": employment_type,
                    "status": "active"
                }
                
                logger.info(f"[SCRAPE_JOB] ✓ Successfully scraped job: {title}")
                logger.info(f"[SCRAPE_JOB] Final data summary:")
                logger.info(f"  - source_id: {result['source_id']}")
                logger.info(f"  - title: {result['title_raw']}")
                logger.info(f"  - company: {result['company_name']}")
                logger.info(f"  - employment_type: {result['employment_type']}")
                logger.info(f"  - raw_text length: {len(result['raw_text'])}")
                logger.info(f"  - job_description length: {len(result['job_description'])}")
                logger.info(f"  - requirements length: {len(result['requirements'])}")
                logger.info(f"  - benefits length: {len(result['benefits'])}")
                
                return result
                
            except Exception as e:
                logger.error(f"[SCRAPE_JOB] ❌ Error scraping job {job_url}: {e}", exc_info=True)
                # Mark proxy as failed if we're using one
                if proxy_url and self.proxy_rotator:
                    self.proxy_rotator.mark_failed(proxy_url)
                if attempt < max_retries:
                    logger.info(f"[SCRAPE_JOB] Will retry with different proxy...")
                    continue
                return None
        
        # If we get here, all retries failed
        logger.error(f"[SCRAPE_JOB] All {max_retries + 1} attempts failed for {job_url}")
        return None


    def _extract_qg_tracking(self, html: str) -> Dict[str, str]:
        try:
            match = re.search(r'window\.qgTracking\s*=\s*({.*?});', html, re.DOTALL)
            if match:
                json_str = match.group(1)
                data = {}
                for key in ['job_title', 'recruiter_company', 'experience', 'work_location', 'salary_range']:
                    # Use regex instead of json.loads because it's a JS object, not pure JSON
                    # Use regex that handles escaped quotes: "(?:[^"\\]|\\.)*"
                    # We capture the entire quoted string to use json.loads on it
                    key_match = re.search(fr'"{key}"\s*:\s*("(?:[^"\\]|\\.)*")', json_str)
                    if key_match:
                        try:
                            # json.loads correctly handles \/, \uXXXX, \", etc.
                            val = json.loads(key_match.group(1))
                            data[key] = val
                        except Exception as e:
                            # Fallback if the JS string is not valid JSON
                            logger.debug(f"[TOPCV] json.loads failed for {key}: {e}")
                            # Try to extract content between quotes and do simple unescape
                            simple_match = re.search(f'"{key}"\s*:\s*"(.*?)"', json_str)
                            if simple_match:
                                data[key] = simple_match.group(1).replace('\\/', '/')
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
        """
        Phân tích địa chỉ tiếng Việt để lấy City và District.
        Chiến thuật: Tìm City trước (quét từ cuối lên), sau đó tìm District ở các phần còn lại bên trái.
        """
        if not text or text == "N/A":
            return {"city": "N/A", "district": "N/A"}

        # Tách chuỗi bằng nhiều loại dấu phân cách: , - \n ; :
        parts = [p.strip() for p in re.split(r'[,|\n|\r|;]|\s-\s', text) if p.strip()]
        if not parts:
            return {"city": "N/A", "district": "N/A"}
        
        city = "N/A"
        district = "N/A"
        
        cities_map = {
            "Hồ Chí Minh": ["HỒ CHÍ MINH", "TP.HCM", "TP. HCM", "HCM", "SÀI GÒN", "SAI GON", "HCMC"],
            "Hà Nội": ["HÀ NỘI", "HA NOI", "HN"],
            "Đà Nẵng": ["ĐÀ NẴNG", "DA NANG"],
            "Bình Dương": ["BÌNH DƯƠNG", "BINH DUONG"],
            "Đồng Nai": ["ĐỒNG NAI", "DONG NAI"],
            "Long An": ["LONG AN"],
            "Cần Thơ": ["CẦN THƠ", "CAN THO"],
            "Bắc Ninh": ["BẮC NINH", "BAC NINH"],
            "Hải Phòng": ["HẢI PHÒNG", "HAI PHONG"]
        }

        city_index = -1
        # 1. Tìm City (Quét từ cuối lên)
        for i in range(len(parts) - 1, -1, -1):
            p_upper = parts[i].upper()
            found = False
            for standard_city, variants in cities_map.items():
                if any(v in p_upper for v in variants):
                    city = standard_city
                    city_index = i
                    found = True
                    break
            if found: break
        
        if city == "N/A":
            # Nếu không mapping được, lấy phần tử cuối cùng làm City giả định
            city = parts[-1]
            city_index = len(parts) - 1

        # 2. Tìm District (Quét từ phần tử bên trái City trở về trước)
        for i in range(city_index - 1, -1, -1):
            p = parts[i]
            p_upper = p.upper()
            # Nếu chứa từ khóa chỉ quận huyện
            if any(kw in p_upper for kw in ["QUẬN", "HUYỆN", "THỊ XÃ", "THÀNH PHỐ", "Q.", "H.", "DISTRICT"]):
                # Kiểm tra để không lấy nhầm phần City (nếu City được lặp lại ở District)
                is_city_alias = False
                for variants in cities_map.values():
                    if p_upper in [v.upper() for v in variants]:
                        is_city_alias = True
                        break
                
                if not is_city_alias:
                    district = p
                    break
        
        # 3. Fallback cho District: Nếu vẫn N/A và có phần tử bên trái City, lấy phần tử đó
        if district == "N/A" and city_index > 0:
            maybe_district = parts[city_index - 1]
            # Đảm bảo không phải là tên thành phố lặp lại
            is_city_alias = False
            for variants in cities_map.values():
                if maybe_district.upper() in [v.upper() for v in variants]:
                    is_city_alias = True
                    break
            if not is_city_alias:
                district = maybe_district

        return {"city": city, "district": district}

    def _extract_location_from_soup(self, soup) -> Optional[str]:
        """Trích xuất địa điểm từ DOM để tránh lỗi qgTracking chứa list phường."""
        try:
            # 1. Company address in sidebar (most specific)
            sidebar_addr = soup.select_one('.company-address .company-value')
            if sidebar_addr:
                addr = sidebar_addr.get_text(strip=True)
                if addr: return addr

            # 2. General location header
            gen_loc = soup.select_one('.section-location .job-detail__info--section-content-value')
            if gen_loc:
                addr = gen_loc.get_text(strip=True)
                if addr: return addr

            # 3. Old template addresses
            box_addr = soup.select_one('.box-address .item-address')
            if box_addr:
                addr = box_addr.get_text(strip=True)
                if addr: return addr
            
            # 4. Search in specific labels
            for div in soup.find_all('div', class_='job-detail__info--section'):
                title = div.find('div', class_='job-detail__info--section-content-title')
                if title and 'địa điểm' in title.get_text().lower():
                    value = div.find('div', class_='job-detail__info--section-content-value')
                    if value: return value.get_text(strip=True)

            return None
        except:
            return None

    def _extract_employment_type(self, soup) -> str:
        """
        Extract employment type from "Thông tin chung" section.
        Looks for "Hình thức làm việc" field.
        """
        try:
            # Find all box-general-group divs
            general_groups = soup.find_all('div', class_='box-general-group')
            
            for group in general_groups:
                title_div = group.find('div', class_='box-general-group-info-title')
                if title_div and 'hình thức làm việc' in title_div.get_text(strip=True).lower():
                    value_div = group.find('div', class_='box-general-group-info-value')
                    if value_div:
                        raw_value = value_div.get_text(strip=True)
                        # Normalize employment type
                        return self._normalize_employment_type(raw_value)
            
            return None
        except Exception as e:
            logger.warning(f"[SCRAPE_JOB] Error extracting employment type: {e}")
            return None
    
    def _normalize_employment_type(self, raw_text: str) -> str:
        """Normalize Vietnamese employment type to standard format."""
        text_lower = raw_text.lower()
        
        if 'toàn thời gian' in text_lower or 'full time' in text_lower:
            return 'Full-time'
        elif 'bán thời gian' in text_lower or 'part time' in text_lower:
            return 'Part-time'
        elif 'thực tập' in text_lower or 'intern' in text_lower:
            return 'Internship'
        elif 'hợp đồng' in text_lower or 'contract' in text_lower:
            return 'Contract'
        elif 'freelance' in text_lower or 'tự do' in text_lower:
            return 'Freelance'
        else:
            # Return original if no match
            return raw_text

    def _parse_job_sections_from_html(self, job_desc_div) -> Dict[str, str]:
        """Parse job sections directly from HTML structure (more accurate)."""
        logger.info(f"[PARSE_HTML] Starting HTML-based section parsing")
        
        sections = {
            "job_description": "",
            "requirements": "",
            "benefits": "",
            "working_hours": "",  # New field for working hours
        }
        
        # Find all job-description__item divs
        items = job_desc_div.find_all('div', class_='job-description__item')
        logger.info(f"[PARSE_HTML] Found {len(items)} job-description__item divs")
        
        for i, item in enumerate(items):
            # Get the header (h3 tag)
            header = item.find('h3')
            if not header:
                logger.debug(f"[PARSE_HTML] Item {i}: No h3 header found, skipping")
                continue
            
            header_text = header.get_text(strip=True).lower()
            logger.debug(f"[PARSE_HTML] Item {i}: Header = '{header_text}'")
            
            # Get the content div
            content_div = item.find('div', class_='job-description__item--content')
            if not content_div:
                logger.debug(f"[PARSE_HTML] Item {i}: No content div found, skipping")
                continue
            
            # Extract clean text from content
            content_text = content_div.get_text("\n", strip=True)
            
            # Map header to section key
            if 'mô tả công việc' in header_text or 'job description' in header_text:
                sections['job_description'] = content_text
                logger.info(f"[PARSE_HTML] Mapped to job_description: {len(content_text)} chars")
            elif 'yêu cầu' in header_text or 'requirement' in header_text:
                sections['requirements'] = content_text
                logger.info(f"[PARSE_HTML] Mapped to requirements: {len(content_text)} chars")
            elif 'quyền lợi' in header_text or 'benefit' in header_text:
                sections['benefits'] = content_text
                logger.info(f"[PARSE_HTML] Mapped to benefits: {len(content_text)} chars")
            elif 'thời gian làm việc' in header_text or 'working hours' in header_text:
                sections['working_hours'] = content_text
                logger.info(f"[PARSE_HTML] Mapped to working_hours: {len(content_text)} chars")
            else:
                logger.debug(f"[PARSE_HTML] Item {i}: Unknown header '{header_text}', skipping")
        
        logger.info(f"[PARSE_HTML] HTML parsing complete:")
        logger.info(f"  - job_description: {len(sections['job_description'])} chars")
        logger.info(f"  - requirements: {len(sections['requirements'])} chars")
        logger.info(f"  - benefits: {len(sections['benefits'])} chars")
        logger.info(f"  - working_hours: {len(sections['working_hours'])} chars")
        
        return sections

    def _parse_job_sections_from_text(self, full_text: str) -> Dict[str, str]:
        """Parse job posting into structured sections from plain text (fallback method)."""
        logger.info(f"[PARSE_TEXT] Starting text-based section parsing")
        logger.info(f"[PARSE_TEXT] Input text length: {len(full_text)} chars")
        
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
        logger.info(f"[PARSE_TEXT] Split into {len(lines)} lines")
        
        current_section = None
        section_line_counts = {key: 0 for key in ["job_description", "requirements", "benefits"]}
        
        for i, line in enumerate(lines):
            clean_line = line.strip()
            found_anchor = False
            
            # Check if this line is a section header
            for anchor_text, key in anchors:
                if anchor_text.lower() in clean_line.lower() and len(clean_line) < 50:
                    current_section = key
                    found_anchor = True
                    logger.info(f"[PARSE_TEXT] Line {i}: Found section header '{anchor_text}' -> {key}")
                    logger.debug(f"[PARSE_TEXT] Header line content: '{clean_line}'")
                    break
            
            # Add content to current section
            if not found_anchor and current_section and clean_line:
                sections[current_section] += line + "\n"
                section_line_counts[current_section] += 1
        
        # Clean up sections
        for key in sections:
            sections[key] = sections[key].strip()
        
        logger.info(f"[PARSE_TEXT] Parsing complete:")
        logger.info(f"  - job_description: {section_line_counts['job_description']} lines, {len(sections['job_description'])} chars")
        logger.info(f"  - requirements: {section_line_counts['requirements']} lines, {len(sections['requirements'])} chars")
        logger.info(f"  - benefits: {section_line_counts['benefits']} lines, {len(sections['benefits'])} chars")
        
        # Log first few lines of full_text to see what we're working with
        logger.debug(f"[PARSE_TEXT] First 10 lines of input:")
        for i, line in enumerate(lines[:10]):
            logger.debug(f"  Line {i}: '{line.strip()}'")
        
        return sections
