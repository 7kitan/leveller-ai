# Backend Setup Guide

## Prerequisites

- Docker & Docker Compose
- Python 3.10+ (for local development)
- PostgreSQL 14+ with pgvector extension
- Redis 7+

## Quick Start (Docker)

### 1. Clone and Configure

```bash
cd backend
cp .env.example .env
```

### 2. Configure Environment Variables

Edit `.env` file with your values:

```bash
# Required - Security
JWT_SECRET=your_jwt_secret_min_32_chars
REDIS_ENCRYPTION_KEY=your_fernet_key_here
GOOGLE_RECAPTCHA_SECRET_KEY=your_recaptcha_secret_key

# Required - Database
POSTGRES_PASSWORD=your_secure_db_password
REDIS_PASSWORD=your_secure_redis_password

# Required - AI Services
OPENAI_API_KEY=sk-proj-...
GOOGLE_API_KEY=AIza...  # For Gemini AI and YouTube

# Required - Frontend
FRONTEND_URL=https://yourdomain.com
ALLOWED_ORIGINS=https://yourdomain.com,http://localhost:3000
```

Generate secure secrets:
```bash
# JWT Secret
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Redis Encryption Key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 3. Start Services

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f gateway
docker-compose logs -f auth-service
```

### 4. Verify Installation

```bash
# Health check
curl http://localhost:8000/health

# Expected response:
# {"status":"ok","service":"gateway"}
```

## Architecture

### Services

- **Gateway** (Port 8000) - API Gateway, routing, auth middleware
- **Auth Service** - Authentication, user management
- **CV Service** - CV parsing, storage, management
- **JD Service** - Job description management
- **Analysis Service** - Gap analysis, recommendations
- **Recommender Service** - Course recommendations
- **Admin Service** - Admin panel, system settings
- **Workers** - Celery workers for async tasks
  - `worker_default` - General tasks
  - `worker_parsing` - CV parsing
  - `worker_analysis` - Gap analysis
  - `worker_crawler` - Web scraping

### Databases

- **PostgreSQL** (Port 5432) - Main database with pgvector
- **Redis** (Port 6379) - Cache, sessions, Celery broker

## Authentication Flow

### 1. Login/Register

```bash
POST /auth/login
POST /auth/register

# Response includes access_token
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {...},
  "expires_in": 604800  # 7 days
}
```

### 2. Store Token

Frontend stores token in localStorage:
```javascript
localStorage.setItem('auth_token', access_token);
```

### 3. Make Authenticated Requests

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/auth/me
```

### 4. Token Expiry

- Token TTL: 7 days
- On 401 error: Redirect to login
- No automatic refresh (simplified auth)

## Development

### Local Development (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
python scripts/run_migrations.py

# Start a service
cd services/auth_service
uvicorn main:app --reload --port 8001

# Start gateway
cd gateway
uvicorn main:app --reload --port 8000
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific service tests
pytest services/auth_service/tests/

# With coverage
pytest --cov=services --cov-report=html
```

### Database Migrations

Migrations run automatically on startup. Manual run:

```bash
python scripts/run_migrations.py
```

See [DATABASE_SETUP.md](./DATABASE_SETUP.md) for details.

## Configuration

### AI Model Settings

AI models are configured in Admin UI (stored in database):
- `AI_MODEL` - Default model (gpt-4o-mini)
- `GAP_LLM_MODEL` - Gap analysis model
- `FALLBACK_AI_MODEL` - Fallback model

### Worker Concurrency

Configured in docker-compose.yml:
```yaml
worker_parsing:
  command: celery -A worker.celery_app worker -Q parsing --concurrency=2
```

### CORS Configuration

See [CORS_GUIDE.md](./CORS_GUIDE.md) for detailed examples.

## Troubleshooting

### Service won't start

```bash
# Check logs
docker-compose logs service-name

# Restart service
docker-compose restart service-name

# Rebuild if code changed
docker-compose build service-name
docker-compose up -d service-name
```

### Database connection issues

```bash
# Check PostgreSQL is running
docker-compose ps db

# Check connection
docker-compose exec db psql -U postgres -d career_advisor -c "SELECT 1;"
```

### Redis connection issues

```bash
# Check Redis is running
docker-compose ps redis

# Test connection
docker-compose exec redis redis-cli ping
# Expected: PONG

# With password
docker-compose exec redis redis-cli -a YOUR_PASSWORD ping
```

### Token authentication fails

1. Check JWT_SECRET is set in .env
2. Verify token is sent in Authorization header
3. Check token hasn't expired (7 days)
4. Verify Redis is running (tokens cached there)

### Worker tasks not processing

```bash
# Check worker logs
docker-compose logs -f worker_default

# Check Celery connection to Redis
docker-compose exec worker_default celery -A worker.celery_app inspect ping
```

## Production Deployment

### Security Checklist

- [ ] Set strong JWT_SECRET (min 32 chars)
- [ ] Set REDIS_ENCRYPTION_KEY
- [ ] Set REDIS_PASSWORD
- [ ] Set POSTGRES_PASSWORD
- [ ] Set ENVIRONMENT=production
- [ ] Configure ALLOWED_ORIGINS correctly
- [ ] Enable HTTPS (secure cookies)
- [ ] Set up firewall rules
- [ ] Regular backups of PostgreSQL

### Performance Tuning

1. **Database Indexes** - Already optimized (25+ indexes)
2. **Redis Cache** - Token caching enabled
3. **Worker Concurrency** - Adjust based on CPU cores
4. **Connection Pooling** - Configured in database.py

### Monitoring

```bash
# Service health
curl http://localhost:8000/health

# Database connections
docker-compose exec db psql -U postgres -d career_advisor \
  -c "SELECT count(*) FROM pg_stat_activity;"

# Redis memory usage
docker-compose exec redis redis-cli info memory
```

## API Documentation

See [API_ENDPOINTS.md](./API_ENDPOINTS.md) for complete endpoint documentation.
