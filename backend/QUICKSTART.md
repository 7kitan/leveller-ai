# Quick Start - Production Setup

## One-Command Setup for New Server

### Prerequisites
- Docker and Docker Compose installed
- Git repository cloned

### Setup Steps

```bash
# 1. Navigate to backend directory
cd backend

# 2. Copy environment file
cp .env.example .env

# 3. Edit .env with your production values
nano .env  # or vim, or any editor

# Required changes:
# - DEFAULT_ADMIN_EMAIL=your-email@domain.com
# - DEFAULT_ADMIN_PASSWORD=YourSecurePassword123!
# - DATABASE_URL=postgresql://postgres:your-password@db:5432/career_advisor

# 4. Make script executable
chmod +x scripts/setup_production.sh

# 5. Run production setup (ONE COMMAND!)
./scripts/setup_production.sh
```

That's it! The script will:
- ✅ Check all prerequisites
- ✅ Start database and Redis
- ✅ Build gateway service
- ✅ Enable PostgreSQL extensions (pgvector, pg_trgm)
- ✅ Create all 18 tables
- ✅ Run all 4 migrations
- ✅ Create admin user
- ✅ Verify setup

### What Gets Set Up

**Database:**
- 18 tables with proper indexes
- 4 migrations applied (job sections, indexes, CV soft delete, vector optimization)
- PostgreSQL extensions: pgvector, pg_trgm

**Admin User:**
- Email: from .env (DEFAULT_ADMIN_EMAIL)
- Password: from .env (DEFAULT_ADMIN_PASSWORD)
- Role: admin

**Optimizations:**
- Jobs table: text search only (no vectors)
- Courses/Skills: vector search enabled
- GIN indexes for fast ILIKE queries
- Composite indexes for common patterns

### After Setup

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f gateway

# Test API
curl http://localhost:8000/health
open http://localhost:8000/docs

# Test admin login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@lumix.ai","password":"Admin@123"}'
```

### Troubleshooting

**Issue: "docker-compose.yml not found"**
```bash
# Make sure you're in backend directory
cd backend
pwd  # Should show: .../Team078/backend
```

**Issue: "Database failed to start"**
```bash
# Check database logs
docker-compose logs db

# Common fix: remove old volumes
docker-compose down -v
./scripts/setup_production.sh
```

**Issue: "Setup script failed"**
```bash
# Check .env file
cat .env | grep DATABASE_URL

# Verify database connection
docker-compose exec db psql -U postgres -c '\l'
```

**Issue: "Permission denied"**
```bash
# Make script executable
chmod +x scripts/setup_production.sh
```

### Re-running Setup

The script is **idempotent** - safe to run multiple times:
- Existing tables: skipped
- Applied migrations: skipped
- Existing admin: skipped

```bash
# Safe to re-run
./scripts/setup_production.sh
```

### Manual Verification

```bash
# Check tables
docker-compose exec db psql -U postgres -d career_advisor -c "\dt"

# Check migrations
docker-compose exec db psql -U postgres -d career_advisor -c "SELECT * FROM schema_migrations;"

# Check admin user
docker-compose exec db psql -U postgres -d career_advisor -c "SELECT email, role FROM users WHERE role='admin';"

# Check indexes
docker-compose exec db psql -U postgres -d career_advisor -c "\d jobs"
```

### Production Checklist

Before going live:
- [ ] Change default admin password in .env
- [ ] Use strong DATABASE_URL password
- [ ] Set OPENAI_API_KEY (optional, for course recommendations)
- [ ] Enable SSL for database connections
- [ ] Set up firewall rules
- [ ] Configure backups
- [ ] Review security settings

### Support

For detailed documentation, see:
- `PRODUCTION_SETUP.md` - Complete setup guide
- `scripts/migrations/` - Migration files
- `scripts/setup_production.py` - Python setup script

---

**Time to setup:** ~5 minutes  
**Commands needed:** 1 (after .env configuration)  
**Safe to re-run:** Yes (idempotent)
