#!/bin/bash
# Health check script for verifying deployment success
# Usage: ./scripts/health_check.sh <base_url>

set -e

BASE_URL="${1:-http://localhost:8000}"
MAX_ATTEMPTS=30
SLEEP_INTERVAL=10

echo "=========================================="
echo "Health Check Script"
echo "Base URL: $BASE_URL"
echo "=========================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check a single endpoint
check_endpoint() {
    local endpoint=$1
    local service_name=$2
    
    echo -n "Checking $service_name ($endpoint)... "
    
    response=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$endpoint" || echo "000")
    
    if [ "$response" = "200" ]; then
        echo -e "${GREEN}✓ OK${NC}"
        return 0
    else
        echo -e "${RED}✗ FAILED (HTTP $response)${NC}"
        return 1
    fi
}

# Function to wait for service to be ready
wait_for_service() {
    local endpoint=$1
    local service_name=$2
    local attempt=1
    
    echo "Waiting for $service_name to be ready..."
    
    while [ $attempt -le $MAX_ATTEMPTS ]; do
        if curl -sf "$BASE_URL$endpoint" > /dev/null 2>&1; then
            echo -e "${GREEN}$service_name is ready!${NC}"
            return 0
        fi
        
        echo "Attempt $attempt/$MAX_ATTEMPTS - $service_name not ready yet..."
        sleep $SLEEP_INTERVAL
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}$service_name failed to become ready after $MAX_ATTEMPTS attempts${NC}"
    return 1
}

# Main health check sequence
echo ""
echo "Step 1: Waiting for gateway to be ready..."
wait_for_service "/health" "Gateway" || exit 1

echo ""
echo "Step 2: Checking all service health endpoints..."
echo ""

failed=0

# Check all services
check_endpoint "/health" "Gateway" || failed=$((failed + 1))
check_endpoint "/auth/health" "Auth Service" || failed=$((failed + 1))
check_endpoint "/cv/health" "CV Service" || failed=$((failed + 1))
check_endpoint "/jd/health" "JD Service" || failed=$((failed + 1))
check_endpoint "/analysis/health" "Analysis Service" || failed=$((failed + 1))
check_endpoint "/recommend/health" "Recommender Service" || failed=$((failed + 1))
check_endpoint "/admin/health" "Admin Service" || failed=$((failed + 1))

echo ""
echo "=========================================="

if [ $failed -eq 0 ]; then
    echo -e "${GREEN}All health checks passed! ✓${NC}"
    echo "=========================================="
    exit 0
else
    echo -e "${RED}$failed health check(s) failed! ✗${NC}"
    echo "=========================================="
    exit 1
fi
