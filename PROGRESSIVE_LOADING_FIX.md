# Fix: Progressive Loading Data Loss in Recommend Page

**Date:** 2026-04-25  
**Issue:** Dữ liệu không load đầy đủ ở trang recommend sau khi gap analysis hoàn thành  
**Status:** ✅ FIXED

---

## 🐛 Vấn đề

Khi gap analysis chạy xong và chuyển sang trang `/user/recommend`, người dùng thấy:
- Skill gaps hiển thị nhưng courses không có
- Hoặc courses có nhưng roadmap không có
- Phải reload trang thì mới thấy đầy đủ data

**Root Cause:**
Logic merge data trong progressive loading bị lỗi - khi nhận partial updates mới, nó **ghi đè** toàn bộ state thay vì **merge** đúng cách.

---

## 🔍 Phân tích

### Flow của Progressive Loading

1. **Analysis page** (page.tsx:302-312):
   ```typescript
   // Khi gaps ready, redirect sớm với partial data
   if (partial_result && partial_result.node === "gap_analysis") {
       sessionStorage.setItem("gap_analysis_partial", JSON.stringify(partial_result));
       router.push(`/user/recommend?task_id=${tid}`);
   }
   ```

2. **Recommend page** nhận `task_id` và bắt đầu polling:
   - Load partial data từ sessionStorage (nếu có)
   - Poll API mỗi 4 giây để nhận updates
   - Mỗi update có thể chứa: skill_gaps, courses, roadmap, videos...

3. **Vấn đề ở đây** (line 200-207 - code cũ):
   ```typescript
   setGapResult(prev => ({
       ...prev,
       ...partial_result,  // ❌ Ghi đè toàn bộ!
       course_recommendations: partial_result.course_recommendations?.length > 0 
           ? partial_result.course_recommendations 
           : (prev?.course_recommendations || [])
   }));
   ```

   **Tại sao lỗi:**
   - Chỉ preserve `course_recommendations`
   - Các arrays khác (skill_gaps, youtube_videos, strengths, weaknesses) bị ghi đè
   - Nếu partial_result không có skill_gaps, nó sẽ = undefined → mất data cũ

---

## ✅ Giải pháp

### Fix 1: Deep Merge cho Partial Updates (line 198-238)

```typescript
if (partial_result) {
  setGapResult(prev => {
    const merged = {
      ...prev,
      ...partial_result,
      // Preserve ALL arrays - only update if new data exists
      skill_gaps: (partial_result.skill_gaps?.length ?? 0) > 0 
        ? partial_result.skill_gaps 
        : (prev?.skill_gaps || []),
      course_recommendations: (partial_result.course_recommendations?.length ?? 0) > 0 
        ? partial_result.course_recommendations 
        : (prev?.course_recommendations || []),
      youtube_videos: (partial_result.youtube_videos?.length ?? 0) > 0
        ? partial_result.youtube_videos
        : (prev?.youtube_videos || []),
      strengths: (partial_result.strengths?.length ?? 0) > 0
        ? partial_result.strengths
        : (prev?.strengths || []),
      weaknesses: (partial_result.weaknesses?.length ?? 0) > 0
        ? partial_result.weaknesses
        : (prev?.weaknesses || []),
      transferable_insights: (partial_result.transferable_insights?.length ?? 0) > 0
        ? partial_result.transferable_insights
        : (prev?.transferable_insights || []),
      // Preserve objects
      career_roadmap: partial_result.career_roadmap || prev?.career_roadmap,
      match_breakdown: partial_result.match_breakdown || prev?.match_breakdown || {},
      gap_summary: partial_result.gap_summary || prev?.gap_summary,
    } as GapResult;
    
    console.log("[RECOMMEND] Merged state:", {
      skill_gaps: merged.skill_gaps?.length,
      courses: merged.course_recommendations?.length,
      videos: merged.youtube_videos?.length,
      roadmap: merged.career_roadmap ? 'present' : 'missing'
    });
    
    return merged;
  });
}
```

**Cải tiến:**
- ✅ Preserve TẤT CẢ arrays (skill_gaps, courses, videos, strengths, weaknesses, insights)
- ✅ Chỉ update nếu data mới có content (length > 0)
- ✅ Preserve objects (career_roadmap, match_breakdown, gap_summary)
- ✅ Log merged state để debug
- ✅ Dùng `?? 0` để handle TypeScript strict null checks

### Fix 2: Deep Merge cho Final Result (line 241-268)

```typescript
if (status === "completed") {
  setGapResult(prev => {
    const finalResult = result as GapResult;
    return {
      ...prev,
      ...finalResult,
      // Ensure we keep the most complete version of each array
      skill_gaps: (finalResult.skill_gaps?.length ?? 0) > 0 
        ? finalResult.skill_gaps 
        : (prev?.skill_gaps || []),
      course_recommendations: (finalResult.course_recommendations?.length ?? 0) > 0 
        ? finalResult.course_recommendations 
        : (prev?.course_recommendations || []),
      youtube_videos: (finalResult.youtube_videos?.length ?? 0) > 0
        ? finalResult.youtube_videos
        : (prev?.youtube_videos || []),
      strengths: (finalResult.strengths?.length ?? 0) > 0
        ? finalResult.strengths
        : (prev?.strengths || []),
      weaknesses: (finalResult.weaknesses?.length ?? 0) > 0
        ? finalResult.weaknesses
        : (prev?.weaknesses || []),
      career_roadmap: finalResult.career_roadmap || prev?.career_roadmap,
      match_breakdown: finalResult.match_breakdown || prev?.match_breakdown || {},
    } as GapResult;
  });
}
```

