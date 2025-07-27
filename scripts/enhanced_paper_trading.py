#!/usr/bin/env python3
"""
Enhanced Paper Trading Engine
"""

import asyncio
import json
import logging
import sys
import os
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python.utils.config import load_config, get_trading_config
from python.utils.logging import setup_logging, TradeLogger

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

class EnhancedPaperTradingEngine:
    def __init__(self):
        self.config = get_trading_config()
        self.starting_capital = self.config.initial_capital
        self.current_capital = self.starting_capital
        self.positions: Dict[str, PaperPosition] = {}
        self.trade_history = []
        self.trade_logger = TradeLogger()
        
    async def run_demo(self):
        """Run paper trading demonstration"""
        logging.info("🚀 ENHANCED PAPER TRADING ENGINE")
        logging.info(f"💰 Starting Capital: ${self.starting_capital:.2f}")
        logging.info("=" * 50)
        
        # Simulate whale trades
        await self.simulate_whale_activity()
        
        # Show results
        await self.show_portfolio_summary()
    
    async def simulate_whale_activity(self):
        """Simulate detecting and mirroring whale trades"""
        whale_trades = [
            {
                "wallet": "0xae2fc483527b8ef99eb5d9b44875f005ba1fae13",
                "token": "0xa0b86a33e6441b24b4b2cccdca5e5f7c9ef3bd20",
                "symbol": "ALPHA",
                "reason": "Elite deployer launched new token"
            },
            {
                "wallet": "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b",
                "token": "0xb1c86a44e6441b24b4b2cccdca5e5f7c9ef3bd21",
                "symbol": "MOON",
                "reason": "Early sniper detected buying"
            }
        ]
        
        for trade in whale_trades:
            await self.execute_paper_buy(
                trade["token"],
                trade["wallet"],
                trade["reason"],
                trade["symbol"]
            )
            await asyncio.sleep(1)  # Simulate time between trades
    
    async def execute_paper_buy(self, token_address: str, whale_wallet: str, reason: str, symbol: str = "TOKEN"):
        """Execute a paper buy trade"""
        allocation = self.config.max_position_size
        usd_to_invest = self.current_capital * allocation
        mock_price = 0.000001  # Mock token price
        quantity = usd_to_invest / mock_price
        
        position = PaperPosition(
            token_address=token_address,
            token_symbol=symbol,
            entry_price=mock_price,
            entry_time=datetime.now(),
            quantity=quantity,
            usd_invested=usd_to_invest,
            whale_wallet=whale_wallet,
            entry_reason=reason
        )
        
        self.positions[token_address] = position
        self.current_capital -= usd_to_invest
        
        trade_data = {
            'action': 'BUY',
            'token_symbol': symbol,
            'whale_wallet': whale_wallet,
            'usd_amount': usd_to_invest,
            'price': mock_price,
            'quantity': quantity,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        }
        
        self.trade_history.append(trade_data)
        self.trade_logger.log_trade('BUY', symbol, usd_to_invest, mock_price, whale=whale_wallet[:10])
        
        logging.info(f"✅ PAPER BUY EXECUTED:")
        logging.info(f"   Token: {symbol}")
        logging.info(f"   Price: ${mock_price:.8f}")
        logging.info(f"   USD Invested: ${usd_to_invest:.2f}")
        logging.info(f"   Whale: {whale_wallet[:10]}...")
        logging.info(f"   Reason: {reason}")
    
    async def show_portfolio_summary(self):
        """Show comprehensive portfolio summary"""
        total_invested = sum(pos.usd_invested for pos in self.positions.values())
        total_value = self.current_capital + total_invested  # Simplified
        total_return = ((total_value - self.starting_capital) / self.starting_capital) * 100
        
        logging.info("\n📊 PORTFOLIO SUMMARY")
        logging.info("=" * 30)
        logging.info(f"💰 Starting Capital: ${self.starting_capital:.2f}")
        logging.info(f"💵 Current Cash: ${self.current_capital:.2f}")
        logging.info(f"🎯 Active Positions: {len(self.positions)}")
        logging.info(f"📈 Total Value: ${total_value:.2f}")
        logging.info(f"📊 Total Return: {total_return:+.1f}%")
        logging.info(f"🔄 Total Trades: {len(self.trade_history)}")
        
        if self.positions:
            logging.info("\n🎯 CURRENT POSITIONS:")
            for pos in self.positions.values():
                logging.info(f"  📈 {pos.token_symbol}: ${pos.usd_invested:.2f}")
                logging.info(f"     Whale: {pos.whale_wallet[:10]}...")
                logging.info(f"     Reason: {pos.entry_reason}")
        
        # Save session
        self.save_session()
    
    def save_session(self):
        """Save trading session"""
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
            'trades': self.trade_history,
            'timestamp': datetime.now().isoformat()
        }
        
        os.makedirs('data', exist_ok=True)
        with open('data/paper_trading_session.json', 'w') as f:
            json.dump(session_data, f, indent=2)
        
        logging.info("💾 Session saved to data/paper_trading_session.json")

async def main():
    setup_logging()
    engine = EnhancedPaperTradingEngine()
    await engine.run_demo()

if __name__ == "__main__":
    asyncio.run(main())
