# docker/qdrant/Dockerfile
# This Dockerfile creates a custom Qdrant image that includes 'curl'
# to allow the Docker healthcheck to function correctly.
#
# The official qdrant image is based on Debian but lacks shell utilities
# like 'curl', which are needed for the healthcheck. This Dockerfile
# starts from the official image and simply adds 'curl'.

FROM qdrant/qdrant:v1.9.2

# Switch to the root user to install packages
USER root

# Install curl using the Debian package manager
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*