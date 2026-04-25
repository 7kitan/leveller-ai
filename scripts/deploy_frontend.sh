#!/bin/bash
# =============================================================================
# Frontend Deployment Script for VPS - UPDATED
# Deploy Next.js frontend to production with correct API URL
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

# Step 1: Create .env file with production values
echo -e "${YELLOW}[1/7] Creating .env file...${NC}"
cat > .env << 'EOF'
NEXT_PUBLIC_API_URL=https://api.onehub.cfd
NEXT_PUBLIC_RECAPTCHA_SITE_KEY=6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI
NEXT_PUBLIC_ENVIRONMENT=production
EOF

echo -e "${GREEN}✅ .env file created${NC}"
cat .env

# Step 2: Pull latest code
echo -e "${YELLOW}[2/7] Pulling latest code...${NC}"
cd "$PROJECT_DIR"
git pull origin $(git branch --show-current)

# Step 3: Stop existing container
echo -e "${YELLOW}[3/7] Stopping existing frontend container...${NC}"
cd "$FRONTEND_DIR"
docker compose -f docker-compose.prod.yml down || echo "No existing container to stop"

# Step 4: Remove old image
echo -e "${YELLOW}[4/7] Removing old image...${NC}"
docker rmi $(docker images -q advisor_frontend_prod) -f 2>/dev/null || echo "No old image to remove"

# Step 5: Build new image
echo -e "${YELLOW}[5/7] Building frontend image...${NC}"
echo "This will take a few minutes..."
docker compose -f docker-compose.prod.yml build --no-cache

# Step 6: Start container
echo -e "${YELLOW}[6/7] Starting frontend container...${NC}"
docker compose -f docker-compose.prod.yml up -d

# Wait for container to start
echo "Waiting for frontend to start..."
sleep 10

# Step 7: Health check and verify
echo -e "${YELLOW}[7/7] Running health check and verification...${NC}"

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
        echo "  docker logs advisor_frontend_prod"
        exit 1
    fi
    
    echo "Attempt $ATTEMPT/$MAX_ATTEMPTS: Frontend not ready yet..."
    sleep 5
    ATTEMPT=$((ATTEMPT + 1))
done

# Verify API URL in built files
echo ""
echo -e "${YELLOW}Verifying API URL in built files...${NC}"
if docker exec advisor_frontend_prod sh -c "grep -r 'api.onehub.cfd' /app/.next/ 2>/dev/null | head -1" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API URL correctly embedded in build!${NC}"
else
    echo -e "${RED}⚠️  Warning: Could not verify API URL in built files${NC}"
    echo "Check manually: docker exec advisor_frontend_prod sh -c \"grep -r 'api.onehub.cfd' /app/.next/\""
fi

# Summary
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Deployment Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}✅ Frontend Status:${NC}"
docker ps --filter "name=advisor_frontend_prod" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo -e "${GREEN}🌐 Access URLs:${NC}"
echo "  Local: http://localhost:3000"
echo "  Public: https://onehub.cfd"
echo ""
echo -e "${YELLOW}📝 Environment Variables:${NC}"
docker exec advisor_frontend_prod env | grep NEXT_PUBLIC || echo "  (Not set in runtime - embedded at build time)"
echo ""
echo -e "${YELLOW}📊 View Logs:${NC}"
echo "  docker logs -f advisor_frontend_prod"
echo ""
echo -e "${GREEN}✅ Frontend deployment successful!${NC}"
