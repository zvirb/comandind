{
    # This is a global options block.
    # It disables automatic HTTPS, as we are providing our own certificates.
    # auto_https off
    # Enable the admin API for Caddy for health checks
    admin 127.0.0.1:2019
}

# Define the primary site address.
# Using a variable makes it easy to change.
(site_address) {
    localhost,
    192.168.0.95
}

# Main server block for the application.
localhost:80 {
    import site_address
    # Route all API requests to the backend 'api' service on port 8000, with TLS verification skipped.
    # The 'handle_path' directive ensures this rule is processed before the general one.
    handle /api/* {
        reverse_proxy https://api:8000 {
            transport http {
                tls_insecure_skip_verify
            }
        }
    }

    # Handle WebSocket connections, also skipping TLS verification for the backend.
    handle /ws/* {
        reverse_proxy https://api:8000 {
            transport http {
                tls_insecure_skip_verify
            }
        }
    }
    # Handle all other requests by proxying them to the SvelteKit
    # frontend 'webui' service, which runs on the default port 3000.
    handle {
        reverse_proxy webui:3000
    }
}
}
