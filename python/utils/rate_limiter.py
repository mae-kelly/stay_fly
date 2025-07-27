"""
Rate Limiting and DDoS Protection
"""

import time
import asyncio
from typing import Dict, Optional
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """Token bucket rate limiter"""
    
    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = defaultdict(deque)
        self.lock = asyncio.Lock()
    
    async def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed"""
        async with self.lock:
            now = time.time()
            request_times = self.requests[identifier]
            
            # Remove old requests outside time window
            while request_times and request_times[0] <= now - self.time_window:
                request_times.popleft()
            
            # Check if under limit
            if len(request_times) < self.max_requests:
                request_times.append(now)
                return True
            
            return False
    
    async def get_reset_time(self, identifier: str) -> Optional[float]:
        """Get time until rate limit resets"""
        async with self.lock:
            request_times = self.requests[identifier]
            if not request_times:
                return None
            
            oldest_request = request_times[0]
            return oldest_request + self.time_window - time.time()

class APIRateLimiter:
    """API-specific rate limiter"""
    
    def __init__(self):
        self.limiters = {
            'etherscan': RateLimiter(5, 1),     # 5 requests per second
            'okx': RateLimiter(10, 1),          # 10 requests per second
            'dexscreener': RateLimiter(2, 1),   # 2 requests per second
            'general': RateLimiter(100, 60),    # 100 requests per minute
        }
    
    async def check_limit(self, api_name: str, identifier: str = 'default') -> bool:
        """Check if API call is allowed"""
        if api_name not in self.limiters:
            api_name = 'general'
        
        return await self.limiters[api_name].is_allowed(identifier)
    
    async def wait_for_reset(self, api_name: str, identifier: str = 'default'):
        """Wait until rate limit resets"""
        if api_name not in self.limiters:
            api_name = 'general'
        
        reset_time = await self.limiters[api_name].get_reset_time(identifier)
        if reset_time and reset_time > 0:
            logger.info(f"Rate limited for {api_name}, waiting {reset_time:.2f}s")
            await asyncio.sleep(reset_time)

# Global rate limiter instance
rate_limiter = APIRateLimiter()
