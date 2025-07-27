#!/bin/bash

# Elite Alpha Mirror Bot - Production Deployment Script
# This script deploys the hardened system to production with all safety measures

set -euo pipefail

echo "🚀 Elite Alpha Mirror Bot - Production Deployment"
echo "=================================================="

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Configuration
DEPLOYMENT_LOG="logs/deployment_$(date +%Y%m%d_%H%M%S).log"
HEALTH_CHECK_RETRIES=30
HEALTH_CHECK_DELAY=10

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$DEPLOYMENT_LOG"
}

# Error handler
error_exit() {
    echo -e "${RED}❌ Error: $1${NC}" >&2
    log "ERROR: $1"
    exit 1
}

# Success message
success() {
    echo -e "${GREEN}✅ $1${NC}"
    log "SUCCESS: $1"
}

# Warning message
warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
    log "WARNING: $1"
}

# Info message
info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
    log "INFO: $1"
}

# Pre-deployment safety checks
pre_deployment_checks() {
    echo -e "${BLUE}🔍 Running pre-deployment safety checks...${NC}"
    
    # Check if .env.production exists
    if [ ! -f ".env.production" ]; then
        error_exit ".env.production not found. Run ./production_setup.sh first"
    fi
    
    # Check if secrets are configured
    if grep -q "YOUR_" .env.production; then
        error_exit "Placeholder values found in .env.production. Please configure all API keys"
    fi
    
    # Check if paper trading is enabled
    if ! grep -q "PAPER_TRADING_MODE=true" .env.production; then
        warning "Paper trading mode not enabled"
        echo -e "${RED}🚨 LIVE TRADING DETECTED!${NC}"
        echo -e "${RED}This will use real money!${NC}"
        echo ""
        read -p "Type 'I UNDERSTAND THE RISKS' to continue with live trading: " -r
        if [[ $REPLY != "I UNDERSTAND THE RISKS" ]]; then
            error_exit "Live trading not confirmed. Enable PAPER_TRADING_MODE=true for safety"
        fi
    fi
    
    # Check Docker availability
    if ! command -v docker &> /dev/null; then
        error_exit "Docker not found. Please install Docker first"
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error_exit "Docker Compose not found. Please install Docker Compose first"
    fi
    
    # Check disk space
    DISK_USAGE=$(df . | awk 'NR==2{print $5}' | sed 's/%//')
    if [ "$DISK_USAGE" -gt 80 ]; then
        warning "Disk usage is ${DISK_USAGE}%. Consider freeing up space"
    fi
    
    # Check available memory
    MEMORY_GB=$(free -g | awk 'NR==2{print $2}')
    if [ "$MEMORY_GB" -lt 4 ]; then
        warning "Only ${MEMORY_GB}GB RAM available. Consider upgrading for better performance"
    fi
    
    success "Pre-deployment checks completed"
}

# Build production images
build_production_images() {
    echo -e "${BLUE}🏗️ Building production Docker images...${NC}"
    
    # Build main application image
    log "Building production Docker image..."
    docker build -f Dockerfile.prod -t elite-alpha-bot:production . || error_exit "Failed to build Docker image"
    
    success "Production Docker image built successfully"
}

# Setup production database
setup_production_database() {
    echo -e "${BLUE}🗄️ Setting up production database...${NC}"
    
    # Start PostgreSQL container first
    log "Starting PostgreSQL container..."
    docker-compose -f docker-compose.prod.yml up -d postgres
    
    # Wait for PostgreSQL to be ready
    info "Waiting for PostgreSQL to be ready..."
    for i in $(seq 1 30); do
        if docker-compose -f docker-compose.prod.yml exec -T postgres pg_isready -U elite_bot; then
            break
        fi
        if [ "$i" -eq 30 ]; then
            error_exit "PostgreSQL failed to start within 5 minutes"
        fi
        sleep 10
    done
    
    # Run database migrations
    log "Running database initialization..."
    docker-compose -f docker-compose.prod.yml exec -T postgres psql -U elite_bot -d elite_bot_prod -f /docker-entrypoint-initdb.d/init.sql || true
    
    success "Database setup completed"
}

# Deploy production services
deploy_production_services() {
    echo -e "${BLUE}🚢 Deploying production services...${NC}"
    
    # Copy environment file
    cp .env.production .env
    
    # Start all production services
    log "Starting all production services..."
    docker-compose -f docker-compose.prod.yml up -d
    
    success "Production services deployed"
}

