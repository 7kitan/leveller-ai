#!/bin/bash
# Script: cleanup_lowercase_keys.sh
# Purpose: Delete lowercase system_settings keys from database on VPS

echo "=== Checking for lowercase keys in system_settings ==="

# 1. Show all keys that contain lowercase letters
docker exec advisor_db_prod psql -U postgres -d career_advisor -c "
SELECT key, value 
FROM system_settings 
WHERE key ~ '[a-z]' 
ORDER BY key;
"

echo ""
echo "=== Checking for duplicate keys (lowercase vs UPPERCASE) ==="

# 2. Find keys that have both lowercase and UPPERCASE versions
docker exec advisor_db_prod psql -U postgres -d career_advisor -c "
SELECT 
    s1.key as lowercase_key,
    s1.value as lowercase_value,
    s2.key as uppercase_key,
    s2.value as uppercase_value
FROM system_settings s1
JOIN system_settings s2 ON UPPER(s1.key) = s2.key
WHERE s1.key != s2.key
ORDER BY s1.key;
"

echo ""
echo "=== Ready to delete lowercase keys ==="
echo "Press Ctrl+C to cancel, or Enter to continue..."
read

# 3. Delete all keys that contain lowercase letters
docker exec advisor_db_prod psql -U postgres -d career_advisor -c "
DELETE FROM system_settings 
WHERE key ~ '[a-z]';
"

echo ""
echo "=== Verifying deletion ==="

# 4. Show remaining keys (should all be UPPERCASE)
docker exec advisor_db_prod psql -U postgres -d career_advisor -c "
SELECT key FROM system_settings ORDER BY key;
"

echo ""
echo "✅ Cleanup completed!"
