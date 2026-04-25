#!/bin/bash
# =============================================================================
# Course Import Script
# Import courses from coursera_links.txt or courses.json
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_DIR="${PROJECT_DIR:-/opt/k109}"
DATASET_DIR="$PROJECT_DIR/dataset"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Lumix AI - Course Import${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if backend is running
if ! docker ps | grep -q advisor_gateway_prod; then
    echo -e "${RED}❌ Backend services are not running!${NC}"
    echo "Please start backend first:"
    echo "  cd $PROJECT_DIR/backend"
    echo "  docker compose -f docker-compose.prod.yml up -d"
    exit 1
fi

# Parse arguments
FORCE=false
DRY_RUN=false
FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --file)
            FILE="$2"
            shift 2
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Usage: $0 [--file <path>] [--force] [--dry-run]"
            exit 1
            ;;
    esac
done

# Find course file
if [ -z "$FILE" ]; then
    if [ -f "$DATASET_DIR/coursera_links.txt" ]; then
        FILE="$DATASET_DIR/coursera_links.txt"
    elif [ -f "$DATASET_DIR/courses.json" ]; then
        FILE="$DATASET_DIR/courses.json"
    else
        echo -e "${RED}❌ No course data file found!${NC}"
        echo ""
        echo "Please create one of these files:"
        echo "  1. $DATASET_DIR/coursera_links.txt (one URL per line)"
        echo "  2. $DATASET_DIR/courses.json (JSON array with 'link' field)"
        echo ""
        echo "Example coursera_links.txt:"
        echo "  https://www.coursera.org/learn/machine-learning"
        echo "  https://www.coursera.org/learn/python-for-data-science"
        echo ""
        exit 1
    fi
fi

if [ ! -f "$FILE" ]; then
    echo -e "${RED}❌ File not found: $FILE${NC}"
    exit 1
fi

echo -e "${GREEN}📁 Using file: $FILE${NC}"
echo ""

# Count URLs
if [[ "$FILE" == *.json ]]; then
    URL_COUNT=$(docker exec advisor_gateway_prod python3 -c "import json; f=open('/app/../dataset/$(basename $FILE)'); print(len(json.load(f)))")
else
    URL_COUNT=$(grep -c "coursera.org" "$FILE" || echo "0")
fi

echo -e "${YELLOW}📊 Found $URL_COUNT course URLs${NC}"
echo ""

# Confirm
if [ "$DRY_RUN" = false ]; then
    echo -e "${YELLOW}⚠️  This will import courses into the database.${NC}"
    if [ "$FORCE" = true ]; then
        echo -e "${YELLOW}⚠️  FORCE mode: Will re-import existing courses.${NC}"
    fi
    echo ""
    read -p "Continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled."
        exit 0
    fi
fi

# Build command
CMD="python scripts/seed_import_worker.py --file /app/../dataset/$(basename $FILE)"
if [ "$FORCE" = true ]; then
    CMD="$CMD --force"
fi
if [ "$DRY_RUN" = true ]; then
    CMD="$CMD --dry-run"
fi

# Run import
echo -e "${YELLOW}🚀 Starting import...${NC}"
echo ""

cd "$PROJECT_DIR/backend"
docker compose -f docker-compose.prod.yml exec gateway $CMD

echo ""
echo -e "${BLUE}========================================${NC}"

if [ "$DRY_RUN" = true ]; then
    echo -e "${BLUE}  Dry Run Complete${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo -e "${YELLOW}This was a dry run. No data was imported.${NC}"
    echo "Run without --dry-run to actually import courses."
else
    echo -e "${BLUE}  Import Complete${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo -e "${GREEN}✅ Courses have been queued for import!${NC}"
    echo ""
    echo -e "${YELLOW}📝 Note:${NC}"
    echo "  - Courses are being processed by Celery workers in the background"
    echo "  - This may take several minutes depending on the number of courses"
    echo "  - Check progress with: docker compose -f docker-compose.prod.yml logs -f worker-cv-parser"
    echo ""
    echo -e "${YELLOW}📊 Check import status:${NC}"
    echo "  docker exec advisor_db_prod psql -U postgres -d career_advisor -c 'SELECT COUNT(*) FROM courses;'"
fi

echo ""
