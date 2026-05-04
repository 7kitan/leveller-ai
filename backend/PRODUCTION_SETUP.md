# Production Database Setup Guide

## Overview

This guide provides complete instructions for setting up the database for production deployment.

## What Gets Set Up

The production setup script performs the following operations:

### 1. PostgreSQL Extensions
- **pgvector**: Vector similarity search for courses and skills
- **pg_trgm**: Fast text search (ILIKE optimization) for jobs

### 2. Database Schema
- Creates all tables with proper constraints
- Sets up foreign keys and cascading deletes
- Applies unique constraints

### 3. Migrations (4 total)
- **001_add_job_sections.sql**: Adds structured job sections (description, requirements, benefits)
- **002_add_missing_indexes.sql**: Creates performance indexes for all tables
- **003_add_cv_soft_delete.sql**: Adds soft delete support for user CVs
- **004_drop_job_vectors_optimize_indexes.sql**: Removes job embeddings, optimizes for text search

### 4. Admin User
- Creates system admin account from environment variables
- Default: admin@lumix.ai / Admin@123 (change in production!)

### 5. Verification
- Checks all extensions are enabled
- Verifies tables and migrations
- Confirms vector columns removed from jobs table
- Validates soft delete on user_cvs table

## Prerequisites

### Required
- Docker and Docker Compose installed
- PostgreSQL 14+ with pgvector extension
- Python 3.8+ (for running setup script)
- `.env` file configured (copied from `.env.example`)

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Admin User (CHANGE IN PRODUCTION!)
DEFAULT_ADMIN_EMAIL=admin@yourdomain.com
DEFAULT_ADMIN_PASSWORD=YourSecurePassword123!
DEFAULT_ADMIN_NAME=System Administrator

# OpenAI (optional - not needed for job search)
OPENAI_API_KEY=sk-...  # Only for course recommendations
```

## Quick Start

### Option 1: Automated Setup (Recommended)

```bash
# 1. Navigate to backend directory
cd backend

# 2. Ensure .env file exists
cp .env.example .env
# Edit .env with your production values

# 3. Start database
docker-compose up -d db redis

# 4. Run production setup
python3 scripts/setup_production.py
```

### Option 2: Using Bash Script

```bash
cd backend
chmod +x scripts/setup_production.sh
./scripts/setup_production.sh
```

### Option 3: Manual Setup

```bash
# 1. Start services
docker-compose up -d db redis

# 2. Enable extensions
docker-compose exec db psql -U postgres -d career_advisor -c "CREATE EXTENSION IF NOT EXISTS vector;"
docker-compose exec db psql -U postgres -d career_advisor -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"

# 3. Create schema
python3 scripts/setup_db.py

# 4. Run migrations
python3 scripts/run_migrations.py

# 5. Verify
docker-compose exec db psql -U postgres -d career_advisor -c "\dt"
```

## Expected Output

```
======================================================================
🚀 PRODUCTION DATABASE SETUP
======================================================================

STEP 1: Enabling PostgreSQL Extensions
  ✓ pgvector extension enabled
  ✓ pg_trgm extension enabled
✅ Extensions enabled successfully

STEP 2: Creating Database Schema
  ✓ All tables created
  ✓ Foreign keys configured
  ✓ Unique constraints applied
✅ Schema created successfully

STEP 3: Running Database Migrations
  ✓ Migration tracking table ready
  📝 Applying 001_add_job_sections.sql...
  ✅ 001_add_job_sections.sql applied successfully
  📝 Applying 002_add_missing_indexes.sql...
  ✅ 002_add_missing_indexes.sql applied successfully
  📝 Applying 003_add_cv_soft_delete.sql...
  ✅ 003_add_cv_soft_delete.sql applied successfully
  📝 Applying 004_drop_job_vectors_optimize_indexes.sql...
  ✅ 004_drop_job_vectors_optimize_indexes.sql applied successfully
✅ Migrations completed: 4 applied, 0 skipped

STEP 4: Creating Admin User
  ✓ Admin user: admin@lumix.ai
✅ Admin user ready

STEP 5: Verifying Setup
  ✓ Extensions: pg_trgm, vector
  ✓ Tables: 18 created
  ✓ Migrations: 4 applied
  ✓ Jobs table: vector columns removed
  ✓ User CVs: soft delete enabled
  ✓ Admin users: 1
✅ Verification completed

