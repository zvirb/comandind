#!/bin/bash
# scripts/setup_client_certificate_ubuntu.sh
# Automated script to set up client certificates for mTLS access on Ubuntu laptops

set -e

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

source "$SCRIPT_DIR/_common_functions.sh"

log_info "🔐 Ubuntu Client Certificate Setup"
log_info "=================================="
log_info "This script will set up client certificates for mTLS access to aiwfe.com"

# Function to detect available browsers
detect_browsers() {
    local browsers=()
    
    if command -v google-chrome >/dev/null 2>&1; then
        browsers+=("chrome")
    fi
    
    if command -v chromium-browser >/dev/null 2>&1; then
        browsers+=("chromium")
    fi
    
    if command -v firefox >/dev/null 2>&1; then
        browsers+=("firefox")
    fi
    
    echo "${browsers[@]}"
}

# Function to generate client certificate
generate_client_certificate() {
    log_info "📝 Generating client certificate..."
    
    if [ -f "$PROJECT_ROOT/webui-client.p12" ]; then
        log_info "Client certificate already exists"
        return 0
    fi
    
    # Run the certificate generation script
    if [ -f "$SCRIPT_DIR/configure_mtls_client.sh" ]; then
        "$SCRIPT_DIR/configure_mtls_client.sh"
    else
        log_error "❌ Certificate generation script not found"
        log_info "Please ensure you're running this from the project directory"
        return 1
    fi
}