# Wait for services to be healthy
wait_for_health_checks() {
    echo -e "${BLUE}🏥 Waiting for health checks...${NC}"
    
    services=("elite-bot-prod" "elite-redis-prod" "elite-postgres-prod")
    
    for service in "${services[@]}"; do
        info "Checking health of $service..."
        
        for i in $(seq 1 $HEALTH_CHECK_RETRIES); do
            if docker inspect "$service" | grep -q '"Health"' && \
               docker inspect "$service" | grep -q '"healthy"'; then
                success "$service is healthy"
                break
            elif [ "$i" -eq $HEALTH_CHECK_RETRIES ]; then
                warning "$service health check timeout"
                docker logs "$service" --tail 20
            else
                sleep $HEALTH_CHECK_DELAY
            fi
        done
    done
    
    # Check application health endpoint
    info "Checking application health endpoint..."
    for i in $(seq 1 $HEALTH_CHECK_RETRIES); do
        if curl -f -s http://localhost:8080/health > /dev/null; then
            success "Application health endpoint responding"
            break
        elif [ "$i" -eq $HEALTH_CHECK_RETRIES ]; then
            error_exit "Application health endpoint not responding after $((HEALTH_CHECK_RETRIES * HEALTH_CHECK_DELAY)) seconds"
        else
            sleep $HEALTH_CHECK_DELAY
        fi
    done
}

# Run post-deployment tests
run_post_deployment_tests() {
    echo -e "${BLUE}🧪 Running post-deployment tests...${NC}"
    
    # Test database connectivity
    info "Testing database connectivity..."
    if docker-compose -f docker-compose.prod.yml exec -T postgres psql -U elite_bot -d elite_bot_prod -c "SELECT 1;" > /dev/null; then
        success "Database connectivity test passed"
    else
        error_exit "Database connectivity test failed"
    fi
    
    # Test Redis connectivity
    info "Testing Redis connectivity..."
    if docker-compose -f docker-compose.prod.yml exec -T redis redis-cli -a "${REDIS_PASSWORD}" ping | grep -q "PONG"; then
        success "Redis connectivity test passed"
    else
        error_exit "Redis connectivity test failed"
    fi
    
    # Test API endpoints
    info "Testing API endpoints..."
    
    # Health endpoint
    if curl -f -s http://localhost:8080/health | grep -q "healthy"; then
        success "Health endpoint test passed"
    else
        error_exit "Health endpoint test failed"
    fi
    
    # Metrics endpoint
    if curl -f -s http://localhost:8081/metrics | grep -q "cpu_percent"; then
        success "Metrics endpoint test passed"
    else
        warning "Metrics endpoint test failed"
    fi
    
    success "Post-deployment tests completed"
}

# Setup monitoring and alerting
setup_monitoring() {
    echo -e "${BLUE}📊 Setting up monitoring and alerting...${NC}"
    
    # Start security monitoring
    if [ -f "scripts/security/monitor_security.sh" ]; then
        info "Starting security monitoring..."
        nohup scripts/security/monitor_security.sh start > logs/security_monitor.log 2>&1 &
        echo $! > logs/security_monitor.pid
        success "Security monitoring started"
    fi
    
    # Start emergency condition monitoring
    if [ -f "scripts/security/emergency_stop.sh" ]; then
        info "Starting emergency monitoring..."
        nohup scripts/security/emergency_stop.sh monitor > logs/emergency_monitor.log 2>&1 &
        echo $! > logs/emergency_monitor.pid
        success "Emergency monitoring started"
    fi
    
    # Schedule automated backups
    if [ -f "scripts/security/backup_system.sh" ]; then
        info "Scheduling automated backups..."
        scripts/security/backup_system.sh schedule
        success "Automated backups scheduled"
    fi
    
    success "Monitoring and alerting setup completed"
}

# Display deployment summary
show_deployment_summary() {
    echo ""
    echo -e "${PURPLE}================================================================${NC}"
    echo -e "${PURPLE}🎉 ELITE ALPHA MIRROR BOT - DEPLOYMENT COMPLETE${NC}"
    echo -e "${PURPLE}================================================================${NC}"
    echo ""
    
    # Get deployment info
    DEPLOYMENT_TIME=$(date)
    PAPER_TRADING=$(grep "PAPER_TRADING_MODE" .env | cut -d= -f2)
    STARTING_CAPITAL=$(grep "STARTING_CAPITAL" .env | cut -d= -f2)
    MAX_CAPITAL=$(grep "MAX_CAPITAL" .env | cut -d= -f2)
    
    echo -e "${GREEN}📊 Deployment Summary:${NC}"
    echo "  • Deployment Time: $DEPLOYMENT_TIME"
    echo "  • Paper Trading: $PAPER_TRADING"
    echo "  • Starting Capital: \$$STARTING_CAPITAL"
    echo "  • Maximum Capital: \$$MAX_CAPITAL"
    echo ""
    
    echo -e "${GREEN}🌐 Access URLs:${NC}"
    echo "  • Application Health: http://localhost:8080/health"
    echo "  • Metrics: http://localhost:8081/metrics"
    echo "  • Grafana Dashboard: http://localhost:3000"
    echo "  • Prometheus: http://localhost:9090"
    echo ""
    
    echo -e "${GREEN}🔧 Management Commands:${NC}"
    echo "  • View logs: docker-compose -f docker-compose.prod.yml logs -f elite-bot"
    echo "  • Stop services: docker-compose -f docker-compose.prod.yml stop"
    echo "  • Restart services: docker-compose -f docker-compose.prod.yml restart"
    echo "  • Emergency stop: scripts/security/emergency_stop.sh stop"
    echo "  • Health check: scripts/monitoring/health_check.sh"
    echo "  • Create backup: scripts/security/backup_system.sh create"
    echo ""
    
    echo -e "${GREEN}📋 Monitoring:${NC}"
    echo "  • Security Monitor: logs/security_monitor.log"
    echo "  • Emergency Monitor: logs/emergency_monitor.log"
    echo "  • Application Logs: logs/production/"
    echo "  • Deployment Log: $DEPLOYMENT_LOG"
    echo ""
    
    if [ "$PAPER_TRADING" = "true" ]; then
        echo -e "${GREEN}✅ PAPER TRADING MODE ACTIVE${NC}"
        echo -e "${GREEN}   Safe for testing - no real money at risk${NC}"
    else
        echo -e "${RED}🚨 LIVE TRADING MODE ACTIVE${NC}"
        echo -e "${RED}   Real money at risk - monitor carefully!${NC}"
    fi
    
    echo ""
    echo -e "${YELLOW}⚠️  Important Reminders:${NC}"
    echo "  • Monitor all trades and system health regularly"
    echo "  • Test emergency stop procedures"
    echo "  • Backup system data regularly"
    echo "  • Review security logs daily"
    echo "  • Keep all credentials secure"
    echo "  • Ensure compliance with local regulations"
    echo ""
    
    log "Deployment summary displayed"
}

