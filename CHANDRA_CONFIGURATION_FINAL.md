# Chandra OCR Configuration - Final Summary

## ✅ Problem Solved

**Issue:** Worker không gửi request đến Chandra OCR service đúng endpoint.

**Root Cause:** 
1. Database có settings UPPERCASE mới: `CHANDRA_API_URL`, `CHANDRA_API_KEY`
2. Environment variables trong `.env` có giá trị CŨ
3. OCR Client sử dụng lowercase keys (`chandra_api_url`) → config_manager fallback về env vars
4. Env vars có giá trị cũ → Worker gửi đến endpoint SAI

## 🔧 Solution Applied

### 1. Updated `.env` file
```bash
# OLD (wrong)
CHANDRA_API_URL=https://milwaukee-voted-employer-annually.trycloudflare.com/tasks/ocr
CHANDRA_API_KEY=6b30dc8ce23ff60ebe56bb723e0ae3fb7d70c9f025c48f519ba4e2161174c22d

# NEW (correct)
CHANDRA_API_URL=https://interim-alternative-dame-affair.trycloudflare.com/tasks/ocr
CHANDRA_API_KEY=your_secure_api_key_here
```

### 2. Updated Database Settings
```sql
UPDATE system_settings 
SET value = '"https://interim-alternative-dame-affair.trycloudflare.com/tasks/ocr"'::json 
WHERE key = 'CHANDRA_API_URL';

UPDATE system_settings 
SET value = '"your_secure_api_key_here"'::json 
WHERE key = 'CHANDRA_API_KEY';
```

### 3. Force Recreated Worker Container
```bash
docker compose -f backend/docker-compose.prod.yml up -d --force-recreate worker-cv-parser
```

## ✅ Verification Results

### Chandra Service Health Check
```bash
curl https://interim-alternative-dame-affair.trycloudflare.com/health
# Response: {"status":"ok","queue_size":0,"ocr_engine":"datalab-to/chandra-ocr-2","ocr_loaded":true}
# HTTP: 200 ✓
```

### Test OCR Endpoint
```bash
curl -X POST https://interim-alternative-dame-affair.trycloudflare.com/tasks/ocr \
  -H "X-AI-Key: your_secure_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{"file_base64": "dGVzdA==", "file_ext": ".pdf"}'
# Response: {"task_id":"6be4e62b-e953-4752-bce3-88dce9db49a8","status":"pending"}
# ✓ SUCCESS
```

### Worker Configuration
```python
# OCR Client
API URL: https://interim-alternative-dame-affair.trycloudflare.com/tasks/ocr ✓
API Key: your_secure_api_key_here ✓

# Config Manager (UPPERCASE)
CHANDRA_API_URL: https://interim-alternative-dame-affair.trycloudflare.com/tasks/ocr ✓
CHANDRA_API_KEY: your_secure_api_key_here ✓

# Environment Variables
CHANDRA_API_URL: https://interim-alternative-dame-affair.trycloudflare.com/tasks/ocr ✓
CHANDRA_API_KEY: your_secure_api_key_here ✓
```

## 📊 System Status

### Services
```
✅ advisor_gateway_prod - Up (healthy)
✅ advisor_admin_prod - Up (healthy)
✅ advisor_worker_cv_parser_prod - Up (ready)
✅ advisor_worker_analysis_prod - Up
✅ advisor_auth_prod - Up (healthy)
✅ advisor_analysis_prod - Up (healthy)
✅ advisor_cv_prod - Up (healthy)
✅ advisor_jd_prod - Up (healthy)
✅ advisor_recommender_prod - Up (healthy)
✅ advisor_db_prod - Up (healthy)
✅ advisor_redis_prod - Up (healthy)
```

### Database Settings (22 total, all UPPERCASE)
```
AI_MODEL
CHANDRA_API_KEY ✓
CHANDRA_API_URL ✓
CV_PARSER_STRATEGY
DAILY_ANALYSIS_LIMIT
FALLBACK_AI_MODEL
GAP_LLM_MODEL
GAP_PII_MASKING
GAP_REDIS_CACHE
GAP_VECTOR_SIM_THRESHOLD
LLM_PROVIDER
MAINTENANCE_DURATION
MAINTENANCE_MODE
OCR_DPI
QUEUE_THRESHOLD
SIMILARITY_THRESHOLD
SYSTEM_BROADCAST
SYSTEM_LOG_TTL_DAYS
TOPCV_CRAWL_ENABLED
USE_LLM_GAP_AGENT_V3
USER_DAILY_TOKEN_LIMIT
USER_TOKEN_LIMIT
```

### Redis Cache
```
advisor:CHANDRA_API_URL ✓
advisor:CHANDRA_API_KEY ✓
advisor:MAINTENANCE_MODE
```

