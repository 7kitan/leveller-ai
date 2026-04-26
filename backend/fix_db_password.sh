#!/bin/bash
# ============================================================================
# Production Database Password Authentication Fix
# ============================================================================
# Run this script on production server to diagnose and fix password issues
# Usage: bash fix_db_password.sh
# ============================================================================

set -e

echo "============================================================================"
echo "🔍 DIAGNOSING DATABASE PASSWORD ISSUE"
echo "============================================================================"
echo ""

# 1. Check .env file
echo "📋 Step 1: Checking .env configuration..."
if [ -f .env ]; then
    ENV_PASSWORD=$(grep "^POSTGRES_PASSWORD=" .env | cut -d'=' -f2)
    echo "   ✓ .env file found"
    echo "   Password in .env: ${ENV_PASSWORD:0:3}***"
else
    echo "   ❌ .env file not found!"
    exit 1
fi

# 2. Check database container
echo ""
echo "📋 Step 2: Checking database container..."
DB_CONTAINER=$(docker ps --filter "name=db" --format "{{.Names}}" | head -1)
if [ -z "$DB_CONTAINER" ]; then
    echo "   ❌ Database container not found!"
    exit 1
fi
echo "   ✓ Database container: $DB_CONTAINER"

# 3. Test connection with current password
echo ""
echo "📋 Step 3: Testing database connection..."
if docker exec $DB_CONTAINER psql -U postgres -d career_advisor -c "SELECT 1;" > /dev/null 2>&1; then
    echo "   ✓ Connection successful - NO PASSWORD ISSUE!"
    echo ""
    echo "============================================================================"
    echo "✅ Database is working fine. The error might be transient or already fixed."
    echo "============================================================================"
    exit 0
else
    echo "   ❌ Connection failed - PASSWORD MISMATCH DETECTED"
fi

# 4. Check if database has data
echo ""
echo "📋 Step 4: Checking if database has existing data..."
TABLE_COUNT=$(docker exec $DB_CONTAINER psql -U postgres -d postgres -t -c "SELECT COUNT(*) FROM pg_database WHERE datname='career_advisor';" 2>/dev/null || echo "0")
if [ "$TABLE_COUNT" -gt 0 ]; then
    echo "   ⚠️  Database 'career_advisor' exists - has data"
    HAS_DATA=true
else
    echo "   ℹ️  Database 'career_advisor' does not exist or is empty"
    HAS_DATA=false
fi

# 5. Offer fix options
echo ""
echo "============================================================================"
echo "🛠️  FIX OPTIONS"
echo "============================================================================"
echo ""
echo "Option 1: Reset postgres user password (RECOMMENDED)"
echo "   - Keeps all existing data"
echo "   - Updates password to match .env"
echo ""
echo "Option 2: Recreate database container (DESTRUCTIVE)"
echo "   - Deletes all data"
echo "   - Fresh start with correct password"
echo ""
read -p "Choose option (1 or 2): " OPTION

if [ "$OPTION" = "1" ]; then
    echo ""
    echo "🔧 Resetting postgres password..."
    
    # Reset password using postgres user (which has trust auth from localhost)
    docker exec $DB_CONTAINER psql -U postgres -d postgres -c "ALTER USER postgres WITH PASSWORD '$ENV_PASSWORD';" 2>&1
    
    if [ $? -eq 0 ]; then
        echo "   ✓ Password reset successful"
        
        # Test connection again
        echo ""
        echo "🧪 Testing connection with new password..."
        if docker exec $DB_CONTAINER psql -U postgres -d career_advisor -c "SELECT 1;" > /dev/null 2>&1; then
            echo "   ✓ Connection successful!"
        else
            echo "   ❌ Connection still failing. Trying alternative method..."
            
            # Alternative: Set password via environment variable
            docker compose -f docker-compose.prod.yml stop db
            docker compose -f docker-compose.prod.yml up -d db
            sleep 5
            
            if docker exec $DB_CONTAINER psql -U postgres -d career_advisor -c "SELECT 1;" > /dev/null 2>&1; then
                echo "   ✓ Connection successful after restart!"
            else
                echo "   ❌ Still failing. Manual intervention needed."
                exit 1
            fi
        fi
        
        # Restart all services
        echo ""
        echo "🔄 Restarting all services..."
        docker compose -f docker-compose.prod.yml restart
        
        echo ""
        echo "============================================================================"
        echo "✅ FIX COMPLETE"
        echo "============================================================================"
        echo "All services have been restarted with the correct password."
        echo "Please test your application now."
        
    else
        echo "   ❌ Failed to reset password"
        exit 1
    fi
    
elif [ "$OPTION" = "2" ]; then
    echo ""
    echo "⚠️  WARNING: This will DELETE ALL DATA in the database!"
    read -p "Are you sure? Type 'yes' to confirm: " CONFIRM
    
    if [ "$CONFIRM" = "yes" ]; then
        echo ""
        echo "🗑️  Stopping and removing database container..."
        docker compose -f docker-compose.prod.yml stop db
        docker compose -f docker-compose.prod.yml rm -f db
        
        echo "🗑️  Removing database volume..."
        docker volume rm $(docker volume ls -q | grep postgres) 2>/dev/null || true
        
        echo "🚀 Recreating database with correct password..."
        docker compose -f docker-compose.prod.yml up -d db
        
        echo "⏳ Waiting for database to be ready..."
        sleep 10
        
        echo "📊 Running database setup..."
        docker compose -f docker-compose.prod.yml exec gateway python scripts/setup_db.py
        
        echo "🔄 Restarting all services..."
        docker compose -f docker-compose.prod.yml restart
        
        echo ""
        echo "============================================================================"
        echo "✅ DATABASE RECREATED"
        echo "============================================================================"
        echo "Database has been recreated with correct password."
        echo "⚠️  All previous data has been lost."
        echo "You need to re-seed data if necessary."
        
    else
        echo "Aborted."
        exit 0
    fi
else
    echo "Invalid option. Aborted."
    exit 1
fi
