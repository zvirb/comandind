# docker/postgres-exporter/Dockerfile

# Use the official image as a source for the binary
FROM prometheuscommunity/postgres-exporter:v0.15.0 AS source

# Use a standard Alpine image as the final base
FROM alpine:latest

# Install curl for the healthcheck and ca-certificates for TLS
RUN apk --no-cache add curl ca-certificates

# Create a dedicated, unprivileged user for the exporter, matching the
# best practice from the official image.
RUN addgroup -S postgres_exporter && \
    adduser -S -G postgres_exporter postgres_exporter

# Copy the exporter binary from the source stage
COPY --from=source /bin/postgres_exporter /usr/local/bin/postgres_exporter

# Switch to the unprivileged user
USER postgres_exporter

# The command will be provided by docker-compose.yml, which handles credentials.
CMD ["postgres_exporter"]