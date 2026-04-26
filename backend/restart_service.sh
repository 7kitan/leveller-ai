#!/bin/bash
# =============================================================================
# Restart Individual Service Script
# Quickly restart a specific service without full rebuild
# =============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

if [ -z "$1" ]; then
    echo -e "${RED}Usage: $0 <service-name>${NC}"
    echo ""
    echo "Available services:"
    echo "  - gateway"
    echo "  - auth-service"
    echo "  - cv-service"
    echo "  - jd-service"
    echo "  - analysis-service"
    echo "  - recommender-service"
    echo "  - admin-service"
    echo "  - worker-cv-parser"
    echo "  - worker-analysis"
    echo "  - worker-market-stats"
    echo "  - worker-email"
    echo "  - celery-beat"
    exit 1
fi

SERVICE=$1

echo -e "${YELLOW}Restarting $SERVICE...${NC}"

# Restart the service
docker compose -f docker-compose.prod.yml restart $SERVICE

# Wait a bit
sleep 5

# Check status
if docker compose -f docker-compose.prod.yml ps $SERVICE | grep -q "Up"; then
    echo -e "${GREEN}✅ $SERVICE restarted successfully${NC}"
    
    # Show logs
    echo ""
    echo -e "${YELLOW}Recent logs:${NC}"
    docker compose -f docker-compose.prod.yml logs --tail=20 $SERVICE
else
    echo -e "${RED}❌ $SERVICE failed to restart${NC}"
    exit 1
fi
