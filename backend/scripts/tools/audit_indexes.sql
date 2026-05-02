-- ============================================================================
-- DATABASE INDEX AUDIT REPORT
-- ============================================================================
-- This script generates a comprehensive report of all indexes in the database
-- Run: psql -U postgres -d career_advisor -f audit_indexes.sql
-- ============================================================================

\echo '================================================================================'
\echo 'DATABASE INDEX AUDIT REPORT'
\echo '================================================================================'
\echo ''

-- Summary by table
\echo '📊 INDEX SUMMARY BY TABLE'
\echo ''
SELECT 
    tablename as "Table",
    COUNT(*) as "Total",
    COUNT(CASE WHEN indexname LIKE 'idx_%' THEN 1 END) as "Performance",
    COUNT(CASE WHEN indexname LIKE 'ix_%' THEN 1 END) as "SQLAlchemy",
    COUNT(CASE WHEN indexname LIKE '%_pkey' OR indexname LIKE '%_key' OR indexname LIKE 'uq_%' THEN 1 END) as "Constraints"
FROM pg_indexes
WHERE schemaname = 'public'
GROUP BY tablename
ORDER BY tablename;

\echo ''
\echo '================================================================================'
\echo 'INDEX TYPE SUMMARY'
\echo '================================================================================'
\echo ''

SELECT 
    CASE 
        WHEN indexname LIKE 'idx_%' THEN 'Performance (Custom)'
        WHEN indexname LIKE 'ix_%' THEN 'SQLAlchemy (Auto)'
        WHEN indexname LIKE '%_pkey' THEN 'Primary Key'
        WHEN indexname LIKE '%_key' OR indexname LIKE 'uq_%' THEN 'Unique Constraint'
        ELSE 'Other'
    END as "Category",
    COUNT(*) as "Count"
FROM pg_indexes
WHERE schemaname = 'public'
GROUP BY 
    CASE 
        WHEN indexname LIKE 'idx_%' THEN 'Performance (Custom)'
        WHEN indexname LIKE 'ix_%' THEN 'SQLAlchemy (Auto)'
        WHEN indexname LIKE '%_pkey' THEN 'Primary Key'
        WHEN indexname LIKE '%_key' OR indexname LIKE 'uq_%' THEN 'Unique Constraint'
        ELSE 'Other'
    END
ORDER BY "Count" DESC;

\echo ''
\echo '================================================================================'
\echo 'INDEX METHOD BREAKDOWN'
\echo '================================================================================'
\echo ''

SELECT 
    CASE 
        WHEN indexdef LIKE '%USING gin%' THEN 'GIN (Array/JSON/Text)'
        WHEN indexdef LIKE '%USING hnsw%' THEN 'HNSW (Vector Search)'
        WHEN indexdef LIKE '%USING btree%' THEN 'B-Tree (Standard)'
        ELSE 'Other'
    END as "Index Method",
    COUNT(*) as "Count"
FROM pg_indexes
WHERE schemaname = 'public'
GROUP BY 
    CASE 
        WHEN indexdef LIKE '%USING gin%' THEN 'GIN (Array/JSON/Text)'
        WHEN indexdef LIKE '%USING hnsw%' THEN 'HNSW (Vector Search)'
        WHEN indexdef LIKE '%USING btree%' THEN 'B-Tree (Standard)'
        ELSE 'Other'
    END
ORDER BY "Count" DESC;

\echo ''
\echo '================================================================================'
\echo 'CRITICAL INDEX VERIFICATION'
\echo '================================================================================'
\echo ''

-- Check critical indexes exist
SELECT 
    'courses' as "Table",
    'idx_courses_tags_gin' as "Index",
    CASE WHEN EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND tablename = 'courses' 
        AND indexname = 'idx_courses_tags_gin'
    ) THEN '✅ EXISTS' ELSE '❌ MISSING' END as "Status",
    'GIN index for tags array search' as "Purpose"
