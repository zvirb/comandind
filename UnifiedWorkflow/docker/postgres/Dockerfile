# Use the official PostgreSQL 16 image on Alpine Linux as the base.
# This provides a lightweight and secure foundation.
FROM postgres:16-alpine

# This Dockerfile establishes a custom build process for the postgres service.
# The entrypoint wrapper script, which handles certificate permissions,
# is mounted via the docker-compose.yml file.
#
# This file can be extended in the future to install additional packages
# or perform other build-time customizations if necessary.
# Example: RUN apk add --no-cache --virtual .build-deps build-base && ...