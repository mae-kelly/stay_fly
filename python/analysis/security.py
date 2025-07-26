import asyncio
import aiohttp
import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from web3 import Web3
from eth_abi import decode_abi

@dataclass
class SecurityAnalysis:
    honeypot_risk: float
    ownership_renounced: bool
    liquidity_locked: bool
    max_transaction_limit: bool
    transfer_pausable: bool
    blacklist_function: bool
    mint_function: bool
    proxy_contract: bool
    verified_contract: bool
    high_tax: bool
    score: float

class TokenSecurityAnalyzer:
    def __init__(self, web3_provider: str, etherscan_api_key: str):
        self.w3 = Web3(Web3.HTTPProvider(web3_provider))
        self.etherscan_key = etherscan_api_key
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def analyze_token(self, token_address: str) -> SecurityAnalysis:
        tasks = [
            self._check_honeypot(token_address),
            self._check_contract_verification(token_address),
            self._analyze_bytecode(token_address),
            self._check_ownership(token_address),
            self._analyze_liquidity(token_address)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        honeypot_risk = results[0] if not isinstance(results[0], Exception) else 1.0
        verified = results[1] if not isinstance(results[1], Exception) else False
        bytecode_analysis = results[2] if not isinstance(results[2], Exception) else {}
        ownership_info = results[3] if not isinstance(results[3], Exception) else {}
        liquidity_info = results[4] if not isinstance(results[4], Exception) else {}

        analysis = SecurityAnalysis(
            honeypot_risk=honeypot_risk,
            ownership_renounced=ownership_info.get('renounced', False),
            liquidity_locked=liquidity_info.get('locked', False),
            max_transaction_limit=bytecode_analysis.get('max_tx_limit', False),
            transfer_pausable=bytecode_analysis.get('pausable', False),
            blacklist_function=bytecode_analysis.get('blacklist', False),
            mint_function=bytecode_analysis.get('mintable', False),
            proxy_contract=bytecode_analysis.get('proxy', False),
            verified_contract=verified,
            high_tax=bytecode_analysis.get('high_tax', False),
            score=0.0
        )

        analysis.score = self._calculate_security_score(analysis)
        return analysis

    async def _check_honeypot(self, token_address: str) -> float:
        try:
            url = f"https://api.honeypot.is/v2/IsHoneypot"
            params = {'address': token_address}
            
            async with self.session.get(url, params=params) as response:
                data = await response.json()
                
                if data.get('isHoneypot'):
                    return 1.0
                
                buy_tax = float(data.get('simulationResult', {}).get('buyTax', 0))
                sell_tax = float(data.get('simulationResult', {}).get('sellTax', 0))
                
                return min((buy_tax + sell_tax) / 20.0, 1.0)
                
        except Exception:
            return 0.5

    async def _check_contract_verification(self, token_address: str) -> bool:
        try:
            url = "https://api.etherscan.io/api"
            params = {
                'module': 'contract',
                'action': 'getsourcecode',
                'address': token_address,
                'apikey': self.etherscan_key
            }
            
            async with self.session.get(url, params=params) as response:
                data = await response.json()
                return data['result'][0]['SourceCode'] != ''
                
        except Exception:
            return False

    async def _analyze_bytecode(self, token_address: str) -> Dict[str, bool]:
        try:
            bytecode = self.w3.eth.get_code(Web3.toChecksumAddress(token_address)).hex()
            
            patterns = {
                'max_tx_limit': [
                    '63ffffffff',
                    'maxTransactionAmount',
                    '_maxTxAmount'
                ],
                'pausable': [
                    'whenNotPaused',
                    '_pause',
                    'paused'
                ],
                'blacklist': [
                    'blacklist',
                    'isBlacklisted',
                    '_blacklist'
                ],
                'mintable': [
                    'mint',
                    '_mint',
                    'mintTo'
                ],
                'proxy': [
                    '3660006000376110006000366000732021',
                    '363d3d373d3d3d363d73'
                ],
                'high_tax': [
                    'transfer.*tax',
                    'fee.*transfer'
                ]
            }
            
            results = {}
            for feature, pattern_list in patterns.items():
                results[feature] = any(
                    pattern.lower() in bytecode.lower() 
                    for pattern in pattern_list
                )
            
            return results
            
        except Exception:
            return {}

    async def _check_ownership(self, token_address: str) -> Dict[str, bool]:
        try:
            contract_abi = json.loads('[{"constant":true,"inputs":[],"name":"owner","outputs":[{"name":"","type":"address"}],"type":"function"}]')
            contract = self.w3.eth.contract(
                address=Web3.toChecksumAddress(token_address),
                abi=contract_abi
            )
            
            try:
                owner = contract.functions.owner().call()
                zero_address = "0x0000000000000000000000000000000000000000"
                dead_address = "0x000000000000000000000000000000000000dEaD"
                
                return {
                    'renounced': owner.lower() in [zero_address.lower(), dead_address.lower()]
                }
            except Exception:
                return {'renounced': False}
                
        except Exception:
            return {'renounced': False}

    async def _analyze_liquidity(self, token_address: str) -> Dict[str, bool]:
        try:
            return {'locked': False}
        except Exception:
            return {'locked': False}

    def _calculate_security_score(self, analysis: SecurityAnalysis) -> float:
        score = 100.0
        
        score -= analysis.honeypot_risk * 40
        
        if not analysis.verified_contract:
            score -= 20
        if not analysis.ownership_renounced:
            score -= 15
        if analysis.blacklist_function:
            score -= 15
        if analysis.transfer_pausable:
            score -= 10
        if analysis.mint_function:
            score -= 10
        if analysis.proxy_contract:
            score -= 5
        if analysis.high_tax:
            score -= 10
        if analysis.max_transaction_limit:
            score -= 5
        
        if analysis.liquidity_locked:
            score += 5
        
        return max(0.0, min(100.0, score))

    async def is_safe_to_trade(self, token_address: str, min_score: float = 70.0) -> Tuple[bool, SecurityAnalysis]:
        analysis = await self.analyze_token(token_address)
        return analysis.score >= min_score, analysis

async def main():
    analyzer = TokenSecurityAnalyzer("https://eth-mainnet.alchemyapi.io/v2/demo", "YourEtherscanAPIKey")
    async with analyzer:
        safe, analysis = await analyzer.is_safe_to_trade("0xA0b86a33E6441b24b4B2CCcdca5E5f7c9eF3Bd20")
        print(f"Safe to trade: {safe}")
        print(f"Security score: {analysis.score}")

if __name__ == "__main__":
    asyncio.run(main())
