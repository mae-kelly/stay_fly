#!/bin/bash
echo "📊 Paper Trading Engine - Real Whale Signals"
echo "💰 Trade with virtual money based on actual whale activity"
echo ""

source venv/bin/activate

echo "Choose option:"
echo "1. 🚀 Start Paper Trading (Monitor live whale trades)"
echo "2. 📊 View Current Portfolio"
echo "3. 📈 Manual Paper Trade (for testing)"
echo ""
read -p "Select option (1-3): " choice

case $choice in
    1)
        echo "🚀 Starting paper trading engine..."
        echo "💡 This will monitor real whale wallets and execute virtual trades"
        echo "⚠️  Press Ctrl+C to stop and save session"
        python paper_trading_engine.py
        ;;
    2)
        echo "📊 Current paper trading portfolio:"
        python view_portfolio.py
        ;;
    3)
        echo "📈 Manual paper trade (for testing):"
        python -c "
import asyncio
from paper_trading_engine import PaperTradingEngine

async def manual_trade():
    engine = PaperTradingEngine(1000.0)
    async with engine:
        # Simulate a whale buy
        await engine.execute_paper_buy(
            '0xa0b86a33e6441b24b4b2cccdca5e5f7c9ef3bd20',
            '0xae2fc483527b8ef99eb5d9b44875f005ba1fae13',
            'Manual test trade',
            30.0
        )
        engine.save_trading_session()

asyncio.run(manual_trade())
"
        ;;
    *)
        echo "❌ Invalid option"
        ;;
esac
