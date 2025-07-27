import asyncio
import websockets
import aiohttp
import json
import time
from datetime import datetime
from typing import Dict, Set, List
from dataclasses import dataclass
import logging


@dataclass
class LiveTrade:
    whale_wallet: str
    token_address: str
    amount_eth: float
    gas_price: int
    timestamp: float
    tx_hash: str
    confidence: float


class WebSocketEngine:
    def __init__(self):
        self.session = None
        self.elite_wallets = set()
        self.pending_trades = asyncio.Queue(maxsize=10000)
        self.stats = {"processed": 0, "detected": 0, "executed": 0}
        self.ml_brain = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        from ml_brain import MLBrain

        self.ml_brain = MLBrain()
        await self.ml_brain.__aenter__()
        await self.load_elite_wallets()
        return self

    async def __aexit__(self, *args):
        if self.ml_brain:
            await self.ml_brain.__aexit__()
        if self.session:
            await self.session.close()

    async def load_elite_wallets(self):
        try:
            with open("data/elite_wallets.json", "r") as f:
                wallets = json.load(f)
                self.elite_wallets = {w["address"].lower() for w in wallets}
        except:
            self.elite_wallets = {
                "0xae2fc483527b8ef99eb5d9b44875f005ba1fae13",
                "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b",
            }

    async def start_realtime_monitoring(self):
        tasks = [
            self.websocket_listener(),
            self.trade_processor(),
            self.performance_monitor(),
        ]
        await asyncio.gather(*tasks)

    async def websocket_listener(self):
        ws_url = (
            "wss://eth-mainnet.ws.alchemyapi.io/v2/alcht_oZ7wU7JpIoZejlOWUcMFOpNsIlLDsX"
        )

        while True:
            try:
                async with websockets.connect(ws_url) as ws:
                    await ws.send(
                        json.dumps(
                            {
                                "id": 1,
                                "method": "eth_subscribe",
                                "params": ["newPendingTransactions"],
                            }
                        )
                    )

                    async for message in ws:
                        await self.process_transaction(json.loads(message))
            except Exception as e:
                await asyncio.sleep(1)

    async def process_transaction(self, data):
        if "params" not in data or "result" not in data["params"]:
            return

        tx_hash = data["params"]["result"]
        tx_data = await self.get_transaction_data(tx_hash)

        if not tx_data:
            return

        self.stats["processed"] += 1

        from_addr = tx_data.get("from", "").lower()
        if from_addr in self.elite_wallets:
            trade = await self.analyze_elite_transaction(tx_data)
            if trade:
                await self.pending_trades.put(trade)
                self.stats["detected"] += 1

    async def get_transaction_data(self, tx_hash):
        try:
            url = "https://eth-mainnet.alchemyapi.io/v2/alcht_oZ7wU7JpIoZejlOWUcMFOpNsIlLDsX"
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_getTransactionByHash",
                "params": [tx_hash],
                "id": 1,
            }
            async with self.session.post(url, json=payload) as response:
                result = await response.json()
                return result.get("result")
        except:
            return None

    async def analyze_elite_transaction(self, tx_data):
        to_addr = tx_data.get("to", "").lower()
        input_data = tx_data.get("input", "")
        value = int(tx_data.get("value", "0x0"), 16)

        dex_routers = {
            "0x7a250d5630b4cf539739df2c5dacb4c659f2488d",
            "0xe592427a0aece92de3edee1f18e0157c05861564",
            "0x1111111254eeb25477b68fb85ed929f73a960582",
        }

        if to_addr in dex_routers and value > 0:
            token_address = self.extract_token_from_input(input_data)
            if token_address:
                return LiveTrade(
                    whale_wallet=tx_data["from"],
                    token_address=token_address,
                    amount_eth=value / 1e18,
                    gas_price=int(tx_data.get("gasPrice", "0x0"), 16),
                    timestamp=time.time(),
                    tx_hash=tx_data.get("hash", ""),
                    confidence=0.8,
                )
        return None

    def extract_token_from_input(self, input_data):
        if len(input_data) < 200:
            return None
        try:
            return "0x" + input_data[138:178]
        except:
            return None

    async def trade_processor(self):
        while True:
            try:
                trade = await self.pending_trades.get()
                await self.execute_trade_simulation(trade)
                self.stats["executed"] += 1
            except Exception as e:
                await asyncio.sleep(0.01)

    async def execute_trade_simulation(self, trade):
        signal = await self.ml_brain.generate_trade_signal(
            trade.token_address,
            0.001,
            1000000,
            {"volatility": 0.05, "volume_24h": 500000},
        )

        position_size = min(trade.amount_eth * 1000, 500)

        print(f"⚡ LIVE TRADE SIMULATION")
        print(f"   Whale: {trade.whale_wallet[:12]}...")
        print(f"   Token: {trade.token_address[:12]}...")
        print(f"   Position: ${position_size:.0f}")
        print(f"   ML Score: {signal.ml_score:.3f}")
        print(f"   Confidence: {signal.confidence:.3f}")
        print(f"   Action: {signal.action}")
        print(f"   Timestamp: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        print()

    async def performance_monitor(self):
        start_time = time.time()
        while True:
            await asyncio.sleep(30)
            runtime = time.time() - start_time
            tps = self.stats["processed"] / max(runtime, 1)

            print(
                f"📊 PERFORMANCE: {runtime:.0f}s | TPS: {tps:.1f} | Detected: {self.stats['detected']} | Executed: {self.stats['executed']}"
            )
