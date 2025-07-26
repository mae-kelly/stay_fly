#!/bin/bash
echo "🧪 Testing Full System with Real API Keys"
echo ""

source venv/bin/activate

echo "1. 🔍 Test Elite Wallet Discovery"
echo "2. 📊 Test Paper Trading Engine"
echo "3. 📱 Test Discord Notifications"
echo "4. 🚀 Run Full System"
echo ""
read -p "Select test (1-4): " choice

case $choice in
    1)
        echo "🔍 Testing elite wallet discovery with real APIs..."
        python discover_real_whales.py
        ;;
    2)
        echo "📊 Testing enhanced paper trading engine..."
        python enhanced_paper_trading.py
        ;;
    3)
        echo "📱 Testing Discord notifications..."
        python discord_notifications.py
        ;;
    4)
        echo "🚀 Running full system with all real APIs!"
        echo "   • Real Ethereum data via Alchemy"
        echo "   • Real whale discovery via Etherscan"
        echo "   • Real token prices via DexScreener"
        echo "   • Discord notifications enabled"
        echo ""
        echo "Press Ctrl+C to stop..."
        python enhanced_paper_trading.py
        ;;
    *)
        echo "❌ Invalid option"
        ;;
esac
