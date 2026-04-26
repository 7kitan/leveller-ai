#!/bin/bash
# =============================================================================
# Production Backend Deployment Script
# Build and run all backend services without git pull
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Backend Production Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Step 1: Stop existing containers
echo -e "${YELLOW}[1/6] Stopping existing containers...${NC}"
docker compose -f docker-compose.prod.yml down
echo -e "${GREEN}✅ Containers stopped${NC}"
echo ""

# Step 2: Build all images
echo -e "${YELLOW}[2/6] Building all Docker images...${NC}"
echo "This may take 5-10 minutes..."
docker compose -f docker-compose.prod.yml build --no-cache
echo -e "${GREEN}✅ All images built successfully${NC}"
echo ""

# Step 3: Start database and redis first
echo -e "${YELLOW}[3/6] Starting database and redis...${NC}"
docker compose -f docker-compose.prod.yml up -d db redis
echo "Waiting for database and redis to be healthy..."
sleep 15

# Check database health
if docker compose -f docker-compose.prod.yml exec -T db pg_isready -U postgres > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Database is healthy${NC}"
else
    echo -e "${RED}❌ Database is not ready${NC}"
    exit 1
fi

# Check redis health
if docker compose -f docker-compose.prod.yml exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis is healthy${NC}"
else
    echo -e "${RED}❌ Redis is not ready${NC}"
    exit 1
fi
echo ""

# Step 4: Start all services
echo -e "${YELLOW}[4/6] Starting all backend services...${NC}"
docker compose -f docker-compose.prod.yml up -d \
    gateway \
    auth-service \
    cv-service \
    jd-service \
    analysis-service \
    recommender-service \
    admin-service

echo "Waiting for services to start..."
sleep 20
echo -e "${GREEN}✅ All services started${NC}"
echo ""

# Step 5: Start all workers
echo -e "${YELLOW}[5/6] Starting all workers...${NC}"
docker compose -f docker-compose.prod.yml up -d \
    worker-cv-parser \
    worker-analysis \
    worker-market-stats \
    worker-email \
    celery-beat

echo "Waiting for workers to connect..."
sleep 10
echo -e "${GREEN}✅ All workers started${NC}"
echo ""

# Step 6: Health checks and status
echo -e "${YELLOW}[6/6] Running health checks...${NC}"

check_health() {
    local service=$1
    local url=$2
    
    if curl -f -s "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $service is healthy${NC}"
        return 0
    else
        echo -e "${RED}❌ $service health check failed${NC}"
        return 1
    fi
}

# Check services
check_health "Gateway" "http://localhost:8000/health"
check_health "Auth Service" "http://localhost:8000/auth/health"
check_health "CV Service" "http://localhost:8000/cv/health"
check_health "JD Service" "http://localhost:8000/jd/health"
check_health "Analysis Service" "http://localhost:8000/analysis/health"

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Deployment Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Show all containers status
echo -e "${GREEN}📦 Container Status:${NC}"
docker compose -f docker-compose.prod.yml ps

echo ""
echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo ""
echo -e "${YELLOW}📝 Next Steps:${NC}"
echo "  1. Check logs: docker compose -f docker-compose.prod.yml logs -f"
echo "  2. Monitor workers: docker logs -f advisor_worker_cv_parser_prod"
echo "  3. Test API: curl http://localhost:8000/health"
echo ""
