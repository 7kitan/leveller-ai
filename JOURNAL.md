# Weekly Journal

Ghi lại hành trình xây dựng sản phẩm mỗi tuần — những gì đã làm, học được gì, AI giúp như thế nào.

> **Cập nhật mỗi cuối tuần** (trước khi tạo PR). Không cần dài, chỉ cần thật.

---

### Tuần 1 — 06/04/2026 - 12/04/2026

**Thành viên:** Nguyễn Tuấn Kiệt, Nguyễn Tuấn Kiệt, Nguyễn Văn Bách

#### Đã làm
- **Xác định bài toán & Scope**: Phân tích pain point và nhu cầu thực tế của người dùng. Thu hẹp scope MVP tập trung vào Parser CV, So khớp kỹ năng, Gợi ý khóa học, Chứng chỉ và Roadmap.
- **Nghiên cứu & Khảo sát**: Thực hiện market research về các đề tài 053, 072, 002. Quyết định chọn đề tài **AI20K-109** (Phân Tích Khoảng Trống Kỹ Năng & Gợi Ý Chứng Chỉ).
- **Thiết kế hệ thống**: Xây dựng kiến trúc hệ thống tổng quan, thiết kế database sơ bộ và phác thảo User Flow.
- **Kỹ thuật**: Setup Git, môi trường làm việc. Viết nháp prompt cho Skill Parser và Skill Normalizer.

#### Khó nhất tuần này
- Tìm ra pain point thực tế mà nhiều người gặp phải và có thể giải quyết được bằng AI.
- Tìm số liệu khảo sát thực tế tại Việt Nam vì dữ liệu công khai còn hạn chế.

#### AI tool đã dùng
| Tool | Mô tả chi tiết cách dùng | Hiệu quả mang lại |
|---|---|---|
| **ChatGPT** | Phân tích chi tiết các thông tin trong đề bài và gợi ý tính năng. | Giúp làm rõ bài toán và đưa ra các ý tưởng feature độc đáo. |
| **Gemini** | Search dữ liệu thị trường và số liệu dẫn chứng cho bài pitching. | Tìm được những con số cần thiết để chứng minh tiềm năng dự án. |

#### Học được
- Cách market research, định hướng sản phẩm và xác định success metrics cho MVP.
- **Tool Stability**: Tầm quan trọng của stop condition (`max_iterations`) khi thiết kế retry logic cho AI Tools để tránh vòng lặp vô hạn.

#### Nếu làm lại, sẽ làm khác
- Sẽ thực hiện market research sớm hơn nữa để chốt đề tài ngay từ ngày đầu tiên, tránh bị trùng lặp với các team khác.

#### Kế hoạch tuần tới
- Hoàn thiện thiết kế chi tiết hệ thống.
- Chốt database schema.
- Xây dựng pipeline crawl / clean data.
- Bắt đầu phát triển backend core.
- Tích hợp AI parsing / normalization.
- Thiết kế UI/UX prototype.
- Chuẩn bị bản MVP đầu tiên để test nội bộ.

---

### Tuần 2 — 13/04/2026 - 19/04/2026

**Thành viên:** Nguyễn Tuấn Kiệt, Nguyễn Tuấn Kiệt, Nguyễn Văn Bách

#### Đã làm
- **AI Engine (The Brain)**: Tối ưu hóa prompt cho Skill Parser, xây dựng golden dataset và bổ sung edge case để cải thiện độ chính xác.
- **Frontend Development**: Tái cấu trúc frontend theo hướng đơn giản (không dùng React), xây dựng component Login và tinh chỉnh UI (font, màu sắc, layout).
- **Thuật toán**: Nghiên cứu và thử nghiệm các phương pháp tính toán Skill Gap; tối ưu hóa logic xử lý NER từ CV.
- **Tài liệu**: Viết Technical Report cho hệ thống prompt và rà soát lại ground truth cho dữ liệu test.

#### Khó nhất tuần này
- Đồng bộ hóa logic giữa kết quả Parsing của AI và các thực thể kỹ năng trong Database.
- Xử lý các file CV định dạng phức tạp (ảnh/scan) với Chandra OCR.

#### AI tool đã dùng
| Tool | Mô tả chi tiết cách dùng | Hiệu quả mang lại |
|---|---|---|
| **Claude Code** | Phân tích sâu các lỗi concurrency và tối ưu hóa các prompt LangGraph nhạy cảm. | Giảm thiểu lỗi runtime và cải thiện chất lượng dữ liệu AI trích xuất. |
| **AI UI Design** | Sử dụng các AI tool để phác thảo nhanh các mẫu UI hiện đại. | Tăng tốc độ thiết kế giao diện lên 3 lần. |

#### Học được
- Kỹ năng Prompt Engineering nâng cao và cách xây dựng bộ dữ liệu đánh giá (evaluation) chuẩn cho AI.

#### Nếu làm lại, sẽ làm khác
- Sẽ chốt Database Schema sớm hơn để việc phát triển frontend và backend có thể diễn ra song song hoàn toàn ngay từ đầu tuần.

