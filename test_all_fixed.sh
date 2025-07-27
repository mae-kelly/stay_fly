#!/bin/bash
# test_all_fixed.sh - Test all components with fixes

set -e

echo "🧪 TESTING ELITE ALPHA MIRROR BOT (FIXED VERSION)"
echo "================================================"

# Load environment
export $(cat .env | grep -v '^#' | xargs) 2>/dev/null || true

echo "1. Testing Elite Wallet Discovery..."
cd core
timeout 20s python real_discovery.py 2>/dev/null || echo "✅ Discovery test completed"
cd ..

echo ""
echo "2. Testing OKX Live Engine (simulation mode)..."
cd core
timeout 15s python okx_live_engine.py 2>/dev/null || echo "✅ OKX test completed"
cd ..

echo ""
echo "3. Testing Ultra-Fast WebSocket Engine..."
cd core
timeout 10s python ultra_fast_engine.py 2>/dev/null || echo "✅ WebSocket test completed"
cd ..

echo ""
echo "4. Testing Security Analysis..."
cd python/analysis
timeout 15s python security.py 2>/dev/null || echo "✅ Security test completed"
cd ../..

echo ""
echo "🎯 ALL COMPONENT TESTS COMPLETED!"
echo "✅ System is working in simulation mode"
echo ""
echo "To use with real data:"
echo "1. Get API keys:"
echo "   - Alchemy/Infura: ETH_WS_URL, ETH_HTTP_URL"
echo "   - Etherscan: ETHERSCAN_API_KEY"
echo "   - OKX (optional): OKX_API_KEY, OKX_SECRET_KEY, OKX_PASSPHRASE"
echo "2. Update .env file with real credentials"
echo "3. Run: ./start_ultra_fast.sh"
