#!/bin/bash
set -e

echo "🚀 Elite Alpha Mirror Bot - Production Deployment"
echo "=================================================="

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}❌ This script should not be run as root${NC}"
   exit 1
fi

# Pre-deployment checks
echo -e "${BLUE}🔍 Running pre-deployment checks...${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    exit 1
fi

# Check .env file
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env file not found${NC}"
    echo "Please create .env file with your API keys"
    exit 1
fi

# Validate API keys
if ! grep -q "OKX_API_KEY=" .env || grep -q "your_" .env; then
    echo -e "${YELLOW}⚠️  Warning: API keys may not be configured${NC}"
    read -p "Continue anyway? (y/N): " continue_deploy
    if [[ ! $continue_deploy =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}✅ Pre-deployment checks passed${NC}"

# Build and deploy
echo -e "${BLUE}🏗️  Building containers...${NC}"
docker-compose build --no-cache

echo -e "${BLUE}📦 Starting services...${NC}"
docker-compose up -d

# Wait for services to be ready
echo -e "${BLUE}⏳ Waiting for services to be ready...${NC}"
sleep 30

# Health check
echo -e "${BLUE}🩺 Running health checks...${NC}"
if curl -f http://localhost:8080/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Health check passed${NC}"
else
    echo -e "${RED}❌ Health check failed${NC}"
    echo "Checking logs..."
    docker-compose logs --tail=50 elite-bot
    exit 1
fi

# Show status
echo -e "${BLUE}📊 Deployment Status:${NC}"
docker-compose ps

echo -e "${GREEN}🎉 Production deployment completed successfully!${NC}"
echo ""
echo "📱 Monitoring:"
echo "  Health: http://localhost:8080/health"
echo "  Metrics: http://localhost:8080/metrics"
echo "  Prometheus: http://localhost:9090"
echo ""
echo "📋 Management commands:"
echo "  View logs: docker-compose logs -f elite-bot"
echo "  Stop: docker-compose down"
echo "  Restart: docker-compose restart elite-bot"
echo ""
echo "💰 The bot is now running and targeting $1K → $1M!"
