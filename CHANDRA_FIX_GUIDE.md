# Hướng Dẫn Fix Chandra Settings

## Vấn Đề
- Admin cập nhật Chandra API URL/Key qua UI nhưng worker không nhận được
- Worker chỉ đọc từ `.env`, không đọc từ database
- Dẫn đến import khóa học bị lỗi vì không gửi được request đến Chandra Hub

## Giải Pháp
Khởi tạo Chandra settings trong database từ `.env`, sau đó worker sẽ đọc từ DB thay vì `.env`

## Các Bước Thực Hiện Trên VPS

### 1. Pull Code Mới Nhất
```bash
cd /opt/k109
git pull origin demo
```

### 2. Chạy Migration Script
```bash
cd /opt/k109/backend

# Option A: Chạy script tự động (recommended)
bash scripts/fix_chandra_settings.sh

# Option B: Chạy migration thủ công
docker compose -f docker-compose.prod.yml exec gateway python /app/scripts/migrate_init_chandra_settings.py
```

### 3. Verify Settings Trong Database
```bash
# Kiểm tra settings đã được tạo chưa
docker compose -f docker-compose.prod.yml exec gateway python << 'PYEOF'
import sys
sys.path.append('/app')

from shared.database import SessionLocal
from shared.models import SystemSetting

db = SessionLocal()
settings = db.query(SystemSetting).filter(
    SystemSetting.key.in_(['chandra_api_url', 'chandra_api_key'])
).all()

for s in settings:
    if 'key' in s.key:
        print(f"{s.key}: {s.value[:20]}...{s.value[-10:]}")
    else:
        print(f"{s.key}: {s.value}")

db.close()
PYEOF
```

### 4. Restart Workers
```bash
cd /opt/k109/backend
docker compose -f docker-compose.prod.yml restart worker-cv-parser
docker compose -f docker-compose.prod.yml restart worker-analysis
```

### 5. Test Chandra Connection
```bash
# Test xem worker có kết nối được Chandra không
docker compose -f docker-compose.prod.yml exec gateway python /app/scripts/test_chandra.py
```

### 6. Verify Qua Admin UI
1. Truy cập: https://onehub.cfd/admin/settings
2. Tìm settings: `chandra_api_url` và `chandra_api_key`
3. Nếu chưa có, tạo mới:
   - Key: `chandra_api_url`
   - Value: `"https://milwaukee-voted-employer-annually.trycloudflare.com/tasks/ocr"`
   - Description: `Chandra OCR Hub API URL`

4. Tạo API key:
   - Key: `chandra_api_key`
   - Value: `"6b30dc8ce23ff60ebe56bb723e0ae3fb7d70c9f025c48f519ba4e2161174c22d"`
   - Description: `Chandra OCR Hub API Key`

### 7. Test Import Khóa Học
```bash
cd /opt/k109/backend

# Test import 1 course
docker compose -f docker-compose.prod.yml exec gateway python << 'PYEOF'
import sys
sys.path.append('/app')

from worker.celery_app import celery_app

url = "https://www.coursera.org/learn/machine-learning"
print(f"Queuing course: {url}")

task = celery_app.send_task(
    "worker.tasks.crawler_tasks.crawl_course_task",
    args=[url],
    kwargs={"auto_save": True}
)
print(f"✅ Task queued: {task.id}")
PYEOF

# Check worker logs
docker logs advisor_worker_cv_parser_prod --tail=50 -f
```

## Troubleshooting

### Nếu Settings Không Xuất Hiện Trong Admin UI
```bash
# Clear Redis cache
docker compose -f docker-compose.prod.yml exec redis redis-cli -a "$REDIS_PASSWORD" FLUSHDB

# Restart gateway
docker compose -f docker-compose.prod.yml restart gateway
```

### Nếu Worker Vẫn Không Nhận Settings
```bash
# Check worker có kết nối DB không
docker compose -f docker-compose.prod.yml exec worker-cv-parser python << 'PYEOF'
import sys
sys.path.append('/app')

from shared.config_utils import config_manager

url = config_manager.get_setting("chandra_api_url")
key = config_manager.get_setting("chandra_api_key")

print(f"Chandra URL: {url}")
print(f"Chandra Key: {key[:20] if key else 'None'}...")
PYEOF
```

### Nếu Chandra Hub Không Phản Hồi
```bash
# Test connection từ worker
docker compose -f docker-compose.prod.yml exec worker-cv-parser curl -v https://milwaukee-voted-employer-annually.trycloudflare.com/tasks/ocr
```

## Cách Hoạt Động

### Trước Fix
```
Admin UI → Database (system_settings)
Worker → .env only ❌
```

### Sau Fix
```
Admin UI → Database (system_settings) → Redis Cache → Worker ✅
Worker fallback: DB → .env → default
```

## Notes
- Settings trong DB có độ ưu tiên cao hơn `.env`
- Redis cache TTL = 3600s (1 hour)
- Admin update settings → cache invalidated → worker đọc từ DB ngay lập tức
- Không cần restart worker khi update settings qua UI
