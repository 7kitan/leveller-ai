# Prompt Templates Migration Scripts

## Quick Reference

### Run Migration

**Development (Docker):**
```powershell
# Windows
.\run_migrations.ps1

# Linux/Mac
./run_migrations.sh
```

**Production:**
```powershell
# Windows
.\run_migrations.ps1 -Environment prod

# Linux/Mac
./run_migrations.sh prod
```

### Files Structure

```
scripts/
├── migrations/
│   └── 001_setup_prompts.sql       # All 5 prompt templates
├── run_migrations.ps1              # Windows runner
├── run_migrations.sh               # Linux/Mac runner
├── DEPLOYMENT_GUIDE.md             # Full deployment documentation
└── README.md                       # This file
```

## What Gets Deployed

### 5 Core Prompts

| Key                   | Name                                        | Parameters | Category              |
|-----------------------|---------------------------------------------|------------|-----------------------|
| cv_parsing            | CV Parsing                                  | 2          | cv_parsing            |
| jd_parsing            | JD Parsing                                  | 1          | jd_parsing            |
| gap_analysis          | Gap Analysis                                | 3          | gap_analysis          |
| gap_analysis_merged   | Gap Analysis Merged (JD Extract + Analysis) | 2          | gap_analysis_merged   |
| course_recommendation | Course Recommendation                       | 3          | course_recommendation |

### Key Features

- ✅ **Idempotent**: Safe to run multiple times (uses `ON CONFLICT`)
- ✅ **Versioned**: Migration files numbered (001, 002, etc.)
- ✅ **Verified**: Includes verification queries
- ✅ **Documented**: Full parameter descriptions and usage examples

## Pre-Deployment Checklist

- [ ] Database backup completed
- [ ] Environment variables configured (`.env` or `.env.production`)
- [ ] Database connection tested
- [ ] Admin service stopped (or ready to restart)
- [ ] Worker service stopped (or ready to restart)

## Post-Deployment Checklist

- [ ] Migration completed successfully (check output)
- [ ] All 5 prompts verified in database
- [ ] Services restarted (admin_service, worker)
- [ ] Redis cache reloaded (`POST /admin/prompts/reload`)
- [ ] Admin UI accessible (http://localhost:3000/admin/prompts)
- [ ] Test each prompt via API or UI

## Quick Verification

```bash
# Check prompts in database
docker exec advisor_db psql -U postgres -d career_advisor -c \
  "SELECT key, name, is_active FROM prompt_templates WHERE is_active = true;"

# Check admin service logs
docker logs advisor_admin --tail 50 | grep prompt

# Test API endpoint
curl http://localhost:8000/admin/prompts/categories
```

## Troubleshooting

**Migration fails with "relation does not exist":**
- Run initial schema migration first
- Check database name in `.env`

**Duplicate key errors:**
- Migration handles this automatically with `ON CONFLICT`
- If persists, check for manual duplicates

**Prompts not loading:**
- Restart services: `docker-compose restart admin_service worker`
- Reload cache: `POST /admin/prompts/reload`
- Check Redis: `docker exec advisor_redis redis-cli ping`

## Documentation

See [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for:
- Detailed deployment steps
- Environment setup
- Rollback procedures
- Monitoring queries
- Security notes

## Support

For issues:
1. Check logs: `docker logs advisor_admin`
2. Verify database: `psql -U postgres -d career_advisor`
3. Review migration file: `migrations/001_setup_prompts.sql`
