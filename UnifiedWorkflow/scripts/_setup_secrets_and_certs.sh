#!/bin/bash
# scripts/_setup_secrets_and_certs.sh

# Exit immediately if a command exits with a non-zero status.
set -e

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

source "$SCRIPT_DIR/_common_functions.sh"

log_info "Setting up secrets and certificates..."

# Ensure directories exist
mkdir -p "$PROJECT_ROOT/secrets"

# --- Generate Environment Configuration Files ---
log_info "Generating environment configuration files..."

# Detect hostname for CORS configuration
HOSTNAME=$(hostname)
HOSTNAME_SHORT=$(hostname -s)
LOCAL_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "")

# Build CORS origins list including common variations and production domain
CORS_ORIGINS="https://localhost,https://127.0.0.1"
if [ -n "$HOSTNAME" ] && [ "$HOSTNAME" != "localhost" ]; then
    CORS_ORIGINS="$CORS_ORIGINS,https://$HOSTNAME"
fi
if [ -n "$HOSTNAME_SHORT" ] && [ "$HOSTNAME_SHORT" != "$HOSTNAME" ] && [ "$HOSTNAME_SHORT" != "localhost" ]; then
    CORS_ORIGINS="$CORS_ORIGINS,https://$HOSTNAME_SHORT,https://$HOSTNAME_SHORT.local"
fi
if [ -n "$LOCAL_IP" ] && [ "$LOCAL_IP" != "127.0.0.1" ]; then
    CORS_ORIGINS="$CORS_ORIGINS,https://$LOCAL_IP"
fi

# Add production domain
CORS_ORIGINS="$CORS_ORIGINS,https://aiwfe.com,http://aiwfe.com"

log_info "Detected CORS origins: $CORS_ORIGINS"

# Generate .env file if it doesn't exist
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    if [ -f "$PROJECT_ROOT/.env.template" ]; then
        cp "$PROJECT_ROOT/.env.template" "$PROJECT_ROOT/.env"
        # Update CORS origins in the generated file
        if [ -n "$CORS_ORIGINS" ]; then
            sed -i "s|CORS_ALLOWED_ORIGINS=.*|CORS_ALLOWED_ORIGINS=$CORS_ORIGINS|g" "$PROJECT_ROOT/.env"
        fi
        log_info "Generated .env file from template with detected hostname configuration"
    else
        log_warn ".env.template not found, creating basic .env file"
        cat > "$PROJECT_ROOT/.env" <<EOF
# AI Workflow Engine Environment Configuration
ENVIRONMENT=production
DEBUG=false
POSTGRES_USER=app_user
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=ai_workflow_db
REDIS_HOST=redis
REDIS_PORT=6379
QDRANT_HOST=qdrant
QDRANT_PORT=6333
OLLAMA_API_BASE_URL=http://ollama:11434
OLLAMA_GENERATION_MODEL_NAME=llama3.2:3b
OLLAMA_EMBEDDING_MODEL_NAME=nomic-embed-text
CORS_ALLOWED_ORIGINS=$CORS_ORIGINS
EOF
    fi
else
    log_info ".env file already exists, skipping generation"
fi

# Generate local.env file if it doesn't exist  
if [ ! -f "$PROJECT_ROOT/local.env" ]; then
    if [ -f "$PROJECT_ROOT/local.env.template" ]; then
        cp "$PROJECT_ROOT/local.env.template" "$PROJECT_ROOT/local.env"
        # Update CORS origins and hostname in the generated file
        if [ -n "$CORS_ORIGINS" ]; then
            sed -i "s|CORS_ALLOWED_ORIGINS=.*|CORS_ALLOWED_ORIGINS=$CORS_ORIGINS|g" "$PROJECT_ROOT/local.env"
        fi
        if [ -n "$HOSTNAME" ]; then
            echo "# Detected hostname: $HOSTNAME" >> "$PROJECT_ROOT/local.env"
        fi
        log_info "Generated local.env file from template with detected hostname configuration"
    else
        log_warn "local.env.template not found, creating basic local.env file"
        cat > "$PROJECT_ROOT/local.env" <<EOF
