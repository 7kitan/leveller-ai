#!/bin/bash

# Benchmark Extension Control Test Script
# Tests enable/disable functionality

set -e

echo "=========================================="
echo "Benchmark Extension Control Test"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ADMIN_URL="http://localhost:8001"
DB_NAME="team078"
DB_USER="postgres"

# Function to check service logs
check_logs() {
    local service=$1
    local expected=$2
    
    echo -n "Checking $service logs... "
    
    if docker-compose logs --tail=50 $service 2>/dev/null | grep -q "$expected"; then
        echo -e "${GREEN}✓ PASS${NC}"
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        return 1
    fi
}

# Function to test route availability
test_route() {
    local url=$1
    local expected_code=$2
    
    echo -n "Testing route $url (expecting $expected_code)... "
    
    actual_code=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
    
    if [ "$actual_code" = "$expected_code" ]; then
        echo -e "${GREEN}✓ PASS (got $actual_code)${NC}"
        return 0
    else
        echo -e "${RED}✗ FAIL (got $actual_code, expected $expected_code)${NC}"
        return 1
    fi
}

# Function to check Celery tasks
check_celery_tasks() {
    local should_exist=$1
    
    echo -n "Checking Celery benchmark tasks... "
    
    if docker-compose exec -T worker celery -A worker.celery_app inspect registered 2>/dev/null | grep -q "benchmark"; then
        if [ "$should_exist" = "true" ]; then
            echo -e "${GREEN}✓ PASS (tasks registered)${NC}"
            return 0
        else
            echo -e "${RED}✗ FAIL (tasks should NOT be registered)${NC}"
            return 1
        fi
    else
        if [ "$should_exist" = "false" ]; then
            echo -e "${GREEN}✓ PASS (tasks not registered)${NC}"
            return 0
        else
            echo -e "${RED}✗ FAIL (tasks should be registered)${NC}"
            return 1
        fi
    fi
}

# Function to set benchmark setting
set_benchmark_setting() {
    local value=$1
    
    echo "Setting ENABLE_BENCHMARK=$value..."
    
    docker-compose exec -T postgres psql -U $DB_USER -d $DB_NAME <<EOF
INSERT INTO system_settings (key, value, description, created_at, updated_at)
VALUES ('ENABLE_BENCHMARK', '$value', 'Enable/disable LLM benchmark extension', NOW(), NOW())
ON CONFLICT (key) DO UPDATE SET value = '$value', updated_at = NOW();
EOF
    
    echo -e "${GREEN}✓ Setting updated${NC}"
}

# Function to restart services
restart_services() {
    echo "Restarting services..."
    docker-compose restart admin_service worker > /dev/null 2>&1
    echo "Waiting for services to start..."
    sleep 15
    echo -e "${GREEN}✓ Services restarted${NC}"
}

# Test 1: Verify default behavior (enabled)
echo ""
echo "=========================================="
echo "Test 1: Default Behavior (Enabled)"
echo "=========================================="
echo ""

set_benchmark_setting "true"
restart_services

echo ""
echo "Running checks..."
check_logs "admin_service" "Benchmark extension ENABLED"
check_logs "worker" "Benchmark extension ENABLED"
test_route "$ADMIN_URL/admin/benchmarks/sessions" "401"  # 401 because not authenticated, but route exists
check_celery_tasks "true"

# Test 2: Disable benchmark
echo ""
echo "=========================================="
echo "Test 2: Disable Benchmark"
echo "=========================================="
echo ""

set_benchmark_setting "false"
restart_services

echo ""
echo "Running checks..."
check_logs "admin_service" "Benchmark extension DISABLED"
check_logs "worker" "Benchmark extension DISABLED"
test_route "$ADMIN_URL/admin/benchmarks/sessions" "404"  # 404 because route not registered
check_celery_tasks "false"

# Test 3: Re-enable benchmark
echo ""
echo "=========================================="
echo "Test 3: Re-enable Benchmark"
echo "=========================================="
echo ""

set_benchmark_setting "true"
restart_services

echo ""
echo "Running checks..."
check_logs "admin_service" "Benchmark extension ENABLED"
check_logs "worker" "Benchmark extension ENABLED"
test_route "$ADMIN_URL/admin/benchmarks/sessions" "401"  # 401 because not authenticated, but route exists
check_celery_tasks "true"

# Summary
echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo ""
echo -e "${GREEN}✓ All tests passed!${NC}"
echo ""
echo "Benchmark extension can be safely disabled in production by setting:"
echo "  ENABLE_BENCHMARK=false"
echo ""
echo "To disable permanently, add to .env file or update database setting."
echo ""
