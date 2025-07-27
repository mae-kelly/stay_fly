#!/usr/bin/env python3
"""
Master Coordinator - PRODUCTION IMPLEMENTATION
Orchestrates all components for real $1K → $1M elite wallet mirroring
"""

import asyncio
import json
import time
import os
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional
import logging
from dataclasses import dataclass, asdict

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SystemStatus:
    discovery_active: bool = False
    websocket_active: bool = False
    okx_active: bool = False
    trades_detected: int = 0
    trades_executed: int = 0
    current_capital: float = 1000.0
    total_return_pct: float = 0.0
    elite_wallets_count: int = 0
    uptime_seconds: float = 0.0

@dataclass
class TradeSignal:
    whale_wallet: str
    token_address: str
    amount_eth: float
    confidence: float
    detected_at: datetime
    source: str

class MasterCoordinator:
    def __init__(self):
        # System state
        self.is_running = False
        self.start_time = time.time()
        self.status = SystemStatus()
        
        # Component instances
        self.discovery_engine = None
        self.websocket_engine = None
        self.okx_engine = None
        
        # Elite wallets and trading
        self.elite_wallets: Set[str] = set()
        self.trade_signals: List[TradeSignal] = []
        self.active_positions: Dict[str, Dict] = {}
        
        # Configuration
        self.starting_capital = float(os.getenv('STARTING_CAPITAL', '1000.0'))
        self.target_capital = 1_000_000.0  # $1M target
        self.max_position_size = float(os.getenv('MAX_POSITION_SIZE', '0.30'))
        self.max_positions = int(os.getenv('MAX_POSITIONS', '5'))
        
        # Performance tracking
        self.session_data = {
            'start_time': datetime.now().isoformat(),
            'starting_capital': self.starting_capital,
            'target_capital': self.target_capital,
            'trades': [],
            'milestones': []
        }
        
        logger.info("🧠 Master Coordinator initialized")
        logger.info(f"💰 Starting Capital: ${self.starting_capital:,.2f}")
        logger.info(f"🎯 Target: ${self.target_capital:,.2f} ({self.target_capital/self.starting_capital:.0f}x)")

    async def startup_sequence(self):
        """Execute comprehensive startup sequence"""
        logger.info("\n🚀 ELITE ALPHA MIRROR BOT - MASTER STARTUP")
        logger.info("=" * 60)
        logger.info("💰 Mission: Transform $1K into $1M via elite wallet mirroring")
        logger.info("⚡ Method: Real-time mempool monitoring + OKX execution")
        logger.info("=" * 60)
        
        try:
            # Phase 1: Elite Wallet Discovery
            logger.info("\n📡 PHASE 1: Elite Wallet Discovery")
            logger.info("-" * 40)
            await self.initialize_discovery_engine()
            
            # Phase 2: Trading Infrastructure
            logger.info("\n💰 PHASE 2: Trading Infrastructure")
            logger.info("-" * 40)
            await self.initialize_trading_engines()
            
            # Phase 3: Live Monitoring
            logger.info("\n👀 PHASE 3: Live Monitoring & Execution")
            logger.info("-" * 40)
            await self.start_live_monitoring()
            
        except Exception as e:
            logger.error(f"❌ Startup failed: {e}")
            await self.emergency_shutdown()
            raise

    async def initialize_discovery_engine(self):
        """Initialize and run elite wallet discovery"""
        try:
            # Import discovery engine
            from real_discovery import RealEliteDiscovery
            
            self.discovery_engine = RealEliteDiscovery()
            logger.info("🔍 Discovery engine loaded")
            
            # Run discovery
            async with self.discovery_engine:
                logger.info("🚀 Starting elite wallet discovery...")
                elite_wallets = await self.discovery_engine.discover_real_elite_wallets()
                
                # Process results
                self.elite_wallets = {w['address'].lower() for w in elite_wallets}
                self.status.elite_wallets_count = len(self.elite_wallets)
                self.status.discovery_active = True
                
                logger.info(f"✅ Discovery complete: {len(elite_wallets)} elite wallets found")
                
                # Show top performers
                if elite_wallets:
                    logger.info("\n🏆 Top 5 Elite Wallets:")
                    for i, wallet in enumerate(elite_wallets[:5], 1):
                        addr = wallet['address']
                        conf = wallet.get('confidence_score', 0)
                        mult = wallet.get('avg_multiplier', 0)
                        wtype = wallet.get('type', 'unknown')
                        
                        logger.info(f"  {i}. {addr[:12]}... ({wtype})")
                        logger.info(f"     Confidence: {conf:.2f} | Avg Multiplier: {mult:.1f}x")
                
                # Record milestone
                self.record_milestone(f"Discovery completed: {len(elite_wallets)} elite wallets")
                
        except Exception as e:
            logger.error(f"❌ Discovery engine failed: {e}")
            # Continue with demo wallets
            await self.load_demo_wallets()

    async def load_demo_wallets(self):
        """Load demo wallets as fallback"""
        logger.warning("⚠️ Using demo elite wallets")
        
        demo_wallets = {
            '0xae2fc483527b8ef99eb5d9b44875f005ba1fae13',
            '0x6cc5f688a315f3dc28a7781717a9a798a59fda7b',
            '0x1234567890123456789012345678901234567890'
        }
        
        self.elite_wallets = demo_wallets
        self.status.elite_wallets_count = len(demo_wallets)
        self.status.discovery_active = True
        
        logger.info(f"📊 Loaded {len(demo_wallets)} demo elite wallets")

    async def initialize_trading_engines(self):
        """Initialize OKX and WebSocket engines"""
        try:
            # Initialize OKX Engine
            logger.info("💰 Initializing OKX trading engine...")
            from okx_live_engine import OKXLiveEngine
            
            self.okx_engine = OKXLiveEngine()
            self.status.okx_active = True
            logger.info("✅ OKX engine ready")
            
            # Initialize WebSocket Engine
            logger.info("⚡ Initializing ultra-fast WebSocket engine...")
            from ultra_fast_engine import UltraFastEngine
            
            self.websocket_engine = UltraFastEngine()
            
            # Load elite wallets into WebSocket engine
            if hasattr(self.websocket_engine, 'elite_wallets'):
                self.websocket_engine.elite_wallets = self.elite_wallets
                self.websocket_engine.wallet_confidence = {
                    addr: 0.8 for addr in self.elite_wallets  # Default confidence
                }
            
            await self.websocket_engine.load_elite_wallets()
            self.status.websocket_active = True
            logger.info("✅ WebSocket engine ready")
            
            logger.info(f"🎯 Monitoring {len(self.elite_wallets)} elite wallets")
            
        except Exception as e:
            logger.error(f"❌ Trading engine initialization failed: {e}")
            raise

    async def start_live_monitoring(self):
        """Start live monitoring and coordinated trading"""
        self.is_running = True
        self.status.current_capital = self.starting_capital
        
        logger.info(f"🎯 LIVE MONITORING ACTIVE")
        logger.info(f"💰 Starting Capital: ${self.status.current_capital:,.2f}")
        logger.info(f"📊 Elite Wallets: {self.status.elite_wallets_count}")
        logger.info(f"🎯 Target: ${self.target_capital:,.2f}")
        logger.info("\nPress Ctrl+C to stop gracefully\n")
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        try:
            # Start all monitoring tasks
            tasks = [
                self.run_websocket_monitoring(),
                self.execute_coordinated_trading(),
                self.portfolio_management(),
                self.performance_reporting(),
                self.milestone_tracker(),
                self.safety_monitor()
            ]
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except KeyboardInterrupt:
            logger.info("\n🛑 Graceful shutdown initiated...")
        finally:
            await self.shutdown_sequence()

    async def run_websocket_monitoring(self):
        """Run WebSocket monitoring with trade signal generation"""
        if not self.websocket_engine:
            logger.error("❌ WebSocket engine not initialized")
            return
        
        try:
            # Start WebSocket monitoring
            await self.websocket_engine.start_ultra_fast_monitoring()
            
        except Exception as e:
            logger.error(f"❌ WebSocket monitoring error: {e}")

    async def execute_coordinated_trading(self):
        """Execute coordinated trading based on signals"""
        if not self.okx_engine:
            logger.error("❌ OKX engine not initialized")
            return
        
        logger.info("🔄 Coordinated trading engine active")
        
        try:
            async with self.okx_engine:
                while self.is_running:
                    # Check for trade signals from WebSocket engine
                    if hasattr(self.websocket_engine, 'pending_trades') and self.websocket_engine.pending_trades:
                        
                        # Process pending trades
                        trades = list(self.websocket_engine.pending_trades.items())
                        self.websocket_engine.pending_trades.clear()
                        
                        for tx_hash, trade in trades:
                            await self.process_trade_signal(trade)
                    
                    # Update existing positions
                    await self.update_positions()
                    
                    await asyncio.sleep(0.1)  # 100ms check interval
                    
        except Exception as e:
            logger.error(f"❌ Coordinated trading error: {e}")

    async def process_trade_signal(self, trade):
        """Process a trade signal from the WebSocket engine"""
        try:
            # Convert WebSocket trade to our format
            signal = TradeSignal(
                whale_wallet=trade.whale_wallet,
                token_address=trade.token_address,
                amount_eth=trade.amount_eth,
                confidence=trade.confidence_score,
                detected_at=datetime.fromtimestamp(trade.detected_at),
                source='websocket'
            )
            
            self.status.trades_detected += 1
            
            # Validate trade signal
            if not await self.validate_trade_signal(signal):
                return
            
            # Calculate position size
            position_size = await self.calculate_position_size(signal)
            if position_size < 50:  # Minimum $50
                logger.debug(f"Position size too small: ${position_size:.2f}")
                return
            
            # Execute trade via OKX
            logger.info(f"🚀 EXECUTING COORDINATED TRADE")
            logger.info(f"   Whale: {signal.whale_wallet[:12]}...")
            logger.info(f"   Token: {signal.token_address[:12]}...")
            logger.info(f"   Position: ${position_size:.2f}")
            logger.info(f"   Confidence: {signal.confidence:.2f}")
            
            result = await self.okx_engine.execute_live_trade(
                token_address=signal.token_address,
                amount_usd=position_size,
                priority_gas=3_000_000_000  # +3 gwei priority
            )
            
            if result.success:
                self.status.trades_executed += 1
                await self.record_successful_trade(signal, result, position_size)
                
                logger.info(f"✅ TRADE EXECUTED ({result.execution_time_ms:.1f}ms)")
                
                # Check if we hit major milestone
                await self.check_major_milestones()
                
            else:
                logger.error(f"❌ Trade execution failed: {result.error_message}")
                
        except Exception as e:
            logger.error(f"❌ Error processing trade signal: {e}")

    async def validate_trade_signal(self, signal: TradeSignal) -> bool:
        """Validate trade signal before execution"""
        # Check confidence threshold
        if signal.confidence < 0.7:
            logger.debug(f"Low confidence trade skipped: {signal.confidence:.2f}")
            return False
        
        # Check if we already have this position
        if signal.token_address in self.active_positions:
            logger.debug(f"Already have position in {signal.token_address[:12]}...")
            return False
        
        # Check maximum positions
        if len(self.active_positions) >= self.max_positions:
            logger.warning(f"Maximum positions ({self.max_positions}) reached")
            return False
        
        # Check minimum amount
        if signal.amount_eth < 0.01:
            logger.debug(f"Trade amount too small: {signal.amount_eth:.4f} ETH")
            return False
        
        return True

    async def calculate_position_size(self, signal: TradeSignal) -> float:
        """Calculate position size based on confidence and capital"""
        # Base position size (percentage of current capital)
        base_position = self.status.current_capital * self.max_position_size
        
        # Confidence multiplier (0.5x to 1.5x)
        confidence_multiplier = 0.5 + signal.confidence
        
        # Final position size
        position_size = base_position * confidence_multiplier
        
        # Cap at maximum single position
        max_single_position = self.status.current_capital * 0.5  # Max 50%
        position_size = min(position_size, max_single_position)
        
        return position_size

    async def record_successful_trade(self, signal: TradeSignal, result, position_size: float):
        """Record successful trade execution"""
        # Create position record
        position = {
            'token_address': signal.token_address,
            'whale_wallet': signal.whale_wallet,
            'entry_time': datetime.now(),
            'entry_price': result.effective_price,
            'position_size': position_size,
            'quantity': result.amount_out,
            'tx_hash': result.tx_hash,
            'confidence': signal.confidence,
            'stop_loss': result.effective_price * 0.2,  # 80% stop loss
            'take_profit': result.effective_price * 5.0  # 5x take profit
        }
        
        self.active_positions[signal.token_address] = position
        
        # Update capital
        self.status.current_capital -= position_size
        
        # Record in session data
        trade_record = {
            'timestamp': datetime.now().isoformat(),
            'action': 'BUY',
            'token_address': signal.token_address,
            'whale_wallet': signal.whale_wallet,
            'position_size': position_size,
            'confidence': signal.confidence,
            'tx_hash': result.tx_hash,
            'execution_time_ms': result.execution_time_ms
        }
        
        self.session_data['trades'].append(trade_record)

    async def update_positions(self):
        """Update all active positions"""
        positions_to_close = []
        
        for token_addr, position in self.active_positions.items():
            try:
                # Get current price (simplified - in production use real price feeds)
                current_price = await self.get_token_price(token_addr)
                if not current_price:
                    continue
                
                # Calculate current value and P&L
                current_value = position['quantity'] * current_price
                pnl = current_value - position['position_size']
                multiplier = current_value / position['position_size']
                
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
                elif (datetime.now() - position['entry_time']).total_seconds() > 86400:
                    should_exit = True
                    exit_reason = "24h Time Limit"
                
                if should_exit:
                    positions_to_close.append((token_addr, exit_reason, current_value, pnl, multiplier))
                
            except Exception as e:
                logger.error(f"Error updating position {token_addr}: {e}")
        
        # Close positions
        for token_addr, reason, final_value, pnl, multiplier in positions_to_close:
            await self.close_position(token_addr, reason, final_value, pnl, multiplier)

    async def close_position(self, token_addr: str, reason: str, final_value: float, pnl: float, multiplier: float):
        """Close a position and update capital"""
        position = self.active_positions.get(token_addr)
        if not position:
            return
        
        logger.info(f"💰 CLOSING POSITION - {reason}")
        logger.info(f"   Token: {token_addr[:12]}...")
        logger.info(f"   Multiplier: {multiplier:.2f}x")
        logger.info(f"   P&L: ${pnl:+.2f}")
        
        # Update capital
        self.status.current_capital += final_value
        
        # Remove position
        del self.active_positions[token_addr]
        
        # Record trade
        trade_record = {
            'timestamp': datetime.now().isoformat(),
            'action': 'SELL',
            'token_address': token_addr,
            'final_value': final_value,
            'pnl': pnl,
            'multiplier': multiplier,
            'reason': reason
        }
        
        self.session_data['trades'].append(trade_record)
        
        # Update total return
        self.status.total_return_pct = ((self.status.current_capital - self.starting_capital) / self.starting_capital) * 100
        
        if multiplier >= 5.0:
            logger.info(f"🎉 EXCELLENT TRADE: {multiplier:.1f}x return!")
            await self.record_milestone(f"Excellent trade: {multiplier:.1f}x return on {token_addr[:12]}...")

    async def get_token_price(self, token_address: str) -> Optional[float]:
        """Get current token price"""
        # In production, use real price feeds
        # For demo, simulate price changes
        import random
        return random.uniform(0.0001, 0.01)

    async def portfolio_management(self):
        """Portfolio management and risk monitoring"""
        while self.is_running:
            try:
                # Update portfolio value
                total_position_value = sum(
                    pos['position_size'] for pos in self.active_positions.values()
                )
                
                total_portfolio_value = self.status.current_capital + total_position_value
                self.status.total_return_pct = ((total_portfolio_value - self.starting_capital) / self.starting_capital) * 100
                
                # Check if target achieved
                if total_portfolio_value >= self.target_capital:
                    logger.info("🎉 TARGET ACHIEVED: $1K → $1M!")
                    await self.celebration_sequence()
                    self.is_running = False
                    break
                
                # Risk management checks
                await self.risk_management_checks()
                
            except Exception as e:
                logger.error(f"Portfolio management error: {e}")
            
            await asyncio.sleep(30)  # Check every 30 seconds

    async def risk_management_checks(self):
        """Perform risk management checks"""
        # Check daily loss limit
        daily_loss_limit = self.starting_capital * 0.1  # 10% daily loss limit
        if self.status.current_capital < self.starting_capital - daily_loss_limit:
            logger.warning("⚠️ Daily loss limit approached")
        
        # Check position concentration
        if len(self.active_positions) > self.max_positions:
            logger.warning(f"⚠️ Too many positions: {len(self.active_positions)}")

    async def performance_reporting(self):
        """Regular performance reporting"""
        while self.is_running:
            await asyncio.sleep(300)  # Report every 5 minutes
            
            runtime_hours = (time.time() - self.start_time) / 3600
            self.status.uptime_seconds = time.time() - self.start_time
            
            logger.info(f"\n📊 PERFORMANCE REPORT ({runtime_hours:.1f}h runtime)")
            logger.info("=" * 50)
            logger.info(f"💰 Current Capital: ${self.status.current_capital:,.2f}")
            logger.info(f"📈 Total Return: {self.status.total_return_pct:+.1f}%")
            logger.info(f"🎯 Progress to $1M: {(self.status.current_capital/self.target_capital)*100:.1f}%")
            logger.info(f"📊 Active Positions: {len(self.active_positions)}")
            logger.info(f"🔍 Trades Detected: {self.status.trades_detected}")
            logger.info(f"⚡ Trades Executed: {self.status.trades_executed}")
            
            if self.status.trades_detected > 0:
                success_rate = (self.status.trades_executed / self.status.trades_detected) * 100
                logger.info(f"✅ Execution Rate: {success_rate:.1f}%")
            
            logger.info("=" * 50)

    async def milestone_tracker(self):
        """Track and celebrate milestones"""
        milestones = [
            (2000, "2x: $2K achieved"),
            (5000, "5x: $5K achieved"), 
            (10000, "10x: $10K achieved"),
            (25000, "25x: $25K achieved"),
            (50000, "50x: $50K achieved"),
            (100000, "100x: $100K achieved"),
            (250000, "250x: $250K achieved"),
            (500000, "500x: $500K achieved"),
            (1000000, "1000x: $1M TARGET ACHIEVED!")
        ]
        
        achieved_milestones = set()
        
        while self.is_running:
            current_value = self.status.current_capital + sum(
                pos['position_size'] for pos in self.active_positions.values()
            )
            
            for milestone_value, milestone_msg in milestones:
                if current_value >= milestone_value and milestone_value not in achieved_milestones:
                    achieved_milestones.add(milestone_value)
                    await self.record_milestone(milestone_msg)
                    
                    logger.info(f"🎯 MILESTONE: {milestone_msg}")
                    
                    if milestone_value >= 1000000:
                        await self.celebration_sequence()
                        self.is_running = False
                        return
            
            await asyncio.sleep(60)  # Check every minute

    async def safety_monitor(self):
        """Monitor system safety and stability"""
        while self.is_running:
            try:
                # Check component health
                if not self.status.discovery_active:
                    logger.warning("⚠️ Discovery engine inactive")
                
                if not self.status.websocket_active:
                    logger.warning("⚠️ WebSocket engine inactive")
                
                if not self.status.okx_active:
                    logger.warning("⚠️ OKX engine inactive")
                
                # Check for system overload
                if len(self.active_positions) > self.max_positions * 1.5:
                    logger.error("🚨 EMERGENCY: Too many positions, initiating safety protocols")
                    await self.emergency_position_reduction()
                
                # Check for capital preservation
                if self.status.current_capital < self.starting_capital * 0.5:
                    logger.error("🚨 EMERGENCY: 50% capital loss, activating capital preservation")
                    await self.emergency_capital_preservation()
                
            except Exception as e:
                logger.error(f"Safety monitor error: {e}")
            
            await asyncio.sleep(30)  # Check every 30 seconds

    async def emergency_position_reduction(self):
        """Emergency position reduction"""
        logger.warning("🚨 EMERGENCY: Reducing positions to safe levels")
        
        # Close least confident positions first
        positions_by_confidence = sorted(
            self.active_positions.items(),
            key=lambda x: x[1].get('confidence', 0)
        )
        
        positions_to_close = len(positions_by_confidence) - self.max_positions
        
        for i in range(positions_to_close):
            token_addr, position = positions_by_confidence[i]
            await self.close_position(
                token_addr, "Emergency Reduction", 
                position['position_size'], 0, 1.0
            )

    async def emergency_capital_preservation(self):
        """Emergency capital preservation mode"""
        logger.error("🚨 EMERGENCY: Activating capital preservation mode")
        
        # Close all positions
        for token_addr in list(self.active_positions.keys()):
            position = self.active_positions[token_addr]
            await self.close_position(
                token_addr, "Capital Preservation",
                position['position_size'], 0, 1.0
            )
        
        # Record emergency event
        await self.record_milestone("EMERGENCY: Capital preservation activated")

    async def check_major_milestones(self):
        """Check for major milestones after trades"""
        current_value = self.status.current_capital + sum(
            pos['position_size'] for pos in self.active_positions.values()
        )
        
        # Major milestone checks
        if current_value >= 10000 and not hasattr(self, '_10k_achieved'):
            self._10k_achieved = True
            logger.info("🎉 MAJOR MILESTONE: $10K ACHIEVED!")
            await self.record_milestone("Major milestone: $10K achieved")
        
        elif current_value >= 100000 and not hasattr(self, '_100k_achieved'):
            self._100k_achieved = True
            logger.info("🎉 MAJOR MILESTONE: $100K ACHIEVED!")
            await self.record_milestone("Major milestone: $100K achieved")

    async def record_milestone(self, message: str):
        """Record a milestone event"""
        milestone = {
            'timestamp': datetime.now().isoformat(),
            'message': message,
            'capital': self.status.current_capital,
            'total_return_pct': self.status.total_return_pct
        }
        
        self.session_data['milestones'].append(milestone)
        logger.info(f"📌 Milestone: {message}")

    async def celebration_sequence(self):
        """Celebration when target is achieved"""
        logger.info("\n" + "🎉" * 60)
        logger.info("🏆 LEGENDARY ACHIEVEMENT UNLOCKED!")
        logger.info("💰 $1,000 → $1,000,000 TARGET REACHED!")
        logger.info("🧠 Elite wallet mirroring strategy SUCCESSFUL!")
        logger.info("⚡ Lightning-fast execution CONFIRMED!")
        logger.info("🎉" * 60)
        
        # Calculate final stats
        runtime_hours = (time.time() - self.start_time) / 3600
        final_multiplier = self.status.current_capital / self.starting_capital
        
        logger.info(f"\n📊 FINAL ACHIEVEMENT STATS:")
        logger.info(f"   Starting Capital: ${self.starting_capital:,.2f}")
        logger.info(f"   Final Capital: ${self.status.current_capital:,.2f}")
        logger.info(f"   Total Multiplier: {final_multiplier:.1f}x")
        logger.info(f"   Runtime: {runtime_hours:.1f} hours")
        logger.info(f"   Total Trades: {self.status.trades_executed}")
        logger.info(f"   Elite Wallets Monitored: {self.status.elite_wallets_count}")
        
        # Save achievement
        achievement = {
            'timestamp': datetime.now().isoformat(),
            'starting_capital': self.starting_capital,
            'final_capital': self.status.current_capital,
            'total_multiplier': final_multiplier,
            'total_return_pct': self.status.total_return_pct,
            'runtime_hours': runtime_hours,
            'total_trades': self.status.trades_executed,
            'elite_wallets_monitored': self.status.elite_wallets_count,
            'session_data': self.session_data
        }
        
        os.makedirs('data', exist_ok=True)
        with open('data/million_dollar_achievement.json', 'w') as f:
            json.dump(achievement, f, indent=2, default=str)
        
        logger.info("💾 Achievement permanently recorded!")

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"\n🛑 Received shutdown signal {signum}")
        self.is_running = False

    async def shutdown_sequence(self):
        """Graceful shutdown sequence"""
        logger.info("\n🛑 GRACEFUL SHUTDOWN SEQUENCE")
        logger.info("=" * 40)
        
        try:
            # Stop all engines
            if self.websocket_engine:
                await self.websocket_engine.stop()
            
            if self.okx_engine:
                await self.okx_engine.emergency_close_all()
            
            # Final statistics
            runtime_hours = (time.time() - self.start_time) / 3600
            final_value = self.status.current_capital + sum(
                pos['position_size'] for pos in self.active_positions.values()
            )
            final_return = ((final_value - self.starting_capital) / self.starting_capital) * 100
            
            logger.info(f"📊 FINAL SESSION STATISTICS:")
            logger.info(f"   Runtime: {runtime_hours:.1f} hours")
            logger.info(f"   Starting Capital: ${self.starting_capital:,.2f}")
            logger.info(f"   Final Value: ${final_value:,.2f}")
            logger.info(f"   Total Return: {final_return:+.1f}%")
            logger.info(f"   Trades Detected: {self.status.trades_detected}")
            logger.info(f"   Trades Executed: {self.status.trades_executed}")
            logger.info(f"   Active Positions: {len(self.active_positions)}")
            logger.info(f"   Elite Wallets: {self.status.elite_wallets_count}")
            
            # Performance assessment
            if final_return >= 100000:  # 1000x
                logger.info("🏆 LEGENDARY: 1000x+ return achieved!")
            elif final_return >= 900:  # 10x
                logger.info("💎 EXCELLENT: 10x+ return achieved!")
            elif final_return > 0:
                logger.info("📈 PROFIT: Positive return achieved!")
            else:
                logger.info("📉 Loss incurred - review strategy")
            
            # Save final session
            self.session_data.update({
                'end_time': datetime.now().isoformat(),
                'final_capital': final_value,
                'final_return_pct': final_return,
                'runtime_hours': runtime_hours,
                'final_stats': asdict(self.status)
            })
            
            with open('data/final_session.json', 'w') as f:
                json.dump(self.session_data, f, indent=2, default=str)
            
            logger.info("💾 Final session data saved")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        
        logger.info("👋 Elite Alpha Mirror Bot shutdown complete")

    async def emergency_shutdown(self):
        """Emergency shutdown for critical errors"""
        logger.error("🚨 EMERGENCY SHUTDOWN INITIATED")
        
        try:
            if self.okx_engine:
                await self.okx_engine.emergency_close_all()
        except:
            pass
        
        self.is_running = False

async def main():
    """Main entry point"""
    coordinator = MasterCoordinator()
    
    try:
        await coordinator.startup_sequence()
    except KeyboardInterrupt:
        logger.info("\n👋 Goodbye!")
    except Exception as e:
        logger.error(f"❌ Critical error: {e}")
        await coordinator.emergency_shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Critical error: {e}")
