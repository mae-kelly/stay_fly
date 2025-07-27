#!/bin/bash
# validate_system.sh - Final system validation and certification

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${PURPLE}🏆 ELITE ALPHA MIRROR BOT - FINAL VALIDATION${NC}"
echo -e "${PURPLE}===========================================${NC}"
echo -e "${CYAN}🎯 Comprehensive system certification process${NC}"
echo ""

# Global validation results
VALIDATION_PASSED=0
VALIDATION_TOTAL=0
CRITICAL_ISSUES=()
WARNINGS=()

# Validation tracking
validate_item() {
    local name="$1"
    local check_result="$2"
    local details="$3"
    local critical="$4"
    
    VALIDATION_TOTAL=$((VALIDATION_TOTAL + 1))
    
    if [ "$check_result" = "true" ]; then
        VALIDATION_PASSED=$((VALIDATION_PASSED + 1))
        echo -e "  ✅ $name: $details"
    else
        if [ "$critical" = "true" ]; then
            CRITICAL_ISSUES+=("$name: $details")
            echo -e "  ❌ $name: $details"
        else
            WARNINGS+=("$name: $details")
            echo -e "  ⚠️ $name: $details"
        fi
    fi
}

# Check virtual environment
check_virtual_environment() {
    echo -e "${BLUE}🐍 Validating Python Environment${NC}"
    echo "----------------------------------------"
    
    if [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        validate_item "Virtual Environment" "true" "Present and activatable" "true"
        
        # Check Python version
        python_version=$(python --version 2>&1)
        if python -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
            validate_item "Python Version" "true" "$python_version" "true"
        else
            validate_item "Python Version" "false" "$python_version (need 3.8+)" "true"
        fi
        
        # Check pip
        if command -v pip &> /dev/null; then
            pip_version=$(pip --version | cut -d' ' -f2)
            validate_item "Pip Package Manager" "true" "Version $pip_version" "true"
        else
            validate_item "Pip Package Manager" "false" "Not available" "true"
        fi
    else
        validate_item "Virtual Environment" "false" "Missing or corrupted" "true"
    fi
}

# Check dependencies
check_dependencies() {
    echo -e "\n${BLUE}📦 Validating Dependencies${NC}"
    echo "----------------------------------------"
    
    # Critical packages
    critical_packages=("aiohttp" "asyncio" "websockets" "web3" "pandas" "numpy")
    
    for package in "${critical_packages[@]}"; do
        if python -c "import ${package//-/_}" 2>/dev/null; then
            version=$(python -c "import ${package//-/_}; print(getattr(${package//-/_}, '__version__', 'unknown'))" 2>/dev/null || echo "unknown")
            validate_item "Package: $package" "true" "Version $version" "true"
        else
            validate_item "Package: $package" "false" "Not installed" "true"
        fi
    done
    
    # Optional packages
    optional_packages=("python-dotenv" "PyYAML" "psutil" "pytest")
    
    for package in "${optional_packages[@]}"; do
        if python -c "import ${package//-/_}" 2>/dev/null; then
            validate_item "Optional: $package" "true" "Available" "false"
        else
            validate_item "Optional: $package" "false" "Missing" "false"
        fi
    done
}

# Check file structure
check_file_structure() {
    echo -e "\n${BLUE}📁 Validating File Structure${NC}"
    echo "----------------------------------------"
    
    # Critical files
    critical_files=(
        ".env:Configuration file"
        "requirements.txt:Python dependencies"
        "core/master_coordinator.py:Main coordinator"
        "core/real_discovery.py:Elite wallet discovery"
        "core/okx_live_engine.py:OKX trading engine"
        "core/ultra_fast_engine.py:WebSocket engine"
        "python/analysis/security.py:Security analysis"
    )
    
    for file_desc in "${critical_files[@]}"; do
        IFS=':' read -r file desc <<< "$file_desc"
        if [ -f "$file" ]; then
            size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo "0")
            validate_item "$desc" "true" "Present (${size} bytes)" "true"
        else
            validate_item "$desc" "false" "Missing" "true"
        fi
    done
    
    # Critical directories
    critical_dirs=("core" "python" "data" "logs" "tests")
    
    for dir in "${critical_dirs[@]}"; do
        if [ -d "$dir" ]; then
            file_count=$(find "$dir" -type f 2>/dev/null | wc -l)
            validate_item "Directory: $dir" "true" "$file_count files" "true"
        else
            validate_item "Directory: $dir" "false" "Missing" "true"
        fi
    done
}

