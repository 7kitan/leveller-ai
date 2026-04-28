#!/bin/bash

# Setup Database Indexes for Career Advisor
# This script runs the SQL setup file to create all necessary indexes
#
# Usage:
#   ./setup_indexes.sh [container_name] [database] [user]
#
# Examples:
#   ./setup_indexes.sh                                    # Use defaults
#   ./setup_indexes.sh advisor_db_prod                    # Custom container
#   ./setup_indexes.sh advisor_db_prod career_advisor     # Custom container + db
#   ./setup_indexes.sh advisor_db_prod career_advisor postgres  # All custom

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

# Set values from arguments or use defaults
CONTAINER_NAME=${1:-advisor_db_prod}
POSTGRES_DB=${2:-career_advisor}
POSTGRES_USER=${3:-postgres}

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
