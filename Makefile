# Elite Alpha Mirror Bot - Automation Makefile

.PHONY: help setup install build test run monitor stop clean docker-build docker-run k8s-deploy

# Variables
PYTHON := python3
PIP := pip3
VENV := venv
DOCKER_IMAGE := elite-alpha-bot
DOCKER_TAG := latest
NAMESPACE := elite-trading

# Default target
help:
	@echo "🚀 Elite Alpha Mirror Bot - Available Commands"
	@echo "=============================================="
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make setup          - Complete production setup"
	@echo "  make install        - Install dependencies only"
	@echo "  make build          - Build Rust components"
	@echo "  make config         - Setup configuration"
	@echo ""
	@echo "Development:"
	@echo "  make test           - Run all tests"
	@echo "  make lint           - Run code linting"
	@echo "  make format         - Format code"
	@echo "  make check          - Run all checks"
	@echo ""
	@echo "Operations:"
	@echo "  make run            - Start the bot"
	@echo "  make run-sim        - Start in simulation mode"
	@echo "  make monitor        - Monitor bot status"
	@echo "  make stop           - Stop the bot"
	@echo "  make logs           - View bot logs"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build   - Build Docker image"
	@echo "  make docker-run     - Run in Docker"
	@echo "  make docker-stop    - Stop Docker containers"
	@echo "  make docker-logs    - View Docker logs"
	@echo ""
	@echo "Kubernetes:"
	@echo "  make k8s-deploy     - Deploy to Kubernetes"
	@echo "  make k8s-undeploy   - Remove from Kubernetes"
	@echo "  make k8s-status     - Check K8s deployment status"
	@echo ""
	@echo "Maintenance:"
	@echo "  make backup         - Backup data"
	@echo "  make clean          - Clean build artifacts"
	@echo "  make update         - Update dependencies"

# Setup and Installation
setup: install build config
	@echo "✅ Production setup complete!"
	@echo "Edit config.env with your API keys, then run: make run"

install:
	@echo "📦 Installing dependencies..."
	@$(PYTHON) -m venv $(VENV) || true
	@source $(VENV)/bin/activate && $(PIP) install --upgrade pip
	@source $(VENV)/bin/activate && $(PIP) install -r requirements.txt
	@echo "✅ Python dependencies installed"

build:
	@echo "🔨 Building Rust components..."
	@if [ -d "rust" ]; then \
		cd rust && cargo build --release; \
		echo "✅ Rust components built"; \
	else \
		echo "⚠️ Rust directory not found, skipping"; \
	fi

config:
	@echo "⚙️ Setting up configuration..."
	@if [ ! -f "config.env" ]; then \
		cp config.env.example config.env; \
		echo "📝 Created config.env from template"; \
		echo "⚠️ Please edit config.env with your API keys!"; \
	else \
		echo "✅ config.env already exists"; \
	fi
	@mkdir -p data/{backups,tokens,trades,wallets} logs/{errors,performance,trades}

# Development
test:
	@echo "🧪 Running tests..."
	@source $(VENV)/bin/activate && python -m pytest tests/ -v
	@if [ -d "rust" ]; then cd rust && cargo test; fi

lint:
	@echo "🔍 Running linters..."
	@source $(VENV)/bin/activate && flake8 python/ core/ --max-line-length=88
	@source $(VENV)/bin/activate && black --check python/ core/
	@source $(VENV)/bin/activate && isort --check-only python/ core/
	@if [ -d "rust" ]; then cd rust && cargo clippy -- -D warnings; fi

format:
	@echo "✨ Formatting code..."
	@source $(VENV)/bin/activate && black python/ core/
	@source $(VENV)/bin/activate && isort python/ core/
	@if [ -d "rust" ]; then cd rust && cargo fmt; fi

check: lint test
	@echo "✅ All checks passed!"

# Operations
run:
	@echo "🚀 Starting Elite Alpha Mirror Bot..."
	@source $(VENV)/bin/activate && python main.py

run-sim:
	@echo "🎮 Starting in simulation mode..."
	@source $(VENV)/bin/activate && SIMULATION_MODE=true python main.py

monitor:
	@echo "📊 Monitoring bot status..."
	@bash monitor_bot.sh

stop:
	@echo "🛑 Stopping bot..."
	@pkill -f "main.py" || echo "Bot not running"
	@pkill -f "master_coordinator.py" || echo "Coordinator not running"

logs:
	@echo "📋 Recent bot activity:"
	@tail -50 logs/elite_bot.log || echo "No logs found"

logs-live:
	@echo "📋 Live bot logs (Ctrl+C to exit):"
	@tail -f logs/elite_bot.log

# Discovery and Analysis
discover:
	@echo "🔍 Discovering elite wallets..."
	@source $(VENV)/bin/activate && python auto_discovery.py

