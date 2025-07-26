#!/bin/bash
set -eo pipefail

echo "🚀 Deploying Elite Alpha Mirror Bot..."

if ! command -v cargo &> /dev/null; then
    echo "Installing Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source ~/.cargo/env
fi

if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not installed."
    exit 1
fi

echo "🐍 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install aiohttp web3 eth-abi aiosqlite requests asyncio

echo "🔧 Compiling Rust components..."
cd rust
cargo build --release
cd ..

echo "📊 Setting up database..."
mkdir -p data
python -c "
import asyncio
import sys
import os
sys.path.append('python')
from analysis.wallet_tracker import EliteWalletTracker

async def setup():
    tracker = EliteWalletTracker('data/wallets.db')
    async with tracker:
        pass

asyncio.run(setup())
"

echo "🎯 Creating configuration..."
cat > config.env << 'ENVEOF'
ETH_HTTP_URL=https://eth-mainnet.alchemyapi.io/v2/YOUR_ALCHEMY_KEY
OKX_API_KEY=your_okx_api_key
OKX_SECRET_KEY=your_okx_secret_key
OKX_PASSPHRASE=your_okx_passphrase
ETHERSCAN_API_KEY=your_etherscan_api_key
ENVEOF

echo "✅ Deployment complete!"
echo "📝 Please update config.env with your API keys"
echo "🚀 Run: source venv/bin/activate && ./start.sh to begin alpha mirroring"
