#!/bin/bash
# scripts/_log_formatter.sh
# Utility functions for structured logging with timestamps and service identification

# Function to format log entries with standard structure
format_log_entry() {
    local severity="$1"
    local service="$2" 
    local message="$3"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S UTC')
    
    echo "[$timestamp] [$severity] [$service] $message"
}

# Function to extract service name from container name
extract_service_name() {
    local container_name="$1"
    # Remove project prefix and instance suffix
    echo "$container_name" | sed 's/^ai_workflow_engine-//' | sed 's/-[0-9]*$//'
}

# Function to determine severity level based on content
determine_severity() {
    local message="$1"
    
    if echo "$message" | grep -qi -E "(critical|fatal)"; then
        echo "CRITICAL"
    elif echo "$message" | grep -qi -E "(error|exception|failed)"; then
        echo "ERROR"
    elif echo "$message" | grep -qi -E "(warning|warn)"; then
        echo "WARNING"
    elif echo "$message" | grep -qi -E "(info|information)"; then
        echo "INFO"
    else
        echo "DEBUG"
    fi
}

# Function to write structured log entry to file
write_structured_log() {
    local log_file="$1"
    local severity="$2"
    local service="$3"
    local message="$4"
    
    local formatted_entry=$(format_log_entry "$severity" "$service" "$message")
    echo "$formatted_entry" >> "$log_file"
}

# Function to create log summary
create_log_summary() {
    local log_file="$1"
    local summary_file="$2"
    
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S UTC')
    
    echo "=== LOG SUMMARY GENERATED AT $timestamp ===" > "$summary_file"
    echo "" >> "$summary_file"
    
    # Count by severity
    echo "ERROR COUNTS BY SEVERITY:" >> "$summary_file"
    echo "CRITICAL: $(grep -c '\[CRITICAL\]' "$log_file" 2>/dev/null || echo 0)" >> "$summary_file"
    echo "ERROR:    $(grep -c '\[ERROR\]' "$log_file" 2>/dev/null || echo 0)" >> "$summary_file"
    echo "WARNING:  $(grep -c '\[WARNING\]' "$log_file" 2>/dev/null || echo 0)" >> "$summary_file"
    echo "" >> "$summary_file"
    
    # Count by service
    echo "ERROR COUNTS BY SERVICE:" >> "$summary_file"
    if [ -f "$log_file" ]; then
        grep -o '\[[a-zA-Z_-]*\]' "$log_file" | sort | uniq -c | sort -nr | head -10 >> "$summary_file"
    fi
    echo "" >> "$summary_file"
    
    # Recent critical/error entries
    echo "RECENT CRITICAL/ERROR ENTRIES (Last 20):" >> "$summary_file"
    if [ -f "$log_file" ]; then
        grep -E '\[(CRITICAL|ERROR)\]' "$log_file" | tail -20 >> "$summary_file"
    fi

    # Append noisy summary
    local noisy_summary_file="$(dirname "$summary_file")/noisy_summary.log"
    if [ -f "$noisy_summary_file" ]; then
        echo "" >> "$summary_file"
        cat "$noisy_summary_file" >> "$summary_file"
    fi
}