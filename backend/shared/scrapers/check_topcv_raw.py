import sys
import io
import re
import json
from curl_cffi import requests
from bs4 import BeautifulSoup

url = "https://www.topcv.vn/viec-lam/chuyen-vien-trien-khai-phan-mem-quan-ly-khach-san-oracle-opera-pms-opera-cloud-opera-pms-implementation-consultant-nhan-viec-ngay/2114007.html"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
}

resp = requests.get(url, headers=headers, impersonate="chrome120")

with open("diag_output.txt", "w", encoding="utf-8") as f:
    f.write(f"Status: {resp.status_code}\n")
    match = re.search(r'window\.qgTracking\s*=\s*({.*?});', resp.text, re.DOTALL)
    if match:
        f.write("Found qgTracking!\n")
        loc_match = re.search(r'"work_location"\s*:\s*"(.*?)"', match.group(1))
        if loc_match:
            f.write(f"work_location (Raw): {loc_match.group(1)}\n")
    else:
        f.write("qgTracking NOT found!\n")

    soup = BeautifulSoup(resp.text, 'html.parser')
    sidebar_addr = soup.select_one('.company-address .company-value')
    if sidebar_addr:
        f.write(f"DOM Address: {sidebar_addr.get_text(strip=True)}\n")
