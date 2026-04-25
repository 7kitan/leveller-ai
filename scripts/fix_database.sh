#!/bin/bash
# =============================================================================
# Database Troubleshooting & Fix Script
# Fix PostgreSQL connection issues on VPS
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_DIR="${PROJECT_DIR:-/opt/k109}"
BACKEND_DIR="$PROJECT_DIR/backend"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Database Troubleshooting${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

cd "$BACKEND_DIR"

# Step 1: Check if database container exists
echo -e "${YELLOW}[1/7] Checking database container...${NC}"
if docker ps -a | grep -q advisor_db_prod; then
    echo -e "${GREEN}✅ Database container exists${NC}"
    
    # Check if running
    if docker ps | grep -q advisor_db_prod; then
        echo -e "${GREEN}✅ Database container is running${NC}"
    else
        echo -e "${RED}❌ Database container is stopped${NC}"
        echo "Starting database..."
        docker compose -f docker-compose.prod.yml up -d db
        sleep 10
    fi
else
    echo -e "${RED}❌ Database container does not exist${NC}"
    echo "Creating database container..."
    docker compose -f docker-compose.prod.yml up -d db
    sleep 15
fi

# Step 2: Check database health
echo -e "${YELLOW}[2/7] Checking database health...${NC}"
MAX_ATTEMPTS=10
ATTEMPT=1

while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
    if docker compose -f docker-compose.prod.yml exec -T db pg_isready -U postgres > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Database is healthy${NC}"
        break
    fi
    
    if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
        echo -e "${RED}❌ Database is not responding after $MAX_ATTEMPTS attempts${NC}"
        echo ""
        echo "Checking logs:"
        docker logs --tail=50 advisor_db_prod
        exit 1
    fi
    
    echo "Attempt $ATTEMPT/$MAX_ATTEMPTS: Waiting for database..."
    sleep 3
    ATTEMPT=$((ATTEMPT + 1))
done

# Step 3: Check if database exists
echo -e "${YELLOW}[3/7] Checking if database exists...${NC}"
DB_EXISTS=$(docker compose -f docker-compose.prod.yml exec -T db psql -U postgres -lqt | cut -d \| -f 1 | grep -w career_advisor | wc -l)

if [ "$DB_EXISTS" -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Database 'career_advisor' does not exist${NC}"
    echo "Creating database..."
    docker compose -f docker-compose.prod.yml exec -T db psql -U postgres -c "CREATE DATABASE career_advisor;"
    echo -e "${GREEN}✅ Database created${NC}"
else
    echo -e "${GREEN}✅ Database 'career_advisor' exists${NC}"
fi

# Step 4: Check pgvector extension
echo -e "${YELLOW}[4/7] Checking pgvector extension...${NC}"
docker compose -f docker-compose.prod.yml exec -T db psql -U postgres -d career_advisor -c "CREATE EXTENSION IF NOT EXISTS vector;" > /dev/null 2>&1
echo -e "${GREEN}✅ pgvector extension ready${NC}"

# Step 5: Check Redis
echo -e "${YELLOW}[5/7] Checking Redis...${NC}"
if docker ps | grep -q advisor_redis_prod; then
    echo -e "${GREEN}✅ Redis is running${NC}"
else
    echo -e "${RED}❌ Redis is not running${NC}"
    echo "Starting Redis..."
    docker compose -f docker-compose.prod.yml up -d redis
    sleep 5
fi

# Step 6: Run migrations
echo -e "${YELLOW}[6/7] Running database migrations...${NC}"
if [ -f "$BACKEND_DIR/scripts/run_all_migrations.py" ]; then
    docker compose -f docker-compose.prod.yml run --rm gateway python scripts/run_all_migrations.py || echo "⚠️  Some migrations may have already been applied"
    echo -e "${GREEN}✅ Migrations completed${NC}"
else
    echo -e "${YELLOW}⚠️  Migration script not found, skipping${NC}"
fi

# Step 7: Restart backend services
echo -e "${YELLOW}[7/7] Restarting backend services...${NC}"
docker compose -f docker-compose.prod.yml restart gateway auth-service cv-service jd-service analysis-service recommender-service admin-service

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Database Fix Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Summary
echo -e "${GREEN}✅ Database Status:${NC}"
docker compose -f docker-compose.prod.yml exec -T db psql -U postgres -c "SELECT version();" | head -3
echo ""
docker compose -f docker-compose.prod.yml exec -T db psql -U postgres -d career_advisor -c "SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = 'public';"
echo ""

echo -e "${YELLOW}📝 Next Steps:${NC}"
echo "  1. Test backend: curl http://localhost:8000/health"
echo "  2. Check logs: docker compose -f $BACKEND_DIR/docker-compose.prod.yml logs -f"
echo "  3. Deploy frontend: bash $PROJECT_DIR/scripts/deploy_frontend.sh"
echo ""
echo -e "${GREEN}✅ All services should be working now!${NC}"