#### Kế hoạch tuần tới
- Xây dựng pipeline xử lý dữ liệu (crawl, clean, chuẩn hóa).
- Tiếp tục thử nghiệm và tối ưu phương pháp tính skill gap.
- Thực hiện test end-to-end cho các luồng chính của hệ thống.
- Hoàn thiện bản MVP để demo.

---

### Tuần 3 — 20/04/2026 - 26/04/2026

**Thành viên:** Nguyễn Tuấn Kiệt, Nguyễn Tuấn Kiệt, Nguyễn Văn Bách

#### Đã làm
- **Data Pipeline**: Hoàn thiện pipeline thu thập dữ liệu từ **Coursera** và **TopCV**; nạp thành công 3,000+ bản ghi khóa học.
- **Tối ưu Backend**: Xây dựng dashboard theo dõi lượng token sử dụng, thêm fallback LLM và hệ thống thông báo khi server quá tải.
- **Hệ thống nạp dữ liệu**: 
    - Triển khai hệ thống **Import/Export với Vector Preservation** (**ADR-3**) giúp tiết kiệm chi phí re-embedding.
    - Xây dựng module **Deduplication** (**ADR-4**) và giao diện hỗ trợ **File Upload URLs** (**ADR-5**).
    - Tích hợp **Confirmation Dialog** (**ADR-6**) hiển thị thời gian ước tính và chi phí trước khi crawl.
- **UI/UX Refinement**: Fix lỗi Google Font, đồng bộ các UI component và tối ưu hóa hiển thị kết quả phân tích.

#### Khó nhất tuần này
- Xử lý Serialization cho dữ liệu Vector (1536 dims) khi chuyển đổi giữa PostgreSQL và hệ thống file JSON.
- Duy trì độ ổn định của Crawler khi đối mặt với cơ chế chống bot của các trang tuyển dụng.

#### AI tool đã dùng
| Tool | Mô tả chi tiết cách dùng | Hiệu quả mang lại |
|---|---|---|
| **OpenCode** | Phân tích cấu trúc database và hỗ trợ viết các script crawl dữ liệu tự động. | Tiết kiệm hàng chục giờ code thủ công cho các module nạp dữ liệu. |
| **LangSmith** | Monitoring các luồng LangGraph để phát hiện các node chạy chậm hoặc tốn token. | Giúp tối ưu hóa 30% chi phí vận hành AI. |

#### Học được
- Cách quản lý Vector Data ở quy mô lớn và quy trình vận hành một hệ thống Data Pipeline tự động.

#### Nếu làm lại, sẽ làm khác
- Sẽ triển khai hệ thống Monitoring ngay từ tuần đầu để có dữ liệu benchmark sớm hơn.

#### Kế hoạch tuần tới
- Thêm nguồn dữ liệu.
- Tối ưu skill gap.
- Hoàn tất test end-to-end.
- Triển khai CI/CD cho MVP.
- Tối ưu hiệu năng, chi phí.
- Hoàn thiện UI/UX.

---

### Tuần 4 — 27/04/2026 - 03/05/2026

**Thành viên:** Nguyễn Tuấn Kiệt, Nguyễn Tuấn Kiệt, Nguyễn Văn Bách

#### Đã làm
- **Ổn định hệ thống**: Fix các bug còn lại trên môi trường Production; tối ưu hóa hệ thống dựa trên kết quả Performance Test (Locust).
- **Design System**: Refactor hệ màu sang **OKLCH** (Lunar Silver-Blue) và chuẩn hóa Typography.
- **AI Evaluation**: Sử dụng framework **RAGAS** để đánh giá độ chính xác của model trên dữ liệu tổng hợp.
- **Admin Features**: Phát triển hệ thống quản lý Skill Taxonomy và Dashboard theo dõi Market Trends.

#### Khó nhất tuần này
- Đảm bảo tính nhất quán của UI sau khi đại tu toàn bộ hệ thống CSS và màu sắc.
- Tối ưu hóa tốc độ Vector Search khi số lượng bản ghi trong Database tăng lên đột ngột.

#### AI tool đã dùng
| Tool | Mô tả chi tiết cách dùng | Hiệu quả mang lại |
|---|---|---|
| **Locust** | Viết các kịch bản test tải (load test) cho các endpoint AI nặng. | Giúp phát hiện sớm các nút thắt cổ chai trong luồng xử lý CV. |
| **Claude Code** | Refactor hệ thống CSS sang OKLCH và chuẩn hóa typography variables. | Đảm bảo giao diện hiện đại và nhất quán 100% trên mọi page. |

#### Học được
- Tầm quan trọng của việc Performance Testing và sức mạnh của hệ màu semantic (OKLCH).

#### Nếu làm lại, sẽ làm khác
- Sẽ sử dụng Lucide Icons ngay từ đầu thay vì các ký tự unicode để tránh lỗi font encoding.

