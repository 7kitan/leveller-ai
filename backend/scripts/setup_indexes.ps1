# Setup Database Indexes for Career Advisor
# PowerShell script for Windows

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Career Advisor - Database Index Setup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SqlFile = Join-Path $ScriptDir "setup_indexes.sql"

# Check if SQL file exists
if (-not (Test-Path $SqlFile)) {
    Write-Host "❌ Error: setup_indexes.sql not found in $ScriptDir" -ForegroundColor Red
    exit 1
}

# Load environment variables from .env if exists
$EnvFile = Join-Path (Split-Path -Parent $ScriptDir) ".env"
if (Test-Path $EnvFile) {
    Write-Host "📄 Loading environment variables from .env..." -ForegroundColor Yellow
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^([^#][^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}

# Set default values
$PostgresUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "postgres" }
$PostgresDb = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "career_advisor" }
$ContainerName = if ($env:CONTAINER_NAME) { $env:CONTAINER_NAME } else { "advisor_db_prod" }

Write-Host "📊 Database Configuration:" -ForegroundColor Cyan
Write-Host "   Container: $ContainerName"
Write-Host "   Database: $PostgresDb"
Write-Host "   User: $PostgresUser"
Write-Host ""

# Check if Docker is running
try {
    docker ps | Out-Null
} catch {
    Write-Host "❌ Error: Docker is not running" -ForegroundColor Red
    Write-Host "   Please start Docker Desktop first" -ForegroundColor Yellow
    exit 1
}

# Check if container is running
$containerRunning = docker ps --format "{{.Names}}" | Select-String -Pattern "^$ContainerName$"
if (-not $containerRunning) {
    Write-Host "Error: Container $ContainerName is not running" -ForegroundColor Red
    Write-Host "Please start the database container first:" -ForegroundColor Yellow
    Write-Host "docker-compose -f docker-compose.prod.yml up -d db"
    exit 1
}

Write-Host "🔧 Creating indexes..." -ForegroundColor Yellow
Write-Host ""

# Run SQL file
try {
    Get-Content $SqlFile | docker exec -i $ContainerName psql -U $PostgresUser -d $PostgresDb
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "Index setup completed successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Verifying indexes..." -ForegroundColor Yellow
        Write-Host ""
        
        # Show vector indexes
        $query = "SELECT tablename, indexname FROM pg_indexes WHERE schemaname = 'public' AND indexname LIKE '%vector%' ORDER BY tablename;"
        docker exec $ContainerName psql -U $PostgresUser -d $PostgresDb -c $query
        
        Write-Host ""
        Write-Host "Setup complete!" -ForegroundColor Green
    } else {
        throw "SQL execution failed"
    }
} catch {
    Write-Host ""
    Write-Host "Error: Index setup failed" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
