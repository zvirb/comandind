#!/bin/bash

# Cloudflare Manager - DNS & Development Mode Controller
# Handles DNS updates, development mode, SSL settings, and monitoring

set -euo pipefail

DOMAIN="aiwfe.com"
CONFIG_FILE="/home/marku/ai_workflow_engine/config/dynamic_dns_config.json"
API_TOKEN_FILE="/home/marku/ai_workflow_engine/secrets/dns_api_token.txt"
LOG_FILE="/home/marku/ai_workflow_engine/logs/cloudflare_manager.log"

# Load API token
load_api_token() {
    if [ ! -f "$API_TOKEN_FILE" ]; then
        log_error "API token file not found: $API_TOKEN_FILE"
        exit 1
    fi
    API_TOKEN=$(cat "$API_TOKEN_FILE")
}

# Get current server IP
get_current_ip() {
    local ip=""
    for service in "https://ipv4.icanhazip.com" "https://api.ipify.org" "https://checkip.amazonaws.com"; do
        ip=$(curl -s --max-time 10 "$service" | tr -d '[:space:]') && break
    done
    
    if [[ "$ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        echo "$ip"
    else
        log_error "Failed to get current IP address"
        return 1
    fi
}

# Get DNS resolved IP
get_dns_ip() {
    local domain=$1
    dig +short "$domain" @8.8.8.8 | head -1
}

# Get zone ID for domain
get_zone_id() {
    local domain=$1
    local response=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones?name=$domain" \
        -H "Authorization: Bearer $API_TOKEN" \
        -H "Content-Type: application/json")
    
    local zone_id=$(echo "$response" | jq -r '.result[0].id')
    if [ "$zone_id" = "null" ]; then
        log_error "Failed to get zone ID for $domain"
        return 1
    fi
    echo "$zone_id"
}

# Update DNS A record
update_dns_record() {
    local domain=$1
    local new_ip=$2
    
    log_info "Updating DNS for $domain to $new_ip"
    
    local zone_id=$(get_zone_id "$domain")
    
    # Get record ID
    local record_id=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones/$zone_id/dns_records?name=$domain&type=A" \
        -H "Authorization: Bearer $API_TOKEN" \
        -H "Content-Type: application/json" | \
        jq -r '.result[0].id')
    
    if [ "$record_id" = "null" ]; then
        log_error "Failed to get record ID for $domain"
        return 1
    fi
    
    # Update record
    local response=$(curl -s -X PUT "https://api.cloudflare.com/client/v4/zones/$zone_id/dns_records/$record_id" \
        -H "Authorization: Bearer $API_TOKEN" \
        -H "Content-Type: application/json" \
        --data "{\"type\":\"A\",\"name\":\"$domain\",\"content\":\"$new_ip\",\"ttl\":300}")
    
    local success=$(echo "$response" | jq -r '.success')
    if [ "$success" = "true" ]; then
        log_info "✅ DNS update successful for $domain"
        return 0
    else
        log_error "❌ DNS update failed: $(echo "$response" | jq -r '.errors[0].message')"
        return 1
    fi
}

# Get development mode status
get_development_mode() {
    local domain=$1
    local zone_id=$(get_zone_id "$domain")
    
    local response=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones/$zone_id/settings/development_mode" \
        -H "Authorization: Bearer $API_TOKEN" \
        -H "Content-Type: application/json")
    
    local dev_mode=$(echo "$response" | jq -r '.result.value')
    echo "$dev_mode"
}

# Set development mode (on/off)
set_development_mode() {
    local domain=$1
    local mode=$2  # "on" or "off"
    
    log_info "Setting development mode $mode for $domain"
    
    local zone_id=$(get_zone_id "$domain")
    
    local response=$(curl -s -X PATCH "https://api.cloudflare.com/client/v4/zones/$zone_id/settings/development_mode" \
        -H "Authorization: Bearer $API_TOKEN" \
        -H "Content-Type: application/json" \
        --data "{\"value\":\"$mode\"}")
    
    local success=$(echo "$response" | jq -r '.success')
    if [ "$success" = "true" ]; then
        log_info "✅ Development mode set to $mode for $domain"
        return 0
    else
        log_error "❌ Failed to set development mode: $(echo "$response" | jq -r '.errors[0].message')"
        return 1
    fi
}

# Get SSL/TLS mode
get_ssl_mode() {
    local domain=$1
    local zone_id=$(get_zone_id "$domain")
    
    local response=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones/$zone_id/settings/ssl" \
        -H "Authorization: Bearer $API_TOKEN" \
        -H "Content-Type: application/json")
    
    local ssl_mode=$(echo "$response" | jq -r '.result.value')
    echo "$ssl_mode"
}

# Get security level
get_security_level() {
    local domain=$1
    local zone_id=$(get_zone_id "$domain")
    
    local response=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones/$zone_id/settings/security_level" \
        -H "Authorization: Bearer $API_TOKEN" \
        -H "Content-Type: application/json")
    
    local security_level=$(echo "$response" | jq -r '.result.value')
    echo "$security_level"
}

# Comprehensive status check
status_check() {
    local domain=$1
    
    log_info "=== Cloudflare Status for $domain ==="
    
    local current_ip=$(get_current_ip)
    local dns_ip=$(get_dns_ip "$domain")
    local dev_mode=$(get_development_mode "$domain")
    local ssl_mode=$(get_ssl_mode "$domain")
    local security_level=$(get_security_level "$domain")
    
    echo "Current Server IP: $current_ip"
    echo "DNS Resolved IP: $dns_ip"
    echo "Development Mode: $dev_mode"
    echo "SSL/TLS Mode: $ssl_mode"
    echo "Security Level: $security_level"
    
    if [ "$current_ip" != "$dns_ip" ]; then
        echo "🚨 IP MISMATCH - DNS update needed!"
        return 1
    else
        echo "✅ DNS is current"
    fi
    
    if [ "$dev_mode" = "on" ]; then
        echo "🔧 Development mode is ON (bypasses cache)"
    else
        echo "📦 Development mode is OFF (caching enabled)"
    fi
}

# Automatic fix for common issues
auto_fix() {
    local domain=$1
    
    log_info "Running auto-fix for $domain"
    
    local current_ip=$(get_current_ip)
    local dns_ip=$(get_dns_ip "$domain")
    local dev_mode=$(get_development_mode "$domain")
    
    local fixed=0
    
    # Fix IP mismatch
    if [ "$current_ip" != "$dns_ip" ]; then
        log_info "Fixing IP mismatch: $dns_ip -> $current_ip"
        if update_dns_record "$domain" "$current_ip"; then
            fixed=1
        fi
    fi
    
    # Enable development mode for testing (if not already on)
    if [ "$dev_mode" = "off" ]; then
        log_info "Enabling development mode for immediate updates"
        if set_development_mode "$domain" "on"; then
            fixed=1
        fi
    fi
    
    if [ $fixed -eq 1 ]; then
        log_info "✅ Auto-fix completed - waiting 30 seconds for propagation"
        sleep 30
        status_check "$domain"
    else
        log_info "ℹ️  No fixes needed"
    fi
}

# Logging functions
log_info() {
    local message="[$(date -Iseconds)] INFO: $1"
    echo "$message" | tee -a "$LOG_FILE"
}

log_error() {
    local message="[$(date -Iseconds)] ERROR: $1"
    echo "$message" | tee -a "$LOG_FILE"
}

# Main function
main() {
    load_api_token
    
    case "${1:-status}" in
        "status")
            status_check "$DOMAIN"
            ;;
        "update-dns")
            current_ip=$(get_current_ip)
            update_dns_record "$DOMAIN" "$current_ip"
            ;;
        "dev-on")
            set_development_mode "$DOMAIN" "on"
            ;;
        "dev-off")
            set_development_mode "$DOMAIN" "off"
            ;;
        "auto-fix")
            auto_fix "$DOMAIN"
            ;;
        "monitor")
            # Continuous monitoring mode
            log_info "Starting continuous monitoring mode"
            while true; do
                auto_fix "$DOMAIN"
                sleep 300  # Check every 5 minutes
            done
            ;;
        *)
            echo "Usage: $0 {status|update-dns|dev-on|dev-off|auto-fix|monitor}"
            echo ""
            echo "Commands:"
            echo "  status      - Show current DNS and Cloudflare settings"
            echo "  update-dns  - Update DNS A record to current server IP"
            echo "  dev-on      - Enable development mode (bypass cache)"
            echo "  dev-off     - Disable development mode"
            echo "  auto-fix    - Automatically fix common issues"
            echo "  monitor     - Continuous monitoring and auto-fix"
            exit 1
            ;;
    esac
}

main "$@"