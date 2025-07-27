"""Logging utilities for Elite Alpha Mirror Bot"""

import logging
import logging.handlers
import os
from datetime import datetime
from typing import Optional


def setup_logging(
    level: str = "INFO",
    log_dir: str = "logs",
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> None:
    """Setup comprehensive logging"""

    # Create log directory
    os.makedirs(log_dir, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler
    if log_file is None:
        log_file = f"bot_{datetime.now().strftime('%Y%m%d')}.log"

    file_path = os.path.join(log_dir, log_file)
    file_handler = logging.handlers.RotatingFileHandler(
        file_path, maxBytes=max_bytes, backupCount=backup_count
    )
    file_handler.setLevel(getattr(logging, level.upper()))
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Error file handler
    error_file_path = os.path.join(log_dir, "errors.log")
    error_handler = logging.handlers.RotatingFileHandler(
        error_file_path, maxBytes=max_bytes, backupCount=backup_count
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    logging.info(f"Logging initialized - Level: {level}, File: {file_path}")


class TradeLogger:
    """Specialized logger for trading activities"""

    def __init__(self, log_dir: str = "logs/trades"):
        os.makedirs(log_dir, exist_ok=True)
        self.logger = logging.getLogger("trades")

        # Trade file handler
        trade_file = os.path.join(log_dir, "trades.log")
        handler = logging.handlers.RotatingFileHandler(
            trade_file, maxBytes=10 * 1024 * 1024, backupCount=10
        )

        formatter = logging.Formatter("%(asctime)s - TRADE - %(message)s")
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def log_trade(self, action: str, token: str, amount: float, price: float, **kwargs):
        """Log a trade action"""
        trade_data = {
            "action": action,
            "token": token,
            "amount": amount,
            "price": price,
            **kwargs,
        }
        self.logger.info(f"{action} - {trade_data}")
