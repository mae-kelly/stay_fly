import asyncio
import subprocess
import json
import os
from typing import Dict, Any
import signal
import sys

class AlphaMirrorOrchestrator:
    def __init__(self):
        self.rust_process = None
        self.okx_client = None
        self.token_analyzer = None
        self.wallet_tracker = None
        self.running = False

    async def initialize(self):
        await self._setup_environment()
        await self._initialize_components()
        await self._compile_rust_engine()

    async def _setup_environment(self):
        os.environ.setdefault('ETH_WS_URL', 'wss://eth-mainnet.ws.alchemyapi.io/v2/demo')
        os.environ.setdefault('OKX_API_KEY', '')
        os.environ.setdefault('OKX_SECRET_KEY', '')
        os.environ.setdefault('OKX_PASSPHRASE', '')
        os.environ.setdefault('ETHERSCAN_API_KEY', '')

    async def _initialize_components(self):
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'python'))
        
        from okx.client import OKXDEXClient
        from analysis.security import TokenSecurityAnalyzer
        from analysis.wallet_tracker import EliteWalletTracker

        self.okx_client = OKXDEXClient(
            os.environ['OKX_API_KEY'],
            os.environ['OKX_SECRET_KEY'],
            os.environ['OKX_PASSPHRASE']
        )

        self.token_analyzer = TokenSecurityAnalyzer(
            os.environ['ETH_WS_URL'].replace('wss://', 'https://'),
            os.environ['ETHERSCAN_API_KEY']
        )

        self.wallet_tracker = EliteWalletTracker()

    async def _compile_rust_engine(self):
        rust_dir = os.path.join(os.path.dirname(__file__), '..', 'rust')
        
        result = subprocess.run(
            ['cargo', 'build', '--release'],
            cwd=rust_dir,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise Exception(f"Rust compilation failed: {result.stderr}")

    async def start_alpha_discovery(self):
        async with self.wallet_tracker:
            elite_wallets = await self.wallet_tracker.discover_elite_wallets()
            print(f"Discovered {len(elite_wallets)} elite wallets")
            await self.wallet_tracker.export_alpha_wallets()

    async def start_rust_engine(self):
        rust_binary = os.path.join(os.path.dirname(__file__), '..', 'rust', 'target', 'release', 'alpha-mirror')
        
        self.rust_process = await asyncio.create_subprocess_exec(
            rust_binary,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

    async def monitor_performance(self):
        while self.running:
            if self.rust_process:
                if self.rust_process.returncode is not None:
                    print("Rust engine crashed, restarting...")
                    await self.start_rust_engine()
            
            await asyncio.sleep(30)

    async def run(self):
        await self.initialize()
        
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.running = True
        
        await self.start_alpha_discovery()
        await self.start_rust_engine()
        
        performance_monitor = asyncio.create_task(self.monitor_performance())
        
        try:
            await performance_monitor
        except asyncio.CancelledError:
            pass
        finally:
            await self.shutdown()

    def _signal_handler(self, signum, frame):
        print(f"Received signal {signum}, shutting down...")
        self.running = False

    async def shutdown(self):
        self.running = False
        
        if self.rust_process and self.rust_process.returncode is None:
            self.rust_process.terminate()
            try:
                await asyncio.wait_for(self.rust_process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.rust_process.kill()
                await self.rust_process.wait()

        if self.okx_client:
            await self.okx_client.__aexit__(None, None, None)
        
        if self.token_analyzer:
            await self.token_analyzer.__aexit__(None, None, None)
        
        if self.wallet_tracker:
            await self.wallet_tracker.__aexit__(None, None, None)

async def main():
    orchestrator = AlphaMirrorOrchestrator()
    await orchestrator.run()

if __name__ == "__main__":
    asyncio.run(main())
