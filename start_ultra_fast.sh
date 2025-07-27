#!/bin/bash
set -e

echo "⚡ Starting Elite Alpha Mirror Bot - Ultra-Fast Mode"
echo "💰 Target: \$1K → \$1M via millisecond-precision trading"
echo ""

# Check configuration
if grep -q "YOUR_API_KEY" .env; then
    echo "⚠️  WARNING: Please update .env with your real API keys!"
    echo ""
    echo "Required APIs:"
    echo "- Alchemy/Infura WebSocket URL (ETH_WS_URL)"
    echo "- Etherscan API key (ETHERSCAN_API_KEY)" 
    echo "- OKX trading credentials (OKX_API_KEY, OKX_SECRET_KEY, OKX_PASSPHRASE)"
    echo ""
    read -p "Continue with demo mode? (y/N): " continue_demo
    if [[ ! $continue_demo =~ ^[Yy]$ ]]; then
        echo "Update .env file and run again"
        exit 1
    fi
    echo "🎮 Running in DEMO mode with simulated trading"
fi

# Activate environment
source venv/bin/activate

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Start the ultra-fast coordinator
echo "🧠 Starting Master Coordinator..."
echo "⚡ WebSocket monitoring active"
echo "💰 OKX execution engine ready"
echo ""

cd core
python master_coordinator.py
