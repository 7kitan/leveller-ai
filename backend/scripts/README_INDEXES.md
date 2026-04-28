# Database Index Setup

Scripts để setup tất cả indexes cần thiết cho Career Advisor database.

## Files

- `setup_indexes.sql` - SQL script chứa tất cả index definitions
- `setup_indexes.sh` - Bash script cho Linux/Mac
- `setup_indexes.ps1` - PowerShell script cho Windows

## Khi nào cần chạy?

1. **Lần đầu setup database trên VPS**
2. **Sau khi restore database từ backup**
3. **Khi phát hiện indexes bị thiếu**
4. **Sau khi migrate/update schema**

## Cách sử dụng

### Trên Windows (PowerShell)

```powershell
cd backend/scripts
.\setup_indexes.ps1
```

### Trên Linux/Mac (Bash)

```bash
cd backend/scripts
chmod +x setup_indexes.sh
./setup_indexes.sh
```

### Chạy trực tiếp SQL file

```bash
docker exec -i advisor_db_prod psql -U postgres -d career_advisor < setup_indexes.sql
```

## Indexes được tạo

### Jobs Table (12 indexes)
- ✅ Vector HNSW index cho similarity search
- ✅ B-tree indexes cho filtering (status, location, salary, company, etc.)
- ✅ Partial indexes cho active jobs

### Courses Table (14 indexes)
- ✅ Vector HNSW index
- ✅ GIN indexes cho full-text search (title, platform, provider)
- ✅ GIN indexes cho JSONB (skills_raw, tags)

### Skills Table (3 indexes)
- ✅ Vector HNSW index
- ✅ Unique constraint trên name

### Job_Skill_Requirement (5 indexes)
- ✅ Foreign key indexes
- ✅ Composite indexes cho filtering

### User_Skill_Profile (6 indexes)
- ✅ Composite index (user_id, skill_id)
- ✅ Foreign key indexes

### Các tables khác
- User CVs, Analysis, Work Experiences
- Market Stats & History
- System Logs, LLM Logs
- User Feedback
- YouTube Courses

## Verify Indexes

Sau khi chạy script, kiểm tra indexes:

```bash
# Check tất cả vector indexes
docker exec advisor_db_prod psql -U postgres -d career_advisor -c "
SELECT tablename, indexname 
FROM pg_indexes 
WHERE schemaname = 'public' AND indexname LIKE '%vector%' 
ORDER BY tablename;
"

# Check số lượng indexes theo table
docker exec advisor_db_prod psql -U postgres -d career_advisor -c "
SELECT tablename, COUNT(*) as index_count 
FROM pg_indexes 
WHERE schemaname = 'public' 
GROUP BY tablename 
ORDER BY index_count DESC;
"

# Check chi tiết indexes của một table
docker exec advisor_db_prod psql -U postgres -d career_advisor -c "\d jobs"
```

## Lưu ý

- Script là **idempotent** - an toàn để chạy nhiều lần
- Sử dụng `CREATE INDEX IF NOT EXISTS` để tránh lỗi nếu index đã tồn tại
- Vector indexes sử dụng HNSW algorithm với `m=16, ef_construction=64`
- Partial indexes được dùng để tối ưu queries cho active records

## Troubleshooting

### Lỗi: Container not running
```bash
docker ps | grep advisor_db_prod
docker-compose -f docker-compose.prod.yml up -d db
```

### Lỗi: Extension not found
```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### Check index size
```sql
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;
```

## Performance Tips

1. **Vector indexes** cần thời gian để build - có thể mất vài phút với nhiều records
2. **GIN indexes** cho full-text search cũng tốn thời gian build
3. Nên chạy script khi database ít traffic
4. Monitor disk space trước khi chạy (indexes chiếm dung lượng)
