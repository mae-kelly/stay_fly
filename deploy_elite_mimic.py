#!/usr/bin/env python3

import os
import sys
import subprocess
import time
from pathlib import Path

def check_rust_installation():
    try:
        result = subprocess.run(['cargo', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Rust/Cargo: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    
    print("❌ Rust not found. Installing...")
    subprocess.run(['curl', '--proto', '=https', '--tlsv1.2', '-sSf', 'https://sh.rustup.rs', '-o', 'rustup.sh'])
    subprocess.run(['sh', 'rustup.sh', '-y'])
    
    os.environ['PATH'] = f"{os.environ['HOME']}/.cargo/bin:{os.environ['PATH']}"
    
    try:
        result = subprocess.run(['cargo', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Rust installed: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        print("❌ Rust installation failed")
        return False

def check_python_dependencies():
    required = ['web3', 'aiohttp', 'websockets', 'pandas', 'numpy', 'eth-account']
    missing = []
    
    for package in required:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            missing.append(package)
            print(f"❌ {package}")
    
    if missing:
        print(f"Installing missing packages: {' '.join(missing)}")
        subprocess.run([sys.executable, '-m', 'pip', 'install'] + missing)
        return True
    
    return True

def setup_environment():
    env_template = Path('.env.template')
    env_file = Path('.env')
    
    if not env_file.exists():
        if env_template.exists():
            env_file.write_text(env_template.read_text())
            print("✅ Created .env from template")
        else:
            print("❌ No .env.template found")
            return False
    else:
        print("✅ .env already exists")
    
    print("\n🔧 CONFIGURATION REQUIRED:")
    print("Edit .env file with your API keys:")
    print("- OKX API credentials (for DEX trading)")
    print("- Ethereum RPC/WS URLs (Alchemy/Infura)")
    print("- Etherscan API key (for contract analysis)")
    print("- Your wallet address and private key")
    print("- Discord webhook (for notifications)")
    
    return True

def build_rust_engine():
    rust_dir = Path("core/rust_mimic_engine")
    
    if not rust_dir.exists():
        print("❌ Rust engine directory not found")
        return False
    
    print("🦀 Building Rust execution engine...")
    
    os.chdir(rust_dir)
    
    result = subprocess.run(['cargo', 'build', '--release'], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Rust engine built successfully")
        print(f"📊 Build output: {result.stderr.split('Finished')[1].strip() if 'Finished' in result.stderr else 'Complete'}")
        os.chdir("../..")
        return True
    else:
        print(f"❌ Rust build failed: {result.stderr}")
        os.chdir("../..")
        return False

def validate_configuration():
    env_file = Path('.env')
    if not env_file.exists():
        print("❌ .env file not found")
        return False
    
    env_content = env_file.read_text()
    required_vars = [
        'OKX_API_KEY', 'OKX_SECRET_KEY', 'OKX_PASSPHRASE',
        'ETHEREUM_RPC_URL', 'ETHEREUM_WS_URL', 'ETHERSCAN_API_KEY',
        'WALLET_ADDRESS', 'PRIVATE_KEY'
    ]
    
    missing = []
    for var in required_vars:
        if f"{var}=your_" in env_content or f"{var}=YOUR_" in env_content:
            missing.append(var)
    
    if missing:
        print(f"❌ Please configure: {', '.join(missing)}")
        return False
    
    print("✅ Configuration appears complete")
    return True

def start_elite_mimic():
    print("🚀 Starting Elite Wallet Mimic System...")
    print("🎯 Target: $1K -> $1M via elite wallet mirroring")
    print("⚡ Using Rust for maximum execution speed")
    
    try:
        subprocess.run([sys.executable, 'elite_mimic_orchestrator.py'])
    except KeyboardInterrupt:
        print("\n👋 Elite Mimic System stopped")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    print("🔥 ELITE WALLET MIMIC DEPLOYMENT")
    print("=" * 50)
    print("🧠 Mirror elite deployer + sniper wallets")
    print("💎 Target 100x tokens within seconds of elite trades")
    print("🚀 $1K -> $1M via smart money following")
    print("=" * 50)
    
    if not check_rust_installation():
        print("❌ Rust installation failed")
        return False
    
    if not check_python_dependencies():
        print("❌ Python dependencies failed")
        return False
    
    if not setup_environment():
        print("❌ Environment setup failed")
        return False
    
    if not build_rust_engine():
        print("❌ Rust build failed")
        return False
    
    print("\n🔧 FINAL SETUP:")
    if not validate_configuration():
        print("❌ Configuration incomplete")
        print("Please edit .env file with your API credentials")
        return False
    
    print("\n✅ DEPLOYMENT READY")
    print("🎯 Elite wallets will be auto-discovered")
    print("⚡ Rust engine compiled and ready")
    print("📡 Mempool monitoring configured")
    
    response = input("\n🚀 Start Elite Mimic System? (y/N): ")
    if response.lower() in ['y', 'yes']:
        start_elite_mimic()
    else:
        print("👋 Run 'python3 elite_mimic_orchestrator.py' when ready")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)