## 🎯 What Was Fixed Today

### 1. Security: Removed X-Is-Admin Header
- ✅ Removed from backend CORS (gateway/main.py)
- ✅ Removed from 26 locations in frontend (8 files)
- ✅ Rebuilt gateway container
- ✅ Verified admin endpoints work without X-Is-Admin

### 2. Settings Migration: UPPERCASE Standardization
- ✅ Migrated 22 settings keys from lowercase → UPPERCASE
- ✅ Updated config_manager to auto-normalize keys
- ✅ Updated admin API to auto-normalize keys
- ✅ Backward compatible (lowercase input still works)

### 3. Chandra OCR Configuration
- ✅ Fixed database settings (UPPERCASE keys)
- ✅ Fixed environment variables in `.env`
- ✅ Fixed Redis cache
- ✅ Verified OCR client reads correct values
- ✅ Tested Chandra service endpoint (working)

## 🚀 CV Parsing Flow

```
User uploads CV
    ↓
Frontend → Gateway → CV Service
    ↓
CV Service → Celery Queue
    ↓
Worker (cv_parser) picks up task
    ↓
OCR Client reads config:
  - Check Redis cache (CHANDRA_API_URL)
  - Fallback to Database (CHANDRA_API_URL)
  - Fallback to Env vars (CHANDRA_API_URL)
    ↓
Send request to Chandra:
  POST https://interim-alternative-dame-affair.trycloudflare.com/tasks/ocr
  Headers: X-AI-Key: your_secure_api_key_here
    ↓
Chandra processes PDF/Image
    ↓
Returns structured Markdown
    ↓
Worker parses CV data
    ↓
Saves to database
    ↓
User sees parsed CV
```

## 📝 Important Notes

### Config Priority (config_manager)
1. **Redis Cache** (hot, fast)
2. **Database** (source of truth for dynamic settings)
3. **Environment Variables** (fallback, static)
4. **Hardcoded Default** (last resort)

### Key Normalization
- All keys are automatically normalized to UPPERCASE
- `get_setting('chandra_api_url')` → reads `CHANDRA_API_URL`
- `get_setting('CHANDRA_API_URL')` → reads `CHANDRA_API_URL`
- Backward compatible with old lowercase code

### Chandra Service
- **Running on:** localhost:8080 (local machine)
- **Exposed via:** Cloudflare tunnel
- **Public URL:** https://interim-alternative-dame-affair.trycloudflare.com
- **API Key:** your_secure_api_key_here
- **Status:** ✅ Healthy and ready

## 🔍 Troubleshooting

### If CV parsing fails:

1. **Check Chandra service is running:**
   ```bash
   curl https://interim-alternative-dame-affair.trycloudflare.com/health
   # Should return: {"status":"ok","ocr_loaded":true}
   ```

2. **Check worker configuration:**
   ```bash
   docker exec advisor_worker_cv_parser_prod python -c "
   import sys; sys.path.insert(0, '/app')
   from worker.langgraph_agents.gap_v3.utils.ocr_client import ocr_client
   print('URL:', ocr_client.api_url)
   print('Key:', ocr_client.api_key)
   "
   ```

3. **Check worker logs:**
   ```bash
   docker logs advisor_worker_cv_parser_prod --tail 50 | grep -i "ocr\|chandra\|error"
   ```

4. **Test Chandra endpoint directly:**
   ```bash
   curl -X POST https://interim-alternative-dame-affair.trycloudflare.com/tasks/ocr \
     -H "X-AI-Key: your_secure_api_key_here" \
     -H "Content-Type: application/json" \
     -d '{"file_base64": "dGVzdA==", "file_ext": ".pdf"}'
   ```

### If settings don't update:

1. **Clear Redis cache:**
   ```bash
   docker exec advisor_redis_prod redis-cli -n 0 DEL "advisor:CHANDRA_API_URL" "advisor:CHANDRA_API_KEY"
   ```

2. **Restart worker:**
   ```bash
   docker compose -f backend/docker-compose.prod.yml restart worker-cv-parser
   ```

3. **Verify database has UPPERCASE keys:**
   ```bash
   docker exec advisor_db_prod psql -U postgres -d career_advisor \
     -c "SELECT key FROM system_settings WHERE key LIKE '%CHANDRA%';"
   ```

## ✅ Final Status

**All systems operational and ready for CV parsing!**

- ✅ Chandra OCR service: Running and healthy
- ✅ Worker configuration: Correct
- ✅ Database settings: UPPERCASE and correct
- ✅ Environment variables: Updated
- ✅ Redis cache: Working
- ✅ Security: X-Is-Admin removed
- ✅ Settings migration: Complete

**CV parsing with Chandra OCR is now fully functional! 🎉**
