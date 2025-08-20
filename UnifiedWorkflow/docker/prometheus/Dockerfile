# Stage 1: Use the official image as a source for the application files.
FROM prom/prometheus:latest AS source

# Stage 2: Build the final image from a standard Alpine base.
FROM alpine:latest

# The entrypoint wrapper script requires su-exec to drop privileges.
# We also install curl to make the healthcheck more robust.
RUN apk add --no-cache su-exec curl

# Copy the prometheus binary from the source image.
COPY --from=source /bin/prometheus /bin/prometheus

# Create directories for console libraries and consoles
RUN mkdir -p /etc/prometheus/console_libraries /etc/prometheus/consoles

# Copy the default console libraries and web files needed for the UI (if they exist)
# Use a script to handle missing directories gracefully
RUN --mount=from=source,target=/source \
    if [ -d /source/etc/prometheus/console_libraries ]; then \
        cp -r /source/etc/prometheus/console_libraries/* /etc/prometheus/console_libraries/ 2>/dev/null || true; \
    fi && \
    if [ -d /source/etc/prometheus/consoles ]; then \
        cp -r /source/etc/prometheus/consoles/* /etc/prometheus/consoles/ 2>/dev/null || true; \
    fi

# Create the data directory and set ownership to the 'nobody' user (UID 65534),
# which the entrypoint wrapper script will use to run the process.
RUN mkdir -p /prometheus && chown -R 65534:65534 /prometheus