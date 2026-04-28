#!/bin/bash

# Setup Database Indexes for Career Advisor
# This script runs the SQL setup file to create all necessary indexes

set -e  # Exit on error

echo "=========================================="
echo "Career Advisor - Database Index Setup"
echo "=========================================="
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SQL_FILE="$SCRIPT_DIR/setup_indexes.sql"

# Check if SQL file exists
if [ ! -f "$SQL_FILE" ]; then
    echo "❌ Error: setup_indexes.sql not found in $SCRIPT_DIR"
    exit 1
fi

# Load environment variables if .env exists
if [ -f "$SCRIPT_DIR/../.env" ]; then
    echo "📄 Loading environment variables from .env..."
    set -a
    source "$SCRIPT_DIR/../.env"
    set +a
fi

# Set default values if not in .env
POSTGRES_USER=${POSTGRES_USER:-postgres}
POSTGRES_DB=${POSTGRES_DB:-career_advisor}
CONTAINER_NAME=${CONTAINER_NAME:-advisor_db_prod}

echo "📊 Database Configuration:"
echo "   Container: $CONTAINER_NAME"
echo "   Database: $POSTGRES_DB"
echo "   User: $POSTGRES_USER"
echo ""

# Check if container is running
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo "❌ Error: Container $CONTAINER_NAME is not running"
    echo "   Please start the database container first"
    exit 1
fi

echo "🔧 Creating indexes..."
echo ""

# Run SQL file
docker exec -i "$CONTAINER_NAME" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$SQL_FILE"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Index setup completed successfully!"
    echo ""
    echo "📊 Verifying indexes..."
    echo ""
    
    # Show vector indexes
    docker exec "$CONTAINER_NAME" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
        SELECT 
            tablename, 
            indexname 
        FROM pg_indexes 
        WHERE schemaname = 'public' 
            AND indexname LIKE '%vector%' 
        ORDER BY tablename;
    "
    
    echo ""
    echo "✅ Setup complete!"
else
    echo ""
    echo "❌ Error: Index setup failed"
    exit 1
fi
