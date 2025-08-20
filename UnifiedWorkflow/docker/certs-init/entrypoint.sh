#!/bin/sh
# docker/certs-init/entrypoint.sh

set -e

echo "Certs-Init: Starting certificate generation for domains: $@"

# --- Argument Parsing ---
# Separate mkcert flags (like -client) from hostnames. This is the key fix.
MKCERT_FLAGS=""
HOSTNAMES=""

for arg in "$@"; do
    case $arg in
        -*) # It's a flag if it starts with a hyphen.
            MKCERT_FLAGS="$MKCERT_FLAGS $arg"
            ;;
        *) # Otherwise, it's a hostname.
            HOSTNAMES="$HOSTNAMES $arg"
            ;;
    esac
done

# --- Certificate Generation ---
# Use the collected flags and hostnames to generate the certificate.
mkcert -cert-file unified-cert.pem -key-file unified-key.pem $MKCERT_FLAGS $HOSTNAMES

# The root CA is located at a standard path inside the container.
# We copy it to the shared volume so other containers can use it.
cp "$(mkcert -CAROOT)/rootCA.pem" .

echo "Certs-Init: Unified certificate, key, and root CA generated."

# --- Prepare Service-Specific Directories (for convenience) ---
echo "Certs-Init: Preparing service-specific certificate directories..."

for host in $HOSTNAMES; do
    # Use a POSIX-compliant case statement to map service names to user:group IDs.
    # This replaces the bash-specific associative array.
    case "$host" in
        postgres)           owner="70:70" ;;
        pgbouncer)          owner="101:101" ;;
        qdrant)             owner="1001:1001" ;;
        prometheus)         owner="65534:65534" ;;
        postgres_exporter)  owner="65534:65534" ;;
        pgbouncer_exporter) owner="65534:65534" ;;
        api)                owner="1000:1000" ;;
        worker)             owner="1000:1000" ;;
        webui)              owner="1000:1000" ;;
        api-migrate)        owner="1000:1000" ;;
        *)                  owner="root:root" ;;
    esac

    echo "Certs-Init:  - Preparing directory for '$host' with owner '$owner'"
    mkdir -p "$host"
    cp unified-cert.pem unified-key.pem rootCA.pem "$host/"
    chown -R "$owner" "$host"
done

echo "Certs-Init: All certificate directories prepared successfully."