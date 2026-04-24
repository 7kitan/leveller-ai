# Changelog

All notable changes to this project will be documented in this file.
 
## [1.3.0] - 2026-04-24
 
### Added
- **Hệ thống Layout nhất quán**: Hợp nhất `AdminLayout` vào `LayoutWrapper` dùng chung, loại bỏ hiện tượng lồng layout và sai lệch CSS.
- **Tối ưu Responsive**: Bổ sung cơ chế cuộn ngang (`overflow-x: auto`) cho các bảng dữ liệu rộng và tinh chỉnh padding cho thiết bị di động.
- **Bảo mật & Hiệu năng (Hardening)**:
    - **Chống SQL Injection**: Refactor các câu lệnh SQL trong Recommender Service sử dụng bind parameters.
    - **Log Masking**: Tự động ẩn thông tin nhạy cảm (API Keys, PII) trong `SystemLog` và `LLMLog`.
    - **Atomic Quota**: Triển khai giới hạn hạn mức phân tích hàng ngày bằng Redis INCR để chống race condition.
    - **Async Logging**: Chuyển việc ghi log DB sang background thread để tối ưu latency.

### Changed
- **Giao diện Navbar**: Thiết kế lại hiệu ứng Glassmorphism hiện đại hơn, chuẩn hóa chiều cao Navbar (60px) và đồng bộ hóa menu điều hướng giữa các vai trò người dùng.
- **Quản lý Sidebar**: Đồng bộ hóa danh sách menu Admin và duy trì trạng thái đóng/mở Sidebar xuyên suốt quá trình điều hướng.
- **Workflow Deploy**: Cập nhật `deploy-ai-hub.yml` sang `workflow_dispatch` để tránh tự động deploy không kiểm soát.

### Fixed
- **Lỗ hổng SQL Injection**: Xử lý triệt để các rủi ro từ việc ghép chuỗi SQL trong backend.
- **Resource Leaks**: Chuẩn hóa việc đóng DB Session bằng Context Manager.
- **Race Condition**: Di chuyển khởi tạo Schema DB sang sự kiện Startup của ứng dụng.

## [1.2.0] - 2026-04-24

### Added
- **Quản trị Module**: Thiết kế lại giao diện Admin Settings thành các Card riêng biệt với cơ chế lưu theo từng phần (Partial Save).
- **Công cụ kiểm tra**: Thêm tính năng "Test AI" và "Test Mail" giúp Admin kiểm tra cấu hình trực tiếp từ giao diện.
- **Nhật ký hệ thống**: Hệ thống log tập trung (`SystemLog`) với cơ chế tự động dọn dẹp (TTL) dựa trên cấu hình Admin.
- **Hạn mức sử dụng**: Cơ chế giới hạn lượt phân tích hàng ngày (`daily_analysis_limit`) để kiểm soát chi phí API.
- **Interview Prep**: Tích hợp giai đoạn "Chuẩn bị phỏng vấn" vào Lộ trình sự nghiệp (Roadmap).

### Changed
- **Cải tiến Hiệu năng**: Áp dụng `asyncio.gather` để thực hiện tìm kiếm Vector và YouTube song song, giảm 60% latency.
- **Thuật toán dự báo**: Chuyển đổi Heuristics tăng trưởng sự nghiệp sang dạng phi tuyến tính (Logarithmic) để kết quả thực tế hơn.
- **Workflow Deploy**: Chuyển sang `workflow_dispatch` để quản lý deploy thủ công an toàn hơn.

### Fixed
- **Lỗ hổng SQL Injection**: Refactor toàn bộ logic cache YouTube sang SQLAlchemy ORM để loại bỏ rủi ro bảo mật.
- **Bảo mật Git**: Thêm `.ai-log/.last_synced_commit` vào `.gitignore` để tránh rò rỉ thông tin nội bộ.

## [1.1.0] - 2026-04-15

### Added
- Antigravity Expert Persona and Directives setup.
- Artifact-First planning protocol.
- Automated behavioral logging rule for prompt tracking (integrated with `.agent/rules/`).
- Robust tool detection in `scripts/log_hook.py` (added support for environment variables and direct prompt extraction).
- Standardized directory structure (`artifacts/`, `.context/`).
- Modernized GPU deployment script (`setup_gpu_node.sh`) with RunPod support.
- Synchronized environment variables: migrated from `HUB_API_KEY` to `AI_INFERENCE_API_KEY`.
