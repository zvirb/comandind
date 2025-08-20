#!/bin/bash
# scripts/setup_chrome_certificate_from_server.sh
# Quick setup script for Chrome certificates when accessing server via SSH

set -e

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

source "$SCRIPT_DIR/_common_functions.sh"

log_info "🔐 Chrome Certificate Setup (SSH Server Access)"
log_info "==============================================="

# Function to copy certificates from server
copy_certificates_from_server() {
    local server_address="$1"
    local server_path="$2"
    
    log_info "📥 Copying certificates from server..."
    
    # Copy client certificate
    if scp "$server_address:$server_path/webui-client.p12" "$PROJECT_ROOT/"; then
        log_success "✅ Client certificate copied"
    else
        log_error "❌ Failed to copy client certificate"
        return 1
    fi
    
    # Copy root CA
    if scp "$server_address:$server_path/rootCA.pem" "$PROJECT_ROOT/"; then
        log_success "✅ Root CA certificate copied"
    else
        log_error "❌ Failed to copy root CA certificate"
        return 1
    fi
}

# Function to generate certificates on server via SSH
generate_certificates_on_server() {
    local server_address="$1"
    local server_path="$2"
    
    log_info "🔧 Generating certificates on server..."
    
    # Run certificate generation on server
    if ssh "$server_address" "cd '$server_path' && ./scripts/configure_mtls_client.sh"; then
        log_success "✅ Certificates generated on server"
    else
        log_error "❌ Failed to generate certificates on server"
        return 1
    fi
}

# Function to install Chrome certificate
install_chrome_certificate() {
    log_info "🌐 Installing certificates for Chrome..."
    
    # Check if Chrome is installed
    if ! command -v google-chrome >/dev/null 2>&1; then
        log_error "❌ Google Chrome is not installed"
        log_info "Install Chrome first: sudo apt-get install google-chrome-stable"
        return 1
    fi
    
    # Install libnss3-tools if not available
    if ! command -v pk12util >/dev/null 2>&1; then
        log_info "Installing NSS tools..."
        if sudo apt-get update && sudo apt-get install -y libnss3-tools; then
            log_success "✅ NSS tools installed"
        else
            log_error "❌ Failed to install NSS tools"
            return 1
        fi
    fi
    
    # Find Chrome profile directory
    local chrome_profile="$HOME/.config/google-chrome/Default"
    if [ ! -d "$chrome_profile" ]; then
        log_warn "⚠️  Chrome profile not found. Please run Chrome once to create the profile."
        log_info "Starting Chrome to create profile..."
        google-chrome --new-window &
        sleep 3
        pkill -f "google-chrome" || true
        sleep 2
        
        if [ ! -d "$chrome_profile" ]; then
            log_error "❌ Could not create Chrome profile"
            return 1
        fi
    fi
    
    # Import client certificate
    log_info "Importing client certificate..."
    if pk12util -i "$PROJECT_ROOT/webui-client.p12" -d sql:"$chrome_profile" -W ""; then
        log_success "✅ Client certificate imported to Chrome"
    else
        log_error "❌ Failed to import client certificate to Chrome"
        return 1
    fi
    
    # Import root CA
    log_info "Importing root CA certificate..."
    if certutil -A -n "AI Workflow Engine Root CA" -t "CT,C,C" -i "$PROJECT_ROOT/rootCA.pem" -d sql:"$chrome_profile"; then
        log_success "✅ Root CA imported to Chrome"
    else
        log_error "❌ Failed to import root CA to Chrome"
        return 1
    fi
}

# Function to install system-wide root CA
install_system_root_ca() {
    log_info "🏛️  Installing root CA system-wide..."
    
    if sudo cp "$PROJECT_ROOT/rootCA.pem" /usr/local/share/ca-certificates/aiwfe-rootCA.crt; then
        if sudo update-ca-certificates; then
            log_success "✅ Root CA installed system-wide"
        else
            log_error "❌ Failed to update CA certificates"
            return 1
        fi
    else
        log_error "❌ Failed to copy root CA certificate"
        return 1
    fi
}

