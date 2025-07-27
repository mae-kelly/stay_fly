#!/bin/bash
# start_demo.sh - Start in safe demo mode

set -e

echo "🚀 ELITE ALPHA MIRROR BOT - DEMO MODE"
echo "====================================="
echo "💰 Demo: Simulated $1K → $1M system"
echo "🎮 Mode: Safe simulation (no real money)"
echo ""

# Load environment
export $(cat .env | grep -v '^#' | xargs) 2>/dev/null || true

echo "🧠 Starting Master Coordinator in demo mode..."
cd core
python master_coordinator.py
