# Team078 Backend

Career Advisor Platform - AI-powered CV analysis and job matching system.

## Quick Start

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 2. Start services
docker-compose up -d

# 3. Verify
curl http://localhost:8000/health
```

## Documentation

- **[SETUP.md](./SETUP.md)** - Complete setup guide
- **[API_ENDPOINTS.md](./API_ENDPOINTS.md)** - API documentation
- **[DATABASE_SETUP.md](./DATABASE_SETUP.md)** - Database configuration
- **[CORS_GUIDE.md](./CORS_GUIDE.md)** - CORS configuration
- **[IP_BLOCK_MANAGEMENT.md](./IP_BLOCK_MANAGEMENT.md)** - IP blocking API

## Architecture

```
Gateway (8000)
├── Auth Service      - Authentication & user management
├── CV Service        - CV parsing & analysis
├── JD Service        - Job description management
├── Analysis Service  - CV-JD gap analysis
├── Recommender       - Course recommendations
└── Admin Service     - Admin tools & settings

Database Layer
├── PostgreSQL        - Main database with pgvector
└── Redis             - Cache & Celery broker
```

## Authentication

Single long-lived access token (7 days):
- Token sent via `Authorization: Bearer <token>` header
- Stored in frontend localStorage
- No cookies, no refresh token

## Key Features

- ✅ AI-powered CV parsing
- ✅ Job description analysis
- ✅ Gap analysis & recommendations
- ✅ Course recommendations
- ✅ Admin dashboard
- ✅ IP-based rate limiting
- ✅ Role-based access control

## Environment Variables

Required variables in `.env`:

```bash
# Security (REQUIRED)
JWT_SECRET=your_jwt_secret_min_32_chars
REDIS_ENCRYPTION_KEY=your_fernet_key_here
GOOGLE_RECAPTCHA_SECRET_KEY=your_recaptcha_secret

# Database (REQUIRED)
POSTGRES_PASSWORD=your_db_password
REDIS_PASSWORD=your_redis_password

# AI Services (REQUIRED)
OPENAI_API_KEY=sk-proj-...
GOOGLE_API_KEY=AIza...

# Frontend (REQUIRED)
FRONTEND_URL=https://yourdomain.com
ALLOWED_ORIGINS=https://yourdomain.com,http://localhost:3000
```

See `.env.example` for complete configuration.

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
python scripts/run_migrations.py

# Start a service locally
cd services/auth_service
uvicorn main:app --reload --port 8001
```

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=services --cov-report=html

# Health check
curl http://localhost:8000/health
```

## Service Ports

- Gateway: 8000 (public)
- PostgreSQL: 5432
- Redis: 6379
- All other services: Internal only

## Troubleshooting

**Services not starting?**
```bash
docker-compose logs gateway
docker-compose restart gateway
```

**Database issues?**
```bash
docker-compose exec db psql -U postgres -d career_advisor -c "SELECT 1;"
```

**Redis issues?**
```bash
docker-compose exec redis redis-cli ping
```

See [SETUP.md](./SETUP.md) for detailed troubleshooting.

## Project Structure

```
backend/
├── services/           # Microservices
│   ├── auth_service/
│   ├── cv_service/
│   ├── jd_service/
│   ├── analysis_service/
│   ├── recommender_service/
│   └── admin_service/
├── gateway/           # API Gateway
├── shared/            # Shared utilities
├── worker/            # Celery workers
├── scripts/           # Deployment scripts
├── .env.example       # Environment template
└── docker-compose.yml # Docker configuration
```

## Support

- Documentation: `/docs/backend/`
- Health check: `http://localhost:8000/health`
- Logs: `docker-compose logs -f <service>`

---

**Version**: 2.0  
**Last Updated**: April 28, 2026  
**Status**: Production Ready
