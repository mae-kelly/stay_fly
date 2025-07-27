#!/bin/bash

echo "🚀 Elite Alpha Mirror Bot - ML Enhanced Launch"
echo "============================================="

echo "🧹 Step 1: Cleaning disk space..."
./cleanup_disk_space.sh

echo "🔧 Step 2: Generating ML system..."
./generate_ml_system.sh

echo "📦 Step 3: Installing optimized dependencies..."
./install_ml_dependencies_optimized.sh

echo "⚙️ Step 4: Setting up configuration..."
if [ ! -f ".env" ]; then
    cp .env.production .env
    echo "📝 Created .env from template"
    echo "⚠️  EDIT .env WITH YOUR REAL API KEYS!"
fi

echo "🧠 Step 5: Pre-training ML model..."
python3 -c "
import asyncio
import sys
sys.path.append('.')
from python.ml.models.whale_predictor import WhaleMLEngine

async def quick_train():
    async with WhaleMLEngine() as engine:
        await engine.train_model(training_minutes=2)
        print('✅ Quick ML training complete!')

asyncio.run(quick_train())
"

echo ""
echo "🎯 SYSTEM READY FOR ML-ENHANCED TRADING!"
echo "========================================="
echo ""
echo "📋 Final Steps:"
echo "1. Edit .env with your real API keys"
echo "2. Set PAPER_TRADING_MODE=true for safety"
echo "3. Run: python3 main_ml_integration.py"
echo ""
echo "🧠 Features:"
echo "• 10-minute ML training on real whale data"
echo "• Grok AI validates every trade"
echo "• M1 GPU acceleration"
echo "• Real-time mempool monitoring"
echo "• Advanced risk management"
echo ""
echo "⚠️  START WITH PAPER TRADING MODE!"