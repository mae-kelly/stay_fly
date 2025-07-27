#!/bin/bash

# Elite Alpha Mirror Bot - Production Setup Script
# This script sets up everything needed for production trading

set -e  # Exit on any error

echo "🚀 Elite Alpha Mirror Bot - Production Setup"
echo "==========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   log_error "This script should not be run as root for security reasons"
   exit 1
fi

# Check system requirements
log_info "Checking system requirements..."

# Check Python version
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 is required but not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_PYTHON="3.9"

if [ "$(printf '%s\n' "$REQUIRED_PYTHON" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_PYTHON" ]; then
    log_error "Python $REQUIRED_PYTHON or higher is required. Found: $PYTHON_VERSION"
    exit 1
fi

log_success "Python $PYTHON_VERSION detected"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    log_error "pip3 is required but not installed"
    exit 1
fi

# Install Rust if not present (for high-performance components)
if ! command -v cargo &> /dev/null; then
    log_info "Installing Rust for high-performance components..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source ~/.cargo/env
    log_success "Rust installed successfully"
else
    log_success "Rust already installed"
fi

# Create virtual environment
log_info "Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    log_success "Virtual environment created"
else
    log_info "Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate
log_success "Virtual environment activated"

# Upgrade pip
log_info "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
log_info "Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    log_success "Python dependencies installed"
else
    log_error "requirements.txt not found"
    exit 1
fi

# Build Rust components for maximum performance
log_info "Building high-performance Rust components..."
if [ -d "rust" ]; then
    cd rust
    cargo build --release
    cd ..
    log_success "Rust components built successfully"
else
    log_warning "Rust directory not found, skipping Rust build"
fi

# Create necessary directories
log_info "Creating necessary directories..."
mkdir -p data/{backups,tokens,trades,wallets}
mkdir -p logs/{errors,performance,trades}
mkdir -p monitoring
log_success "Directories created"

# Set up configuration
log_info "Setting up configuration..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        log_warning "Created .env from template. Please edit it with your API keys!"
        log_warning "IMPORTANT: Add your OKX API credentials before running the bot"
    else
        log_error ".env.example not found"
        exit 1
    fi
else
    log_info ".env already exists"
fi

# Validate configuration
log_info "Validating configuration..."
if grep -q "your_okx_api_key_here" .env; then
    log_warning "Please update .env with your actual OKX API credentials"
fi

if grep -q "YOUR_API_KEY" .env; then
    log_warning "Please update .env with your actual Ethereum RPC endpoints"
fi

# Set up Git hooks (if this is a git repository)
if [ -d ".git" ]; then
    log_info "Setting up Git hooks..."
    mkdir -p .git/hooks
    
    # Pre-commit hook to prevent committing sensitive data
    cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Prevent committing sensitive files
if git diff --cached --name-only | grep -E "(config\.env|\.key|\.pem)$"; then
    echo "Error: Attempting to commit sensitive files!"
    echo "Please remove sensitive files from staging area."
    exit 1
fi
EOF
    chmod +x .git/hooks/pre-commit
    log_success "Git hooks configured"
fi

# Install system monitoring tools
log_info "Setting up system monitoring..."
if command -v systemctl &> /dev/null; then
    # Create systemd service file
    cat > elite-bot.service << EOF
[Unit]
Description=Elite Alpha Mirror Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/python core/master_coordinator.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    log_info "Systemd service file created (elite-bot.service)"
    log_info "To install: sudo mv elite-bot.service /etc/systemd/system/"
    log_info "To enable: sudo systemctl enable elite-bot"
    log_info "To start: sudo systemctl start elite-bot"
fi

# Set up log rotation
log_info "Setting up log rotation..."
cat > elite-bot-logrotate << EOF
$(pwd)/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
}
EOF
log_info "Log rotation config created (elite-bot-logrotate)"
log_info "To install: sudo mv elite-bot-logrotate /etc/logrotate.d/"

# Set file permissions
log_info "Setting secure file permissions..."
chmod 600 .env
chmod -R 755 scripts/
chmod -R 700 data/
chmod -R 755 logs/
log_success "File permissions set"

# Run initial tests
log_info "Running initial system tests..."

# Test Python imports
python3 -c "
import asyncio
import aiohttp
import web3
import pandas
import numpy
print('✅ All Python dependencies imported successfully')
" || {
    log_error "Python dependency test failed"
    exit 1
}

# Test Rust components
if [ -f "rust/target/release/alpha-mirror" ]; then
    log_success "Rust components built and ready"
fi

# Create startup script
log_info "Creating startup script..."
cat > start_bot.sh << 'EOF'
#!/bin/bash
# Elite Alpha Mirror Bot Startup Script

