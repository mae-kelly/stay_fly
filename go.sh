#!/bin/bash
# run_tests_bulletproof.sh - Self-correcting test runner

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

echo -e "${PURPLE}🧪 BULLETPROOF TEST RUNNER${NC}"
echo -e "${PURPLE}=========================${NC}"

# Function to check and fix dependencies
check_and_fix_dependencies() {
    echo -e "${YELLOW}🔍 Checking dependencies...${NC}"
    
    # Activate virtual environment
    if [ -d "venv" ]; then
        source venv/bin/activate
        echo -e "${GREEN}✅ Virtual environment activated${NC}"
    else
        echo -e "${RED}❌ Virtual environment missing. Creating...${NC}"
        python3 -m venv venv
        source venv/bin/activate
    fi
    
    # Check for missing packages and install them
    missing_packages=()
    
    # Test each package
    packages=("aiohttp" "websockets" "web3" "pandas" "numpy" "requests" "python-dotenv" "PyYAML" "psutil" "pytest" "aiosqlite")
    
    for package in "${packages[@]}"; do
        if ! python -c "import ${package//-/_}" 2>/dev/null; then
            missing_packages+=("$package")
        fi
    done
    
    # Install missing packages
    if [ ${#missing_packages[@]} -gt 0 ]; then
        echo -e "${YELLOW}📦 Installing missing packages: ${missing_packages[*]}${NC}"
        pip install "${missing_packages[@]}"
    fi
    
    # Fix eth-abi version if needed
    if ! python -c "from eth_abi import decode" 2>/dev/null; then
        echo -e "${YELLOW}🔧 Fixing eth-abi...${NC}"
        pip install --upgrade eth-abi==4.2.1
    fi
}

# Function to prepare test environment
prepare_test_environment() {
    echo -e "${YELLOW}🔧 Preparing test environment...${NC}"
    
    # Set Python path
    export PYTHONPATH="$(pwd):$(pwd)/core:$(pwd)/python:$PYTHONPATH"
    
    # Load environment variables
    if [ -f ".env" ]; then
        export $(cat .env | grep -v '^#' | xargs) 2>/dev/null || true
    fi
    
    # Create necessary directories
    mkdir -p {tests/reports,logs,data,monitoring}
    
    # Ensure test file exists and is executable
    if [ ! -f "tests/test_comprehensive.py" ]; then
        echo -e "${RED}❌ Test file missing${NC}"
        exit 1
    fi
}

# Function to run tests with retry logic
run_tests_with_retry() {
    local max_attempts=3
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        echo -e "${BLUE}🧪 Running test suite (attempt $attempt/$max_attempts)...${NC}"
        
        if python tests/test_comprehensive.py; then
            echo -e "${GREEN}✅ All tests passed!${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠️ Tests failed on attempt $attempt${NC}"
            
            if [ $attempt -lt $max_attempts ]; then
                echo -e "${YELLOW}🔧 Attempting to fix issues...${NC}"
                
                # Try to fix common issues
                check_and_fix_dependencies
                
                # Wait before retry
                sleep 2
            else
                echo -e "${RED}❌ Tests failed after $max_attempts attempts${NC}"
                return 1
            fi
        fi
        
        attempt=$((attempt + 1))
    done
}

# Function to analyze test results
analyze_test_results() {
    echo -e "${BLUE}📊 Analyzing test results...${NC}"
    
    # Find the latest test report
    latest_report=$(find tests/reports -name "test_report_*.json" -type f -exec ls -t {} + 2>/dev/null | head -1)
    
    if [ -n "$latest_report" ] && [ -f "$latest_report" ]; then
        echo -e "${GREEN}📋 Test report found: $latest_report${NC}"
        
        # Extract key metrics using python
        python3 << EOF
import json
import sys

try:
    with open('$latest_report', 'r') as f:
        report = json.load(f)
    
    summary = report.get('summary', {})
    print(f"📊 Test Summary:")
    print(f"   Total Tests: {summary.get('total_tests', 0)}")
    print(f"   Passed: {summary.get('passed_tests', 0)}")
    print(f"   Failed: {summary.get('failed_tests', 0)}")
    print(f"   Success Rate: {summary.get('success_rate', 0):.1f}%")
    
    # Show component breakdown
    components = report.get('component_breakdown', {})
    print(f"\n📋 Component Status:")
    for component, stats in components.items():
        total = stats['passed'] + stats['failed']
        rate = (stats['passed'] / total * 100) if total > 0 else 0
        status = "✅" if rate == 100 else "⚠️" if rate >= 80 else "❌"
        print(f"   {status} {component}: {stats['passed']}/{total} ({rate:.1f}%)")
    
    # Show failed tests
    failed_tests = [r for r in report.get('test_results', []) if not r.get('passed')]
    if failed_tests:
        print(f"\n❌ Failed Tests:")
        for test in failed_tests[:5]:  # Show first 5 failures
            print(f"   • {test['component']}/{test['test_name']}: {test['error_message']}")
    
except Exception as e:
    print(f"Error reading test report: {e}")
EOF
    else
        echo -e "${YELLOW}⚠️ No test report found${NC}"
    fi
}

# Function to provide recommendations
provide_recommendations() {
    echo -e "${BLUE}💡 Recommendations:${NC}"
    echo ""
    
    # Check configuration status
    if grep -q "YOUR_API_KEY" .env 2>/dev/null; then
        echo -e "${YELLOW}🔑 API Configuration:${NC}"
        echo "   • System is running in DEMO mode (safe simulation)"
        echo "   • For live trading, configure API keys in .env:"
        echo "     - ETH_WS_URL (Alchemy/Infura WebSocket)"
        echo "     - ETHERSCAN_API_KEY (contract analysis)"
        echo "     - OKX credentials (live trading - optional)"
        echo ""
    fi
    
    echo -e "${GREEN}🚀 Ready to Start:${NC}"
    echo "   • Run: ./start_bulletproof.sh"
    echo "   • Monitor: tail -f logs/bot.log"
    echo "   • Health check: ./monitoring/health_check.sh"
    echo ""
    
    echo -e "${BLUE}🎯 System Status:${NC}"
    echo "   • Elite wallet discovery: Ready"
    echo "   • Real-time monitoring: Ready"
    echo "   • OKX DEX integration: Ready"
    echo "   • Security analysis: Ready"
    echo "   • Risk management: Ready"
    echo ""
    
    echo -e "${GREEN}💰 Mission: Transform \$1K → \$1M via elite wallet mirroring!${NC}"
}

# Main execution
main() {
    echo -e "${BLUE}Starting bulletproof test suite...${NC}"
    echo ""
    
    # Step 1: Check and fix dependencies
    check_and_fix_dependencies
    
    # Step 2: Prepare environment
    prepare_test_environment
    
    # Step 3: Run tests with retry
    if run_tests_with_retry; then
        echo ""
        echo -e "${GREEN}🎉 TEST SUITE COMPLETED SUCCESSFULLY!${NC}"
        echo -e "${GREEN}===================================${NC}"
        
        # Analyze results
        analyze_test_results
        
        # Provide recommendations
        provide_recommendations
        
        return 0
    else
        echo ""
        echo -e "${RED}❌ TEST SUITE FAILED${NC}"
        echo -e "${RED}==================${NC}"
        
        # Still analyze what we can
        analyze_test_results
        
        echo ""
        echo -e "${YELLOW}🔧 Troubleshooting Steps:${NC}"
        echo "   1. Check .env configuration"
        echo "   2. Verify API keys (if using live mode)"
        echo "   3. Check internet connection"
        echo "   4. Run: ./fix_dependencies.sh"
        echo "   5. Restart: ./setup_bulletproof.sh"
        
        return 1
    fi
}

# Execute main function
main "$@"