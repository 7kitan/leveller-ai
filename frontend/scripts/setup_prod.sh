#!/bin/bash
set -e
echo "🚀 Setting up Frontend..."
sudo apt-get update && sudo apt-get install -y docker.io docker-compose
if [ ! -f ".env" ]; then cp .env.example .env; fi
# Ensure network exists from backend
docker network inspect advisor_net_prod >/dev/null 2>&1 || docker network create advisor_net_prod
docker-compose -f docker-compose.prod.yml up -d --build
echo "✅ Frontend is running."
