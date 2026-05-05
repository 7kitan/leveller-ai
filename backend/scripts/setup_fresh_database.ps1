# PowerShell script for fresh database setup
# Usage: .\setup_fresh_database.ps1 [-Environment dev|prod]

param(
    [string]$Environment = "dev"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$MigrationsDir = Join-Path $ScriptDir "migrations"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Fresh Database Setup" -ForegroundColor Cyan
Write-Host "Environment: $Environment" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Load environment variables
if ($Environment -eq "prod") {
    $EnvFile = Join-Path (Split-Path -Parent $ScriptDir) ".env.production"
} else {
    $EnvFile = Join-Path (Split-Path -Parent $ScriptDir) ".env"
}

if (-not (Test-Path $EnvFile)) {
    Write-Host "Error: Environment file not found: $EnvFile" -ForegroundColor Red
    exit 1
}

# Parse .env file
Get-Content $EnvFile | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
        $key = $matches[1].Trim()
        $value = $matches[2].Trim()
        Set-Variable -Name $key -Value $value -Scope Script
    }
}

$DbHost = if ($POSTGRES_HOST) { $POSTGRES_HOST } else { "localhost" }
$DbPort = if ($POSTGRES_PORT) { $POSTGRES_PORT } else { "5432" }
$DbName = if ($POSTGRES_DB) { $POSTGRES_DB } else { "career_advisor" }
$DbUser = if ($POSTGRES_USER) { $POSTGRES_USER } else { "postgres" }

Write-Host "Database: $DbName@$DbHost:$DbPort" -ForegroundColor Yellow
Write-Host ""

# Function to run migration
function Run-Migration {
    param($MigrationFile)
    
    $FileName = Split-Path $MigrationFile -Leaf
    Write-Host "Running: $FileName" -ForegroundColor Yellow
    
    if ($Environment -eq "prod") {
        $env:PGPASSWORD = $POSTGRES_PASSWORD
        & psql -h $DbHost -p $DbPort -U $DbUser -d $DbName -f $MigrationFile
    } else {
        Get-Content $MigrationFile -Raw | docker exec -i advisor_db psql -U $DbUser -d $DbName
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Completed: $FileName" -ForegroundColor Green
    } else {
        Write-Host "✗ Failed: $FileName" -ForegroundColor Red
        exit 1
    }
    Write-Host ""
}

# Check if prompt_templates table exists
Write-Host "Checking existing tables..." -ForegroundColor Yellow
if ($Environment -eq "prod") {
    $env:PGPASSWORD = $POSTGRES_PASSWORD
    $TableExists = & psql -h $DbHost -p $DbPort -U $DbUser -d $DbName -tAc "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'prompt_templates');"
} else {
    $TableExists = docker exec advisor_db psql -U $DbUser -d $DbName -tAc "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'prompt_templates');"
}

if ($TableExists -eq "t") {
    Write-Host "✓ prompt_templates table exists" -ForegroundColor Green
    Write-Host "Skipping schema creation..." -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host "✗ prompt_templates table does not exist" -ForegroundColor Yellow
    Write-Host "Creating schema..." -ForegroundColor Yellow
    Write-Host ""
    
    Run-Migration (Join-Path $MigrationsDir "000_create_prompt_schema.sql")
}

# Run prompts setup (idempotent)
Write-Host "Setting up prompts..." -ForegroundColor Yellow
Run-Migration (Join-Path $MigrationsDir "001_setup_prompts.sql")

# Check if core tables exist
Write-Host "Checking core tables..." -ForegroundColor Yellow
if ($Environment -eq "prod") {
    $env:PGPASSWORD = $POSTGRES_PASSWORD
    $CoreExists = & psql -h $DbHost -p $DbPort -U $DbUser -d $DbName -tAc "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users');"
} else {
    $CoreExists = docker exec advisor_db psql -U $DbUser -d $DbName -tAc "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users');"
}

if ($CoreExists -eq "t") {
    Write-Host "✓ Core tables exist" -ForegroundColor Green
    Write-Host "Skipping core table creation..." -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host "✗ Core tables do not exist" -ForegroundColor Yellow
    Write-Host "Creating core tables..." -ForegroundColor Yellow
    Write-Host ""
    
    Run-Migration (Join-Path $MigrationsDir "003_create_core_tables.sql")
}

# Check if relationship tables exist
Write-Host "Checking relationship tables..." -ForegroundColor Yellow
if ($Environment -eq "prod") {
    $env:PGPASSWORD = $POSTGRES_PASSWORD
    $RelExists = & psql -h $DbHost -p $DbPort -U $DbUser -d $DbName -tAc "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'job_skill_requirement');"
} else {
    $RelExists = docker exec advisor_db psql -U $DbUser -d $DbName -tAc "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'job_skill_requirement');"
}

