#!/bin/bash
# =============================================================================
# Production Full Deployment & Setup Script
# Build, Setup Database, Run Migrations, Create Admin, and Start Services
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Backend Production Full Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Step 0: Check Environment
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Error: .env file not found!${NC}"
    exit 1
fi

# Step 1: Stop and Clean
echo -e "${YELLOW}[1/7] Stopping existing containers...${NC}"
docker compose -f docker-compose.prod.yml down
echo -e "${GREEN}✅ Containers stopped${NC}"
echo ""

# Step 2: Build Images
echo -e "${YELLOW}[2/7] Building all Docker images...${NC}"
docker compose -f docker-compose.prod.yml build
echo -e "${GREEN}✅ All images built successfully${NC}"
echo ""

# Step 3: Start Infrastructure
echo -e "${YELLOW}[3/7] Starting database and redis...${NC}"
docker compose -f docker-compose.prod.yml up -d db redis
echo "Waiting for database to be ready..."

# Check database health with retries
MAX_RETRIES=30
RETRY_COUNT=0
until docker compose -f docker-compose.prod.yml exec -T db pg_isready -U postgres > /dev/null 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT+1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo -e "${RED}❌ Database failed to start${NC}"
        exit 1
    fi
    echo -n "."
    sleep 2
done
echo -e "\n${GREEN}✅ Infrastructure is healthy${NC}"
echo ""

# Step 4: Database Core Setup (Schema, Extensions, Admin)
echo -e "${YELLOW}[4/7] Running Core Database Setup & Admin Creation...${NC}"
echo "This will create tables, extensions, and the admin user from .env"
docker compose -f docker-compose.prod.yml run --rm \
    --no-deps \
    gateway python3 scripts/setup_production.py

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Core setup failed${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Core database and admin ready${NC}"
echo ""

# Step 5: Run SQL Migrations (Prompts, Benchmarks, etc.)
echo -e "${YELLOW}[5/7] Running SQL Migrations...${NC}"
# Get all migration files and run them in order
for migration_file in scripts/migrations/*.sql; do
    if [ -f "$migration_file" ]; then
        filename=$(basename "$migration_file")
        echo "Executing $filename..."
        # Pipe file content directly to psql inside container
        docker compose -f docker-compose.prod.yml exec -T db psql -U postgres -d career_advisor < "$migration_file" > /dev/null 2>&1
    fi
done
echo -e "${GREEN}✅ All migrations applied${NC}"
echo ""

# Step 6: Start All Services & Workers
echo -e "${YELLOW}[6/7] Starting all services and workers...${NC}"
docker compose -f docker-compose.prod.yml up -d
echo "Waiting for services to initialize..."
sleep 15
echo -e "${GREEN}✅ All services started${NC}"
echo ""

# Step 7: Health Checks
echo -e "${YELLOW}[7/7] Running final health checks...${NC}"

check_health() {
    local service=$1
    local url=$2
    if curl -f -s "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $service is online${NC}"
    else
        echo -e "${RED}❌ $service is DOWN${NC}"
    fi
}

check_health "API Gateway" "http://localhost:8000/health"
check_health "Auth Service" "http://localhost:8000/auth/health"
check_health "CV Service" "http://localhost:8000/cv/health"

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Deployment Summary${NC}"
echo -e "${BLUE}========================================${NC}"
docker compose -f docker-compose.prod.yml ps
echo ""
echo -e "${GREEN}🎉 SYSTEM IS READY FOR PRODUCTION!${NC}"
echo -e "${YELLOW}Admin Login:${NC} Use the email/password defined in your .env"
echo ""
