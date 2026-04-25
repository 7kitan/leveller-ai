# Debug 400 Bad Request Error - VPS

## 1. Check Container Status
```bash
cd /opt/k109/backend
docker compose -f docker-compose.prod.yml ps
```

## 2. View Gateway Logs (Main API)
```bash
# Last 100 lines
docker logs advisor_gateway_prod --tail=100

# Real-time follow
docker logs advisor_gateway_prod -f

# Search for 400 errors
docker logs advisor_gateway_prod --tail=500 | grep -i "400\|bad request\|error"

# With timestamps
docker logs advisor_gateway_prod --tail=100 -t
```

## 3. View Individual Service Logs
```bash
# Auth Service
docker logs advisor_auth_service_prod --tail=100

# CV Service
docker logs advisor_cv_service_prod --tail=100

# Analysis Service
docker logs advisor_analysis_service_prod --tail=100

# JD Service
docker logs advisor_jd_service_prod --tail=100

# Recommender Service
docker logs advisor_recommender_service_prod --tail=100

# Admin Service
docker logs advisor_admin_service_prod --tail=100
```

## 4. View Worker Logs
```bash
# CV Parser Worker
docker logs advisor_worker_cv_parser_prod --tail=100

# Analysis Worker
docker logs advisor_worker_analysis_prod --tail=100

# Market Stats Worker
docker logs advisor_worker_market_stats_prod --tail=100
```

## 5. Check Database Logs
```bash
docker logs advisor_db_prod --tail=100
```

## 6. Check System Logs in Database
```bash
docker compose -f docker-compose.prod.yml exec gateway python << 'PYEOF'
import sys
sys.path.insert(0, '/app')
from shared.database import SessionLocal
from shared.models import SystemLog
from datetime import datetime, timedelta

db = SessionLocal()

# Get logs from last 1 hour
one_hour_ago = datetime.utcnow() - timedelta(hours=1)
logs = db.query(SystemLog).filter(
    SystemLog.created_at >= one_hour_ago,
    SystemLog.level.in_(['ERROR', 'CRITICAL'])
).order_by(SystemLog.created_at.desc()).limit(50).all()

print(f"\n🔍 Found {len(logs)} error logs in last hour:\n")
for log in logs:
    print(f"[{log.created_at}] {log.level} - {log.module}")
    print(f"  Message: {log.message}")
    if log.details:
        print(f"  Details: {log.details}")
    print()

db.close()
PYEOF
```

## 7. Check LLM Logs (If 400 is from AI service)
```bash
docker compose -f docker-compose.prod.yml exec gateway python << 'PYEOF'
import sys
sys.path.insert(0, '/app')
from shared.database import SessionLocal
from shared.models import LLMLog
from datetime import datetime, timedelta

db = SessionLocal()

# Get failed LLM calls from last 1 hour
one_hour_ago = datetime.utcnow() - timedelta(hours=1)
logs = db.query(LLMLog).filter(
    LLMLog.created_at >= one_hour_ago,
    LLMLog.status == 'error'
).order_by(LLMLog.created_at.desc()).limit(20).all()

print(f"\n🔍 Found {len(logs)} failed LLM calls in last hour:\n")
for log in logs:
    print(f"[{log.created_at}] {log.call_type} - {log.model_id}")
    print(f"  Error: {log.error_message}")
    print()

db.close()
PYEOF
```

## 8. Search All Logs for Specific Pattern
```bash
# Search for "400" in all containers
docker compose -f docker-compose.prod.yml logs --tail=500 | grep -i "400"

# Search for specific endpoint
docker compose -f docker-compose.prod.yml logs --tail=500 | grep -i "/api/cv/upload"

# Search for validation errors
docker compose -f docker-compose.prod.yml logs --tail=500 | grep -i "validation\|invalid"
```

## 9. Export Logs to File for Analysis
```bash
# Export all logs from last hour
docker logs advisor_gateway_prod --since 1h > /tmp/gateway_logs.txt

# Export specific service
docker logs advisor_cv_service_prod --since 1h > /tmp/cv_service_logs.txt

# View the file
cat /tmp/gateway_logs.txt | grep -i "error\|400"
```

## 10. Check Nginx/Reverse Proxy Logs (If using)
```bash
# If you have nginx container
docker logs nginx_container_name --tail=100

# Or system nginx
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log | grep " 400 "
```

## Common 400 Error Causes

### 1. Validation Error
```
Look for: "validation error", "invalid input", "missing required field"
```

### 2. Malformed JSON
```
Look for: "JSON decode error", "invalid JSON", "unexpected token"
```

### 3. Missing Headers
```
Look for: "missing authorization", "missing content-type"
```

### 4. File Upload Issues
```
Look for: "file too large", "invalid file type", "upload failed"
```

### 5. Database Constraint Violation
```
Look for: "unique constraint", "foreign key", "not null constraint"
```

## Quick Debug Script
```bash
#!/bin/bash
# Save as debug_400.sh

echo "=== Checking Gateway Logs ==="
docker logs advisor_gateway_prod --tail=200 | grep -i "400\|error" | tail -20

echo ""
echo "=== Checking CV Service Logs ==="
docker logs advisor_cv_service_prod --tail=200 | grep -i "400\|error" | tail -20

echo ""
echo "=== Checking Auth Service Logs ==="
docker logs advisor_auth_service_prod --tail=200 | grep -i "400\|error" | tail -20

echo ""
echo "=== Recent System Errors ==="
docker compose -f docker-compose.prod.yml exec gateway python << 'PYEOF'
import sys
sys.path.insert(0, '/app')
from shared.database import SessionLocal
from shared.models import SystemLog
from datetime import datetime, timedelta

db = SessionLocal()
one_hour_ago = datetime.utcnow() - timedelta(hours=1)
logs = db.query(SystemLog).filter(
    SystemLog.created_at >= one_hour_ago,
    SystemLog.level == 'ERROR'
).order_by(SystemLog.created_at.desc()).limit(10).all()

for log in logs:
    print(f"[{log.created_at}] {log.module}: {log.message}")

db.close()
PYEOF
```

## Usage
```bash
cd /opt/k109/backend
chmod +x debug_400.sh
./debug_400.sh
```
