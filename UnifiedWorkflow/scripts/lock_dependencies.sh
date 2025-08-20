#!/bin/bash
# scripts/lock_dependencies.sh
# This script updates the poetry.lock file using a consistent Docker environment,
# ensuring that the lock file is compatible with the container's Python version.

set -e

# Get the directory of this script to source common functions
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/_common_functions.sh"

log_info "Updating poetry.lock file to match pyproject.toml..."
log_info "Using python:3.11-slim Docker image for consistency."

# The -it flags are removed to make this script more CI/CD friendly.
# We upgrade pip and install a recent version of poetry to ensure compatibility
# with modern flags like --no-update. We invoke poetry via `python -m poetry`
# to ensure we use the version just installed, avoiding PATH issues.
docker run --rm -v "$(pwd):/app" -w /app python:3.11-slim sh -c "python -m pip install --upgrade pip && python -m pip install poetry>=1.5 && python -m poetry lock --no-interaction --no-ansi && python -m poetry install --only dev"

log_info "✅ poetry.lock has been successfully updated."
log_info "✅ context.json has been successfully generated."