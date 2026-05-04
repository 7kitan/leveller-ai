#!/bin/bash
# =============================================================================
# Setup Prompt Templates and Benchmark System
# =============================================================================
# This script creates and populates:
# 1. prompt_templates table
# 2. Benchmark tables (test_sets, test_cases, runs, results)
# 3. Initial prompt data
# 4. Sample benchmark test sets
#
# Usage:
#   ./setup_prompts_and_benchmark.sh [dev|prod]
#
# Requirements:
#   - Docker containers running
#   - PostgreSQL database exists
#   - .env file configured
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Determine environment (default: dev)
ENVIRONMENT="${1:-dev}"

# Load .env file safely (handle special characters and quotes)
if [ -f "$(dirname "$0")/../.env" ]; then
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ "$key" =~ ^#.*$ ]] && continue
        [[ -z "$key" ]] && continue
        
        # Remove leading/trailing whitespace
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs)
        
        # Remove quotes if present
        value="${value%\"}"
        value="${value#\"}"
        value="${value%\'}"
        value="${value#\'}"
        
        # Export variable
        export "$key=$value"
    done < "$(dirname "$0")/../.env"
    echo -e "${GREEN}[SUCCESS]${NC} .env file loaded"
else
    echo -e "${YELLOW}[WARNING]${NC} .env file not found, using defaults"
fi

# Configuration based on environment
if [ "$ENVIRONMENT" = "prod" ]; then
    DB_CONTAINER="advisor_db_prod"
    DB_NAME="${POSTGRES_DB:-career_advisor}"
    DB_USER="${POSTGRES_USER:-postgres}"
    DB_PASSWORD="${POSTGRES_PASSWORD}"
else
    DB_CONTAINER="advisor_db"
    DB_NAME="${POSTGRES_DB:-career_advisor}"
    DB_USER="${POSTGRES_USER:-postgres}"
    DB_PASSWORD="${POSTGRES_PASSWORD:-postgres}"
fi

MIGRATIONS_DIR="$(dirname "$0")/migrations"

# =============================================================================
# Helper Functions
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_docker() {
    if ! docker ps | grep -q "$DB_CONTAINER"; then
        log_error "Database container '$DB_CONTAINER' is not running"
        if [ "$ENVIRONMENT" = "prod" ]; then
            log_info "Start it with: docker-compose -f docker-compose.prod.yml up -d db"
        else
            log_info "Start it with: docker-compose up -d advisor_db"
        fi
        exit 1
    fi
    log_success "Database container is running"
}

check_database() {
    if ! docker exec "$DB_CONTAINER" psql -U "$DB_USER" -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
        log_error "Database '$DB_NAME' does not exist"
        exit 1
    fi
    log_success "Database '$DB_NAME' exists"
}

run_sql_file() {
    local file=$1
    local description=$2
    
    log_info "Running: $description"
    
    if [ ! -f "$file" ]; then
        log_error "Migration file not found: $file"
        exit 1
    fi
    
    # Use PGPASSWORD environment variable for authentication
    if [ -n "$DB_PASSWORD" ]; then
        if docker exec -i "$DB_CONTAINER" bash -c "PGPASSWORD='$DB_PASSWORD' psql -U $DB_USER -d $DB_NAME" < "$file" > /dev/null 2>&1; then
            log_success "$description completed"
            return 0
        else
            log_error "$description failed"
            return 1
        fi
    else
        if docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" < "$file" > /dev/null 2>&1; then
            log_success "$description completed"
            return 0
        else
            log_error "$description failed"
            return 1
        fi
    fi
}

check_table_exists() {
    local table_name=$1
    if [ -n "$DB_PASSWORD" ]; then
        docker exec "$DB_CONTAINER" bash -c "PGPASSWORD='$DB_PASSWORD' psql -U $DB_USER -d $DB_NAME -tAc \"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name='$table_name');\"" | grep -q 't'
    else
        docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -tAc \
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name='$table_name');" | grep -q 't'
    fi
}

count_prompts() {
    if [ -n "$DB_PASSWORD" ]; then
        docker exec "$DB_CONTAINER" bash -c "PGPASSWORD='$DB_PASSWORD' psql -U $DB_USER -d $DB_NAME -tAc 'SELECT COUNT(*) FROM prompt_templates WHERE is_active = true;'" 2>/dev/null || echo "0"
    else
        docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -tAc \
            "SELECT COUNT(*) FROM prompt_templates WHERE is_active = true;" 2>/dev/null || echo "0"
    fi
}

count_test_sets() {
    if [ -n "$DB_PASSWORD" ]; then
        docker exec "$DB_CONTAINER" bash -c "PGPASSWORD='$DB_PASSWORD' psql -U $DB_USER -d $DB_NAME -tAc 'SELECT COUNT(*) FROM llm_test_sets;'" 2>/dev/null || echo "0"
    else
        docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -tAc \
            "SELECT COUNT(*) FROM llm_test_sets;" 2>/dev/null || echo "0"
    fi
}

# =============================================================================
# Main Setup Process
# =============================================================================

