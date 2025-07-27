"""
Comprehensive Input Validation and Sanitization
"""

import re
import logging
from typing import Union, Optional
from decimal import Decimal
import html

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom validation error"""
    pass

class InputValidator:
    """Comprehensive input validation"""
    
    # Regex patterns
    ETHEREUM_ADDRESS_PATTERN = r'^0x[a-fA-F0-9]{40}$'
    TRANSACTION_HASH_PATTERN = r'^0x[a-fA-F0-9]{64}$'
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    @staticmethod
    def validate_ethereum_address(address: str) -> str:
        """Validate Ethereum address format"""
        if not isinstance(address, str):
            raise ValidationError("Address must be a string")
        
        address = address.strip()
        if not re.match(InputValidator.ETHEREUM_ADDRESS_PATTERN, address):
            raise ValidationError("Invalid Ethereum address format")
        
        return address.lower()
    
    @staticmethod
    def validate_amount(amount: Union[str, float, Decimal], 
                       min_value: float = 0.0, 
                       max_value: float = 1000000.0) -> Decimal:
        """Validate monetary amounts"""
        try:
            amount_decimal = Decimal(str(amount))
        except:
            raise ValidationError("Invalid amount format")
        
        if amount_decimal < Decimal(str(min_value)):
            raise ValidationError(f"Amount must be >= {min_value}")
        
        if amount_decimal > Decimal(str(max_value)):
            raise ValidationError(f"Amount must be <= {max_value}")
        
        return amount_decimal
    
    @staticmethod
    def validate_percentage(percentage: Union[str, float], 
                          min_val: float = 0.0, 
                          max_val: float = 100.0) -> float:
        """Validate percentage values"""
        try:
            pct = float(percentage)
        except:
            raise ValidationError("Invalid percentage format")
        
        if pct < min_val or pct > max_val:
            raise ValidationError(f"Percentage must be between {min_val} and {max_val}")
        
        return pct
    
    @staticmethod
    def sanitize_string(input_str: str, max_length: int = 255) -> str:
        """Sanitize string input"""
        if not isinstance(input_str, str):
            raise ValidationError("Input must be a string")
        
        # Remove null bytes and control characters
        sanitized = ''.join(char for char in input_str if ord(char) >= 32 or char in '\t\n\r')
        
        # HTML escape
        sanitized = html.escape(sanitized)
        
        # Truncate to max length
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized.strip()
    
    @staticmethod
    def validate_api_key(api_key: str) -> str:
        """Validate API key format"""
        if not isinstance(api_key, str):
            raise ValidationError("API key must be a string")
        
        api_key = api_key.strip()
        
        # Check length (most API keys are 20-64 characters)
        if len(api_key) < 20 or len(api_key) > 128:
            raise ValidationError("API key length invalid")
        
        # Check for valid characters (alphanumeric + common symbols)
        if not re.match(r'^[a-zA-Z0-9\-_\.=+/]+$', api_key):
            raise ValidationError("API key contains invalid characters")
        
        return api_key
    
    @staticmethod
    def validate_gas_price(gas_price: Union[str, int]) -> int:
        """Validate gas price"""
        try:
            gas = int(gas_price)
        except:
            raise ValidationError("Invalid gas price format")
        
        # Gas price limits (in wei)
        MIN_GAS = 1_000_000_000  # 1 gwei
        MAX_GAS = 500_000_000_000  # 500 gwei
        
        if gas < MIN_GAS or gas > MAX_GAS:
            raise ValidationError(f"Gas price must be between {MIN_GAS} and {MAX_GAS} wei")
        
        return gas

def validate_trading_params(params: dict) -> dict:
    """Validate trading parameters"""
    validator = InputValidator()
    validated = {}
    
    # Required fields
    required_fields = ['token_address', 'amount', 'slippage']
    for field in required_fields:
        if field not in params:
            raise ValidationError(f"Missing required field: {field}")
    
    # Validate each field
    validated['token_address'] = validator.validate_ethereum_address(params['token_address'])
    validated['amount'] = validator.validate_amount(params['amount'], min_value=1.0, max_value=10000.0)
    validated['slippage'] = validator.validate_percentage(params['slippage'], min_val=0.1, max_val=10.0)
    
    # Optional fields
    if 'gas_price' in params:
        validated['gas_price'] = validator.validate_gas_price(params['gas_price'])
    
    if 'whale_wallet' in params:
        validated['whale_wallet'] = validator.validate_ethereum_address(params['whale_wallet'])
    
    return validated
