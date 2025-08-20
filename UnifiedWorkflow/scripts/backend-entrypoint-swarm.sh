#!/bin/sh
set -e

# This script waits for the Ollama model to be available before starting the main application.
# It's used in Docker Swarm where `depends_on` doesn't wait for one-off tasks to complete.

# Environment variables are passed from docker-stack.yml
OLLAMA_HOST_URL="${OLLAMA_HOST}"
MODEL_TO_CHECK="${OLLAMA_MODEL}"
WAIT_TIMEOUT=900 # 15 minutes, model downloads can be long

echo "--- Backend Entrypoint: Waiting for Ollama model '$MODEL_TO_CHECK' ---"

if [ -z "$OLLAMA_HOST_URL" ] || [ -z "$MODEL_TO_CHECK" ]; then
  echo "Error: OLLAMA_HOST and OLLAMA_MODEL environment variables must be set."
  exit 1
fi

start_time=$(date +%s)
until curl -s --fail "$OLLAMA_HOST_URL/api/tags" | jq -e ".models[] | select(.name == \"$MODEL_TO_CHECK\")" > /dev/null; do
  current_time=$(date +%s)
  elapsed_time=$((current_time - start_time))

  if [ $elapsed_time -ge $WAIT_TIMEOUT ]; then
    echo "Error: Timed out after $WAIT_TIMEOUT seconds waiting for model '$MODEL_TO_CHECK' at $OLLAMA_HOST_URL." >&2
    echo "--- Last response from Ollama tags API: ---" >&2
    curl -s "$OLLAMA_HOST_URL/api/tags" || echo "Failed to contact Ollama." >&2
    echo "-------------------------------------------" >&2
    exit 1
  fi

  echo "Model '$MODEL_TO_CHECK' not yet available. Retrying in 15 seconds..."
  sleep 15
done

echo "✅ Model '$MODEL_TO_CHECK' is available. Starting application..."

# Execute the original command passed to the container
exec "$@"