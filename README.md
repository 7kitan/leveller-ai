# SkillNexus AI - Hướng Dẫn Cài Đặt và Vận Hành

SkillNexus AI là nền tảng phân tích CV và gợi ý lộ trình nghề nghiệp thông minh, sử dụng công nghệ Vector Search và LLM (OpenAI) để kết nối ứng viên với công việc và khóa học phù hợp nhất.

---

## Yêu cầu hệ thống (Prerequisites)

Trước khi bắt đầu, hãy đảm bảo máy tính của bạn đã cài đặt các phần mềm sau:
1.  **Docker Desktop**: [Tải tại đây](https://www.docker.com/products/docker-desktop/) (Bắt buộc để chạy Database và Redis).
2.  **Python 3.10+**: [Tải tại đây](https://www.python.org/downloads/).
3.  **Node.js 18+**: [Tải tại đây](https://nodejs.org/).
4.  **OpenAI API Key**: Cần thiết để tạo Embedding và phân tích logic.

---

## Bước 1: Thiết lập Môi trường (Environment)

1.  **Tải mã nguồn**:
    ```bash
    git clone https://github.com/a20-ai-thuc-chien/A20-App-078.git
    cd A20-App-078
    ```

2.  **Cấu hình biến môi trường**:
    - Di chuyển vào thư mục `backend/`.
    - Tạo file `.env` từ file mẫu:
    ```bash
    cp .env.example .env
    ```
    - Mở file `.env` và điền `OPENAI_API_KEY` của bạn.

---

## Bước 2: Khởi động Hạ tầng (Infrastructure)

Sử dụng Docker để khởi chạy PostgreSQL (với pgvector) và Redis.

1.  Mở Terminal tại thư mục `backend/`.
2.  Chạy lệnh build và khởi động các dịch vụ:
    ```bash
    docker-compose up -d --build
    ```
3.  Kiểm tra trạng thái các container: `docker ps`. Đảm bảo các dịch vụ `advisor_db`, `advisor_redis`, và `advisor_worker` đang chạy.

---

## Bước 3: Khởi tạo Database và Admin

Bước này sẽ tạo các bảng trong Database và tạo tài khoản Admin mặc định.

1.  Cài đặt thư viện Python (tại thư mục `backend/`):
    ```bash
    pip install -r requirements.txt
    ```
2.  Chạy script khởi tạo:
    ```bash
    python scripts/setup_db.py
    ```
    - *Script này sẽ tự động tạo bảng và tài khoản admin: `admin@lumix.ai` / `Admin@123`.*

---

## Bước 4: Nạp dữ liệu Khóa học (Seeding Courses)

Dữ liệu khóa học sẽ được nạp từ bộ 306 link Coursera có sẵn.

### Nạp Khóa học Coursera (Async)
Đẩy các link từ `dataset/coursera_links.txt` vào hàng đợi để Worker xử lý:
```bash
python scripts/seed_all.py --force
```
*(Hệ thống sử dụng Vector Search để gợi ý khóa học dựa trên kỹ năng trong CV)*

---

## Bước 5: Thu thập Job từ TopCV (Live Import)

Vì không sử dụng bộ dữ liệu tĩnh, bạn cần cào dữ liệu trực tiếp từ TopCV để có danh sách công việc.

### Cách 1: Chạy lệnh thủ công qua CLI
Cào 20 tin tuyển dụng mới nhất:
```bash
python -c "from worker.celery_app import celery_app; celery_app.send_task('worker.tasks.crawler_tasks.crawl_topcv_jobs_task', args=[20], kwargs={'force': True})"
```

### Cách 2: Qua Dashboard Admin
1. Đăng nhập vào trang Admin (`/admin`).
2. Vào mục **Jobs Manager** -> Nhấn **Trigger TopCV Crawl**.

---

## Bước 6: Cấu hình bóc tách CV (Parser Strategies)

Hệ thống hỗ trợ 2 chiến lược bóc tách dữ liệu từ CV (Direct và Chandra):

1.  **Direct (Mặc định)**: Sử dụng thư viện nội bộ (`pymupdf`, `pdf2image`) để trích xuất text. Phù hợp cho CV dạng text hoặc file PDF chuẩn.
2.  **Chandra (Khuyên dùng cho bản quét)**: Sử dụng dịch vụ OCR thông minh (qua API) để xử lý các CV dạng ảnh chụp hoặc scan có độ phức tạp cao.

Để chuyển đổi chiến lược, hãy sửa biến `CV_PARSER_STRATEGY` trong file `.env`:
```env
# Chọn 'direct' hoặc 'chandra'
CV_PARSER_STRATEGY=chandra
```

---

## Bước 7: Khởi động Frontend

1.  Di chuyển sang thư mục `frontend/`:\
    ```bash
    cd ../frontend
    ```
2.  Cài đặt các dependencies và chạy ứng dụng:\
    ```bash
    npm install
    npm run dev
    ```

---

## Truy cập Hệ thống

-   **User Dashboard**: [http://localhost:3000](http://localhost:3000)
-   **Admin Panel**: [http://localhost:3000/admin](http://localhost:3000/admin)
-   **Thông tin đăng nhập Admin mặc định**: `admin@lumix.ai` / `Admin@123`
