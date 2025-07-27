import asyncio
import json
import aiohttp
from typing import Dict, List, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import sqlite3
import aiosqlite


@dataclass
class WalletMetrics:
    address: str
    total_trades: int
    successful_trades: int
    avg_hold_time: float
    avg_multiplier: float
    max_multiplier: float
    total_volume: float
    last_active: datetime
    deployment_count: int
    snipe_success_rate: float
    risk_score: float


@dataclass
class TokenDeploy:
    deployer: str
    token_address: str
    timestamp: datetime
    initial_liquidity: float
    max_price_multiplier: float
    current_multiplier: float


class EliteWalletTracker:
    def __init__(self, db_path: str = "wallets.db"):
        self.db_path = db_path
        self.session: aiohttp.ClientSession = None
        self.tracked_wallets: Set[str] = set()
        self.elite_threshold = 50.0

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        await self.init_database()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def init_database(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS wallet_metrics (
                    address TEXT PRIMARY KEY,
                    total_trades INTEGER,
                    successful_trades INTEGER,
                    avg_hold_time REAL,
                    avg_multiplier REAL,
                    max_multiplier REAL,
                    total_volume REAL,
                    last_active TEXT,
                    deployment_count INTEGER,
                    snipe_success_rate REAL,
                    risk_score REAL
                )
            """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS token_deploys (
                    deployer TEXT,
                    token_address TEXT,
                    timestamp TEXT,
                    initial_liquidity REAL,
                    max_price_multiplier REAL,
                    current_multiplier REAL,
                    PRIMARY KEY (deployer, token_address)
                )
            """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS wallet_trades (
                    wallet TEXT,
                    token_address TEXT,
                    action TEXT,
                    amount REAL,
                    price REAL,
                    timestamp TEXT,
                    tx_hash TEXT,
                    multiplier REAL
                )
            """
            )

            await db.commit()

    async def discover_elite_wallets(self) -> List[str]:
        successful_tokens = await self._get_100x_tokens_last_30_days()
        elite_wallets = set()

        for token_data in successful_tokens:
            deployer = await self._get_token_deployer(token_data["address"])
            if deployer:
                elite_wallets.add(deployer)

            early_buyers = await self._get_early_buyers(
                token_data["address"], token_data["deploy_time"]
            )
            elite_wallets.update(early_buyers)

        filtered_elites = []
        for wallet in elite_wallets:
            metrics = await self.analyze_wallet_performance(wallet)
            if metrics.avg_multiplier > self.elite_threshold:
                filtered_elites.append(wallet)
                await self.save_wallet_metrics(metrics)

        return filtered_elites

    async def _get_100x_tokens_last_30_days(self) -> List[Dict]:
        cutoff_date = datetime.now() - timedelta(days=30)

        try:
            url = "https://api.dexscreener.com/latest/dex/tokens"
            params = {
                "chainId": "ethereum",
                "limit": 100,
                "sort": "priceChangeH24",
                "order": "desc",
            }

            async with self.session.get(url, params=params) as response:
                data = await response.json()

                high_performers = []
                for token in data.get("pairs", []):
                    price_change = float(token.get("priceChange", {}).get("h24", 0))
                    if price_change > 9900:
                        high_performers.append(
                            {
                                "address": token["baseToken"]["address"],
                                "deploy_time": datetime.fromisoformat(
                                    token["pairCreatedAt"].replace("Z", "+00:00")
                                ),
                                "multiplier": price_change / 100 + 1,
                            }
                        )

                return high_performers

        except Exception:
            return []

    async def _get_token_deployer(self, token_address: str) -> str:
        try:
            url = f"https://api.etherscan.io/api"
            params = {
                "module": "account",
                "action": "txlist",
                "address": token_address,
                "startblock": 0,
                "endblock": 99999999,
                "page": 1,
                "offset": 1,
                "sort": "asc",
                "apikey": "YourEtherscanAPIKey",
            }

            async with self.session.get(url, params=params) as response:
                data = await response.json()

                if data["result"]:
                    return data["result"][0]["from"]

        except Exception:
            pass

        return None

    async def _get_early_buyers(
        self, token_address: str, deploy_time: datetime, window_minutes: int = 60
    ) -> List[str]:
        try:
            end_time = deploy_time + timedelta(minutes=window_minutes)

            url = f"https://api.etherscan.io/api"
            params = {
                "module": "account",
                "action": "tokentx",
                "contractaddress": token_address,
                "startblock": 0,
                "endblock": 99999999,
                "page": 1,
                "offset": 100,
                "sort": "asc",
                "apikey": "YourEtherscanAPIKey",
            }

            async with self.session.get(url, params=params) as response:
                data = await response.json()

                early_buyers = []
                for tx in data.get("result", []):
                    tx_time = datetime.fromtimestamp(int(tx["timeStamp"]))
                    if (
                        deploy_time <= tx_time <= end_time
                        and tx["to"] != "0x0000000000000000000000000000000000000000"
                    ):
                        early_buyers.append(tx["to"])

                return list(set(early_buyers))

        except Exception:
            return []

    async def analyze_wallet_performance(self, wallet_address: str) -> WalletMetrics:
        trades = await self._get_wallet_trades(wallet_address)

        if not trades:
            return WalletMetrics(
                address=wallet_address,
                total_trades=0,
                successful_trades=0,
                avg_hold_time=0,
                avg_multiplier=0,
                max_multiplier=0,
                total_volume=0,
                last_active=datetime.now(),
                deployment_count=0,
                snipe_success_rate=0,
                risk_score=100,
            )

        successful_trades = [t for t in trades if t.get("multiplier", 0) > 1.0]
        multipliers = [t.get("multiplier", 0) for t in trades if t.get("multiplier")]

        deployments = await self._count_deployments(wallet_address)

        return WalletMetrics(
            address=wallet_address,
            total_trades=len(trades),
            successful_trades=len(successful_trades),
            avg_hold_time=self._calculate_avg_hold_time(trades),
            avg_multiplier=sum(multipliers) / len(multipliers) if multipliers else 0,
            max_multiplier=max(multipliers) if multipliers else 0,
            total_volume=sum(t.get("amount", 0) for t in trades),
            last_active=max(datetime.fromisoformat(t["timestamp"]) for t in trades)
            if trades
            else datetime.now(),
            deployment_count=deployments,
            snipe_success_rate=len(successful_trades) / len(trades) if trades else 0,
            risk_score=self._calculate_risk_score(trades),
        )

    async def _get_wallet_trades(self, wallet_address: str) -> List[Dict]:
        try:
            url = f"https://api.etherscan.io/api"
            params = {
                "module": "account",
                "action": "txlist",
                "address": wallet_address,
                "startblock": 0,
                "endblock": 99999999,
                "page": 1,
                "offset": 1000,
                "sort": "desc",
                "apikey": "YourEtherscanAPIKey",
            }

            async with self.session.get(url, params=params) as response:
                data = await response.json()

                return data.get("result", [])

        except Exception:
            return []

    def _calculate_avg_hold_time(self, trades: List[Dict]) -> float:
        return 3600.0

    async def _count_deployments(self, wallet_address: str) -> int:
        return 0

    def _calculate_risk_score(self, trades: List[Dict]) -> float:
        if not trades:
            return 100.0

        recent_activity = len([t for t in trades[:10]])
        consistency = min(50.0, recent_activity * 5)

        return max(0.0, 100.0 - consistency)

    async def save_wallet_metrics(self, metrics: WalletMetrics):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO wallet_metrics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    metrics.address,
                    metrics.total_trades,
                    metrics.successful_trades,
                    metrics.avg_hold_time,
                    metrics.avg_multiplier,
                    metrics.max_multiplier,
                    metrics.total_volume,
                    metrics.last_active.isoformat(),
                    metrics.deployment_count,
                    metrics.snipe_success_rate,
                    metrics.risk_score,
                ),
            )
            await db.commit()

    async def export_alpha_wallets(self, output_file: str = "data/alpha_wallets.json"):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT * FROM wallet_metrics 
                WHERE avg_multiplier > ? AND snipe_success_rate > 0.6
                ORDER BY avg_multiplier DESC
                LIMIT 100
            """,
                (self.elite_threshold,),
            )

            rows = await cursor.fetchall()

            wallets = []
            for row in rows:
                wallets.append(
                    {
                        "address": row[0],
                        "avg_multiplier": row[4],
                        "win_rate": row[9],
                        "last_active": int(datetime.fromisoformat(row[7]).timestamp()),
                        "deploy_count": row[8],
                        "snipe_success": row[1],
                        "risk_score": row[10],
                    }
                )

            with open(output_file, "w") as f:
                json.dump(wallets, f, indent=2)


async def main():
    tracker = EliteWalletTracker()
    async with tracker:
        elite_wallets = await tracker.discover_elite_wallets()
        print(f"Found {len(elite_wallets)} elite wallets")
        await tracker.export_alpha_wallets()


if __name__ == "__main__":
    asyncio.run(main())