# Local development environment overrides
ENVIRONMENT=development
DEBUG=true
WEBUI_PORT=5173
API_PORT=8000
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ai_workflow_engine
POSTGRES_USER=postgres
REDIS_HOST=localhost
REDIS_PORT=6379
QDRANT_HOST=localhost
QDRANT_PORT=6333
OLLAMA_API_BASE_URL=http://localhost:11434
CORS_ALLOWED_ORIGINS=$CORS_ORIGINS
# Detected hostname: $HOSTNAME
EOF
    fi
else
    log_info "local.env file already exists, skipping generation"
fi

# --- Generate Secrets ---
log_info "Generating application secrets..."

# Generate PostgreSQL password and pgbouncer userlist together to avoid race conditions.
if [ ! -f "$PROJECT_ROOT/secrets/postgres_password.txt" ] || [ ! -f "$PROJECT_ROOT/secrets/pgbouncer_userlist.txt" ]; then
    log_info "Generating PostgreSQL password and pgbouncer userlist..."
    POSTGRES_PASSWORD=$(openssl rand -base64 32)
    
    echo "$POSTGRES_PASSWORD" > "$PROJECT_ROOT/secrets/postgres_password.txt"
    log_info "Generated secrets/postgres_password.txt"

    cat > "$PROJECT_ROOT/secrets/pgbouncer_userlist.txt" <<EOF
"pgbouncer" "$POSTGRES_PASSWORD"
"app_user" "$POSTGRES_PASSWORD"
EOF
    log_info "Generated secrets/pgbouncer_userlist.txt"
else
    log_info "PostgreSQL password and pgbouncer userlist already exist, skipping generation."
fi

if [ ! -f "$PROJECT_ROOT/secrets/jwt_secret_key.txt" ]; then
    openssl rand -base64 64 > "$PROJECT_ROOT/secrets/jwt_secret_key.txt"
    log_info "Generated secrets/jwt_secret_key.txt"
fi
if [ ! -f "$PROJECT_ROOT/secrets/qdrant_api_key.txt" ]; then
    openssl rand -base64 48 | head -c 32 > "$PROJECT_ROOT/secrets/qdrant_api_key.txt"
    log_info "Generated secrets/qdrant_api_key.txt"

fi
if [ ! -f "$PROJECT_ROOT/secrets/api_key.txt" ]; then
    openssl rand -base64 32 > "$PROJECT_ROOT/secrets/api_key.txt"
    log_info "Generated secrets/api_key.txt"
fi

# Generate Redis secrets for ACL. This ensures both files are created if either is missing,
# preventing them from getting out of sync.
if [ ! -f "$PROJECT_ROOT/secrets/redis_password.txt" ] || [ ! -f "$PROJECT_ROOT/secrets/redis_users.acl" ]; then
    log_info "Redis secrets not found or incomplete. Regenerating..."
    # Generate a raw password for services that need it (redis healthcheck, api, worker).
    REDIS_PASS=$(openssl rand -base64 32 | tr -d '\n')
    echo "$REDIS_PASS" > "$PROJECT_ROOT/secrets/redis_password.txt"

    # The redis_exporter expects a JSON-formatted file. We create a separate secret for it.
    printf '"%s"' "$REDIS_PASS" > "$PROJECT_ROOT/secrets/redis_exporter_password.json"

    # Disable the insecure 'default' user and create a new app user.
    echo "user default off" > "$PROJECT_ROOT/secrets/redis_users.acl"
    echo "user lwe-app on >${REDIS_PASS} ~* &* +@all +@pubsub" >> "$PROJECT_ROOT/secrets/redis_users.acl"
    # Set proper permissions for Redis ACL file (must be readable by Docker containers)
    chmod 644 "$PROJECT_ROOT/secrets/redis_users.acl"
    log_info "Generated new redis_password.txt, redis_exporter_password.json, and redis_users.acl."
