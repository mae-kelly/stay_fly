# Elite Alpha Mirror Bot - OKX Setup Guide

## 🚀 Quick Start

```bash
# Make setup script executable
chmod +x quick_start_okx.sh

# Run the setup
./quick_start_okx.sh
```

## 📋 Step-by-Step Instructions

### 1. First Time Setup
```bash
# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install aiohttp web3 requests asyncio pandas numpy eth-account
```

### 2. Discover Elite Wallets
```bash
python discover_real_whales.py
```
This will:
- Scan DexScreener for recent 100x+ tokens
- Find deployer wallets using your Etherscan API
- Identify early buyer wallets (snipers)
- Save results to `data/real_elite_wallets.json`

### 3. Start OKX Paper Trading
```bash
python okx_focused_trading.py
```
This will:
- Load discovered elite wallets
- Monitor Ethereum blockchain using your Alchemy API
- Simulate trades through OKX when elite wallets trade
- Send notifications to your Discord webhook

## ⚠️ Important OKX Setup Notes

### For Paper Trading (Safe Mode):
- No real money at risk
- Uses your APIs to get real data
- Simulates OKX trades
- Perfect for testing the system

### For Live Trading:
You'll need to add to `config.env`:
```bash
WALLET_ADDRESS=your_okx_connected_wallet_address
PRIVATE_KEY=your_wallet_private_key
OKX_PASSPHRASE=your_okx_trading_passphrase
```

## 🎯 How It Works

1. **Elite Discovery:** Uses your Etherscan API to find wallets that deployed/bought 100x tokens
2. **Real-time Monitoring:** Uses your Alchemy WebSocket to watch these wallets
3. **OKX Execution:** Routes all trades through OKX DEX aggregator
4. **Safety Validation:** Validates tokens before mirroring trades
5. **Discord Alerts:** Sends real-time notifications to your webhook

## 📊 Expected Performance

**Target:** $1K → $1M through capital compounding

**Strategy:**
- Mirror elite wallet trades within seconds
- 30% position sizing per trade
- Auto-exit at 5x gains or stop-loss
- Compound profits into next opportunity

**Math:**
- Trade 1: $1K → $10K (10x)
- Trade 2: $10K → $100K (10x)  
- Trade 3: $100K → $1M (10x)

## 🔐 Security Features

- ✅ Contract verification checks
- ✅ Honeypot detection
- ✅ Ownership renunciation validation
- ✅ Liquidity analysis (min $50K)
- ✅ Maximum position limits (30%)
- ✅ Time-based exits (24h max)

## 📱 Discord Notifications

Your Discord webhook will receive:
- 🐋 Elite wallet activity alerts
- 📊 Trade execution confirmations
- 💰 P&L updates
- 🎯 Portfolio summaries
- 🚨 Risk management alerts

## 🚀 Quick Commands

```bash
# Discover elite wallets
python discover_real_whales.py

# Start paper trading
python okx_focused_trading.py

# Test Discord notifications
python -c "
import asyncio
import aiohttp
webhook = 'https://discord.com/api/webhooks/1398448251933298740/lSnT3iPsfvb87RWdN0XCd3AjdFsCZiTpF-_I1ciV3rB2BqTpIszS6U6tFxAVk5QmM2q3'
async def test():
    async with aiohttp.ClientSession() as session:
        await session.post(webhook, json={'content': '🧪 Elite Mirror Bot Test!'})
asyncio.run(test())
"
```

## 💡 Pro Tips

1. **Start with Paper Trading:** Test the system risk-free first
2. **Watch Discord:** Monitor all activity through notifications
3. **Check Elite Wallets:** Review `data/real_elite_wallets.json` for quality
4. **Monitor Performance:** Track results in `data/okx_trading_session.json`
5. **Scale Gradually:** Start small when moving to live trading

## 🎉 You're Ready!

Your bot is configured with:
- ✅ Real API keys for data feeds
- ✅ OKX integration for trading
- ✅ Elite wallet discovery system
- ✅ Risk management features
- ✅ Discord notifications

Run `./quick_start_okx.sh` and select option 1 to begin!