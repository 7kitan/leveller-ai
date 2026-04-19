# Weekly Journal

Ghi lại hành trình xây dựng sản phẩm mỗi tuần — những gì đã làm, học được gì, AI giúp như thế nào.

> **Cập nhật mỗi cuối tuần** (trước khi tạo PR). Không cần dài, chỉ cần thật.

---

### Tuần 1 — 05/04/2026

**Thành viên:** Nguyễn Tuấn Kiệt, Nguyễn Tuấn Kiệt, Nguyễn Văn Bách

#### Đã làm
- Market research tìm pain point và tìm số liệu làm các dẫn chứng.
- Đã market research về đề 053 nhưng khá khó để phát triển thêm các feature để thành SaaS -> No Go.
- Đã market research về đề 072 và thấy có tiềm năng nhưng đã có người phát triển tốt và có cả open source đã tốt -> No Go.
- Đã market research và phân tích làm xong chi tiết cho đề 002 nhưng mà đã có 3 team chọn trước -> No Go.


#### Khó nhất tuần này
- Tìm ra pain point thực tế mà nhiều người gặp phải và có thể giải quyết được bằng AI
- Tìm số liệu làm các dẫn chứng vì ở VN không có quá nhiều số liệu về khảo sát thực tế

#### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| Chatgpt | phân tích chi tiết các thông tin trong đề bài và đưa ra gợi ý | có những gợi ý hay có thể dùng được |
| Gemini | search những dữ liệu mới | tìm được những số liệu cần thiết |

#### Học được
- cách market research và định hướng sản phẩm

#### Nếu làm lại, sẽ làm khác
- Nếu làm lại thì sẽ market research đầu tiên và sớm nhất để chọn được đề sớm nhất mà không bị max team.

#### Kế hoạch tuần tới
- Sau khi phân tích xong về sản phẩm thì sẽ đi đến thiết kế kiến trúc hệ thống và tìm data.
---


### Tuần 2 — 19/04/2026

**Thành viên:** Nguyễn Tuấn Kiệt, Nguyễn Tuấn Kiệt, Nguyễn Văn Bách

#### Đã làm
- **Kiến trúc AI (The Brain):**
    - Chuyển đổi từ gọi LLM đơn lẻ sang hệ thống **LangGraph Orchestration** đa tác vụ cho CV Parsing (V3).
    - Tích hợp thành công **Multi-modal Ingestion** (Chandra OCR) giúp hệ thống xử lý được cả hồ sơ định dạng ảnh/scan với độ chính xác cao.
    - Xây dựng **Advanced Gap Engine v7.0** sử dụng Vector Similarity để so khớp kỹ năng ở 3 tầng (Exact, Semantic, Related).
- **Tính năng Sản phẩm (Core Features):**
    - Triển khai **Career Simulation & Market Preview**: Cho phép người dùng "thử nghiệm" học các khóa học để xem điểm Match Score tăng lên bao nhiêu trước khi học thật.
    - Vẽ biểu đồ **Skill Radar** so sánh đa chiều giữa "Năng lực hiện tại" và "Kỳ vọng thị trường".
    - Tích hợp **AI CV Suggester**: Đưa ra các gợi ý hiệu chỉnh CV ngay trong trang Gap Analysis dựa trên các lỗ hổng kỹ năng phát hiện được.
- **Kỹ thuật Hệ thống (Engineering Excellence):**
    - Giải quyết bài toán UI blockage bằng **Celery & Redis**: Toàn bộ tác vụ AI nặng được đẩy xuống background xử lý bất đồng bộ.
    - Xây dựng hệ thống **Real-time Progress Tracking**: Hiển thị tiến trình xử lý chi tiết từng bước (Step-by-step) cho người dùng.
- **Trải nghiệm Người dùng (Premium UI/UX):**
    - Hoàn thiện bộ **Custom Component System**: Thay thế hoàn toàn các Select/Input mặc định bằng các component được thiết kế riêng với Micro-animations.
    - Tối ưu hóa **Fluid Design & Dark Mode**: Đảm bảo giao diện hiện đại, chuyên nghiệp và nhất quán trên toàn bộ các module.

#### Khó nhất tuần này

#### AI tool đã dùng
| Tool | Mô tả chi tiết cách dùng | Hiệu quả mang lại |
|---|---|---|
| **Antigravity (Gemini)** | Thiết kế kiến trúc component trung tâm, refactor logic frontend phức tạp và viết unit test. | Tăng tốc độ phát triển giao diện lên 3-4 lần, đảm bảo code sạch và dễ bảo trì. |
| **Claude Code** | Phân tích sâu các lỗi concurrency trong Celery và tối ưu hóa các prompt LangGraph nhạy cảm. | Giảm thiểu lỗi runtime hệ thống và cải thiện chất lượng dữ liệu AI trích xuất. |
| **GPT-4o API** | Engine chính cho việc Parsing CV và phân tích Gap chuyên sâu. | Đạt độ chính xác >90% trên các mẫu CV tiếng Anh và tiếng Việt hỗn hợp. |

#### Học được
- **Human-in-the-loop (HITL):** Hiểu rằng AI không bao giờ chính xác 100%, vì vậy việc xây dựng giao diện cho phép người dùng kiểm tra và hiệu chỉnh (Check & Verify) là cực kỳ quan trọng để giữ niềm tin.
- **Async State Management:** Kỹ năng quản lý trạng thái phức tạp khi các service Backend trả về kết quả tại các thời điểm khác nhau.

#### Nếu làm lại, sẽ làm khác
- Sẽ xây dựng một **Shared Consistency Layer** ngay từ đầu cho các hằng số (constants) và types để frontend/backend không bao giờ bị lệch nhãn (labels).

#### Kế hoạch tuần tới
- Phát triển hệ thống **Smart Recommendation v2**: Không chỉ gợi ý khóa học mà còn gợi ý cả các Project thực tế để lấp đầy Gap.
- Dashboard quản trị và tích hợp Pipeline phân tích Course tự động từ dữ liệu Udemy/Coursera.
---
---
