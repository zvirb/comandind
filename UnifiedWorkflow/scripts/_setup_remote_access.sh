#!/bin/bash
# scripts/_setup_remote_access.sh
# Sets up certificates and configuration for remote access to the AI Workflow Engine

# Exit immediately if a command exits with a non-zero status.
set -e

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

source "$SCRIPT_DIR/_common_functions.sh"

# Default values
EXTERNAL_HOSTNAME=""
EXTERNAL_IP=""
PORT_HTTP="80"
PORT_HTTPS="443"
INSTALL_CA="false"

print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Sets up AI Workflow Engine for remote access with proper SSL certificates."
    echo ""
    echo "OPTIONS:"
    echo "  -h, --hostname HOSTNAME    External hostname/domain (e.g., myserver.example.com)"
    echo "  -i, --ip IP_ADDRESS        External IP address (e.g., 192.168.1.100)"
    echo "  --http-port PORT          HTTP port (default: 80)"
    echo "  --https-port PORT         HTTPS port (default: 443)"
    echo "  --install-ca              Install root CA on this system for client access"
    echo "  --help                    Show this help message"
    echo ""
    echo "EXAMPLES:"
    echo "  # Setup for hostname access"
    echo "  $0 --hostname myserver.local"
    echo ""
    echo "  # Setup for IP access with custom ports"
    echo "  $0 --ip 192.168.1.100 --https-port 8443"
    echo ""
    echo "  # Setup with both hostname and IP"
    echo "  $0 --hostname myserver.local --ip 192.168.1.100 --install-ca"
    echo ""
    echo "NOTE: At least one of --hostname or --ip must be specified."
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--hostname)
            EXTERNAL_HOSTNAME="$2"
            shift 2
            ;;
        -i|--ip)
            EXTERNAL_IP="$2"
            shift 2
            ;;
        --http-port)
            PORT_HTTP="$2"
            shift 2
            ;;
        --https-port)
            PORT_HTTPS="$2"
            shift 2
            ;;
        --install-ca)
            INSTALL_CA="true"
            shift
            ;;
        --help)
            print_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Validate inputs
if [ -z "$EXTERNAL_HOSTNAME" ] && [ -z "$EXTERNAL_IP" ]; then
    log_error "Either --hostname or --ip (or both) must be specified."
    print_usage
    exit 1
fi

log_info "Setting up AI Workflow Engine for remote access..."
log_info "External hostname: ${EXTERNAL_HOSTNAME:-"(not set)"}"
log_info "External IP: ${EXTERNAL_IP:-"(not set)"}"
log_info "HTTP port: $PORT_HTTP"
log_info "HTTPS port: $PORT_HTTPS"

# Check for mkcert
if ! command -v mkcert >/dev/null 2>&1; then
    log_error "mkcert is required but not installed. Please install mkcert first."
    log_info "Installation: https://github.com/FiloSottile/mkcert#installation"
    exit 1
fi

# Install mkcert CA if requested or if not already installed
if [ "$INSTALL_CA" = "true" ] || ! mkcert -CAROOT >/dev/null 2>&1; then
    log_info "Installing mkcert CA for this system..."
    mkcert -install
    if [ $? -ne 0 ]; then
        log_error "Failed to install mkcert CA."
        exit 1
    fi
    log_success "✅ mkcert CA installed. Browsers on this system will trust the certificates."
fi

# Build certificate domains list
CERT_DOMAINS="localhost 127.0.0.1"

if [ -n "$EXTERNAL_HOSTNAME" ]; then
    CERT_DOMAINS="$CERT_DOMAINS $EXTERNAL_HOSTNAME"
fi

if [ -n "$EXTERNAL_IP" ]; then
    CERT_DOMAINS="$CERT_DOMAINS $EXTERNAL_IP"
fi

# Add service domains for internal communication
CERT_DOMAINS="$CERT_DOMAINS postgres pgbouncer redis qdrant prometheus grafana cadvisor api worker webui caddy_reverse_proxy postgres_exporter pgbouncer_exporter api-migrate"

log_info "Generating SSL certificates for domains: $CERT_DOMAINS"

# Generate certificate using host mkcert
cd "$PROJECT_ROOT"
mkcert $CERT_DOMAINS
if [ $? -ne 0 ]; then
    log_error "Failed to generate certificates using mkcert."
    exit 1
fi

# Find the generated certificate files
CERT_FILE=$(ls localhost+*.pem | grep -v '\-key\.pem' | head -n 1)
KEY_FILE=$(ls localhost+*-key.pem | head -n 1)

if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
    log_error "Generated certificate files not found."
    exit 1
fi

log_info "Generated certificate: $CERT_FILE and key: $KEY_FILE"

# Copy the root CA from mkcert's location to project root
MKCERT_CA_ROOT=$(mkcert -CAROOT)
cp "$MKCERT_CA_ROOT/rootCA.pem" "$PROJECT_ROOT/rootCA.pem"
log_info "Copied mkcert root CA to project root."

# Rename generated files to standard names
mv "$CERT_FILE" unified-cert.pem
mv "$KEY_FILE" unified-key.pem

