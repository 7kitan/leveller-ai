# Backend Production Deployment Scripts

Bộ scripts để deploy và quản lý backend production.

## 📋 Danh Sách Scripts

### 1. `deploy_prod.sh` / `deploy_prod.ps1`
**Mục đích**: Deploy toàn bộ backend production từ đầu

**Sử dụng**:
```bash
# Linux/Mac
bash deploy_prod.sh

# Windows PowerShell
.\deploy_prod.ps1
```

**Các bước thực hiện**:
1. Stop tất cả containers hiện tại
2. Build tất cả Docker images (--no-cache)
3. Start database và redis
4. Start tất cả services (gateway, auth, cv, jd, analysis, recommender, admin)
5. Start tất cả workers (cv-parser, analysis, market-stats, email, celery-beat)
6. Health checks

**Thời gian**: ~10-15 phút

---

### 2. `restart_service.sh`
**Mục đích**: Restart một service cụ thể mà không cần rebuild

**Sử dụng**:
```bash
bash restart_service.sh <service-name>

# Ví dụ:
bash restart_service.sh cv-service
bash restart_service.sh worker-cv-parser
```

**Services có sẵn**:
- `gateway`
- `auth-service`
- `cv-service`
- `jd-service`
- `analysis-service`
- `recommender-service`
- `admin-service`
- `worker-cv-parser`
- `worker-analysis`
- `worker-market-stats`
- `worker-email`
- `celery-beat`

**Thời gian**: ~10-20 giây

---

### 3. `rebuild_worker.sh`
**Mục đích**: Rebuild và restart worker CV parser (dùng khi fix DOCX)

**Sử dụng**:
```bash
bash rebuild_worker.sh
```

**Các bước thực hiện**:
1. Build worker image mới
2. Stop worker cũ
3. Start worker mới
4. Verify python-docx đã được cài

**Thời gian**: ~2-3 phút

---

### 4. `check_status.sh`
**Mục đích**: Kiểm tra trạng thái toàn bộ hệ thống

**Sử dụng**:
```bash
bash check_status.sh
```

**Thông tin hiển thị**:
- Container status
- Health checks (tất cả services)
- Database status và stats (users, CVs, jobs count)
- Redis status
- Worker status
- Disk usage
- Recent errors (10 lỗi gần nhất)

**Thời gian**: ~5 giây

---

### 5. `rollback.sh`
**Mục đích**: Rollback về version trước khi có vấn đề

**Sử dụng**:
```bash
bash rollback.sh
```

**Cảnh báo**: Script này sẽ:
1. Stop tất cả containers
2. Restore database từ backup gần nhất
3. Restart services với images cũ

**Yêu cầu**: Phải có database backup trong `~/backups/`

**Thời gian**: ~5-10 phút

---

## 🚀 Quy Trình Deploy Thông Thường

### Deploy Lần Đầu
```bash
# 1. Pull code
git pull origin demo

# 2. Deploy toàn bộ
bash deploy_prod.sh

# 3. Kiểm tra status
bash check_status.sh
```

### Deploy Update Nhỏ (chỉ code thay đổi)
```bash
# 1. Pull code
git pull origin demo

# 2. Rebuild service cụ thể
bash restart_service.sh cv-service

# 3. Kiểm tra
bash check_status.sh
```

### Fix DOCX Issue
```bash
# 1. Pull code với fix
git pull origin demo

# 2. Rebuild worker
bash rebuild_worker.sh

# 3. Test upload DOCX
# Upload file .docx qua frontend và monitor logs
docker logs -f advisor_worker_cv_parser_prod
```

---

## 🔍 Monitoring & Debugging

### Xem logs realtime
```bash
# Tất cả services
docker compose -f docker-compose.prod.yml logs -f

# Service cụ thể
docker compose -f docker-compose.prod.yml logs -f cv-service

# Worker cụ thể
docker logs -f advisor_worker_cv_parser_prod

# Chỉ errors
docker compose -f docker-compose.prod.yml logs -f | grep -i error
```

### Kiểm tra database
```bash
# Connect vào database
docker exec -it advisor_db_prod psql -U postgres -d career_advisor

# Query nhanh
docker exec advisor_db_prod psql -U postgres -d career_advisor -c "SELECT COUNT(*) FROM user_cvs WHERE status='completed';"
```

### Kiểm tra Redis
```bash
# Ping Redis
docker exec advisor_redis_prod redis-cli ping

# Check queue length
docker exec advisor_redis_prod redis-cli LLEN cv_parsing
```

---

## ⚠️ Troubleshooting

### Worker không kết nối Redis
```bash
# Restart worker
bash restart_service.sh worker-cv-parser

# Kiểm tra network
docker network inspect backend_advisor_net_prod
```

### Service không healthy
```bash
# Xem logs
docker compose -f docker-compose.prod.yml logs <service-name> --tail=100

# Restart service
bash restart_service.sh <service-name>
```

### Database connection issues
```bash
# Kiểm tra database
docker exec advisor_db_prod pg_isready -U postgres

# Restart database (cẩn thận!)
docker compose -f docker-compose.prod.yml restart db
```

### DOCX không parse được
```bash
# Verify python-docx
docker exec advisor_worker_cv_parser_prod python -c "import docx; print(docx.__version__)"

# Nếu không có, rebuild worker
bash rebuild_worker.sh
```

---

## 📊 Health Check Endpoints

- Gateway: `http://localhost:8000/health`
- Auth: `http://localhost:8000/auth/health`
- CV: `http://localhost:8000/cv/health`
- JD: `http://localhost:8000/jd/health`
- Analysis: `http://localhost:8000/analysis/health`

---

## 🔐 Security Notes

1. **Không commit .env file** - Chứa secrets
2. **Backup database thường xuyên** - Trước mỗi deploy
3. **Monitor logs** - Phát hiện issues sớm
4. **Test trước khi deploy** - Chạy trên dev environment trước

---

## 📞 Support

Nếu gặp vấn đề:
1. Chạy `bash check_status.sh` để xem tổng quan
2. Xem logs của service/worker có vấn đề
3. Nếu cần rollback: `bash rollback.sh`
4. Liên hệ team nếu vấn đề nghiêm trọng

---

**Last Updated**: 2026-04-26
**Version**: 1.0
