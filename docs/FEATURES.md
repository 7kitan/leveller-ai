# 🚀 TỔNG QUAN CHỨC NĂNG & ROADMAP - LUMIX AI

> **Mục tiêu:** Giúp người dùng biết chính xác cần học gì để sẵn sàng đi làm nhanh nhất và tối ưu hóa giá trị bản thân trên thị trường lao động.

---

## 1. CÁC CHỨC NĂNG CỐT LÕI (ĐÃ HOÀN THÀNH)

### 1.1 Quản lý CV & Hồ sơ Kỹ năng
- **Tải lên đa định dạng**: Hỗ trợ PDF và hình ảnh (scan/ảnh chụp).
- **Xử lý CV thông minh**: Kết hợp Direct Extraction và OCR (Chandra OCR 2) để bóc tách văn bản.
- **Bóc tách AI (Holistic Parsing)**: Tự động trích xuất Kỹ năng, Kinh nghiệm, Học vấn và Chứng chỉ dưới dạng JSON có cấu trúc.
- **Ẩn danh dữ liệu (PII Masking)**: Bảo vệ quyền riêng tư trước khi xử lý qua LLM.

### 1.2 Phân tích Mô tả Công việc (JD Analysis)
- **Thu thập JD đa nguồn**: Xử lý yêu cầu từ văn bản dán vào hoặc cào dữ liệu trực tiếp (TopCV).
- **Bóc tách yêu cầu chuyên sâu**: Xác định kỹ năng bắt buộc, kỹ năng ưu tiên và số năm kinh nghiệm tối thiểu.
- **Tìm kiếm thông minh**: Lọc công việc theo mức lương, địa điểm và độ tương đồng vector.

### 1.3 Phân tích Khoảng cách (Gap Analysis v3)
- **So khớp ngữ nghĩa**: So sánh toàn diện CV với JD dựa trên ngữ cảnh công việc thay vì chỉ so khớp từ khóa.
- **Đánh giá mức độ nghiêm trọng (Severity)**: Xác định kỹ năng thiếu hụt và mức độ ảnh hưởng đến khả năng trúng tuyển.
- **Phân tích tác động tăng trưởng (Impact Analysis)**:
    - Dự báo tỷ lệ khớp tăng thêm (+X% match score).
    - Dự báo mức lương tăng thêm (+Y% salary) cho từng kỹ năng.
- **Lộ trình học tập (Career Roadmap)**: Tạo lộ trình theo thời gian với các giai đoạn và cột mốc rõ ràng.
- **Đề xuất Khóa học & Video**: Gợi ý từ Coursera, Udemy và YouTube dựa trên tìm kiếm vector.

---

## 2. QUẢN TRỊ & HỆ THỐNG

### 2.1 Dashboard Quản trị (Admin Dashboard)
- **Giám sát AI**: Theo dõi Token usage, Latency, Cost và tỷ lệ lỗi LLM.
- **Quản lý Hạn mức (Quota)**: Kiểm soát số lượt phân tích hàng ngày cho từng người dùng.
- **Quản lý Dữ liệu**: Quản trị danh sách công việc (Jobs Manager) và khóa học.
- **Hệ thống Phản hồi (Feedback Loop)**: Thu thập và xử lý đánh giá của người dùng về độ chính xác của AI.

### 2.2 Hiệu năng & Ổn định
- **Caching**: Tăng tốc độ phản hồi bằng cách lưu trữ kết quả phân tích trong Redis.
- **Atomic Operations**: Sử dụng Redis Lua script để quản lý quota an toàn, chống race condition.

---

## 3. LỘ TRÌNH PHÁT TRIỂN (ROADMAP) (Dự tính)

### 3.1 Giai đoạn tiếp theo: Cải thiện UI/UX Nâng cao
- **[FRONTEND] Interview Coach UI**: Giao diện luyện tập phỏng vấn dựa trên các câu hỏi AI đề xuất (Backend đã sẵn sàng).
- **[FRONTEND] CV Optimizer UI**: Gợi ý sửa đổi CV trực tiếp trên giao diện để tối ưu hóa tỷ lệ match.
- **[FRONTEND] Interactive Simulation**: Cho phép người dùng chọn/bỏ chọn khóa học để thấy điểm Match Score thay đổi thời gian thực.

### 3.2 Giai đoạn tiếp theo: Mở rộng tính năng Hệ thống
- **[BACKEND] Hỗ trợ DOCX**: Tích hợp thư viện xử lý file Word.
- **[BACKEND] Hệ thống thông báo**: Gửi Email/Push Notification khi hoàn thành các tác vụ xử lý nền dài hạn.
- **[AI] Multi-Agent Review**: Thêm bước kiểm tra chéo giữa các tác nhân AI để giảm thiểu sai sót (hallucinations).
- **[DATA] Real-time Scraper**: Tự động cập nhật Job hàng ngày từ các sàn tuyển dụng lớn nhất Việt Nam.

---

**Tài liệu liên quan:**
- `ARCHITECTURE.md` - Chi tiết kiến trúc và công nghệ.
- `PROJECT_REPORTS.md` - Báo cáo hoàn thành và lịch sử sửa lỗi.