# Function to install system-wide root CA
install_system_root_ca() {
    log_info "🏛️  Installing root CA certificate system-wide..."
    
    if [ ! -f "$PROJECT_ROOT/rootCA.pem" ]; then
        log_error "❌ Root CA certificate not found"
        return 1
    fi
    
    # Install system-wide
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

# Function to set up Chrome/Chromium
setup_chrome_certificate() {
    local browser="$1"
    local browser_name="$2"
    
    log_info "🌐 Setting up certificates for $browser_name..."
    
    # Chrome/Chromium uses the system certificate store on Linux
    log_info "Installing client certificate in NSS database..."
    
    # Find Chrome/Chromium profile directory
    local profile_dir=""
    if [ "$browser" = "chrome" ]; then
        profile_dir="$HOME/.config/google-chrome/Default"
    elif [ "$browser" = "chromium" ]; then
        profile_dir="$HOME/.config/chromium/Default"
    fi
    
    if [ ! -d "$profile_dir" ]; then
        log_warn "⚠️  $browser_name profile directory not found"
        log_info "Please run $browser_name once to create the profile"
        return 1
    fi
    
    # Use pk12util to import the certificate
    if command -v pk12util >/dev/null 2>&1; then
        # Import client certificate
        if pk12util -i "$PROJECT_ROOT/webui-client.p12" -d sql:"$profile_dir" -W ""; then
            log_success "✅ Client certificate imported to $browser_name"
        else
            log_error "❌ Failed to import client certificate to $browser_name"
        fi
        
        # Import root CA
        if certutil -A -n "AI Workflow Engine Root CA" -t "CT,C,C" -i "$PROJECT_ROOT/rootCA.pem" -d sql:"$profile_dir"; then
            log_success "✅ Root CA imported to $browser_name"
        else
            log_error "❌ Failed to import root CA to $browser_name"
        fi
    else
        log_warn "⚠️  pk12util not found. Installing libnss3-tools..."
        if sudo apt-get update && sudo apt-get install -y libnss3-tools; then
            # Retry after installation
            if pk12util -i "$PROJECT_ROOT/webui-client.p12" -d sql:"$profile_dir" -W ""; then
                log_success "✅ Client certificate imported to $browser_name"
            fi
            if certutil -A -n "AI Workflow Engine Root CA" -t "CT,C,C" -i "$PROJECT_ROOT/rootCA.pem" -d sql:"$profile_dir"; then
                log_success "✅ Root CA imported to $browser_name"
            fi
        else
            log_error "❌ Failed to install libnss3-tools"
            return 1
        fi
    fi
}

# Function to set up Firefox
setup_firefox_certificate() {
    log_info "🦊 Setting up certificates for Firefox..."
    
    # Find Firefox profile directory
    local firefox_dir="$HOME/.mozilla/firefox"
    if [ ! -d "$firefox_dir" ]; then
        log_warn "⚠️  Firefox profile directory not found"
        log_info "Please run Firefox once to create the profile"
        return 1
    fi
    
    # Find the default profile
    local profile_dir=$(find "$firefox_dir" -name "*.default*" -type d | head -n 1)
    if [ -z "$profile_dir" ]; then
        log_warn "⚠️  Firefox default profile not found"
        return 1
    fi
    
    log_info "Found Firefox profile: $profile_dir"
    
    # Use pk12util to import the certificate
    if command -v pk12util >/dev/null 2>&1; then
        # Import client certificate
        if pk12util -i "$PROJECT_ROOT/webui-client.p12" -d sql:"$profile_dir" -W ""; then
            log_success "✅ Client certificate imported to Firefox"
        else
            log_error "❌ Failed to import client certificate to Firefox"
        fi
        
        # Import root CA
        if certutil -A -n "AI Workflow Engine Root CA" -t "CT,C,C" -i "$PROJECT_ROOT/rootCA.pem" -d sql:"$profile_dir"; then
            log_success "✅ Root CA imported to Firefox"
        else
            log_error "❌ Failed to import root CA to Firefox"
        fi
    else
        log_warn "⚠️  pk12util not found. Installing libnss3-tools..."
        if sudo apt-get update && sudo apt-get install -y libnss3-tools; then
            # Retry after installation
            if pk12util -i "$PROJECT_ROOT/webui-client.p12" -d sql:"$profile_dir" -W ""; then
                log_success "✅ Client certificate imported to Firefox"
            fi
            if certutil -A -n "AI Workflow Engine Root CA" -t "CT,C,C" -i "$PROJECT_ROOT/rootCA.pem" -d sql:"$profile_dir"; then
                log_success "✅ Root CA imported to Firefox"
            fi
        else
            log_error "❌ Failed to install libnss3-tools"
            return 1
        fi
    fi
}

# Function to provide manual setup instructions
provide_manual_instructions() {
    log_info "📋 Manual Setup Instructions"
    log_info "============================"
    
    log_info "If automatic setup failed, you can manually install certificates:"
    echo ""
    
    log_info "For Chrome/Chromium:"
    echo "1. Go to chrome://settings/certificates"
    echo "2. Click 'Personal' tab → 'Import'"
    echo "3. Select: $PROJECT_ROOT/webui-client.p12"
    echo "4. Leave password empty"
    echo "5. Click 'Authorities' tab → 'Import'"
    echo "6. Select: $PROJECT_ROOT/rootCA.pem"
    echo "7. Check 'Trust this certificate for identifying websites'"
    echo ""
    
    log_info "For Firefox:"
    echo "1. Go to about:preferences#privacy"
    echo "2. Click 'View Certificates'"
    echo "3. Click 'Your Certificates' tab → 'Import'"
    echo "4. Select: $PROJECT_ROOT/webui-client.p12"
    echo "5. Leave password empty"
    echo "6. Click 'Authorities' tab → 'Import'"
    echo "7. Select: $PROJECT_ROOT/rootCA.pem"
    echo "8. Check 'Trust this CA to identify websites'"
    echo ""
}

# Function to test the setup
test_certificate_setup() {
    log_info "🧪 Testing certificate setup..."
    
    # Test if curl can connect with the client certificate
    if command -v curl >/dev/null 2>&1; then
        log_info "Testing connection to aiwfe.com with client certificate..."
        
        # Convert p12 to pem for curl
        if openssl pkcs12 -in "$PROJECT_ROOT/webui-client.p12" -out /tmp/client-cert.pem -clcerts -nokeys -passin pass: && \
           openssl pkcs12 -in "$PROJECT_ROOT/webui-client.p12" -out /tmp/client-key.pem -nocerts -nodes -passin pass:; then
            
            if curl -s --cert /tmp/client-cert.pem --key /tmp/client-key.pem --cacert "$PROJECT_ROOT/rootCA.pem" https://aiwfe.com >/dev/null 2>&1; then
                log_success "✅ Certificate setup appears to be working!"
            else
                log_warn "⚠️  Connection test failed. This may be normal if the server is not running."
            fi
            
            # Clean up temporary files
            rm -f /tmp/client-cert.pem /tmp/client-key.pem
        else
            log_warn "⚠️  Could not convert certificate for testing"
        fi
    else
        log_warn "⚠️  curl not available for testing"
    fi
}

# Function to create desktop shortcut
create_desktop_shortcut() {
    log_info "🖥️  Creating desktop shortcut..."
    
    local desktop_dir="$HOME/Desktop"
    if [ ! -d "$desktop_dir" ]; then
        desktop_dir="$HOME/デスクトップ"  # Japanese
        if [ ! -d "$desktop_dir" ]; then
            log_warn "⚠️  Desktop directory not found, skipping shortcut creation"
            return 1
        fi
    fi
    
    cat > "$desktop_dir/AI Workflow Engine.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Link
Name=AI Workflow Engine
Comment=Access AI Workflow Engine WebUI
Icon=applications-internet
URL=https://aiwfe.com
EOF
    
    chmod +x "$desktop_dir/AI Workflow Engine.desktop"
    log_success "✅ Desktop shortcut created"
}

# Main execution
main() {
    log_info "Starting automated certificate setup for Ubuntu..."
    
    # Check if running on Ubuntu
    if ! grep -q "Ubuntu" /etc/os-release 2>/dev/null; then
        log_warn "⚠️  This script is designed for Ubuntu. It may work on other Debian-based systems."
    fi
    
    # Generate client certificate if needed
    generate_client_certificate || return 1
    
    # Install system-wide root CA
    install_system_root_ca || return 1
    
    # Detect available browsers
    browsers=($(detect_browsers))
    if [ ${#browsers[@]} -eq 0 ]; then
        log_warn "⚠️  No supported browsers found"
        provide_manual_instructions
        return 1
    fi
    
    log_info "Found browsers: ${browsers[*]}"
    
    # Set up certificates for each browser
    for browser in "${browsers[@]}"; do
        case "$browser" in
            "chrome")
                setup_chrome_certificate "chrome" "Google Chrome"
                ;;
            "chromium")
                setup_chrome_certificate "chromium" "Chromium"
                ;;
            "firefox")
                setup_firefox_certificate
                ;;
        esac
    done
    
    # Test the setup
    test_certificate_setup
    
    # Create desktop shortcut
    create_desktop_shortcut
    
    # Provide final instructions
    log_success "🎯 Certificate setup complete!"
    log_info ""
    log_info "📋 Next steps:"
    log_info "1. Restart your browser(s)"
    log_info "2. Clear browser cache for aiwfe.com"
    log_info "3. Visit https://aiwfe.com"
    log_info "4. Select the 'AI Workflow Engine WebUI Client' certificate when prompted"
    log_info ""
    log_info "🔍 If you still have issues:"
    log_info "- Check that the server is running with mTLS enabled"
    log_info "- Try clearing all browser data for aiwfe.com"
    log_info "- Use the manual setup instructions above"
    log_info ""
    log_info "📁 Certificate files location:"
    log_info "- Client certificate: $PROJECT_ROOT/webui-client.p12"
    log_info "- Root CA: $PROJECT_ROOT/rootCA.pem"
    
    if [ ${#browsers[@]} -eq 0 ]; then
        provide_manual_instructions
    fi
}

# Handle command line arguments
case "${1:-}" in
    "manual")
        provide_manual_instructions
        ;;
    "test")
        test_certificate_setup
        ;;
    "chrome")
        setup_chrome_certificate "chrome" "Google Chrome"
        ;;
    "firefox")
        setup_firefox_certificate
        ;;
    *)
        main
        ;;
esac