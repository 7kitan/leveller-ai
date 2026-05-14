@echo off
echo ========================================
echo   Running Database Migrations (Windows)
echo ========================================

set DOCKER_COMPOSE_FILE=docker-compose.prod.yml

:: Check if DB is running
docker compose -f %DOCKER_COMPOSE_FILE% ps db | findstr "Up" >nul
if %errorlevel% neq 0 (
    echo Starting database service...
    docker compose -f %DOCKER_COMPOSE_FILE% up -d db
    timeout /t 5
)

echo Executing migration files...

:: Loop through all .sql files in scripts/migrations
for %%f in (scripts/migrations/*.sql) do (
    echo Processing: %%f
    type scripts\migrations\%%f | docker compose -f %DOCKER_COMPOSE_FILE% exec -T db psql -U postgres -d career_advisor
)

echo.
echo Done! All migrations applied.
pause
