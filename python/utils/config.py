"""Configuration management for Elite Alpha Mirror Bot"""

import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class TradingConfig:
    initial_capital: float = 1000.0
    max_position_size: float = 0.3
    max_positions: int = 5
    min_liquidity: float = 50000.0
    max_slippage: float = 0.05
    stop_loss_percent: float = 0.8
    take_profit_percent: float = 5.0

@dataclass
class APIConfig:
    eth_http_url: str = ""
    eth_ws_url: str = ""
    etherscan_api_key: str = ""
    okx_api_key: str = ""
    okx_secret_key: str = ""
    okx_passphrase: str = ""
    discord_webhook: str = ""

def load_config(config_path: str = "config.env") -> Dict[str, str]:
    """Load configuration from environment file"""
    config = {}
    
    try:
        with open(config_path, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
                    os.environ[key.strip()] = value.strip()
    except FileNotFoundError:
        logging.warning(f"Config file {config_path} not found")
    
    # Load from environment variables
    for key, value in os.environ.items():
        if key.startswith(('ETH_', 'OKX_', 'DISCORD_', 'WALLET_', 'ETHERSCAN_')):
            config[key] = value
    
    return config

def get_trading_config() -> TradingConfig:
    """Get trading configuration"""
    return TradingConfig(
        initial_capital=float(os.getenv('INITIAL_CAPITAL', '1000.0')),
        max_position_size=float(os.getenv('MAX_POSITION_SIZE', '0.3')),
        max_positions=int(os.getenv('MAX_POSITIONS', '5')),
        min_liquidity=float(os.getenv('MIN_LIQUIDITY', '50000.0')),
        max_slippage=float(os.getenv('MAX_SLIPPAGE', '0.05')),
        stop_loss_percent=float(os.getenv('STOP_LOSS_PERCENT', '0.8')),
        take_profit_percent=float(os.getenv('TAKE_PROFIT_PERCENT', '5.0'))
    )

def get_api_config() -> APIConfig:
    """Get API configuration"""
    return APIConfig(
        eth_http_url=os.getenv('ETH_HTTP_URL', ''),
        eth_ws_url=os.getenv('ETH_WS_URL', ''),
        etherscan_api_key=os.getenv('ETHERSCAN_API_KEY', ''),
        okx_api_key=os.getenv('OKX_API_KEY', ''),
        okx_secret_key=os.getenv('OKX_SECRET_KEY', ''),
        okx_passphrase=os.getenv('OKX_PASSPHRASE', ''),
        discord_webhook=os.getenv('DISCORD_WEBHOOK', '')
    )
