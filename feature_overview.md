# 🚀 Danh sách chức năng – Hệ thống AI hướng nghiệp (Lumix AI)

## 🎯 Mục tiêu
> Giúp người dùng biết chính xác cần học gì để sẵn sàng đi làm nhanh nhất và tối ưu hóa giá trị bản thân trên thị trường lao động.

---

## 🧠 1. Chức năng chính

### 1.1 Quản lý CV & Hồ sơ kỹ năng
- **Tải lên đa định dạng**: Hỗ trợ PDF, DOCX và hình ảnh (scan/ảnh chụp).
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
- **Mô phỏng lộ trình (Career Roadmap) ⭐**: Tạo lộ trình học tập theo thời gian với các giai đoạn và cột mốc cụ thể.
- **Gợi ý khóa học**: Đề xuất khóa học từ Coursera/Udemy dựa trên độ khớp vector và mức độ ưu tiên của kỹ năng thiếu.

---

## 📊 2. Phân tích thị trường chuyên sâu (Premium) ⭐

### 2.1 Ước tính giá trị kỹ năng (Skill Valuation)
- Dự báo mức lương tăng thêm dự kiến cho mỗi kỹ năng trong lộ trình học.
- Giúp người dùng ưu tiên học những kỹ năng có lợi nhuận đầu tư (ROI) cao nhất.

### 2.2 Chỉ số khớp thị trường (Market Fit Index)
- Thống kê số lượng công việc thực tế khớp với bộ kỹ năng hiện tại của người dùng.
- Định vị vị thế cá nhân trong thị trường (ví dụ: "Bạn đang thuộc Top 10% ứng viên phù hợp nhất").

### 2.3 Radar xu hướng 30 ngày (Trend Radar)
- Cập nhật hàng ngày các kỹ năng đang tăng trưởng nóng về nhu cầu tuyển dụng.
- Phân tích xu hướng lương theo từng nhóm kỹ năng và vị trí.

---

## 🔁 3. Hệ thống học máy & Phản hồi

### 3.1 Vòng lặp phản hồi (Feedback Loop) ⭐
- Người dùng đánh giá độ chính xác của phân tích Gap.
- Báo cáo kỹ năng bị bỏ sót để AI tự học và điều chỉnh kết quả lần sau.

### 3.2 Tối ưu hóa cá nhân hóa
- Hệ thống tự điều chỉnh trọng số gợi ý dựa trên lịch sử tương tác và phản hồi của người dùng.

---

## 🔐 4. Bảo mật & Trải nghiệm người dùng

### 4.1 Bảo mật dữ liệu ⭐
- **Ẩn danh thông tin (PII Masking)**: Tự động che số điện thoại, email, địa chỉ trước khi gửi dữ liệu đến LLM.
- **Quyền riêng tư**: Mã hóa dữ liệu người dùng và file CV.

### 4.2 Trải nghiệm Premium
- **Xử lý nền (Async Processing)**: Sử dụng Celery để xử lý các tác vụ AI nặng mà không gây treo trình duyệt.
- **Thông báo trạng thái**: Cập nhật tiến trình xử lý chi tiết theo thời gian thực.
- **Giao diện hiện đại**: Hỗ trợ Dark/Light mode, hiệu ứng mượt mà và responsive trên mọi thiết bị.

---

## 🏁 Tổng kết
Hệ thống không chỉ là một công cụ phân tích mà còn là một **Trợ lý Sự nghiệp AI** giúp người dùng:
1. Hiểu rõ giá trị hiện tại của bản thân.
2. Biết chính xác những gì thị trường đang cần và trả lương cao.
3. Có lộ trình học tập tối ưu để đạt được mục tiêu thu nhập mong muốn.
