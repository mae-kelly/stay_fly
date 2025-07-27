#!/bin/bash
# Emergency Stop Script

set -euo pipefail

EMERGENCY_FILE="/tmp/emergency_stop"
LOG_FILE="logs/security/emergency.log"

log_emergency() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - EMERGENCY - $1" | tee -a "$LOG_FILE"
}

# Create emergency stop signal
emergency_stop() {
    local reason="${1:-Manual emergency stop}"
    
    log_emergency "EMERGENCY STOP INITIATED: $reason"
    
    # Create emergency stop file
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $reason" > "$EMERGENCY_FILE"
    
    # Stop all trading containers
    if command -v docker-compose &> /dev/null; then
        log_emergency "Stopping Docker containers..."
        docker-compose -f docker-compose.prod.yml stop elite-bot
    fi
    
    # Kill trading processes
    log_emergency "Terminating trading processes..."
    pkill -f "start_production.py" || true
    pkill -f "master_coordinator.py" || true
    
    # Send alerts
    send_emergency_alerts "$reason"
    
    log_emergency "Emergency stop completed"
}

# Send emergency alerts
send_emergency_alerts() {
    local reason="$1"
    
    # Discord webhook
    if [ -n "${DISCORD_WEBHOOK:-}" ]; then
        curl -X POST "$DISCORD_WEBHOOK" \
            -H "Content-Type: application/json" \
            -d "{\"content\": \"🚨 **EMERGENCY STOP** - Elite Alpha Bot\\nReason: $reason\\nTime: $(date)\"}" \
            2>/dev/null || true
    fi
    
    # Email alert (if configured)
    if command -v mail &> /dev/null && [ -n "${EMAIL_ALERTS:-}" ]; then
        echo "EMERGENCY STOP - Elite Alpha Bot - $reason - $(date)" | mail -s "EMERGENCY STOP" "$EMAIL_ALERTS" || true
    fi
}

# Check if emergency stop is active
check_emergency_stop() {
    if [ -f "$EMERGENCY_FILE" ]; then
        echo "EMERGENCY STOP ACTIVE"
        cat "$EMERGENCY_FILE"
        return 0
    else
        echo "No emergency stop active"
        return 1
    fi
}

# Clear emergency stop
clear_emergency_stop() {
    if [ -f "$EMERGENCY_FILE" ]; then
        rm "$EMERGENCY_FILE"
        log_emergency "Emergency stop cleared"
        echo "Emergency stop cleared"
    else
        echo "No emergency stop to clear"
    fi
}

# Monitor for automatic emergency conditions
monitor_emergency_conditions() {
    while true; do
        # Check capital loss threshold
        if [ -f "data/production/current_capital.txt" ]; then
            CURRENT_CAPITAL=$(cat "data/production/current_capital.txt" 2>/dev/null || echo "1000")
            STARTING_CAPITAL=${STARTING_CAPITAL:-1000}
            LOSS_PCT=$(echo "scale=2; (($STARTING_CAPITAL - $CURRENT_CAPITAL) / $STARTING_CAPITAL) * 100" | bc -l 2>/dev/null || echo "0")
            
            if (( $(echo "$LOSS_PCT > 50" | bc -l) )); then
                emergency_stop "Capital loss exceeds 50%: $LOSS_PCT%"
                break
            fi
        fi
        
        # Check for repeated errors
        ERROR_COUNT=$(tail -n 100 logs/production/bot.log 2>/dev/null | grep -c "ERROR" || echo "0")
        if [ "$ERROR_COUNT" -gt 20 ]; then
            emergency_stop "Excessive errors detected: $ERROR_COUNT in last 100 log entries"
            break
        fi
        
        # Check system resources
        MEMORY_USAGE=$(free | awk 'FNR==2{printf "%.0f", $3/($3+$4)*100}')
        if [ "$MEMORY_USAGE" -gt 95 ]; then
            emergency_stop "Critical memory usage: ${MEMORY_USAGE}%"
            break
        fi
        
        sleep 60  # Check every minute
    done
}

# Main command handler
case "${1:-}" in
    "stop")
        emergency_stop "${2:-Manual emergency stop}"
        ;;
    "check")
        check_emergency_stop
        ;;
    "clear")
        clear_emergency_stop
        ;;
    "monitor")
        monitor_emergency_conditions
        ;;
    *)
        echo "Emergency Stop Management"
        echo "Usage: $0 {stop|check|clear|monitor}"
        echo ""
        echo "Commands:"
        echo "  stop [reason]  - Trigger emergency stop"
        echo "  check          - Check if emergency stop is active"
        echo "  clear          - Clear emergency stop"
        echo "  monitor        - Monitor for emergency conditions"
        echo ""
        echo "Examples:"
        echo "  $0 stop \"High losses detected\""
        echo "  $0 check"
        echo "  $0 clear"
        exit 1
        ;;
esac
