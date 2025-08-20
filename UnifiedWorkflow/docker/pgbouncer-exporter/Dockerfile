# docker/pgbouncer-exporter/Dockerfile
# This Dockerfile creates a robust image for the pgbouncer-exporter.
# It downloads the static binary directly from GitHub releases to ensure reliability,
# avoiding potential issues with multi-stage builds from third-party images.

FROM alpine:latest

# Install ca-certificates for TLS connections. The shell is already present in alpine.
RUN apk --no-cache add ca-certificates curl

# Create a dedicated, unprivileged user for the exporter
RUN addgroup -S pgbouncer_exporter && \
    adduser -S -G pgbouncer_exporter pgbouncer_exporter

# Download and install the pgbouncer_exporter binary
ARG PGBOUNCER_EXPORTER_VERSION=v0.6.0
ARG TARGETARCH=amd64
ADD "https://github.com/prometheus-community/pgbouncer_exporter/releases/download/${PGBOUNCER_EXPORTER_VERSION}/pgbouncer_exporter-${PGBOUNCER_EXPORTER_VERSION#v}.linux-${TARGETARCH}.tar.gz" /tmp/
RUN tar -xzf /tmp/pgbouncer_exporter-*.tar.gz -C /tmp && \
    mv /tmp/pgbouncer_exporter-*/pgbouncer_exporter /usr/local/bin/ && \
    rm -rf /tmp/*

# Install su-exec for privilege dropping
RUN apk --no-cache add su-exec

CMD ["/usr/local/bin/pgbouncer_exporter"]