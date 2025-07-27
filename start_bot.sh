#!/bin/bash
set -e

cd "$(dirname "$0")"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🧠 Elite Alpha Mirror Bot${NC}"
echo -e "${BLUE}💰 Target: \$1K → \$1M through smart money mirroring${NC}"
echo ""

# Check virtual environment
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Virtual environment not found. Run ./master_setup.sh first${NC}"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Load configuration
if [ -f config.env ]; then
    export $(cat config.env | grep -v '^#' | xargs)
fi

# Check for API keys
if [[ "$ETH_HTTP_URL" == *"YOUR_"* ]] || [ -z "$ETH_HTTP_URL" ]; then
    echo -e "${RED}⚠️  Please update config.env with your API keys first${NC}"
    echo ""
    echo "Required API keys:"
    echo "- ETH_HTTP_URL (Alchemy or Infura)"
    echo "- ETHERSCAN_API_KEY"
    echo "- OKX API credentials (optional for live trading)"
    echo "- DISCORD_WEBHOOK (optional for notifications)"
    echo ""
    read -p "Continue anyway with demo mode? (y/N): " continue_demo
    if [[ ! $continue_demo =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}🚀 Starting Enhanced Paper Trading Engine...${NC}"
python scripts/enhanced_paper_trading.py
