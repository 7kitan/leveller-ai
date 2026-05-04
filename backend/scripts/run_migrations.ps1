# PowerShell Migration Runner for Windows
# Usage: .\run_migrations.ps1 [-Environment dev|prod]

param(
    [string]$Environment = "dev"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$MigrationsDir = Join-Path $ScriptDir "migrations"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Running Prompt Template Migrations" -ForegroundColor Cyan
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

# Run migrations in order
$MigrationFiles = Get-ChildItem -Path $MigrationsDir -Filter "*.sql" | Sort-Object Name

foreach ($MigrationFile in $MigrationFiles) {
    Write-Host "Running migration: $($MigrationFile.Name)" -ForegroundColor Yellow
    
    if ($Environment -eq "prod") {
        # Production: Use psql directly
        $env:PGPASSWORD = $POSTGRES_PASSWORD
        & psql -h $DbHost -p $DbPort -U $DbUser -d $DbName -f $MigrationFile.FullName
    } else {
        # Development: Use docker exec
        $Content = Get-Content $MigrationFile.FullName -Raw
        $Content | docker exec -i advisor_db psql -U $DbUser -d $DbName
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Migration completed: $($MigrationFile.Name)" -ForegroundColor Green
    } else {
        Write-Host "✗ Migration failed: $($MigrationFile.Name)" -ForegroundColor Red
        exit 1
    }
    Write-Host ""
}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "All migrations completed successfully!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Verify prompts
Write-Host "Verifying prompt templates..." -ForegroundColor Yellow
if ($Environment -eq "prod") {
    $env:PGPASSWORD = $POSTGRES_PASSWORD
    & psql -h $DbHost -p $DbPort -U $DbUser -d $DbName -c "SELECT key, name, category, is_active FROM prompt_templates WHERE is_active = true ORDER BY category;"
} else {
    docker exec advisor_db psql -U $DbUser -d $DbName -c "SELECT key, name, category, is_active FROM prompt_templates WHERE is_active = true ORDER BY category;"
}
