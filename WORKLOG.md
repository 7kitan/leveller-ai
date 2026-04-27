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

## Ví dụ

### [ADR-1] Dùng TypeScript thay vì Python — 30/03/2026

**Bối cảnh:** Cả nhóm cần chọn 1 ngôn ngữ chính để xây dựng agent. Có 2 thành viên quen Python, 1 thành viên quen TypeScript.

**Các lựa chọn đã xem xét:**
- **Python**: Ecosystem ML tốt hơn, syntax đơn giản, thành viên quen hơn.
- **TypeScript**: Type safety, dễ refactor khi project lớn, nhiều library AI mới ra bản TS trước.

**Quyết định:** Chọn TypeScript vì project này focus vào agent architecture, không cần ML library nặng. Type safety sẽ giúp bắt lỗi sớm hơn khi codebase phình ra.

**Hệ quả:** 2 thành viên Python cần học TypeScript cơ bản (ước tính 1 tuần). Sẽ không dùng được `langchain` Python trực tiếp.

---

### [ADR-2] Lưu conversation history bằng file JSON — 03/04/2026

**Bối cảnh:** Agent cần nhớ context giữa các lần chạy. Cần chọn storage.

**Các lựa chọn đã xem xét:**
- **In-memory array**: Đơn giản nhất nhưng mất khi restart.
- **File JSON**: Persistent, không cần setup, dễ inspect bằng tay.
- **SQLite**: Có thể query, tốt cho production nhưng overkill cho prototype.
- **Redis**: Fast nhưng cần chạy thêm service.

**Quyết định:** File JSON cho giai đoạn prototype. Thiết kế interface `MemoryStore` để sau này swap sang SQLite không cần sửa logic agent.

**Hệ quả:** Không query được theo thời gian hay user. Chấp nhận được ở giai đoạn này.

---

### Sprint 1 — 31/03 → 06/04/2026

| Task | Người làm | Deadline | Trạng thái |
|---|---|---|---|
| Setup TypeScript project + CI | Văn A | 01/04 | ✅ Xong |
| Implement agent loop cơ bản | Thị B | 02/04 | ✅ Xong |
| Tool: `search_web` (Brave API) | Văn C | 03/04 | ✅ Xong |
| Tool: `read_file`, `write_file` | Thị B | 05/04 | ✅ Xong |
| Conversation memory (JSON) | Văn A | 06/04 | ✅ Xong |
| README + setup docs | Văn C | 06/04 | ✅ Xong |

---

### Sprint 2 — 07/04 → 13/04/2026

| Task | Người làm | Deadline | Trạng thái |
|---|---|---|---|
| Fix infinite loop: thêm `max_iterations` | Thị B | 08/04 | 🔄 Đang làm |
| Tool: `run_tests` (chạy pytest) | Văn C | 10/04 | ⏳ Chờ |
| Sliding window memory | Văn A | 09/04 | ⏳ Chờ |
| Demo prep + slides | Cả nhóm | 13/04 | ⏳ Chờ |

---

### Brainstorm: Tính năng cho demo — 05/04/2026

**Câu hỏi:** Demo tuần tới nên show gì để ấn tượng nhất trong 5 phút?

**Các ý tưởng:**
- **Ý tưởng 1 (Văn A):** Cho agent đọc 1 file Python có bug, tự fix, rồi chạy test để verify. Trực quan, dễ hiểu.
- **Ý tưởng 2 (Thị B):** Agent tự build 1 tính năng nhỏ từ mô tả bằng tiếng Việt. Show khả năng hiểu ngôn ngữ tự nhiên.
- **Ý tưởng 3 (Văn C):** Agent review PR, comment vào từng dòng code có vấn đề. Gần với use case thực tế nhất.

**Pros/Cons:**
| Ý tưởng | Pros | Cons |
|---|---|---|
| Fix bug | Dễ làm, chắc chắn chạy được | Ít "wow" hơn |
| Build từ mô tả | Ấn tượng nhất | Có thể fail nếu prompt phức tạp |
| Review PR | Thực tế, liên quan trực tiếp đến khóa học | Cần setup GitHub webhook |

**Kết luận:** Chọn ý tưởng 1 (fix bug) cho demo chính vì đảm bảo. Nếu còn thời gian sẽ show thêm ý tưởng 2 như bonus.

---

### Bug quan trọng: Tool call loop vô hạn — 04/04/2026

**Triệu chứng:** Agent gọi `search_web` liên tục không dừng khi tool trả về lỗi network.

**Root cause:** Không có stop condition khi tool raise exception. Agent nhận `"error": "timeout"` nhưng interpret là cần thử lại.

**Fix:** Thêm 2 điều kiện dừng:
1. `max_iterations = 10` — hard stop sau 10 vòng
2. Nếu tool trả về lỗi 3 lần liên tiếp → dừng và báo user

**Code thay đổi:** `src/agent.ts` lines 45-67

**Học được:** Luôn thiết kế stop condition trước khi implement retry logic.

---

## Quyết định kỹ thuật - Tuần 3

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

## Sprint 3 — 21/04 → 27/04/2026

(Các công việc chi tiết đã được chuyển vào hệ thống quản lý task hoặc JOURNAL.md)

---


---
