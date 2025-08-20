#!/bin/bash
set -e

# --- Load SSH key using keychain ---
# This line securely loads your key, prompting for a passphrase only if needed.
eval $(keychain --eval --quiet id_ed25519)

# --- Configuration ---
PROJECT_DIR="/home/marku/ai_workflow_engine"
DEBOUNCE_FILE="/tmp/rebuild_debounce_timestamp"
DEBOUNCE_HOURS=1

# Ensure the script is running with the virtual environment activated
source "$PROJECT_DIR/.venv/bin/activate"
cd "$PROJECT_DIR"

# --- Step 1: Fetch changes from remote ---
echo "Fetching remote changes..."
git fetch

# --- Step 2: Check for local changes ---
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse @{u})

if [ "$LOCAL" == "$REMOTE" ]; then
    echo "Git repository is up-to-date. No action needed."
    exit 0
fi

echo "New changes detected in the remote repository. Pulling changes..."
git pull

# --- Step 3: Debounce the rebuild ---
if [ -f "$DEBOUNCE_FILE" ]; then
    LAST_REBUILD_TIME=$(cat "$DEBOUNCE_FILE")
    CURRENT_TIME=$(date +%s)
    TIME_DIFF=$((CURRENT_TIME - LAST_REBUILD_TIME))
    DEBOUNCE_SECONDS=$((DEBOUNCE_HOURS * 3600))

    if [ "$TIME_DIFF" -lt "$DEBOUNCE_SECONDS" ]; then
        echo "Rebuild was triggered recently. Debouncing for 1 hour. Skipping."
        exit 0
    fi
fi

# --- Step 4: Trigger the rebuild and record timestamp ---
echo "Changes detected and debounce period passed. Triggering a soft reset..."
"$PROJECT_DIR/run.sh" --soft-reset

# Record the timestamp of this rebuild
date +%s > "$DEBOUNCE_FILE"

echo "Stack rebuild completed successfully."
