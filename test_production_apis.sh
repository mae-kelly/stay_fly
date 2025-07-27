#!/bin/bash
# test_production_apis.sh - Test real API connections

set -e

echo "🔍 Testing Production API Connections"
echo "===================================="

export $(cat .env | grep -v '^#' | xargs)

echo "1. Testing Alchemy connection..."
curl -s -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
  "$ETH_HTTP_URL" | jq '.result' || echo "❌ Alchemy test failed"

echo ""
echo "2. Testing Etherscan API..."
curl -s "https://api.etherscan.io/api?module=stats&action=ethsupply&apikey=$ETHERSCAN_API_KEY" | jq '.status' || echo "❌ Etherscan test failed"

echo ""
echo "3. Testing Discord webhook..."
curl -s -X POST \
  -H "Content-Type: application/json" \
  -d '{"content": "🧪 Elite Alpha Mirror Bot API test"}' \
  "$DISCORD_WEBHOOK" || echo "❌ Discord test failed"

echo ""
echo "✅ API connection tests completed"
echo ""
echo "⚠️  NOTE: OKX API requires passphrase to test"
