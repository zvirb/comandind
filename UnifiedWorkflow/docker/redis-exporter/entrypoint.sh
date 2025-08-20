#!/bin/sh
set -e

# Export the Redis password from the secret file as an environment variable
export REDIS_EXPORTER_REDIS_PASSWORD="$(cat /run/secrets/REDIS_PASSWORD)"

# Execute the redis_exporter with all passed arguments
exec /redis_exporter "$@"