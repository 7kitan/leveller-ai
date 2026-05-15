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
- **AI**: OpenAI GPT-4o, Chandra OCR (Multimodal Parsing), LangGraph, Semantic Search, LiteLLM.

---

## ⚡ Hướng Dẫn Chạy Nhanh (Quick Start)

### 1. Cài đặt hạ tầng (Docker)
Yêu cầu: Docker & Docker Compose.
```bash
cd backend
cp .env.example .env  # Cập nhật OPENAI_API_KEY vào .env
docker-compose up -d --build
```

### 2. Cấu hình AI Inference Hub (Chandra OCR)
Đây là "bộ não" xử lý trích xuất thông tin CV.
```bash
cd ai_inference_hub
python3 -m venv venv
source venv/bin/activate  # Hoặc venv\Scripts\activate trên Windows
pip install -r requirements_ai.txt
python setup_chandra.py    # Tải trọng số mô hình (~5GB)
python setup_poppler.py    # (Windows) Setup tool xử lý PDF
python main.py             # Chạy AI Hub tại port 8080
```

### 3. Khởi tạo dữ liệu (Chạy trong Docker)
Sau khi Bước 1 đã chạy xong (containers đã up), bạn không cần cài Python trên máy host mà hãy chạy lệnh trực tiếp vào container:
```bash
# 1. Khởi tạo Database & Admin (Chạy 1 lần)
docker exec -it advisor_worker_crawler python scripts/setup_db.py

# 2. Nạp dữ liệu mẫu (Khóa học & Kỹ năng)
docker exec -it advisor_worker_crawler python scripts/seed_all.py

# Lưu ý: Backend (FastAPI) đã tự động chạy bên trong Docker tại port 8000.
# Bạn có thể kiểm tra tại: http://localhost:8000/docs
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

1.  **Phân tích CV**: Upload file CV (PDF/JPG/PNG/DOC/DOCX) lên hệ thống.
2.  **Xem Gap Analysis**: Hệ thống sẽ hiển thị biểu đồ Radar Chart so sánh kỹ năng của bạn với thị trường.
3.  **Khám phá Roadmap**: Nhấp vào các kỹ năng còn thiếu để xem danh sách khóa học và công việc gợi ý.
4.  **Thử nghiệm (Simulation)**: Chọn "Simulate Completion" trên một khóa học để xem điểm tương quan (Match Score) của bạn sẽ thay đổi thế nào sau khi học.

---

## 📂 Tài Liệu Chi Tiết

- **[Kiến Trúc Hệ Thống](ARCHITECTURE.md)**: Chi tiết về Microservices và Data Flow.
- **[Hướng Dẫn Cài Đặt Chi Tiết](SETUP_GUIDE.md)**: Cách thiết lập môi trường và nạp dữ liệu.
- **[Nhật Ký Phát Triển](JOURNAL.md)**: Quá trình xây dựng sản phẩm hàng tuần.
- **[Quy Chuẩn AI Agent](AGENTS.md)**: Dành cho các AI coding assistants.

---

*© 2026 Leveller.ai - 078 Team - A20 AI Thực Chiến*
