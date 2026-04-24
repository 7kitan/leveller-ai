# Changelog

All notable changes to this project will be documented in this file.
 
## [1.4.0] - 2026-04-24

### Added
- **Thuật toán Tính Tăng Trưởng Dựa Trên Database**: Triển khai module `growth_calculator.py` mới để tính toán chính xác tiềm năng tăng trưởng (potential_match, salary_growth) dựa trên dữ liệu thực tế từ DB thay vì ước lượng từ LLM.
    - `calculate_skill_impact()`: Tính toán impact của từng skill dựa trên `JobSkillRequirement.importance_weight` và `MarketSkillStats.salary_premium_pct`.
    - `calculate_market_sentiment()`: Phân tích xu hướng thị trường dựa trên `growth_rate_30d` và `demand_score`.
    - Mỗi skill gap giờ hiển thị **match_impact** (+X% match) và **salary_impact** (+Y% salary) riêng biệt.
- **Hiển thị Impact Badge**: Thêm badges trực quan cho từng skill gap trên giao diện Recommend, giúp người dùng thấy rõ skill nào ảnh hưởng nhiều nhất đến tỷ lệ match và mức lương.

### Changed
- **Cải tiến Thuật Toán Dự Báo**: Thay thế thuật toán heuristic cũ (chỉ đếm số lượng khóa học: `log2(course_count) * 6.5`) bằng thuật toán dựa trên trọng số thực tế từ Job Description và dữ liệu thị trường.
    - **Trước**: Học Python (critical, 30% weight) = Học Excel (nice-to-have, 5% weight)
    - **Sau**: Python (+25% match, +12% salary) ≠ Excel (+3% match, +2% salary)
- **Tối ưu LLM Prompt**: Loại bỏ các trường `potential_match_pct` và `salary_growth_pct` khỏi LLM prompt vì giờ được tính toán tự động bởi backend.
- **Cải thiện Layout Trang Recommend**: Chuyển đổi `matchBanner` sang layout dọc (vertical stack) với radar chart căn giữa, tối ưu cho mobile.
    - Loại bỏ `matchBreakdownSection` trùng lặp (duplicate bar charts).
    - Radar chart responsive: 350px (mobile) → 400px (tablet) → 450px (desktop).
    - Thêm padding 1.5-2.5rem để tránh cắt label của radar chart.

### Fixed
- **Lỗi Build Frontend**: Bổ sung các translation keys thiếu (`admin_jobs_status_inactive`, `admin_settings_load_error`, `cv_processing`, `notify_me`, `will_notify`).
- **Lỗi TypeScript**: 
    - Fix `AuthContext.login` return type (Promise<void>).
    - Fix unreachable code trong `MaintenanceOverlay`.
    - Fix type errors trong admin pages (jobs, settings, users).
    - Thêm các fields mới vào `SkillGap` interface (`match_impact`, `salary_impact`, `market_demand`, `avg_salary_range`).
- **Lỗi CSS Radar Chart**: Loại bỏ các CSS rules trùng lặp ghi đè chiều cao radar chart, đảm bảo sizing nhất quán.
- **Bug Market Stats Aggregator**: Fix logic extract skills từ `extracted_requirements_json` - trước đây chỉ lấy được `type="skill"` và bỏ qua toàn bộ skills trong `type="group"`, dẫn đến MarketSkillStats table trống. Sau khi fix, đã populate thành công 71 skills với đầy đủ salary premium, demand score, và growth rate.

## [1.3.0] - 2026-04-24
 
### Added
- **Hệ thống Layout nhất quán**: Hợp nhất `AdminLayout` vào `LayoutWrapper` dùng chung, loại bỏ hiện tượng lồng layout và sai lệch CSS.
- **Tối ưu Responsive**: Bổ sung cơ chế cuộn ngang (`overflow-x: auto`) cho các bảng dữ liệu rộng và tinh chỉnh padding cho thiết bị di động.
- **Bảo mật & Hiệu năng (Hardening)**:
    - **Chống SQL Injection**: Refactor các câu lệnh SQL trong Recommender Service sử dụng bind parameters.
    - **Log Masking**: Tự động ẩn thông tin nhạy cảm (API Keys, PII) trong `SystemLog` và `LLMLog`.
    - **Atomic Quota**: Triển khai giới hạn hạn mức phân tích hàng ngày bằng Redis INCR để chống race condition.
    - **Hệ thống Quota tập trung**: Hợp nhất quản lý hạn mức phân tích (`daily_analysis_limit`) và token (`daily_token_limit`) vào `QuotaManager`, hỗ trợ cấu hình riêng biệt cho từng User.
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
