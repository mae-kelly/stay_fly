#!/bin/bash
set -eo pipefail

if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run ./deploy.sh first"
    exit 1
fi

source venv/bin/activate

if [ -f .env ]; then
    export $(cat .env | xargs)
fi

echo "🧠 Starting Elite Alpha Mirror Bot..."
echo "💰 Target: \$1K → \$1M through smart money mirroring"

python core/orchestrator.py
