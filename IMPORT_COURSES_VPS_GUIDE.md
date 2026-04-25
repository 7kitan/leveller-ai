# Hướng dẫn Import Khóa học trên VPS

## 🎯 Mục đích
Import dữ liệu khóa học từ Coursera vào database trên VPS production.

## 📋 Có 2 cách import

### Cách 1: Bulk Import (Hàng loạt) - Dùng Script
**Phù hợp:** Import nhiều khóa học cùng lúc (50-300 courses)

### Cách 2: Manual Import (Thủ công) - Dùng Admin UI
**Phù hợp:** Import từng khóa học, kiểm tra và chỉnh sửa trước khi lưu

---

## 🚀 Cách 1: Bulk Import với Script

### Bước 1: Chuẩn bị file URLs

**Option A: File JSON (từ Coursera300.json)**
```json
[
  {
    "link": "https://www.coursera.org/learn/python-for-data-science",
    "title": "Python for Data Science"
  },
  {
    "link": "https://www.coursera.org/learn/machine-learning",
    "title": "Machine Learning"
  }
]
```

**Option B: File TXT (đơn giản hơn)**
```
https://www.coursera.org/learn/python-for-data-science
https://www.coursera.org/learn/machine-learning
https://www.coursera.org/learn/deep-learning
```

### Bước 2: Upload file lên VPS

```bash
# Từ máy local
scp coursera_urls.txt user@vps-ip:/tmp/

# Hoặc dùng file có sẵn
scp dataset/Coursera300.json user@vps-ip:/tmp/
```

### Bước 3: SSH vào VPS và chạy script

```bash
# SSH vào VPS
ssh user@vps-ip
cd /path/to/Team078/backend

# Kiểm tra file đã upload
ls -lh /tmp/coursera_urls.txt

# Chạy script import (DRY RUN - test trước)
docker exec advisor_worker_market_stats_prod python scripts/seed_import_worker.py /tmp/coursera_urls.txt --dry-run

# Nếu OK, chạy thật
docker exec advisor_worker_market_stats_prod python scripts/seed_import_worker.py /tmp/coursera_urls.txt

# Hoặc với file JSON
docker exec advisor_worker_market_stats_prod python scripts/seed_import_worker.py /tmp/Coursera300.json
```

**Tham số:**
- `--dry-run`: Test xem sẽ import bao nhiêu URLs (không thực sự import)
- `--force`: Import lại cả URLs đã tồn tại trong database

### Bước 4: Monitor quá trình import

```bash
# Xem logs của worker
docker logs -f advisor_worker_market_stats_prod

# Kiểm tra số lượng tasks trong queue
docker exec advisor_redis_prod redis-cli -n 1 LLEN "market_stats"

# Kiểm tra số khóa học đã import
docker exec advisor_db_prod psql -U postgres -d career_advisor -c "SELECT COUNT(*) FROM courses;"

# Xem khóa học mới nhất
docker exec advisor_db_prod psql -U postgres -d career_advisor -c "SELECT title, source_platform, created_at FROM courses ORDER BY created_at DESC LIMIT 10;"
```

### Bước 5: Verify kết quả

```bash
# Kiểm tra tổng số courses
docker exec advisor_db_prod psql -U postgres -d career_advisor -c "
SELECT 
    COUNT(*) as total_courses,
    COUNT(CASE WHEN source_platform = 'Coursera' THEN 1 END) as coursera_courses,
    COUNT(CASE WHEN vector IS NOT NULL THEN 1 END) as courses_with_vector
FROM courses;
"

# Kiểm tra courses có đầy đủ thông tin
docker exec advisor_db_prod psql -U postgres -d career_advisor -c "
SELECT 
    title,
    provider,
    level,
    duration_hours,
    url
FROM courses 
WHERE source_platform = 'Coursera'
ORDER BY created_at DESC 
LIMIT 5;
"
```

---

## 🖱️ Cách 2: Manual Import qua Admin UI

### Bước 1: Truy cập Admin Panel

```
URL: https://your-domain.com/admin/courses/import
Hoặc: http://vps-ip:3000/admin/courses/import
```

