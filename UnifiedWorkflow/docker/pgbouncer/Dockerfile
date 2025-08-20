# /docker/pgbouncer/Dockerfile

# Use the same base as the postgres container to ensure compatibility with
# client tools like psql, which the entrypoint-wrapper.sh script uses.
# The alpine version is lightweight and includes 'su-exec'.
FROM postgres:16-alpine

# Add a label to identify the maintainer
LABEL maintainer="Marku <you@example.com>"

# Install pgbouncer. The base image already has the necessary client tools.
RUN apk add --no-cache pgbouncer gettext

# The entrypoint and command are specified in the docker-compose.yml file.
# The entrypoint-wrapper.sh will run as root, set up files, and then use
# 'su-exec pgbouncer' to drop privileges and run the main process.
