#!/bin/bash
# start_production_safe.sh - Start with maximum safety

set -e

echo "🚨 PRODUCTION MODE STARTUP"
echo "========================="

# Load environment
if [ ! -f .env ]; then
    echo "❌ No .env file found. Run setup_production_env.sh first"
    exit 1
fi

export $(cat .env | grep -v '^#' | xargs)

# Safety checks
echo "🔍 Safety Checks..."

if [ "$OKX_PASSPHRASE" = "REQUIRED_BUT_NOT_PROVIDED" ]; then
    echo "❌ OKX_PASSPHRASE not set in .env file"
    exit 1
fi

if [ "$WALLET_ADDRESS" = "YOUR_WALLET_ADDRESS_HERE" ]; then
    echo "❌ WALLET_ADDRESS not set in .env file"
    exit 1
fi

if [ "$PAPER_TRADING_MODE" != "true" ]; then
    echo "🚨 WARNING: Paper trading mode is OFF"
    echo "⚠️  This will execute REAL trades with REAL money"
    read -p "Continue with LIVE trading? (type 'LIVE TRADING'): " confirm
    if [ "$confirm" != "LIVE TRADING" ]; then
        echo "❌ Cancelled for safety"
        exit 1
    fi
fi

echo "✅ Safety checks passed"
echo ""
echo "💰 Starting Capital: $${STARTING_CAPITAL}"
echo "📊 Max Position Size: ${MAX_POSITION_SIZE}% of capital"
echo "🎯 Max Positions: ${MAX_POSITIONS}"
echo "🛡️  Paper Trading: ${PAPER_TRADING_MODE}"
echo ""

# Start the system
cd core
python master_coordinator.py
