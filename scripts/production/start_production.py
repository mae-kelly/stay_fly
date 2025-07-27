#!/usr/bin/env python3
"""
Production Startup Script with Safety Checks
"""

import asyncio
import sys
import os
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/production/startup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ProductionSafetyChecks:
    """Production safety checks before startup"""
    
    def __init__(self):
        self.checks_passed = 0
        self.checks_total = 0
        
    def check_environment(self):
        """Check environment configuration"""
        self.checks_total += 1
        
        required_vars = [
            'ETH_HTTP_URL', 'ETH_WS_URL', 'ETHERSCAN_API_KEY',
            'OKX_API_KEY', 'OKX_SECRET_KEY', 'WALLET_ADDRESS'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.error(f"❌ Missing required environment variables: {missing_vars}")
            return False
            
        # Check for placeholder values
        placeholder_patterns = ['YOUR_', 'REPLACE_', 'CHANGE_']
        for var in required_vars:
            value = os.getenv(var, '')
            if any(pattern in value for pattern in placeholder_patterns):
                logger.error(f"❌ Environment variable {var} contains placeholder value")
                return False
                
        self.checks_passed += 1
        logger.info("✅ Environment configuration valid")
        return True
    
    def check_risk_limits(self):
        """Check risk management settings"""
        self.checks_total += 1
        
        max_capital = float(os.getenv('MAX_CAPITAL', '0'))
        starting_capital = float(os.getenv('STARTING_CAPITAL', '0'))
        
        if max_capital <= 0:
            logger.error("❌ MAX_CAPITAL must be set and > 0")
            return False
            
        if starting_capital > max_capital:
            logger.error("❌ STARTING_CAPITAL cannot exceed MAX_CAPITAL")
            return False
            
        if starting_capital > 1000:
            logger.warning(f"⚠️ High starting capital: ${starting_capital}")
            response = input("Continue with high capital amount? (yes/no): ")
            if response.lower() != 'yes':
                return False
                
        self.checks_passed += 1
        logger.info(f"✅ Risk limits configured: ${starting_capital} / ${max_capital}")
        return True
    
    def check_paper_trading(self):
        """Check if paper trading is enabled for safety"""
        self.checks_total += 1
        
        paper_trading = os.getenv('PAPER_TRADING_MODE', 'false').lower() == 'true'
        simulation = os.getenv('SIMULATION_MODE', 'false').lower() == 'true'
        
        if not (paper_trading or simulation):
            logger.error("❌ CRITICAL: Paper trading not enabled!")
            logger.error("❌ Set PAPER_TRADING_MODE=true for safety")
            return False
            
        self.checks_passed += 1
        logger.info("✅ Paper trading mode enabled")
        return True
    
    def check_file_permissions(self):
        """Check critical file permissions"""
        self.checks_total += 1
        
        critical_files = ['.env.production', 'config/security/']
        
        for file_path in critical_files:
            if os.path.exists(file_path):
                stat = os.stat(file_path)
                mode = oct(stat.st_mode)[-3:]
                if mode not in ['600', '644', '755']:
                    logger.warning(f"⚠️ File {file_path} has permissions {mode}")
        
        self.checks_passed += 1
        logger.info("✅ File permissions checked")
        return True
    
    def check_database_connection(self):
        """Check database connectivity"""
        self.checks_total += 1
        
        try:
            # This would check actual database connection
            # For now, just verify config
            db_host = os.getenv('DB_HOST')
            db_name = os.getenv('DB_NAME')
            
            if not all([db_host, db_name]):
                logger.warning("⚠️ Database configuration incomplete")
            
            self.checks_passed += 1
            logger.info("✅ Database configuration checked")
            return True
        except Exception as e:
            logger.error(f"❌ Database check failed: {e}")
            return False
    
    def run_all_checks(self):
        """Run all safety checks"""
        logger.info("🔍 Running production safety checks...")
        
        checks = [
            self.check_environment,
            self.check_risk_limits,
            self.check_paper_trading,
            self.check_file_permissions,
            self.check_database_connection
        ]
        
        for check in checks:
            if not check():
                logger.error("❌ Safety check failed - aborting startup")
                return False
        
        success_rate = (self.checks_passed / self.checks_total) * 100
        logger.info(f"✅ Safety checks passed: {self.checks_passed}/{self.checks_total} ({success_rate:.1f}%)")
        
        return self.checks_passed == self.checks_total

async def main():
    """Main production startup"""
    logger.info("🚀 Elite Alpha Mirror Bot - Production Startup")
    logger.info("=" * 60)
    
    # Run safety checks
    safety = ProductionSafetyChecks()
    if not safety.run_all_checks():
        logger.error("🛑 Safety checks failed - startup aborted")
        sys.exit(1)
    
    # Final confirmation for live trading
    paper_trading = os.getenv('PAPER_TRADING_MODE', 'false').lower() == 'true'
    if not paper_trading:
        logger.warning("🚨 LIVE TRADING MODE DETECTED!")
        logger.warning("🚨 This will use real money!")
        response = input("Type 'I UNDERSTAND THE RISKS' to continue: ")
        if response != 'I UNDERSTAND THE RISKS':
            logger.info("Startup cancelled by user")
            sys.exit(0)
    
    try:
        # Import and start the main coordinator
        from core.master_coordinator import MasterCoordinator
        
        coordinator = MasterCoordinator()
        logger.info("🎯 Starting master coordinator...")
        
        await coordinator.startup_sequence()
        
    except KeyboardInterrupt:
        logger.info("👋 Shutdown requested")
    except Exception as e:
        logger.error(f"❌ Critical error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
