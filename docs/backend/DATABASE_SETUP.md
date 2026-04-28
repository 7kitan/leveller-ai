# Database Setup and Migrations

## Overview

The database uses PostgreSQL with pgvector extension for vector similarity search.

## Automatic Setup (Recommended)

All services automatically run migrations on startup via `init_db()` in `shared/database.py`.

**No manual intervention needed for production deployments.**

## Manual Migration (If Needed)

If automatic migrations fail, run manually:

```bash
# Inside backend directory
python scripts/run_migrations.py
```

## Migration Files

Migrations are located in `scripts/migrations/` and run in order:

1. `001_add_job_sections.sql` - Add job description sections
2. `002_add_missing_indexes.sql` - Add 25+ performance indexes

## Index Summary

### Performance Indexes (25 total)

**Courses Table (9 indexes):**
- `idx_courses_tags_gin` - GIN index for tags array search
- `idx_courses_skills_raw_gin` - GIN index for skills JSON search
- `idx_courses_vector_hnsw` - HNSW index for vector similarity
- `idx_courses_title_trgm` - Trigram index for title ILIKE
- `idx_courses_platform_trgm` - Trigram index for platform ILIKE
- `idx_courses_provider_trgm` - Trigram index for provider ILIKE
- `idx_courses_is_active` - Partial index for active courses
- `idx_courses_level` - Index for level filtering
- `idx_courses_active_created` - Composite index for active + created_at

**Job Tables (7 indexes):**
- `idx_job_skill_req_job_id` - FK index for job_id
- `idx_job_skill_req_skill_id` - FK index for skill_id
- `idx_job_skill_req_job_mandatory` - Composite index
- `idx_job_skill_req_level` - Index for required_level
- `idx_jobs_status` - Partial index for active jobs
- `idx_jobs_created_at` - Index for time-based queries
- `idx_jobs_status_created` - Composite index

**User Tables (7 indexes):**
- `idx_user_skill_profile_user_id` - Index for user_id
- `idx_user_skill_profile_skill_id` - FK index for skill_id
- `idx_user_skill_profile_cv_id` - FK index for cv_id
- `idx_user_skill_profile_level` - Index for level
- `idx_user_skill_profile_user_skill` - Composite index
- `idx_user_work_exp_cv_id` - FK index for cv_id
- `idx_user_cvs_user_id` - Index for user_id
- `idx_user_cvs_created_at` - Index for sorting

**Skills Table (1 index):**
- `idx_skills_vector_hnsw` - HNSW index for skill vectors

### SQLAlchemy Auto-Indexes (26 total)

These are created automatically from `index=True` in models.py:
- Primary keys (16)
- Unique constraints (4)
- Foreign key indexes (6)

## Verifying Indexes

Run the audit script to verify all indexes exist:

```bash
# Via Docker
docker exec advisor_db_prod psql -U postgres -d career_advisor -f /app/scripts/audit_indexes.sql

# Or via psql directly
psql -U postgres -d career_advisor -f scripts/audit_indexes.sql
```

Expected output:
- **71 total indexes**
- **25 performance indexes** (idx_*)
- **26 SQLAlchemy indexes** (ix_*)
- **All critical indexes: ✅ EXISTS**

## Performance Impact

With indexes:
- Course search: ~1.7ms (303 courses)
- Vector similarity: ~2-5ms (HNSW index)
- JOIN queries: 10-50x faster (FK indexes)

Without indexes:
- Course search: ~50-100ms (sequential scan)
- Vector similarity: ~100-500ms (sequential scan)
- JOIN queries: Very slow (sequential scans)

## Troubleshooting

### Indexes not created on new deployment

1. Check if migrations ran:
   ```sql
   SELECT * FROM schema_migrations;
   ```

2. Manually run migrations:
   ```bash
   python scripts/run_migrations.py
   ```

3. Check logs for migration errors:
   ```bash
   docker logs advisor_gateway_prod | grep migration
   ```

### Index already exists error

This is safe to ignore. Migrations are idempotent and use `CREATE INDEX IF NOT EXISTS`.

### Slow queries after deployment

Run ANALYZE to update statistics:
```sql
ANALYZE courses;
ANALYZE jobs;
ANALYZE user_skill_profile;
```
