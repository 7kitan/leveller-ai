# =============================================================================
# Setup Prompt Templates and Benchmark System (PowerShell)
# =============================================================================
# This script creates and populates:
# 1. prompt_templates table
# 2. Benchmark tables (test_sets, test_cases, runs, results)
# 3. Initial prompt data
# 4. Sample benchmark test sets
#
# Usage:
#   .\setup_prompts_and_benchmark.ps1 [dev|prod]
#
# Requirements:
#   - Docker Desktop running
#   - PostgreSQL database exists
#   - .env file configured
# =============================================================================

param(
    [string]$Environment = "dev"
)

$ErrorActionPreference = "Stop"

# Load .env file
$envFile = Join-Path (Split-Path $PSScriptRoot -Parent) ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^([^#][^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
    Write-Host "[SUCCESS] .env file loaded" -ForegroundColor Green
}
else {
    Write-Host "[WARNING] .env file not found, using defaults" -ForegroundColor Yellow
}

# Configuration based on environment
if ($Environment -eq "prod") {
    $DB_CONTAINER = "advisor_db_prod"
    $DB_NAME = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "career_advisor" }
    $DB_USER = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "postgres" }
    $DB_PASSWORD = $env:POSTGRES_PASSWORD
}
else {
    $DB_CONTAINER = "advisor_db"
    $DB_NAME = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "career_advisor" }
    $DB_USER = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "postgres" }
    $DB_PASSWORD = if ($env:POSTGRES_PASSWORD) { $env:POSTGRES_PASSWORD } else { "postgres" }
}

$MIGRATIONS_DIR = Join-Path $PSScriptRoot "migrations"

# =============================================================================
# Helper Functions
# =============================================================================

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Test-DockerContainer {
    $running = docker ps --format "{{.Names}}" | Select-String -Pattern $DB_CONTAINER -Quiet
    if (-not $running) {
        Write-Error "Database container '$DB_CONTAINER' is not running"
        if ($Environment -eq "prod") {
            Write-Info "Start it with: docker-compose -f docker-compose.prod.yml up -d db"
        }
        else {
            Write-Info "Start it with: docker-compose up -d advisor_db"
        }
        exit 1
    }
    Write-Success "Database container is running"
}

function Test-Database {
    $exists = docker exec $DB_CONTAINER psql -U $DB_USER -lqt 2>$null | Select-String -Pattern $DB_NAME -Quiet
    if (-not $exists) {
        Write-Error "Database '$DB_NAME' does not exist"
        exit 1
    }
    Write-Success "Database '$DB_NAME' exists"
}

function Invoke-SqlFile {
    param(
        [string]$FilePath,
        [string]$Description
    )
    
    Write-Info "Running: $Description"
    
    if (-not (Test-Path $FilePath)) {
        Write-Error "Migration file not found: $FilePath"
        exit 1
    }
    
    try {
        if ($DB_PASSWORD) {
            $env:PGPASSWORD = $DB_PASSWORD
            Get-Content $FilePath -Raw | docker exec -i $DB_CONTAINER bash -c "PGPASSWORD='$DB_PASSWORD' psql -U $DB_USER -d $DB_NAME" 2>&1 | Out-Null
        }
        else {
            Get-Content $FilePath -Raw | docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME 2>&1 | Out-Null
        }
        Write-Success "$Description completed"
        return $true
    }
    catch {
        Write-Error "$Description failed: $_"
        return $false
    }
}

function Test-TableExists {
    param([string]$TableName)
    
    $query = "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name='$TableName');"
    if ($DB_PASSWORD) {
        $result = docker exec $DB_CONTAINER bash -c "PGPASSWORD='$DB_PASSWORD' psql -U $DB_USER -d $DB_NAME -tAc `"$query`"" 2>$null
    }
    else {
        $result = docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -tAc $query 2>$null
    }
    return $result -eq "t"
}

function Get-PromptCount {
    $query = "SELECT COUNT(*) FROM prompt_templates WHERE is_active = true;"
    if ($DB_PASSWORD) {
        $result = docker exec $DB_CONTAINER bash -c "PGPASSWORD='$DB_PASSWORD' psql -U $DB_USER -d $DB_NAME -tAc `"$query`"" 2>$null
    }
    else {
        $result = docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -tAc $query 2>$null
    }
    if ($result) { return [int]$result } else { return 0 }
}