main() {
    echo ""
    echo "========================================================================="
    echo "  Setup Prompt Templates and Benchmark System"
    echo "  Environment: $ENVIRONMENT"
    echo "========================================================================="
    echo ""
    
    # Step 1: Pre-flight checks
    log_info "Step 1/5: Pre-flight checks"
    log_info "Container: $DB_CONTAINER"
    log_info "Database: $DB_NAME"
    log_info "User: $DB_USER"
    check_docker
    check_database
    echo ""
    
    # Step 2: Create prompt_templates table
    log_info "Step 2/5: Create prompt_templates table"
    if check_table_exists "prompt_templates"; then
        log_warning "Table 'prompt_templates' already exists, skipping creation"
    else
        run_sql_file "$MIGRATIONS_DIR/000_create_prompt_schema.sql" "Create prompt_templates schema"
    fi
    echo ""
    
    # Step 3: Populate initial prompts
    log_info "Step 3/5: Populate prompt templates"
    PROMPT_COUNT=$(count_prompts)
    if [ "$PROMPT_COUNT" -ge 5 ]; then
        log_warning "Found $PROMPT_COUNT active prompts, skipping population"
    else
        run_sql_file "$MIGRATIONS_DIR/001_setup_prompts.sql" "Populate initial prompts"
        PROMPT_COUNT=$(count_prompts)
        log_success "Loaded $PROMPT_COUNT active prompts"
    fi
    echo ""
    
    # Step 4: Create benchmark tables
    log_info "Step 4/5: Create benchmark tables"
    if check_table_exists "llm_test_sets"; then
        log_warning "Benchmark tables already exist, skipping creation"
    else
        run_sql_file "$MIGRATIONS_DIR/002_create_benchmark_tables.sql" "Create benchmark tables"
    fi
    echo ""
    
    # Step 5: Populate benchmark test sets (optional)
    log_info "Step 5/5: Populate benchmark test sets"
    TEST_SET_COUNT=$(count_test_sets)
    if [ "$TEST_SET_COUNT" -ge 1 ]; then
        log_warning "Found $TEST_SET_COUNT test sets, skipping population"
    else
        if [ -f "$MIGRATIONS_DIR/populate_benchmark_test_sets.sql" ]; then
            run_sql_file "$MIGRATIONS_DIR/populate_benchmark_test_sets.sql" "Populate benchmark test sets"
            TEST_SET_COUNT=$(count_test_sets)
            log_success "Loaded $TEST_SET_COUNT test sets"
        else
            log_warning "populate_benchmark_test_sets.sql not found, skipping"
        fi
    fi
    echo ""
    
    # Final verification
    echo "========================================================================="
    echo "  Setup Complete - Verification"
    echo "========================================================================="
    
    # Verify prompt_templates
    PROMPT_COUNT=$(count_prompts)
    echo -e "${GREEN}✓${NC} prompt_templates: $PROMPT_COUNT active prompts"
    
    # Verify benchmark tables
    if check_table_exists "llm_test_sets"; then
        TEST_SET_COUNT=$(count_test_sets)
        echo -e "${GREEN}✓${NC} llm_test_sets: $TEST_SET_COUNT test sets"
    fi
    
    if check_table_exists "llm_test_cases"; then
        if [ -n "$DB_PASSWORD" ]; then
            TEST_CASE_COUNT=$(docker exec "$DB_CONTAINER" bash -c "PGPASSWORD='$DB_PASSWORD' psql -U $DB_USER -d $DB_NAME -tAc 'SELECT COUNT(*) FROM llm_test_cases;'" 2>/dev/null || echo "0")
        else
            TEST_CASE_COUNT=$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -tAc \
                "SELECT COUNT(*) FROM llm_test_cases;" 2>/dev/null || echo "0")
        fi
        echo -e "${GREEN}✓${NC} llm_test_cases: $TEST_CASE_COUNT test cases"
    fi
    
    if check_table_exists "llm_benchmark_sessions"; then
        echo -e "${GREEN}✓${NC} llm_benchmark_sessions: Ready"
    fi
    
    if check_table_exists "llm_benchmark_results"; then
        echo -e "${GREEN}✓${NC} llm_benchmark_results: Ready"
    fi
    
    echo ""
    echo "========================================================================="
    log_success "All setup completed successfully!"
    echo "========================================================================="
    echo ""
    echo "Next steps:"
    if [ "$ENVIRONMENT" = "prod" ]; then
        echo "  1. Enable benchmark: docker exec $DB_CONTAINER bash -c \"PGPASSWORD='$DB_PASSWORD' psql -U $DB_USER -d $DB_NAME -c \\\"INSERT INTO system_settings (key, value) VALUES ('ENABLE_BENCHMARK', 'true') ON CONFLICT (key) DO UPDATE SET value = 'true';\\\"\""
        echo "  2. Restart workers: docker-compose -f docker-compose.prod.yml restart worker-benchmark"
        echo "  3. Access admin UI: https://yourdomain.com/admin/prompts"
    else
        echo "  1. Enable benchmark: docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c \"INSERT INTO system_settings (key, value) VALUES ('ENABLE_BENCHMARK', 'true') ON CONFLICT (key) DO UPDATE SET value = 'true';\""
        echo "  2. Restart workers: docker-compose restart advisor_worker_benchmark"
        echo "  3. Access admin UI: http://localhost:3000/admin/prompts"
    fi
    echo ""
}

# =============================================================================
# Script Entry Point
# =============================================================================

# Check if running from correct directory
if [ ! -d "$MIGRATIONS_DIR" ]; then
    log_error "Migrations directory not found: $MIGRATIONS_DIR"
    log_info "Please run this script from backend/scripts directory"
    exit 1
fi

# Run main setup
main

exit 0
