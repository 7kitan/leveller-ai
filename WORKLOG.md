# Worklog

Ghi lại các quyết định kỹ thuật, phân công, và brainstorming của nhóm.

> Cập nhật **bất cứ khi nào** nhóm ra quyết định kỹ thuật quan trọng hoặc thay đổi hướng đi.

---

## Template

### Quyết định kỹ thuật

```markdown
### [ADR-N] Tiêu đề quyết định — DD/MM/YYYY

**Bối cảnh:** Vấn đề cần giải quyết là gì?

**Các lựa chọn đã xem xét:**
- Option A: ...
- Option B: ...

**Quyết định:** Chọn option nào và tại sao.

**Hệ quả:** Những gì bị ảnh hưởng / trade-off.
```

### Phân công

```markdown
### Sprint N — DD/MM → DD/MM/YYYY

| Task | Người làm | Deadline | Trạng thái |
|---|---|---|---|
| | | | |
```

### Brainstorming

```markdown
### Brainstorm: [Chủ đề] — DD/MM/YYYY

**Câu hỏi:** ...

**Các ý tưởng:**
- Ý tưởng 1: ...
- Ý tưởng 2: ...

**Kết luận:** ...
```

---

## Quyết định kỹ thuật

### [ADR-3] Export/Import System với Vector Preservation — 27/04/2026

**Bối cảnh:** Hệ thống cần khả năng backup/restore database và migrate data giữa các môi trường (dev/staging/production). Vector embeddings được generate bởi OpenAI API tốn chi phí và thời gian, cần preserve khi migrate.

**Các lựa chọn đã xem xét:**
- **Option A - Database Dump (pg_dump)**: 
  - Pros: Native PostgreSQL, bao gồm cả vectors, fast
  - Cons: Không portable giữa các DB versions, khó filter data, binary format khó inspect
- **Option B - JSON Export với Vectors**:
  - Pros: Human-readable, portable, có thể filter/transform data, inspect dễ dàng
  - Cons: File size lớn hơn, cần serialize/deserialize vectors
- **Option C - CSV Export (không có vectors)**:
  - Pros: Đơn giản, dễ edit bằng Excel
  - Cons: Mất vectors → phải re-embed → tốn tiền và thời gian

**Quyết định:** Chọn Option B (JSON Export với Vectors) vì:
1. Preserve vectors → không cần re-generate embeddings (tiết kiệm $$$)
2. Human-readable → dễ debug và validate data
3. Portable → có thể import vào bất kỳ environment nào
4. Flexible → có thể filter/transform data trước khi import

**Hệ quả:** 
- File size lớn hơn (~2-3MB cho 1000 courses với vectors)
- Cần implement proper serialization/deserialization logic
- Trade-off được chấp nhận vì lợi ích về cost và flexibility

---

### [ADR-4] Deduplication Strategy cho Import Operations — 27/04/2026

**Bối cảnh:** Khi import bulk data, có thể có duplicates hoặc data đã tồn tại trong DB. Cần quyết định cách xử lý.

**Các lựa chọn đã xem xét:**
- **Option A - Overwrite existing**: Update nếu đã tồn tại
  - Pros: Luôn có data mới nhất
  - Cons: Có thể mất data quan trọng, không safe
- **Option B - Skip duplicates**: Bỏ qua nếu đã tồn tại
  - Pros: Safe, không mất data cũ
  - Cons: Không update được data đã thay đổi
- **Option C - Fail on duplicates**: Throw error và rollback
  - Pros: Đảm bảo data integrity
  - Cons: User experience kém, phải manual cleanup

**Quyết định:** Chọn Option B (Skip duplicates) với detailed reporting vì:
1. Safe by default → không risk mất data
2. User-friendly → không fail toàn bộ operation vì 1 duplicate
3. Transparent → báo cáo rõ ràng số lượng imported/skipped/errors
4. Có thể extend sau để support update mode nếu cần

**Hệ quả:**
- Cần implement unique constraint checks (source_platform + source_id cho Courses, source_id cho Jobs)
- Response phải include detailed breakdown: imported_count, skipped_count, error_count
- User cần review skipped items để quyết định có cần manual update không

---

### [ADR-5] File Upload vs Paste URLs — 27/04/2026

**Bối cảnh:** Admin cần import hàng trăm URLs. Paste thủ công vào textarea không practical.

**Các lựa chọn đã xem xét:**
- **Option A - Chỉ textarea**: Đơn giản nhất
  - Pros: Không cần implement file upload
  - Cons: UX kém với nhiều URLs, dễ lỗi copy/paste
- **Option B - Chỉ file upload**: Modern approach
  - Pros: Professional, handle large datasets
  - Cons: Không flexible cho quick tests với vài URLs
- **Option C - Cả hai (textarea + file upload)**:
  - Pros: Flexible, phù hợp mọi use case
  - Cons: Phức tạp hơn về UI/UX