# Create initial backup
create_initial_backup() {
    echo -e "${BLUE}💾 Creating initial deployment backup...${NC}"
    
    if [ -f "scripts/security/backup_system.sh" ]; then
        scripts/security/backup_system.sh create full
        success "Initial backup created"
    else
        warning "Backup system not found, skipping initial backup"
    fi
}

# Setup log rotation
setup_log_rotation() {
    echo -e "${BLUE}📝 Setting up log rotation...${NC}"
    
    cat > /tmp/elite-bot-logrotate << 'EOF'
/app/logs/production/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 elitebot elitebot
    postrotate
        docker-compose -f docker-compose.prod.yml restart elite-bot > /dev/null 2>&1 || true
    endscript
}

/app/logs/security/*.log {
    daily
    missingok
    rotate 90
    compress
    delaycompress
    notifempty
    create 644 elitebot elitebot
}
EOF

    if [ -d "/etc/logrotate.d" ]; then
        sudo cp /tmp/elite-bot-logrotate /etc/logrotate.d/elite-bot
        success "Log rotation configured"
    else
        warning "Logrotate not available, manual log management required"
    fi
    
    rm -f /tmp/elite-bot-logrotate
}

# Cleanup function
cleanup_deployment() {
    echo -e "${BLUE}🧹 Cleaning up deployment artifacts...${NC}"
    
    # Remove temporary files
    rm -f .env
    
    # Clean up Docker build cache
    docker system prune -f > /dev/null 2>&1 || true
    
    success "Cleanup completed"
}

# Rollback function
rollback_deployment() {
    echo -e "${YELLOW}🔄 Rolling back deployment...${NC}"
    
    # Stop all services
    docker-compose -f docker-compose.prod.yml down
    
    # Remove containers
    docker-compose -f docker-compose.prod.yml rm -f
    
    warning "Deployment rolled back"
    
    exit 1
}

# Signal handlers
trap rollback_deployment ERR
trap 'echo "Deployment interrupted by user"; rollback_deployment' INT TERM

# Main deployment function
main() {
    echo -e "${BLUE}Starting production deployment process...${NC}"
    
    # Create logs directory
    mkdir -p logs
    
    log "Production deployment started by $(whoami) at $(date)"
    
    # Run deployment steps
    pre_deployment_checks
    build_production_images
    setup_production_database
    deploy_production_services
    wait_for_health_checks
    run_post_deployment_tests
    setup_monitoring
    create_initial_backup
    setup_log_rotation
    cleanup_deployment
    
    # Show final summary
    show_deployment_summary
    
    log "Production deployment completed successfully"
    
    success "🎉 Production deployment completed successfully!"
}

# Pre-flight safety confirmation
echo ""
echo -e "${YELLOW}🚨 PRODUCTION DEPLOYMENT SAFETY CONFIRMATION${NC}"
echo "=============================================="
echo ""
echo "This script will deploy the Elite Alpha Mirror Bot to production."
echo ""
echo -e "${RED}⚠️  WARNINGS:${NC}"
echo "• This system involves real financial trading"
echo "• Real money may be at risk"
echo "• Ensure all configurations are correct"
echo "• Have emergency procedures ready"
echo ""
echo -e "${GREEN}✅ SAFETY MEASURES:${NC}"
echo "• Paper trading mode available for testing"
echo "• Risk management limits configured"
echo "• Emergency stop mechanisms in place"
echo "• Comprehensive monitoring and alerting"
echo "• Encrypted backups and audit logs"
echo ""

# Final confirmation
read -p "Do you want to proceed with production deployment? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled by user."
    exit 0
fi

echo ""
read -p "Have you reviewed all configuration files and API keys? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Please review all configurations before deployment."
    exit 0
fi

echo ""
echo -e "${GREEN}🚀 Starting deployment...${NC}"
echo ""

# Execute main deployment
main