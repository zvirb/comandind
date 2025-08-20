#!/bin/bash
# scripts/_setup_server.sh
# 
# Additional setup script for remote server deployments
# Handles server-specific configurations and common deployment issues

set -e

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

source "$SCRIPT_DIR/_common_functions.sh"

log_info "Starting server-specific setup..."

# --- Server Environment Detection ---
log_info "Detecting server environment..."

# Get system information
OS_NAME=$(lsb_release -si 2>/dev/null || echo "Unknown")
OS_VERSION=$(lsb_release -sr 2>/dev/null || echo "Unknown")
HOSTNAME=$(hostname)
HOSTNAME_FQDN=$(hostname -f 2>/dev/null || hostname)
LOCAL_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "")

log_info "Server details:"
log_info "  OS: $OS_NAME $OS_VERSION"
log_info "  Hostname: $HOSTNAME"
log_info "  FQDN: $HOSTNAME_FQDN"
log_info "  Local IP: $LOCAL_IP"

# --- Check Docker and Docker Compose ---
log_info "Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed. Please install Docker first."
    log_info "Installation guide: https://docs.docker.com/engine/install/"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    log_error "Docker Compose is not installed or is an old version."
    log_info "Please install Docker Compose v2. For most systems:"
    log_info "  sudo apt-get update && sudo apt-get install docker-compose-plugin"
    exit 1
fi

log_success "✅ Docker and Docker Compose are installed"

# --- Check System Resources ---
log_info "Checking system resources..."

TOTAL_MEM=$(free -g | awk '/^Mem:/{print $2}')
AVAILABLE_DISK=$(df -BG "$PROJECT_ROOT" | awk 'NR==2{print $4}' | sed 's/G//')

if [ "$TOTAL_MEM" -lt 4 ]; then
    log_warn "⚠️  Low memory detected ($TOTAL_MEM GB). AI Workflow Engine requires at least 4GB RAM."
    log_warn "Consider upgrading your server or enabling swap space."
fi

if [ "$AVAILABLE_DISK" -lt 10 ]; then
    log_warn "⚠️  Low disk space detected ($AVAILABLE_DISK GB available)."
    log_warn "AI Workflow Engine requires at least 10GB free space for Docker images and data."
fi

log_info "System resources: ${TOTAL_MEM}GB RAM, ${AVAILABLE_DISK}GB available disk"

# --- Check Network Ports ---
log_info "Checking if required ports are available..."

check_port() {
    local port=$1
    local service=$2
    if ss -tlun | grep -q ":$port "; then
        log_warn "⚠️  Port $port is already in use (required for $service)"
        log_info "You may need to stop other services or modify the configuration"
    else
        log_info "✅ Port $port is available ($service)"
    fi
}

check_port 8000 "API"
check_port 5173 "WebUI"
check_port 5432 "PostgreSQL"
check_port 6379 "Redis"
check_port 6333 "Qdrant"
check_port 11434 "Ollama"

# --- Check Firewall Configuration ---
log_info "Checking firewall configuration..."
if command -v ufw &> /dev/null; then
    UFW_STATUS=$(ufw status | head -1)
    log_info "UFW status: $UFW_STATUS"
    
    if echo "$UFW_STATUS" | grep -q "active"; then
        log_warn "⚠️  UFW firewall is active. You may need to allow ports 8000 and 5173:"
        log_info "  sudo ufw allow 8000"
        log_info "  sudo ufw allow 5173"
    fi
elif command -v firewall-cmd &> /dev/null; then
    FIREWALL_STATUS=$(firewall-cmd --state 2>/dev/null || echo "inactive")
    log_info "Firewalld status: $FIREWALL_STATUS"
    
    if [ "$FIREWALL_STATUS" = "running" ]; then
        log_warn "⚠️  Firewalld is active. You may need to allow ports 8000 and 5173:"
        log_info "  sudo firewall-cmd --permanent --add-port=8000/tcp"
        log_info "  sudo firewall-cmd --permanent --add-port=5173/tcp"
        log_info "  sudo firewall-cmd --reload"
    fi
fi

# --- Update Environment Files with Server Configuration ---
log_info "Updating environment files for server deployment..."

# Update .env file with server-specific settings
if [ -f "$PROJECT_ROOT/.env" ]; then
    # Add server hostname information
    if ! grep -q "SERVER_HOSTNAME" "$PROJECT_ROOT/.env"; then
        echo "" >> "$PROJECT_ROOT/.env"
        echo "# Server Configuration" >> "$PROJECT_ROOT/.env"
        echo "SERVER_HOSTNAME=$HOSTNAME" >> "$PROJECT_ROOT/.env"
        echo "SERVER_FQDN=$HOSTNAME_FQDN" >> "$PROJECT_ROOT/.env"
        if [ -n "$LOCAL_IP" ]; then
            echo "SERVER_LOCAL_IP=$LOCAL_IP" >> "$PROJECT_ROOT/.env"
        fi
    fi
    
    log_info "Updated .env file with server configuration"
fi

# --- Check SSL/TLS Certificate Requirements ---
log_info "Checking SSL/TLS configuration..."

if [ ! -f "$PROJECT_ROOT/rootCA.pem" ]; then
    log_warn "⚠️  Root CA certificate not found. HTTPS connections may not be trusted."
    log_info "Run the setup script to generate certificates: ./scripts/_setup_secrets_and_certs.sh"
fi

# --- Docker Group Check ---
log_info "Checking Docker permissions..."
if ! groups | grep -q docker; then
    log_warn "⚠️  Current user is not in the docker group."
    log_info "To run Docker without sudo, add your user to the docker group:"
    log_info "  sudo usermod -aG docker \$USER"
    log_info "  newgrp docker  # or logout and login again"
fi

# --- System Service Check ---
log_info "Checking system services..."
if ! systemctl is-enabled docker &>/dev/null; then
    log_warn "⚠️  Docker service is not enabled to start on boot."
    log_info "To enable Docker on boot: sudo systemctl enable docker"
fi

# --- Create Server-Specific Configuration ---
log_info "Creating server-specific configuration..."

cat > "$PROJECT_ROOT/server-info.env" <<EOF
# Server Information (Auto-generated)
SERVER_OS=$OS_NAME
SERVER_OS_VERSION=$OS_VERSION
SERVER_HOSTNAME=$HOSTNAME
SERVER_FQDN=$HOSTNAME_FQDN
SERVER_LOCAL_IP=$LOCAL_IP
SERVER_MEMORY_GB=$TOTAL_MEM
SERVER_DISK_AVAILABLE_GB=$AVAILABLE_DISK
SETUP_DATE=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
EOF

log_success "✅ Server-specific setup complete!"
log_info "📋 Server information saved to server-info.env"

# --- Final Recommendations ---
log_info ""
log_info "🚀 Next steps for server deployment:"
log_info "1. Run ./scripts/_setup_secrets_and_certs.sh if you haven't already"
log_info "2. Review and customize .env and local.env files"
log_info "3. Run ./scripts/_setup.sh to build the application"
log_info "4. Run ./run.sh to start the services"
log_info ""
log_info "🌐 After startup, access the application at:"
log_info "  - https://localhost:8000 (if accessing locally)"
log_info "  - https://$HOSTNAME:8000 (from other machines)"
if [ -n "$LOCAL_IP" ]; then
    log_info "  - https://$LOCAL_IP:8000 (via IP address)"
fi
log_info ""
log_info "📚 For troubleshooting, check the logs with:"
log_info "  docker compose logs -f"