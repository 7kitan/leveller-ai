#!/bin/bash

# Script to replace Lumix with Leveller across the codebase

echo "🔍 Searching for 'Lumix' instances..."

# Find all relevant files and replace Lumix with Leveller
find /Users/kitan/dev/build-078/frontend/src -type f \( -name "*.tsx" -o -name "*.ts" -o -name "*.json" -o -name "*.md" \) -exec sed -i '' 's/Lumix/Leveller/g' {} +

# Also replace in lowercase for email addresses
find /Users/kitan/dev/build-078/frontend/src -type f \( -name "*.tsx" -o -name "*.ts" -o -name "*.json" -o -name "*.md" \) -exec sed -i '' 's/lumix/leveller/g' {} +

echo "✅ Replacement complete!"
echo ""
echo "📊 Verifying changes..."
grep -r "Leveller" /Users/kitan/dev/build-078/frontend/src --include="*.tsx" --include="*.ts" --include="*.json" --include="*.md" | wc -l
echo "instances of 'Leveller' found"