fi

# Prompt for admin user credentials if not already set (for db-seeder)
if [ ! -f "$PROJECT_ROOT/secrets/admin_email.txt" ] || [ ! -f "$PROJECT_ROOT/secrets/admin_password.txt" ]; then
    log_warn "Admin user credentials not found. Please provide them to create an initial admin account."
    read -p "Enter admin email: " ADMIN_EMAIL
    read -s -p "Enter admin password: " ADMIN_PASSWORD
    echo
    echo "$ADMIN_EMAIL" > "$PROJECT_ROOT/secrets/admin_email.txt"
    echo "$ADMIN_PASSWORD" > "$PROJECT_ROOT/secrets/admin_password.txt"
    log_info "Admin credentials saved to secrets/admin_email.txt and secrets/admin_password.txt"
fi

# Prompt for Google OAuth credentials if not already set (for Google services integration)
if [ ! -f "$PROJECT_ROOT/secrets/google_client_id.txt" ] || [ ! -f "$PROJECT_ROOT/secrets/google_client_secret.txt" ]; then
    log_warn "Google OAuth credentials not found. These are required for Google services integration (Calendar, Drive, Gmail)."
    log_info "You can get these credentials from the Google Cloud Console:"
    log_info "  1. Go to https://console.cloud.google.com/"
    log_info "  2. Create a new project or select existing one"
    log_info "  3. Enable the Google Calendar API, Google Drive API, and Gmail API"
    log_info "  4. Go to 'Credentials' and create OAuth 2.0 Client ID"
    log_info "  5. Set authorized redirect URIs to: https://your-domain.com/api/v1/oauth/google/callback"
    log_info ""
    read -p "Enter Google OAuth Client ID: " GOOGLE_CLIENT_ID
    read -s -p "Enter Google OAuth Client Secret: " GOOGLE_CLIENT_SECRET
    echo
    echo "$GOOGLE_CLIENT_ID" > "$PROJECT_ROOT/secrets/google_client_id.txt"
    echo "$GOOGLE_CLIENT_SECRET" > "$PROJECT_ROOT/secrets/google_client_secret.txt"
    log_info "Google OAuth credentials saved to secrets/google_client_id.txt and secrets/google_client_secret.txt"
fi

# --- Generate mkcert Certificates ---
log_info "Checking/Installing mkcert on host and generating certificates..."
if ! command -v mkcert &> /dev/null; then
    log_warn "mkcert not found on host. Please install it to generate trusted local certificates."
    log_warn "  MacOS: brew install mkcert && brew install nss"
    log_warn "  Linux: sudo apt install libnss3-tools"
    log_warn "         wget -O mkcert https://dl.filippo.io/mkcert/v1.4.3?for=linux/amd64 && chmod +x mkcert && sudo mv mkcert /usr/local/bin/"
    log_warn "Attempting to install mkcert CA on host (requires sudo)..."
    mkcert -install
    if [ $? -ne 0 ]; then
        log_error "Failed to install mkcert CA. Certificates might not be trusted by host browser."
    else
        log_info "mkcert CA installed on host."
    fi
else
    mkcert -install
    if [ $? -ne 0 ]; then
        log_error "Failed to install mkcert CA. Certificates might not be trusted by host browser."
    else
        log_info "mkcert CA already installed/updated on host."
    fi
fi

log_info "Generating unified certificate using host mkcert (ensures browser compatibility)..."
CERT_DOMAINS="localhost 127.0.0.1 postgres pgbouncer redis qdrant prometheus grafana cadvisor api worker webui caddy_reverse_proxy postgres_exporter pgbouncer_exporter api-migrate"

# Add detected hostnames to certificate domains
if [ -n "$HOSTNAME" ] && [ "$HOSTNAME" != "localhost" ]; then
    CERT_DOMAINS="$CERT_DOMAINS $HOSTNAME"
