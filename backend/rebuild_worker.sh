#!/bin/bash
# =============================================================================
# Quick Rebuild Worker Script
# Rebuild and restart only the CV parser worker (for DOCX fixes)
# =============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Rebuild CV Parser Worker${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${YELLOW}[1/4] Building worker image...${NC}"
docker compose -f docker-compose.prod.yml build worker-cv-parser
echo -e "${GREEN}✅ Worker image built${NC}"
echo ""

echo -e "${YELLOW}[2/4] Stopping old worker...${NC}"
docker compose -f docker-compose.prod.yml stop worker-cv-parser
echo -e "${GREEN}✅ Worker stopped${NC}"
echo ""

echo -e "${YELLOW}[3/4] Starting new worker...${NC}"
docker compose -f docker-compose.prod.yml up -d worker-cv-parser
echo "Waiting for worker to connect..."
sleep 10
echo -e "${GREEN}✅ Worker started${NC}"
echo ""

echo -e "${YELLOW}[4/4] Verifying python-docx installation...${NC}"
if docker exec advisor_worker_cv_parser_prod python -c "import docx; print('python-docx version:', docx.__version__)" 2>/dev/null; then
    echo -e "${GREEN}✅ python-docx is installed and working${NC}"
else
    echo -e "${RED}❌ python-docx verification failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 Worker rebuild completed!${NC}"
echo ""
echo "Monitor worker logs:"
echo "  docker logs -f advisor_worker_cv_parser_prod"