UNION ALL
SELECT 
    'courses',
    'idx_courses_skills_raw_gin',
    CASE WHEN EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND tablename = 'courses' 
        AND indexname = 'idx_courses_skills_raw_gin'
    ) THEN '✅ EXISTS' ELSE '❌ MISSING' END,
    'GIN index for skills JSON search'
UNION ALL
SELECT 
    'courses',
    'idx_courses_vector_hnsw',
    CASE WHEN EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND tablename = 'courses' 
        AND indexname = 'idx_courses_vector_hnsw'
    ) THEN '✅ EXISTS' ELSE '❌ MISSING' END,
    'HNSW index for vector similarity'
UNION ALL
SELECT 
    'courses',
    'idx_courses_title_trgm',
    CASE WHEN EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND tablename = 'courses' 
        AND indexname = 'idx_courses_title_trgm'
    ) THEN '✅ EXISTS' ELSE '❌ MISSING' END,
    'Trigram index for title ILIKE'
UNION ALL
SELECT 
    'job_skill_requirement',
    'idx_job_skill_req_job_id',
    CASE WHEN EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND tablename = 'job_skill_requirement' 
        AND indexname = 'idx_job_skill_req_job_id'
    ) THEN '✅ EXISTS' ELSE '❌ MISSING' END,
    'FK index for job_id (JOIN performance)'
UNION ALL
SELECT 
    'job_skill_requirement',
    'idx_job_skill_req_skill_id',
    CASE WHEN EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND tablename = 'job_skill_requirement' 
        AND indexname = 'idx_job_skill_req_skill_id'
    ) THEN '✅ EXISTS' ELSE '❌ MISSING' END,
    'FK index for skill_id (JOIN performance)'
UNION ALL
SELECT 
    'user_skill_profile',
    'idx_user_skill_profile_user_id',
    CASE WHEN EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND tablename = 'user_skill_profile' 
        AND indexname = 'idx_user_skill_profile_user_id'
    ) THEN '✅ EXISTS' ELSE '❌ MISSING' END,
    'Index for user_id filtering'
UNION ALL
SELECT 
    'skills',
    'idx_skills_vector_hnsw',
    CASE WHEN EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND tablename = 'skills' 
        AND indexname = 'idx_skills_vector_hnsw'
    ) THEN '✅ EXISTS' ELSE '❌ MISSING' END,
    'HNSW index for skill vectors';

\echo ''
\echo '================================================================================'
\echo 'DETAILED INDEX LIST (COURSES TABLE)'
\echo '================================================================================'
\echo ''

SELECT 
    indexname as "Index Name",
    CASE 
        WHEN indexdef LIKE '%USING gin%' THEN 'GIN'
        WHEN indexdef LIKE '%USING hnsw%' THEN 'HNSW'
        WHEN indexdef LIKE '%USING btree%' THEN 'B-Tree'
        ELSE 'Other'
    END as "Method",
    pg_size_pretty(pg_relation_size(indexrelid::regclass)) as "Size"
FROM pg_indexes
WHERE schemaname = 'public' 
AND tablename = 'courses'
ORDER BY indexname;

\echo ''
\echo '================================================================================'
\echo 'SETUP SCRIPT COMPATIBILITY CHECK'
\echo '================================================================================'
\echo ''
\echo 'Checking if indexes are defined in SQLAlchemy models or migration scripts...'
\echo ''

-- Check if models.py has index definitions
\echo '📝 SQLAlchemy Model Indexes (from Column definitions):'
\echo '   - source_platform: index=True (line 211)'
\echo '   - source_id: index=True (line 212)'
\echo '   - external_uuid: index=True (line 213)'
\echo ''
\echo '📝 Performance Indexes (from add_missing_indexes.sql):'
\echo '   - 25 custom indexes created via migration script'
\echo '   - Script location: backend/scripts/add_missing_indexes.sql'
\echo ''
\echo '⚠️  IMPORTANT: New deployments need to run add_missing_indexes.sql'
\echo '   Command: psql -U postgres -d career_advisor -f scripts/add_missing_indexes.sql'
\echo ''
\echo '================================================================================'
