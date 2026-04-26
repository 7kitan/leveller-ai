# TopCV Crawling - Proxy Configuration Guide

## Vấn đề

TopCV sử dụng Cloudflare và yêu cầu CAPTCHA verification cho các IP nước ngoài (Singapore, US, etc.). Điều này khiến scraper không thể hoạt động từ server production.

## Kết quả test

```
[TEST 2] Accessing TopCV homepage...
[OK] Status Code: 200
[FAIL] CAPTCHA DETECTED: Site requires captcha verification

[TEST 3] Accessing specific job posting...
[OK] Status Code: 200
[FAIL] CAPTCHA DETECTED

cf-ray: 9f2255d6bbed2673-HKG (Cloudflare Hong Kong)
```

## Giải pháp đã implement

### 1. Thêm proxy support vào TopCVScraper

File: `backend/shared/scrapers/topcv.py`

```python
class TopCVScraper:
    def __init__(self, proxy: str = None):
        """
        Args:
            proxy: Optional proxy URL 
                   Format: "http://user:pass@proxy.com:8080" 
                   or "socks5://proxy.com:1080"
        """
        self.proxy = proxy
        # ... rest of init
```

### 2. Cập nhật JD service để sử dụng proxy

File: `backend/services/jd_service/main.py`

```python
topcv_proxy = os.getenv("TOPCV_PROXY")
scraper = TopCVScraper(proxy=topcv_proxy)
```

### 3. Thêm config vào .env

File: `backend/.env.example`

```bash
# TopCV Proxy (Recommended for non-Vietnam servers)
TOPCV_PROXY=http://user:pass@proxy.com:8080
```

## Cách sử dụng

### Option 1: Dùng Vietnam Residential Proxy (Khuyến nghị)

1. Đăng ký dịch vụ proxy Việt Nam:
   - [Bright Data](https://brightdata.com/) - Residential proxies
   - [Smartproxy](https://smartproxy.com/) - Vietnam residential IPs
   - [Oxylabs](https://oxylabs.io/) - Vietnam datacenter/residential
   - [Thordata](https://www.thordata.com/) - Mentioned in curl-cffi sponsors

2. Thêm vào `.env`:
```bash
TOPCV_PROXY=http://username:password@proxy.provider.com:8080
```

3. Restart service:
```bash
docker-compose restart jd-service
```

### Option 2: Dùng VPN/VPS Việt Nam

1. Thuê VPS tại Việt Nam (VNG Cloud, Viettel IDC, etc.)
2. Cài đặt Squid proxy hoặc Shadowsocks
3. Point TOPCV_PROXY đến VPS đó

### Option 3: Không dùng proxy (Chỉ cho dev local tại VN)

Nếu bạn đang ở Việt Nam, không cần set TOPCV_PROXY, scraper sẽ hoạt động bình thường.

## Test proxy

Chạy script test để verify proxy hoạt động:

```bash
# Trên server production
cd /app
python test_topcv_access.py
```

Kết quả mong đợi khi dùng proxy VN:
```
[TEST 2] Accessing TopCV homepage...
[OK] Status Code: 200
[OK] Homepage accessible - No obvious blocking

[TEST 3] Accessing specific job posting...
[OK] Status Code: 200
[OK] Job page accessible with content - No blocking detected
```

## Lưu ý

1. **Rotating proxies**: Một số provider cung cấp rotating proxies (IP thay đổi mỗi request), rất tốt để tránh rate limit
2. **Residential vs Datacenter**: Residential proxies (IP thật từ ISP) ít bị block hơn datacenter proxies
3. **Cost**: Residential proxies thường tính phí theo bandwidth (~$5-15/GB)
4. **Compliance**: Đảm bảo tuân thủ Terms of Service của TopCV khi crawl

## Troubleshooting

### Proxy không hoạt động
```bash
# Check proxy connectivity
curl -x http://user:pass@proxy.com:8080 https://ipapi.co/json/

# Should return Vietnam IP
```

### Vẫn bị CAPTCHA
- Thử đổi sang residential proxy
- Thêm delay giữa các requests
- Rotate user agents

### Proxy timeout
- Tăng timeout trong scraper
- Check proxy provider status
- Thử proxy server khác
