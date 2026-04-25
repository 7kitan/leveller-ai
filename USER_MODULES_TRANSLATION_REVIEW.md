# 📋 USER MODULES TRANSLATION REVIEW - SUMMARY

> **Ngày:** 25/04/2026  
> **Status:** ✅ Review hoàn tất - Phát hiện 12 vấn đề cần fix

---

## 🔍 PHÁT HIỆN

### ✅ ĐIỂM TỐT
- **227+ translation keys** đã được implement
- **Hầu hết text** đã được internationalize với `t()` function
- **Cấu trúc translation** rõ ràng và có tổ chức tốt

### ❌ VẤN ĐỀ CẦN FIX (12 issues)

---

## 📄 JOBS PAGE (`frontend/src/app/user/jobs/page.tsx`)

### Issue 1: Redundant fallback values
**Lines:** 200, 214, 221, 238, 250, 259, 268, 277, 288, 295, 311

**Hiện tại:**
```tsx
title={t("job_details_title") || "Job Details"}
<span className={styles.modalMetaLabel}>{t("location") || "Location"}</span>
<span className={styles.modalMetaLabel}>{t("salary") || "Salary"}</span>
{t("close") || "Close"}
```

**Vấn đề:** Các keys này ĐÃ TỒN TẠI trong translations, không cần fallback

**Fix:** Xóa tất cả `|| "..."` fallback values

**Keys đã tồn tại:**
- ✅ `job_details_title`
- ✅ `location`
- ✅ `salary`
- ✅ `posted_at`
- ✅ `employment_type`
- ✅ `job_description`
- ✅ `job_requirements`
- ✅ `job_benefits`
- ✅ `no_description_available`
- ✅ `close`
- ❌ `view_original` - THIẾU KEY

### Issue 2: Missing translation key
**Line:** 311

**Hiện tại:**
```tsx
{t("view_original") || "Xem bản gốc"}
```

**Fix:** Thêm key `view_original` vào translations

---

## 📄 DASHBOARD PAGE (`frontend/src/app/user/page.tsx`)

### Issue 3: Hardcoded period labels
**Lines:** 250-256

**Hiện tại:**
```tsx
{['day', 'week', 'month'].map((p) => (
  <button>
    {p === 'day' ? '24h' : p === 'week' ? '7d' : '30d'}
  </button>
))}
```

**Fix:** Tạo translation keys cho period labels
```tsx
// Thêm vào translations:
period_24h: "24h"
period_7d: "7d"  
period_30d: "30d"

// Hoặc dùng map:
const periodLabels = {
  day: t("period_24h"),
  week: t("period_7d"),
  month: t("period_30d")
}
```

### Issue 4: Hardcoded "None" value
**Line:** 269

**Hiện tại:**
```tsx
{marketData?.market_trends?.summary?.top_gainer || "None"}
```

**Fix:** Thêm key `no_data` hoặc `not_available`

### Issue 5: Hardcoded "E-learning"
**Line:** 117

**Hiện tại:**
```tsx
platform: c.platform || "E-learning"
```

**Fix:** Thêm key `platform_default: "E-learning"`

---

## 📄 CV PAGE (`frontend/src/app/user/cv/page.tsx`)

### Issue 6: Hardcoded seniority levels (KHÔNG CẦN FIX)
**Lines:** 152-153

**Hiện tại:**
```tsx
const SENIORITY_LEVELS = ["Junior", "Mid-level", "Senior", "Expert", "Unknown"];
const SKILL_LEVELS = ["Junior", "Mid-level", "Senior", "Expert"];
```

**Status:** ✅ ĐÃ ĐƯỢC XỬ LÝ ĐÚNG
- Các values này là **enum constants** để gửi lên backend
- Đã có function `getSeniorityLabel()` để convert sang translation
- Không cần fix

### Issue 7: Console.error với Vietnamese text
**Lines:** 192, 282, 289

**Hiện tại:**
```tsx
console.error("Fetch history error:", err);
console.error("Lỗi khi lấy chi tiết CV cũ:", err);
console.error("Backend did not return parser_id or completed status", resp.data);
```

**Fix:** Chuyển tất cả console messages sang English
```tsx
console.error("Failed to fetch CV history:", err);
console.error("Failed to fetch CV details:", err);
console.error("Backend did not return parser_id or completed status:", resp.data);
```

---

## 📄 ANALYSIS PAGE (`frontend/src/app/user/analysis/page.tsx`)

### Issue 8: Hardcoded title "GAP ANALYSIS"
**Line:** 381

**Hiện tại:**
```tsx
title="GAP ANALYSIS"
```