**Quyết định:** Chọn Option C (cả hai) vì:
1. Flexibility → admin có thể chọn cách phù hợp với số lượng URLs
2. Better UX → file upload cho bulk, textarea cho quick tests
3. Không tốn nhiều effort → file upload chỉ cần FileReader API

**Hệ quả:**
- UI phức tạp hơn một chút (2 input methods)
- Cần validate file format (.txt only)
- Cần handle file reading errors

---

### [ADR-6] Confirmation Dialog cho Bulk Operations — 27/04/2026

**Bối cảnh:** Crawl 3,000+ URLs tốn thời gian (~2-3 giờ) và OpenAI API costs. Cần prevent accidental triggers.

**Các lựa chọn đã xem xét:**
- **Option A - No confirmation**: Click là chạy ngay
  - Pros: Nhanh
  - Cons: Dễ nhầm lẫn, waste resources nếu trigger nhầm
- **Option B - Simple confirm()**: Browser native dialog
  - Pros: Đơn giản, không cần code UI
  - Cons: Ugly, không hiển thị được thông tin chi tiết
- **Option C - Custom modal với preview**:
  - Pros: Professional, hiển thị số lượng + estimated time
  - Cons: Cần code thêm component

**Quyết định:** Chọn Option C (Custom modal) vì:
1. Better UX → user biết rõ sẽ xảy ra gì
2. Prevent mistakes → hiển thị estimated time giúp user aware về cost
3. Professional → phù hợp với admin dashboard standards

**Hệ quả:**
- Cần implement modal component với animation
- Cần calculate estimated time (số URLs × average time per URL)
- Thêm 1 step vào workflow nhưng improve safety

---

### [ADR-7] Tái cấu trúc và Chuẩn hóa Tài liệu (Documentation Restructuring) — 11/05/2026

**Bối cảnh:** Tài liệu dự án bị phân tán ở nhiều file MD khác nhau trong `backend/` và thư mục gốc, gây khó khăn cho việc cài đặt và nắm bắt kiến trúc.

**Các lựa chọn đã xem xét:**
- **Option A - Giữ nguyên**: Dễ gây nhầm lẫn cho người mới.
- **Option B - Hợp nhất toàn bộ vào README**: Khiến file README quá dài và khó theo dõi.
- **Option C - Tách biệt theo vai trò (User/Dev/Architecture)**: Chuyên nghiệp, dễ quản lý và cập nhật.

**Quyết định:** Chọn Option C. Tạo mới `ARCHITECTURE.md` và `SETUP_GUIDE.md` bằng tiếng Việt làm tài liệu chính. Rút gọn `README.md` làm trang điều hướng.

**Hệ quả:** 
- Người dùng dễ dàng tìm thấy thông tin cần thiết.
- Dễ dàng bảo trì tài liệu khi hệ thống thay đổi.
- Xóa bỏ các file cũ dư thừa để làm sạch codebase.

---

## Phân công

### Sprint 1 — 30/03/2026 → 04/04/2026

| Task | Người làm | Deadline | Trạng thái |
|---|---|---|---|
| Thiết lập kênh làm việc và quy trình phối hợp | Cả nhóm | 04/04 | ✅ Xong |
| Liệt kê các lĩnh vực quan tâm (RAG, AI Agents) | Cả nhóm | 04/04 | ✅ Xong |
| Market Research: Thu thập dữ liệu về pain points | Cả nhóm | 04/04 | ✅ Xong |
| Chốt đề tài với coach/mentor | Cả nhóm | 04/04 | ✅ Xong |

---

### Sprint 2 — 06/04/2026 → 10/04/2026

| Task | Người làm | Deadline | Trạng thái |
|---|---|---|---|
| Nghiên cứu feature, metrics đánh giá sản phẩm | Kiệt (232) | 10/04 | ✅ Xong |
| Setup Git, môi trường làm việc | Kiệt (232) | 10/04 | ✅ Xong |
| Lên kế hoạch khảo sát pain point | Kiệt (232) | 10/04 | ✅ Xong |
| Viết nháp prompt cho Skill Parser, Normalizer | Kiệt (232) | 10/04 | ✅ Xong |
| Thu hẹp scope MVP, xác định cách đo giá trị | Kiệt (233) | 10/04 | ✅ Xong |
| Xây dựng success metrics, phác thảo user flow | Kiệt (233) | 10/04 | ✅ Xong |
| Nghiên cứu recommendation engine | Kiệt (233) | 10/04 | ✅ Xong |
| Phân tích bài toán, đề xuất feature MVP/Phase 2 | Bách (234) | 10/04 | ✅ Xong |
| Thiết kế kiến trúc sơ bộ, database sơ bộ | Bách (234) | 10/04 | ✅ Xong |
| Crawl và phân tích dữ liệu | Bách (234) | 10/04 | ✅ Xong |

