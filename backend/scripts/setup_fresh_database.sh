#!/bin/bash
# Complete setup script for fresh production database
# This script creates all tables and populates prompts
# Usage: ./setup_fresh_database.sh [environment]

set -e

ENVIRONMENT=${1:-dev}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIGRATIONS_DIR="$SCRIPT_DIR/migrations"

echo "=========================================="
echo "Fresh Database Setup"
echo "Environment: $ENVIRONMENT"
echo "=========================================="
echo ""

# Load environment variables
if [ "$ENVIRONMENT" = "prod" ]; then
    ENV_FILE="$SCRIPT_DIR/../.env.production"
else
    ENV_FILE="$SCRIPT_DIR/../.env"
fi

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: Environment file not found: $ENV_FILE"
    exit 1
fi

source "$ENV_FILE"

# Database connection details
DB_HOST=${POSTGRES_HOST:-localhost}
DB_PORT=${POSTGRES_PORT:-5432}
DB_NAME=${POSTGRES_DB:-career_advisor}
DB_USER=${POSTGRES_USER:-postgres}

echo "Database: $DB_NAME@$DB_HOST:$DB_PORT"
echo ""

# Function to run SQL file
run_migration() {
    local migration_file=$1
    local filename=$(basename "$migration_file")
    
    echo "Running: $filename"
    
    if [ "$ENVIRONMENT" = "prod" ]; then
        # Production: Use psql directly
        PGPASSWORD=$POSTGRES_PASSWORD psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$migration_file"
    else
        # Development: Use docker exec
        cat "$migration_file" | docker exec -i advisor_db psql -U "$DB_USER" -d "$DB_NAME"
    fi
    
    if [ $? -eq 0 ]; then
        echo "✓ Completed: $filename"
    else
        echo "✗ Failed: $filename"
        exit 1
    fi
    echo ""
}

# Check if prompt_templates table exists
echo "Checking existing tables..."
if [ "$ENVIRONMENT" = "prod" ]; then
    TABLE_EXISTS=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'prompt_templates');")
else
    TABLE_EXISTS=$(docker exec advisor_db psql -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'prompt_templates');")
fi

if [ "$TABLE_EXISTS" = "t" ]; then
    echo "✓ prompt_templates table exists"
    echo "Skipping schema creation..."
    echo ""
else
    echo "✗ prompt_templates table does not exist"
    echo "Creating schema..."
    echo ""
    
    # Run schema creation
    run_migration "$MIGRATIONS_DIR/000_create_prompt_schema.sql"
fi

# Run prompts setup (idempotent)
echo "Setting up prompts..."
run_migration "$MIGRATIONS_DIR/001_setup_prompts.sql"

# Check if benchmark tables exist
echo "Checking benchmark tables..."
if [ "$ENVIRONMENT" = "prod" ]; then
    BENCHMARK_EXISTS=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'lm_test_sets');")
else
    BENCHMARK_EXISTS=$(docker exec advisor_db psql -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'lm_test_sets');")
fi

if [ "$BENCHMARK_EXISTS" = "t" ]; then
    echo "✓ Benchmark tables exist"
    echo "Skipping benchmark table creation..."
    echo ""
else
    echo "✗ Benchmark tables do not exist"
    echo "Creating benchmark tables..."
    echo ""
    
    # Run benchmark table creation
    run_migration "$MIGRATIONS_DIR/002_create_benchmark_tables.sql"
fi

echo "=========================================="
echo "Setup completed successfully!"
echo "=========================================="
echo ""

# Final verification
echo "Verifying installation..."
echo ""

echo "1. Prompt Templates:"
if [ "$ENVIRONMENT" = "prod" ]; then
    PGPASSWORD=$POSTGRES_PASSWORD psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT key, name, category, is_active FROM prompt_templates WHERE is_active = true ORDER BY category;"
else
    docker exec advisor_db psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT key, name, category, is_active FROM prompt_templates WHERE is_active = true ORDER BY category;"
fi

echo ""
echo "2. Benchmark Tables:"
if [ "$ENVIRONMENT" = "prod" ]; then
    PGPASSWORD=$POSTGRES_PASSWORD psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'lm_%' ORDER BY table_name;"
else
    docker exec advisor_db psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'lm_%' ORDER BY table_name;"
fi

echo ""
echo "=========================================="
echo "Next Steps:"
echo "1. Restart services: docker-compose restart admin_service worker"
echo "2. Reload cache: curl -X POST http://localhost:8000/admin/prompts/reload"
echo "3. Test prompts via Admin UI: http://localhost:3000/admin/prompts"
echo "=========================================="