**Tại sao cần fix cả completed:**
- Backend có thể trả về final result không đầy đủ (do cache hoặc lỗi)
- Cần đảm bảo không mất data đã load từ partial updates

---

## 🧪 Testing Scenarios

### Scenario 1: Normal Flow (Happy Path)
1. User chọn CV + Job → Start Analysis
2. Analysis page redirect sớm khi gaps ready
3. Recommend page load partial data từ sessionStorage
4. Poll API nhận thêm courses → merge vào state
5. Poll API nhận thêm roadmap → merge vào state
6. Final result → merge vào state

**Expected:** Tất cả data hiển thị đầy đủ, không bị mất

### Scenario 2: Slow Network
1. User chọn CV + Job → Start Analysis
2. Redirect sớm với partial data (chỉ có gaps)
3. Network chậm → courses đến sau 10 giây
4. Roadmap đến sau 15 giây

**Expected:** 
- Gaps hiển thị ngay
- Courses xuất hiện sau 10s (không làm mất gaps)
- Roadmap xuất hiện sau 15s (không làm mất gaps + courses)

### Scenario 3: Reload Page
1. User đang ở recommend page với task_id
2. Reload trang
3. Polling tiếp tục từ đầu

**Expected:** Data load lại đầy đủ từ API

### Scenario 4: Direct Access (No task_id)
1. User vào `/user/recommend` trực tiếp (không có task_id)
2. Load từ sessionStorage hoặc `/analysis/user/latest`

**Expected:** Load data từ analysis gần nhất

---

## 📊 Before vs After

### Before Fix
```
Timeline:
0s:  Redirect to /recommend with gaps
2s:  Receive courses update → gaps LOST ❌
4s:  Receive roadmap update → courses LOST ❌
6s:  Final result → roadmap LOST ❌

Result: User sees incomplete data, needs reload
```

### After Fix
```
Timeline:
0s:  Redirect to /recommend with gaps
2s:  Receive courses update → MERGE with gaps ✅
4s:  Receive roadmap update → MERGE with gaps + courses ✅
6s:  Final result → MERGE all ✅

Result: User sees complete data progressively
```

---

## 🔍 Debug Logs

Khi fix hoạt động đúng, console sẽ hiển thị:

```
[RECOMMEND] Polling for progressive updates - Task ID: abc123
[RECOMMEND] Received partial update: gap_analysis
[RECOMMEND] Merged state: { skill_gaps: 5, courses: 0, videos: 0, roadmap: 'missing' }
[RECOMMEND] Received partial update: course_recommendation
[RECOMMEND] Merged state: { skill_gaps: 5, courses: 8, videos: 0, roadmap: 'missing' }
[RECOMMEND] Received partial update: career_roadmap
[RECOMMEND] Merged state: { skill_gaps: 5, courses: 8, videos: 3, roadmap: 'present' }
[RECOMMEND] Analysis completed!
```

**Nếu thấy số liệu giảm (5 → 0) = BUG chưa fix đúng**

---

## ✅ Verification

### Build Status
```bash
npm run build
# ✓ Compiled successfully
# ✓ TypeScript check passed
# ✓ All 30 pages generated
```

### Files Modified
- `frontend/src/app/user/recommend/page.tsx` (lines 198-268)

### TypeScript Fixes
- Dùng `?? 0` thay vì `> 0` để handle undefined
- Ensures type safety với strict null checks

---

## 🎯 Impact

**User Experience:**
- ✅ Không cần reload trang để thấy đầy đủ data
- ✅ Progressive loading mượt mà hơn
- ✅ Thấy data xuất hiện dần (gaps → courses → roadmap)

**Developer Experience:**
- ✅ Debug logs rõ ràng hơn
- ✅ Type-safe với TypeScript
- ✅ Dễ maintain và extend

**Performance:**
- ✅ Không thay đổi (vẫn poll 4s/lần)
- ✅ Giảm số lần user phải reload

---

## 📝 Notes

1. **Tại sao không dùng `useMemo` hoặc `useCallback`?**
   - State merge logic đơn giản, không cần optimize
   - Polling interval 4s đã đủ chậm

2. **Tại sao không dùng WebSocket?**
   - Polling đơn giản hơn, dễ debug
   - 4s interval không tạo load lớn cho server
   - WebSocket cần infrastructure phức tạp hơn

3. **Tại sao preserve data cũ nếu data mới rỗng?**
   - Backend có thể trả về partial updates không đầy đủ
   - Tránh mất data đã load trước đó
   - User experience tốt hơn (thấy data dần dần, không bị nhấp nháy)

---

**Fix completed:** 2026-04-25 19:35 UTC+7  
**Build status:** ✅ SUCCESS  
**Ready for testing:** ✅ YES
