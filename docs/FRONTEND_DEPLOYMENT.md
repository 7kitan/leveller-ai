# 🚀 Hướng Dẫn Deploy Frontend Lên VPS

**Quick Guide:** Deploy Next.js frontend lên VPS Ubuntu

---

## ĐIỀU KIỆN TIÊN QUYẾT

- ✅ VPS đã setup (Docker, Nginx đã cài)
- ✅ Project đã clone tại `/opt/k109`
- ✅ Backend đang chạy
- ✅ Domain đã trỏ về VPS (optional)

---

## BƯỚC 1: SSH VÀO VPS

```bash
ssh deploy@YOUR_VPS_IP
cd /opt/k109
```

---

## BƯỚC 2: CẤU HÌNH .ENV CHO FRONTEND

```bash
cd /opt/k109/frontend

# Copy file mẫu
cp .env.example .env

# Chỉnh sửa
vim .env
```

**Nội dung .env:**

```bash
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000
# Hoặc nếu đã có domain:
# NEXT_PUBLIC_API_URL=https://api.yourdomain.com

# reCAPTCHA Site Key (optional cho dev)
NEXT_PUBLIC_RECAPTCHA_SITE_KEY=6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI

# Environment
NEXT_PUBLIC_ENVIRONMENT=production

# Feature flags
NEXT_PUBLIC_ENABLE_ANALYTICS=false
NEXT_PUBLIC_ENABLE_DEBUG=false
```

**Lưu file:** `:wq`

---

## BƯỚC 3: DEPLOY FRONTEND

### Option 1: Sử dụng Script Tự Động (Recommended)

```bash
cd /opt/k109
bash scripts/deploy_frontend.sh
```

Script sẽ tự động:
- Pull code mới nhất
- Build Docker image
- Start container
- Health check

### Option 2: Deploy Thủ Công

```bash
cd /opt/k109/frontend

# Build image
docker compose -f docker-compose.prod.yml build

# Start container
docker compose -f docker-compose.prod.yml up -d

# Check logs
docker compose -f docker-compose.prod.yml logs -f
```

---

## BƯỚC 4: VERIFY FRONTEND ĐANG CHẠY

```bash
# Check container status
docker ps | grep frontend

# Test local access
curl http://localhost:3000

# Check logs
docker logs advisor_frontend_prod
```

**Expected output:**
- Container status: `Up`
- HTTP response: HTML content
- Logs: No errors

---

## BƯỚC 5: CẤU HÌNH NGINX (Nếu Chưa Có)

### 5.1. Tạo Nginx Config

```bash
sudo vim /etc/nginx/sites-available/lumix-frontend
```

**Nội dung:**

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
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

### 5.2. Enable Site

```bash
# Create symlink
sudo ln -s /etc/nginx/sites-available/lumix-frontend /etc/nginx/sites-enabled/

# Test config
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### 5.3. Test Access

```bash
# Test từ VPS
curl http://localhost

# Test từ máy local
curl http://YOUR_VPS_IP
```

---

## BƯỚC 6: SETUP SSL (HTTPS)

```bash
# Install certbot (nếu chưa có)
sudo apt install -y certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Follow prompts:
# - Enter email
# - Agree to terms
# - Choose redirect HTTP to HTTPS (option 2)

# Test auto-renewal
sudo certbot renew --dry-run
```

**Sau khi setup SSL, update .env:**

```bash
cd /opt/k109/frontend
vim .env

# Update API URL to HTTPS
NEXT_PUBLIC_API_URL=https://api.yourdomain.com

# Restart frontend
docker compose -f docker-compose.prod.yml restart
```

---

## BƯỚC 7: VERIFY DEPLOYMENT

### 7.1. Check All Services

```bash
cd /opt/k109
bash scripts/health_check.sh
```

### 7.2. Test Frontend

```bash
# Test homepage
curl https://yourdomain.com

# Test API connection
curl https://yourdomain.com/api/health
```

### 7.3. Browser Test

Mở trình duyệt và truy cập:
- https://yourdomain.com
- Đăng ký tài khoản mới
- Đăng nhập
- Test các chức năng

---

## TROUBLESHOOTING

### Issue 1: Container không start

```bash
# Check logs
docker logs advisor_frontend_prod

# Common issues:
# - Port 3000 đã được sử dụng
# - .env file thiếu hoặc sai
# - Build failed

# Solution: Rebuild
docker compose -f /opt/k109/frontend/docker-compose.prod.yml down
docker compose -f /opt/k109/frontend/docker-compose.prod.yml build --no-cache
docker compose -f /opt/k109/frontend/docker-compose.prod.yml up -d
```

### Issue 2: Cannot connect to backend

```bash
# Check backend is running
curl http://localhost:8000/health

# Check .env API URL
cat /opt/k109/frontend/.env | grep API_URL

# Check CORS settings in backend
# Backend .env should have:
# ALLOWED_ORIGINS=https://yourdomain.com
```

### Issue 3: 502 Bad Gateway

```bash
# Check frontend container
docker ps | grep frontend

# Check Nginx config
sudo nginx -t

# Check Nginx logs
sudo tail -f /var/log/nginx/error.log

# Restart services
docker compose -f /opt/k109/frontend/docker-compose.prod.yml restart
sudo systemctl restart nginx
```

### Issue 4: SSL certificate issues

```bash
# Check certificate status
sudo certbot certificates

# Renew certificate
sudo certbot renew

# Check Nginx SSL config
sudo vim /etc/nginx/sites-available/lumix-frontend
```

---

## MONITORING & MAINTENANCE

### View Logs

```bash
# Real-time logs
docker logs -f advisor_frontend_prod

# Last 100 lines
docker logs --tail=100 advisor_frontend_prod

# Logs with timestamps
docker logs -t advisor_frontend_prod
```

### Restart Frontend

```bash
cd /opt/k109/frontend
docker compose -f docker-compose.prod.yml restart
```

### Update Frontend

```bash
cd /opt/k109
git pull origin main
bash scripts/deploy_frontend.sh
```

### Check Resource Usage

```bash
# Container stats
docker stats advisor_frontend_prod

# Disk usage
docker system df
```

---

## AUTO-DEPLOYMENT VỚI GITHUB ACTIONS

Frontend đã được cấu hình trong `.github/workflows/frontend-cicd.yml`.

**Để enable auto-deployment:**

1. Push code lên branch `main`
2. GitHub Actions sẽ tự động:
   - Build frontend
   - Deploy lên VPS
   - Run health checks

**Xem deployment status:**
- GitHub Repository → Actions tab

---

## CHECKLIST HOÀN THÀNH

- [ ] .env file đã cấu hình
- [ ] Frontend container đang chạy
- [ ] Nginx đã cấu hình
- [ ] SSL certificate đã cài đặt
- [ ] Domain đã trỏ đúng
- [ ] Frontend accessible từ browser
- [ ] API connection hoạt động
- [ ] Đăng ký/đăng nhập hoạt động

---

## QUICK COMMANDS

```bash
# Deploy frontend
cd /opt/k109 && bash scripts/deploy_frontend.sh

# Check status
docker ps | grep frontend

# View logs
docker logs -f advisor_frontend_prod

# Restart
docker restart advisor_frontend_prod

# Stop
docker stop advisor_frontend_prod

# Remove
docker rm -f advisor_frontend_prod
```

---

**Version:** 1.0  
**Last Updated:** 25/04/2026  
**Status:** ✅ Production Ready
