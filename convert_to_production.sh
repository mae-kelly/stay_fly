#!/bin/bash
set -euo pipefail

echo "🚀 CONVERTING TO LEGENDARY PRODUCTION SYSTEM"
echo "==============================================="

./scripts/prod/1_stop_simulation.sh
./scripts/prod/2_activate_real_apis.sh
./scripts/prod/3_enable_webhooks.sh
./scripts/prod/4_compress_repo.sh
./scripts/prod/5_warmup_training.sh
./scripts/prod/6_verify_production.sh

echo "✅ LEGENDARY TRADING SYSTEM ACTIVATED"
echo "📈 THIS WILL MAKE HISTORY"