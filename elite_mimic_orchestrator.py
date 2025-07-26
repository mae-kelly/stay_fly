#!/usr/bin/env python3

import asyncio
import json
import subprocess
import sys
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional
import aiohttp
import websockets
from web3 import Web3
from eth_account import Account
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class EliteMimicOrchestrator:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(self.get_env_var("ETHEREUM_RPC_URL")))
        self.okx_api_key = self.get_env_var("OKX_API_KEY")
        self.okx_secret = self.get_env_var("OKX_SECRET_KEY")
        self.okx_passphrase = self.get_env_var("OKX_PASSPHRASE")
        self.wallet_address = self.get_env_var("WALLET_ADDRESS")
        self.private_key = self.get_env_var("PRIVATE_KEY")
        
        self.initial_capital = 1000.0
        self.current_capital = self.initial_capital
        self.positions = {}
        self.trade_history = []
        self.alpha_wallets = []
        
        self.rust_process = None
        
    def get_env_var(self, name: str) -> str:
        import os
        value = os.getenv(name)
        if not value:
            raise ValueError(f"Environment variable {name} not set")
        return value
    
    async def initialize_alpha_wallets(self):
        logging.info("Initializing alpha wallet discovery...")
        
        try:
            alpha_wallets_path = Path("alpha_wallets.json")
            if alpha_wallets_path.exists():
                with open(alpha_wallets_path, 'r') as f:
                    self.alpha_wallets = json.load(f)
                logging.info(f"Loaded {len(self.alpha_wallets)} existing alpha wallets")
            else:
                await self.discover_alpha_wallets()
        except Exception as e:
            logging.error(f"Failed to initialize alpha wallets: {e}")
            await self.discover_alpha_wallets()
    
    async def discover_alpha_wallets(self):
        logging.info("Discovering elite wallets from 100x tokens...")
        
        hundred_x_tokens = await self.find_100x_tokens()
        deployer_wallets = await self.extract_deployers(hundred_x_tokens)
        sniper_wallets = await self.find_early_snipers(hundred_x_tokens)
        
        all_wallets = deployer_wallets + sniper_wallets
        scored_wallets = await self.score_wallets(all_wallets)
        
        self.alpha_wallets = scored_wallets[:50]
        
        with open("alpha_wallets.json", 'w') as f:
            json.dump(self.alpha_wallets, f, indent=2)
        
        logging.info(f"Discovered and saved {len(self.alpha_wallets)} elite alpha wallets")
    
    async def find_100x_tokens(self) -> List[Dict]:
        async with aiohttp.ClientSession() as session:
            url = "https://api.dexscreener.com/latest/dex/pairs/ethereum"
            
            async with session.get(url) as response:
                data = await response.json()
                
                hundred_x_tokens = []
                
                if 'pairs' in data:
                    for pair in data['pairs'][:1000]:
                        try:
                            price_change_24h = float(pair.get('priceChange', {}).get('h24', 0))
                            if price_change_24h >= 10000:  # 100x = 10,000%
                                token_info = {
                                    'address': pair['baseToken']['address'],
                                    'symbol': pair['baseToken']['symbol'],
                                    'price_change_24h': price_change_24h,
                                    'volume_24h': float(pair.get('volume', {}).get('h24', 0)),
                                    'liquidity_usd': float(pair.get('liquidity', {}).get('usd', 0)),
                                    'pair_address': pair['pairAddress'],
                                    'dex_id': pair.get('dexId', ''),
                                }
                                
                                if token_info['liquidity_usd'] >= 50000:
                                    hundred_x_tokens.append(token_info)
                        except (ValueError, KeyError):
                            continue
                
                logging.info(f"Found {len(hundred_x_tokens)} tokens with 100x+ performance")
                return sorted(hundred_x_tokens, key=lambda x: x['price_change_24h'], reverse=True)[:100]
    
    async def extract_deployers(self, tokens: List[Dict]) -> List[Dict]:
        deployers = {}
        
        for token in tokens:
            deployer = await self.get_token_deployer(token['address'])
            if deployer:
                if deployer not in deployers:
                    deployers[deployer] = {
                        'address': deployer,
                        'deployed_tokens': [],
                        'total_multiplier': 0.0,
                        'success_count': 0,
                    }
                
                multiplier = (token['price_change_24h'] / 100.0) + 1.0
                deployers[deployer]['deployed_tokens'].append(token)
                deployers[deployer]['total_multiplier'] += multiplier
                if multiplier >= 10.0:
                    deployers[deployer]['success_count'] += 1
        
        elite_deployers = []
        for deployer_data in deployers.values():
            deploy_count = len(deployer_data['deployed_tokens'])
            avg_multiplier = deployer_data['total_multiplier'] / deploy_count
            success_rate = deployer_data['success_count'] / deploy_count
            
            if success_rate >= 0.6 and avg_multiplier >= 20.0:
                elite_deployers.append({
                    'address': deployer_data['address'],
                    'type': 'deployer',
                    'avg_multiplier': avg_multiplier,
                    'success_rate': success_rate,
                    'total_deploys': deploy_count,
                    'deployer_score': avg_multiplier * success_rate,
                })
        
        return sorted(elite_deployers, key=lambda x: x['deployer_score'], reverse=True)[:25]
    
    async def find_early_snipers(self, tokens: List[Dict]) -> List[Dict]:
        sniper_candidates = {}
        
        for token in tokens:
            early_buyers = await self.get_early_token_buyers(token['address'])
            
            for buyer in early_buyers[:10]:
                if buyer not in sniper_candidates:
                    sniper_candidates[buyer] = {
                        'address': buyer,
                        'sniped_tokens': [],
                        'total_multiplier': 0.0,
                        'avg_speed': 0.0,
                    }
                
                multiplier = (token['price_change_24h'] / 100.0) + 1.0
                sniper_candidates[buyer]['sniped_tokens'].append(token)
                sniper_candidates[buyer]['total_multiplier'] += multiplier
        
        elite_snipers = []
        for sniper_data in sniper_candidates.values():
            if len(sniper_data['sniped_tokens']) >= 3:
                avg_multiplier = sniper_data['total_multiplier'] / len(sniper_data['sniped_tokens'])
                
                if avg_multiplier >= 15.0:
                    elite_snipers.append({
                        'address': sniper_data['address'],
                        'type': 'sniper',
                        'avg_multiplier': avg_multiplier,
                        'tokens_sniped': len(sniper_data['sniped_tokens']),
                        'sniper_score': avg_multiplier * len(sniper_data['sniped_tokens']),
                    })
        
        return sorted(elite_snipers, key=lambda x: x['sniper_score'], reverse=True)[:25]
    
    async def get_token_deployer(self, token_address: str) -> Optional[str]:
        try:
            etherscan_api_key = self.get_env_var("ETHERSCAN_API_KEY")
            url = f"https://api.etherscan.io/api"
            params = {
                'module': 'contract',
                'action': 'getcontractcreation',
                'contractaddresses': token_address,
                'apikey': etherscan_api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    data = await response.json()
                    
                    if data.get('status') == '1' and data.get('result'):
                        return data['result'][0]['contractCreator']
            
            await asyncio.sleep(0.2)  # Rate limiting
            return None
        except Exception:
            return None
    
    async def get_early_token_buyers(self, token_address: str) -> List[str]:
        try:
            etherscan_api_key = self.get_env_var("ETHERSCAN_API_KEY")
            url = f"https://api.etherscan.io/api"
            params = {
                'module': 'account',
                'action': 'tokentx',
                'contractaddress': token_address,
                'page': 1,
                'offset': 100,
                'sort': 'asc',
                'apikey': etherscan_api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    data = await response.json()
                    
                    buyers = []
                    if data.get('status') == '1' and data.get('result'):
                        for tx in data['result'][:20]:
                            buyers.append(tx['to'])
                    
                    await asyncio.sleep(0.2)
                    return buyers
        except Exception:
            return []
    
    async def score_wallets(self, wallets: List[Dict]) -> List[Dict]:
        for wallet in wallets:
            if wallet['type'] == 'deployer':
                wallet['composite_score'] = wallet['deployer_score']
            else:
                wallet['composite_score'] = wallet['sniper_score']
            
            wallet['risk_score'] = min(0.8, 1.0 - (wallet['avg_multiplier'] / 200.0))
        
        return sorted(wallets, key=lambda x: x['composite_score'], reverse=True)
    
    async def start_rust_engine(self):
        logging.info("Starting Rust execution engine...")
        
        try:
            rust_dir = Path("core/rust_mimic_engine")
            self.rust_process = await asyncio.create_subprocess_exec(
                "cargo", "run", "--release",
                cwd=rust_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            logging.info("Rust engine started successfully")
            return True
        except Exception as e:
            logging.error(f"Failed to start Rust engine: {e}")
            return False
    
    async def monitor_rust_engine(self):
        if not self.rust_process:
            return
        
        while True:
            try:
                line = await self.rust_process.stdout.readline()
                if line:
                    logging.info(f"Rust Engine: {line.decode().strip()}")
                else:
                    break
            except Exception as e:
                logging.error(f"Error reading Rust output: {e}")
                break
    
    async def portfolio_monitor(self):
        while True:
            try:
                await asyncio.sleep(30)
                
                portfolio_data = await self.get_portfolio_status()
                
                current_value = portfolio_data.get('total_value', self.current_capital)
                total_return = ((current_value - self.initial_capital) / self.initial_capital) * 100
                
                logging.info(f"Portfolio: ${current_value:.2f} ({total_return:+.1f}%) | "
                           f"Positions: {portfolio_data.get('active_positions', 0)}")
                
                if total_return >= 100000:  # 1000x
                    logging.info("🎉 TARGET ACHIEVED: $1K -> $1M via elite wallet mirroring!")
                    await self.emergency_shutdown()
                    break
                    
            except Exception as e:
                logging.error(f"Portfolio monitoring error: {e}")
                await asyncio.sleep(10)
    
    async def get_portfolio_status(self) -> Dict:
        try:
            portfolio_file = Path("/tmp/portfolio_status.json")
            if portfolio_file.exists():
                with open(portfolio_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        
        return {
            'total_value': self.current_capital,
            'active_positions': 0,
            'total_trades': 0,
            'win_rate': 0.0
        }
    
    async def emergency_shutdown(self):
        logging.info("Initiating emergency shutdown...")
        
        if self.rust_process:
            self.rust_process.terminate()
            await self.rust_process.wait()
        
        logging.info("Emergency shutdown complete")
    
    async def run(self):
        logging.info("🚀 Starting Elite Wallet Mimic System")
        logging.info("🎯 Target: $1K -> $1M via 100x token mirroring")
        logging.info(f"💰 Initial Capital: ${self.initial_capital}")
        
        await self.initialize_alpha_wallets()
        
        rust_started = await self.start_rust_engine()
        if not rust_started:
            logging.error("Failed to start Rust engine, aborting...")
            return
        
        tasks = [
            self.monitor_rust_engine(),
            self.portfolio_monitor(),
        ]
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logging.info("Shutdown requested by user")
        except Exception as e:
            logging.error(f"System error: {e}")
        finally:
            await self.emergency_shutdown()

async def main():
    orchestrator = EliteMimicOrchestrator()
    await orchestrator.run()

if __name__ == "__main__":
    asyncio.run(main())