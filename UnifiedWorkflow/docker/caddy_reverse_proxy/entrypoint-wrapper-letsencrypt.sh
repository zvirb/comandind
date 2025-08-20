#!/bin/sh

# ==============================================================================
# Caddy Let's Encrypt Entrypoint Wrapper
# AI Workflow Engine - SSL Certificate Management
# ==============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[Caddy-LE]${NC} $*"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

# Print startup banner
log "Starting Caddy with Let's Encrypt DNS-01 Support"
log "================================================="

# Validate required environment variables
if [ -z "$DOMAIN" ]; then
    error "DOMAIN environment variable is required"
    exit 1
fi

if [ -z "$DNS_PROVIDER" ]; then
    error "DNS_PROVIDER environment variable is required"
    exit 1
fi

if [ -z "$DNS_API_TOKEN" ]; then
    error "DNS_API_TOKEN environment variable is required"
    exit 1
fi

if [ -z "$ACME_EMAIL" ]; then
    error "ACME_EMAIL environment variable is required"
    exit 1
fi

log "Configuration:"
log "  Domain: $DOMAIN"
log "  DNS Provider: $DNS_PROVIDER"
log "  ACME Email: $ACME_EMAIL"
log "  API Token: ${DNS_API_TOKEN:0:10}..."

# Validate DNS provider is supported
case "$DNS_PROVIDER" in
    cloudflare|route53|digitalocean|namecheap)
        success "DNS provider '$DNS_PROVIDER' is supported"
        ;;
    *)
        error "Unsupported DNS provider: $DNS_PROVIDER"
        error "Supported providers: cloudflare, route53, digitalocean, namecheap"
        exit 1
        ;;
esac

# Test DNS API token
log "Testing DNS API token..."
case "$DNS_PROVIDER" in
    cloudflare)
        if curl -s -f -H "Authorization: Bearer $DNS_API_TOKEN" \
           "https://api.cloudflare.com/client/v4/user/tokens/verify" | grep -q '"success":true'; then
            success "Cloudflare API token is valid"
        else
            error "Cloudflare API token is invalid or expired"
            error "Please generate a new token at: https://dash.cloudflare.com/profile/api-tokens"
            exit 1
        fi
        ;;
    *)
        warning "API token validation not implemented for $DNS_PROVIDER"
        ;;
esac

# Create log directory
mkdir -p /var/log/caddy
touch /var/log/caddy/access.log

# Set appropriate permissions
chown -R caddy:caddy /var/log/caddy /data /config 2>/dev/null || true

# Validate Caddyfile
log "Validating Caddyfile configuration..."
if caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile; then
    success "Caddyfile configuration is valid"
else
    error "Caddyfile configuration is invalid"
    exit 1
fi

# List available DNS providers (for debugging)
log "Available DNS providers:"
caddy list-modules | grep dns.providers || true

log "Starting Caddy server..."
success "Ready to acquire Let's Encrypt certificates via DNS-01 challenge"

# Execute the main command
exec "$@"