# docker/certs-init/Dockerfile
# This container encapsulates the mkcert dependency for certificate generation.
# It is run as a one-off job by the _setup_secrets_and_certs.sh script.
FROM alpine:latest

# Install dependencies for mkcert
RUN apk add --no-cache \
    ca-certificates \
    curl \
    nss-tools

# Install mkcert from the official source
RUN curl -JLo mkcert "https://dl.filippo.io/mkcert/v1.4.3?for=linux/amd64" && \
    chmod +x mkcert && \
    mv mkcert /usr/local/bin/mkcert

# Copy the new entrypoint script that handles all cert generation logic.
COPY ./docker/certs-init/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set the working directory where the certs will be generated
WORKDIR /certs

ENTRYPOINT ["/entrypoint.sh"]