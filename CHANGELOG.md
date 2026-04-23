# Changelog

All notable changes to this project will be documented in this file.

## [1.2.0] - 2026-04-24

### Added
- **Kiến trúc Hệ thống (v3)**: Thiết kế lại toàn bộ tài liệu `architecture.md` với sơ đồ Mermaid trực quan cho Microservices, Database ERD và Pipeline AI.
- **Đa ngôn ngữ (Vietnamese)**: Bản dịch tiếng Việt hoàn chỉnh cho tài liệu kiến trúc hệ thống.
- **Admin Profile**: Tính năng đổi mật khẩu cho tài liệu Admin.
- **Bảo trì hệ thống**: Cơ chế chặn người dùng khi ở chế độ bảo trì (Maintenance Mode) mà không gây lỗi hydration.

### Changed
- **Tối ưu hóa Pipeline**: Cải thiện hiệu suất bóc tách CV và cơ chế vô hiệu hóa cache (cache invalidation) cho Gap Analysis v3.
- **JD Extraction**: Tối ưu hóa logic bóc tách yêu cầu công việc từ JD thô.
- **UI/UX Navbar**: Di chuyển nút chuyển đổi ngôn ngữ lên Navbar và sử dụng font IBM Plex Mono.
- **Giao diện Cao cấp**: Tăng cường trải nghiệm người dùng với các hiệu ứng và layout premium cho Dashboard.

### Fixed
- **Bảo mật**: Thêm `rel="noopener noreferrer"` cho các liên kết ngoài để ngăn chặn reverse tabnabbing.
- **UI Tweaks**: Loại bỏ hiệu ứng hover lift trên card để tránh click nhầm và tinh chỉnh tiêu đề trang.

## [1.1.0] - 2026-04-15

### Added
- Antigravity Expert Persona and Directives setup.
- Artifact-First planning protocol.
- Automated behavioral logging rule for prompt tracking (integrated with `.agent/rules/`).
- Robust tool detection in `scripts/log_hook.py` (added support for environment variables and direct prompt extraction).
- Standardized directory structure (`artifacts/`, `.context/`).
- Modernized GPU deployment script (`setup_gpu_node.sh`) with RunPod support.
- Synchronized environment variables: migrated from `HUB_API_KEY` to `AI_INFERENCE_API_KEY`.
