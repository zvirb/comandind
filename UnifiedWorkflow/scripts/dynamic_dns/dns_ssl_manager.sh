#!/bin/bash

# Dynamic DNS SSL Certificate Manager
# Handles IP changes and certificate renewals automatically

set -euo pipefail

DOMAIN="aiwfe.com"
CONFIG_FILE="/home/marku/ai_workflow_engine/config/dynamic_dns_config.json"
LOG_FILE="/home/marku/ai_workflow_engine/logs/dns_ssl_manager.log"

# Load configuration
load_config() {
    if [ ! -f "$CONFIG_FILE" ]; then
        echo "Creating default configuration at $CONFIG_FILE"
        create_default_config
    fi
    
    DNS_PROVIDER=$(jq -r '.dns_provider' "$CONFIG_FILE")
    API_TOKEN_FILE=$(jq -r '.api_token_file' "$CONFIG_FILE")
    WEBHOOK_URL=$(jq -r '.webhook_url // empty' "$CONFIG_FILE")
    CHECK_INTERVAL=$(jq -r '.check_interval // 300' "$CONFIG_FILE")
}

create_default_config() {
    cat > "$CONFIG_FILE" << 'EOF'
{
  "dns_provider": "cloudflare",
  "api_token_file": "/run/secrets/dns_api_token",
  "webhook_url": "",
  "check_interval": 300,
  "domains": ["aiwfe.com"],
  "certificate_renewal_buffer": 30,
  "dns_propagation_timeout": 600
}
EOF
    echo "⚠️  Please configure your DNS provider API token in the config file"
}

# Get current server IP
get_current_ip() {
    # Try multiple services for reliability
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

# Update DNS record based on provider
update_dns_record() {
    local domain=$1
    local new_ip=$2
    
    case $DNS_PROVIDER in
        "cloudflare")
            update_cloudflare_dns "$domain" "$new_ip"
            ;;
        "route53")
            update_route53_dns "$domain" "$new_ip"
            ;;
        "digitalocean")
            update_digitalocean_dns "$domain" "$new_ip"
            ;;
        "namecheap")
            update_namecheap_dns "$domain" "$new_ip"
            ;;
        *)
            log_error "Unsupported DNS provider: $DNS_PROVIDER"
            return 1
            ;;
    esac
}

# Cloudflare DNS update
update_cloudflare_dns() {
    local domain=$1
    local new_ip=$2
    local api_token=$(cat "$API_TOKEN_FILE")
    
    log_info "Updating Cloudflare DNS for $domain to $new_ip"
    
    # Get zone ID
    local zone_id=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones?name=$domain" \
        -H "Authorization: Bearer $api_token" \
        -H "Content-Type: application/json" | \
        jq -r '.result[0].id')
    
    if [ "$zone_id" = "null" ]; then
        log_error "Failed to get zone ID for $domain"
        return 1
    fi
    
    # Get record ID
    local record_id=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones/$zone_id/dns_records?name=$domain&type=A" \
        -H "Authorization: Bearer $api_token" \
        -H "Content-Type: application/json" | \
        jq -r '.result[0].id')
    
    if [ "$record_id" = "null" ]; then
        log_error "Failed to get record ID for $domain"
        return 1
    fi
    
    # Update record
    local response=$(curl -s -X PUT "https://api.cloudflare.com/client/v4/zones/$zone_id/dns_records/$record_id" \
        -H "Authorization: Bearer $api_token" \
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

# Route53 DNS update
update_route53_dns() {
    local domain=$1
    local new_ip=$2
    
    log_info "Updating Route53 DNS for $domain to $new_ip"
    
    # Get hosted zone ID
    local zone_id=$(aws route53 list-hosted-zones --query "HostedZones[?Name=='$domain.'].Id" --output text | cut -d'/' -f3)
    
    if [ -z "$zone_id" ]; then
        log_error "Failed to get hosted zone ID for $domain"
        return 1
    fi
    
    # Create change batch
    local change_batch=$(cat << EOF
{
    "Changes": [{
        "Action": "UPSERT",
        "ResourceRecordSet": {
            "Name": "$domain",
            "Type": "A",
            "TTL": 300,
            "ResourceRecords": [{"Value": "$new_ip"}]
        }
    }]
}
EOF
)
    
    # Submit change
    local change_id=$(echo "$change_batch" | aws route53 change-resource-record-sets \
        --hosted-zone-id "$zone_id" \
        --change-batch file:///dev/stdin \
        --query 'ChangeInfo.Id' --output text)
    
    if [ -n "$change_id" ]; then
        log_info "✅ Route53 DNS update successful for $domain (Change ID: $change_id)"
        return 0
    else
        log_error "❌ Route53 DNS update failed"
        return 1
    fi
}

# Wait for DNS propagation
wait_for_dns_propagation() {
    local domain=$1
    local expected_ip=$2
    local timeout=${3:-600}
    local interval=30
    local elapsed=0
    
    log_info "Waiting for DNS propagation of $domain to $expected_ip"
    
    while [ $elapsed -lt $timeout ]; do
        local resolved_ip=$(get_dns_ip "$domain")
        
        if [ "$resolved_ip" = "$expected_ip" ]; then
            log_info "✅ DNS propagation complete ($elapsed seconds)"
            return 0
        fi
        
        log_info "⏳ DNS still shows $resolved_ip, waiting... ($elapsed/$timeout seconds)"
        sleep $interval
        elapsed=$((elapsed + interval))
    done
    
    log_error "❌ DNS propagation timeout after $timeout seconds"
    return 1
}

# Trigger certificate renewal
trigger_certificate_renewal() {
    log_info "Triggering certificate renewal"
    
    if docker-compose -f /home/marku/ai_workflow_engine/docker-compose-mtls.yml exec -T caddy_reverse_proxy caddy reload --config /etc/caddy/Caddyfile; then
        log_info "✅ Certificate renewal triggered successfully"
        return 0
    else
        log_error "❌ Failed to trigger certificate renewal"
        return 1
    fi
}

# Check certificate validity
check_certificate_validity() {
    local domain=$1
    
    local cert_info=$(echo | openssl s_client -servername "$domain" -connect "$domain:443" 2>/dev/null | openssl x509 -noout -dates 2>/dev/null)
    
    if [ -z "$cert_info" ]; then
        log_error "Cannot retrieve certificate for $domain"
        return 1
    fi
    
    local not_after=$(echo "$cert_info" | grep "notAfter" | cut -d= -f2)
    local expiry_timestamp=$(date -d "$not_after" +%s)
    local current_timestamp=$(date +%s)
    local days_until_expiry=$(( (expiry_timestamp - current_timestamp) / 86400 ))
    
    log_info "Certificate for $domain expires in $days_until_expiry days"
    
    if [ $days_until_expiry -lt 30 ]; then
        log_warn "Certificate for $domain expires soon ($days_until_expiry days)"
        return 1
    fi
    
    return 0
}

# Send notification
send_notification() {
    local level=$1
    local message=$2
    
    if [ -n "$WEBHOOK_URL" ]; then
        local emoji="ℹ️"
        case $level in
            "error") emoji="🚨" ;;
            "warning") emoji="⚠️" ;;
            "success") emoji="✅" ;;
        esac
        
        curl -s -X POST "$WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{\"text\": \"$emoji Dynamic DNS SSL Manager\\n$message\\nTime: $(date -Iseconds)\"}" \
            >/dev/null 2>&1
    fi
}