# Function to test the setup
test_chrome_setup() {
    log_info "🧪 Testing Chrome certificate setup..."
    
    # Test with curl if available
    if command -v curl >/dev/null 2>&1; then
        # Convert p12 to pem for curl test
        if openssl pkcs12 -in "$PROJECT_ROOT/webui-client.p12" -out /tmp/client-cert.pem -clcerts -nokeys -passin pass: 2>/dev/null && \
           openssl pkcs12 -in "$PROJECT_ROOT/webui-client.p12" -out /tmp/client-key.pem -nocerts -nodes -passin pass: 2>/dev/null; then
            
            if curl -s --cert /tmp/client-cert.pem --key /tmp/client-key.pem --cacert "$PROJECT_ROOT/rootCA.pem" https://aiwfe.com >/dev/null 2>&1; then
                log_success "✅ Certificate test passed!"
            else
                log_warn "⚠️  Connection test failed (server may not be running)"
            fi
            
            # Clean up
            rm -f /tmp/client-cert.pem /tmp/client-key.pem
        fi
    fi
}

# Function to provide usage instructions
show_usage() {
    log_info "Usage: $0 [server_address] [server_project_path]"
    log_info ""
    log_info "Examples:"
    log_info "  $0 user@server.com /home/user/ai_workflow_engine"
    log_info "  $0 192.168.1.100 /opt/ai_workflow_engine"
    log_info ""
    log_info "Or run interactively without arguments"
}

# Interactive setup
interactive_setup() {
    log_info "🔍 Interactive Setup"
    log_info "==================="
    
    # Get server address
    read -p "Enter server address (user@hostname or IP): " server_address
    if [ -z "$server_address" ]; then
        log_error "❌ Server address is required"
        return 1
    fi
    
    # Get server path
    read -p "Enter path to project on server [/home/$(whoami)/ai_workflow_engine]: " server_path
    if [ -z "$server_path" ]; then
        server_path="/home/$(whoami)/ai_workflow_engine"
    fi
    
    log_info "Server: $server_address"
    log_info "Path: $server_path"
    
    # Test SSH connection
    log_info "Testing SSH connection..."
    if ssh "$server_address" "cd '$server_path' && pwd" >/dev/null 2>&1; then
        log_success "✅ SSH connection successful"
    else
        log_error "❌ SSH connection failed"
        log_info "Make sure you can SSH to the server and the project path exists"
        return 1
    fi
    
    # Generate certificates on server
    generate_certificates_on_server "$server_address" "$server_path"
    
    # Copy certificates
    copy_certificates_from_server "$server_address" "$server_path"
    
    return 0
}

# Main setup function
main() {
    local server_address="$1"
    local server_path="$2"
    
    log_info "Starting Chrome certificate setup for mTLS access..."
    
    # If no arguments provided, run interactive setup
    if [ -z "$server_address" ]; then
        interactive_setup || return 1
    else
        # Use provided arguments
        if [ -z "$server_path" ]; then
            log_error "❌ Server path is required"
            show_usage
            return 1
        fi
        
        # Test SSH connection
        log_info "Testing SSH connection to $server_address..."
        if ! ssh "$server_address" "cd '$server_path' && pwd" >/dev/null 2>&1; then
            log_error "❌ SSH connection failed"
            return 1
        fi
        
        # Generate and copy certificates
        generate_certificates_on_server "$server_address" "$server_path"
        copy_certificates_from_server "$server_address" "$server_path"
    fi
    
    # Install system-wide root CA
    install_system_root_ca
    
    # Install Chrome certificate
    install_chrome_certificate
    
    # Test the setup
    test_chrome_setup
    
    # Final instructions
    log_success "🎯 Chrome certificate setup complete!"
    log_info ""
    log_info "📋 Next steps:"
    log_info "1. Close all Chrome windows"
    log_info "2. Restart Chrome"
    log_info "3. Clear cache for aiwfe.com (Chrome → Settings → Privacy → Clear browsing data)"
    log_info "4. Visit https://aiwfe.com"
    log_info "5. When prompted, select 'AI Workflow Engine WebUI Client' certificate"
    log_info ""
    log_info "🔍 If you still get ERR_BAD_SSL_CLIENT_AUTH_CERT:"
    log_info "- Make sure mTLS is enabled on the server"
    log_info "- Try incognito mode"
    log_info "- Check Chrome certificate manager: chrome://settings/certificates"
    log_info ""
    log_info "📂 Certificate files saved to:"
    log_info "- $PROJECT_ROOT/webui-client.p12"
    log_info "- $PROJECT_ROOT/rootCA.pem"
}

# Handle command line arguments
case "${1:-}" in
    "help"|"--help"|"-h")
        show_usage
        ;;
    "test")
        test_chrome_setup
        ;;
    *)
        main "$@"
        ;;
esac