analyze:
	@echo "📊 Analyzing repository..."
	@source $(VENV)/bin/activate && python analyze_repo.py

# Docker Operations
docker-build:
	@echo "🐳 Building Docker image..."
	@docker build -t $(DOCKER_IMAGE):$(DOCKER_TAG) .
	@echo "✅ Docker image built: $(DOCKER_IMAGE):$(DOCKER_TAG)"

docker-run:
	@echo "🐳 Running in Docker..."
	@docker-compose up -d
	@echo "✅ Services started. Monitor at http://localhost:8080/health"

docker-stop:
	@echo "🐳 Stopping Docker containers..."
	@docker-compose down

docker-logs:
	@echo "📋 Docker logs:"
	@docker-compose logs -f elite-bot

docker-clean:
	@echo "🧹 Cleaning Docker resources..."
	@docker-compose down -v
	@docker system prune -f

# Kubernetes Operations
k8s-deploy:
	@echo "☸️ Deploying to Kubernetes..."
	@kubectl create namespace $(NAMESPACE) || true
	@kubectl apply -f k8s/ -n $(NAMESPACE)
	@echo "✅ Deployed to Kubernetes namespace: $(NAMESPACE)"

k8s-undeploy:
	@echo "☸️ Removing from Kubernetes..."
	@kubectl delete -f k8s/ -n $(NAMESPACE) || true

k8s-status:
	@echo "☸️ Kubernetes deployment status:"
	@kubectl get all -n $(NAMESPACE)

k8s-logs:
	@echo "📋 Kubernetes logs:"
	@kubectl logs -f deployment/elite-alpha-bot -n $(NAMESPACE)

k8s-shell:
	@echo "🐚 Opening shell in pod..."
	@kubectl exec -it deployment/elite-alpha-bot -n $(NAMESPACE) -- /bin/bash

# Maintenance
backup:
	@echo "💾 Creating backup..."
	@bash backup_data.sh
	@echo "✅ Backup completed"

clean:
	@echo "🧹 Cleaning build artifacts..."
	@rm -rf $(VENV) __pycache__/ *.pyc .pytest_cache/
	@if [ -d "rust" ]; then cd rust && cargo clean; fi
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleanup complete"

update:
	@echo "📦 Updating dependencies..."
	@source $(VENV)/bin/activate && $(PIP) install --upgrade -r requirements.txt
	@if [ -d "rust" ]; then cd rust && cargo update; fi

# Security
security-scan:
	@echo "🔒 Running security scans..."
	@source $(VENV)/bin/activate && bandit -r python/ core/
	@source $(VENV)/bin/activate && safety check

# Performance
benchmark:
	@echo "⚡ Running performance benchmarks..."
	@source $(VENV)/bin/activate && python -m pytest benchmarks/ -v

profile:
	@echo "📊 Profiling application..."
	@source $(VENV)/bin/activate && python -m cProfile -o profile_output main.py

# Documentation
docs:
	@echo "📚 Generating documentation..."
	@source $(VENV)/bin/activate && sphinx-build -b html docs/ docs/_build/

# Health Checks
health:
	@echo "🩺 Checking system health..."
	@curl -f http://localhost:8080/health || echo "Health endpoint not accessible"

metrics:
	@echo "📊 Fetching metrics..."
	@curl -s http://localhost:8080/metrics || echo "Metrics endpoint not accessible"

# Quick Commands
status: health
	@echo "📊 System Status:"
	@ps aux | grep -E "(main.py|master_coordinator)" | grep -v grep || echo "Bot not running"
	@echo "💾 Disk usage:"
	@df -h . | tail -1
	@echo "🧠 Memory usage:"
	@free -h | grep Mem

restart: stop run
	@echo "🔄 Bot restarted"

# Development helpers
dev-setup: setup
	@echo "🔧 Setting up development environment..."
	@source $(VENV)/bin/activate && pip install pytest black isort flake8 mypy
	@echo "✅ Development environment ready"

# One-liner for complete deployment
deploy-production: docker-build docker-run
	@echo "🚀 Production deployment complete!"
	@echo "🌐 Monitor at: http://localhost:3000 (Grafana)"
	@echo "📊 Health check: http://localhost:8080/health"
	@echo "📈 Metrics: http://localhost:8080/metrics"

# Emergency commands
emergency-stop:
	@echo "🚨 EMERGENCY STOP - Killing all processes..."
	@pkill -f "elite" || true
	@docker-compose down || true
	@kubectl delete -f k8s/ -n $(NAMESPACE) || true

emergency-backup:
	@echo "🚨 EMERGENCY BACKUP..."
	@timestamp=$(date +%Y%m%d_%H%M%S); \
	tar -czf "emergency_backup_$timestamp.tar.gz" data/ config.env logs/ || true
	@echo "✅ Emergency backup created"
	@echo "