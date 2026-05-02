# Verification Script for All Fixes
# Run this after creating a job via admin interface

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "VERIFICATION SCRIPT - ALL FIXES" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check 1: Recent job creation
Write-Host "[1] Checking recent job creation..." -ForegroundColor Yellow
docker exec advisor_jd python -c "
from shared.database import SessionLocal
from shared.models import Job
from sqlalchemy import desc
import json

db = SessionLocal()
recent = db.query(Job).order_by(desc(Job.created_at)).limit(3).all()

print('\nRecent jobs:')
for j in recent:
    print(f'  - {j.title_raw}')
    print(f'    Created: {j.created_at}')
    print(f'    Has requirements: {bool(j.requirements)}')
    print(f'    Has extracted skills: {bool(j.extracted_requirements_json)}')
    if j.extracted_requirements_json:
        tech_count = sum(1 for s in j.extracted_requirements_json if s.get('skill_type') == 'technical')
        soft_count = sum(1 for s in j.extracted_requirements_json if s.get('skill_type') == 'soft')
        print(f'    Skills: {len(j.extracted_requirements_json)} total ({tech_count} technical, {soft_count} soft)')
    print()

db.close()
"

# Check 2: Worker logs for extraction
Write-Host "`n[2] Checking worker logs for skill extraction..." -ForegroundColor Yellow
docker logs advisor_worker_crawler --tail 50 --since 5m 2>&1 | Select-String -Pattern "extract|skill" | Select-Object -Last 10

# Check 3: Backend logs for job creation
Write-Host "`n[3] Checking backend logs for job creation..." -ForegroundColor Yellow
docker logs advisor_jd --tail 50 --since 5m 2>&1 | Select-String -Pattern "admin_create_job|MANUAL JOB|Triggered skill extraction" | Select-Object -Last 5

# Check 4: Verify no type errors
Write-Host "`n[4] Checking for type errors (should be none)..." -ForegroundColor Yellow
$errors = docker logs advisor_worker_crawler --tail 100 --since 10m 2>&1 | Select-String -Pattern "unsupported operand type"
if ($errors) {
    Write-Host "  ❌ FOUND TYPE ERRORS (worker needs restart):" -ForegroundColor Red
    $errors | Select-Object -Last 3
} else {
    Write-Host "  ✅ No type errors found!" -ForegroundColor Green
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "VERIFICATION COMPLETE" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. If job has extracted_requirements_json → ✅ Fix working!" -ForegroundColor Green
Write-Host "2. If no skills after 30 seconds → Run manual extraction:" -ForegroundColor Yellow
Write-Host "   curl -X POST http://localhost:8000/jd/admin/extract-skills/{job_id}" -ForegroundColor Gray
Write-Host "3. Check radar chart on frontend has 5 dimensions" -ForegroundColor Yellow
