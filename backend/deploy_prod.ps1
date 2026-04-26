# =============================================================================
# Production Backend Deployment Script (PowerShell)
# Build and run all backend services without git pull
# =============================================================================

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Blue
Write-Host "  Backend Production Deployment" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

# Step 1: Stop existing containers
Write-Host "[1/6] Stopping existing containers..." -ForegroundColor Yellow
docker compose -f docker-compose.prod.yml down
Write-Host "✅ Containers stopped" -ForegroundColor Green
Write-Host ""

# Step 2: Build all images
Write-Host "[2/6] Building all Docker images..." -ForegroundColor Yellow
Write-Host "This may take 5-10 minutes..."
docker compose -f docker-compose.prod.yml build --no-cache
Write-Host "✅ All images built successfully" -ForegroundColor Green
Write-Host ""

# Step 3: Start database and redis first
Write-Host "[3/6] Starting database and redis..." -ForegroundColor Yellow
docker compose -f docker-compose.prod.yml up -d db redis
Write-Host "Waiting for database and redis to be healthy..."
Start-Sleep -Seconds 15

# Check database health
try {
    docker compose -f docker-compose.prod.yml exec db pg_isready -U postgres | Out-Null
    Write-Host "✅ Database is healthy" -ForegroundColor Green
} catch {
    Write-Host "❌ Database is not ready" -ForegroundColor Red
    exit 1
}

# Check redis health
try {
    docker compose -f docker-compose.prod.yml exec redis redis-cli ping | Out-Null
    Write-Host "✅ Redis is healthy" -ForegroundColor Green
} catch {
    Write-Host "❌ Redis is not ready" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 4: Start all services
Write-Host "[4/6] Starting all backend services..." -ForegroundColor Yellow
docker compose -f docker-compose.prod.yml up -d `
    gateway `
    auth-service `
    cv-service `
    jd-service `
    analysis-service `
    recommender-service `
    admin-service

Write-Host "Waiting for services to start..."
Start-Sleep -Seconds 20
Write-Host "✅ All services started" -ForegroundColor Green
Write-Host ""

# Step 5: Start all workers
Write-Host "[5/6] Starting all workers..." -ForegroundColor Yellow
docker compose -f docker-compose.prod.yml up -d `
    worker-cv-parser `
    worker-analysis `
    worker-market-stats `
    worker-email `
    celery-beat

Write-Host "Waiting for workers to connect..."
Start-Sleep -Seconds 10
Write-Host "✅ All workers started" -ForegroundColor Green
Write-Host ""

# Step 6: Health checks and status
Write-Host "[6/6] Running health checks..." -ForegroundColor Yellow

function Test-ServiceHealth {
    param(
        [string]$ServiceName,
        [string]$Url
    )
    
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ $ServiceName is healthy" -ForegroundColor Green
            return $true
        }
    } catch {
        Write-Host "❌ $ServiceName health check failed" -ForegroundColor Red
        return $false
    }
}

# Check services
Test-ServiceHealth "Gateway" "http://localhost:8000/health"
Test-ServiceHealth "Auth Service" "http://localhost:8000/auth/health"
Test-ServiceHealth "CV Service" "http://localhost:8000/cv/health"
Test-ServiceHealth "JD Service" "http://localhost:8000/jd/health"
Test-ServiceHealth "Analysis Service" "http://localhost:8000/analysis/health"

Write-Host ""
Write-Host "========================================" -ForegroundColor Blue
Write-Host "  Deployment Summary" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

# Show all containers status
Write-Host "📦 Container Status:" -ForegroundColor Green
docker compose -f docker-compose.prod.yml ps

Write-Host ""
Write-Host "🎉 Deployment completed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Check logs: docker compose -f docker-compose.prod.yml logs -f"
Write-Host "  2. Monitor workers: docker logs -f advisor_worker_cv_parser_prod"
Write-Host "  3. Test API: curl http://localhost:8000/health"
Write-Host ""
