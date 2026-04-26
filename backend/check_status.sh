#!/bin/bash
# =============================================================================
# Production Status Check Script
# Check health and status of all services
# =============================================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Production Status Check${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check containers
echo -e "${YELLOW}📦 Container Status:${NC}"
docker compose -f docker-compose.prod.yml ps
echo ""

# Check health endpoints
echo -e "${YELLOW}🏥 Health Checks:${NC}"

check_health() {
    local service=$1
    local url=$2
    
    if curl -f -s "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $service${NC}"
    else
        echo -e "${RED}❌ $service${NC}"
    fi
}

check_health "Gateway        " "http://localhost:8000/health"
check_health "Auth Service   " "http://localhost:8000/auth/health"
check_health "CV Service     " "http://localhost:8000/cv/health"
check_health "JD Service     " "http://localhost:8000/jd/health"
check_health "Analysis Service" "http://localhost:8000/analysis/health"

echo ""

# Check database
echo -e "${YELLOW}💾 Database Status:${NC}"
if docker exec advisor_db_prod pg_isready -U postgres > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PostgreSQL is ready${NC}"
    
    # Show database stats
    docker exec advisor_db_prod psql -U postgres -d career_advisor -t -c "
        SELECT 
            'Users: ' || COUNT(*) 
        FROM users;
    " 2>/dev/null || echo "  Unable to query database"
    
    docker exec advisor_db_prod psql -U postgres -d career_advisor -t -c "
        SELECT 
            'CVs: ' || COUNT(*) 
        FROM user_cvs;
    " 2>/dev/null || echo "  Unable to query database"
    
    docker exec advisor_db_prod psql -U postgres -d career_advisor -t -c "
        SELECT 
            'Jobs: ' || COUNT(*) 
        FROM jobs;
    " 2>/dev/null || echo "  Unable to query database"
else
    echo -e "${RED}❌ PostgreSQL is not ready${NC}"
fi

echo ""

# Check Redis
echo -e "${YELLOW}🔴 Redis Status:${NC}"
if docker exec advisor_redis_prod redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis is ready${NC}"
else
    echo -e "${RED}❌ Redis is not ready${NC}"
fi

echo ""

# Check workers
echo -e "${YELLOW}👷 Worker Status:${NC}"
docker compose -f docker-compose.prod.yml ps | grep worker

echo ""

# Check disk usage
echo -e "${YELLOW}💿 Disk Usage:${NC}"
df -h | grep -E "Filesystem|/var/lib/docker" || df -h | head -2

echo ""

# Check recent errors
echo -e "${YELLOW}⚠️  Recent Errors (last 10):${NC}"
docker compose -f docker-compose.prod.yml logs --tail=100 | grep -i "error\|exception\|failed" | tail -10 || echo "No recent errors found"

echo ""
echo -e "${GREEN}Status check completed${NC}"
