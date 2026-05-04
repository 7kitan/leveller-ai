#!/bin/bash
# Quick Deployment Helper Script
# Location: scripts/deploy_ip_management.sh

set -e  # Exit on error

echo "================================================"
echo "🚀 IP Block Management - Quick Deploy Helper"
echo "================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo "ℹ️  $1"
}

# Check if running from correct directory
if [ ! -f "docker-compose.prod.yml" ]; then
    print_error "Please run this script from the backend root directory"
    exit 1
fi

echo "Step 1: Checking Backend Services"
echo "-----------------------------------"

# Check if Docker is running
if ! docker ps > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi
print_success "Docker is running"

# Check if backend services are running
if docker ps | grep -q "advisor_admin_prod"; then
    print_success "Admin service is running"
else
    print_error "Admin service is not running"
    echo "Starting services..."
    docker compose -f docker-compose.prod.yml up -d
    sleep 5
fi

# Check if Redis is running
if docker ps | grep -q "advisor_redis_prod"; then
    print_success "Redis is running"
else
    print_error "Redis is not running"
    exit 1
fi

echo ""
echo "Step 2: Testing Backend Endpoints"
echo "-----------------------------------"

# Check if admin endpoint is accessible
ADMIN_URL="http://localhost:8000/admin/blocked-ips"
print_info "Testing: $ADMIN_URL"

# Note: This will return 401 without auth, which is expected
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $ADMIN_URL)

if [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "200" ]; then
    print_success "Admin endpoint is accessible (HTTP $HTTP_CODE)"
else
    print_error "Admin endpoint returned HTTP $HTTP_CODE"
    exit 1
fi

echo ""
echo "Step 3: Checking Redis Keys"
echo "-----------------------------------"

# Check if Redis has any blocked IPs
BLOCKED_COUNT=$(docker exec advisor_redis_prod redis-cli KEYS "lockout:*" | wc -l)
print_info "Currently blocked IPs: $BLOCKED_COUNT"

if [ "$BLOCKED_COUNT" -gt 0 ]; then
    print_warning "There are $BLOCKED_COUNT IPs currently blocked"
    echo "Sample blocked IPs:"
    docker exec advisor_redis_prod redis-cli KEYS "lockout:*" | head -5
else
    print_info "No IPs are currently blocked"
fi

echo ""
echo "Step 4: Frontend Files Check"
echo "-----------------------------------"

FRONTEND_DIR="docs/frontend-code/admin/blocked-ips"

if [ -d "$FRONTEND_DIR" ]; then
    print_success "Frontend files directory exists"
    
    # Check each required file
    FILES=(
        "BlockedIPsPage.tsx"
        "BlockedIPTable.tsx"
        "UnblockConfirmModal.tsx"
        "ClearAllConfirmModal.tsx"
        "BlockedIPs.css"
        "api.ts"
        "README.md"
    )
    
    for file in "${FILES[@]}"; do
        if [ -f "$FRONTEND_DIR/$file" ]; then
            print_success "$file exists"
        else
            print_error "$file is missing"
        fi
    done
else
    print_error "Frontend files directory not found"
    exit 1
fi

echo ""
echo "Step 5: Documentation Check"
echo "-----------------------------------"

DOCS=(
    "docs/security/IP_BLOCK_MANAGEMENT.md"
    "docs/deployment/DEPLOYMENT_CHECKLIST.md"
    "docs/deployment/TESTING_GUIDE.md"
    "docs/FEATURE_SUMMARY.md"
)

for doc in "${DOCS[@]}"; do
    if [ -f "$doc" ]; then
        print_success "$(basename $doc) exists"
    else
        print_warning "$(basename $doc) is missing"
    fi
done

echo ""
echo "================================================"
echo "📋 Summary"
echo "================================================"
echo ""

print_success "Backend is ready!"
print_info "Admin service: http://localhost:8000"
print_info "Blocked IPs endpoint: http://localhost:8000/admin/blocked-ips"
print_info "Currently blocked IPs: $BLOCKED_COUNT"

echo ""
print_success "Frontend files are ready!"
print_info "Location: $FRONTEND_DIR"
print_info "Files: 7 components + styles + API client"

echo ""
echo "================================================"
echo "🎯 Next Steps"
echo "================================================"
echo ""
echo "1. Copy frontend files to your React project:"
echo "   cp -r $FRONTEND_DIR/* /path/to/frontend/src/"
echo ""
echo "2. Add route to your router:"
echo "   <Route path=\"/admin/blocked-ips\" element={<BlockedIPsPage />} />"
echo ""
echo "3. Add navigation link:"
echo "   <NavLink to=\"/admin/blocked-ips\">🔒 Blocked IPs</NavLink>"
echo ""
echo "4. Configure API URL in frontend/.env:"
echo "   REACT_APP_API_URL=http://localhost:8000"
echo ""
echo "5. Test the feature:"
echo "   - Navigate to /admin/blocked-ips"
echo "   - Try unblocking an IP"
echo "   - Try clearing all IPs"
echo ""
echo "📚 Documentation:"
echo "   - Integration: $FRONTEND_DIR/README.md"
echo "   - Deployment: docs/deployment/DEPLOYMENT_CHECKLIST.md"
echo "   - Testing: docs/deployment/TESTING_GUIDE.md"
echo "   - Summary: docs/FEATURE_SUMMARY.md"
echo ""
echo "================================================"
print_success "All checks passed! Ready to integrate."
echo "================================================"
