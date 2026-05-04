# LLM Prompt Management System

## 📋 Tổng quan

Hệ thống quản lý prompt LLM cho phép admin:
- Tạo và quản lý nhiều phiên bản prompt cho cùng một function
- Test và đánh giá chất lượng các prompt khác nhau
- Dễ dàng switch giữa các prompt versions
- Tự động cache active prompts vào Redis
- Parameter replacement đơn giản với `{{param}}` syntax

## 🏗️ Kiến trúc

```
┌─────────────────┐
│  Admin UI       │ → Create/Edit/Activate prompts
│  /admin/prompts │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  Admin API      │ → CRUD operations + validation
│  /api/admin/    │
│  prompts        │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  Database       │ → Store all prompt versions
│  prompt_        │   (only 1 active per key)
│  templates      │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  Redis Cache    │ → Cache active prompts
│  prompt:key     │   (loaded on startup)
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  Prompt Manager │ → Render prompts with params
│  get_prompt()   │
└─────────────────┘
```

## 🚀 Cài đặt

### 1. Chạy Database Migration

```bash
# Development
docker compose -f backend/docker-compose.yml exec gateway \
  psql -U postgres -d career_advisor -f /app/scripts/migrations/add_prompt_templates.sql

# Production
docker compose -f backend/docker-compose.prod.yml exec gateway \
  psql -U postgres -d career_advisor -f /app/scripts/migrations/add_prompt_templates.sql
```

Migration sẽ:
- Tạo bảng `prompt_templates`
- Thêm indexes và constraints
- Insert 3 default prompts (cv_parsing, gap_analysis, job_recommendation)

### 2. Restart Admin Service

```bash
# Development
docker compose -f backend/docker-compose.yml restart admin-service

# Production
docker compose -f backend/docker-compose.prod.yml restart admin-service
```

Admin service sẽ tự động:
- Initialize prompt manager
- Load active prompts vào Redis

### 3. Verify Installation

```bash
# Check logs
docker compose -f backend/docker-compose.yml logs admin-service | grep -i prompt

# Expected output:
# [ADMIN] Prompt manager initialized
# [ADMIN] Loaded 3 active prompts on startup
```

## 📖 Sử dụng

### Admin UI

1. Truy cập: `http://localhost:3000/admin/prompts`
2. Xem danh sách prompts được group theo key
3. Tạo prompt mới hoặc edit prompt hiện có
4. Activate prompt để sử dụng trong production

### Tạo Prompt Mới

**Ví dụ: Tạo CV Parsing v2**

```
Key: cv_parsing
Name: CV Parsing v2 - More Detailed
Category: cv_parsing
Prompt Text:
  Bạn là chuyên gia phân tích CV. Hôm nay là {{current_date}}.
  
  Phân tích CV sau: {{cv_text}}
  
  Trả về JSON với các trường chi tiết...

Parameters: cv_text, current_date
Temperature: 0.3
Max Tokens: 2000
Active: false (test trước)
Admin Notes: Testing more detailed extraction
```

### Test Workflow

1. **Tạo prompt mới** với `is_active = false`
2. **Test thực tế** với users
3. **Đánh giá** trong Admin Notes:
   - "Accuracy 92%, extract skills tốt hơn v1"
4. **Activate** khi hài lòng → tự động deactivate v1

### Sử dụng trong Code

```python
from shared.prompt_manager import get_prompt
from datetime import datetime

# Get and render prompt
prompt_text, model_config = get_prompt(
    'cv_parsing',
    cv_text=cv_content,
    current_date=datetime.now().strftime('%Y-%m-%d')
)

# Use with LLM
response = llm_client.chat(
    prompt=prompt_text,
    temperature=model_config['temperature'],
    max_tokens=model_config['max_tokens']
)
```

## 🔧 API Endpoints

### List Prompts
```bash
GET /api/admin/prompts?category=cv_parsing&is_active=true
```

### Get Prompt
```bash
GET /api/admin/prompts/{prompt_id}
```