#### Kế hoạch tuần tới
- Tiếp tục fix bug phát sinh sau test.
- Tối ưu performance dựa trên kết quả Locust.
- Hoàn thiện UI/UX và đảm bảo consistency.
- Tiếp tục cải thiện độ chính xác của model/prompt.
- Chuẩn bị hoàn thiện hệ thống cho demo MVP.

---

### Tuần 5 — 04/05/2026 - 10/05/2026

**Thành viên:** Nguyễn Tuấn Kiệt, Nguyễn Tuấn Kiệt, Nguyễn Văn Bách

#### Đã làm
- **Pitching & Demo**: Thiết kế Slide trình bày, quay và chỉnh sửa video demo sản phẩm hoàn chỉnh.
- **Landing Page**: Thiết kế Logo mới, xây dựng Landing Page với hiệu ứng Scroll Snap và thông điệp "Real signal on both sides".
- **Benchmark**: Thực hiện Ragas prompt test chuyên sâu và tối ưu hóa hệ thống quản lý prompt tùy chỉnh.
- **Tài liệu**: Cập nhật toàn bộ tài liệu hướng dẫn cài đặt và sơ đồ kiến trúc hệ thống (SVG).

#### Khó nhất tuần này
- Gói gọn toàn bộ giá trị của một hệ thống AI phức tạp vào một video demo dài 3 phút và slide pitching súc tích.
- Tối ưu hóa Landing Page để đạt điểm hiệu năng cao trên cả thiết bị di động.

#### AI tool đã dùng
| Tool | Mô tả chi tiết cách dùng | Hiệu quả mang lại |
|---|---|---|
| **Ragas** | Đánh giá độ tin cậy và tính liên quan của các khóa học được AI gợi ý. | Đảm bảo kết quả Roadmap mang lại giá trị thực tế cho người dùng. |
| **Slide Design AI** | Hỗ trợ bố cục slide và tối ưu hóa nội dung trình bày pitching. | Giúp slide trông chuyên nghiệp và bám sát mạch câu chuyện sản phẩm. |

#### Học được
- Cách truyền tải giá trị sản phẩm thông qua hình ảnh và demo trực quan.

#### Nếu làm lại, sẽ làm khác
- Sẽ bắt đầu viết kịch bản Pitching sớm hơn 1 tuần để có nhiều thời gian refine thông điệp hơn.

#### Kế hoạch tuần tới
- Tiếp tục refine UI/UX.
- Fix bug và tối ưu performance.
- Cải thiện độ chính xác hệ thống prompt.
- Hoàn thiện tài liệu kỹ thuật.

---

### Tuần 6 — 11/05/2026 - 17/05/2026

**Thành viên:** Nguyễn Tuấn Kiệt, Nguyễn Tuấn Kiệt, Nguyễn Văn Bách

#### Đã làm
- **Rebranding & Docs**: 
    - Chính thức đổi tên thương hiệu thành **Leveller.ai**; chuẩn hóa toàn bộ tài liệu dự án sang Tiếng Việt chuyên nghiệp.
    - Thực hiện tái cấu trúc hệ thống tài liệu (**ADR-7**) để tối ưu hóa việc bàn giao và cài đặt.
- **Production Stabilization**: Giải quyết triệt để lỗi 502 Bad Gateway; triển khai ConfigManager động (Database > .env).
- **Final UAT**: Kiểm thử cuối cùng toàn bộ luồng hệ thống từ Upload CV đến nạp Roadmap và Career Simulation.
- **Deployment**: Đóng gói Docker Compose Production hoàn chỉnh và tích hợp các script cài đặt tự động.

#### Khó nhất tuần này
- Đảm bảo tính nhất quán tuyệt đối giữa mã nguồn thực tế và các sơ đồ kiến trúc trong tài liệu.
- Xử lý các lỗi "phút chót" khi chuyển đổi sang môi trường Production thực tế.

#### AI tool đã dùng
| Tool | Mô tả chi tiết cách dùng | Hiệu quả mang lại |
|---|---|---|
| **Antigravity** | Hỗ trợ rà soát toàn bộ codebase và đồng bộ hóa tài liệu dự án theo chuẩn quốc tế. | Đảm bảo hồ sơ dự án chuyên nghiệp và đầy đủ 100%. |
| **Claude Code** | Tối ưu hóa cấu hình Docker Production và xử lý các lỗi proxy gateway. | Giúp hệ thống vận hành trơn tru trên server thực tế. |

#### Học được
- Quy trình chuẩn hóa và đóng gói sản phẩm phần mềm để sẵn sàng bàn giao (Production-ready).

#### Nếu làm lại, sẽ làm khác
- Sẽ thiết lập môi trường Staging giống hệt Production sớm hơn để việc deploy cuối cùng diễn ra nhanh chóng hơn nữa.

#### Kế hoạch tuần tới
- Bảo vệ dự án và tổng kết kết quả đạt được.

---
*Cập nhật lần cuối: 15/05/2026*
