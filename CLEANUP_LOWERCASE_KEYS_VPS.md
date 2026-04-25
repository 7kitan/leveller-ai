# Hướng dẫn xóa lowercase keys trên VPS

## 🎯 Mục đích
Xóa các system_settings keys có chữ thường (lowercase) khỏi database trên VPS production.

## ⚠️ Lưu ý quan trọng
- **Backup database trước khi chạy!**
- Chỉ xóa keys có chữ thường nếu đã có phiên bản UPPERCASE tương ứng
- Kiểm tra kỹ trước khi xóa

---

## 📋 Các bước thực hiện

### Bước 1: SSH vào VPS
```bash
ssh user@your-vps-ip
cd /path/to/Team078
```

### Bước 2: Kiểm tra keys hiện tại
```bash
# Xem tất cả keys
docker exec advisor_db_prod psql -U postgres -d career_advisor -c "SELECT key FROM system_settings ORDER BY key;"

# Xem chỉ keys có chữ thường
docker exec advisor_db_prod psql -U postgres -d career_advisor -c "SELECT key, value FROM system_settings WHERE key ~ '[a-z]' ORDER BY key;"
```

### Bước 3: Kiểm tra keys trùng lặp (lowercase vs UPPERCASE)
```bash
docker exec advisor_db_prod psql -U postgres -d career_advisor -c "
SELECT 
    s1.key as lowercase_key,
    s2.key as uppercase_key,
    s1.value = s2.value as values_match
FROM system_settings s1
JOIN system_settings s2 ON UPPER(s1.key) = s2.key
WHERE s1.key != s2.key
ORDER BY s1.key;
"
```

**Ví dụ output:**
```
 lowercase_key      | uppercase_key      | values_match
--------------------+--------------------+--------------
 chandra_api_key    | CHANDRA_OCR_API_KEY| t
 chandra_api_url    | CHANDRA_OCR_URL    | t
```

### Bước 4: Backup database (QUAN TRỌNG!)
```bash
# Backup toàn bộ database
docker exec advisor_db_prod pg_dump -U postgres career_advisor > backup_before_cleanup_$(date +%Y%m%d_%H%M%S).sql

# Hoặc chỉ backup bảng system_settings
docker exec advisor_db_prod psql -U postgres -d career_advisor -c "COPY system_settings TO STDOUT WITH CSV HEADER;" > system_settings_backup_$(date +%Y%m%d_%H%M%S).csv
```

### Bước 5: Xóa lowercase keys

**Option A: Xóa tất cả keys có chữ thường**
```bash
docker exec advisor_db_prod psql -U postgres -d career_advisor -c "
DELETE FROM system_settings 
WHERE key ~ '[a-z]';
"
```

**Option B: Xóa từng key cụ thể (an toàn hơn)**
```bash
# Xóa chandra_api_key (nếu đã có CHANDRA_OCR_API_KEY)
docker exec advisor_db_prod psql -U postgres -d career_advisor -c "
DELETE FROM system_settings WHERE key = 'chandra_api_key';
"

# Xóa chandra_api_url (nếu đã có CHANDRA_OCR_URL)
docker exec advisor_db_prod psql -U postgres -d career_advisor -c "
DELETE FROM system_settings WHERE key = 'chandra_api_url';
"
```

**Option C: Xóa chỉ keys có phiên bản UPPERCASE (an toàn nhất)**
```bash
docker exec advisor_db_prod psql -U postgres -d career_advisor -c "
DELETE FROM system_settings s1
WHERE s1.key ~ '[a-z]'
AND EXISTS (
    SELECT 1 FROM system_settings s2 
    WHERE UPPER(s1.key) = s2.key 
    AND s1.key != s2.key
);
"
```

### Bước 6: Verify kết quả
```bash
# Kiểm tra không còn lowercase keys
docker exec advisor_db_prod psql -U postgres -d career_advisor -c "
SELECT key FROM system_settings WHERE key ~ '[a-z]';
"
# Output: (0 rows) = thành công

# Xem tất cả keys còn lại
docker exec advisor_db_prod psql -U postgres -d career_advisor -c "
SELECT key FROM system_settings ORDER BY key;
"
```

### Bước 7: Clear Redis cache
```bash
# Clear cache để force reload từ database
docker exec advisor_redis_prod redis-cli -n 0 KEYS "advisor:*" | xargs -I {} docker exec advisor_redis_prod redis-cli -n 0 DEL {}

# Hoặc clear toàn bộ cache
docker exec advisor_redis_prod redis-cli -n 0 FLUSHDB
```

### Bước 8: Restart services (nếu cần)
```bash
# Restart admin service để reload config
docker restart advisor_admin_prod

# Restart analysis service
docker restart advisor_analysis_prod

# Restart CV service
docker restart advisor_cv_prod
```

---

## 🔍 Troubleshooting

### Nếu xóa nhầm key quan trọng:
```bash
# Restore từ backup
docker exec -i advisor_db_prod psql -U postgres career_advisor < backup_before_cleanup_YYYYMMDD_HHMMSS.sql
```

### Nếu services không hoạt động sau khi xóa:
```bash
# Check logs
docker logs advisor_admin_prod --tail 50
docker logs advisor_analysis_prod --tail 50

# Verify keys trong database
docker exec advisor_db_prod psql -U postgres -d career_advisor -c "SELECT key, value FROM system_settings ORDER BY key;"
```

---

## ✅ Checklist

- [ ] SSH vào VPS
- [ ] Kiểm tra keys hiện tại
- [ ] Kiểm tra keys trùng lặp
- [ ] **Backup database**
- [ ] Xóa lowercase keys (chọn option phù hợp)
- [ ] Verify không còn lowercase keys
- [ ] Clear Redis cache
- [ ] Test services hoạt động bình thường
- [ ] Xóa file backup cũ (sau 1 tuần nếu không có vấn đề)

---

## 📝 Notes

**Tại sao cần xóa lowercase keys?**
- Code hiện tại đã chuẩn hóa tất cả keys thành UPPERCASE
- Lowercase keys là dư thừa từ code cũ
- Có thể gây confusion khi debug
- Tốn storage không cần thiết

**Keys nào nên xóa?**
- `chandra_api_key` → đã có `CHANDRA_OCR_API_KEY`
- `chandra_api_url` → đã có `CHANDRA_OCR_URL`
- Bất kỳ key nào có chữ thường và đã có phiên bản UPPERCASE

**Keys nào KHÔNG nên xóa?**
- Nếu key chỉ có lowercase và không có phiên bản UPPERCASE
- Nếu không chắc chắn → hỏi trước khi xóa
