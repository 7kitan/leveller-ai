# Setup Prompts and Benchmark System

## Overview

This directory contains scripts to initialize the prompt management and benchmark systems.

## Quick Start

### Windows (PowerShell)

```powershell
cd backend/scripts
.\setup_prompts_and_benchmark.ps1
```

### Linux/Mac (Bash)

```bash
cd backend/scripts
chmod +x setup_prompts_and_benchmark.sh
./setup_prompts_and_benchmark.sh
```

## What This Does

The setup script performs the following steps:

1. **Pre-flight Checks**
   - Verifies Docker container is running
   - Verifies database exists

2. **Create Prompt Templates Table**
   - Runs `000_create_prompt_schema.sql`
   - Creates `prompt_templates` table with indexes and triggers
   - Skips if table already exists

3. **Populate Initial Prompts**
   - Runs `001_setup_prompts.sql`
   - Loads 6 prompt templates:
     - `cv_parsing` - CV parsing with PII masking
     - `gap_analysis` - Gap analysis from requirements
     - `gap_analysis_merged` - Combined JD parsing + gap analysis
     - `course_recommendation` - Course selection and roadmap
     - `jd_parsing` - Job description skill extraction
     - `roadmap_building` - Learning roadmap generation
   - Skips if 5+ active prompts already exist

4. **Create Benchmark Tables**
   - Runs `002_create_benchmark_tables.sql`
   - Creates 4 tables:
     - `llm_test_sets` - Test set definitions
     - `llm_test_cases` - Individual test cases
     - `llm_benchmark_sessions` - Benchmark execution sessions
     - `llm_benchmark_results` - Test case results
   - Skips if tables already exist

5. **Populate Test Sets (Optional)**
   - Runs `populate_benchmark_test_sets.sql` if available
   - Creates sample test sets for CV parsing and gap analysis
   - Skips if test sets already exist

## Migration Files

### Core Migrations (Required)

| File | Description | Creates |
|------|-------------|---------|
| `000_create_prompt_schema.sql` | Prompt templates table schema | `prompt_templates` table |
| `001_setup_prompts.sql` | Initial prompt data | 6 prompt templates |
| `002_create_benchmark_tables.sql` | Benchmark system schema | 4 benchmark tables |

### Optional Migrations

| File | Description | Creates |
|------|-------------|---------|
| `populate_benchmark_test_sets.sql` | Sample test data | Test sets and cases |
| `add_jd_parsing_prompt.sql` | Add JD parsing prompt | 1 prompt template |
| `add_course_recommendation_prompt.sql` | Add course recommendation | 1 prompt template |

## Requirements

- Docker Desktop running
- PostgreSQL container `advisor_db` running
- Database `career_advisor` exists

## Verification

After running the script, verify the setup:

```sql
-- Check prompts
SELECT category, is_active, 
       model_config->>'temperature' as temp 
FROM prompt_templates 
ORDER BY category;

-- Check benchmark tables
SELECT table_name 
FROM information_schema.tables 
WHERE table_name LIKE 'llm_%';

-- Check test sets
SELECT name, flow_type, 
       (SELECT COUNT(*) FROM llm_test_cases WHERE test_set_id = llm_test_sets.id) as cases
FROM llm_test_sets;
```

## Troubleshooting

### Error: "Database container is not running"

**Solution**: Start the database container
```bash
docker-compose up -d advisor_db
```

### Error: "Database 'career_advisor' does not exist"

**Solution**: Create the database
```bash
docker exec advisor_db psql -U postgres -c "CREATE DATABASE career_advisor;"
```

### Error: "Migration file not found"

**Solution**: Ensure you're running from the correct directory
```bash
cd backend/scripts
pwd  # Should show: .../backend/scripts
```

### Error: "Table already exists"

**Solution**: This is normal. The script skips existing tables. If you want to recreate:
```sql
-- Drop and recreate (WARNING: This deletes all data)
DROP TABLE IF EXISTS prompt_templates CASCADE;
DROP TABLE IF EXISTS llm_benchmark_results CASCADE;
DROP TABLE IF EXISTS llm_benchmark_sessions CASCADE;
DROP TABLE IF EXISTS llm_test_cases CASCADE;
DROP TABLE IF EXISTS llm_test_sets CASCADE;

-- Then run the setup script again
```

## Manual Migration

If you prefer to run migrations manually:

```bash
# Step 1: Create prompt schema
docker exec -i advisor_db psql -U postgres -d career_advisor < migrations/000_create_prompt_schema.sql

# Step 2: Populate prompts
docker exec -i advisor_db psql -U postgres -d career_advisor < migrations/001_setup_prompts.sql

# Step 3: Create benchmark tables
docker exec -i advisor_db psql -U postgres -d career_advisor < migrations/002_create_benchmark_tables.sql

# Step 4: Populate test sets (optional)
docker exec -i advisor_db psql -U postgres -d career_advisor < migrations/populate_benchmark_test_sets.sql
```

## Next Steps

After successful setup:

1. **Restart Workers**
   ```bash
   docker-compose restart advisor_worker_analysis advisor_worker_parsing
   ```

2. **Access Admin UI**
   - Prompts: http://localhost:3000/admin/prompts
   - Benchmarks: http://localhost:3000/admin/benchmarks

3. **Verify Prompts**
   - Check all 6 prompts are active
   - Verify temperature settings (0 or 0.6)
   - Test prompt rendering with parameters

4. **Run Benchmark**
   - Use Quick Test to verify system works
   - Run full benchmark with test sets
   - Export results for analysis

## Related Documentation

- `backend/BENCHMARK_GUIDE.md` - Complete benchmark system guide
- `backend/shared/ai_service/README.md` - AI service architecture
- `backend/docs/PROMPT_MANAGEMENT.md` - Prompt management guide

## Support

If you encounter issues:

1. Check Docker logs: `docker logs advisor_db`
2. Check worker logs: `docker logs advisor_worker_parsing`
3. Verify database connection: `docker exec advisor_db psql -U postgres -d career_advisor -c "\dt"`
