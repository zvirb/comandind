
# The official ollama/ollama image is a minimal "distroless" image that lacks
# a shell and package manager. This prevents adding utilities like 'curl',
# which is needed for the healthcheck in docker-compose.yml.
#
# This multi-stage Dockerfile solves this by:
# 1. Using a 'builder' stage to extract the 'ollama' binary from the official image.
# 2. Creating a final image based on a standard image (alpine) that includes a
#    package manager.
# 3. Installing 'curl' in the final image for the healthcheck.
# 4. Copying the entire application from the builder to ensure all required
#    shared libraries and dependencies are present.

# Stage 1: Extract the ollama binary
FROM ollama/ollama:latest as source

# Stage 2: Build the final image with curl
# The ollama binary is built for glibc, so we must use a glibc-based distro
# like Debian instead of Alpine (which uses musl).
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*

COPY --from=source / /

ENTRYPOINT ["/bin/ollama"]
CMD ["serve"]