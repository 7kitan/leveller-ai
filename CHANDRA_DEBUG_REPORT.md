# Chandra OCR Debug Report

## 🔍 Phân Tích Vấn Đề

### 1. ✅ Settings Database & Redis Cache - HOÀN TOÀN OK

**Database (system_settings table):**
```sql
chandra_api_url | "https://milwaukee-voted-employer-annually.trycloudflare.com/tasks/ocr"
chandra_api_key | "6b30dc8ce23ff60ebe56bb723e0ae3fb7d70c9f025c48f519ba4e2161174c22d"
Updated: 2026-04-25 18:01:12
```

**Redis Cache (DB 0):**
```
advisor:chandra_api_url → "https://milwaukee-voted-employer-annually.trycloudflare.com/tasks/ocr"
advisor:chandra_api_key → "6b30dc8ce23ff60ebe56bb723e0ae3fb7d70c9f025c48f519ba4e2161174c22d"
```

**Worker Environment:**
```bash
CV_PARSER_STRATEGY=chandra
CHANDRA_API_URL=https://milwaukee-voted-employer-annually.trycloudflare.com/tasks/ocr
CHANDRA_API_KEY=6b30dc8ce23ff60ebe56bb723e0ae3fb7d70c9f025c48f519ba4e2161174c22d
```

**Config Manager Test:**
```python
# Từ worker container
config_manager.get_setting('chandra_api_url')
# → 'https://milwaukee-voted-employer-annually.trycloudflare.com/tasks/ocr'

config_manager.get_setting('chandra_api_key')
# → '6b30dc8ce23ff60ebe56bb723e0ae3fb7d70c9f025c48f519ba4e2161174c22d'
```

**✅ Kết luận:** Settings hoạt động HOÀN HẢO. Admin update settings → lưu vào DB → cache vào Redis → worker đọc được.

---

### 2. ❌ Chandra OCR Service - KHÔNG CHẠY

**Vấn đề chính:**
```bash
# Test connection từ gateway container
curl https://milwaukee-voted-employer-annually.trycloudflare.com/tasks/ocr
# → HTTP 000 (Connection failed)
```

**Nguyên nhân:**
- Chandra OCR service (`ai_inference_hub/`) KHÔNG được start
- Cloudflare tunnel URL đang trỏ đến service không tồn tại
- Backend đã config đúng, nhưng service endpoint không available

**Kiểm tra:**
```bash
# Không có container Chandra đang chạy
docker ps | grep chandra
# → (empty)

# Không có Python process nào chạy ai_inference_hub
Get-Process | grep python
# → (không có uvicorn/fastapi process)
```

---

## 🔧 Giải Pháp

### Option 1: Chạy Chandra Service Locally (Recommended cho Dev)

**Yêu cầu:**
- Python 3.10+
- 8GB RAM minimum (16GB recommended)
- GPU optional (CPU mode sẽ chậm hơn)

**Các bước:**

1. **Setup Python Environment**
```bash
cd C:\Users\bach\Documents\Project\Team078\ai_inference_hub

# Tạo virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements_ai.txt
```

2. **Configure Environment**
```bash
# File .env đã có sẵn:
AI_INFERENCE_API_KEY=6b30dc8ce23ff60ebe56bb723e0ae3fb7d70c9f025c48f519ba4e2161174c22d
PORT=8080
CHANDRA_MODEL_PATH=datalab-to/chandra-ocr-2
```

3. **Start Service**
```bash
# Chạy service
uvicorn main:app --host 0.0.0.0 --port 8080

# Hoặc dùng Python trực tiếp
python -m uvicorn main:app --host 0.0.0.0 --port 8080
```

4. **Expose via Cloudflare Tunnel**
```bash
# Install cloudflared (nếu chưa có)
# Download từ: https://github.com/cloudflare/cloudflared/releases

# Start tunnel
cloudflared tunnel --url http://localhost:8080
# → Sẽ tạo URL dạng: https://xxx-yyy-zzz.trycloudflare.com
```

5. **Update Backend Settings**
```bash
# Lấy URL mới từ cloudflared output
# Ví dụ: https://new-tunnel-url.trycloudflare.com

# Update trong database
docker exec advisor_db_prod psql -U postgres -d career_advisor -c \
  "UPDATE system_settings SET value = '\"https://new-tunnel-url.trycloudflare.com/tasks/ocr\"'::json WHERE key = 'chandra_api_url';"

# Clear Redis cache
docker exec advisor_redis_prod redis-cli DEL "advisor:chandra_api_url"
```

