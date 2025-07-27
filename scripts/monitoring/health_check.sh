#!/bin/bash
# Health Check Script for Production

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🏥 Elite Alpha Mirror Bot - Health Check"
echo "========================================="

# Check if bot is running
if curl -f -s http://localhost:8080/health > /dev/null; then
    echo -e "${GREEN}✅ Bot API: Healthy${NC}"
else
    echo -e "${RED}❌ Bot API: Down${NC}"
    exit 1
fi

# Check Redis
if redis-cli -a "${REDIS_PASSWORD}" ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis: Connected${NC}"
else
    echo -e "${RED}❌ Redis: Connection failed${NC}"
fi

# Check PostgreSQL
if pg_isready -h localhost -p 5432 -U elite_bot > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PostgreSQL: Connected${NC}"
else
    echo -e "${RED}❌ PostgreSQL: Connection failed${NC}"
fi

# Check disk space
DISK_USAGE=$(df / | awk 'NR==2{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 80 ]; then
    echo -e "${GREEN}✅ Disk Usage: ${DISK_USAGE}%${NC}"
else
    echo -e "${YELLOW}⚠️ Disk Usage: ${DISK_USAGE}%${NC}"
fi

# Check memory usage
MEMORY_USAGE=$(free | awk 'FNR==2{printf "%.0f", $3/($3+$4)*100}')
if [ "$MEMORY_USAGE" -lt 85 ]; then
    echo -e "${GREEN}✅ Memory Usage: ${MEMORY_USAGE}%${NC}"
else
    echo -e "${YELLOW}⚠️ Memory Usage: ${MEMORY_USAGE}%${NC}"
fi

# Check log errors
ERROR_COUNT=$(tail -n 100 logs/production/bot.log | grep -c "ERROR" || echo "0")
if [ "$ERROR_COUNT" -lt 5 ]; then
    echo -e "${GREEN}✅ Recent Errors: ${ERROR_COUNT}${NC}"
else
    echo -e "${YELLOW}⚠️ Recent Errors: ${ERROR_COUNT}${NC}"
fi

echo "========================================="
echo "Health check completed"
