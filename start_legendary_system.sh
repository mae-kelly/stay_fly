#!/bin/bash
set -euo pipefail

echo "🏆 STARTING LEGENDARY TRADING SYSTEM"
echo "====================================="

if [ ! -f ".production_ready" ]; then
    echo "🔧 Converting to production..."
    ./convert_to_production.sh
    touch .production_ready
fi

echo "🧠 Executing 10-minute ML warmup..."
python3 warmup_coordinator.py

if [ $? -eq 0 ]; then
    echo "🚀 WARMUP COMPLETE - STARTING LIVE TRADING"
    
    export PAPER_TRADING_MODE=false
    export LIVE_TRADING=true
    export WEBHOOK_MODE=true
    export EXECUTION_SPEED=ULTRA
    
    uvicorn core.webhook_engine:app --host 0.0.0.0 --port 8000 &
    WEBHOOK_PID=$!
    
    python3 core/live_discovery.py &
    DISCOVERY_PID=$!
    
    python3 core/live_websocket.py &
    WEBSOCKET_PID=$!
    
    python3 main.py &
    MAIN_PID=$!
    
    echo "✅ ALL SYSTEMS OPERATIONAL"
    echo "📡 Webhook server: http://localhost:8000"
    echo "🧠 ML warmup active"
    echo "⚡ Ultra-fast execution enabled"
    echo "🎯 Zero simulation mode"
    echo ""
    echo "🏆 LEGENDARY SYSTEM IS LIVE"
    echo "📈 MAKING TRADING HISTORY NOW"
    
    trap "kill $WEBHOOK_PID $DISCOVERY_PID $WEBSOCKET_PID $MAIN_PID 2>/dev/null || true" EXIT
    
    wait
else
    echo "❌ WARMUP FAILED - ABORTING STARTUP"
    exit 1
fi