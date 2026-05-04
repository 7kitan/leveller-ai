#!/bin/bash
# Migration runner script for prompt templates
# Usage: ./run_migrations.sh [environment]
# Environment: dev (default) | prod

set -e

ENVIRONMENT=${1:-dev}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIGRATIONS_DIR="$SCRIPT_DIR/migrations"

echo "=========================================="
echo "Running Prompt Template Migrations"
echo "Environment: $ENVIRONMENT"
echo "=========================================="

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

# Run migrations in order
for migration_file in "$MIGRATIONS_DIR"/*.sql; do
    if [ -f "$migration_file" ]; then
        filename=$(basename "$migration_file")
        echo "Running migration: $filename"
        
        if [ "$ENVIRONMENT" = "prod" ]; then
            # Production: Use psql with password prompt
            PGPASSWORD=$POSTGRES_PASSWORD psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$migration_file"
        else
            # Development: Use docker exec
            docker exec advisor_db psql -U "$DB_USER" -d "$DB_NAME" -f "/app/scripts/migrations/$filename"
        fi
        
        if [ $? -eq 0 ]; then
            echo "✓ Migration completed: $filename"
        else
            echo "✗ Migration failed: $filename"
            exit 1
        fi
        echo ""
    fi
done

echo "=========================================="
echo "All migrations completed successfully!"
echo "=========================================="

# Verify prompts
echo ""
echo "Verifying prompt templates..."
if [ "$ENVIRONMENT" = "prod" ]; then
    PGPASSWORD=$POSTGRES_PASSWORD psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT key, name, category, is_active FROM prompt_templates WHERE is_active = true ORDER BY category;"
else
    docker exec advisor_db psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT key, name, category, is_active FROM prompt_templates WHERE is_active = true ORDER BY category;"
fi