### Bước 2: Nhập URL và Crawl

1. Paste URL khóa học Coursera vào ô input
   ```
   https://www.coursera.org/learn/python-for-data-science
   ```

2. Click nút **"Crawl Course"**

3. Đợi 5-10 giây để hệ thống crawl data

4. Xem preview data đã crawl được

### Bước 3: Chỉnh sửa thông tin (nếu cần)

- **Title**: Tên khóa học
- **Provider**: Nhà cung cấp (Google, IBM, Stanford...)
- **Level**: Beginner, Intermediate, Advanced
- **Duration**: Số giờ học
- **Skills**: Các kỹ năng học được (có thể thêm/xóa)
- **Tools**: Công cụ sử dụng
- **Outcomes**: Kết quả đạt được sau khóa học

### Bước 4: Lưu vào Database

1. Click nút **"Save to Database"** cho từng khóa học
2. Hoặc click **"Save All"** để lưu tất cả cùng lúc
3. Kiểm tra thông báo thành công

### Bước 5: Verify trong Admin Courses List

```
URL: https://your-domain.com/admin/courses
```

Kiểm tra khóa học vừa import đã xuất hiện trong danh sách.

---

## 📊 So sánh 2 cách

| Tiêu chí | Bulk Import (Script) | Manual Import (UI) |
|----------|---------------------|-------------------|
| **Tốc độ** | Nhanh (100+ courses/phút) | Chậm (1 course/lần) |
| **Kiểm soát** | Thấp (tự động) | Cao (review từng course) |
| **Chỉnh sửa** | Không (phải edit sau) | Có (edit trước khi lưu) |
| **Phù hợp** | Import hàng loạt | Import chọn lọc |
| **Yêu cầu** | SSH access | Chỉ cần browser |

---

## 🔧 Troubleshooting

### Issue 1: Script báo lỗi "No such file"

**Nguyên nhân:** File URLs không tồn tại hoặc path sai

**Fix:**
```bash
# Kiểm tra file có tồn tại không
ls -lh /tmp/coursera_urls.txt

# Copy file vào container nếu cần
docker cp /tmp/coursera_urls.txt advisor_worker_market_stats_prod:/tmp/
```

### Issue 2: Worker không xử lý tasks

**Nguyên nhân:** Worker không chạy hoặc queue sai

**Fix:**
```bash
# Kiểm tra worker status
docker ps --filter "name=advisor_worker_market_stats"

# Restart worker
docker restart advisor_worker_market_stats_prod

# Kiểm tra logs
docker logs advisor_worker_market_stats_prod --tail 50
```

### Issue 3: Crawl thất bại - "Scraper returned empty data"

**Nguyên nhân:** 
- URL không hợp lệ
- Coursera thay đổi cấu trúc HTML
- Network issue

**Fix:**
```bash
# Test crawl 1 URL thủ công
docker exec advisor_worker_market_stats_prod python -c "
from shared.scrapers.coursera import scrape_coursera_course
result = scrape_coursera_course('https://www.coursera.org/learn/python')
print(result)
"

# Nếu lỗi, check scraper code
docker exec advisor_worker_market_stats_prod cat shared/scrapers/coursera.py
```

### Issue 4: Courses bị duplicate

**Nguyên nhân:** Import lại URLs đã tồn tại

**Fix:**
```bash
# Xóa duplicates
docker exec advisor_db_prod psql -U postgres -d career_advisor -c "
DELETE FROM courses a USING courses b
WHERE a.id > b.id 
AND a.url = b.url;
"

# Hoặc dùng --force để ghi đè
docker exec advisor_worker_market_stats_prod python scripts/seed_import_worker.py /tmp/urls.txt --force
```

### Issue 5: Courses không có vector embedding

**Nguyên nhân:** Vector chưa được generate

**Fix:**
```bash
# Trigger vector rebuild cho courses
docker exec advisor_db_prod psql -U postgres -d career_advisor -c "
SELECT id, title FROM courses WHERE vector IS NULL LIMIT 10;
"

# Rebuild vectors (qua admin UI hoặc API)
curl -X POST http://localhost:8000/admin/vectordb/sync \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

## 📈 Performance Tips

### 1. Import theo batch nhỏ
```bash
# Thay vì import 300 courses cùng lúc
# Chia thành 6 batch x 50 courses

