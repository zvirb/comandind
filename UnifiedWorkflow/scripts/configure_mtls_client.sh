#!/bin/bash
# scripts/configure_mtls_client.sh
# Script to help users configure client certificates for mTLS access to the webui

set -e

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

source "$SCRIPT_DIR/_common_functions.sh"

log_info "Configuring client certificates for mTLS access to webui..."

# Check if client certificates already exist in project directory
if [ -f "$PROJECT_ROOT/client-cert.pem" ] && [ -f "$PROJECT_ROOT/client-key.pem" ] && [ -f "$PROJECT_ROOT/rootCA.pem" ]; then
    log_info "Client certificates already exist in project directory."
    
    # Fix permissions if needed
    if [ ! -w "$PROJECT_ROOT/client-key.pem" ] || [ ! -w "$PROJECT_ROOT/client-cert.pem" ] || [ ! -w "$PROJECT_ROOT/rootCA.pem" ]; then
        log_info "Fixing certificate file permissions..."
        
        # Try to fix permissions, use sudo if needed
        if ! chmod 600 "$PROJECT_ROOT/client-key.pem" 2>/dev/null; then
            log_warn "⚠️  Need sudo to fix permissions..."
            sudo chmod 600 "$PROJECT_ROOT/client-key.pem"
            sudo chmod 644 "$PROJECT_ROOT/client-cert.pem"
            sudo chmod 644 "$PROJECT_ROOT/rootCA.pem"
            sudo chown $(whoami):$(whoami) "$PROJECT_ROOT/client-key.pem" "$PROJECT_ROOT/client-cert.pem" "$PROJECT_ROOT/rootCA.pem"
        else
            chmod 644 "$PROJECT_ROOT/client-cert.pem"
            chmod 644 "$PROJECT_ROOT/rootCA.pem"
        fi
    fi
    
    log_success "✅ Client certificates ready in project directory."
    
elif [ ! -f "$PROJECT_ROOT/rootCA.pem" ]; then
    log_error "Root CA certificate not found. Please run scripts/_setup_secrets_and_certs.sh first."
    exit 1
    
else
    # Try to extract from Docker volume
    log_info "Extracting client certificates from Docker volume..."
    
    if docker run --rm -v "ai_workflow_engine_certs:/certs" -v "$PROJECT_ROOT:/host" alpine:latest sh -c "
      cp /certs/client-cert.pem /host/client-cert.pem 2>/dev/null || exit 1
      cp /certs/client-key.pem /host/client-key.pem 2>/dev/null || exit 1
      cp /certs/rootCA.pem /host/rootCA.pem 2>/dev/null || exit 1
    " 2>/dev/null; then
        log_success "✅ Client certificates extracted from Docker volume."
    else
        log_error "❌ Failed to extract certificates from Docker volume."
        log_info "This may happen if certificates haven't been generated yet."
        log_info "Please run: ./scripts/_setup_secrets_and_certs.sh"
        exit 1
    fi
    
    # Set appropriate permissions
    chmod 600 "$PROJECT_ROOT/client-key.pem"
    chmod 644 "$PROJECT_ROOT/client-cert.pem"
    chmod 644 "$PROJECT_ROOT/rootCA.pem"
    
    log_info "Client certificates extracted to project root."
fi

# Create PKCS#12 file for browser import
log_info "Creating PKCS#12 file for browser import..."

# Check if the p12 file already exists
if [ -f "$PROJECT_ROOT/webui-client.p12" ]; then
    log_info "PKCS#12 file already exists, recreating..."
    rm -f "$PROJECT_ROOT/webui-client.p12"
fi

# Prompt for a passphrase
echo "Please enter a passphrase for the webui-client.p12 file. This will be required by Android."
read -s -p "Enter Passphrase: " P12_PASSWORD
echo
read -s -p "Verify Passphrase: " P12_PASSWORD_VERIFY
echo

if [ "$P12_PASSWORD" != "$P12_PASSWORD_VERIFY" ]; then
    log_error "Passphrases do not match. Aborting."
    exit 1
fi

if [ -z "$P12_PASSWORD" ]; then
    log_error "Passphrase cannot be empty. Aborting."
    exit 1
fi

# Create the p12 file with the provided passphrase
if openssl pkcs12 -export -out "$PROJECT_ROOT/webui-client.p12" \
    -inkey "$PROJECT_ROOT/client-key.pem" \
    -in "$PROJECT_ROOT/client-cert.pem" \
    -certfile "$PROJECT_ROOT/rootCA.pem" \
    -name "AI Workflow Engine WebUI Client" \
    -passout "pass:$P12_PASSWORD"; then
    log_success "✅ PKCS#12 file created successfully!"
else
    log_error "❌ Failed to create PKCS#12 file."
    log_info "This may be due to missing or corrupted certificate files."
    log_info "Try running: ./scripts/_setup_secrets_and_certs.sh"
    exit 1
fi

# Set appropriate permissions for the p12 file
chmod 600 "$PROJECT_ROOT/webui-client.p12"

log_success "✅ Client certificate configuration complete!"
log_info ""
log_info "📋 Next steps to configure your browser:"
log_info ""
log_info "1. Import the client certificate into your browser:"
log_info "   - Chrome/Edge: Settings → Privacy and Security → Manage certificates → Personal → Import"
log_info "   - Firefox: Settings → Privacy & Security → Certificates → View Certificates → Your Certificates → Import"
log_info "   - Safari: Double-click the .p12 file to import into Keychain"
log_info ""
log_info "2. Import file: $PROJECT_ROOT/webui-client.p12"
log_info "   - Password: (leave empty - no password set)"
log_info ""
log_info "3. Access the webui at:"
log_info "   - Production: https://aiwfe.com"
log_info "   - Local: https://localhost"
log_info ""
log_info "4. Your browser will prompt you to select the client certificate when connecting."
log_info ""
log_info "⚠️  Important: Keep the client certificate files secure and do not share them."
log_info "   Files created: client-cert.pem, client-key.pem, webui-client.p12"

# Clean up temporary files (keep the .p12 file for user convenience)
rm -f "$PROJECT_ROOT/client-cert.pem" "$PROJECT_ROOT/client-key.pem"

log_info "Setup complete. You can now access the webui with mTLS authentication."