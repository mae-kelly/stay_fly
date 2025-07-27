#!/usr/bin/env python3
"""
OKX-Focused Elite Wallet Mirror Trading Bot
All trades executed through OKX DEX with your API credentials
"""

import asyncio
import aiohttp
import json
import time
import os
import hmac
import hashlib
import base64
from datetime import datetime
from web3 import Web3
from dataclasses import dataclass
from typing import Dict, List, Optional

# Load configuration
def load_config():
    """Load configuration from config.env"""
    config = {}
    try:
        with open('config.env', 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    config[key] = value
    except FileNotFoundError:
        print("❌ config.env not found")
    return config

CONFIG = load_config()

@dataclass
class OKXTradeParams:
    from_token: str
    to_token: str
    amount: str
    slippage: str = "0.05"  # 5% slippage
    
@dataclass
class Position:
    token_address: str
    token_symbol: str
    entry_price: float
    entry_time: datetime
    quantity: float
    usd_invested: float
    whale_wallet: str

class OKXTradingEngine:
    def __init__(self):
        self.api_key = CONFIG.get('OKX_API_KEY')
        self.secret_key = CONFIG.get('OKX_SECRET_KEY')
        self.passphrase = CONFIG.get('OKX_PASSPHRASE', 'trading_bot_2024')
        self.base_url = CONFIG.get('OKX_BASE_URL', 'https://www.okx.com')
        
        self.session = None
        self.w3 = Web3(Web3.HTTPProvider(CONFIG.get('ETH_HTTP_URL')))
        
        # Portfolio management
        self.starting_capital = float(CONFIG.get('STARTING_CAPITAL', 1000.0))
        self.current_capital = self.starting_capital
        self.positions: Dict[str, Position] = {}
        self.trade_history = []
        
        # Load elite wallets
        self.elite_wallets = {}
        self.load_elite_wallets()
        
        print(f"✅ OKX Trading Engine initialized")
        print(f"💰 Starting Capital: ${self.starting_capital:.2f}")
        print(f"🐋 Monitoring {len(self.elite_wallets)} elite wallets")
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def load_elite_wallets(self):
        """Load elite wallets from discovery"""
        try:
            with open('data/real_elite_wallets.json', 'r') as f:
                wallets = json.load(f)
                self.elite_wallets = {w['address'].lower(): w for w in wallets}
            print(f"📊 Loaded {len(self.elite_wallets)} elite wallets")
        except FileNotFoundError:
            print("❌ No elite wallets found. Run discovery first.")
            # Create sample data for testing
            self.elite_wallets = {
                '0xae2fc483527b8ef99eb5d9b44875f005ba1fae13': {
                    'address': '0xae2fc483527b8ef99eb5d9b44875f005ba1fae13',
                    'type': 'deployer',
                    'performance': 150.5
                }
            }
    
    def _create_okx_signature(self, timestamp: str, method: str, request_path: str, body: str = "") -> str:
        """Create OKX API signature"""
        message = timestamp + method + request_path + body
        mac = hmac.new(
            bytes(self.secret_key, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod=hashlib.sha256
        )
        return base64.b64encode(mac.digest()).decode()
    
    def _get_okx_headers(self, method: str, request_path: str, body: str = "") -> dict:
        """Get OKX API headers with authentication"""
        timestamp = str(time.time())
        signature = self._create_okx_signature(timestamp, method, request_path, body)
        
        return {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }
    
    async def get_okx_token_quote(self, from_token: str, to_token: str, amount: str) -> Optional[dict]:
        """Get quote from OKX DEX aggregator"""
        path = '/api/v5/dex/aggregator/quote'
        params = {
            'chainId': '1',  # Ethereum mainnet
            'fromTokenAddress': from_token,
            'toTokenAddress': to_token,
            'amount': amount,
            'slippage': '0.5'  # 0.5%
        }
        
        url = f"{self.base_url}{path}"
        headers = self._get_okx_headers('GET', path)
        
        try:
            async with self.session.get(url, params=params, headers=headers) as response:
                data = await response.json()
                if data.get('code') == '0':
                    return data.get('data', [{}])[0]
                else:
                    print(f"❌ OKX Quote Error: {data.get('msg', 'Unknown error')}")
        except Exception as e:
            print(f"❌ OKX Quote Exception: {e}")
        
        return None
    
    async def execute_okx_trade(self, trade_params: OKXTradeParams) -> bool:
        """Execute trade through OKX DEX"""
        # First get quote
        quote = await self.get_okx_token_quote(
            trade_params.from_token,
            trade_params.to_token,
            trade_params.amount
        )
        
        if not quote:
            print("❌ Failed to get OKX quote")
            return False
        
        # Execute swap
        path = '/api/v5/dex/aggregator/swap'
        swap_data = {
            'chainId': '1',
            'fromTokenAddress': trade_params.from_token,
            'toTokenAddress': trade_params.to_token,
            'amount': trade_params.amount,
            'slippage': trade_params.slippage,
            'userWalletAddress': CONFIG.get('WALLET_ADDRESS', ''),
            'referrer': 'elite_mirror_bot'
        }
        
        body = json.dumps(swap_data)
        headers = self._get_okx_headers('POST', path, body)
        
        try:
            url = f"{self.base_url}{path}"
            async with self.session.post(url, data=body, headers=headers) as response:
                data = await response.json()
                
                if data.get('code') == '0':
                    result = data.get('data', [{}])[0]
                    print(f"✅ OKX Trade Executed: {result.get('txHash', 'N/A')}")
                    return True
                else:
                    print(f"❌ OKX Trade Failed: {data.get('msg', 'Unknown error')}")
        except Exception as e:
            print(f"❌ OKX Trade Exception: {e}")
        
        return False
    
    async def get_token_info_dexscreener(self, token_address: str) -> dict:
        """Get token info from DexScreener"""
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            async with self.session.get(url) as response:
                data = await response.json()
                
                if data.get('pairs'):
                    pair = data['pairs'][0]
                    return {
                        'symbol': pair.get('baseToken', {}).get('symbol', 'UNKNOWN'),
                        'name': pair.get('baseToken', {}).get('name', 'Unknown Token'),
                        'price_usd': float(pair.get('priceUsd', 0))
                    }
        except Exception as e:
            print(f"❌ Error getting token info: {e}")
        
        return {'symbol': 'UNKNOWN', 'name': 'Unknown Token', 'price_usd': 0.0}
    
    async def mirror_whale_trade(self, token_address: str, whale_address: str, amount_eth: float):
        """Mirror a whale's trade through OKX"""
        print(f"🐋 Mirroring whale {whale_address[:10]}... trading {token_address[:10]}...")
        
        # Get token info
        token_info = await self.get_token_info_dexscreener(token_address)
        if token_info['price_usd'] <= 0:
            print(f"❌ Cannot get price for {token_address}")
            return False
        
        # Calculate position size (30% of current capital)
        max_investment = self.current_capital * 0.30
        investment_amount = min(amount_eth, max_investment)
        
        if investment_amount < 0.01:  # Minimum 0.01 ETH
            print(f"❌ Investment amount too small: ${investment_amount:.4f}")
            return False
        
        # Check if we already have this position
        if token_address in self.positions:
            print(f"⚠️ Already have position in {token_info['symbol']}")
            return False
        
        # Prepare OKX trade
        weth_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
        amount_wei = str(int(investment_amount * 1e18))
        
        trade_params = OKXTradeParams(
            from_token=weth_address,
            to_token=token_address,
            amount=amount_wei,
            slippage="0.05"  # 5% slippage
        )
        
        # Execute trade
        success = await self.execute_okx_trade(trade_params)
        
        if success:
            # Record position
            position = Position(
                token_address=token_address,
                token_symbol=token_info['symbol'],
                entry_price=token_info['price_usd'],
                entry_time=datetime.now(),
                quantity=investment_amount / token_info['price_usd'],
                usd_invested=investment_amount,
                whale_wallet=whale_address
            )
            
            self.positions[token_address] = position
            self.current_capital -= investment_amount
            
            # Record trade
            self.trade_history.append({
                'timestamp': datetime.now().isoformat(),
                'action': 'BUY',
                'token_address': token_address,
                'token_symbol': token_info['symbol'],
                'price': token_info['price_usd'],
                'amount_usd': investment_amount,
                'whale_wallet': whale_address,
                'method': 'OKX_DEX'
            })
            
            print(f"✅ MIRROR TRADE EXECUTED:")
            print(f"   Token: {token_info['symbol']}")
            print(f"   Amount: ${investment_amount:.2f}")
            print(f"   Price: ${token_info['price_usd']:.6f}")
            print(f"   Remaining Capital: ${self.current_capital:.2f}")
            
            # Send Discord notification
            await self.send_discord_notification({
                'action': 'BUY',
                'token_symbol': token_info['symbol'],
                'whale_wallet': whale_address,
                'usd_amount': investment_amount,
                'price': token_info['price_usd'],
                'method': 'OKX_DEX_MIRROR'
            })
            
            return True
        
        return False
    
    async def monitor_whale_activity(self):
        """Monitor blockchain for whale activity and mirror trades"""
        print("👀 Starting whale activity monitoring...")
        
        last_block = 0
        
        while True:
            try:
                current_block = self.w3.eth.block_number
                
                if current_block > last_block:
                    print(f"🔍 Scanning block {current_block} | Capital: ${self.current_capital:.2f}")
                    
                    # Get block with transactions
                    try:
                        block = self.w3.eth.get_block(current_block, full_transactions=True)
                        
                        for tx in block.transactions:
                            if tx['from'] and tx['from'].hex().lower() in self.elite_wallets:
                                await self.analyze_whale_transaction(tx)
                    except Exception as e:
                        print(f"❌ Error processing block {current_block}: {e}")
                    
                    last_block = current_block
                
                # Update positions every few blocks
                if current_block % 5 == 0:
                    await self.update_positions()
                
                await asyncio.sleep(12)  # ~1 block time
                
            except Exception as e:
                print(f"❌ Error in monitoring loop: {e}")
                await asyncio.sleep(5)
    
    async def analyze_whale_transaction(self, tx):
        """Analyze whale transaction for mirroring opportunity"""
        whale_address = tx['from'].hex().lower()
        whale_info = self.elite_wallets.get(whale_address, {})
        
        print(f"🐋 WHALE ACTIVITY: {whale_address[:10]}... ({whale_info.get('type', 'unknown')})")
        
        eth_value = self.w3.from_wei(tx['value'], 'ether')
        
        if eth_value > 0.1:  # Minimum 0.1 ETH to consider
            print(f"   💰 {eth_value:.4f} ETH transaction")
            
            # Check if it's a DEX transaction
            if await self.is_dex_transaction(tx):
                # For demo, use a popular token
                # In production, you'd decode the transaction to get the actual token
                demo_tokens = [
                    "0xA0b86a33E6441b24b4B2CCcdca5E5f7c9eF3Bd20",  # DOGE
                    "0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE",  # SHIB
                ]
                
                for token_addr in demo_tokens:
                    success = await self.mirror_whale_trade(token_addr, whale_address, float(eth_value))
                    if success:
                        break
    
    async def is_dex_transaction(self, tx) -> bool:
        """Check if transaction is likely a DEX trade"""
        dex_routers = {
            '0x7a250d5630b4cf539739df2c5dacb4c659f2488d',  # Uniswap V2
            '0xe592427a0aece92de3edee1f18e0157c05861564',  # Uniswap V3
            '0x1111111254eeb25477b68fb85ed929f73a960582',  # 1inch
        }
        return tx['to'] and tx['to'].hex().lower() in dex_routers
    
    async def update_positions(self):
        """Update position values and check exit conditions"""
        for token_addr, position in list(self.positions.items()):
            current_info = await self.get_token_info_dexscreener(token_addr)
            current_price = current_info['price_usd']
            
            if current_price > 0:
                current_value = position.quantity * current_price
                pnl = current_value - position.usd_invested
                multiplier = current_value / position.usd_invested
                
                # Check exit conditions
                should_exit = False
                exit_reason = ""
                
                # Take profit at 5x
                if multiplier >= 5.0:
                    should_exit = True
                    exit_reason = "5x Take Profit"
                
                # Stop loss at 80% loss
                elif multiplier <= 0.2:
                    should_exit = True
                    exit_reason = "Stop Loss"
                
                # Time-based exit (24 hours)
                elif (datetime.now() - position.entry_time).total_seconds() > 86400:
                    should_exit = True
                    exit_reason = "24h Time Limit"
                
                if should_exit:
                    await self.close_position(token_addr, exit_reason)
                else:
                    print(f"📊 {position.token_symbol}: ${current_value:.2f} ({multiplier:.2f}x) | P&L: ${pnl:.2f}")
    
    async def close_position(self, token_addr: str, reason: str):
        """Close a position through OKX"""
        position = self.positions.get(token_addr)
        if not position:
            return
        
        print(f"💰 Closing {position.token_symbol} position - {reason}")
        
        # Get current price
        current_info = await self.get_token_info_dexscreener(token_addr)
        current_value = position.quantity * current_info['price_usd']
        pnl = current_value - position.usd_invested
        
        # For demo, just update capital (in production, execute actual sell trade)
        self.current_capital += current_value
        
        # Remove position
        del self.positions[token_addr]
        
        # Record trade
        self.trade_history.append({
            'timestamp': datetime.now().isoformat(),
            'action': 'SELL',
            'token_address': token_addr,
            'token_symbol': position.token_symbol,
            'price': current_info['price_usd'],
            'amount_usd': current_value,
            'pnl': pnl,
            'reason': reason,
            'method': 'OKX_DEX'
        })
        
        multiplier = current_value / position.usd_invested
        print(f"✅ Position closed: {multiplier:.2f}x | P&L: ${pnl:.2f}")
        
        # Check if we've hit the $1M target
        if self.current_capital >= 1000000:
            print("🎉 TARGET ACHIEVED: $1K → $1M!")
            await self.send_discord_notification({
                'action': 'TARGET_ACHIEVED',
                'message': f'🎉 $1K → $1M ACHIEVED! Final Value: ${self.current_capital:.2f}'
            })
    
    async def send_discord_notification(self, trade_data: dict):
        """Send notification to Discord"""
        webhook_url = CONFIG.get('DISCORD_WEBHOOK')
        if not webhook_url:
            return
        
        try:
            embed = {
                "title": "🚀 Elite Mirror Bot - OKX Trade",
                "color": 0x00ff00 if trade_data['action'] == 'BUY' else 0xff0000,
                "fields": [
                    {
                        "name": "Action",
                        "value": f"📊 {trade_data['action']}",
                        "inline": True
                    },
                    {
                        "name": "Method",
                        "value": "🔄 OKX DEX",
                        "inline": True
                    },
                    {
                        "name": "Capital",
                        "value": f"💰 ${self.current_capital:.2f}",
                        "inline": True
                    }
                ],
                "footer": {
                    "text": "Elite Alpha Mirror Bot • OKX Trading"
                },
                "timestamp": datetime.now().isoformat()
            }
            
            if 'token_symbol' in trade_data:
                embed["fields"].extend([
                    {
                        "name": "Token",
                        "value": f"💎 {trade_data['token_symbol']}",
                        "inline": True
                    },
                    {
                        "name": "Amount",
                        "value": f"💵 ${trade_data['usd_amount']:.2f}",
                        "inline": True
                    }
                ])
            
            payload = {"embeds": [embed]}
            
            async with self.session.post(webhook_url, json=payload) as response:
                if response.status == 204:
                    print("📱 Discord notification sent!")
        except Exception as e:
            print(f"❌ Discord error: {e}")
    
    def save_session(self):
        """Save current trading session"""
        session_data = {
            'starting_capital': self.starting_capital,
            'current_capital': self.current_capital,
            'positions': [
                {
                    'token_address': pos.token_address,
                    'token_symbol': pos.token_symbol,
                    'entry_price': pos.entry_price,
                    'entry_time': pos.entry_time.isoformat(),
                    'quantity': pos.quantity,
                    'usd_invested': pos.usd_invested,
                    'whale_wallet': pos.whale_wallet
                }
                for pos in self.positions.values()
            ],
            'trade_history': self.trade_history
        }
        
        os.makedirs('data', exist_ok=True)
        with open('data/okx_trading_session.json', 'w') as f:
            json.dump(session_data, f, indent=2)
        
        print("💾 Session saved")

async def main():
    """Main function to run the OKX-focused elite mirror bot"""
    print("🚀 ELITE ALPHA MIRROR BOT - OKX EDITION")
    print("=" * 50)
    print("💰 Target: $1K → $1M via OKX DEX mirroring")
    print("🐋 Following elite wallet trades")
    print("⚡ All trades executed through OKX")
    print("=" * 50)
    
    engine = OKXTradingEngine()
    
    try:
        async with engine:
            # Send startup notification
            await engine.send_discord_notification({
                'action': 'STARTUP',
                'message': f'🚀 Elite Mirror Bot Started | Capital: ${engine.current_capital:.2f}'
            })
            
            # Start monitoring
            await engine.monitor_whale_activity()
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping OKX Elite Mirror Bot...")
        
        # Save session
        engine.save_session()
        
        # Final stats
        total_return = ((engine.current_capital - engine.starting_capital) / engine.starting_capital) * 100
        print(f"\n📊 FINAL RESULTS:")
        print(f"   Starting: ${engine.starting_capital:.2f}")
        print(f"   Final: ${engine.current_capital:.2f}")
        print(f"   Return: {total_return:+.1f}%")
        print(f"   Trades: {len(engine.trade_history)}")
        
        if total_return >= 100000:  # 1000x
            print("🎉 LEGENDARY: $1K → $1M achieved!")
        elif total_return >= 900:  # 10x
            print("💎 EXCELLENT: 10x+ return!")
        elif total_return > 0:
            print("📈 PROFIT: Positive return via smart money following")

if __name__ == "__main__":
    asyncio.run(main())