---

### Option 2: Sử dụng Fallback Strategy (Quick Fix)

Nếu không muốn chạy Chandra service, có thể dùng fallback strategy:

**1. Đổi CV Parser Strategy sang `pymupdf`:**
```bash
# Update .env
CV_PARSER_STRATEGY=pymupdf

# Restart worker
docker compose -f backend/docker-compose.prod.yml restart worker-cv-parser
```

**2. Hoặc dùng `textract` (nếu có):**
```bash
CV_PARSER_STRATEGY=textract
```

**Lưu ý:** Các strategy này sẽ cho kết quả kém hơn Chandra OCR về:
- Độ chính xác OCR
- Xử lý layout phức tạp
- Hỗ trợ đa ngôn ngữ

---

### Option 3: Deploy Chandra trên VPS/Cloud (Production)

**Cho production environment:**

1. **Deploy lên VPS riêng:**
```bash
# SSH vào VPS
ssh user@your-vps-ip

# Clone repo
git clone <repo-url>
cd ai_inference_hub

# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements_ai.txt

# Run with PM2
pm2 start "uvicorn main:app --host 0.0.0.0 --port 8080" --name chandra-ocr

# Expose với Nginx reverse proxy
# hoặc dùng Cloudflare tunnel permanent
```

2. **Hoặc deploy lên GPU cloud (RunPod/Vast.ai):**
```bash
# Sử dụng script có sẵn
chmod +x setup_gpu_node.sh
./setup_gpu_node.sh
```

---

## 📊 Tóm Tắt Tình Trạng

| Component | Status | Notes |
|-----------|--------|-------|
| Database Settings | ✅ OK | Chandra URL & Key đã lưu đúng |
| Redis Cache | ✅ OK | Settings được cache vào Redis DB 0 |
| Config Manager | ✅ OK | Worker đọc được settings từ DB/Redis |
| Admin API Endpoint | ✅ OK | PATCH /admin/settings/{key} hoạt động |
| Cache Invalidation | ✅ OK | Update settings → clear cache tự động |
| Chandra Service | ❌ NOT RUNNING | Service chưa được start |
| Cloudflare Tunnel | ❌ INACTIVE | URL không accessible |
| CV Upload | ❌ FAILED | Không parse được vì Chandra offline |

---

## 🎯 Next Steps

**Để CV parsing hoạt động, cần:**

1. **Start Chandra OCR service** (chọn 1 trong 3 options trên)
2. **Verify service health:**
   ```bash
   curl http://localhost:8080/health
   # → {"status": "ok", "ocr_loaded": true}
   ```
3. **Test OCR endpoint:**
   ```bash
   curl -X POST http://localhost:8080/tasks/ocr \
     -H "X-AI-Key: 6b30dc8ce23ff60ebe56bb723e0ae3fb7d70c9f025c48f519ba4e2161174c22d" \
     -H "Content-Type: application/json" \
     -d '{"file_base64": "test", "file_ext": ".pdf"}'
   ```
4. **Update backend settings** với URL mới (nếu tunnel URL thay đổi)
5. **Test CV upload** từ frontend

---

## 🔍 Debug Commands

**Check if Chandra is reachable:**
```bash
docker exec advisor_gateway_prod curl -v https://milwaukee-voted-employer-annually.trycloudflare.com/health
```

**Check worker logs for OCR errors:**
```bash
docker logs advisor_worker_cv_parser_prod --tail 100 | grep -i "ocr\|chandra\|error"
```

**Test config_manager from worker:**
```bash
docker exec advisor_worker_cv_parser_prod python -c "
import sys; sys.path.insert(0, '/app')
from shared.config_utils import config_manager
print('URL:', config_manager.get_setting('chandra_api_url'))
print('Key:', config_manager.get_setting('chandra_api_key')[:20] + '...')
"
```

**Check Redis cache:**
```bash
docker exec advisor_redis_prod redis-cli -n 0 KEYS "advisor:chandra*"
docker exec advisor_redis_prod redis-cli -n 0 GET "advisor:chandra_api_url"
```

---

## ✅ Kết Luận

**Vấn đề KHÔNG PHẢI Ở:**
- ❌ Settings không lưu vào database
- ❌ Redis cache không hoạt động
- ❌ Worker không đọc được settings
- ❌ Admin API không update được

**Vấn đề THỰC SỰ:**
- ✅ **Chandra OCR service chưa được start**
- ✅ **Cloudflare tunnel không active**

**Fix:** Start Chandra service theo Option 1, 2, hoặc 3 ở trên.
