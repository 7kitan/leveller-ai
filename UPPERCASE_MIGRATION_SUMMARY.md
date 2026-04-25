# System Settings Migration: UPPERCASE Standardization

## ✅ Completed Tasks

### 1. Security Cleanup: Removed X-Is-Admin Header
**Problem:** Frontend was sending `X-Is-Admin` header causing CORS 400 errors.

**Solution:**
- ✅ Removed `X-Is-Admin` from backend CORS `allowed_headers` (gateway/main.py)
- ✅ Removed all 26 occurrences of `X-Is-Admin` from frontend code:
  - admin/page.tsx (1)
  - admin/settings/page.tsx (2)
  - admin/youtube/page.tsx (3)
  - admin/jobs/page.tsx (7)
  - admin/jobs/import/page.tsx (3)
  - admin/cvs/page.tsx (2)
  - admin/courses/page.tsx (4)
  - admin/courses/import/page.tsx (4)
- ✅ Rebuilt gateway container
- ✅ Verified all admin endpoints work without X-Is-Admin

**Security Model:**
```
Frontend → JWT Token → Gateway (verify & extract role) → Inject X-User-Role → Backend
```
Backend only trusts `X-User-Role` from gateway (cryptographically verified from JWT).

---

### 2. Settings Keys Migration: lowercase → UPPERCASE

**Problem:** Inconsistent naming between database keys (lowercase) and environment variables (UPPERCASE).

**Solution:**
- ✅ Migrated all 22 system_settings keys to UPPERCASE in database
- ✅ Updated `config_manager.get_setting()` to auto-normalize keys to UPPERCASE
- ✅ Updated admin API endpoints to auto-normalize keys to UPPERCASE
- ✅ Cleared Redis cache to remove old lowercase keys
- ✅ Rebuilt gateway and admin-service containers

**Migration Results:**
```
Before → After
--------------
ai_model → AI_MODEL
chandra_api_url → CHANDRA_API_URL
chandra_api_key → CHANDRA_API_KEY
cv_parser_strategy → CV_PARSER_STRATEGY
daily_analysis_limit → DAILY_ANALYSIS_LIMIT
fallback_ai_model → FALLBACK_AI_MODEL
gap_llm_model → GAP_LLM_MODEL
gap_pii_masking → GAP_PII_MASKING
gap_redis_cache → GAP_REDIS_CACHE
gap_vector_sim_threshold → GAP_VECTOR_SIM_THRESHOLD
llm_provider → LLM_PROVIDER
maintenance_duration → MAINTENANCE_DURATION
maintenance_mode → MAINTENANCE_MODE
ocr_dpi → OCR_DPI
queue_threshold → QUEUE_THRESHOLD
similarity_threshold → SIMILARITY_THRESHOLD
system_broadcast → SYSTEM_BROADCAST
system_log_ttl_days → SYSTEM_LOG_TTL_DAYS
topcv_crawl_enabled → TOPCV_CRAWL_ENABLED
use_llm_gap_agent_v3 → USE_LLM_GAP_AGENT_V3
user_daily_token_limit → USER_DAILY_TOKEN_LIMIT
user_token_limit → USER_TOKEN_LIMIT
```

**Code Changes:**

1. **shared/config_utils.py:**
```python
@staticmethod
def get_setting(key: str, default: Any = None, cast: Optional[Type[T]] = None) -> Any:
    # Normalize key to UPPERCASE for consistency
    key = key.upper()
    
    # 1. Check Redis Cache
    # 2. Check Database
    # 3. Check Environment Variables (already UPPERCASE)
    # 4. Fallback to default
```

2. **services/admin_service/main.py:**
```python
@app.patch("/admin/settings/{key}")
def admin_update_setting(key: str, ...):
    # Normalize key to UPPERCASE
    key = key.upper()
    # ... rest of logic
```

**Benefits:**
- ✅ Consistent naming across database, Redis, and environment variables
- ✅ Developers can use lowercase in code: `get_setting('chandra_api_url')` → auto-converts to `CHANDRA_API_URL`
- ✅ Admin UI can send lowercase keys → auto-converts to UPPERCASE
- ✅ Easier to match with environment variables (no case confusion)

---

## 🔍 Verification Tests

### Test 1: Config Manager Auto-Normalization
```python
# Input: lowercase
config_manager.get_setting('chandra_api_url')
# → Reads from DB key: CHANDRA_API_URL
# → Returns: "https://milwaukee-voted-employer-annually.trycloudflare.com/tasks/ocr"

# Input: UPPERCASE
config_manager.get_setting('CHANDRA_API_URL')
# → Same result
```

### Test 2: Admin API Auto-Normalization
```bash
# PATCH with lowercase key
curl -X PATCH /admin/settings/test_lowercase_key -d '{"value": "test123"}'
# → Saves to DB as: TEST_LOWERCASE_KEY

# Verify in database
SELECT key FROM system_settings WHERE key = 'TEST_LOWERCASE_KEY';
# → TEST_LOWERCASE_KEY (UPPERCASE)
```