# Update docker-compose.yml to expose ports if they're non-standard
if [ "$PORT_HTTP" != "80" ] || [ "$PORT_HTTPS" != "443" ]; then
    log_info "Updating docker-compose.yml to expose custom ports..."
    
    # Create a backup
    cp "$PROJECT_ROOT/docker-compose.yml" "$PROJECT_ROOT/docker-compose.yml.backup"
    
    # Update the Caddy reverse proxy ports
    sed -i "s/\"80:80\"/\"$PORT_HTTP:80\"/g" "$PROJECT_ROOT/docker-compose.yml"
    sed -i "s/\"443:443\"/\"$PORT_HTTPS:443\"/g" "$PROJECT_ROOT/docker-compose.yml"
    
    log_info "Updated ports in docker-compose.yml (backup saved as docker-compose.yml.backup)"
fi

# Ensure Docker volume exists
docker volume create ai_workflow_engine_certs >/dev/null 2>&1

# Copy certificates to Docker volume for all services
log_info "Distributing certificates to Docker volume..."
SERVICES="localhost 127.0.0.1 postgres pgbouncer redis qdrant prometheus grafana cadvisor api worker webui caddy_reverse_proxy postgres_exporter pgbouncer_exporter api-migrate"

docker run --rm -v "ai_workflow_engine_certs:/certs" -v "$PROJECT_ROOT:/host" alpine:latest sh -c "
  # Copy unified cert and key to volume root
  cp /host/unified-cert.pem /certs/
  cp /host/unified-key.pem /certs/
  cp /host/rootCA.pem /certs/
  
  # Create service-specific directories and copy certificates
  for service in $SERVICES; do
    mkdir -p /certs/\$service
    cp /host/unified-cert.pem /certs/\$service/
    cp /host/unified-key.pem /certs/\$service/
    cp /host/rootCA.pem /certs/\$service/
  done
  
  # Set appropriate permissions
  chmod 600 /certs/unified-key.pem /certs/*/unified-key.pem
  chmod 644 /certs/unified-cert.pem /certs/*/unified-cert.pem  
  chmod 644 /certs/rootCA.pem /certs/*/rootCA.pem
"

# Clean up temporary files
rm unified-cert.pem unified-key.pem

# --- Configure CORS Origins ---
log_info "Configuring CORS allowed origins for remote access..."
CORS_ORIGINS="https://localhost"
if [ -n "$EXTERNAL_HOSTNAME" ]; then
    if [ "$PORT_HTTPS" = "443" ]; then
        CORS_ORIGINS="$CORS_ORIGINS,https://$EXTERNAL_HOSTNAME"
    else
        CORS_ORIGINS="$CORS_ORIGINS,https://$EXTERNAL_HOSTNAME:$PORT_HTTPS"
    fi
fi
if [ -n "$EXTERNAL_IP" ]; then
    if [ "$PORT_HTTPS" = "443" ]; then
        CORS_ORIGINS="$CORS_ORIGINS,https://$EXTERNAL_IP"
    else
        CORS_ORIGINS="$CORS_ORIGINS,https://$EXTERNAL_IP:$PORT_HTTPS"
    fi
fi

ENV_FILE="$PROJECT_ROOT/local.env"
touch "$ENV_FILE" # Ensure the file exists
sed -i '/^CORS_ALLOWED_ORIGINS=/d' "$ENV_FILE" # Remove existing line to avoid duplicates
echo "CORS_ALLOWED_ORIGINS=$CORS_ORIGINS" >> "$ENV_FILE"
log_success "✅ CORS origins configured in $ENV_FILE to allow: $CORS_ORIGINS"

log_success "✅ Remote access setup complete!"
echo ""
log_info "🌐 Your AI Workflow Engine is now configured for remote access:"

if [ -n "$EXTERNAL_HOSTNAME" ]; then
    if [ "$PORT_HTTPS" = "443" ]; then
        log_info "   📡 HTTPS: https://$EXTERNAL_HOSTNAME"
    else
        log_info "   📡 HTTPS: https://$EXTERNAL_HOSTNAME:$PORT_HTTPS"
    fi
fi

if [ -n "$EXTERNAL_IP" ]; then
    if [ "$PORT_HTTPS" = "443" ]; then
        log_info "   📡 HTTPS: https://$EXTERNAL_IP"
    else
        log_info "   📡 HTTPS: https://$EXTERNAL_IP:$PORT_HTTPS"
    fi
fi

echo ""
log_info "🔐 For clients to trust the SSL certificate:"
log_info "   1. Copy rootCA.pem to client machines"
log_info "   2. Install it in their browser/system trust store"
log_info "   3. Or use: mkcert -install (if mkcert is available on client)"
echo ""
log_info "🚀 To start the services:"
log_info "   ./run.sh"
echo ""

if [ "$INSTALL_CA" = "true" ]; then
    log_success "✅ Root CA installed on this system - browsers here will trust the certificates!"
fi

# Provide the root CA for easy distribution
log_info "📋 Root CA certificate location: $PROJECT_ROOT/rootCA.pem"
log_info "   Share this file with users who need to access the system securely."