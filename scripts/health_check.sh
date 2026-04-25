#!/bin/bash
# =============================================================================
# Health Check Script
# Check status of all services and system resources
# =============================================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_DIR="$HOME/projects/A20-App-078"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Lumix AI - Health Check${NC}"
echo -e "${BLUE}  $(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# System Resources
echo -e "${YELLOW}📊 System Resources${NC}"
echo "---"
echo -e "${GREEN}CPU:${NC}"
top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print "  Usage: " 100 - $1 "%"}'

echo -e "${GREEN}Memory:${NC}"
free -h | awk 'NR==2{printf "  Used: %s / %s (%.2f%%)\n", $3, $2, $3*100/$2}'

echo -e "${GREEN}Disk:${NC}"
df -h / | awk 'NR==2{printf "  Used: %s / %s (%s)\n", $3, $2, $5}'
echo ""

# Docker Status
echo -e "${YELLOW}🐳 Docker Containers${NC}"
echo "---"
if command -v docker &> /dev/null; then
    if docker ps &> /dev/null; then
        RUNNING=$(docker ps --format "{{.Names}}" | grep advisor | wc -l)
        TOTAL=$(docker ps -a --format "{{.Names}}" | grep advisor | wc -l)
        echo -e "${GREEN}Running: $RUNNING / $TOTAL${NC}"
        echo ""
        docker ps --filter "name=advisor" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -20
    else
        echo -e "${RED}❌ Cannot connect to Docker daemon${NC}"
    fi
else
    echo -e "${RED}❌ Docker not installed${NC}"
fi
echo ""

# Backend Services Health
echo -e "${YELLOW}🔧 Backend Services${NC}"
echo "---"

check_service() {
    local name=$1
    local url=$2
    
    if curl -f -s -m 5 "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $name${NC}"
        return 0
    else
        echo -e "${RED}❌ $name${NC}"
        return 1
    fi
}

check_service "Gateway" "http://localhost:8000/health"
check_service "Auth Service" "http://localhost:8000/auth/health"
check_service "CV Service" "http://localhost:8000/cv/health"
check_service "JD Service" "http://localhost:8000/jd/health"
check_service "Analysis Service" "http://localhost:8000/analysis/health"
check_service "Recommender Service" "http://localhost:8000/recommend/health"
check_service "Admin Service" "http://localhost:8000/admin/health"
echo ""

# Frontend Health
echo -e "${YELLOW}🌐 Frontend${NC}"
echo "---"
check_service "Frontend" "http://localhost:3000"
echo ""

# Database Status
echo -e "${YELLOW}💾 Database${NC}"
echo "---"
if docker ps | grep -q advisor_db_prod; then
    if docker exec advisor_db_prod pg_isready -U postgres &> /dev/null; then
        echo -e "${GREEN}✅ PostgreSQL is ready${NC}"
        
        # Database size
        DB_SIZE=$(docker exec advisor_db_prod psql -U postgres -d career_advisor -t -c "SELECT pg_size_pretty(pg_database_size('career_advisor'));" 2>/dev/null | xargs)
        echo "  Size: $DB_SIZE"
        
        # Connection count
        CONN_COUNT=$(docker exec advisor_db_prod psql -U postgres -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | xargs)
        echo "  Connections: $CONN_COUNT"
        
        # Table counts
        echo ""
        echo "  Data Statistics:"
        docker exec advisor_db_prod psql -U postgres -d career_advisor -t -c "SELECT '    Users: ' || COUNT(*) FROM users;" 2>/dev/null | xargs
        docker exec advisor_db_prod psql -U postgres -d career_advisor -t -c "SELECT '    CVs: ' || COUNT(*) FROM user_cv;" 2>/dev/null | xargs
        docker exec advisor_db_prod psql -U postgres -d career_advisor -t -c "SELECT '    Jobs: ' || COUNT(*) FROM jobs;" 2>/dev/null | xargs
        docker exec advisor_db_prod psql -U postgres -d career_advisor -t -c "SELECT '    Courses: ' || COUNT(*) FROM courses;" 2>/dev/null | xargs
        docker exec advisor_db_prod psql -U postgres -d career_advisor -t -c "SELECT '    Analyses: ' || COUNT(*) FROM user_analysis;" 2>/dev/null | xargs
    else
        echo -e "${RED}❌ PostgreSQL is not ready${NC}"
    fi
