#!/bin/bash
echo "🚀 Elite Alpha Mirror Bot - Quick Start"
echo ""

# Check if data exists
if [ ! -f "data/alpha_wallets.json" ]; then
    echo "📁 Creating sample elite wallets..."
    mkdir -p data
    cat > data/alpha_wallets.json << 'WALLETEOF'
[
  {
    "address": "0xae2fc483527b8ef99eb5d9b44875f005ba1fae13",
    "avg_multiplier": 150.5,
    "win_rate": 0.85,
    "last_active": 1735197600,
    "deploy_count": 12,
    "snipe_success": 8,
    "risk_score": 15.2
  },
  {
    "address": "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b",
    "avg_multiplier": 89.3,
    "win_rate": 0.72,
    "last_active": 1735197300,
    "deploy_count": 6,
    "snipe_success": 15,
    "risk_score": 22.1
  }
]
WALLETEOF
fi

echo "🔍 1. Demo Mode - See the bot in action"
echo "🚀 2. Live Mode - Start real monitoring"
echo "⚙️  3. Check Configuration"
echo ""
read -p "Select option (1-3): " choice

case $choice in
    1)
        echo "🎮 Starting Demo Mode..."
        python3 -c "
import json
import time
import random

print('🧠 Elite Alpha Mirror Bot Demo')
print('💰 Simulating \$1K → \$1M journey...')
print('')

with open('data/alpha_wallets.json', 'r') as f:
    wallets = json.load(f)

capital = 1000
for i in range(3):
    wallet = random.choice(wallets)
    multiplier = random.uniform(2.0, 12.0)
    
    print(f'🔍 Elite wallet: {wallet[\"address\"][:10]}... (avg: {wallet[\"avg_multiplier\"]:.1f}x)')
    print(f'⚡ Mirroring their trade...')
    time.sleep(1)
    
    old_capital = capital
    capital *= multiplier
    
    print(f'✅ \${old_capital:,.0f} → \${capital:,.0f} ({multiplier:.1f}x)')
    print('')
    time.sleep(2)

print(f'📊 Demo Result: \${capital:,.2f}')
print('💡 This shows how the bot mirrors elite wallet trades!')
"
        ;;
    2)
        echo "🚀 Starting Live Monitoring..."
        echo "⚡ Rust engine will monitor for alpha wallet activity"
        ./rust/target/release/alpha-mirror
        ;;
    3)
        echo "⚙️ Configuration Status:"
        if [ -f "config.env" ]; then
            source config.env
            echo "📝 Config file found"
            if [[ "$ETH_HTTP_URL" == *"YOUR_ALCHEMY_KEY"* ]]; then
                echo "❌ Update ETH_HTTP_URL with real Alchemy key"
            else
                echo "✅ Ethereum endpoint configured"
            fi
        else
            echo "❌ No config.env found"
        fi
        ;;
    *)
        echo "❌ Invalid option"
        ;;
esac