function Get-TestSetCount {
    $query = "SELECT COUNT(*) FROM llm_test_sets;"
    if ($DB_PASSWORD) {
        $result = docker exec $DB_CONTAINER bash -c "PGPASSWORD='$DB_PASSWORD' psql -U $DB_USER -d $DB_NAME -tAc `"$query`"" 2>$null
    }
    else {
        $result = docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -tAc $query 2>$null
    }
    if ($result) { return [int]$result } else { return 0 }
}

# =============================================================================
# Main Setup Process
# =============================================================================

function Main {
    Write-Host ""
    Write-Host "=========================================================================" -ForegroundColor Cyan
    Write-Host "  Setup Prompt Templates and Benchmark System" -ForegroundColor Cyan
    Write-Host "  Environment: $Environment" -ForegroundColor Cyan
    Write-Host "=========================================================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Step 1: Pre-flight checks
    Write-Info "Step 1/5: Pre-flight checks"
    Write-Info "Container: $DB_CONTAINER"
    Write-Info "Database: $DB_NAME"
    Write-Info "User: $DB_USER"
    Test-DockerContainer
    Test-Database
    Write-Host ""
    
    # Step 2: Create prompt_templates table
    Write-Info "Step 2/5: Create prompt_templates table"
    if (Test-TableExists "prompt_templates") {
        Write-Warning "Table 'prompt_templates' already exists, skipping creation"
    }
    else {
        $file = Join-Path $MIGRATIONS_DIR "000_create_prompt_schema.sql"
        Invoke-SqlFile -FilePath $file -Description "Create prompt_templates schema"
    }
    Write-Host ""
    
    # Step 3: Populate initial prompts
    Write-Info "Step 3/5: Populate prompt templates"
    $promptCount = Get-PromptCount
    if ($promptCount -ge 5) {
        Write-Warning "Found $promptCount active prompts, skipping population"
    }
    else {
        $file = Join-Path $MIGRATIONS_DIR "001_setup_prompts.sql"
        Invoke-SqlFile -FilePath $file -Description "Populate initial prompts"
        $promptCount = Get-PromptCount
        Write-Success "Loaded $promptCount active prompts"
    }
    Write-Host ""
    
    # Step 4: Create benchmark tables
    Write-Info "Step 4/5: Create benchmark tables"
    if (Test-TableExists "llm_test_sets") {
        Write-Warning "Benchmark tables already exist, skipping creation"
    }
    else {
        $file = Join-Path $MIGRATIONS_DIR "002_create_benchmark_tables.sql"
        Invoke-SqlFile -FilePath $file -Description "Create benchmark tables"
    }
    Write-Host ""
    
    # Step 5: Populate benchmark test sets (optional)
    Write-Info "Step 5/5: Populate benchmark test sets"
    $testSetCount = Get-TestSetCount
    if ($testSetCount -ge 1) {
        Write-Warning "Found $testSetCount test sets, skipping population"
    }
    else {
        $file = Join-Path $MIGRATIONS_DIR "populate_benchmark_test_sets.sql"
        if (Test-Path $file) {
            Invoke-SqlFile -FilePath $file -Description "Populate benchmark test sets"
            $testSetCount = Get-TestSetCount
            Write-Success "Loaded $testSetCount test sets"
        }
        else {
            Write-Warning "populate_benchmark_test_sets.sql not found, skipping"
        }
    }
    Write-Host ""
    
    # Final verification
    Write-Host "=========================================================================" -ForegroundColor Cyan
    Write-Host "  Setup Complete - Verification" -ForegroundColor Cyan
    Write-Host "=========================================================================" -ForegroundColor Cyan
    
    # Verify prompt_templates
    $promptCount = Get-PromptCount
    Write-Host "✓ prompt_templates: $promptCount active prompts" -ForegroundColor Green
    
    # Verify benchmark tables
    if (Test-TableExists "llm_test_sets") {
        $testSetCount = Get-TestSetCount
        Write-Host "✓ llm_test_sets: $testSetCount test sets" -ForegroundColor Green
    }
    
    if (Test-TableExists "llm_test_cases") {
        $query = "SELECT COUNT(*) FROM llm_test_cases;"
        if ($DB_PASSWORD) {
            $testCaseCount = docker exec $DB_CONTAINER bash -c "PGPASSWORD='$DB_PASSWORD' psql -U $DB_USER -d $DB_NAME -tAc `"$query`"" 2>$null
        }
        else {
            $testCaseCount = docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -tAc $query 2>$null
        }
        Write-Host "✓ llm_test_cases: $testCaseCount test cases" -ForegroundColor Green
    }
    
    if (Test-TableExists "llm_benchmark_sessions") {
        Write-Host "✓ llm_benchmark_sessions: Ready" -ForegroundColor Green
    }
    
    if (Test-TableExists "llm_benchmark_results") {
        Write-Host "✓ llm_benchmark_results: Ready" -ForegroundColor Green
    }
    
    Write-Host ""
    Write-Host "=========================================================================" -ForegroundColor Cyan
    Write-Success "All setup completed successfully!"
    Write-Host "=========================================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Next steps:"
    if ($Environment -eq "prod") {
        Write-Host "  1. Enable benchmark: docker exec $DB_CONTAINER bash -c `"PGPASSWORD='$DB_PASSWORD' psql -U $DB_USER -d $DB_NAME -c \`"INSERT INTO system_settings (key, value) VALUES ('ENABLE_BENCHMARK', 'true') ON CONFLICT (key) DO UPDATE SET value = 'true';\`"`""
        Write-Host "  2. Restart workers: docker-compose -f docker-compose.prod.yml restart worker-benchmark"
        Write-Host "  3. Access admin UI: https://yourdomain.com/admin/prompts"
    }
    else {
        Write-Host "  1. Enable benchmark: docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c `"INSERT INTO system_settings (key, value) VALUES ('ENABLE_BENCHMARK', 'true') ON CONFLICT (key) DO UPDATE SET value = 'true';`""
        Write-Host "  2. Restart workers: docker-compose restart advisor_worker_benchmark"
        Write-Host "  3. Access admin UI: http://localhost:3000/admin/prompts"
    }
    Write-Host ""
}

# =============================================================================
# Script Entry Point
# =============================================================================

# Check if running from correct directory
if (-not (Test-Path $MIGRATIONS_DIR)) {
    Write-Error "Migrations directory not found: $MIGRATIONS_DIR"
    Write-Info "Please run this script from backend/scripts directory"
    exit 1
}

# Run main setup
Main

exit 0
