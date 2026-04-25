#!/bin/bash
# =============================================================================
# Frontend Deployment Script for VPS
# Deploy Next.js frontend to production
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_DIR="${PROJECT_DIR:-/opt/k109}"
FRONTEND_DIR="$PROJECT_DIR/frontend"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Frontend Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if frontend directory exists
if [ ! -d "$FRONTEND_DIR" ]; then
    echo -e "${RED}❌ Frontend directory not found: $FRONTEND_DIR${NC}"
    exit 1
fi

cd "$FRONTEND_DIR"

# Step 1: Check .env file
echo -e "${YELLOW}[1/6] Checking environment configuration...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    echo ""
    echo "Please create .env file:"
    echo "  cd $FRONTEND_DIR"
    echo "  cp .env.example .env"
    echo "  vim .env"
    echo ""
    echo "Required variables:"
    echo "  NEXT_PUBLIC_API_URL=https://api.yourdomain.com"
    echo "  NEXT_PUBLIC_RECAPTCHA_SITE_KEY=your_site_key"
    exit 1
fi

echo -e "${GREEN}✅ Environment file found${NC}"

# Step 2: Pull latest code
echo -e "${YELLOW}[2/6] Pulling latest code...${NC}"
cd "$PROJECT_DIR"
git pull origin $(git branch --show-current)

# Step 3: Stop existing container
echo -e "${YELLOW}[3/6] Stopping existing frontend container...${NC}"
cd "$FRONTEND_DIR"
docker compose -f docker-compose.prod.yml down || echo "No existing container to stop"

# Step 4: Build new image
echo -e "${YELLOW}[4/6] Building frontend image...${NC}"
docker compose -f docker-compose.prod.yml build --no-cache

# Step 5: Start container
echo -e "${YELLOW}[5/6] Starting frontend container...${NC}"
docker compose -f docker-compose.prod.yml up -d

# Wait for container to start
echo "Waiting for frontend to start..."
sleep 10

# Step 6: Health check
echo -e "${YELLOW}[6/6] Running health check...${NC}"

MAX_ATTEMPTS=10
ATTEMPT=1

while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
    if curl -f -s http://localhost:3000 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Frontend is running!${NC}"
        break
    fi
    
    if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
        echo -e "${RED}❌ Frontend health check failed after $MAX_ATTEMPTS attempts${NC}"
        echo ""
        echo "Check logs:"
        echo "  docker compose -f $FRONTEND_DIR/docker-compose.prod.yml logs"
        exit 1
    fi
    
    echo "Attempt $ATTEMPT/$MAX_ATTEMPTS: Frontend not ready yet..."
    sleep 5
    ATTEMPT=$((ATTEMPT + 1))
done

# Summary
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Deployment Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}✅ Frontend Status:${NC}"
docker compose -f "$FRONTEND_DIR/docker-compose.prod.yml" ps
echo ""
echo -e "${GREEN}🌐 Access URLs:${NC}"
echo "  Local: http://localhost:3000"
echo "  Public: https://yourdomain.com (after Nginx setup)"
echo ""
echo -e "${YELLOW}📝 Next Steps:${NC}"
echo "  1. Configure Nginx reverse proxy (if not done)"
echo "  2. Setup SSL with certbot"
echo "  3. Test the application"
echo ""
echo -e "${YELLOW}📊 View Logs:${NC}"
echo "  docker compose -f $FRONTEND_DIR/docker-compose.prod.yml logs -f"
echo ""
echo -e "${GREEN}✅ Frontend deployment successful!${NC}"
