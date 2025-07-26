#!/bin/bash
echo "🐋 REAL Elite Alpha Mirror Bot"
echo "💰 Connecting to live blockchain data..."
echo ""

source venv/bin/activate

echo "Choose mode:"
echo "1. 🔍 Discover Real Elite Wallets (from recent moonshots)"
echo "2. 👀 Monitor Elite Wallets in Real-Time"
echo "3. 📊 Show Current Elite Wallet List"
echo ""
read -p "Select option (1-3): " choice

case $choice in
    1)
        echo "🔍 Starting real elite wallet discovery..."
        echo "⚠️  Note: You need a real Etherscan API key for full functionality"
        python discover_real_whales.py
        ;;
    2)
        echo "👀 Starting real-time monitoring..."
        echo "⚠️  Note: You need a real Ethereum RPC endpoint for live data"
        python monitor_real_trades.py
        ;;
    3)
        if [ -f "data/real_elite_wallets.json" ]; then
            echo "📊 Current Elite Wallets:"
            python -c "
import json
with open('data/real_elite_wallets.json', 'r') as f:
    wallets = json.load(f)
    
for i, wallet in enumerate(wallets[:10], 1):
    print(f'{i:2d}. {wallet[\"address\"][:10]}... - {wallet[\"type\"]} - {wallet.get(\"performance\", 0):.0f}% gain')
    
print(f'\\nTotal: {len(wallets)} elite wallets')
"
        else
            echo "❌ No elite wallets found. Run discovery first."
        fi
        ;;
    *)
        echo "❌ Invalid option"
        ;;
esac