### Test 3: Worker Reading Settings
```python
# Worker container test
config_manager.get_setting('cv_parser_strategy')  # lowercase input
# → Returns: "chandra" (from DB key: CV_PARSER_STRATEGY)

config_manager.get_setting('GAP_LLM_MODEL')  # UPPERCASE input
# → Returns: "gpt-4o-mini" (from DB key: GAP_LLM_MODEL)
```

### Test 4: Redis Cache
```bash
# After reading settings, Redis cache uses UPPERCASE keys
redis-cli KEYS "advisor:*"
# → advisor:CHANDRA_API_URL
# → advisor:CHANDRA_API_KEY
# → advisor:CV_PARSER_STRATEGY
# (All UPPERCASE)
```

---

## 📊 Current System Status

### Database Settings (22 total)
```sql
SELECT key FROM system_settings ORDER BY key;
```
All keys are now UPPERCASE ✓

### Redis Cache
- DB 0: Config cache (UPPERCASE keys)
- DB 1: Celery broker
- DB 2: Result cache
- DB 3: LLM cache

### Services Status
```
✅ advisor_gateway_prod - Up (healthy)
✅ advisor_admin_prod - Up (healthy)
✅ advisor_worker_cv_parser_prod - Up
✅ advisor_worker_analysis_prod - Up
✅ advisor_auth_prod - Up (healthy)
✅ advisor_analysis_prod - Up (healthy)
✅ advisor_cv_prod - Up (healthy)
✅ advisor_jd_prod - Up (healthy)
✅ advisor_recommender_prod - Up (healthy)
✅ advisor_db_prod - Up (healthy)
✅ advisor_redis_prod - Up
```

---

## 🚨 Remaining Issue: Chandra OCR Service

**Status:** ❌ NOT RUNNING

**Problem:**
- Settings are configured correctly in database
- Worker is configured to use Chandra strategy
- BUT: Chandra OCR service is not running
- Cloudflare tunnel URL is not accessible

**Evidence:**
```bash
curl https://milwaukee-voted-employer-annually.trycloudflare.com/tasks/ocr
# → Connection failed (HTTP 000)
```

**Impact:**
- CV upload will fail when using `CV_PARSER_STRATEGY=chandra`
- System will not be able to parse CV files

**Solution:** See `CHANDRA_DEBUG_REPORT.md` for detailed instructions on:
1. Starting Chandra OCR service locally
2. Setting up Cloudflare tunnel
3. Alternative fallback strategies (pymupdf, textract)

---

## 📝 Migration Script

For future reference, the migration script used:

```python
# backend/scripts/migrate_keys_to_uppercase.py
from shared.database import SessionLocal
from shared.models import SystemSetting
from shared.redis_client import config_cache

db = SessionLocal()
settings = db.query(SystemSetting).all()

for setting in settings:
    old_key = setting.key
    new_key = old_key.upper()
    
    if old_key != new_key:
        setting.key = new_key
        config_cache.delete(old_key)
        config_cache.delete(new_key)

db.commit()
```

---

## 🎯 Next Steps

### For Development
1. ✅ All settings keys are now UPPERCASE
2. ✅ Config manager auto-normalizes keys
3. ✅ Admin API auto-normalizes keys
4. ⚠️ Start Chandra OCR service (see CHANDRA_DEBUG_REPORT.md)

### For Production Deployment
1. Pull latest code
2. Run migration script (if not already done):
   ```bash
   docker exec gateway python -c "
   # Migration code here
   "
   ```
3. Restart services:
   ```bash
   docker compose restart gateway admin-service worker-cv-parser
   ```
4. Clear Redis cache:
   ```bash
   docker exec redis redis-cli FLUSHDB
   ```

---

## 🔧 Backward Compatibility

**Good news:** The system is backward compatible!

- Old code using lowercase keys: `get_setting('chandra_api_url')` → Still works (auto-converts to UPPERCASE)
- New code using UPPERCASE keys: `get_setting('CHANDRA_API_URL')` → Works
- Admin UI sending lowercase keys → Auto-converts to UPPERCASE
- Environment variables (already UPPERCASE) → Works seamlessly

**No breaking changes for existing code!**

---

## 📚 Related Files

- `backend/shared/config_utils.py` - Config manager with UPPERCASE normalization
- `backend/services/admin_service/main.py` - Admin API with UPPERCASE normalization
- `backend/scripts/migrate_keys_to_uppercase.py` - Migration script
- `CHANDRA_DEBUG_REPORT.md` - Chandra OCR troubleshooting guide
- `SECURITY_ANALYSIS.md` - Security model documentation

---

## ✅ Summary

**Completed:**
1. ✅ Removed X-Is-Admin security issue (26 frontend + 1 backend)
2. ✅ Migrated 22 settings keys to UPPERCASE
3. ✅ Auto-normalization in config_manager
4. ✅ Auto-normalization in admin API
5. ✅ Backward compatible (lowercase input still works)
6. ✅ All services rebuilt and running
7. ✅ Redis cache cleared and working with UPPERCASE keys

**Remaining:**
- ⚠️ Chandra OCR service needs to be started (separate issue, not related to settings)

**Impact:**
- 🎯 Consistent naming across entire system
- 🎯 Easier debugging (no case confusion)
- 🎯 Better alignment with environment variables
- 🎯 No breaking changes for existing code
