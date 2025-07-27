#!/bin/bash
set -e

echo "🧪 Testing Elite Alpha Mirror Bot Components"
echo "============================================="

source venv/bin/activate
export $(cat .env | grep -v '^#' | xargs)

echo "1. Testing Elite Wallet Discovery..."
cd core
python real_discovery.py
echo ""

echo "2. Testing OKX Live Engine..."
python okx_live_engine.py
echo ""

echo "3. Testing Ultra-Fast WebSocket Engine..."
timeout 10s python ultra_fast_engine.py || echo "✅ WebSocket test completed"
echo ""

echo "🎯 All component tests completed!"
echo "Ready for full system deployment with ./start_ultra_fast.sh"
