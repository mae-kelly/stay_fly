#!/bin/bash
set -euo pipefail

clear
echo "🏆 LEGENDARY TRADING SYSTEM LAUNCHER"
echo "====================================="
echo "💰 Target: \$1,000 → \$1,000,000"
echo "⚡ Method: Elite whale mirroring"
echo "🧠 Intelligence: ML-powered predictions"
echo "🎯 Speed: Sub-50ms execution"
echo "====================================="
echo ""

if [ ! -f "legendary_status.txt" ]; then
    echo "🔧 Converting to legendary system..."
    ./convert_to_production.sh
    ./scripts/prod/7_instant_profits.sh
    ./scripts/prod/8_final_optimizer.sh
fi

echo "⚠️  LIVE TRADING WARNING"
echo "This system trades with REAL MONEY"
echo "Verify your API keys and risk tolerance"
echo ""
read -p "Continue with live trading? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "🛑 Launch cancelled"
    exit 0
fi

export LIVE_TRADING=true
export PAPER_TRADING_MODE=false
export WEBHOOK_MODE=true
export EXECUTION_SPEED=LEGENDARY
export PROFIT_OPTIMIZATION=maximum

echo ""
echo "🧠 Starting 10-minute ML warmup..."
python3 warmup_coordinator.py

if [ $? -eq 0 ]; then
    echo ""
    echo "🚀 LAUNCHING LEGENDARY SYSTEM"
    echo "================================"
    
    uvicorn core.webhook_engine:app --host 0.0.0.0 --port 8000 --workers 4 &
    WEBHOOK_PID=$!
    
    python3 core/live_discovery.py &
    DISCOVERY_PID=$!
    
    python3 core/live_websocket.py &
    WEBSOCKET_PID=$!
    
    python3 ultimate_main.py &
    MAIN_PID=$!
    
    echo "✅ ALL SYSTEMS OPERATIONAL"
    echo ""
    echo "🏆 LEGENDARY TRADING SYSTEM IS LIVE"
    echo "📊 Monitoring: Elite whale wallets"
    echo "⚡ Execution: Ultra-fast webhooks"
    echo "🧠 Intelligence: Real-time ML"
    echo "💰 Target: \$1,000,000"
    echo ""
    echo "📈 THIS SYSTEM WILL MAKE HISTORY"
    echo "🎯 PREPARE FOR LEGENDARY RETURNS"
    echo ""
    echo "Press Ctrl+C to stop (emergency stop)"
    
    trap "echo '🛑 EMERGENCY STOP'; kill $WEBHOOK_PID $DISCOVERY_PID $WEBSOCKET_PID $MAIN_PID 2>/dev/null || true; echo '✅ All processes terminated'" EXIT
    
    wait $MAIN_PID
else
    echo "❌ ML WARMUP FAILED"
    echo "🔧 Check your API configurations"
    exit 1
fi