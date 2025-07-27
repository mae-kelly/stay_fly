#!/bin/bash
# Security Monitoring Script

LOG_FILE="logs/security/security_monitor.log"
mkdir -p logs/security

# Function to log security events
log_security() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - SECURITY - $1" | tee -a "$LOG_FILE"
}

# Monitor failed login attempts
monitor_failed_logins() {
    FAILED_COUNT=$(grep "authentication failed" logs/production/*.log | wc -l 2>/dev/null || echo "0")
    if [ "$FAILED_COUNT" -gt 10 ]; then
        log_security "HIGH - Multiple failed authentication attempts: $FAILED_COUNT"
    fi
}

# Monitor API rate limiting
monitor_rate_limits() {
    RATE_LIMIT_COUNT=$(grep "rate limit" logs/production/*.log | wc -l 2>/dev/null || echo "0")
    if [ "$RATE_LIMIT_COUNT" -gt 50 ]; then
        log_security "MEDIUM - High rate limiting activity: $RATE_LIMIT_COUNT"
    fi
}

# Monitor disk space for log tampering
monitor_disk_space() {
    DISK_USAGE=$(df /var/log 2>/dev/null | awk 'NR==2{print $5}' | sed 's/%//' || echo "0")
    if [ "$DISK_USAGE" -gt 90 ]; then
        log_security "HIGH - Disk space critical: ${DISK_USAGE}%"
    fi
}

# Monitor unusual API activity
monitor_api_activity() {
    API_ERRORS=$(grep "API.*error" logs/production/*.log | wc -l 2>/dev/null || echo "0")
    if [ "$API_ERRORS" -gt 100 ]; then
        log_security "MEDIUM - High API error rate: $API_ERRORS"
    fi
}

# Monitor file permission changes
monitor_file_permissions() {
    # Check critical files
    CRITICAL_FILES=(".env.production" "config/security/secrets.env" "data/keys")
    
    for file in "${CRITICAL_FILES[@]}"; do
        if [ -e "$file" ]; then
            PERMS=$(stat -f "%A" "$file" 2>/dev/null || stat -c "%a" "$file" 2>/dev/null || echo "000")
            if [[ "$file" == *".env"* ]] && [ "$PERMS" != "600" ]; then
                log_security "HIGH - Insecure permissions on $file: $PERMS"
            elif [[ "$file" == *"keys"* ]] && [ "$PERMS" != "700" ]; then
                log_security "HIGH - Insecure permissions on $file: $PERMS"
            fi
        fi
    done
}

# Monitor process integrity
monitor_processes() {
    # Check if main bot process is running
    if ! pgrep -f "start_production.py" > /dev/null; then
        log_security "CRITICAL - Main bot process not running"
    fi
    
    # Check for suspicious processes
    SUSPICIOUS_PROCS=$(ps aux | grep -E "(bitcoin|mining|crypto)" | grep -v grep | wc -l)
    if [ "$SUSPICIOUS_PROCS" -gt 0 ]; then
        log_security "MEDIUM - Suspicious processes detected: $SUSPICIOUS_PROCS"
    fi
}

# Monitor network connections
monitor_network() {
    # Check for unusual outbound connections
    CONNECTIONS=$(netstat -tn 2>/dev/null | grep ESTABLISHED | wc -l || echo "0")
    if [ "$CONNECTIONS" -gt 100 ]; then
        log_security "MEDIUM - High number of network connections: $CONNECTIONS"
    fi
}

# Main monitoring loop
main_monitor() {
    log_security "Security monitoring started"
    
    while true; do
        monitor_failed_logins
        monitor_rate_limits
        monitor_disk_space
        monitor_api_activity
        monitor_file_permissions
        monitor_processes
        monitor_network
        
        sleep 300  # Check every 5 minutes
    done
}

# Run monitoring
case "${1:-}" in
    "start")
        main_monitor
        ;;
    "check")
        monitor_failed_logins
        monitor_rate_limits
        monitor_disk_space
        monitor_api_activity
        monitor_file_permissions
        monitor_processes
        monitor_network
        ;;
    *)
        echo "Usage: $0 {start|check}"
        echo "  start - Run continuous monitoring"
        echo "  check - Run single security check"
        exit 1
        ;;
esac
