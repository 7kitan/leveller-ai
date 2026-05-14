#!/bin/bash
# Fix Chandra Settings - Initialize DB settings from .env
# This ensures workers can read Chandra config from database instead of only .env

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "🔧 Fixing Chandra Settings"
echo "=========================================="
echo ""

cd "$BACKEND_DIR"

# Check if .env exists
if [ ! -f .env ]; then
    echo "Please create .env with CHANDRA_OCR_URL and CHANDRA_OCR_API_KEY"
    exit 1
fi

# Check if Chandra settings exist in .env
if ! grep -q "CHANDRA_OCR_URL" .env; then
    echo "⚠️  Warning: CHANDRA_OCR_URL not found in .env"
    echo "Please add: CHANDRA_OCR_URL=https://your-chandra-hub-url/tasks/ocr"
fi

if ! grep -q "CHANDRA_OCR_API_KEY" .env; then
    echo "⚠️  Warning: CHANDRA_OCR_API_KEY not found in .env"
    echo "Please add: CHANDRA_OCR_API_KEY=your_api_key"
fi

echo "📦 Running migration to initialize Chandra settings in database..."
echo ""

# Run migration inside gateway container (has access to DB)
docker compose -f docker-compose.prod.yml exec gateway python /app/scripts/migrate_init_chandra_settings.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Chandra settings initialized in database!"
    echo ""
    echo "📋 Next steps:"
    echo "1. Verify settings in admin panel: https://onehub.cfd/admin/settings"
    echo "2. Look for 'CHANDRA_OCR_URL' and 'CHANDRA_OCR_API_KEY'"
    echo "3. Update them via UI if needed"
    echo "4. Workers will automatically pick up changes from database"
    echo ""
    echo "🔄 Restarting workers to apply changes..."
    docker compose -f docker-compose.prod.yml restart worker-cv-parser
    echo ""
    echo "✅ Done! Workers should now use database settings."
else
    echo ""
    echo "❌ Migration failed. Check logs above for errors."
    exit 1
fi
