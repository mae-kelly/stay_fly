import asyncio
import aiohttp
import json
import time
import os
import websockets
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Set, List, Optional
import logging

@dataclass
class FastTrade:
    whale_wallet: str
    token_address: str
    amount_eth: float
    gas_price: int
    detected_at: float
    tx_hash: str
    method_signature: str
    confidence_score: float

class FixedMempoolScanner:
    def __init__(self):
        self.eth_ws_url = os.getenv("ETH_WS_URL", "")
        self.eth_http_url = os.getenv("ETH_HTTP_URL", "")
        self.elite_wallets = set()
        self.pending_trades = {}
        
        self.dex_routers = {
            "0x7a250d5630b4cf539739df2c5dacb4c659f2488d",
            "0xe592427a0aece92de3edee1f18e0157c05861564", 
            "0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f",
            "0x1111111254eeb25477b68fb85ed929f73a960582",
        }
        
        self.session = None
        self.is_running = False
        
    async def load_elite_wallets(self):
        try:
            with open("data/real_elite_wallets.json", "r") as f:
                wallets = json.load(f)
                for wallet in wallets:
                    self.elite_wallets.add(wallet["address"].lower())
            logging.info(f"Loaded {len(self.elite_wallets)} elite wallets")
        except FileNotFoundError:
            demo_wallets = {
                "0xae2fc483527b8ef99eb5d9b44875f005ba1fae13",
                "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b",
                "0x1234567890123456789012345678901234567890",
            }
            self.elite_wallets = demo_wallets
            logging.info(f"Using {len(demo_wallets)} demo wallets")
    
    async def start_ultra_fast_monitoring(self):
        self.is_running = True
        connector = aiohttp.TCPConnector(limit=100, ttl_dns_cache=300)
        timeout = aiohttp.ClientTimeout(total=10)
        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        
        await self.load_elite_wallets()
        
        try:
            if self.eth_ws_url and not self.eth_ws_url.startswith("YOUR_"):
                await self.run_live_monitoring()
            else:
                await self.run_simulation_mode()
        finally:
            if self.session:
                await self.session.close()
    
    async def run_simulation_mode(self):
        logging.info("Running in simulation mode")
        
        for i in range(10):
            import random
            whale_addr = random.choice(list(self.elite_wallets))
            
            trade = FastTrade(
                whale_wallet=whale_addr,
                token_address=f"0x{'a' * 40}",
                amount_eth=random.uniform(0.1, 2.0),
                gas_price=random.randint(20, 50),
                detected_at=time.time(),
                tx_hash=f"0x{'b' * 64}",
                method_signature="swapExactETHForTokens",
                confidence_score=0.8,
            )
            
            self.pending_trades[f"sim_{i}"] = trade
            logging.info(f"Simulated trade: {whale_addr[:10]}... trading {trade.token_address[:10]}...")
            
            await asyncio.sleep(2)
    
    async def run_live_monitoring(self):
        logging.info("Starting live WebSocket monitoring")
        
        retry_count = 0
        max_retries = 5
        
        while retry_count < max_retries and self.is_running:
            try:
                async with websockets.connect(self.eth_ws_url) as websocket:
                    subscribe_msg = json.dumps({
                        "id": 1,
                        "method": "eth_subscribe", 
                        "params": ["newPendingTransactions"]
                    })
                    
                    await websocket.send(subscribe_msg)
                    logging.info("Subscribed to pending transactions")
                    
                    async for message in websocket:
                        if not self.is_running:
                            break
                            
                        try:
                            data = json.loads(message)
                            if "params" in data and "result" in data["params"]:
                                tx_hash = data["params"]["result"]
                                await self.process_transaction(tx_hash)
                        except Exception as e:
                            logging.debug(f"Error processing message: {e}")
                            
            except Exception as e:
                retry_count += 1
                logging.warning(f"WebSocket error (attempt {retry_count}/{max_retries}): {e}")
                await asyncio.sleep(2 ** retry_count)
    
    async def process_transaction(self, tx_hash: str):
        try:
            tx_data = await self.get_transaction_data(tx_hash)
            if not tx_data:
                return
                
            from_addr = tx_data.get("from", "").lower()
            if from_addr in self.elite_wallets:
                trade = await self.analyze_transaction(tx_data)
                if trade:
                    self.pending_trades[tx_hash] = trade
                    logging.info(f"Elite trade detected: {from_addr[:10]}... -> {trade.token_address[:10]}...")
                    
        except Exception as e:
            logging.debug(f"Error processing transaction {tx_hash}: {e}")
    
    async def get_transaction_data(self, tx_hash: str):
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_getTransactionByHash",
                "params": [tx_hash],
                "id": 1
            }
            
            async with self.session.post(self.eth_http_url, json=payload) as response:
                result = await response.json()
                return result.get("result")
        except Exception as e:
            logging.debug(f"Error getting transaction data: {e}")
            return None
    
    async def analyze_transaction(self, tx_data):
        try:
            to_addr = tx_data.get("to", "").lower()
            if to_addr not in self.dex_routers:
                return None
                
            input_data = tx_data.get("input", "")
            if len(input_data) < 10:
                return None
                
            method_id = input_data[2:10]
            value = int(tx_data.get("value", "0x0"), 16)
            
            if method_id in ["7ff36ab5", "18cbafe5"] and value > 0:
                from core.abi_decoder import decoder
                token_address = decoder.extract_token_from_swap_data(bytes.fromhex(input_data[2:]))
                
                if token_address:
                    return FastTrade(
                        whale_wallet=tx_data["from"],
                        token_address=token_address,
                        amount_eth=value / 1e18,
                        gas_price=int(tx_data.get("gasPrice", "0x0"), 16),
                        detected_at=time.time(),
                        tx_hash=tx_data.get("hash", ""),
                        method_signature=method_id,
                        confidence_score=0.8,
                    )
        except Exception as e:
            logging.debug(f"Error analyzing transaction: {e}")
            
        return None
    
    async def stop(self):
        self.is_running = False
