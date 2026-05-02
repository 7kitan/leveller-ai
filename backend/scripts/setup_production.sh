#!/bin/bash
# Production Database Setup Script
# 
# This script sets up the complete database for production deployment.
# Safe to run multiple times (idempotent).
#
# Usage:
#   cd backend
#   ./scripts/setup_production.sh

set -e  # Exit on error

echo "======================================================================"
echo "🚀 PRODUCTION DATABASE SETUP"
echo "======================================================================"
echo ""

# Check if running from backend directory
if [ ! -f "docker-compose.prod.yml" ]; then
    echo "❌ Error: docker-compose.prod.yml not found"
    echo "   Please run this script from the backend directory:"
    echo "   cd backend && ./scripts/setup_production.sh"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed"
    echo "   Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! docker compose version &> /dev/null; then
    echo "❌ Error: Docker Compose is not installed"
    echo "   Please install Docker Compose V2"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "✅ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Please update .env with your production values:"
    echo "   - DATABASE_URL"
    echo "   - DEFAULT_ADMIN_EMAIL"
    echo "   - DEFAULT_ADMIN_PASSWORD"
    echo "   - OPENAI_API_KEY (optional)"
    echo ""
    read -p "Press Enter after updating .env file, or Ctrl+C to exit..."
fi

# Load environment variables safely
if [ -f ".env" ]; then
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip comments and empty lines
        [[ "$line" =~ ^#.*$ ]] && continue
        [[ "$line" =~ ^[[:space:]]*$ ]] && continue
        
        # Export only if it's a valid KEY=VALUE pair
        if [[ "$line" =~ ^[^=]+=.+$ ]]; then
            export "$line"
        fi
    done < .env
fi

echo "======================================================================"
echo "STEP 1: Starting Database and Redis"
echo "======================================================================"
echo ""

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker compose -f docker-compose.prod.yml down 2>/dev/null || true

# Start database and redis
echo "🚀 Starting database and redis..."
docker compose -f docker-compose.prod.yml up -d db redis

# Wait for database to be ready with retries
echo "⏳ Waiting for database to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0
until docker compose -f docker-compose.prod.yml exec -T db psql -U postgres -c '\q' 2>/dev/null; do
    RETRY_COUNT=$((RETRY_COUNT+1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "❌ Database failed to start after ${MAX_RETRIES} attempts"
        echo "   Check logs: docker compose -f docker-compose.prod.yml logs db"
        exit 1
    fi
    echo "   Attempt $RETRY_COUNT/$MAX_RETRIES - waiting 2 seconds..."
    sleep 2
done

echo "✅ Database is ready"
echo ""

echo "======================================================================"
echo "STEP 2: Building Gateway Service"
echo "======================================================================"
echo ""

# Build gateway service (has all Python dependencies)
echo "📦 Building gateway service with all dependencies..."
docker compose -f docker-compose.prod.yml build gateway

if [ $? -ne 0 ]; then
    echo "❌ Failed to build gateway service"
    echo "   Check logs above for errors"
    exit 1
fi

echo "✅ Gateway service built successfully"
echo ""

echo "======================================================================"
echo "STEP 3: Running Database Setup Script"
echo "======================================================================"
echo ""

# Run setup script inside gateway container
echo "🐍 Running setup_production.py inside Docker container..."
echo ""

docker compose -f docker-compose.prod.yml run --rm \
    --no-deps \
    gateway python3 scripts/setup_production.py

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Setup script failed. Check logs above."
    echo "   Common issues:"
    echo "   - DATABASE_URL incorrect in .env"
    echo "   - Database not accessible from container"
    echo "   - tuning file missing"
    exit 1
fi

echo ""
echo "======================================================================"
echo "STEP 4: Verification"
echo "======================================================================"
echo ""

# Verify database setup
echo "🔍 Verifying database setup..."

# Check tables
TABLE_COUNT=$(docker compose -f docker-compose.prod.yml exec -T db psql -U postgres -d career_advisor -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | xargs)

if [ -z "$TABLE_COUNT" ] || [ "$TABLE_COUNT" -lt 15 ]; then
    echo "⚠️  Warning: Expected at least 15 tables, found: $TABLE_COUNT"
else
    echo "✅ Database tables ready: $TABLE_COUNT"
fi

# Check admin user
ADMIN_COUNT=$(docker compose -f docker-compose.prod.yml exec -T db psql -U postgres -d career_advisor -t -c "SELECT COUNT(*) FROM users WHERE role = 'admin';" 2>/dev/null | xargs)

if [ -z "$ADMIN_COUNT" ] || [ "$ADMIN_COUNT" -lt 1 ]; then
    echo "⚠️  Warning: No admin user found"
else
    echo "✅ Admin users: $ADMIN_COUNT"
fi

echo ""
echo "======================================================================"
echo "🎉 PRODUCTION SETUP COMPLETED SUCCESSFULLY"
echo "======================================================================"
echo ""
echo "Your database is ready for production!"
echo ""
echo "Next steps:"
echo ""
echo "  1. Start all services:"
echo "     docker compose -f docker-compose.prod.yml up -d"
echo ""
echo "  2. Check service health:"
echo "     docker compose -f docker-compose.prod.yml ps"
echo ""
echo "  3. View logs:"
echo "     docker compose -f docker-compose.prod.yml logs -f gateway"
echo "     docker compose -f docker-compose.prod.yml logs -f jd-service"
echo ""
echo "  4. Test API:"
echo "     curl http://localhost:8000/health"
echo "     open http://localhost:8000/docs"
echo ""
echo "  5. Test admin login:"
echo "     Email: ${DEFAULT_ADMIN_EMAIL:-admin@lumix.ai}"
echo "     Password: (check your .env file)"
echo ""
echo "======================================================================"
echo ""