if ($RelExists -eq "t") {
    Write-Host "✓ Relationship tables exist" -ForegroundColor Green
    Write-Host "Skipping relationship table creation..." -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host "✗ Relationship tables do not exist" -ForegroundColor Yellow
    Write-Host "Creating relationship tables..." -ForegroundColor Yellow
    Write-Host ""
    
    Run-Migration (Join-Path $MigrationsDir "004_create_relationship_tables.sql")
}

# Check if feedback/logging tables exist
Write-Host "Checking feedback and logging tables..." -ForegroundColor Yellow
if ($Environment -eq "prod") {
    $env:PGPASSWORD = $POSTGRES_PASSWORD
    $LogExists = & psql -h $DbHost -p $DbPort -U $DbUser -d $DbName -tAc "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'llm_logs');"
} else {
    $LogExists = docker exec advisor_db psql -U $DbUser -d $DbName -tAc "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'llm_logs');"
}

if ($LogExists -eq "t") {
    Write-Host "✓ Feedback and logging tables exist" -ForegroundColor Green
    Write-Host "Skipping feedback/logging table creation..." -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host "✗ Feedback and logging tables do not exist" -ForegroundColor Yellow
    Write-Host "Creating feedback and logging tables..." -ForegroundColor Yellow
    Write-Host ""
    
    Run-Migration (Join-Path $MigrationsDir "005_create_feedback_logging_tables.sql")
}

# Check if course/market tables exist
Write-Host "Checking course and market tables..." -ForegroundColor Yellow
if ($Environment -eq "prod") {
    $env:PGPASSWORD = $POSTGRES_PASSWORD
    $CourseExists = & psql -h $DbHost -p $DbPort -U $DbUser -d $DbName -tAc "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'courses');"
} else {
    $CourseExists = docker exec advisor_db psql -U $DbUser -d $DbName -tAc "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'courses');"
}

if ($CourseExists -eq "t") {
    Write-Host "✓ Course and market tables exist" -ForegroundColor Green
    Write-Host "Skipping course/market table creation..." -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host "✗ Course and market tables do not exist" -ForegroundColor Yellow
    Write-Host "Creating course and market tables..." -ForegroundColor Yellow
    Write-Host ""
    
    Run-Migration (Join-Path $MigrationsDir "006_create_course_market_tables.sql")
}

# Check if benchmark tables exist
Write-Host "Checking benchmark tables..." -ForegroundColor Yellow
if ($Environment -eq "prod") {
    $env:PGPASSWORD = $POSTGRES_PASSWORD
    $BenchmarkExists = & psql -h $DbHost -p $DbPort -U $DbUser -d $DbName -tAc "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'llm_test_sets');"
} else {
    $BenchmarkExists = docker exec advisor_db psql -U $DbUser -d $DbName -tAc "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'llm_test_sets');"
}

if ($BenchmarkExists -eq "t") {
    Write-Host "✓ Benchmark tables exist" -ForegroundColor Green
    Write-Host "Skipping benchmark table creation..." -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host "✗ Benchmark tables do not exist" -ForegroundColor Yellow
    Write-Host "Creating benchmark tables..." -ForegroundColor Yellow
    Write-Host ""
    
    Run-Migration (Join-Path $MigrationsDir "002_create_benchmark_tables.sql")
}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Setup completed successfully!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Final verification
Write-Host "Verifying installation..." -ForegroundColor Yellow
Write-Host ""

Write-Host "1. Prompt Templates:" -ForegroundColor Cyan
if ($Environment -eq "prod") {
    $env:PGPASSWORD = $POSTGRES_PASSWORD
    & psql -h $DbHost -p $DbPort -U $DbUser -d $DbName -c "SELECT key, name, category, is_active FROM prompt_templates WHERE is_active = true ORDER BY category;"
} else {
    docker exec advisor_db psql -U $DbUser -d $DbName -c "SELECT key, name, category, is_active FROM prompt_templates WHERE is_active = true ORDER BY category;"
}

Write-Host ""
Write-Host "2. All Tables:" -ForegroundColor Cyan
if ($Environment -eq "prod") {
    $env:PGPASSWORD = $POSTGRES_PASSWORD
    & psql -h $DbHost -p $DbPort -U $DbUser -d $DbName -c "SELECT table_name, (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as columns FROM information_schema.tables t WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name;"
} else {
    docker exec advisor_db psql -U $DbUser -d $DbName -c "SELECT table_name, (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as columns FROM information_schema.tables t WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name;"
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Seed skills: python scripts/seed_data.py" -ForegroundColor White
Write-Host "2. Restart services: docker-compose restart" -ForegroundColor White
Write-Host "3. Reload cache: curl -X POST http://localhost:8000/admin/prompts/reload" -ForegroundColor White
Write-Host "4. Test Admin UI: http://localhost:3000/admin/prompts" -ForegroundColor White
Write-Host "==========================================" -ForegroundColor Cyan