cd "$(dirname "$0")"
source venv/bin/activate

echo "🚀 Starting Elite Alpha Mirror Bot..."
echo "📊 Check logs/performance.log for detailed information"
echo "🔍 Monitor at http://localhost:8080/health"
echo ""

# Start the bot
python core/master_coordinator.py
EOF
chmod +x start_bot.sh
log_success "Startup script created (start_bot.sh)"

# Create monitoring script
log_info "Creating monitoring script..."
cat > monitor_bot.sh << 'EOF'
#!/bin/bash
# Elite Alpha Mirror Bot Monitoring Script

echo "🔍 Elite Alpha Mirror Bot - System Monitor"
echo "======================================="

# Check if bot is running
if pgrep -f "master_coordinator.py" > /dev/null; then
    echo "✅ Bot Status: RUNNING"
else
    echo "❌ Bot Status: NOT RUNNING"
fi

# Check health endpoint
if curl -s http://localhost:8080/health > /dev/null; then
    echo "✅ Health Endpoint: ACCESSIBLE"
else
    echo "❌ Health Endpoint: NOT ACCESSIBLE"
fi

# Show recent logs
echo ""
echo "📋 Recent Activity:"
tail -5 logs/performance.log 2>/dev/null || echo "No performance logs found"

# Show system resources
echo ""
echo "💻 System Resources:"
echo "CPU: $(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1"%"}')"
echo "Memory: $(free | grep Mem | awk '{printf("%.1f%%", $3/$2 * 100.0)}')"
echo "Disk: $(df . | tail -1 | awk '{print $5}')"
EOF
chmod +x monitor_bot.sh
log_success "Monitoring script created (monitor_bot.sh)"

# Create backup script
log_info "Creating backup script..."
cat > backup_data.sh << 'EOF'
#!/bin/bash
# Elite Alpha Mirror Bot Backup Script

BACKUP_DIR="data/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="elite_bot_backup_$TIMESTAMP.tar.gz"

echo "🗄️ Creating backup: $BACKUP_FILE"

# Create backup
tar -czf "$BACKUP_DIR/$BACKUP_FILE" \
    data/real_elite_wallets.json \
    data/discovery_summary.json \
    data/*.db \
    .env.backup 2>/dev/null || true

# Keep only last 30 backups
find "$BACKUP_DIR" -name "elite_bot_backup_*.tar.gz" -mtime +30 -delete

echo "✅ Backup completed: $BACKUP_DIR/$BACKUP_FILE"
EOF
chmod +x backup_data.sh
log_success "Backup script created (backup_data.sh)"

# Set up automatic backups
log_info "Setting up automatic backups..."
(crontab -l 2>/dev/null; echo "0 */6 * * * $(pwd)/backup_data.sh") | crontab -
log_success "Automatic backups configured (every 6 hours)"

# Final security check
log_info "Performing final security check..."

# Check for default passwords/keys
SECURITY_ISSUES=0

if grep -q "your_.*_here" .env 2>/dev/null; then
    log_warning "Default API keys detected in .env"
    SECURITY_ISSUES=$((SECURITY_ISSUES + 1))
fi

if [ -f ".env" ] && [ "$(stat -c %a .env)" != "600" ]; then
    log_warning ".env permissions should be 600"
    SECURITY_ISSUES=$((SECURITY_ISSUES + 1))
fi

if [ $SECURITY_ISSUES -gt 0 ]; then
    log_warning "Found $SECURITY_ISSUES security issues. Please review above warnings."
else
    log_success "Security check passed"
fi

# Setup completion
echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "Next steps:"
echo "1. Edit .env with your API keys:"
echo "   - OKX API credentials"
echo "   - Ethereum RPC endpoints"
echo "   - Discord webhook URL"
echo ""
echo "2. Test the configuration:"
echo "   ./start_bot.sh"
echo ""
echo "3. Monitor the bot:"
echo "   ./monitor_bot.sh"
echo ""
echo "4. View performance:"
echo "   tail -f logs/performance.log"
echo ""
echo "⚠️  IMPORTANT REMINDERS:"
echo "   - Only trade with money you can afford to lose"
echo "   - Start with a small amount to test the system"
echo "   - Monitor the bot closely for the first few hours"
echo "   - Keep your API keys secure and never share them"
echo ""
echo "🚀 Ready to transform $1K into $1M with elite wallet mirroring!"

# Create a setup completion marker
touch .setup_complete
echo "Setup completed at $(date)" > .setup_complete

log_success "Production setup completed successfully!"