split -l 50 coursera_urls.txt batch_

# Import từng batch
for file in batch_*; do
  docker exec advisor_worker_market_stats_prod python scripts/seed_import_worker.py /tmp/$file
  sleep 60  # Đợi 1 phút giữa các batch
done
```

### 2. Monitor worker resources
```bash
# Kiểm tra CPU/Memory usage
docker stats advisor_worker_market_stats_prod

# Nếu quá tải, tăng concurrency
# Edit docker-compose.prod.yml:
# WORKER_MARKET_STATS_CONCURRENCY=2  # Tăng từ 1 lên 2
```

### 3. Optimize database
```bash
# Sau khi import xong, chạy VACUUM
docker exec advisor_db_prod psql -U postgres -d career_advisor -c "VACUUM ANALYZE courses;"

# Rebuild indexes
docker exec advisor_db_prod psql -U postgres -d career_advisor -c "REINDEX TABLE courses;"
```

---

## ✅ Checklist Import Courses

### Trước khi import:
- [ ] Backup database
- [ ] Chuẩn bị file URLs (JSON hoặc TXT)
- [ ] Kiểm tra worker đang chạy
- [ ] Kiểm tra disk space đủ (ít nhất 5GB free)

### Trong quá trình import:
- [ ] Monitor worker logs
- [ ] Kiểm tra queue length
- [ ] Verify courses được insert vào DB
- [ ] Check for errors trong logs

### Sau khi import:
- [ ] Verify tổng số courses
- [ ] Kiểm tra courses có đầy đủ thông tin
- [ ] Rebuild vectors nếu cần
- [ ] Test search courses trong UI
- [ ] Cleanup temporary files

---

## 📝 Example: Import 100 Coursera Courses

```bash
# 1. SSH vào VPS
ssh user@vps-ip

# 2. Tạo file URLs
cat > /tmp/top100_courses.txt << 'EOF'
https://www.coursera.org/learn/machine-learning
https://www.coursera.org/learn/python
https://www.coursera.org/learn/data-science
# ... thêm 97 URLs nữa
EOF

# 3. Backup database
docker exec advisor_db_prod pg_dump -U postgres career_advisor > backup_before_import_$(date +%Y%m%d).sql

# 4. Dry run test
docker exec advisor_worker_market_stats_prod python scripts/seed_import_worker.py /tmp/top100_courses.txt --dry-run

# 5. Import thật
docker exec advisor_worker_market_stats_prod python scripts/seed_import_worker.py /tmp/top100_courses.txt

# 6. Monitor progress
watch -n 5 'docker exec advisor_db_prod psql -U postgres -d career_advisor -c "SELECT COUNT(*) FROM courses;"'

# 7. Verify kết quả
docker exec advisor_db_prod psql -U postgres -d career_advisor -c "
SELECT 
    COUNT(*) as total,
    COUNT(CASE WHEN created_at > NOW() - INTERVAL '1 hour' THEN 1 END) as imported_last_hour
FROM courses;
"

# 8. Cleanup
rm /tmp/top100_courses.txt
```

---

## 🔗 Related Documentation

- **Crawler Tasks:** `backend/worker/tasks/crawler_tasks.py`
- **Coursera Scraper:** `backend/shared/scrapers/coursera.py`
- **Admin Import UI:** `frontend/src/app/admin/courses/import/page.tsx`
- **Worker Configuration:** `WORKER_CONFIGURATION_FINAL.md`

---

## 💡 Tips

1. **Import vào giờ thấp điểm** (2-4 AM) để không ảnh hưởng users
2. **Test với 5-10 courses trước** khi import hàng trăm
3. **Monitor disk space** - mỗi course ~50KB data
4. **Backup trước khi import** - phòng trường hợp cần rollback
5. **Verify data quality** - check random 10 courses sau khi import

---

**Created:** 2026-04-25  
**Last Updated:** 2026-04-25  
**Status:** ✅ READY TO USE
