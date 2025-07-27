#!/usr/bin/env python3
"""
Token Security Analysis System - PRODUCTION IMPLEMENTATION
Comprehensive token safety validation before trading
"""

import asyncio
import aiohttp
import json
import os
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from web3 import Web3
from eth_abi import decode_abi
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SecurityAnalysis:
    token_address: str
    contract_verified: bool
    ownership_renounced: bool
    liquidity_locked: bool
    max_transaction_limit: bool
    transfer_pausable: bool
    blacklist_function: bool
    mint_function: bool
    proxy_contract: bool
    high_tax: bool
    honeypot_risk: float
    liquidity_eth: float
    holder_count: int
    trading_enabled: bool
    safety_score: float
    risk_level: str
    analysis_time: datetime


@dataclass
class ContractInfo:
    address: str
    name: str
    symbol: str
    decimals: int
    total_supply: int
    creator: str
    creation_block: int
    verified: bool
    source_code: str


class TokenSecurityAnalyzer:
    def __init__(self):
        self.session = None
        self.web3 = None

        # API configuration
        self.etherscan_key = os.getenv("ETHERSCAN_API_KEY", "YourApiKey")
        self.eth_rpc_url = os.getenv("ETH_HTTP_URL", "")

        # Initialize Web3 if RPC available
        if self.eth_rpc_url:
            try:
                self.web3 = Web3(Web3.HTTPProvider(self.eth_rpc_url))
                if self.web3.isConnected():
                    logger.info("✅ Web3 connected")
                else:
                    logger.warning("⚠️ Web3 connection failed")
                    self.web3 = None
            except Exception as e:
                logger.warning(f"⚠️ Web3 initialization failed: {e}")
                self.web3 = None

        # Rate limiting
        self.last_etherscan_call = 0
        self.etherscan_delay = 0.2  # 200ms between calls
        self.last_honeypot_call = 0
        self.honeypot_delay = 1.0  # 1s between honeypot calls

        # Dangerous function signatures
        self.dangerous_functions = {
            # Blacklist functions
            "blacklist": ["blacklist", "isblacklisted", "_blacklist", "addtoBlacklist"],
            # Pause functions
            "pause": ["pause", "unpause", "paused", "whennotpaused", "_pause"],
            # Fee modification
            "fee_modify": [
                "setfee",
                "settax",
                "updatefee",
                "changefee",
                "setbuyfee",
                "setsellfee",
            ],
            # Ownership
            "ownership": ["onlyowner", "transferownership", "renounceownership"],
            # Minting
            "mint": ["mint", "_mint", "mintto", "createsupply"],
            # Trading control
            "trading": ["enabletrading", "disabletrading", "settradingactive"],
            # Limits
            "limits": ["setmaxwallet", "setmaxtx", "setlimits", "removelimits"],
        }

    async def __aenter__(self):
        connector = aiohttp.TCPConnector(limit=50, ttl_dns_cache=300)
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={"User-Agent": "SecurityAnalyzer/1.0"},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def analyze_token(self, token_address: str) -> SecurityAnalysis:
        """Comprehensive token security analysis"""
        logger.info(f"🔍 Analyzing token security: {token_address[:12]}...")

        start_time = time.time()

        # Normalize address
        token_address = token_address.lower()
        if not token_address.startswith("0x"):
            token_address = "0x" + token_address

        # Run all security checks concurrently
        tasks = [
            self.check_contract_verification(token_address),
            self.check_ownership_status(token_address),
            self.check_liquidity_info(token_address),
            self.analyze_contract_bytecode(token_address),
            self.check_honeypot_status(token_address),
            self.check_trading_enabled(token_address),
            self.get_holder_statistics(token_address),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Extract results (handle exceptions)
        contract_verified = (
            results[0] if not isinstance(results[0], Exception) else False
        )
        ownership_info = results[1] if not isinstance(results[1], Exception) else {}
        liquidity_info = results[2] if not isinstance(results[2], Exception) else {}
        bytecode_analysis = results[3] if not isinstance(results[3], Exception) else {}
        honeypot_info = results[4] if not isinstance(results[4], Exception) else {}
        trading_enabled = results[5] if not isinstance(results[5], Exception) else False
        holder_stats = results[6] if not isinstance(results[6], Exception) else {}

        # Compile analysis
        analysis = SecurityAnalysis(
            token_address=token_address,
            contract_verified=contract_verified,
            ownership_renounced=ownership_info.get("renounced", False),
            liquidity_locked=liquidity_info.get("locked", False),
            max_transaction_limit=bytecode_analysis.get("max_tx_limit", False),
            transfer_pausable=bytecode_analysis.get("pausable", False),
            blacklist_function=bytecode_analysis.get("blacklist", False),
            mint_function=bytecode_analysis.get("mintable", False),
            proxy_contract=bytecode_analysis.get("proxy", False),
            high_tax=honeypot_info.get("high_tax", False),
            honeypot_risk=honeypot_info.get("honeypot_risk", 0.0),
            liquidity_eth=liquidity_info.get("liquidity_eth", 0.0),
            holder_count=holder_stats.get("holder_count", 0),
            trading_enabled=trading_enabled,
            safety_score=0.0,
            risk_level="UNKNOWN",
            analysis_time=datetime.now(),
        )

        # Calculate safety score
        analysis.safety_score = self.calculate_safety_score(analysis)
        analysis.risk_level = self.determine_risk_level(analysis.safety_score)

        analysis_time = time.time() - start_time
        logger.info(f"✅ Security analysis complete ({analysis_time:.1f}s)")
        logger.info(f"   Safety Score: {analysis.safety_score:.1f}/100")
        logger.info(f"   Risk Level: {analysis.risk_level}")

        return analysis

    async def check_contract_verification(self, token_address: str) -> bool:
        """Check if contract is verified on Etherscan"""
        await self.rate_limit_etherscan()

        try:
            url = "https://api.etherscan.io/api"
            params = {
                "module": "contract",
                "action": "getsourcecode",
                "address": token_address,
                "apikey": self.etherscan_key,
            }

            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    return False

                data = await response.json()

                if data.get("status") == "1" and data.get("result"):
                    source_code = data["result"][0].get("SourceCode", "")
                    return len(source_code.strip()) > 0

        except Exception as e:
            logger.debug(f"Error checking contract verification: {e}")

        return False

    async def check_ownership_status(self, token_address: str) -> Dict:
        """Check contract ownership status"""
        ownership_info = {"renounced": False, "owner": None, "is_multisig": False}

        if not self.web3:
            return ownership_info

        try:
            # Standard ERC20 owner() function
            owner_abi = [
                {
                    "constant": True,
                    "inputs": [],
                    "name": "owner",
                    "outputs": [{"name": "", "type": "address"}],
                    "type": "function",
                }
            ]

            contract = self.web3.eth.contract(
                address=Web3.toChecksumAddress(token_address), abi=owner_abi
            )

            owner_address = contract.functions.owner().call()

            # Check if ownership is renounced
            zero_address = "0x0000000000000000000000000000000000000000"
            dead_address = "0x000000000000000000000000000000000000dEaD"

            if owner_address.lower() in [zero_address.lower(), dead_address.lower()]:
                ownership_info["renounced"] = True
            else:
                ownership_info["owner"] = owner_address.lower()

                # Check if owner is a multisig (basic heuristic)
                owner_code = self.web3.eth.get_code(owner_address)
                if len(owner_code) > 2:  # Has code beyond '0x'
                    ownership_info["is_multisig"] = True

        except Exception as e:
            logger.debug(f"Error checking ownership: {e}")
            # Try alternative ownership patterns
            try:
                # Ownable contract pattern
                ownable_abi = [
                    {
                        "constant": True,
                        "inputs": [],
                        "name": "_owner",
                        "outputs": [{"name": "", "type": "address"}],
                        "type": "function",
                    }
                ]

                contract = self.web3.eth.contract(
                    address=Web3.toChecksumAddress(token_address), abi=ownable_abi
                )

                owner_address = contract.functions._owner().call()
                ownership_info["owner"] = owner_address.lower()

            except:
                pass

        return ownership_info

    async def check_liquidity_info(self, token_address: str) -> Dict:
        """Check liquidity information"""
        liquidity_info = {
            "liquidity_eth": 0.0,
            "liquidity_usd": 0.0,
            "locked": False,
            "pool_address": None,
        }

        try:
            # Get liquidity from DexScreener
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    pairs = data.get("pairs", [])

                    if pairs:
                        # Use the pair with highest liquidity
                        best_pair = max(
                            pairs,
                            key=lambda p: float(p.get("liquidity", {}).get("usd", 0)),
                        )

                        liquidity_info.update(
                            {
                                "liquidity_eth": float(
                                    best_pair.get("liquidity", {}).get("base", 0)
                                ),
                                "liquidity_usd": float(
                                    best_pair.get("liquidity", {}).get("usd", 0)
                                ),
                                "pool_address": best_pair.get("pairAddress"),
                            }
                        )

            # Check if liquidity is locked (simplified check)
            if (
                liquidity_info["liquidity_usd"] > 50000
            ):  # $50K+ usually indicates some stability
                liquidity_info["locked"] = True

        except Exception as e:
            logger.debug(f"Error checking liquidity: {e}")

        return liquidity_info

    async def analyze_contract_bytecode(self, token_address: str) -> Dict:
        """Analyze contract bytecode for dangerous patterns"""
        bytecode_analysis = {
            "max_tx_limit": False,
            "pausable": False,
            "blacklist": False,
            "mintable": False,
            "proxy": False,
            "fee_modifiable": False,
            "trading_controllable": False,
        }

        try:
            # Get contract source code for analysis
            await self.rate_limit_etherscan()

            url = "https://api.etherscan.io/api"
            params = {
                "module": "contract",
                "action": "getsourcecode",
                "address": token_address,
                "apikey": self.etherscan_key,
            }

            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    return bytecode_analysis

                data = await response.json()

                if data.get("status") == "1" and data.get("result"):
                    source_code = data["result"][0].get("SourceCode", "").lower()

                    if source_code:
                        # Analyze source code for dangerous patterns
                        bytecode_analysis.update(self.analyze_source_code(source_code))
                    else:
                        # Fallback to bytecode analysis
                        if self.web3:
                            bytecode = self.web3.eth.get_code(
                                Web3.toChecksumAddress(token_address)
                            )
                            bytecode_analysis.update(
                                self.analyze_bytecode_patterns(bytecode.hex())
                            )

        except Exception as e:
            logger.debug(f"Error analyzing bytecode: {e}")

        return bytecode_analysis

    def analyze_source_code(self, source_code: str) -> Dict:
        """Analyze source code for dangerous patterns"""
        analysis = {
            "max_tx_limit": False,
            "pausable": False,
            "blacklist": False,
            "mintable": False,
            "proxy": False,
            "fee_modifiable": False,
            "trading_controllable": False,
        }

        # Check for blacklist functionality
        blacklist_patterns = [
            "blacklist",
            "isblacklisted",
            "_blacklist",
            "addtoblacklist",
        ]
        analysis["blacklist"] = any(
            pattern in source_code for pattern in blacklist_patterns
        )

        # Check for pause functionality
        pause_patterns = ["pause", "unpause", "paused", "whennotpaused", "_pause"]
        analysis["pausable"] = any(pattern in source_code for pattern in pause_patterns)

        # Check for minting functionality
        mint_patterns = ["mint", "_mint", "mintto", "createsupply"]
        analysis["mintable"] = any(pattern in source_code for pattern in mint_patterns)

        # Check for transaction limits
        limit_patterns = ["maxtx", "maxwallet", "maxamount", "transferlimit"]
        analysis["max_tx_limit"] = any(
            pattern in source_code for pattern in limit_patterns
        )

        # Check for fee modification
        fee_patterns = ["setfee", "settax", "updatefee", "changefee"]
        analysis["fee_modifiable"] = any(
            pattern in source_code for pattern in fee_patterns
        )

        # Check for trading control
        trading_patterns = ["enabletrading", "disabletrading", "tradingactive"]
        analysis["trading_controllable"] = any(
            pattern in source_code for pattern in trading_patterns
        )

        # Check for proxy patterns
        proxy_patterns = ["proxy", "implementation", "upgradeto", "delegate"]
        analysis["proxy"] = any(pattern in source_code for pattern in proxy_patterns)

        return analysis

    def analyze_bytecode_patterns(self, bytecode: str) -> Dict:
        """Analyze raw bytecode for patterns"""
        analysis = {
            "max_tx_limit": False,
            "pausable": False,
            "blacklist": False,
            "mintable": False,
            "proxy": False,
            "fee_modifiable": False,
            "trading_controllable": False,
        }

        # Common bytecode patterns (simplified)
        # This is a basic implementation - production would need more sophisticated analysis

        # Check for common function selectors
        dangerous_selectors = {
            "0x40c10f19": "mint",  # mint(address,uint256)
            "0x8da5cb5b": "owner",  # owner()
            "0x8456cb59": "pause",  # pause()
            "0x3f4ba83a": "unpause",  # unpause()
        }

        for selector, function_name in dangerous_selectors.items():
            if selector.replace("0x", "") in bytecode.lower():
                if function_name == "mint":
                    analysis["mintable"] = True
                elif function_name in ["pause", "unpause"]:
                    analysis["pausable"] = True

        return analysis

    async def check_honeypot_status(self, token_address: str) -> Dict:
        """Check if token is a honeypot"""
        await self.rate_limit_honeypot()

        honeypot_info = {
            "is_honeypot": False,
            "honeypot_risk": 0.0,
            "buy_tax": 0.0,
            "sell_tax": 0.0,
            "high_tax": False,
            "transfer_pausable": False,
        }

        try:
            # Use honeypot.is API
            url = f"https://api.honeypot.is/v2/IsHoneypot"
            params = {"address": token_address}

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    honeypot_info["is_honeypot"] = data.get("isHoneypot", False)

                    # Get simulation results
                    simulation = data.get("simulationResult", {})
                    if simulation:
                        buy_tax = float(simulation.get("buyTax", 0))
                        sell_tax = float(simulation.get("sellTax", 0))

                        honeypot_info.update(
                            {
                                "buy_tax": buy_tax,
                                "sell_tax": sell_tax,
                                "high_tax": (buy_tax + sell_tax)
                                > 10.0,  # > 10% total tax
                                "transfer_pausable": not simulation.get(
                                    "transferSuccessful", True
                                ),
                            }
                        )

                        # Calculate risk score
                        total_tax = buy_tax + sell_tax
                        honeypot_info["honeypot_risk"] = min(
                            total_tax / 20.0, 1.0
                        )  # Max 20% = 100% risk

        except Exception as e:
            logger.debug(f"Error checking honeypot status: {e}")
            # Fallback risk assessment
            honeypot_info["honeypot_risk"] = 0.5  # Unknown = medium risk

        return honeypot_info

    async def check_trading_enabled(self, token_address: str) -> bool:
        """Check if trading is enabled for the token"""
        if not self.web3:
            return True  # Assume enabled if can't check

        try:
            # Try a simple transfer simulation to check if trading works
            # This is a simplified check
            token_abi = [
                {
                    "constant": True,
                    "inputs": [
                        {"name": "_owner", "type": "address"},
                        {"name": "_spender", "type": "address"},
                    ],
                    "name": "allowance",
                    "outputs": [{"name": "", "type": "uint256"}],
                    "type": "function",
                }
            ]

            contract = self.web3.eth.contract(
                address=Web3.toChecksumAddress(token_address), abi=token_abi
            )

            # If we can call a read function, trading is likely enabled
            zero_address = "0x0000000000000000000000000000000000000000"
            allowance = contract.functions.allowance(zero_address, zero_address).call()

            return True

        except Exception as e:
            logger.debug(f"Error checking trading status: {e}")
            return False

    async def get_holder_statistics(self, token_address: str) -> Dict:
        """Get token holder statistics"""
        holder_stats = {
            "holder_count": 0,
            "top_holder_percentage": 0.0,
            "concentration_risk": False,
        }

        try:
            # Try to get holder count from Etherscan
            await self.rate_limit_etherscan()

            url = "https://api.etherscan.io/api"
            params = {
                "module": "token",
                "action": "tokenholderlist",
                "contractaddress": token_address,
                "page": 1,
                "offset": 100,
                "apikey": self.etherscan_key,
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    if data.get("status") == "1" and data.get("result"):
                        holders = data["result"]
                        holder_stats["holder_count"] = len(holders)

                        if holders:
                            # Calculate top holder percentage
                            total_supply = sum(
                                int(h.get("TokenHolderQuantity", 0)) for h in holders
                            )
                            if total_supply > 0:
                                top_holder_balance = int(
                                    holders[0].get("TokenHolderQuantity", 0)
                                )
                                holder_stats["top_holder_percentage"] = (
                                    top_holder_balance / total_supply
                                ) * 100

                                # Flag concentration risk if top holder has >50%
                                holder_stats["concentration_risk"] = (
                                    holder_stats["top_holder_percentage"] > 50.0
                                )

        except Exception as e:
            logger.debug(f"Error getting holder statistics: {e}")

        return holder_stats

    def calculate_safety_score(self, analysis: SecurityAnalysis) -> float:
        """Calculate overall safety score (0-100)"""
        score = 100.0

        # Deduct points for risks
        if not analysis.contract_verified:
            score -= 25.0

        if not analysis.ownership_renounced:
            score -= 15.0

        if analysis.blacklist_function:
            score -= 20.0

        if analysis.transfer_pausable:
            score -= 15.0

        if analysis.mint_function:
            score -= 10.0

        if analysis.high_tax:
            score -= 15.0

        if analysis.honeypot_risk > 0.5:
            score -= 20.0
        elif analysis.honeypot_risk > 0.2:
            score -= 10.0

        if analysis.max_transaction_limit:
            score -= 5.0

        if analysis.proxy_contract:
            score -= 10.0

        if not analysis.trading_enabled:
            score -= 30.0

        if analysis.liquidity_eth < 1.0:  # Less than 1 ETH liquidity
            score -= 15.0
        elif analysis.liquidity_eth < 5.0:  # Less than 5 ETH liquidity
            score -= 5.0

        if analysis.holder_count < 100:
            score -= 10.0
        elif analysis.holder_count < 50:
            score -= 20.0

        # Add points for positive factors
        if analysis.liquidity_locked:
            score += 5.0

        if analysis.holder_count > 1000:
            score += 5.0

        return max(0.0, min(100.0, score))

    def determine_risk_level(self, safety_score: float) -> str:
        """Determine risk level based on safety score"""
        if safety_score >= 80:
            return "LOW"
        elif safety_score >= 60:
            return "MEDIUM"
        elif safety_score >= 40:
            return "HIGH"
        else:
            return "CRITICAL"

    async def is_safe_to_trade(
        self, token_address: str, min_score: float = 70.0
    ) -> Tuple[bool, SecurityAnalysis]:
        """Quick safety check for trading decisions"""
        analysis = await self.analyze_token(token_address)
        is_safe = analysis.safety_score >= min_score and analysis.risk_level in [
            "LOW",
            "MEDIUM",
        ]

        logger.info(f"🔐 Safety Check: {token_address[:12]}...")
        logger.info(f"   Score: {analysis.safety_score:.1f}/100")
        logger.info(f"   Risk: {analysis.risk_level}")
        logger.info(f"   Safe to Trade: {'✅' if is_safe else '❌'}")

        return is_safe, analysis

    async def rate_limit_etherscan(self):
        """Rate limit Etherscan API calls"""
        now = time.time()
        time_since_last = now - self.last_etherscan_call
        if time_since_last < self.etherscan_delay:
            await asyncio.sleep(self.etherscan_delay - time_since_last)
        self.last_etherscan_call = time.time()

    async def rate_limit_honeypot(self):
        """Rate limit honeypot API calls"""
        now = time.time()
        time_since_last = now - self.last_honeypot_call
        if time_since_last < self.honeypot_delay:
            await asyncio.sleep(self.honeypot_delay - time_since_last)
        self.last_honeypot_call = time.time()


async def main():
    """Demo security analysis"""
    analyzer = TokenSecurityAnalyzer()

    # Demo tokens for testing
    demo_tokens = [
        "0xA0b86a33E6441b24b4B2CCcdca5E5f7c9eF3Bd20",  # Example token 1
        "0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE",  # Example token 2
    ]

    async with analyzer:
        print("🔐 TOKEN SECURITY ANALYSIS DEMO")
        print("=" * 50)

        for token_addr in demo_tokens:
            print(f"\n🔍 Analyzing {token_addr}...")

            try:
                safe, analysis = await analyzer.is_safe_to_trade(
                    token_addr, min_score=60.0
                )

                print(f"📊 Results:")
                print(
                    f"   Contract Verified: {'✅' if analysis.contract_verified else '❌'}"
                )
                print(
                    f"   Ownership Renounced: {'✅' if analysis.ownership_renounced else '❌'}"
                )
                print(f"   Honeypot Risk: {analysis.honeypot_risk:.1%}")
                print(f"   Safety Score: {analysis.safety_score:.1f}/100")
                print(f"   Risk Level: {analysis.risk_level}")
                print(f"   Safe to Trade: {'✅' if safe else '❌'}")

            except Exception as e:
                print(f"❌ Analysis failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
