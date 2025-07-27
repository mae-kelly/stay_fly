#!/bin/bash
# Firewall Setup for Production

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}⚠️  Setting up production firewall rules...${NC}"

# Check if ufw is available
if ! command -v ufw &> /dev/null; then
    echo -e "${RED}❌ ufw not found. Installing...${NC}"
    apt-get update && apt-get install -y ufw
fi

# Reset firewall to defaults
echo "Resetting firewall to defaults..."
ufw --force reset

# Set default policies
ufw default deny incoming
ufw default allow outgoing

# Allow SSH (customize port as needed)
SSH_PORT=${SSH_PORT:-22}
ufw allow "$SSH_PORT"/tcp comment "SSH"

# Allow HTTP and HTTPS for web interface
ufw allow 80/tcp comment "HTTP"
ufw allow 443/tcp comment "HTTPS"

# Allow application ports (restrict to specific IPs in production)
ufw allow from 127.0.0.1 to any port 8080 comment "Bot Health Check"
ufw allow from 127.0.0.1 to any port 8081 comment "Bot Metrics"
ufw allow from 127.0.0.1 to any port 3000 comment "Grafana"
ufw allow from 127.0.0.1 to any port 9090 comment "Prometheus"

# Allow Docker network communication
ufw allow from 172.16.0.0/12 comment "Docker networks"

# Database ports (restrict to application only)
ufw allow from 127.0.0.1 to any port 5432 comment "PostgreSQL local"
ufw allow from 127.0.0.1 to any port 6379 comment "Redis local"

# Rate limiting for SSH
ufw limit ssh comment "SSH rate limiting"

# Enable firewall
echo "Enabling firewall..."
ufw --force enable

# Show status
echo -e "${GREEN}✅ Firewall configured successfully${NC}"
ufw status verbose

echo ""
echo -e "${YELLOW}📋 Firewall Rules Summary:${NC}"
echo "• SSH: Port $SSH_PORT (rate limited)"
echo "• HTTP/HTTPS: Ports 80, 443"
echo "• Application ports: 8080, 8081 (localhost only)"
echo "• Monitoring: 3000, 9090 (localhost only)"
echo "• Database: 5432, 6379 (localhost only)"
echo "• Docker networks: 172.16.0.0/12"
echo ""
echo -e "${YELLOW}⚠️  Important:${NC}"
echo "• Customize SSH port and allowed IPs for production"
echo "• Consider VPN access for remote management"
echo "• Monitor firewall logs: sudo ufw status verbose"
