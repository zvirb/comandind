#!/bin/bash
# Comprehensive Network Validation Script

# Logging setup
LOG_FILE="/home/marku/ai_workflow_engine/.claude/monitoring/network_validation.log"
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

# Monitoring configuration
CRITICAL_HOSTS=("aiwfe.com" "www.google.com" "dns.google")
NETWORK_TIMEOUT=5

# Metrics tracking
passed_tests=0
failed_tests=0

# Network Health Score Calculation
calculate_network_health_score() {
    local total_tests=$(( ${#CRITICAL_HOSTS[@]} * 3 ))
    local success_rate=$(( (passed_tests * 100) / total_tests ))
    echo $success_rate
}

# Perform comprehensive network tests
perform_network_tests() {
    passed_tests=0
    failed_tests=0
    echo "[$TIMESTAMP] Starting Network Validation" >> "$LOG_FILE"

    for host in "${CRITICAL_HOSTS[@]}"; do
        # DNS Resolution Test
        host_ip=$(timeout $NETWORK_TIMEOUT dig +short "$host" | head -n1)
        if [[ -n "$host_ip" ]]; then
            ((passed_tests++))
            echo "[$TIMESTAMP] DNS Resolution for $host: PASSED (IP: $host_ip)" >> "$LOG_FILE"
        else
            ((failed_tests++))
            echo "[$TIMESTAMP] DNS Resolution for $host: FAILED" >> "$LOG_FILE"
        fi

        # HTTP/HTTPS Connectivity Test
        http_status=$(timeout $NETWORK_TIMEOUT curl -sL -w "%{http_code}" "https://$host" -o /dev/null)
        if [[ "$http_status" == "200" ]]; then
            ((passed_tests++))
            echo "[$TIMESTAMP] HTTPS Connectivity for $host: PASSED (Status: $http_status)" >> "$LOG_FILE"
        else
            ((failed_tests++))
            echo "[$TIMESTAMP] HTTPS Connectivity for $host: FAILED (Status: $http_status)" >> "$LOG_FILE"
        fi

        # Ping Test
        ping_result=$(timeout $NETWORK_TIMEOUT ping -c 3 "$host" | grep -E "packet loss|rtt")
        if [[ -n "$ping_result" ]]; then
            ((passed_tests++))
            echo "[$TIMESTAMP] Ping Test for $host: PASSED" >> "$LOG_FILE"
        else
            ((failed_tests++))
            echo "[$TIMESTAMP] Ping Test for $host: FAILED" >> "$LOG_FILE"
        fi
    done

    # Calculate and log network health score
    HEALTH_SCORE=$(calculate_network_health_score)
    echo "[$TIMESTAMP] Network Health Score: $HEALTH_SCORE%" >> "$LOG_FILE"
    echo "$HEALTH_SCORE"
    
    # Export metrics for Prometheus
    cat << EOF > /tmp/network_metrics
# HELP network_health_score Overall network health percentage
# TYPE network_health_score gauge
network_health_score ${HEALTH_SCORE}

# HELP network_passed_tests Number of network tests passed
# TYPE network_passed_tests counter
network_passed_tests ${passed_tests}

# HELP network_failed_tests Number of network tests failed
# TYPE network_failed_tests counter
network_failed_tests ${failed_tests}
EOF
}

# Execute tests and collect metrics
perform_network_tests