import asyncio
import aiohttp
import json
import time
from datetime import datetime
from web3 import Web3
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class PaperPosition:
    token_address: str
    token_symbol: str
    entry_price: float
    entry_time: datetime
    quantity: float
    usd_invested: float
    whale_wallet: str
    entry_reason: str

@dataclass
class PaperTrade:
    timestamp: datetime
    action: str  # 'BUY' or 'SELL'
    token_address: str
    token_symbol: str
    price: float
    quantity: float
    usd_amount: float
    whale_wallet: str
    reason: str
    pnl: float = 0.0

class PaperTradingEngine:
    def __init__(self, starting_capital: float = 1000.0):
        self.starting_capital = starting_capital
        self.current_capital = starting_capital
        self.positions: Dict[str, PaperPosition] = {}
        self.trade_history: List[PaperTrade] = []
        self.w3 = Web3(Web3.HTTPProvider('https://eth-mainnet.alchemyapi.io/v2/alcht_oZ7wU7JpIoZejlOWUcMFOpNsIlLDsX'))
        self.session = None
        self.elite_wallets = {}
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        await self.load_elite_wallets()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def load_elite_wallets(self):
        """Load elite wallets from discovery"""
        try:
            with open('data/real_elite_wallets.json', 'r') as f:
                wallets = json.load(f)
                self.elite_wallets = {w['address'].lower(): w for w in wallets}
            print(f"📊 Loaded {len(self.elite_wallets)} elite wallets for paper trading")
        except FileNotFoundError:
            print("❌ No elite wallets found. Run discovery first.")
    
    async def get_token_price_usd(self, token_address: str) -> float:
        """Get current token price in USD from DexScreener"""
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            async with self.session.get(url) as response:
                data = await response.json()
                
                if data.get('pairs'):
                    # Get the pair with highest liquidity
                    best_pair = max(data['pairs'], key=lambda x: float(x.get('liquidity', {}).get('usd', 0)))
                    price = float(best_pair.get('priceUsd', 0))
                    return price
        except Exception as e:
            print(f"❌ Error getting price for {token_address}: {e}")
        
        return 0.0
    
    async def get_token_info(self, token_address: str) -> dict:
        """Get token symbol and other info"""
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
    
    async def execute_paper_buy(self, token_address: str, whale_wallet: str, reason: str, allocation_percent: float = 30.0):
        """Execute a paper buy trade mirroring a whale"""
        print(f"🛒 PAPER BUY: Mirroring whale {whale_wallet[:10]}...")
        
        # Get token info and price
        token_info = await self.get_token_info(token_address)
        if token_info['price_usd'] <= 0:
            print(f"❌ Cannot get price for {token_address}")
            return
        
        # Calculate position size (% of current capital)
        usd_to_invest = self.current_capital * (allocation_percent / 100)
        quantity = usd_to_invest / token_info['price_usd']
        
        # Create position
        position = PaperPosition(
            token_address=token_address,
            token_symbol=token_info['symbol'],
            entry_price=token_info['price_usd'],
            entry_time=datetime.now(),
            quantity=quantity,
            usd_invested=usd_to_invest,
            whale_wallet=whale_wallet,
            entry_reason=reason
        )
        
        # Update portfolio
        self.positions[token_address] = position
        self.current_capital -= usd_to_invest
        
        # Record trade
        trade = PaperTrade(
            timestamp=datetime.now(),
            action='BUY',
            token_address=token_address,
            token_symbol=token_info['symbol'],
            price=token_info['price_usd'],
            quantity=quantity,
            usd_amount=usd_to_invest,
            whale_wallet=whale_wallet,
            reason=reason
        )
        self.trade_history.append(trade)
        
        print(f"✅ PAPER BUY EXECUTED:")
        print(f"   Token: {token_info['symbol']}")
        print(f"   Price: ${token_info['price_usd']:.6f}")
        print(f"   Quantity: {quantity:,.2f}")
        print(f"   USD Invested: ${usd_to_invest:.2f}")
        print(f"   Remaining Capital: ${self.current_capital:.2f}")
        print(f"   Whale: {whale_wallet[:10]}...")
        print(f"   Reason: {reason}")
    
    async def execute_paper_sell(self, token_address: str, reason: str, sell_percent: float = 100.0):
        """Execute a paper sell trade"""
        if token_address not in self.positions:
            print(f"❌ No position found for {token_address}")
            return
        
        position = self.positions[token_address]
        current_price = await self.get_token_price_usd(token_address)
        
        if current_price <= 0:
            print(f"❌ Cannot get current price for {token_address}")
            return
        
        # Calculate quantities to sell
        quantity_to_sell = position.quantity * (sell_percent / 100)
        usd_received = quantity_to_sell * current_price
        
        # Calculate P&L
        cost_basis = (position.usd_invested / position.quantity) * quantity_to_sell
        pnl = usd_received - cost_basis
        pnl_percent = (pnl / cost_basis) * 100 if cost_basis > 0 else 0
        
        # Update portfolio
        self.current_capital += usd_received
        
        if sell_percent >= 100:
            del self.positions[token_address]
        else:
            position.quantity -= quantity_to_sell
            position.usd_invested -= cost_basis
        
        # Record trade
        trade = PaperTrade(
            timestamp=datetime.now(),
            action='SELL',
            token_address=token_address,
            token_symbol=position.token_symbol,
            price=current_price,
            quantity=quantity_to_sell,
            usd_amount=usd_received,
            whale_wallet=position.whale_wallet,
            reason=reason,
            pnl=pnl
        )
        self.trade_history.append(trade)
        
        print(f"✅ PAPER SELL EXECUTED:")
        print(f"   Token: {position.token_symbol}")
        print(f"   Entry Price: ${position.entry_price:.6f}")
        print(f"   Exit Price: ${current_price:.6f}")
        print(f"   Quantity Sold: {quantity_to_sell:,.2f}")
        print(f"   USD Received: ${usd_received:.2f}")
        print(f"   P&L: ${pnl:.2f} ({pnl_percent:+.1f}%)")
        print(f"   New Capital: ${self.current_capital:.2f}")
    
    async def monitor_whale_transactions(self):
        """Monitor blockchain for whale transactions and execute paper trades"""
        print("👀 Starting paper trading based on real whale activity...")
        print(f"💰 Starting Capital: ${self.starting_capital:.2f}")
        
        last_block = 0
        
        while True:
            try:
                current_block = self.w3.eth.block_number
                
                if current_block > last_block:
                    print(f"🔍 Scanning block {current_block} for whale activity...")
                    
                    # Get block with transactions
                    block = self.w3.eth.get_block(current_block, full_transactions=True)
                    
                    for tx in block.transactions:
                        if tx['from'] and tx['from'].lower() in self.elite_wallets:
                            await self.analyze_whale_transaction(tx)
                    
                    last_block = current_block
                
                # Update position values every block
                await self.update_portfolio_values()
                
                await asyncio.sleep(12)  # Check every block
                
            except Exception as e:
                print(f"❌ Error monitoring: {e}")
                await asyncio.sleep(5)
    
    async def analyze_whale_transaction(self, tx):
        """Analyze whale transaction and decide if we should mirror it"""
        whale_address = tx['from']
        whale_info = self.elite_wallets.get(whale_address.lower(), {})
        
        print(f"🐋 WHALE ACTIVITY DETECTED!")
        print(f"   Whale: {whale_address[:10]}... ({whale_info.get('type', 'unknown')})")
        print(f"   TX Hash: {tx['hash'].hex()[:10]}...")
        
        # Check if it's a significant transaction
        eth_value = Web3.from_wei(tx['value'], 'ether')
        
        if eth_value > 0.1:  # Minimum 0.1 ETH to consider
            print(f"   ETH Value: {eth_value:.4f} ETH")
            
            # Try to decode if it's a DEX swap
            if await self.is_dex_transaction(tx):
                # For demo purposes, extract token from common DEX patterns
                token_address = await self.extract_token_from_tx(tx)
                
                if token_address:
                    reason = f"Mirroring {whale_info.get('type', 'whale')} - {eth_value:.2f} ETH trade"
                    await self.execute_paper_buy(token_address, whale_address, reason)
    
    async def is_dex_transaction(self, tx) -> bool:
        """Check if transaction is likely a DEX trade"""
        # Common DEX router addresses
        dex_routers = {
            '0x7a250d5630b4cf539739df2c5dacb4c659f2488d',  # Uniswap V2
            '0xe592427a0aece92de3edee1f18e0157c05861564',  # Uniswap V3
            '0x1111111254eeb25477b68fb85ed929f73a960582',  # 1inch
        }
        
        return tx['to'] and tx['to'].lower() in dex_routers
    
    async def extract_token_from_tx(self, tx) -> str:
        """Extract token address from transaction (simplified)"""
        # This is a simplified version - in reality you'd decode the calldata
        # For demo, we'll return a placeholder
        return "0xa0b86a33e6441b24b4b2cccdca5e5f7c9ef3bd20"  # Example token
    
    async def update_portfolio_values(self):
        """Update current portfolio values"""
        if not self.positions:
            return
        
        total_portfolio_value = self.current_capital
        
        for token_address, position in self.positions.items():
            current_price = await self.get_token_price_usd(token_address)
            current_value = position.quantity * current_price
            total_portfolio_value += current_value
        
        total_pnl = total_portfolio_value - self.starting_capital
        total_return_pct = (total_pnl / self.starting_capital) * 100
        
        print(f"💼 Portfolio Update:")
        print(f"   Cash: ${self.current_capital:.2f}")
        print(f"   Total Value: ${total_portfolio_value:.2f}")
        print(f"   Total P&L: ${total_pnl:.2f} ({total_return_pct:+.1f}%)")
    
    def save_trading_session(self):
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
                    'whale_wallet': pos.whale_wallet,
                    'entry_reason': pos.entry_reason
                }
                for pos in self.positions.values()
            ],
            'trades': [
                {
                    'timestamp': trade.timestamp.isoformat(),
                    'action': trade.action,
                    'token_symbol': trade.token_symbol,
                    'price': trade.price,
                    'quantity': trade.quantity,
                    'usd_amount': trade.usd_amount,
                    'whale_wallet': trade.whale_wallet,
                    'reason': trade.reason,
                    'pnl': trade.pnl
                }
                for trade in self.trade_history
            ]
        }
        
        with open('data/paper_trading_session.json', 'w') as f:
            json.dump(session_data, f, indent=2)
        
        print("💾 Trading session saved to data/paper_trading_session.json")

async def main():
    engine = PaperTradingEngine(starting_capital=1000.0)
    
    try:
        async with engine:
            # Start monitoring
            await engine.monitor_whale_transactions()
    except KeyboardInterrupt:
        print("\n🛑 Stopping paper trading engine...")
        engine.save_trading_session()
        
        # Print final results
        total_value = engine.current_capital + sum(
            pos.quantity * await engine.get_token_price_usd(pos.token_address)
            for pos in engine.positions.values()
        )
        
        total_return = ((total_value - engine.starting_capital) / engine.starting_capital) * 100
        
        print(f"\n📊 FINAL RESULTS:")
        print(f"   Starting Capital: ${engine.starting_capital:.2f}")
        print(f"   Final Value: ${total_value:.2f}")
        print(f"   Total Return: {total_return:+.1f}%")
        print(f"   Total Trades: {len(engine.trade_history)}")

if __name__ == "__main__":
    asyncio.run(main())
