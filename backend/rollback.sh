#!/bin/bash
# =============================================================================
# Rollback Script
# Stop current deployment and restore from backup
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${RED}========================================${NC}"
echo -e "${RED}  ROLLBACK WARNING${NC}"
echo -e "${RED}========================================${NC}"
echo ""
echo -e "${YELLOW}This will:${NC}"
echo "  1. Stop all current containers"
echo "  2. Restore database from latest backup"
echo "  3. Restart services with previous images"
echo ""
read -p "Are you sure you want to rollback? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Rollback cancelled"
    exit 0
fi

echo ""
echo -e "${YELLOW}[1/4] Stopping all containers...${NC}"
docker compose -f docker-compose.prod.yml down
echo -e "${GREEN}✅ Containers stopped${NC}"
echo ""

echo -e "${YELLOW}[2/4] Finding latest database backup...${NC}"
BACKUP_DIR="$HOME/backups"
LATEST_BACKUP=$(ls -t $BACKUP_DIR/db_backup_*.sql.gz 2>/dev/null | head -1)

if [ -z "$LATEST_BACKUP" ]; then
    echo -e "${RED}❌ No backup found in $BACKUP_DIR${NC}"
    echo "Please restore database manually"
else
    echo "Found backup: $LATEST_BACKUP"
    echo -e "${YELLOW}[3/4] Restoring database...${NC}"
    
    # Start database
    docker compose -f docker-compose.prod.yml up -d db
    sleep 10
    
    # Restore backup
    gunzip -c "$LATEST_BACKUP" | docker exec -i advisor_db_prod psql -U postgres career_advisor
    
    echo -e "${GREEN}✅ Database restored${NC}"
fi

echo ""
echo -e "${YELLOW}[4/4] Starting all services...${NC}"
docker compose -f docker-compose.prod.yml up -d

echo "Waiting for services to start..."
sleep 20

echo ""
echo -e "${GREEN}✅ Rollback completed${NC}"
echo ""
echo "Please verify services are working:"
echo "  docker compose -f docker-compose.prod.yml ps"
echo "  curl http://localhost:8000/health"
