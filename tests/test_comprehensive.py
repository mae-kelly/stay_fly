#!/usr/bin/env python3
"""
Comprehensive Test Suite - FIXED VERSION
Tests all components with proper error handling and Python 3.13 compatibility
"""

import asyncio
import aiohttp
import json
import time
import os
import sys
import platform
import sqlite3
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import logging

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    name: str
    category: str
    passed: bool
    duration_ms: float
    error_message: str = ""


@dataclass
class TestSummary:
    total_tests: int
    passed_tests: int
    failed_tests: int
    success_rate: float
    total_runtime: float
    categories: Dict[str, Dict[str, int]]


class FixedComprehensiveTestSuite:
    def __init__(self):
        self.test_results: List[TestResult] = []
        self.start_time = time.time()
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def log_test(
        self,
        category: str,
        name: str,
        passed: bool,
        duration_ms: float,
        error: str = "",
    ):
        """Log test result"""
        result = TestResult(name, category, passed, duration_ms, error)
        self.test_results.append(result)

        status = "✅" if passed else "❌"
        logger.info(f"  {status} {name}: {'PASS' if passed else 'FAIL'}")
        if error:
            logger.info(f"     Error: {error}")

    async def run_test_with_timeout(self, test_func, timeout_seconds: int = 10):
        """Run test with timeout and proper error handling"""
        try:
            return await asyncio.wait_for(test_func(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            return False, "Test timeout"
        except Exception as e:
            return False, str(e)

    async def test_python_environment(self):
        """Test Python environment and critical imports"""
        logger.info("🐍 Python Environment Tests")
        logger.info("-" * 40)

        # Python version
        start_time = time.time()
        try:
            version_info = f"{platform.python_version()}"
            self.log_test(
                "Python",
                f"Version {version_info}",
                True,
                (time.time() - start_time) * 1000,
            )
        except Exception as e:
            self.log_test(
                "Python",
                "Version Check",
                False,
                (time.time() - start_time) * 1000,
                str(e),
            )

        # Critical imports
        imports_to_test = [
            ("aiohttp", "aiohttp"),
            ("asyncio", "asyncio"),
            ("pandas", "pandas"),
            ("numpy", "numpy"),
            ("requests", "requests"),
            ("websockets", "websockets"),
            ("dotenv", "python-dotenv"),
            ("yaml", "PyYAML"),
            ("psutil", "psutil"),
        ]

        for module_name, display_name in imports_to_test:
            start_time = time.time()
            try:
                __import__(module_name)
                self.log_test(
                    "Python",
                    f"Import {display_name}",
                    True,
                    (time.time() - start_time) * 1000,
                )
            except ImportError as e:
                self.log_test(
                    "Python",
                    f"Import {display_name}",
                    False,
                    (time.time() - start_time) * 1000,
                    str(e),
                )
            except Exception as e:
                self.log_test(
                    "Python",
                    f"Import {display_name}",
                    False,
                    (time.time() - start_time) * 1000,
                    str(e),
                )

    async def test_blockchain_packages(self):
        """Test blockchain-related packages"""
        logger.info("🔗 Blockchain Package Tests")
        logger.info("-" * 40)

        blockchain_imports = [
            ("web3", "web3"),
            ("eth_account", "eth-account"),
        ]

        for module_name, display_name in blockchain_imports:
            start_time = time.time()
            try:
                __import__(module_name)
                self.log_test(
                    "Blockchain",
                    f"Import {display_name}",
                    True,
                    (time.time() - start_time) * 1000,
                )
            except ImportError as e:
                self.log_test(
                    "Blockchain",
                    f"Import {display_name}",
                    False,
                    (time.time() - start_time) * 1000,
                    str(e),
                )

        # Test eth_abi separately (known compatibility issue)
        start_time = time.time()
        try:
            import eth_abi

            # Try to use a basic function
            eth_abi.decode(["uint256"], b"\x00" * 32)
            self.log_test(
                "Blockchain",
                "eth_abi functionality",
                True,
                (time.time() - start_time) * 1000,
            )
        except ImportError as e:
            self.log_test(
                "Blockchain",
                "eth_abi import",
                False,
                (time.time() - start_time) * 1000,
                f"Import error (Python 3.13 compatibility): {e}",
            )
        except Exception as e:
            self.log_test(
                "Blockchain",
                "eth_abi functionality",
                False,
                (time.time() - start_time) * 1000,
                str(e),
            )

    async def test_api_connectivity(self):
        """Test API connectivity"""
        logger.info("🌐 API Connectivity Tests")
        logger.info("-" * 40)

        # Test basic HTTP connectivity
        start_time = time.time()
        try:
            async with self.session.get(
                "https://httpbin.org/status/200", timeout=5
            ) as response:
                if response.status == 200:
                    self.log_test(
                        "API",
                        "HTTP Connectivity",
                        True,
                        (time.time() - start_time) * 1000,
                    )
                else:
                    self.log_test(
                        "API",
                        "HTTP Connectivity",
                        False,
                        (time.time() - start_time) * 1000,
                        f"Status: {response.status}",
                    )
        except Exception as e:
            self.log_test(
                "API",
                "HTTP Connectivity",
                False,
                (time.time() - start_time) * 1000,
                str(e),
            )

        # Test Ethereum RPC (if URL provided)
        eth_url = os.getenv("ETH_HTTP_URL", "")
        if eth_url and not eth_url.startswith("YOUR_"):
            start_time = time.time()
            try:
                payload = {
                    "jsonrpc": "2.0",
                    "method": "eth_blockNumber",
                    "params": [],
                    "id": 1,
                }
                async with self.session.post(
                    eth_url, json=payload, timeout=10
                ) as response:
                    data = await response.json()
                    if "result" in data:
                        block_num = int(data["result"], 16)
                        self.log_test(
                            "API",
                            f"Ethereum RPC: Block {block_num:,}",
                            True,
                            (time.time() - start_time) * 1000,
                        )
                    else:
                        self.log_test(
                            "API",
                            "Ethereum RPC",
                            False,
                            (time.time() - start_time) * 1000,
                            "No result in response",
                        )
            except Exception as e:
                self.log_test(
                    "API",
                    "Ethereum RPC",
                    False,
                    (time.time() - start_time) * 1000,
                    str(e),
                )

        # Test Etherscan API (if key provided)
        etherscan_key = os.getenv("ETHERSCAN_API_KEY", "")
        if etherscan_key and not etherscan_key.startswith("YOUR_"):
            start_time = time.time()
            try:
                url = f"https://api.etherscan.io/api?module=stats&action=ethsupply&apikey={etherscan_key}"
                async with self.session.get(url, timeout=10) as response:
                    data = await response.json()
                    if data.get("status") == "1":
                        supply = int(data["result"]) // 10**18
                        self.log_test(
                            "API",
                            f"Etherscan: ETH Supply {supply:,}",
                            True,
                            (time.time() - start_time) * 1000,
                        )
                    else:
                        self.log_test(
                            "API",
                            "Etherscan",
                            False,
                            (time.time() - start_time) * 1000,
                            data.get("message", "Unknown error"),
                        )
            except Exception as e:
                self.log_test(
                    "API", "Etherscan", False, (time.time() - start_time) * 1000, str(e)
                )

    async def test_file_structure(self):
        """Test critical file structure"""
        logger.info("📁 File Structure Tests")
        logger.info("-" * 40)

        critical_files = [
            "core/master_coordinator.py",
            "core/real_discovery.py",
            "core/okx_live_engine.py",
            "core/ultra_fast_engine.py",
            "python/analysis/security.py",
            "requirements.txt",
            ".env",
        ]

        for file_path in critical_files:
            start_time = time.time()
            try:
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    self.log_test(
                        "Files",
                        f"{file_path}: {file_size} bytes",
                        True,
                        (time.time() - start_time) * 1000,
                    )
                else:
                    self.log_test(
                        "Files",
                        file_path,
                        False,
                        (time.time() - start_time) * 1000,
                        "File not found",
                    )
            except Exception as e:
                self.log_test(
                    "Files", file_path, False, (time.time() - start_time) * 1000, str(e)
                )

        # Check data directories
        data_dirs = ["data", "logs", "core", "python"]
        for dir_path in data_dirs:
            start_time = time.time()
            try:
                if os.path.exists(dir_path) and os.path.isdir(dir_path):
                    file_count = len(
                        [
                            f
                            for f in os.listdir(dir_path)
                            if os.path.isfile(os.path.join(dir_path, f))
                        ]
                    )
                    self.log_test(
                        "Files",
                        f"Dir {dir_path}: {file_count} files",
                        True,
                        (time.time() - start_time) * 1000,
                    )
                else:
                    self.log_test(
                        "Files",
                        f"Dir {dir_path}",
                        False,
                        (time.time() - start_time) * 1000,
                        "Directory not found",
                    )
            except Exception as e:
                self.log_test(
                    "Files",
                    f"Dir {dir_path}",
                    False,
                    (time.time() - start_time) * 1000,
                    str(e),
                )

    async def test_database_operations(self):
        """Test database operations"""
        logger.info("📊 Database Operation Tests")
        logger.info("-" * 40)

        # Test SQLite
        start_time = time.time()
        try:
            test_db = "test_temp.db"
            conn = sqlite3.connect(test_db)
            cursor = conn.cursor()
            cursor.execute(
                "CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)"
            )
            cursor.execute("INSERT INTO test_table (name) VALUES (?)", ("test",))
            cursor.execute("SELECT * FROM test_table")
            result = cursor.fetchone()
            conn.close()
            os.remove(test_db)

            if result:
                self.log_test(
                    "Database",
                    "SQLite Operations",
                    True,
                    (time.time() - start_time) * 1000,
                )
            else:
                self.log_test(
                    "Database",
                    "SQLite Operations",
                    False,
                    (time.time() - start_time) * 1000,
                    "No data returned",
                )
        except Exception as e:
            self.log_test(
                "Database",
                "SQLite Operations",
                False,
                (time.time() - start_time) * 1000,
                str(e),
            )

    async def test_ml_components(self):
        """Test ML components if available"""
        logger.info("🧠 ML Component Tests")
        logger.info("-" * 40)

        # Test torch import
        start_time = time.time()
        try:
            import torch

            # Test basic tensor operations
            x = torch.tensor([1.0, 2.0, 3.0])
            y = x * 2
            self.log_test(
                "ML",
                "PyTorch Basic Operations",
                True,
                (time.time() - start_time) * 1000,
            )
        except ImportError:
            self.log_test(
                "ML",
                "PyTorch Import",
                False,
                (time.time() - start_time) * 1000,
                "PyTorch not installed (optional)",
            )
        except Exception as e:
            self.log_test(
                "ML",
                "PyTorch Operations",
                False,
                (time.time() - start_time) * 1000,
                str(e),
            )

        # Test ML brain if available
        start_time = time.time()
        try:
            sys.path.append("core")
            from ml_brain import MLBrain

            # Test ML brain initialization
            brain = MLBrain()
            self.log_test(
                "ML", "ML Brain Initialization", True, (time.time() - start_time) * 1000
            )
        except ImportError as e:
            self.log_test(
                "ML",
                "ML Brain Import",
                False,
                (time.time() - start_time) * 1000,
                f"Import error: {e}",
            )
        except Exception as e:
            self.log_test(
                "ML", "ML Brain", False, (time.time() - start_time) * 1000, str(e)
            )

    async def test_configuration(self):
        """Test configuration loading"""
        logger.info("⚙️ Configuration Tests")
        logger.info("-" * 40)

        start_time = time.time()
        try:
            # Test .env file loading
            env_vars = {}
            if os.path.exists(".env"):
                with open(".env", "r") as f:
                    for line in f:
                        line = line.strip()
                        if "=" in line and not line.startswith("#"):
                            key, value = line.split("=", 1)
                            env_vars[key.strip()] = value.strip()

                config_count = len(env_vars)
                self.log_test(
                    "Config",
                    f"Environment Variables: {config_count} loaded",
                    True,
                    (time.time() - start_time) * 1000,
                )
            else:
                self.log_test(
                    "Config",
                    "Environment File",
                    False,
                    (time.time() - start_time) * 1000,
                    ".env file not found",
                )

        except Exception as e:
            self.log_test(
                "Config",
                "Configuration Loading",
                False,
                (time.time() - start_time) * 1000,
                str(e),
            )

    async def test_core_components(self):
        """Test core component imports"""
        logger.info("🔧 Core Component Tests")
        logger.info("-" * 40)

        # Test core imports with error handling
        core_modules = [
            ("core.master_coordinator", "Master Coordinator"),
            ("core.real_discovery", "Elite Discovery"),
            ("core.okx_live_engine", "OKX Engine"),
            ("core.ultra_fast_engine", "Ultra-Fast Engine"),
        ]

        for module_path, display_name in core_modules:
            start_time = time.time()
            try:
                # Add core to path if not already there
                core_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), "..", "core"
                )
                if core_path not in sys.path:
                    sys.path.append(core_path)

                # Try importing
                __import__(module_path.replace("core.", ""))
                self.log_test(
                    "Core",
                    f"{display_name} Import",
                    True,
                    (time.time() - start_time) * 1000,
                )
            except ImportError as e:
                self.log_test(
                    "Core",
                    f"{display_name} Import",
                    False,
                    (time.time() - start_time) * 1000,
                    f"Import error: {e}",
                )
            except Exception as e:
                self.log_test(
                    "Core",
                    f"{display_name} Import",
                    False,
                    (time.time() - start_time) * 1000,
                    str(e),
                )

    async def test_performance_metrics(self):
        """Test system performance"""
        logger.info("⚡ Performance Tests")
        logger.info("-" * 40)

        # Test system resources
        start_time = time.time()
        try:
            import psutil

            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            self.log_test(
                "Performance",
                f"CPU Usage: {cpu_percent:.1f}%",
                True,
                (time.time() - start_time) * 1000,
            )
            self.log_test(
                "Performance",
                f"Memory: {memory.percent:.1f}% used",
                True,
                (time.time() - start_time) * 1000,
            )
            self.log_test(
                "Performance",
                f"Disk: {disk.percent:.1f}% used",
                True,
                (time.time() - start_time) * 1000,
            )

        except ImportError:
            self.log_test(
                "Performance",
                "System Metrics",
                False,
                (time.time() - start_time) * 1000,
                "psutil not available",
            )
        except Exception as e:
            self.log_test(
                "Performance",
                "System Metrics",
                False,
                (time.time() - start_time) * 1000,
                str(e),
            )

    def calculate_summary(self) -> TestSummary:
        """Calculate test summary"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result.passed)
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        total_runtime = time.time() - self.start_time

        # Group by category
        categories = {}
        for result in self.test_results:
            if result.category not in categories:
                categories[result.category] = {"total": 0, "passed": 0, "failed": 0}

            categories[result.category]["total"] += 1
            if result.passed:
                categories[result.category]["passed"] += 1
            else:
                categories[result.category]["failed"] += 1

        return TestSummary(
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            success_rate=success_rate,
            total_runtime=total_runtime,
            categories=categories,
        )

    async def run_comprehensive_tests(self):
        """Run all tests"""
        logger.info(
            "🧪 Starting Comprehensive Elite Alpha Mirror Bot Test Suite - FIXED VERSION"
        )
        logger.info("=" * 80)

        # Run all test categories
        test_categories = [
            self.test_python_environment,
            self.test_blockchain_packages,
            self.test_api_connectivity,
            self.test_file_structure,
            self.test_database_operations,
            self.test_configuration,
            self.test_core_components,
            self.test_ml_components,
            self.test_performance_metrics,
        ]

        for test_category in test_categories:
            try:
                await test_category()
                logger.info("")
            except Exception as e:
                logger.error(f"Test category failed: {e}")
                logger.info("")

        # Generate summary
        summary = self.calculate_summary()

        logger.info("=" * 80)
        logger.info("🧪 COMPREHENSIVE TEST REPORT - FIXED VERSION")
        logger.info("=" * 80)
        logger.info(f"📊 Test Summary:")
        logger.info(f"   Total Tests: {summary.total_tests}")
        logger.info(f"   Passed: {summary.passed_tests}")
        logger.info(f"   Failed: {summary.failed_tests}")
        logger.info(f"   Success Rate: {summary.success_rate:.1f}%")
        logger.info(f"   Total Runtime: {summary.total_runtime:.2f}s")
        logger.info("")

        logger.info("📋 Component Breakdown:")
        for category, stats in summary.categories.items():
            success_rate = (
                (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
            )
            status = "✅" if success_rate >= 80 else "⚠️" if success_rate >= 50 else "❌"
            logger.info(
                f"   {status} {category}: {stats['passed']}/{stats['total']} ({success_rate:.1f}%)"
            )

        logger.info("")

        # Show failed tests
        failed_tests = [result for result in self.test_results if not result.passed]
        if failed_tests:
            logger.info("❌ Failed Tests Detail:")
            for test in failed_tests:
                logger.info(f"   {test.category}/{test.name}: {test.error_message}")
            logger.info("")

        # Save detailed report
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": asdict(summary),
            "detailed_results": [asdict(result) for result in self.test_results],
            "system_info": {
                "python_version": platform.python_version(),
                "platform": platform.platform(),
                "architecture": platform.architecture(),
            },
        }

        os.makedirs("tests/reports", exist_ok=True)
        report_file = f"tests/reports/test_report_fixed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w") as f:
            json.dump(report_data, f, indent=2, default=str)

        logger.info(f"💾 Detailed report saved: {report_file}")
        logger.info("")

        # Final assessment
        if summary.success_rate >= 90:
            logger.info("🎉 EXCELLENT: System is production ready!")
        elif summary.success_rate >= 75:
            logger.info("👍 GOOD: System is mostly functional with minor issues")
        elif summary.success_rate >= 50:
            logger.info("⚠️ WARNING: System has significant issues that need attention")
        else:
            logger.info("❌ CRITICAL: System has major issues and needs immediate fixes")


async def main():
    """Main test runner"""
    test_suite = FixedComprehensiveTestSuite()
    async with test_suite:
        await test_suite.run_comprehensive_tests()


if __name__ == "__main__":
    asyncio.run(main())
