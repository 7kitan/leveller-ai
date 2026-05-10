# Hướng Dẫn Cài Đặt & Nạp Dữ Liệu

Tài liệu này hướng dẫn chi tiết cách thiết lập môi trường phát triển và nạp dữ liệu ban đầu cho hệ thống Leveller.ai.

---

## 1. Yêu Cầu Tiên Quyết

Đảm bảo bạn đã cài đặt:
- **Docker & Docker Compose** (Bắt buộc cho DB và Redis).
- **Python 3.10+**.
- **Node.js 18+** & **npm**.
- **OpenAI API Key** (Để chạy các tính năng AI).

---

## 2. Các Bước Cài Đặt Nhanh (Quick Start)

### Bước 2.1: Clone Source Code
```bash
git clone https://github.com/a20-ai-thuc-chien/A20-App-078.git
cd A20-App-078
```

### Bước 2.2: Cấu Hình Biến Môi Trường
1.  Vào thư mục `backend/`:
    ```bash
    cp .env.example .env
    ```
2.  Mở `.env` và cập nhật các thông số quan trọng:
    - `OPENAI_API_KEY`: Key của bạn.
    - `POSTGRES_PASSWORD`: Mật khẩu DB (mặc định là `postgres`).
    - `REDIS_PASSWORD`: (Nếu có).

### Bước 2.3: Khởi Động Hạ Tầng (Docker)
Tại thư mục `backend/`:
```bash
docker-compose up -d --build
```
*Lệnh này sẽ khởi chạy Database, Redis, API Gateway, các Microservices và Workers.*

### Bước 2.4: Cài Đặt Dependencies (Local)
Nếu bạn muốn chạy script hoặc debug local:
```bash
# Tại backend/
pip install -r requirements.txt

# Tại frontend/
npm install
```

---

## 3. Khởi Tạo Database & Admin

Chạy script sau để tạo bảng và tài khoản Admin mặc định:
```bash
# Tại backend/
python scripts/setup_db.py
```
- **Tài khoản Admin**: `admin@leveller.ai`
- **Mật khẩu**: `Admin@123`

---

## 4. Hướng Dẫn Nạp Dữ Liệu (Seed Data)

Hệ thống cần dữ liệu Khóa học (Courses) và Công việc (Jobs) để thực hiện gợi ý.

### A. Nạp Khóa Học (Courses)
Dữ liệu mẫu từ Coursera (hơn 3000 khóa học) có thể được nạp bằng 2 cách:

1.  **Qua CLI (Khuyên dùng)**:
    ```bash
    python scripts/seed_all.py --force
    ```
2.  **Qua Admin Dashboard**:
    - Truy cập: `http://localhost:3000/admin/courses/import`
    - Upload file `dataset/coursera_tech_urls.txt`.
    - Nhấn **"Crawl All"** để bắt đầu thu thập dữ liệu.

### B. Nạp Công Việc (Jobs)
Cào dữ liệu thực tế từ TopCV để có danh sách công việc mới nhất:

1.  **Lệnh thủ công**:
    ```bash
    python -c "from worker.celery_app import celery_app; celery_app.send_task('worker.tasks.crawler_tasks.crawl_topcv_jobs_task', args=[20], kwargs={'force': True})"
    ```
2.  **Qua Admin UI**:
    - Vào **Jobs Manager** -> Nhấn **Trigger TopCV Crawl**.

### C. Import Dữ Liệu Có Sẵn (Tiết kiệm chi phí AI)
Nếu bạn có file backup JSON (đã có sẵn Vector Embeddings), hãy sử dụng tính năng **Import Full Data** trong Admin Panel để không phải gọi API OpenAI lần nữa.

---

## 5. Chạy Frontend

```bash
cd frontend
npm run dev
```
Ứng dụng sẽ chạy tại: [http://localhost:3000](http://localhost:3000)

---

## 6. Xử Lý Sự Cố Thường Gặp

- **Lỗi kết nối DB**: Kiểm tra xem container `advisor_db` có đang chạy không (`docker ps`).
- **Lỗi OpenAI Quota**: Kiểm tra số dư trong tài khoản OpenAI của bạn.
- **Worker không chạy**: Kiểm tra logs tại `backend/logs/worker_*.log`.
- **Reset Database**: Nếu muốn làm sạch dữ liệu và cài lại từ đầu:
  ```bash
  docker-compose down -v
  docker-compose up -d
  python scripts/setup_db.py
  ```
