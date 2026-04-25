#!/bin/bash
set -e
echo "🚀 Setting up Backend..."
sudo apt-get update && sudo apt-get install -y docker.io docker-compose
if [ ! -f ".env" ]; then cp .env.example .env; fi
docker-compose -f docker-compose.prod.yml up -d --build
echo "✅ Backend is running."
