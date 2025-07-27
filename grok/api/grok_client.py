import aiohttp
import json
import os
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

class GrokAIClient:
    def __init__(self):
        self.api_key = os.getenv("GROK_API_KEY", "")
        self.base_url = "https://api.x.ai/v1"
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
            
    async def analyze_trade_decision(self, whale_data: Dict, token_data: Dict, market_context: Dict) -> Dict[str, Any]:
        prompt = f"""
Analyze this crypto trading opportunity:

WHALE WALLET:
- Address: {whale_data.get('address', 'N/A')[:12]}...
- Success Rate: {whale_data.get('success_rate', 0):.1%}
- Avg Multiplier: {whale_data.get('avg_multiplier', 0):.1f}x
- Total Trades: {whale_data.get('total_trades', 0)}
- Last Activity: {whale_data.get('last_activity', 'Unknown')}

TOKEN:
- Address: {token_data.get('address', 'N/A')[:12]}...
- Price: ${token_data.get('price', 0):.8f}
- Volume 24h: ${token_data.get('volume_24h', 0):,.0f}
- Liquidity: ${token_data.get('liquidity', 0):,.0f}
- Holders: {token_data.get('holders', 0)}
- Price Change 24h: {token_data.get('price_change_24h', 0):+.1f}%

MARKET:
- ETH Price: ${market_context.get('eth_price', 0):,.0f}
- Gas Price: {market_context.get('gas_price', 0)} gwei
- Market Sentiment: {market_context.get('sentiment', 'Unknown')}
- Total Market Cap: ${market_context.get('total_market_cap', 0):,.0f}

Should I execute this trade? Consider:
1. Whale wallet reliability and track record
2. Token fundamentals and security
3. Market conditions and timing
4. Risk/reward ratio
5. Liquidity and exit strategy

Respond with JSON: {{"execute": true/false, "confidence": 0-100, "reason": "explanation", "position_size": 0.1-0.5, "stop_loss": 0.1-0.9, "take_profit": 2.0-10.0}}
"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "model": "grok-beta",
            "stream": False,
            "temperature": 0.3
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data["choices"][0]["message"]["content"]
                    
                    try:
                        return json.loads(content)
                    except:
                        return {
                            "execute": False,
                            "confidence": 0,
                            "reason": "Failed to parse Grok response",
                            "position_size": 0.1,
                            "stop_loss": 0.8,
                            "take_profit": 3.0
                        }
                else:
                    return {
                        "execute": False,
                        "confidence": 0,
                        "reason": f"Grok API error: {response.status}",
                        "position_size": 0.1,
                        "stop_loss": 0.8,
                        "take_profit": 3.0
                    }
        except Exception as e:
            return {
                "execute": False,
                "confidence": 0,
                "reason": f"Grok API exception: {str(e)}",
                "position_size": 0.1,
                "stop_loss": 0.8,
                "take_profit": 3.0
            }
            
    async def get_market_sentiment(self) -> Dict[str, Any]:
        prompt = """
Analyze current crypto market sentiment based on recent news, social media, and market data. 
Respond with JSON: {"sentiment": "bullish/bearish/neutral", "confidence": 0-100, "key_factors": ["factor1", "factor2"], "risk_level": "low/medium/high"}
"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "model": "grok-beta",
            "stream": False,
            "temperature": 0.5
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data["choices"][0]["message"]["content"]
                    try:
                        return json.loads(content)
                    except:
                        pass
        except:
            pass
            
        return {
            "sentiment": "neutral",
            "confidence": 50,
            "key_factors": ["API unavailable"],
            "risk_level": "medium"
        }