fi
if [ -n "$HOSTNAME_SHORT" ] && [ "$HOSTNAME_SHORT" != "$HOSTNAME" ] && [ "$HOSTNAME_SHORT" != "localhost" ]; then
    CERT_DOMAINS="$CERT_DOMAINS $HOSTNAME_SHORT $HOSTNAME_SHORT.local"
fi
if [ -n "$LOCAL_IP" ] && [ "$LOCAL_IP" != "127.0.0.1" ]; then
    CERT_DOMAINS="$CERT_DOMAINS $LOCAL_IP"
fi

# Add production domain
CERT_DOMAINS="$CERT_DOMAINS aiwfe.com"

log_info "Certificate domains: $CERT_DOMAINS"

# Generate server certificate using host mkcert to ensure it uses the browser-trusted CA
cd "$PROJECT_ROOT"
mkcert $CERT_DOMAINS
if [ $? -ne 0 ]; then
    log_error "Failed to generate certificates using host mkcert. Exiting."
    exit 1
fi

# Find the generated certificate files (mkcert names them based on first domain)
CERT_FILE=$(ls localhost+*.pem | grep -v '\-key\.pem' | head -n 1)
KEY_FILE=$(ls localhost+*-key.pem | head -n 1)

if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
    log_error "Generated certificate files not found. Exiting."
    exit 1
fi

log_info "Generated server certificate: $CERT_FILE and key: $KEY_FILE"

# Generate client certificate for mTLS
log_info "Generating client certificate for mTLS..."
mkcert -client webui-client
if [ $? -ne 0 ]; then
    log_error "Failed to generate client certificate using host mkcert. Exiting."
    exit 1
fi

# Find the generated client certificate files
# mkcert generates files with different naming patterns depending on the version
CLIENT_CERT_FILE=""
CLIENT_KEY_FILE=""

# Try different naming patterns
for pattern in "webui-client+*.pem" "webui-client-client.pem" "webui-client.pem"; do
    if ls $pattern 2>/dev/null | grep -v '\-key\.pem' >/dev/null 2>&1; then
        CLIENT_CERT_FILE=$(ls $pattern | grep -v '\-key\.pem' | head -n 1)
        break
    fi
done

for pattern in "webui-client+*-key.pem" "webui-client-client-key.pem" "webui-client-key.pem"; do
    if ls $pattern 2>/dev/null >/dev/null 2>&1; then
        CLIENT_KEY_FILE=$(ls $pattern | head -n 1)
        break
    fi
done

if [ ! -f "$CLIENT_CERT_FILE" ] || [ ! -f "$CLIENT_KEY_FILE" ]; then
    log_error "Generated client certificate files not found."
    log_info "Looking for files matching:"
    log_info "  Certificate: webui-client*.pem"
    log_info "  Key: webui-client*-key.pem"
    log_info "Found files:"
    ls -la webui-client* 2>/dev/null || log_info "  No webui-client* files found"
    exit 1
fi

log_info "Generated client certificate: $CLIENT_CERT_FILE and key: $CLIENT_KEY_FILE"

# Copy the root CA from mkcert's location to project root
MKCERT_CA_ROOT=$(mkcert -CAROOT)
cp "$MKCERT_CA_ROOT/rootCA.pem" "$PROJECT_ROOT/rootCA.pem"
log_info "Copied mkcert root CA to project root for container use."

# Rename generated files to standard names
mv "$CERT_FILE" unified-cert.pem
mv "$KEY_FILE" unified-key.pem
mv "$CLIENT_CERT_FILE" client-cert.pem
mv "$CLIENT_KEY_FILE" client-key.pem

# Ensure Docker volume exists
docker volume create ai_workflow_engine_certs >/dev/null 2>&1