======================================================================
🎉 PRODUCTION SETUP COMPLETED SUCCESSFULLY
======================================================================
```

## Database Architecture

### Tables Created (18 total)

**Core Tables:**
- `users` - User accounts and authentication
- `user_cvs` - User CV uploads (with soft delete)
- `user_skill_profile` - User skills extracted from CVs
- `user_work_experiences` - User work history
- `user_analysis` - Gap analysis results

**Job Tables:**
- `jobs` - Job postings (text search optimized, NO vectors)
- `skills` - Master skills taxonomy (with vectors for matching)
- `job_skill_requirement` - Job-skill relationships

**Course Tables:**
- `courses` - Course catalog (with vectors for recommendations)
- `youtube_courses` - YouTube course metadata
- `youtube_video_skills` - YouTube video-skill mappings

**System Tables:**
- `system_settings` - Application configuration
- `system_logs` - System event logs
- `llm_logs` - LLM API usage tracking
- `user_feedback` - User feedback submissions
- `pending_skills` - Skills pending admin approval
- `market_skill_stats` - Market demand statistics
- `market_skill_history` - Historical market trends
- `schema_migrations` - Migration tracking

### Index Strategy

**Jobs Table (Text Search):**
- GIN indexes for fast ILIKE queries (title, company, requirements)
- Composite indexes for common query patterns
- Partial indexes for active jobs only
- NO vector indexes (removed for performance)

**Courses Table (Vector Search):**
- HNSW index for fast similarity search
- GIN indexes for text search
- JSON indexes for tags and skills

**Skills Table (Vector Search):**
- HNSW index for skill matching
- Unique constraint on skill name

## Verification Commands

### Check Extensions
```bash
docker-compose exec db psql -U postgres -d career_advisor -c "SELECT extname FROM pg_extension WHERE extname IN ('vector', 'pg_trgm');"
```

### Check Tables
```bash
docker-compose exec db psql -U postgres -d career_advisor -c "\dt"
```

### Check Migrations
```bash
docker-compose exec db psql -U postgres -d career_advisor -c "SELECT * FROM schema_migrations ORDER BY applied_at;"
```

### Verify Jobs Table (No Vectors)
```bash
docker-compose exec db psql -U postgres -d career_advisor -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'jobs' AND column_name IN ('vector', 'embedding_context');"
# Expected: 0 rows
```

### Check Indexes
```bash
docker-compose exec db psql -U postgres -d career_advisor -c "\d jobs"
```

### Check Database Size
```bash
docker-compose exec db psql -U postgres -d career_advisor -c "SELECT pg_size_pretty(pg_database_size('career_advisor'));"
```

## Troubleshooting

### Issue: "pgvector extension not found"
**Solution:**
```bash
# Install pgvector in PostgreSQL container
docker-compose exec db apt-get update
docker-compose exec db apt-get install -y postgresql-14-pgvector
docker-compose restart db
```

### Issue: "Migration file not found"
**Solution:**
```bash
# Verify migration files exist
ls -la backend/scripts/migrations/
# Should show: 001, 002, 003, 004 .sql files
```

### Issue: "DATABASE_URL not found"
**Solution:**
```bash
# Check .env file
cat .env | grep DATABASE_URL
# If missing, add: DATABASE_URL=postgresql://postgres:postgres@db:5432/career_advisor
```

### Issue: "Permission denied"
**Solution:**
```bash
# Make scripts executable
chmod +x scripts/setup_production.sh
chmod +x scripts/setup_production.py
```

### Issue: "Tables already exist"
**Solution:**
This is normal! The setup is idempotent. It will skip existing tables and migrations.

### Issue: "Migration already applied"
**Solution:**
This is expected behavior. Migrations are tracked and won't run twice.

## Post-Setup Steps

### 1. Start All Services
```bash
docker-compose up -d
```

### 2. Verify Services
```bash
docker-compose ps
# All services should show "Up"
```

### 3. Check Logs
```bash
docker-compose logs -f gateway
docker-compose logs -f jd-service
```

### 4. Test API
```bash
# Health check
curl http://localhost:8000/health

# API docs
open http://localhost:8000/docs
```

### 5. Test Admin Login
```bash
# Login endpoint
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@lumix.ai","password":"Admin@123"}'
```

## Performance Optimization

### After Initial Setup

**1. Analyze Tables (Update Statistics)**
```sql
ANALYZE jobs;
ANALYZE courses;
ANALYZE skills;
```

**2. Vacuum Full (Reclaim Space - Requires Downtime)**
```sql
VACUUM FULL jobs;  -- Reclaim space from dropped vector columns
```

**3. Enable Query Logging**
```sql
ALTER DATABASE career_advisor SET log_min_duration_statement = 1000;
```

## Maintenance

### Weekly
```bash
# Analyze tables for query planner
docker-compose exec db psql -U postgres -d career_advisor -c "ANALYZE;"
```

### Monthly
```bash
# Reindex if needed
docker-compose exec db psql -U postgres -d career_advisor -c "REINDEX DATABASE CONCURRENTLY career_advisor;"
```

### Backup
```bash
# Daily backup
docker-compose exec db pg_dump -U postgres career_advisor > backup_$(date +%Y%m%d).sql
```

## Security Checklist

- [ ] Change default admin password
- [ ] Use strong DATABASE_URL password
- [ ] Enable SSL for database connections
- [ ] Set up firewall rules
- [ ] Enable database backups
- [ ] Rotate API keys regularly
- [ ] Review user permissions

## Support

For issues or questions:
1. Check logs: `docker-compose logs -f`
2. Review this documentation
3. Check migration files in `scripts/migrations/`
4. Contact: admin@lumix.ai

---

**Last Updated:** 2026-05-02
**Version:** 1.0.0
**Database Schema Version:** 004
