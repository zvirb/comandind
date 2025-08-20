# ==============================================================================
# Enhanced Caddy Reverse Proxy with mTLS Support
# AI Workflow Engine - Secure Gateway Service
# ==============================================================================

FROM caddy:2-alpine

# Install su-exec for privilege dropping capability
RUN apk add --no-cache su-exec

# Create the certificate directory structure
RUN mkdir -p /etc/certs

# Copy the entrypoint wrapper script (will be overridden by volume mount)
COPY docker/caddy_reverse_proxy/entrypoint-wrapper-mtls.sh /usr/local/bin/entrypoint-wrapper.sh
RUN chmod +x /usr/local/bin/entrypoint-wrapper.sh

# Set the entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint-wrapper.sh"]

# Default command (will be overridden by docker-compose)
CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]

# Health check endpoint
HEALTHCHECK --interval=15s --timeout=3s --retries=3 --start-period=30s \
    CMD wget --quiet --tries=1 --spider http://127.0.0.1:2019/config/ || exit 1

# Expose standard HTTP/HTTPS ports and admin API
EXPOSE 80 443 8443 2019

# Add labels for service identification
LABEL service="caddy_reverse_proxy"
LABEL component="gateway"
LABEL security="mtls"
LABEL version="2.0"