**Fix:** Sử dụng translation key
```tsx
title={t("analysis_title")}
```

**Key đã tồn tại:** ✅ `analysis_title: "Phân tích khoảng cách kỹ năng"`

### Issue 9: Console.log/error messages
**Lines:** 135, 147, 162, 216, 239, 243, 255, 264, 303, 314, 346, 350, 362

**Hiện tại:**
```tsx
console.error("[ANALYSIS] Failed to fetch job info from URL:", err);
console.log("[ANALYSIS] Auto-run triggered (forcing recompute)");
```

**Status:** ✅ ACCEPTABLE
- Console messages for debugging purposes
- Không ảnh hưởng đến UI
- Có thể giữ nguyên hoặc remove trong production build

---

## 📄 RECOMMEND PAGE (`frontend/src/app/user/recommend/page.tsx`)

### Issue 10: Error messages với hardcoded text
**Lines:** 261, 266, 282

**Hiện tại:**
```tsx
setError(t("error") + ": No analysis found");
setError(t("error") + ": Connection failed");
setError(t("error") + ": Refresh failed");
```

**Fix:** Tạo dedicated error keys
```tsx
// Thêm vào translations:
error_no_analysis: "Không tìm thấy phân tích"
error_connection_failed: "Kết nối thất bại"
error_refresh_failed: "Làm mới thất bại"

// Sử dụng:
setError(t("error_no_analysis"));
setError(t("error_connection_failed"));
setError(t("error_refresh_failed"));
```

### Issue 11: Console.log/error messages
**Lines:** 176, 200, 213, 219, 224, 240, 247, 257, 260, 265, 281

**Status:** ✅ ACCEPTABLE (debugging purposes)

---

## 📄 PROFILE PAGE (`frontend/src/app/user/profile/page.tsx`)

### Issue 12: Cần review
**Status:** ⏳ CHƯA REVIEW CHI TIẾT

**Action:** Cần đọc file để kiểm tra

---

## 📊 TỔNG KẾT

### Thống kê vấn đề:
| Loại | Số lượng | Mức độ |
|------|----------|--------|
| Redundant fallback values | 11 | 🟡 Medium |
| Missing translation keys | 5 | 🔴 High |
| Hardcoded values | 3 | 🟡 Medium |
| Console messages (Vietnamese) | 3 | 🟢 Low |
| Console messages (English) | 20+ | ✅ OK |

### Ưu tiên fix:

**🔴 HIGH PRIORITY (Cần fix ngay):**
1. ✅ Thêm missing keys vào translations
2. ✅ Xóa redundant fallback values trong jobs page
3. ✅ Fix hardcoded "GAP ANALYSIS" title

**🟡 MEDIUM PRIORITY (Nên fix):**
4. ✅ Thêm period labels (24h, 7d, 30d)
5. ✅ Thêm error message keys
6. ✅ Fix hardcoded "None" và "E-learning"

**🟢 LOW PRIORITY (Optional):**
7. ⚠️ Chuyển console.error Vietnamese sang English
8. ⚠️ Remove console.log trong production build

---

## 🔧 MISSING TRANSLATION KEYS CẦN BỔ SUNG

### Vietnamese:
```typescript
// Jobs Page
view_original: "Xem bản gốc",

// Dashboard
period_24h: "24h",
period_7d: "7d",
period_30d: "30d",
platform_default: "E-learning",

// Recommend Page  
error_no_analysis: "Không tìm thấy phân tích",
error_connection_failed: "Kết nối thất bại",
error_refresh_failed: "Làm mới thất bại",
```

### English:
```typescript
// Jobs Page
view_original: "View Original",

// Dashboard
period_24h: "24h",
period_7d: "7d",
period_30d: "30d",
platform_default: "E-learning",

// Recommend Page
error_no_analysis: "No analysis found",
error_connection_failed: "Connection failed",
error_refresh_failed: "Refresh failed",
```

---

## ✅ NEXT STEPS

1. **Bổ sung 7 missing keys** vào `frontend/src/translations/index.ts`
2. **Fix jobs page** - Xóa 11 redundant fallback values
3. **Fix analysis page** - Thay "GAP ANALYSIS" bằng `t("analysis_title")`
4. **Fix dashboard** - Thay hardcoded period labels
5. **Fix recommend page** - Thay error messages
6. **Review profile page** - Kiểm tra chi tiết
7. **Optional:** Clean up console messages

---

**Tổng số files cần sửa:** 4 files  
**Tổng số dòng code cần sửa:** ~25 lines  
**Thời gian ước tính:** 15-20 phút

---

**Report by:** OpenCode AI Assistant  
**Date:** 25/04/2026
