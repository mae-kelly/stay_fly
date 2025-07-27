#!/bin/bash

echo "🔧 Installing ML Dependencies for Mac M1..."

pip install --upgrade pip setuptools wheel

echo "🧠 Installing PyTorch with Metal Performance Shaders (M1 GPU)..."
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cpu

echo "📊 Installing ML packages..."
pip install numpy pandas scikit-learn matplotlib seaborn

echo "🌐 Installing networking packages..."
pip install aiohttp websockets requests

echo "🔧 Installing utilities..."
pip install python-dotenv asyncio

echo "🦀 Building Rust components..."
cd rust 2>/dev/null && cargo build --release && cd .. || echo "Rust build skipped"

echo "✅ ML dependencies installed!"