# Check configuration
check_configuration() {
    echo -e "\n${BLUE}⚙️ Validating Configuration${NC}"
    echo "----------------------------------------"
    
    if [ -f ".env" ]; then
        validate_item "Configuration File" "true" "Present" "true"
        
        # Load and check key configurations
        source .env 2>/dev/null || true
        
        # Check critical settings
        if [ -n "$STARTING_CAPITAL" ] && [ "$STARTING_CAPITAL" != "YOUR_STARTING_CAPITAL" ]; then
            validate_item "Starting Capital" "true" "\$$STARTING_CAPITAL" "false"
        else
            validate_item "Starting Capital" "false" "Not configured" "false"
        fi
        
        if [ -n "$MAX_POSITION_SIZE" ]; then
            validate_item "Position Size Limit" "true" "$MAX_POSITION_SIZE" "false"
        else
            validate_item "Position Size Limit" "false" "Not set" "false"
        fi
        
        # Check API configurations (non-critical for demo mode)
        if [[ "$ETH_HTTP_URL" != *"YOUR_"* ]] && [ -n "$ETH_HTTP_URL" ]; then
            validate_item "Ethereum RPC" "true" "Configured" "false"
        else
            validate_item "Ethereum RPC" "false" "Demo mode (placeholder)" "false"
        fi
        
        if [[ "$ETHERSCAN_API_KEY" != "YOUR_"* ]] && [ -n "$ETHERSCAN_API_KEY" ]; then
            validate_item "Etherscan API" "true" "Configured" "false"
        else
            validate_item "Etherscan API" "false" "Demo mode (placeholder)" "false"
        fi
        
        # Check safety settings
        if [ "$PAPER_TRADING_MODE" = "true" ]; then
            validate_item "Paper Trading Mode" "true" "Enabled (safe)" "false"
        else
            validate_item "Paper Trading Mode" "false" "Disabled (live trading)" "false"
        fi
    else
        validate_item "Configuration File" "false" "Missing .env file" "true"
    fi
}

# Test core components
test_core_components() {
    echo -e "\n${BLUE}🧪 Testing Core Components${NC}"
    echo "----------------------------------------"
    
    # Set Python path
    export PYTHONPATH="$(pwd):$(pwd)/core:$(pwd)/python:$PYTHONPATH"
    
    # Test imports
    components=(
        "core.master_coordinator:Master Coordinator"
        "core.real_discovery:Elite Discovery Engine"
        "core.okx_live_engine:OKX Trading Engine"
        "core.ultra_fast_engine:Ultra-Fast WebSocket Engine"
        "python.analysis.security:Security Analysis"
    )
    
    for component_desc in "${components[@]}"; do
        IFS=':' read -r module desc <<< "$component_desc"
        if python -c "import $module" 2>/dev/null; then
            validate_item "$desc Import" "true" "Module loads successfully" "true"
        else
            validate_item "$desc Import" "false" "Import error" "true"
        fi
    done
}

# Check system resources
check_system_resources() {
    echo -e "\n${BLUE}💻 Validating System Resources${NC}"
    echo "----------------------------------------"
    
    # Check available disk space
    available_space=$(df . | tail -1 | awk '{print $4}')
    available_gb=$((available_space / 1024 / 1024))
    
    if [ "$available_gb" -gt 1 ]; then
        validate_item "Disk Space" "true" "${available_gb}GB available" "false"
    else
        validate_item "Disk Space" "false" "Low space (${available_gb}GB)" "true"
    fi
    
    # Check internet connectivity
    if curl -s --connect-timeout 5 https://api.coingecko.com/api/v3/ping > /dev/null 2>&1; then
        validate_item "Internet Connectivity" "true" "Connected" "true"
    else
        validate_item "Internet Connectivity" "false" "Connection failed" "true"
    fi
    
    # Check system tools
    tools=("curl" "git" "jq")
    for tool in "${tools[@]}"; do
        if command -v "$tool" &> /dev/null; then
            version=$($tool --version 2>&1 | head -1 | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+' | head -1 || echo "installed")
            validate_item "System Tool: $tool" "true" "$version" "false"
        else
            validate_item "System Tool: $tool" "false" "Not installed" "false"
        fi
    done
}

# Run comprehensive tests
run_comprehensive_tests() {
    echo -e "\n${BLUE}🧪 Running Comprehensive Tests${NC}"
    echo "----------------------------------------"
    
    if [ -f "tests/test_comprehensive.py" ]; then
        echo -e "${YELLOW}Running test suite...${NC}"
        
        # Capture test output
        if python tests/test_comprehensive.py > /tmp/test_output.log 2>&1; then
            test_success_rate=$(grep "Success Rate:" /tmp/test_output.log | grep -o '[0-9]\+\.[0-9]\+' || echo "0")
            validate_item "Comprehensive Tests" "true" "Success rate: ${test_success_rate}%" "false"
        else
            validate_item "Comprehensive Tests" "false" "Tests failed" "false"
        fi
        
        # Check for test report
        if find tests/reports -name "test_report_*.json" -type f -quit 2>/dev/null; then
            validate_item "Test Reports" "true" "Generated successfully" "false"
        else
            validate_item "Test Reports" "false" "Not generated" "false"
        fi
    else
        validate_item "Test Suite" "false" "Test file missing" "true"
    fi
}

# Check API connectivity (if configured)
check_api_connectivity() {
    echo -e "\n${BLUE}🌐 Validating API Connectivity${NC}"
    echo "----------------------------------------"
    
    # Load environment
    source .env 2>/dev/null || true
    
    # Test public APIs
    if curl -s --connect-timeout 10 "https://api.coingecko.com