---

### Sprint 3 — 13/04/2026 → 17/04/2026

| Task | Người làm | Deadline | Trạng thái |
|---|---|---|---|
| Chỉnh sửa tối ưu prompt, bổ sung edge case | Kiệt (232) | 17/04 | ✅ Xong |
| Viết technical report cho prompt (Skill Parser) | Kiệt (232) | 17/04 | ✅ Xong |
| Rà soát test, xây dựng golden dataset | Kiệt (232) | 17/04 | ✅ Xong |
| Chỉnh sửa UI (font, màu sắc, layout), design AI | Kiệt (233) | 17/04 | ✅ Xong |
| Tái cấu trúc frontend (không dùng React), login | Kiệt (233) | 17/04 | ✅ Xong |
| Chuẩn bị tích hợp frontend với backend | Kiệt (233) | 17/04 | ✅ Xong |
| Phân tích tối ưu thuật toán, thử nghiệm skill gap | Bách (234) | 17/04 | ✅ Xong |
| Fix các lỗi phát sinh trong quá trình phát triển | Bách (234) | 17/04 | ✅ Xong |

---

### Sprint 4 — 20/04/2026 → 24/04/2026

| Task | Người làm | Deadline | Trạng thái |
|---|---|---|---|
| Cải thiện prompt, thêm test/edge case, tối ưu token | Kiệt (232) | 24/04 | ✅ Xong |
| Nghiên cứu benchmark | Kiệt (232) | 24/04 | ✅ Xong |
| Hoàn thiện UI, fix Google Font, đồng bộ component | Kiệt (233) | 24/04 | ✅ Xong |
| Fix bug, tối ưu backend, hoàn thiện feature | Bách (234) | 24/04 | ✅ Xong |
| Xây dashboard theo dõi token | Bách (234) | 24/04 | ✅ Xong |
| Thêm fallback LLM, gửi email khi quá tải | Bách (234) | 24/04 | ✅ Xong |

---

### Sprint 5 — 27/04/2026 → 02/05/2026

| Task | Người làm | Deadline | Trạng thái |
|---|---|---|---|
| Fix test case, performance test bằng Locust | Kiệt (232) | 02/05 | ✅ Xong |
| Cải tiến prompt cho case đặc biệt (0 year exp) | Kiệt (232) | 02/05 | ✅ Xong |
| Test và đánh giá prompt mới trên synthetic data | Kiệt (232) | 02/05 | ✅ Xong |
| Cải thiện UI consistency, refactor color design | Kiệt (233) | 02/05 | ✅ Xong |
| Hoàn thiện UI design, thử nghiệm library mới | Kiệt (233) | 02/05 | ✅ Xong |
| Fix bug production, xử lý bug test | Bách (234) | 02/05 | ✅ Xong |
| Tối ưu hệ thống từ kết quả performance test | Bách (234) | 02/05 | ✅ Xong |
| Refactor backend, build version check accuracy | Bách (234) | 02/05 | ✅ Xong |

---

### Sprint 6 — 04/05/2026 → 08/05/2026

| Task | Người làm | Deadline | Trạng thái |
|---|---|---|---|
| Hoàn thiện pitching, slide trình bày | Kiệt (232) | 08/05 | ✅ Xong |
| Quay và chỉnh sửa demo sản phẩm | Kiệt (232) | 08/05 | ✅ Xong |
| Thiết kế UI, logo, tối ưu landing page | Kiệt (233) | 08/05 | ✅ Xong |
| Hoàn thiện giao diện, thực hiện ragas prompt test | Kiệt (233) | 08/05 | ✅ Xong |
| Hoàn thiện hệ thống quản lý prompt tùy chỉnh | Bách (234) | 08/05 | ✅ Xong |
| Benchmark, test và tối ưu backend | Bách (234) | 08/05 | ✅ Xong |
| Cập nhật tài liệu setup và kiến trúc hệ thống | Bách (234) | 08/05 | ✅ Xong |

---

### Sprint 7 — 11/05/2026 → 15/05/2026

| Task | Người làm | Deadline | Trạng thái |
|---|---|---|---|
| Hoàn thiện demo, slide pitching, video demo | Kiệt (232) | 15/05 | ✅ Xong |
| Kiểm tra các mục cần submit | Kiệt (232) | 15/05 | ✅ Xong |
| Hoàn thiện landing page, rà soát checklist | Kiệt (233) | 15/05 | ✅ Xong |
| Review, chuẩn hóa tài liệu kỹ thuật, sửa URL | Bách (234) | 15/05 | ✅ Xong |
| Setup môi trường production, check độ ổn định | Bách (234) | 15/05 | ✅ Xong |
| Tham gia review cuối cùng hệ thống | Bách (234) | 15/05 | ✅ Xong |

