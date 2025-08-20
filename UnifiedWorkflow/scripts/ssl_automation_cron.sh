#!/bin/bash
# SSL Certificate Automation Cron Script
# Run daily to check and manage SSL certificates

set -e

# Change to project directory
cd /home/marku/ai_workflow_engine

# Set up Python environment if needed
export PYTHONPATH=/home/marku/ai_workflow_engine:$PYTHONPATH

# Log file
LOG_FILE="/home/marku/ai_workflow_engine/logs/ssl_automation_cron.log"

# Create log directory if it doesn't exist
mkdir -p "$(dirname "$LOG_FILE")"

# Function to log with timestamp
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log_message "Starting SSL automation cycle"

# Run the automation
if python3 scripts/ssl_certificate_automation.py --run >> "$LOG_FILE" 2>&1; then
    log_message "SSL automation completed successfully"
else
    log_message "SSL automation failed with exit code $?"
    
    # Send alert on failure (implement your alerting here)
    # For example, you could send an email or webhook notification
fi

# Rotate logs if they get too large (keep last 100MB)
if [ -f "$LOG_FILE" ]; then
    LOG_SIZE=$(stat -c%s "$LOG_FILE")
    if [ "$LOG_SIZE" -gt 104857600 ]; then
        mv "$LOG_FILE" "${LOG_FILE}.old"
        log_message "Log rotated due to size"
    fi
fi

log_message "SSL automation cron job completed"