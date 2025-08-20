# docker/cadvisor/Dockerfile

# Use the official image as a source for the binary
FROM gcr.io/cadvisor/cadvisor:v0.49.1 AS source

# Use a compatible Debian-based image for the final stage. The cadvisor
# binary is compiled for a glibc environment and has dependencies.
FROM debian:bookworm-slim

# Install curl for the healthcheck and libpfm4, the required shared library.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpfm4 && \
    rm -rf /var/lib/apt/lists/*

# Copy the cadvisor binary from the official image to a standard path
COPY --from=source /usr/bin/cadvisor /usr/bin/cadvisor

# The official image's entrypoint is just the binary. We replicate that.
ENTRYPOINT ["/usr/bin/cadvisor"]