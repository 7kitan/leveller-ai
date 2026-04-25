# 🚀 Hướng Dẫn Setup VPS Ubuntu & CI/CD

**Project:** Team078 - Lumix AI Career Advisor  
**Date:** 25/04/2026  
**Target:** Ubuntu 22.04 LTS VPS

---

## 📋 MỤC LỤC

1. [Yêu Cầu Hệ Thống](#yêu-cầu-hệ-thống)
2. [Bước 1: Setup VPS Ubuntu Ban Đầu](#bước-1-setup-vps-ubuntu-ban-đầu)
3. [Bước 2: Cài Đặt Docker & Docker Compose](#bước-2-cài-đặt-docker--docker-compose)
4. [Bước 3: Clone Project & Cấu Hình](#bước-3-clone-project--cấu-hình)
5. [Bước 4: Cấu Hình GitHub Secrets cho CI/CD](#bước-4-cấu-hình-github-secrets-cho-cicd)
6. [Bước 5: Deploy Lần Đầu](#bước-5-deploy-lần-đầu)
7. [Bước 6: Nạp Dữ Liệu Khóa Học](#bước-6-nạp-dữ-liệu-khóa-học)
8. [Bước 7: Cấu Hình Nginx & SSL](#bước-7-cấu-hình-nginx--ssl)
9. [Bước 8: Monitoring & Maintenance](#bước-8-monitoring--maintenance)
10. [Troubleshooting](#troubleshooting)

---

## YÊU CẦU HỆ THỐNG

### Minimum Requirements
- **CPU:** 4 cores
- **RAM:** 8GB
- **Storage:** 50GB SSD
- **OS:** Ubuntu 22.04 LTS
- **Network:** Public IP với port 80, 443, 22 mở

### Recommended Requirements
- **CPU:** 8 cores
- **RAM:** 16GB
- **Storage:** 100GB SSD
- **Bandwidth:** 100Mbps+

---

## BƯỚC 1: SETUP VPS UBUNTU BAN ĐẦU

### 1.1. Kết Nối VPS

```bash
# Kết nối qua SSH
ssh root@YOUR_VPS_IP

# Hoặc nếu dùng user khác
ssh your_user@YOUR_VPS_IP
```

### 1.2. Update Hệ Thống

```bash
# Update package list
sudo apt update && sudo apt upgrade -y

# Install essential tools
sudo apt install -y curl wget git vim htop net-tools ufw
```

### 1.3. Tạo User Deploy (Recommended)

```bash
# Tạo user mới cho deployment
sudo adduser deploy

# Add user vào sudo group
sudo usermod -aG sudo deploy

# Switch sang user deploy
su - deploy
```

### 1.4. Cấu Hình Firewall

```bash
# Enable UFW
sudo ufw enable

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP & HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Check status
sudo ufw status
```

### 1.5. Cấu Hình SSH Key (Recommended)

```bash
# Trên máy local, tạo SSH key nếu chưa có
ssh-keygen -t ed25519 -C "your_email@example.com"

# Copy public key lên VPS
ssh-copy-id deploy@YOUR_VPS_IP

# Test kết nối không cần password
ssh deploy@YOUR_VPS_IP
```

### 1.6. Tăng Cường Bảo Mật SSH

```bash
# Edit SSH config
sudo vim /etc/ssh/sshd_config

# Thay đổi các setting sau:
# PermitRootLogin no
# PasswordAuthentication no
# PubkeyAuthentication yes

# Restart SSH service
sudo systemctl restart sshd
```

---

## BƯỚC 2: CÀI ĐẶT DOCKER & DOCKER COMPOSE

### 2.1. Cài Đặt Docker

```bash
# Remove old versions
sudo apt remove docker docker-engine docker.io containerd runc

# Install dependencies
sudo apt install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Verify installation
docker --version
docker compose version
```

### 2.2. Cấu Hình Docker cho User

```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Apply group changes (logout/login hoặc)
newgrp docker

# Test Docker without sudo
docker run hello-world
```

### 2.3. Cấu Hình Docker Daemon (Optional - Performance)

```bash
# Create daemon config
sudo vim /etc/docker/daemon.json
```

Thêm nội dung:
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2"
}
```

```bash
# Restart Docker
sudo systemctl restart docker
```

---

## BƯỚC 3: CLONE PROJECT & CẤU HÌNH

### 3.1. Clone Repository

```bash
# Tạo thư mục project (nếu chưa có)
sudo mkdir -p /opt/k109
sudo chown deploy:deploy /opt/k109

# Clone repository
cd /opt
git clone https://github.com/a20-ai-thuc-chien/A20-App-078.git k109
cd k109

# Checkout branch demo (hoặc main)
git checkout demo
```

### 3.2. Tạo File .env cho Backend

```bash
cd backend
cp .env.example .env
vim .env
```

**Cấu hình các biến quan trọng:**

```bash
# === SECURITY (CRITICAL) ===
# Generate JWT Secret
JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Generate Redis Password
REDIS_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Generate Postgres Password
POSTGRES_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Generate Redis Encryption Key
REDIS_ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# === DATABASE ===
POSTGRES_HOST=advisor_db_prod
POSTGRES_PORT=5432
POSTGRES_DB=career_advisor
POSTGRES_USER=postgres

# === REDIS ===
REDIS_HOST=advisor_redis_prod
REDIS_PORT=6379

# === ENVIRONMENT ===
ENVIRONMENT=production

# === FRONTEND ===
FRONTEND_URL=https://yourdomain.com
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# === LLM ===
OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE
LLM_MODEL=gpt-4o-mini

# === GOOGLE SERVICES ===
GOOGLE_RECAPTCHA_SECRET_KEY=YOUR_RECAPTCHA_SECRET
YOUTUBE_API_KEY=YOUR_YOUTUBE_KEY

# === EMAIL (SMTP) ===
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM_EMAIL=noreply@yourdomain.com
SMTP_FROM_NAME=Lumix AI

# === QUOTA ===
DAILY_ANALYSIS_LIMIT=10
DAILY_TOKEN_LIMIT=50000
```

**Lưu các giá trị đã generate:**
```bash
# Save to secure file for reference
cat > ~/project_secrets.txt << EOF
JWT_SECRET=$JWT_SECRET
REDIS_PASSWORD=$REDIS_PASSWORD
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
REDIS_ENCRYPTION_KEY=$REDIS_ENCRYPTION_KEY
EOF

chmod 600 ~/project_secrets.txt
```

### 3.3. Tạo File .env cho Frontend

```bash
cd ../frontend
cp .env.example .env
vim .env
```

```bash
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
# Hoặc nếu backend cùng domain:
# NEXT_PUBLIC_API_URL=https://yourdomain.com/api
```

### 3.4. Tạo Docker Network

```bash
# Tạo external network để backend và frontend giao tiếp
docker network create advisor_net_prod
```

---

## BƯỚC 4: CẤU HÌNH GITHUB SECRETS CHO CI/CD

### 4.1. Tạo SSH Key cho GitHub Actions

```bash
# Trên VPS, tạo SSH key riêng cho CI/CD
ssh-keygen -t ed25519 -f ~/.ssh/github_actions_deploy -N ""

# Add public key vào authorized_keys
cat ~/.ssh/github_actions_deploy.pub >> ~/.ssh/authorized_keys

# Copy private key (sẽ dùng cho GitHub Secret)
cat ~/.ssh/github_actions_deploy
```

### 4.2. Thêm Secrets vào GitHub Repository

Vào GitHub Repository → Settings → Secrets and variables → Actions → New repository secret

Thêm các secrets sau:

| Secret Name | Value | Description |
|------------|-------|-------------|
| `DEPLOY_HOST` | `YOUR_VPS_IP` | IP address của VPS |
| `DEPLOY_USER` | `deploy` | Username để SSH |
| `DEPLOY_KEY` | `<private_key_content>` | Nội dung file `~/.ssh/github_actions_deploy` |
| `PROJECT_DIR` | `/opt/k109` | Đường dẫn project trên VPS |

**Cách copy DEPLOY_KEY:**
```bash
# Trên VPS
cat ~/.ssh/github_actions_deploy

# Copy toàn bộ output (bao gồm cả -----BEGIN và -----END)
# Paste vào GitHub Secret DEPLOY_KEY
```

### 4.3. Test SSH Connection từ Local

```bash
# Test với private key
ssh -i ~/.ssh/github_actions_deploy deploy@YOUR_VPS_IP

# Nếu thành công, GitHub Actions sẽ connect được
```

---

## BƯỚC 5: DEPLOY LẦN ĐẦU

### 5.1. Build và Start Backend Services

```bash
cd /opt/k109/backend

# Build images
docker compose -f docker-compose.prod.yml build

# Start database và redis trước
docker compose -f docker-compose.prod.yml up -d db redis

# Đợi 15 giây để DB khởi động
sleep 15

# Check DB health
docker compose -f docker-compose.prod.yml ps
```

### 5.2. Chạy Database Migrations

```bash
# Run all migrations
docker compose -f docker-compose.prod.yml exec -T db psql -U postgres -d career_advisor << 'EOF'
-- Create pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify extension
SELECT * FROM pg_extension WHERE extname = 'vector';
EOF

# Run migration scripts
docker compose -f docker-compose.prod.yml run --rm gateway python scripts/run_all_migrations.py
```

### 5.3. Tạo Admin User

```bash
# Create admin account
docker compose -f docker-compose.prod.yml run --rm gateway python scripts/create_admin.py \
  --email admin@yourdomain.com \
  --password "YourSecurePassword123!" \
  --full-name "Admin User"
```

### 5.4. Start All Backend Services

```bash
# Start all services
docker compose -f docker-compose.prod.yml up -d

# Check all containers
docker compose -f docker-compose.prod.yml ps

# Check logs
docker compose -f docker-compose.prod.yml logs -f --tail=50
```

### 5.5. Verify Backend Health

```bash
# Test gateway health
curl http://localhost:8000/health

# Expected: {"status":"healthy"}

# Test auth service
curl http://localhost:8000/auth/health

# Test other services
curl http://localhost:8000/cv/health
curl http://localhost:8000/jd/health
curl http://localhost:8000/analysis/health
```

### 5.6. Deploy Frontend

```bash
cd /opt/k109/frontend

# Build and start
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# Check logs
docker compose -f docker-compose.prod.yml logs -f
```

### 5.7. Verify Frontend

```bash
# Test frontend
curl http://localhost:3000

# Should return HTML content
```

---

## BƯỚC 6: NẠP DỮ LIỆU KHÓA HỌC

### 6.1. Chuẩn Bị File Dữ Liệu

**Option 1: Sử dụng file coursera_links.txt**

```bash
cd /opt/k109

# Tạo thư mục dataset nếu chưa có
mkdir -p dataset

# Tạo file coursera_links.txt với danh sách URL
vim dataset/coursera_links.txt
```

Thêm các URL khóa học Coursera (mỗi dòng 1 URL):
```
https://www.coursera.org/learn/machine-learning
https://www.coursera.org/learn/python-for-data-science
https://www.coursera.org/learn/deep-learning
...
```

**Option 2: Sử dụng file JSON**

```bash
# Tạo file JSON với cấu trúc
vim dataset/courses.json
```

```json
[
  {
    "link": "https://www.coursera.org/learn/machine-learning",
    "title": "Machine Learning"
  },
  {
    "link": "https://www.coursera.org/learn/python-for-data-science",
    "title": "Python for Data Science"
  }
]
```

### 6.2. Import Khóa Học vào Database

**Method 1: Sử dụng Celery Worker (Recommended)**

```bash
cd /opt/k109/backend

# Đảm bảo Celery workers đang chạy
docker compose -f docker-compose.prod.yml ps | grep worker

# Run seed script
docker compose -f docker-compose.prod.yml exec gateway python scripts/seed_import_worker.py \
  --file /app/../dataset/coursera_links.txt

# Hoặc với JSON
docker compose -f docker-compose.prod.yml exec gateway python scripts/seed_import_worker.py \
  --file /app/../dataset/courses.json

# Check progress trong logs
docker compose -f docker-compose.prod.yml logs -f worker-cv-parser
```

**Method 2: Import Trực Tiếp (Nhanh hơn nhưng blocking)**

```bash
# Run seed_all script
docker compose -f docker-compose.prod.yml exec gateway python scripts/seed_all.py \
  --skip-embed  # Skip embeddings để nhanh hơn, sẽ generate sau

# Với force mode (overwrite existing)
docker compose -f docker-compose.prod.yml exec gateway python scripts/seed_all.py --force
```

### 6.3. Verify Dữ Liệu Đã Import

```bash
# Check số lượng courses trong DB
docker compose -f docker-compose.prod.yml exec db psql -U postgres -d career_advisor -c \
  "SELECT COUNT(*) as total_courses FROM courses;"

# Check courses mới nhất
docker compose -f docker-compose.prod.yml exec db psql -U postgres -d career_advisor -c \
  "SELECT id, title, platform, level, created_at FROM courses ORDER BY created_at DESC LIMIT 10;"

# Check courses có embeddings
docker compose -f docker-compose.prod.yml exec db psql -U postgres -d career_advisor -c \
  "SELECT COUNT(*) as courses_with_embeddings FROM courses WHERE course_embedding IS NOT NULL;"
```

### 6.4. Generate Embeddings (Nếu Skip Ở Bước Trước)

```bash
# Generate embeddings cho courses chưa có
docker compose -f docker-compose.prod.yml exec gateway python << 'PYEOF'
import sys
sys.path.append('/app')
from shared.database import SessionLocal
from shared.models import Course
from shared.skill_extraction import get_embedding
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = SessionLocal()
try:
    courses = db.query(Course).filter(Course.course_embedding == None).all()
    logger.info(f"Found {len(courses)} courses without embeddings")
    
    for i, course in enumerate(courses):
        try:
            text = f"{course.title} {course.description or ''}"
            embedding = get_embedding(text)
            course.course_embedding = embedding
            db.commit()
            
            if (i + 1) % 10 == 0:
                logger.info(f"Processed {i+1}/{len(courses)} courses")
        except Exception as e:
            logger.error(f"Error processing course {course.id}: {e}")
            db.rollback()
    
    logger.info("✅ Embeddings generation complete!")
finally:
    db.close()
PYEOF
```

### 6.5. Import Jobs Data (Optional)

```bash
# Nếu có file jobs dataset
docker compose -f docker-compose.prod.yml exec gateway python scripts/seed_jobs.py \
  --file /app/../dataset/jobs.json
```

---

## BƯỚC 7: CẤU HÌNH NGINX & SSL

### 7.1. Cài Đặt Nginx

```bash
sudo apt install -y nginx
sudo systemctl enable nginx
sudo systemctl start nginx
```

### 7.2. Cấu Hình Nginx cho Backend

```bash
sudo vim /etc/nginx/sites-available/lumix-backend
```

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    client_max_body_size 10M;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

### 7.3. Cấu Hình Nginx cho Frontend

```bash
sudo vim /etc/nginx/sites-available/lumix-frontend
```

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### 7.4. Enable Sites

```bash
# Enable backend
sudo ln -s /etc/nginx/sites-available/lumix-backend /etc/nginx/sites-enabled/

# Enable frontend
sudo ln -s /etc/nginx/sites-available/lumix-frontend /etc/nginx/sites-enabled/

# Test config
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### 7.5. Cài Đặt SSL với Let's Encrypt

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get SSL certificate for backend
sudo certbot --nginx -d api.yourdomain.com

# Get SSL certificate for frontend
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Test auto-renewal
sudo certbot renew --dry-run
```

### 7.6. Update .env với HTTPS URLs

```bash
# Backend .env
cd /opt/k109/backend
vim .env

# Update:
FRONTEND_URL=https://yourdomain.com
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Frontend .env
cd /opt/k109/frontend
vim .env

# Update:
NEXT_PUBLIC_API_URL=https://api.yourdomain.com

# Restart services
cd /opt/k109/backend
docker compose -f docker-compose.prod.yml restart

cd /opt/k109/frontend
docker compose -f docker-compose.prod.yml restart
```

---

## BƯỚC 8: MONITORING & MAINTENANCE

### 8.1. Setup Log Rotation

```bash
# Create logrotate config
sudo vim /etc/logrotate.d/docker-containers
```

```
/var/lib/docker/containers/*/*.log {
    rotate 7
    daily
    compress
    size=10M
    missingok
    delaycompress
    copytruncate
}
```

### 8.2. Setup Monitoring Script

```bash
# Create monitoring script
vim /opt/k109/scripts/monitor.sh
```

```bash
#!/bin/bash
# Simple monitoring script

echo "=== Docker Containers Status ==="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo -e "\n=== Disk Usage ==="
df -h | grep -E "Filesystem|/dev/sda"

echo -e "\n=== Memory Usage ==="
free -h

echo -e "\n=== Database Size ==="
docker exec advisor_db_prod psql -U postgres -d career_advisor -c \
  "SELECT pg_size_pretty(pg_database_size('career_advisor')) as db_size;"

echo -e "\n=== Course Count ==="
docker exec advisor_db_prod psql -U postgres -d career_advisor -c \
  "SELECT COUNT(*) as total_courses FROM courses;"

echo -e "\n=== Recent Errors (Last 50 lines) ==="
docker compose -f /opt/k109/backend/docker-compose.prod.yml logs --tail=50 | grep -i error
```

```bash
chmod +x /opt/k109/scripts/monitor.sh

# Run monitoring
/opt/k109/scripts/monitor.sh
```

### 8.3. Setup Cron Jobs

```bash
# Edit crontab
crontab -e
```

```cron
# Backup database daily at 2 AM
0 2 * * * docker exec advisor_db_prod pg_dump -U postgres career_advisor > ~/backups/db_backup_$(date +\%Y\%m\%d).sql

# Clean old backups (keep 7 days)
0 3 * * * find ~/backups -name "db_backup_*.sql" -mtime +7 -delete

# Monitor system every hour
0 * * * * /opt/k109/scripts/health_check.sh >> ~/monitor.log 2>&1

# Restart services weekly (Sunday 3 AM)
0 3 * * 0 cd /opt/k109/backend && docker compose -f docker-compose.prod.yml restart
```

### 8.4. Database Backup Script

```bash
# Create backup directory
mkdir -p ~/backups

# Create backup script
vim ~/backup_db.sh
```

```bash
#!/bin/bash
BACKUP_DIR=~/backups
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/db_backup_$DATE.sql"

echo "Starting database backup..."
docker exec advisor_db_prod pg_dump -U postgres career_advisor > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "✅ Backup successful: $BACKUP_FILE"
    gzip "$BACKUP_FILE"
    echo "✅ Compressed: $BACKUP_FILE.gz"
else
    echo "❌ Backup failed!"
    exit 1
fi

# Keep only last 7 days
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +7 -delete
echo "✅ Old backups cleaned"
```

```bash
chmod +x ~/backup_db.sh

# Test backup
~/backup_db.sh
```

---

## TROUBLESHOOTING

### Issue 1: Container không start

```bash
# Check logs
docker compose -f docker-compose.prod.yml logs <service_name>

# Check container status
docker compose -f docker-compose.prod.yml ps

# Restart specific service
docker compose -f docker-compose.prod.yml restart <service_name>

# Rebuild if needed
docker compose -f docker-compose.prod.yml up -d --build <service_name>
```

### Issue 2: Database connection failed

```bash
# Check DB is running
docker compose -f docker-compose.prod.yml ps db

# Check DB logs
docker compose -f docker-compose.prod.yml logs db

# Test connection
docker compose -f docker-compose.prod.yml exec db psql -U postgres -d career_advisor -c "SELECT 1;"

# Check .env variables
cat backend/.env | grep POSTGRES
```

### Issue 3: Out of disk space

```bash
# Check disk usage
df -h

# Clean Docker
docker system prune -a --volumes

# Clean old images
docker image prune -a

# Clean logs
sudo truncate -s 0 /var/lib/docker/containers/*/*-json.log
```

### Issue 4: High memory usage

```bash
# Check memory
free -h

# Check container memory
docker stats

# Restart services
docker compose -f docker-compose.prod.yml restart

# Adjust resource limits in docker-compose.prod.yml
```

### Issue 5: CI/CD deployment failed

```bash
# Check GitHub Actions logs
# Go to: GitHub Repo → Actions → Latest workflow run

# Common issues:
# 1. SSH key incorrect → Re-add DEPLOY_KEY secret
# 2. Permission denied → Check user permissions on VPS
# 3. Docker build failed → Check Dockerfile and dependencies
# 4. Health check failed → Check service logs

# Manual deployment
cd /opt/k109
git pull origin main
cd backend
docker compose -f docker-compose.prod.yml up -d --build
```

---

## 🎯 CHECKLIST HOÀN THÀNH

### VPS Setup
- [ ] VPS Ubuntu 22.04 đã cài đặt
- [ ] User deploy đã tạo
- [ ] SSH key authentication đã setup
- [ ] Firewall đã cấu hình
- [ ] Docker & Docker Compose đã cài đặt

### Project Deployment
- [ ] Repository đã clone
- [ ] File .env đã cấu hình đầy đủ
- [ ] Docker network đã tạo
- [ ] Backend services đang chạy
- [ ] Frontend đang chạy
- [ ] Database migrations đã chạy
- [ ] Admin user đã tạo

### Data Import
- [ ] File dữ liệu khóa học đã chuẩn bị
- [ ] Courses đã import vào database
- [ ] Embeddings đã generate
- [ ] Dữ liệu đã verify

### CI/CD
- [ ] GitHub Secrets đã cấu hình
- [ ] SSH key cho GitHub Actions đã setup
- [ ] Workflow đã test thành công

### Production Ready
- [ ] Nginx đã cấu hình
- [ ] SSL certificates đã cài đặt
- [ ] Domain đã trỏ đúng
- [ ] Monitoring script đã setup
- [ ] Backup cron jobs đã cấu hình
- [ ] Log rotation đã setup

---

## 📞 SUPPORT

Nếu gặp vấn đề, check theo thứ tự:

1. **Logs**: `docker compose logs -f`
2. **Container status**: `docker compose ps`
3. **Resource usage**: `docker stats`
4. **Disk space**: `df -h`
5. **Network**: `docker network ls`

---

**Version:** 1.0  
**Last Updated:** 25/04/2026  
**Status:** ✅ Production Ready
