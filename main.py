#!/usr/bin/env python3
"""
Elite Alpha Mirror Bot - Main Entry Point
The complete $1K → $1M elite wallet mirroring system
"""

import asyncio
import sys
import os
import signal
import logging
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.master_coordinator import MasterCoordinator

def setup_logging():
    """Setup comprehensive logging"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'elite_bot.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Suppress noisy libraries
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('websockets').setLevel(logging.WARNING)

def check_dependencies():
    """Check if all required dependencies are available"""
    try:
        import aiohttp
        import web3
        import pandas
        import numpy
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Run: pip install -r requirements.txt")
        return False

def check_configuration():
    """Check if configuration is properly set up"""
    config_file = Path("config.env")
    if not config_file.exists():
        print("❌ config.env not found")
        print("Run: cp config.env.example config.env")
        print("Then edit config.env with your API keys")
        return False
    
    # Check for placeholder values
    with open(config_file) as f:
        content = f.read()
        if "your_okx_api_key_here" in content:
            print("⚠️ Please update config.env with your actual OKX API credentials")
        if "YOUR_API_KEY" in content:
            print("⚠️ Please update config.env with your actual API endpoints")
    
    return True

async def main():
    """Main application entry point"""
    print("🚀 Elite Alpha Mirror Bot - Starting Up")
    print("=" * 60)
    print("💰 Target: Transform $1K into $1M via elite wallet mirroring")
    print("⚡ Method: Real-time mempool monitoring + OKX DEX execution")
    print("🧠 Strategy: Mirror proven smart money within seconds")
    print("=" * 60)
    
    # Pre-flight checks
    if not check_dependencies():
        sys.exit(1)
    
    if not check_configuration():
        sys.exit(1)
    
    # Initialize logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Initialize and start the master coordinator
    coordinator = MasterCoordinator()
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        coordinator.is_running = False
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        logger.info("🚀 Starting Elite Alpha Mirror Bot Master Coordinator")
        await coordinator.startup_sequence()
        
    except KeyboardInterrupt:
        logger.info("👋 Shutdown requested by user")
    except Exception as e:
        logger.error(f"❌ Critical error: {e}")
        await coordinator.emergency_shutdown()
        sys.exit(1)
    finally:
        logger.info("Elite Alpha Mirror Bot shutdown complete")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)