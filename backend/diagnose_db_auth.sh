#!/bin/bash
# ============================================================================
# Deep Diagnosis: Find Which Service Has Password Issue
# ============================================================================
# This script checks ALL services to find which one is failing
# ============================================================================

echo "============================================================================"
echo "🔍 DEEP DIAGNOSIS: Finding Service With Password Issue"
echo "============================================================================"
echo ""

# Get password from .env
ENV_PASSWORD=$(grep "^POSTGRES_PASSWORD=" .env | cut -d'=' -f2)
echo "📋 Password in .env: ${ENV_PASSWORD:0:3}***"
echo ""

# List all running containers
echo "============================================================================"
echo "📦 CHECKING ALL SERVICES"
echo "============================================================================"
echo ""

SERVICES=$(docker compose -f docker-compose.prod.yml ps --services)

for SERVICE in $SERVICES; do
    CONTAINER=$(docker compose -f docker-compose.prod.yml ps -q $SERVICE)
    
    if [ -z "$CONTAINER" ]; then
        echo "⏭️  $SERVICE - Not running"
        continue
    fi
    
    echo "🔍 Checking: $SERVICE"
    
    # Check environment variables
    SERVICE_PASSWORD=$(docker exec $CONTAINER env 2>/dev/null | grep "^POSTGRES_PASSWORD=" | cut -d'=' -f2)
    
    if [ -z "$SERVICE_PASSWORD" ]; then
        echo "   ⚠️  No POSTGRES_PASSWORD env var"
    elif [ "$SERVICE_PASSWORD" != "$ENV_PASSWORD" ]; then
        echo "   ❌ PASSWORD MISMATCH!"
        echo "      Expected: ${ENV_PASSWORD:0:3}***"
        echo "      Got: ${SERVICE_PASSWORD:0:3}***"
    else
        echo "   ✓ Password matches .env"
    fi
    
    # Check recent logs for auth errors
    ERROR_COUNT=$(docker logs $CONTAINER --since 10m 2>&1 | grep -c "password authentication failed" || echo "0")
    if [ "$ERROR_COUNT" -gt 0 ]; then
        echo "   ❌ Found $ERROR_COUNT auth errors in last 10 minutes!"
        echo "   Last error:"
        docker logs $CONTAINER --since 10m 2>&1 | grep "password authentication failed" | tail -1
    fi
    
    echo ""
done

echo "============================================================================"
echo "🔍 CHECKING DATABASE LOGS"
echo "============================================================================"
echo ""

# Check database logs for failed connections
echo "Recent authentication failures from database perspective:"
docker logs advisor_db_prod --since 30m 2>&1 | grep "FATAL.*password authentication failed" | tail -10

echo ""
echo "============================================================================"
echo "🔍 CHECKING FOR HARDCODED PASSWORDS IN CODE"
echo "============================================================================"
echo ""

# Check if any service is using hardcoded connection string
echo "Searching for hardcoded database URLs..."
if grep -r "postgresql://.*:.*@" --include="*.py" --include="*.env*" . 2>/dev/null | grep -v ".git" | grep -v "node_modules"; then
    echo "⚠️  Found potential hardcoded connection strings above"
else
    echo "✓ No hardcoded connection strings found"
fi

echo ""
echo "============================================================================"
echo "🔧 RECOMMENDED ACTIONS"
echo "============================================================================"
echo ""
echo "1. If you found services with password mismatch:"
echo "   → Run: docker compose -f docker-compose.prod.yml up -d --force-recreate"
echo ""
echo "2. If database logs show specific service failing:"
echo "   → Run: docker compose -f docker-compose.prod.yml restart <service-name>"
echo ""
echo "3. If errors persist:"
echo "   → Check .env file is properly loaded"
echo "   → Run: docker compose -f docker-compose.prod.yml down && docker compose -f docker-compose.prod.yml up -d"
echo ""
