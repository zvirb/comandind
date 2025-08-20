#!/bin/sh
set -e

# This script runs as root, so it can read secrets.
# Export Redis password from Docker secret
export REDIS_EXPORTER_REDIS_PASSWORD=$(cat /run/secrets/REDIS_PASSWORD)

echo "Redis Exporter: Starting with Docker secret authentication"

# Execute the redis_exporter with password authentication
exec /redis_exporter -redis.addr=redis:6379 -redis.user=lwe-app -redis.password=$REDIS_EXPORTER_REDIS_PASSWORD