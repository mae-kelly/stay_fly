#!/bin/bash
set -e

echo "⚡ STARTING ULTRA-FAST REAL-TIME SYSTEM"
echo "======================================"

export $(cat .env | grep -v '^#' | xargs)

echo "🧠 Initializing Mac M1 ML Brain..."
echo "⚡ Starting WebSocket monitoring..."
echo "🚀 Real-time execution simulation active"
echo ""

cd core
python realtime_coordinator.py