# Copy certificates to Docker volume for all services that need them
log_info "Distributing certificates to Docker volume for all services..."
SERVICES="localhost 127.0.0.1 postgres pgbouncer redis qdrant prometheus grafana cadvisor api worker webui caddy_reverse_proxy postgres_exporter pgbouncer_exporter api-migrate mcp-server"

docker run --rm -v "ai_workflow_engine_certs:/certs" -v "$PROJECT_ROOT:/host" alpine:latest sh -c "
  # Copy unified cert and key to volume root
  cp /host/unified-cert.pem /certs/
  cp /host/unified-key.pem /certs/
  cp /host/rootCA.pem /certs/
  cp /host/client-cert.pem /certs/
  cp /host/client-key.pem /certs/
  
  # Create service-specific directories and copy certificates
  for service in $SERVICES; do
    mkdir -p /certs/\$service
    cp /host/unified-cert.pem /certs/\$service/
    cp /host/unified-key.pem /certs/\$service/
    cp /host/rootCA.pem /certs/\$service/
    cp /host/client-cert.pem /certs/\$service/
    cp /host/client-key.pem /certs/\$service/
  done
  
  # Set appropriate permissions
  chmod 600 /certs/unified-key.pem /certs/*/unified-key.pem
  chmod 600 /certs/client-key.pem /certs/*/client-key.pem
  chmod 644 /certs/unified-cert.pem /certs/*/unified-cert.pem
  chmod 644 /certs/client-cert.pem /certs/*/client-cert.pem
  chmod 644 /certs/rootCA.pem /certs/*/rootCA.pem
"

# Clean up temporary files
rm unified-cert.pem unified-key.pem client-cert.pem client-key.pem

log_info "Certificates generated and distributed to Docker volume."

chmod 600 "$PROJECT_ROOT/secrets/"*.txt # Ensure secret files are only readable by owner
# Set proper permissions for Redis-specific files
if [ -f "$PROJECT_ROOT/secrets/redis_users.acl" ]; then
    chmod 644 "$PROJECT_ROOT/secrets/redis_users.acl"  # Must be readable by Docker containers
fi
if [ -f "$PROJECT_ROOT/secrets/redis_exporter_password.json" ]; then
    chmod 600 "$PROJECT_ROOT/secrets/redis_exporter_password.json"  # Keep restricted for security
fi
log_info "Certificate and secret permissions set."

# --- Install Root CA Certificate System-Wide ---
log_info "Installing root CA certificate system-wide for HTTPS trust..."
if [ -f "$PROJECT_ROOT/rootCA.pem" ]; then
    if command -v sudo >/dev/null 2>&1; then
        log_info "Installing root CA certificate to system trust store..."
        if sudo cp "$PROJECT_ROOT/rootCA.pem" /usr/local/share/ca-certificates/ai-workflow-rootCA.crt 2>/dev/null; then
            if sudo update-ca-certificates >/dev/null 2>&1; then
                log_success "✅ Root CA certificate installed system-wide. HTTPS localhost should now work securely."
                log_info "💡 You may need to restart your browser for the changes to take effect."
            else
                log_warn "⚠️  Failed to update CA certificates. You may need to manually run: sudo update-ca-certificates"
            fi
        else
            log_warn "⚠️  Could not copy root CA certificate. You may need to manually install it for HTTPS trust."
            log_info "Manual command: sudo cp $PROJECT_ROOT/rootCA.pem /usr/local/share/ca-certificates/ai-workflow-rootCA.crt && sudo update-ca-certificates"
        fi
    else
        log_warn "⚠️  sudo not available. Root CA certificate not installed system-wide."
        log_info "To enable HTTPS trust, manually run: sudo cp $PROJECT_ROOT/rootCA.pem /usr/local/share/ca-certificates/ai-workflow-rootCA.crt && sudo update-ca-certificates"
    fi
else
    log_warn "⚠️  rootCA.pem not found in project root. Cannot install system-wide certificate trust."
fi

log_info "Secrets and certificates setup complete."