else
    echo -e "${RED}❌ Database container not running${NC}"
fi
echo ""

# Redis Status
echo -e "${YELLOW}⚡ Redis${NC}"
echo "---"
if docker ps | grep -q advisor_redis_prod; then
    if docker exec advisor_redis_prod redis-cli ping &> /dev/null; then
        echo -e "${GREEN}✅ Redis is ready${NC}"
        
        # Redis info
        REDIS_KEYS=$(docker exec advisor_redis_prod redis-cli DBSIZE 2>/dev/null | awk '{print $2}')
        REDIS_MEM=$(docker exec advisor_redis_prod redis-cli INFO memory 2>/dev/null | grep "used_memory_human" | cut -d: -f2 | tr -d '\r')
        echo "  Keys: $REDIS_KEYS"
        echo "  Memory: $REDIS_MEM"
    else
        echo -e "${RED}❌ Redis is not ready${NC}"
    fi
else
    echo -e "${RED}❌ Redis container not running${NC}"
fi
echo ""

# Celery Workers
echo -e "${YELLOW}⚙️  Celery Workers${NC}"
echo "---"
WORKER_COUNT=$(docker ps --filter "name=advisor_worker" --format "{{.Names}}" | wc -l)
if [ $WORKER_COUNT -gt 0 ]; then
    echo -e "${GREEN}✅ $WORKER_COUNT workers running${NC}"
    docker ps --filter "name=advisor_worker" --format "  - {{.Names}}: {{.Status}}"
else
    echo -e "${RED}❌ No workers running${NC}"
fi
echo ""

# Recent Errors
echo -e "${YELLOW}⚠️  Recent Errors (Last 10)${NC}"
echo "---"
if [ -d "$PROJECT_DIR/backend" ]; then
    cd "$PROJECT_DIR/backend"
    ERROR_COUNT=$(docker compose -f docker-compose.prod.yml logs --tail=100 2>/dev/null | grep -i "error\|critical\|exception" | wc -l)
    if [ $ERROR_COUNT -gt 0 ]; then
        echo -e "${RED}Found $ERROR_COUNT errors in logs${NC}"
        docker compose -f docker-compose.prod.yml logs --tail=100 2>/dev/null | grep -i "error\|critical\|exception" | tail -10
    else
        echo -e "${GREEN}No recent errors found${NC}"
    fi
else
    echo "Project directory not found"
fi
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Summary${NC}"
echo -e "${BLUE}========================================${NC}"

TOTAL_CHECKS=10
PASSED_CHECKS=0

# Count passed checks
curl -f -s -m 5 "http://localhost:8000/health" > /dev/null 2>&1 && ((PASSED_CHECKS++))
curl -f -s -m 5 "http://localhost:3000" > /dev/null 2>&1 && ((PASSED_CHECKS++))
docker ps | grep -q advisor_db_prod && ((PASSED_CHECKS++))
docker ps | grep -q advisor_redis_prod && ((PASSED_CHECKS++))
docker ps | grep -q advisor_gateway_prod && ((PASSED_CHECKS++))
docker ps | grep -q advisor_auth_prod && ((PASSED_CHECKS++))
docker ps | grep -q advisor_cv_prod && ((PASSED_CHECKS++))
docker ps | grep -q advisor_jd_prod && ((PASSED_CHECKS++))
docker ps | grep -q advisor_analysis_prod && ((PASSED_CHECKS++))
[ $WORKER_COUNT -gt 0 ] && ((PASSED_CHECKS++))

HEALTH_PERCENT=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))

if [ $HEALTH_PERCENT -ge 90 ]; then
    echo -e "${GREEN}✅ System Health: $HEALTH_PERCENT% ($PASSED_CHECKS/$TOTAL_CHECKS checks passed)${NC}"
elif [ $HEALTH_PERCENT -ge 70 ]; then
    echo -e "${YELLOW}⚠️  System Health: $HEALTH_PERCENT% ($PASSED_CHECKS/$TOTAL_CHECKS checks passed)${NC}"
else
    echo -e "${RED}❌ System Health: $HEALTH_PERCENT% ($PASSED_CHECKS/$TOTAL_CHECKS checks passed)${NC}"
fi

echo ""
