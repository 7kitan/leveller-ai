# 🚀 Danh sách chức năng – Hệ thống AI hướng nghiệp (Lumix AI)

## 🎯 Mục tiêu
> Giúp người dùng biết chính xác cần học gì để sẵn sàng đi làm nhanh nhất và tối ưu hóa giá trị bản thân trên thị trường lao động.

---

## 🧠 1. Chức năng chính (Đã hoàn thành)

### 1.1 Quản lý CV & Hồ sơ kỹ năng
- **Tải lên đa định dạng**: Hỗ trợ PDF và hình ảnh (scan/ảnh chụp). (DOCX dự kiến hỗ trợ ở phiên bản sau).
- **Xử lý CV từ ảnh (Chandra OCR 2) ⭐**: Sử dụng engine OCR chuyên dụng để trích xuất văn bản có cấu trúc từ ảnh.
- **Bóc tách AI (Holistic Parsing)**: Tự động trích xuất Kỹ năng, Kinh nghiệm, Học vấn và Chứng chỉ.
- **Xác thực hồ sơ**: Người dùng có thể kiểm tra và chỉnh sửa lại thông tin AI đã bóc tách trước khi lưu.

### 1.2 Phân tích thị trường (Job Description)
- **Thu thập JD thông minh**: Xử lý yêu cầu từ tin tuyển dụng hoặc văn bản dán vào.
- **Bóc tách yêu cầu (Extraction)**: Xác định kỹ năng bắt buộc, kỹ năng ưu tiên và số năm kinh nghiệm tối thiểu.
- **Tìm kiếm nâng cao ⭐**: Lọc công việc theo địa điểm, mức lương, loại hình làm việc và độ khớp kỹ năng.

### 1.3 Phân tích khoảng cách & Lộ trình (Gap Analysis v3)
- **So khớp kỹ năng thông minh**: So sánh toàn diện CV với JD dựa trên ngữ cảnh (không chỉ là từ khóa).
- **Đánh giá mức độ chênh lệch (Skill Gap)**: Xác định kỹ năng đã có, kỹ năng thiếu và mức độ nghiêm trọng (Severity).
- **Phân tích tác động (Impact Analysis) ⭐**: Tính toán chính xác mức độ tăng tỷ lệ match (+X%) và mức lương (+Y%) cho từng kỹ năng thiếu.
- **Lộ trình sự nghiệp (Career Roadmap)**: Tạo lộ trình học tập theo thời gian với các giai đoạn, cột mốc và kỹ năng đạt được.
- **Gợi ý khóa học & Video**: Đề xuất khóa học từ Coursera/Udemy/YouTube dựa trên độ khớp vector và mức độ ưu tiên.

---

## 📊 2. Phân tích thị trường chuyên sâu (Premium)

### 2.1 Dashboard Xu hướng (Market Trends) ⭐
- **Biểu đồ Area Chart**: Theo dõi nhu cầu kỹ năng theo thời gian (24h, 7d, 30d).
- **Top Gainers**: Tự động nhận diện các kỹ năng đang "hot" và có mức tăng trưởng nhu cầu cao nhất.
- **Chỉ số Market Fit**: Đánh giá độ khớp tổng thể của người dùng với toàn bộ thị trường lao động.

### 2.2 Ước tính giá trị kỹ năng (Skill Valuation)
- Dự báo mức lương tăng thêm dự kiến cho mỗi kỹ năng dựa trên dữ liệu thực tế từ hàng ngàn JD.
- Giúp người dùng ưu tiên học những kỹ năng có ROI cao nhất.

### 2.3 Giả lập tăng trưởng (Growth Simulation)
- Tính toán điểm tiềm năng (Potential Match Score) khi hoàn thành các khóa học được chọn.
- Dự báo mức lương sau khi bổ sung các kỹ năng mới.

---

## 🔁 3. Hệ thống học máy & Quản trị

### 3.1 Vòng lặp phản hồi (Feedback Loop) ⭐
- **Giao diện phản hồi**: Người dùng đánh giá độ chính xác của phân tích Gap ngay tại trang kết quả.
- **Báo cáo kỹ năng**: Cho phép người dùng báo cáo các kỹ năng bị AI bỏ sót để cải thiện độ chính xác.

### 3.2 Quản trị hệ thống (Admin Dashboard)
- **Giám sát AI**: Token, Latency, Cost và tỉ lệ lỗi LLM.
- **Quản lý Phản hồi ⭐**: Giao diện tập trung xem xét các đánh giá và góp ý kỹ năng từ người dùng.
- **Quản lý Quota**: Kiểm soát hạn mức sử dụng hàng ngày của từng tài khoản.

---

## 🚧 4. Chức năng chưa có (Roadmap - Cần triển khai)

### 4.1 UI/UX cho Tính năng Nâng cao
- **[FRONTEND] Interview Coach UI**: Tích hợp giao diện hiển thị câu hỏi phỏng vấn thử (đã có API backend).
- **[FRONTEND] CV Optimizer UI**: Giao diện gợi ý sửa đổi CV trực quan (đã có API backend).
- **[FRONTEND] Interactive Simulation**: Cho phép người dùng tick/untick khóa học trên Roadmap để thấy Match Score nhảy realtime.

### 4.2 Tính năng Hệ thống
- **[BACKEND] DOCX Support**: Tích hợp thư viện `python-docx` để hỗ trợ bóc tách CV định dạng Word (hiện tại chưa hỗ trợ).
- **[BACKEND] Notification System**: Gửi Email/Push notification khi các tác vụ xử lý AI nền (Async) hoàn tất.
- **[AI] Multi-Agent Review**: Thêm bước kiểm tra chéo giữa các AI Agent để giảm hallucination trong lộ trình.
- **[DATA] Real-time Scraper**: Tự động cập nhật JD từ các nguồn TopCV, VietnamWorks hàng ngày (hiện tại chủ yếu dùng dữ liệu mẫu/seed).

---

## 🏁 Tổng kết
Hệ thống là một **Trợ lý Sự nghiệp AI** toàn diện giúp người dùng:
1. Hiểu rõ giá trị hiện tại của bản thân.
2. Biết chính xác những gì thị trường đang cần và trả lương cao.
3. Có lộ trình học tập tối ưu để đạt được mục tiêu thu nhập mong muốn.
