import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from python.ml.models.whale_predictor import WhaleMLEngine
from grok.api.grok_client import GrokAIClient
from core.okx_live_engine import OKXLiveEngine
from core.ultra_fast_engine import UltraFastEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MLEnhancedTradingSystem:
    def __init__(self):
        self.ml_engine = None
        self.grok_client = None
        self.okx_engine = None
        self.websocket_engine = None
        self.capital = float(os.getenv("STARTING_CAPITAL", "1000"))
        self.positions = {}
        self.trade_decisions = []
        
    async def initialize(self):
        logger.info("🧠 Initializing ML-Enhanced Trading System...")
        
        self.ml_engine = WhaleMLEngine()
        self.grok_client = GrokAIClient()
        self.okx_engine = OKXLiveEngine()
        self.websocket_engine = UltraFastEngine()
        
        await self.ml_engine.__aenter__()
        await self.grok_client.__aenter__()
        await self.okx_engine.__aenter__()
        
        logger.info("🔥 Training ML model on historical whale data...")
        training_time = int(os.getenv("ML_TRAINING_MINUTES", "10"))
        await self.ml_engine.train_model(training_minutes=training_time)
        
        await self.websocket_engine.load_elite_wallets()
        
        logger.info("✅ ML-Enhanced system ready!")
        
    async def run_trading_loop(self):
        logger.info("🚀 Starting ML-enhanced trading loop...")
        
        while True:
            try:
                if hasattr(self.websocket_engine, 'pending_trades') and self.websocket_engine.pending_trades:
                    trades = list(self.websocket_engine.pending_trades.items())
                    self.websocket_engine.pending_trades.clear()
                    
                    for tx_hash, trade in trades:
                        await self.process_trade_with_ml_and_grok(trade)
                        
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Trading loop error: {e}")
                await asyncio.sleep(1)
                
    async def process_trade_with_ml_and_grok(self, trade):
        try:
            logger.info(f"🤖 Processing trade with ML+Grok: {trade.whale_wallet[:12]}...")
            
            whale_data = {
                "address": trade.whale_wallet,
                "avg_multiplier": 25.0,
                "success_rate": 0.75,
                "total_trades": 150,
                "last_activity": datetime.now().isoformat()
            }
            
            token_data = {
                "address": trade.token_address,
                "price": 0.000001,
                "volume_24h": 500000,
                "liquidity": 100000,
                "holders": 1000,
                "price_change_24h": 50.0
            }
            
            market_context = {
                "eth_price": 3000,
                "gas_price": 30,
                "sentiment": "neutral",
                "total_market_cap": 2500000000000
            }
            
            ml_prediction = self.ml_engine.predict_trade_success(whale_data, token_data)
            logger.info(f"🧠 ML Prediction: {ml_prediction:.3f}")
            
            grok_decision = await self.grok_client.analyze_trade_decision(
                whale_data, token_data, market_context
            )
            logger.info(f"🤖 Grok Decision: {grok_decision}")
            
            combined_confidence = (ml_prediction + grok_decision["confidence"] / 100) / 2
            
            should_execute = (
                grok_decision["execute"] and 
                ml_prediction > 0.7 and 
                combined_confidence > 0.75
            )
            
            if should_execute:
                position_size = min(
                    self.capital * grok_decision.get("position_size", 0.2),
                    self.capital * 0.3
                )
                
                logger.info(f"✅ Executing trade: ${position_size:.2f}")
                
                result = await self.okx_engine.execute_live_trade(
                    token_address=trade.token_address,
                    amount_usd=position_size,
                    priority_gas=5_000_000_000
                )
                
                if result.success:
                    await self.record_successful_trade(trade, result, grok_decision, ml_prediction)
                    logger.info(f"🎯 Trade executed successfully!")
                else:
                    logger.error(f"❌ Trade execution failed: {result.error_message}")
            else:
                logger.info(f"⏭️ Trade rejected by ML+Grok analysis")
                
            self.trade_decisions.append({
                "timestamp": datetime.now().isoformat(),
                "whale_wallet": trade.whale_wallet,
                "token_address": trade.token_address,
                "ml_prediction": ml_prediction,
                "grok_decision": grok_decision,
                "executed": should_execute,
                "combined_confidence": combined_confidence
            })
            
        except Exception as e:
            logger.error(f"Error in ML+Grok processing: {e}")
            
    async def record_successful_trade(self, trade, result, grok_decision, ml_prediction):
        self.positions[trade.token_address] = {
            "entry_time": datetime.now(),
            "position_size": grok_decision.get("position_size", 0.2) * self.capital,
            "stop_loss": grok_decision.get("stop_loss", 0.8),
            "take_profit": grok_decision.get("take_profit", 3.0),
            "ml_prediction": ml_prediction,
            "grok_confidence": grok_decision["confidence"]
        }
        
        self.capital -= self.positions[trade.token_address]["position_size"]
        
    async def cleanup(self):
        if self.ml_engine:
            await self.ml_engine.__aexit__(None, None, None)
        if self.grok_client:
            await self.grok_client.__aexit__(None, None, None)
        if self.okx_engine:
            await self.okx_engine.__aexit__(None, None, None)

async def main():
    system = MLEnhancedTradingSystem()
    
    try:
        await system.initialize()
        
        monitoring_task = asyncio.create_task(system.websocket_engine.start_ultra_fast_monitoring())
        trading_task = asyncio.create_task(system.run_trading_loop())
        
        await asyncio.gather(monitoring_task, trading_task)
        
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await system.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