### Create Prompt
```bash
POST /api/admin/prompts
Content-Type: application/json

{
  "key": "cv_parsing",
  "name": "CV Parsing v2",
  "category": "cv_parsing",
  "prompt_text": "Analyze CV: {{cv_text}}",
  "parameters": ["cv_text", "current_date"],
  "model_config": {
    "temperature": 0.3,
    "max_tokens": 2000
  },
  "is_active": false,
  "admin_notes": "Testing new version"
}
```

### Update Prompt
```bash
PUT /api/admin/prompts/{prompt_id}
Content-Type: application/json

{
  "admin_notes": "Accuracy improved to 95%"
}
```

### Activate Prompt
```bash
POST /api/admin/prompts/{prompt_id}/activate
```

### Delete Prompt
```bash
DELETE /api/admin/prompts/{prompt_id}
```

### Reload Cache
```bash
POST /api/admin/prompts/reload
```

## 🎯 Best Practices

### 1. Naming Convention
```
{Function} v{Version} - {Description}

Examples:
- CV Parsing v1 - Standard
- CV Parsing v2 - Detailed extraction
- Gap Analysis v1 - Standard
- Gap Analysis v2 - Shorter response
```

### 2. Parameter Naming
- Sử dụng `snake_case`: `cv_text`, `current_date`
- Tên rõ ràng, dễ hiểu
- Consistent across prompts

### 3. Testing Strategy
```
1. Create new prompt (inactive)
2. Test with sample data
3. Deploy to production (still inactive)
4. Monitor real usage for 1-2 days
5. Compare metrics with current active
6. Activate if better, delete if worse
```

### 4. Admin Notes Format
```
Version: v2
Tested: 2026-05-03
Sample size: 100 CVs
Accuracy: 92% (vs 85% in v1)
Issues: None
Recommendation: Activate
```

## 🔍 Troubleshooting

### Prompt không được cache
```bash
# Check Redis
docker compose exec redis redis-cli
> KEYS prompt:*
> GET prompt:cv_parsing

# Reload manually
curl -X POST http://localhost:8000/api/admin/prompts/reload \
  -H "Cookie: session=..."
```

### Parameter không được replace
- Kiểm tra format: `{{param}}` (2 dấu ngoặc nhọn)
- Kiểm tra tên parameter match với code
- Xem logs: `[OCR DEBUG]` hoặc `[Prompt Manager]`

### Multiple active prompts
```sql
-- Check database
SELECT key, name, is_active FROM prompt_templates WHERE is_active = true;

-- Fix manually if needed
UPDATE prompt_templates SET is_active = false WHERE key = 'cv_parsing' AND id != 123;
```

## 📊 Monitoring

### Check Active Prompts
```bash
# Redis
docker compose exec redis redis-cli KEYS "prompt:*"

# Database
docker compose exec gateway psql -U postgres -d career_advisor \
  -c "SELECT key, name, is_active FROM prompt_templates WHERE is_active = true;"
```

### View Logs
```bash
# Admin service logs
docker compose logs -f admin-service | grep -i prompt

# Worker logs (when using prompts)
docker compose logs -f worker_parsing | grep -i prompt
```

## 🎨 UI Features

- ✅ Group prompts by key
- ✅ Show active badge
- ✅ One-click activate/deactivate
- ✅ Inline prompt preview
- ✅ Parameter validation on save
- ✅ Admin notes for quality tracking
- ✅ Category filtering
- ✅ Reload cache button

## 🔐 Security

- ✅ Admin-only access (require_admin middleware)
- ✅ Parameter validation before save
- ✅ SQL injection protection (parameterized queries)
- ✅ Redis cache isolation (separate prefix)

## 📝 Future Enhancements

- [ ] Prompt versioning history
- [ ] A/B testing framework
- [ ] Automatic quality metrics
- [ ] Prompt preview with sample data
- [ ] Export/import prompts
- [ ] Prompt templates library

## 🤝 Contributing

Khi thêm prompt mới:
1. Tạo với `is_active = false`
2. Test kỹ trước khi activate
3. Document trong Admin Notes
4. Update README nếu cần

---

**Built with ❤️ for Team078 Career Advisor Platform**
