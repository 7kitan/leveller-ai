#!/bin/bash
# =============================================================================
# Deployment Script for Lumix AI
# Deploys backend and frontend services
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_DIR="$HOME/projects/A20-App-078"
BACKUP_DIR="$HOME/backups"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Lumix AI - Deployment Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if project directory exists
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}❌ Project directory not found: $PROJECT_DIR${NC}"
    echo "Please clone the repository first:"
    echo "  git clone https://github.com/a20-ai-thuc-chien/A20-App-078.git ~/projects/A20-App-078"
    exit 1
fi

cd "$PROJECT_DIR"

# Step 1: Backup database
echo -e "${YELLOW}[1/10] Creating database backup...${NC}"
mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/db_backup_$(date +%Y%m%d_%H%M%S).sql"

if docker ps | grep -q advisor_db_prod; then
    docker exec advisor_db_prod pg_dump -U postgres career_advisor > "$BACKUP_FILE" 2>/dev/null || echo "⚠️  No existing database to backup"
    if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
        gzip "$BACKUP_FILE"
        echo -e "${GREEN}✅ Backup created: $BACKUP_FILE.gz${NC}"
    fi
else
    echo "⚠️  Database container not running, skipping backup"
fi

# Step 2: Pull latest code
echo -e "${YELLOW}[2/10] Pulling latest code...${NC}"
git fetch origin
CURRENT_BRANCH=$(git branch --show-current)
echo "Current branch: $CURRENT_BRANCH"
git pull origin "$CURRENT_BRANCH"

# Step 3: Check .env files
echo -e "${YELLOW}[3/10] Checking environment files...${NC}"
if [ ! -f "$PROJECT_DIR/backend/.env" ]; then
    echo -e "${RED}❌ Backend .env file not found!${NC}"
    echo "Please create backend/.env from backend/.env.example"
    exit 1
fi

if [ ! -f "$PROJECT_DIR/frontend/.env" ]; then
    echo -e "${RED}❌ Frontend .env file not found!${NC}"
    echo "Please create frontend/.env from frontend/.env.example"
    exit 1
fi

echo -e "${GREEN}✅ Environment files found${NC}"

# Step 4: Create Docker network if not exists
echo -e "${YELLOW}[4/10] Checking Docker network...${NC}"
if ! docker network ls | grep -q advisor_net_prod; then
    docker network create advisor_net_prod
    echo -e "${GREEN}✅ Created Docker network${NC}"
else
    echo "✅ Docker network already exists"
fi

# Step 5: Deploy Backend
echo -e "${YELLOW}[5/10] Deploying backend services...${NC}"
cd "$PROJECT_DIR/backend"

# Build images
echo "Building backend images..."
docker compose -f docker-compose.prod.yml build

# Start database and redis first
echo "Starting database and redis..."
docker compose -f docker-compose.prod.yml up -d db redis

# Wait for database to be ready
echo "Waiting for database to be ready..."
sleep 15

# Check database health
if docker compose -f docker-compose.prod.yml exec -T db pg_isready -U postgres; then
    echo -e "${GREEN}✅ Database is ready${NC}"
else
    echo -e "${RED}❌ Database is not ready${NC}"
    exit 1
fi

# Step 6: Run migrations
echo -e "${YELLOW}[6/10] Running database migrations...${NC}"
docker compose -f docker-compose.prod.yml run --rm gateway python scripts/run_all_migrations.py || echo "⚠️  Migrations may have already been applied"

# Step 7: Start all backend services
echo -e "${YELLOW}[7/10] Starting all backend services...${NC}"
docker compose -f docker-compose.prod.yml up -d

# Wait for services to start
echo "Waiting for services to start..."
sleep 30

# Step 8: Health checks
echo -e "${YELLOW}[8/10] Running health checks...${NC}"

check_health() {
    local service=$1
    local url=$2
    local max_attempts=5
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ $service is healthy${NC}"
            return 0
        fi
        echo "Attempt $attempt/$max_attempts: $service not ready yet..."
        sleep 5
        attempt=$((attempt + 1))
    done

    echo -e "${RED}❌ $service health check failed${NC}"
    return 1
}

check_health "Gateway" "http://localhost:8000/health"
check_health "Auth Service" "http://localhost:8000/auth/health"
check_health "CV Service" "http://localhost:8000/cv/health"
check_health "JD Service" "http://localhost:8000/jd/health"
check_health "Analysis Service" "http://localhost:8000/analysis/health"

# Step 9: Deploy Frontend
echo -e "${YELLOW}[9/10] Deploying frontend...${NC}"
cd "$PROJECT_DIR/frontend"

docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# Wait for frontend
sleep 10

# Check frontend
if curl -f -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Frontend is running${NC}"
else
    echo -e "${RED}❌ Frontend health check failed${NC}"
fi

# Step 10: Summary
echo -e "${YELLOW}[10/10] Deployment summary...${NC}"
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Deployment Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}✅ Backend Services:${NC}"
docker compose -f "$PROJECT_DIR/backend/docker-compose.prod.yml" ps --format "table {{.Name}}\t{{.Status}}"
echo ""
echo -e "${GREEN}✅ Frontend Service:${NC}"
docker compose -f "$PROJECT_DIR/frontend/docker-compose.prod.yml" ps --format "table {{.Name}}\t{{.Status}}"
echo ""
echo -e "${YELLOW}📊 Quick Stats:${NC}"
docker exec advisor_db_prod psql -U postgres -d career_advisor -t -c "SELECT 'Users: ' || COUNT(*) FROM users;" 2>/dev/null || echo "Users: N/A"
docker exec advisor_db_prod psql -U postgres -d career_advisor -t -c "SELECT 'Courses: ' || COUNT(*) FROM courses;" 2>/dev/null || echo "Courses: N/A"
docker exec advisor_db_prod psql -U postgres -d career_advisor -t -c "SELECT 'Jobs: ' || COUNT(*) FROM jobs;" 2>/dev/null || echo "Jobs: N/A"
echo ""
echo -e "${GREEN}🌐 Access URLs:${NC}"
echo "  Backend API: http://localhost:8000"
echo "  Frontend: http://localhost:3000"
echo ""
echo -e "${YELLOW}📝 Next Steps:${NC}"
echo "  1. Configure Nginx reverse proxy"
echo "  2. Setup SSL certificates with certbot"
echo "  3. Import course data if needed"
echo "  4. Create admin user if needed"
echo ""
echo -e "${GREEN}✅ Deployment successful!${NC}"
