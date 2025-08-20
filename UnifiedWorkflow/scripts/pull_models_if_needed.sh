#!/bin/sh
set -e

MODELS_TO_PULL="llama3.2:3b nomic-embed-text"

echo "--- Checking for required Ollama models ---"

# Get the list of currently installed models (first column, skipping header)
INSTALLED_MODELS=$(ollama list | awk 'NR>1 {print $1}')

for model in $MODELS_TO_PULL; do
  # Use grep with -w for whole-word match and -q for quiet mode.
  if echo "$INSTALLED_MODELS" | grep -q -w "$model"; then
    echo "✅ Model '$model' already exists. Skipping pull."
  else
    echo "⏳ Model '$model' not found. Pulling..."
    ollama pull "$model"
  fi
done

echo "--- ✅ All required models are present. ---"