# Logging functions
log_info() {
    local message="[$(date -Iseconds)] INFO: $1"
    echo "$message" | tee -a "$LOG_FILE"
}

log_warn() {
    local message="[$(date -Iseconds)] WARN: $1"
    echo "$message" | tee -a "$LOG_FILE"
    send_notification "warning" "$1"
}

log_error() {
    local message="[$(date -Iseconds)] ERROR: $1"
    echo "$message" | tee -a "$LOG_FILE"
    send_notification "error" "$1"
}

log_success() {
    local message="[$(date -Iseconds)] SUCCESS: $1"
    echo "$message" | tee -a "$LOG_FILE"
    send_notification "success" "$1"
}

# Main monitoring loop
main_check() {
    log_info "Starting DNS/SSL check for $DOMAIN"
    
    local current_ip=$(get_current_ip)
    local dns_ip=$(get_dns_ip "$DOMAIN")
    
    log_info "Current server IP: $current_ip"
    log_info "DNS resolved IP: $dns_ip"
    
    if [ "$current_ip" != "$dns_ip" ]; then
        log_warn "IP mismatch detected. Server: $current_ip, DNS: $dns_ip"
        
        # Update DNS
        if update_dns_record "$DOMAIN" "$current_ip"; then
            log_success "DNS record updated to $current_ip"
            
            # Wait for propagation
            if wait_for_dns_propagation "$DOMAIN" "$current_ip"; then
                # Trigger certificate renewal
                if trigger_certificate_renewal; then
                    log_success "Certificate renewal process completed"
                else
                    log_error "Certificate renewal failed"
                fi
            else
                log_error "DNS propagation failed"
            fi
        else
            log_error "DNS update failed"
        fi
    else
        log_info "DNS is up to date"
        
        # Check certificate validity
        if ! check_certificate_validity "$DOMAIN"; then
            log_warn "Certificate needs attention"
        fi
    fi
}

# Daemon mode
run_daemon() {
    log_info "Starting Dynamic DNS SSL Manager daemon (interval: ${CHECK_INTERVAL}s)"
    
    while true; do
        main_check
        sleep "$CHECK_INTERVAL"
    done
}

# Command line interface
case "${1:-daemon}" in
    "daemon")
        load_config
        run_daemon
        ;;
    "check")
        load_config
        main_check
        ;;
    "update")
        load_config
        current_ip=$(get_current_ip)
        update_dns_record "$DOMAIN" "$current_ip"
        ;;
    "status")
        load_config
        echo "Domain: $DOMAIN"
        echo "Current IP: $(get_current_ip)"
        echo "DNS IP: $(get_dns_ip "$DOMAIN")"
        check_certificate_validity "$DOMAIN"
        ;;
    *)
        echo "Usage: $0 {daemon|check|update|status}"
        exit 1
        ;;
esac