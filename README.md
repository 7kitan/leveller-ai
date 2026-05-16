# Leveller.ai - Phân Tích Khoảng Trống Kỹ Năng & Gợi Ý Chứng Chỉ

Leveller.ai là nền tảng đột phá sử dụng Trí tuệ nhân tạo (AI) để giúp ứng viên thấu hiểu bản thân thông qua việc **Phân tích Khoảng trống Kỹ năng (Skill Gap Analysis)** và xây dựng lộ trình sự nghiệp tối ưu bằng các **Gợi ý Chứng chỉ & Khóa học (Certificate Suggestion)**.

---

## 🎯 Mục Tiêu & Vấn Đề Giải Quyết

Trong thị trường lao động biến động, ứng viên thường gặp khó khăn trong việc:
- **Xác định lỗ hổng kỹ năng**: Không biết mình thiếu gì so với yêu cầu thực tế của nhà tuyển dụng.
- **Lựa chọn chứng chỉ & lộ trình**: Giữa hàng ngàn chứng chỉ, không biết cái nào thực sự giá trị để lấp đầy khoảng trống năng lực.
- **Tối ưu hóa hồ sơ**: Hồ sơ không phản ánh đúng các kỹ năng cốt lõi mà thị trường đang khao khát.

**Leveller.ai** giải quyết vấn đề này bằng cách sử dụng **Vector Search** và **LLM Reasoning** để phân tích sự tương quan giữa năng lực cá nhân và yêu cầu của **Job Description (JD)**, từ đó đưa ra gợi ý lộ trình chứng chỉ chính xác nhất.

---

## 🚀 Tính Năng Nổi Bật

- **AI CV Parser**: Bóc tách thông tin năng lực tự động với độ chính xác cao (hỗ trợ cả file scan/ảnh).
- **Skill Gap Analysis**: So sánh năng lực hiện tại với yêu cầu của **Job Description (JD)** mục tiêu để chỉ ra chính xác các khoảng trống kỹ năng.
- **Certificate Roadmap**: Đề xuất các chứng chỉ chuyên môn (Professional Certificates) và khóa học (Coursera, Udemy) tối ưu để lấp đầy các khoảng trống kỹ năng cho công việc đã chọn.
- **Market Skill Insights**: Cập nhật xu hướng và trọng số nhu cầu của các kỹ năng từ dữ liệu thị trường thực tế.

---

## 🛠️ Công Nghệ Sử Dụng

- **Backend**: FastAPI, Celery, Redis, PostgreSQL (pgvector).
- **Frontend**: Next.js 14, TypeScript, TailwindCSS.
- **AI**: OpenAI GPT-4o, Chandra OCR (Tùy chọn) / PDF Fallback, LangGraph, Semantic Search, LiteLLM.

---

## ⚡ Hướng Dẫn Chạy Nhanh (Quick Start)

### 1. Cài đặt hạ tầng (Docker)
Yêu cầu: Docker & Docker Compose.
```bash
cd backend
cp .env.example .env  # Cập nhật OPENAI_API_KEY vào .env
docker-compose up -d --build
```

### 2. Cấu hình AI Inference Hub (Chandra OCR) - *Tùy chọn*
Đây là service xử lý trích xuất thông tin CV nâng cao (hỗ trợ file ảnh/scan). **Lưu ý**: Nếu bỏ qua bước này, hệ thống sẽ tự động sử dụng thư viện PDF fallback để trích xuất văn bản từ các file PDF chuẩn.
```bash
cd ai_inference_hub
python3 -m venv venv
source venv/bin/activate  # Hoặc venv\Scripts\activate trên Windows
pip install -r requirements_ai.txt
python setup_chandra.py    # Tải trọng số mô hình (~5GB)
python main.py             # Chạy AI Hub tại port 8080
```

### 3. Khởi tạo dữ liệu (Chạy trong Docker)
Sau khi Bước 1 đã chạy xong (containers đã up), hãy chạy các lệnh sau để khởi tạo hệ thống:
```bash
# 1. Khởi tạo Database & Admin (Chạy 1 lần)
docker exec -it advisor_worker_crawler python scripts/setup_db.py

# 2. Nạp dữ liệu mồi (Khóa học & Kỹ năng)
# Mẹo: Dùng --limit để import nhanh một số lượng nhỏ (ví dụ: 20 khóa học)
docker exec -it advisor_worker_crawler python scripts/seed_all.py --limit 20

# 3. Nạp dữ liệu công việc (TopCV) - Mẫu 20 tin tuyển dụng
# Lưu ý: TopCV chặn các dải IP Datacenter. Nếu chạy trên Cloud (AWS/GCP...), 
# hãy cấu hình PROXY_LIST (nên dùng Proxy dân cư) trong Admin Settings trước khi crawl.
docker exec -it advisor_worker_crawler celery -A worker.celery_app call worker.tasks.crawler_tasks.crawl_topcv_jobs_task --args="[20, true]"
```

### 4. Chạy Frontend
```bash
cd frontend
npm install
npm run dev
```
Truy cập: [http://localhost:3000](http://localhost:3000)

---

## 📖 Hướng Dẫn Sử Dụng

1.  **Phân tích CV**: Upload file CV (PDF/Ảnh) lên hệ thống. AI sẽ tự động bóc tách bộ kỹ năng và kinh nghiệm của bạn.
2.  **Lựa chọn Vị trí (JD)**: Chọn một công việc mục tiêu (ví dụ: Senior Frontend) từ danh sách được crawl từ **TopCV** hoặc dán JD vào để so sánh.
3.  **Phân tích Khoảng trống (Gap Analysis)**: Hệ thống hiển thị biểu đồ Radar Chart so sánh kỹ năng của bạn với yêu cầu thực tế của JD, tính toán **Match Score** hiện tại.
4.  **Nhận Lộ trình Chứng chỉ**: Khám phá danh sách các chứng chỉ chuyên môn và khóa học (Coursera/Youtube) được gợi ý riêng cho bạn để lấp đầy các kỹ năng còn thiếu.
5.  **Dự báo Tăng trưởng**: Xem chỉ số **Match Impact** (khả năng tăng tỷ lệ trúng tuyển) và **Market Demand** (nhu cầu thực tế của thị trường) sau khi hoàn thành lộ trình.

---

## 📂 Tài Liệu Chi Tiết

- **[Kiến Trúc Hệ Thống](ARCHITECTURE.md)**: Chi tiết về Microservices và Data Flow.
- **[Hướng Dẫn Cài Đặt Chi Tiết](SETUP_GUIDE.md)**: Cách thiết lập môi trường và nạp dữ liệu.
- **[Nhật Ký Phát Triển](JOURNAL.md)**: Quá trình xây dựng sản phẩm hàng tuần.
- **[Quy Chuẩn AI Agent](AGENTS.md)**: Dành cho các AI coding assistants.

---

*© 2026 Leveller.ai - 078 Team - A20 AI Thực Chiến*
