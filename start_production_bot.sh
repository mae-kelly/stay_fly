#!/bin/bash
echo "🚀 Starting Elite Mirror Bot - Production Mode"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Run ./production_setup.sh first to create configuration"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Set production environment
export ENVIRONMENT=production
export PYTHONPATH=$(pwd):$PYTHONPATH

# Start the bot
echo "🤖 Starting Elite Mirror Bot..."
echo "💰 Target: $1K → $1M via elite wallet mirroring"
echo "🔐 Using secure credential management"
echo ""

python elite_mirror_bot.py
