#!/bin/bash
# scripts/_setup_client_access.sh
# Sets up a client computer to trust the AI Workflow Engine's SSL certificates

# Exit immediately if a command exits with a non-zero status.
set -e

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# Default values
ROOT_CA_FILE=""
SERVER_URL=""
AUTO_INSTALL="false"

print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Sets up client computer to trust AI Workflow Engine SSL certificates."
    echo ""
    echo "OPTIONS:"
    echo "  -f, --ca-file FILE        Path to rootCA.pem file"
    echo "  -u, --url URL            Server URL to test (e.g., https://myserver.local)"
    echo "  -y, --yes                Automatically install without prompting"
    echo "  --help                   Show this help message"
    echo ""
    echo "EXAMPLES:"
    echo "  # Install CA and test connection"
    echo "  $0 --ca-file rootCA.pem --url https://myserver.local"
    echo ""
    echo "  # Auto-install without prompts"
    echo "  $0 --ca-file rootCA.pem --yes"
    echo ""
    echo "NOTE: This script will install the root CA certificate system-wide."
    echo "      You may need sudo permissions for installation."
}

log_info() {
    echo -e "\e[34m\e[1mINFO:\e[0m $1"
}

log_success() {
    echo -e "\e[32m\e[1mSUCCESS:\e[0m $1"
}

log_warn() {
    echo -e "\e[33m\e[1mWARN:\e[0m $1"
}

log_error() {
    echo -e "\e[31m\e[1mERROR:\e[0m $1"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--ca-file)
            ROOT_CA_FILE="$2"
            shift 2
            ;;
        -u|--url)
            SERVER_URL="$2"
            shift 2
            ;;
        -y|--yes)
            AUTO_INSTALL="true"
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
if [ -z "$ROOT_CA_FILE" ]; then
    log_error "Root CA file must be specified with --ca-file"
    print_usage
    exit 1
fi

if [ ! -f "$ROOT_CA_FILE" ]; then
    log_error "Root CA file not found: $ROOT_CA_FILE"
    exit 1
fi

log_info "Setting up client access to AI Workflow Engine..."
log_info "Root CA file: $ROOT_CA_FILE"
log_info "Test URL: ${SERVER_URL:-"(not specified)"}"

# Check if running as root for system-wide installation
if [ "$EUID" -eq 0 ]; then
    log_info "Running as root - will install system-wide."
    NEED_SUDO=""
else
    log_info "Running as regular user - will use sudo for system installation."
    NEED_SUDO="sudo"
fi

# Function to install CA on different systems
install_ca_linux() {
    log_info "Installing root CA for Linux system..."
    
    # Copy to system CA directory
    if $NEED_SUDO cp "$ROOT_CA_FILE" /usr/local/share/ca-certificates/ai-workflow-rootCA.crt; then
        log_info "Copied root CA to system certificate store."
    else
        log_error "Failed to copy root CA certificate."
        return 1
    fi
    
    # Update CA certificates
    if $NEED_SUDO update-ca-certificates; then
        log_success "✅ Root CA installed system-wide on Linux."
    else
        log_error "Failed to update CA certificates."
        return 1
    fi
}

install_ca_macos() {
    log_info "Installing root CA for macOS system..."
    
    # Add to system keychain
    if $NEED_SUDO security add-trusted-cert -d -r trustRoot -k /System/Library/Keychains/SystemRootCertificates.keychain "$ROOT_CA_FILE"; then
        log_success "✅ Root CA installed system-wide on macOS."
    else
        log_error "Failed to install root CA on macOS."
        return 1
    fi
}

# Detect OS and install accordingly
if [ -f /etc/os-release ]; then
    # Linux
    OS_TYPE="linux"
elif [ "$(uname)" = "Darwin" ]; then
    # macOS
    OS_TYPE="macos"
else
    log_error "Unsupported operating system."
    exit 1
fi

# Confirm installation unless auto-install is enabled
if [ "$AUTO_INSTALL" != "true" ]; then
    echo ""
    log_warn "This will install the root CA certificate system-wide."
    log_warn "This allows the system to trust SSL certificates issued by the AI Workflow Engine."
    echo ""
    read -p "Do you want to continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Installation cancelled."
        exit 0
    fi
fi

# Install the CA certificate
case $OS_TYPE in
    linux)
        install_ca_linux
        ;;
    macos)
        install_ca_macos
        ;;
esac

if [ $? -ne 0 ]; then
    log_error "Failed to install root CA certificate."
    exit 1
fi

# Test connection if URL provided
if [ -n "$SERVER_URL" ]; then
    log_info "Testing connection to $SERVER_URL..."
    
    if command -v curl >/dev/null 2>&1; then
        if curl -s -f "$SERVER_URL" >/dev/null; then
            log_success "✅ Successfully connected to $SERVER_URL with trusted certificate!"
        else
            log_warn "⚠️  Connection test failed. The server might not be running or accessible."
        fi
    elif command -v wget >/dev/null 2>&1; then
        if wget -q --spider "$SERVER_URL"; then
            log_success "✅ Successfully connected to $SERVER_URL with trusted certificate!"
        else
            log_warn "⚠️  Connection test failed. The server might not be running or accessible."
        fi
    else
        log_info "No curl or wget available for connection testing."
    fi
fi

echo ""
log_success "🎉 Client setup complete!"
log_info "🌐 You can now securely access the AI Workflow Engine without certificate warnings."
echo ""
log_info "💡 Note: You may need to restart your browser for the changes to take effect."

if [ -n "$SERVER_URL" ]; then
    log_info "🔗 Try accessing: $SERVER_URL"
fi