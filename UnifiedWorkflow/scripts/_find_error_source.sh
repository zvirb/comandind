#!/bin/bash
# _find_error_source.sh
# Analyzes the error log for multiple known error patterns to find related project files.

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
source "$SCRIPT_DIR/_common_functions.sh"
LOG_FILE="$SCRIPT_DIR/../logs/error_log.txt"
PROJECT_ROOT="$SCRIPT_DIR/.."

if [ ! -s "$LOG_FILE" ]; then
    log_info "No errors found in $LOG_FILE. Nothing to do."
    exit 0
fi

log_info "Analyzing $LOG_FILE to find potential source files..."

# --- Step 1: Check for DIFFERENT error patterns in order ---
ERROR_TYPE=""
FILE_PATH=""

# Pattern 1: "No such file or directory"
if [[ -z "$FILE_PATH" ]]; then
    FILE_PATH=$(awk -F '"' '/could not load/ && /No such file or directory/ {print $2}' "$LOG_FILE")
    if [[ ! -z "$FILE_PATH" ]]; then ERROR_TYPE="Missing file"; fi
fi

# Pattern 2: "Read-only file system" (your new error)
if [[ -z "$FILE_PATH" ]]; then
    # This sed command extracts the file path from the 'chown' error message
    FILE_PATH=$(sed -n 's/.*chown: \([^:]*\): Read-only file system.*/\1/p' "$LOG_FILE")
    if [[ ! -z "$FILE_PATH" ]]; then ERROR_TYPE="Read-only file system"; fi
fi

# Add more 'if' blocks here for other patterns in the future...

# --- Step 2: Report findings and search ---
if [[ -z "$FILE_PATH" ]]; then
    log_error "Could not automatically detect a known error pattern. Please check manually."
    exit 1
fi

log_info "Detected Error Type: '$ERROR_TYPE' involving file: $FILE_PATH"
FILENAME=$(basename "$FILE_PATH")

echo
log_info "Searching project for references to '$FILENAME'..."
grep -r --color=always "$FILENAME" "$PROJECT_ROOT" | grep -v "_find_error_source.sh"
echo "-----------------------------------------------------------------------"

echo
log_info "Checking Docker and configuration files for related settings..."
grep -i --color=always -E "volume|COPY|ADD|SSL|read_only" "$PROJECT_ROOT/docker-compose.yml" 2>/dev/null
echo "-----------------------------------------------------------------------"

log_info "Search complete."