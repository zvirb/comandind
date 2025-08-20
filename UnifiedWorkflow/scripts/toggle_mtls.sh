#!/bin/bash
# scripts/toggle_mtls.sh
# Script to toggle mTLS on/off for local development

set -e

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

source "$SCRIPT_DIR/_common_functions.sh"

CADDYFILE_PATH="$PROJECT_ROOT/config/caddy/Caddyfile"
CADDYFILE_MTLS_LOCAL="$PROJECT_ROOT/config/caddy/Caddyfile.mtls-local"

usage() {
    echo "Usage: $0 [on|off|status]"
    echo "  on     - Enable mTLS for local development (requires client certificates)"
    echo "  off    - Disable mTLS for local development (default)"
    echo "  status - Show current mTLS status"
    exit 1
}

check_status() {
    if grep -q "client_auth" "$CADDYFILE_PATH" && grep -q "localhost.*client_auth" "$CADDYFILE_PATH"; then
        echo "enabled"
    else
        echo "disabled"
    fi
}

enable_mtls() {
    log_info "Enabling mTLS for local development..."
    
    if [ ! -f "$CADDYFILE_MTLS_LOCAL" ]; then
        log_error "mTLS configuration file not found: $CADDYFILE_MTLS_LOCAL"
        exit 1
    fi
    
    cp "$CADDYFILE_MTLS_LOCAL" "$CADDYFILE_PATH"
    log_success "✅ mTLS enabled for local development"
    log_info "You will need client certificates to access https://localhost"
    log_info "Run './scripts/configure_mtls_client.sh' to set up client certificates"
}

disable_mtls() {
    log_info "Disabling mTLS for local development..."
    
    # Remove client_auth configuration from localhost section only
    sed -i '/# Local development and internal access/,/^}$/{
        /client_auth {/,/}/ {
            /mode require_and_verify/d
            /trusted_ca_cert_file/d
            /client_auth {/d
            /        }/d
        }
    }' "$CADDYFILE_PATH"
    
    # Update the comment to reflect the change
    sed -i 's/# Local development and internal access (all services with mTLS enabled)/# Local development and internal access (all services - no mTLS for convenience)/' "$CADDYFILE_PATH"
    sed -i 's/# Enable TLS with our certificates and require client certificates for mTLS/# Enable TLS with our certificates - no client certificate required for local development/' "$CADDYFILE_PATH"
    
    log_success "✅ mTLS disabled for local development"
    log_info "You can now access https://localhost without client certificates"
}

restart_caddy() {
    log_info "Restarting Caddy to apply configuration changes..."
    if docker-compose ps caddy_reverse_proxy | grep -q "Up"; then
        docker-compose restart caddy_reverse_proxy
        log_success "✅ Caddy restarted successfully"
    else
        log_warn "Caddy is not running. Start the services with 'docker-compose up -d'"
    fi
}

case "${1:-}" in
    "on"|"enable")
        if [ "$(check_status)" = "enabled" ]; then
            log_info "mTLS is already enabled for local development"
        else
            enable_mtls
            restart_caddy
        fi
        ;;
    "off"|"disable")
        if [ "$(check_status)" = "disabled" ]; then
            log_info "mTLS is already disabled for local development"
        else
            disable_mtls
            restart_caddy
        fi
        ;;
    "status")
        status=$(check_status)
        log_info "mTLS for local development: $status"
        
        if [ "$status" = "enabled" ]; then
            log_info "Access requires client certificates:"
            log_info "  Production: https://aiwfe.com (always requires mTLS)"
            log_info "  Local: https://localhost (requires mTLS)"
        else
            log_info "Access without client certificates:"
            log_info "  Production: https://aiwfe.com (always requires mTLS)"
            log_info "  Local: https://localhost (no mTLS required)"
        fi
        ;;
    *)
        usage
        ;;
esac