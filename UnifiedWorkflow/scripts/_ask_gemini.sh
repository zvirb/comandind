#!/bin/bash
# scripts/_ask_gemini.sh
# Gathers error logs, prepares a prompt for Gemini, and copies it to the clipboard.

# --- FIX 1: Make paths relative to the script's location ---
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
source "$SCRIPT_DIR/_common_functions.sh"
LOG_FILE="$SCRIPT_DIR/../logs/error_log.txt"

# Check if log file is missing or empty
if [ ! -f "$LOG_FILE" ] || [ ! -s "$LOG_FILE" ]; then
    log_info "No errors found in $LOG_FILE. Nothing to do."
    exit 0
fi

log_info "Found errors in $LOG_FILE. Preparing a prompt for Gemini..."

# Prepare the prompt by assigning the multi-line string directly
PROMPT="I'm having trouble with my Docker-based AI Workflow Engine project.
The setup script failed. Here are the contents of the error log file that was generated.

Can you please analyze the error and suggest a fix?

--- ERROR LOG ---
$(cat "$LOG_FILE")
--- END ERROR LOG ---

For additional context, I can provide files like docker-compose.yml, setup scripts, etc. if you ask for them.
Please keep in mind @orchestration_detail.txt if dealing with docker containers setup and execution (not internal code)"

echo "-----------------------------------------------------------------------"
echo "--- Prompt for Gemini Code Assist ---"
echo "-----------------------------------------------------------------------"
# Using printf is slightly safer for printing arbitrary variables than echo
printf "%s\n" "$PROMPT"
echo "-----------------------------------------------------------------------"
echo

# --- IMPROVEMENT 2: Automatically copy the prompt to clipboard ---
if command -v xclip &> /dev/null; then
    printf "%s" "$PROMPT" | xclip -selection clipboard
    log_info "✅ Prompt has been automatically copied to your clipboard!"
else
    log_info "💡 Install 'xclip' (sudo apt-get install xclip) to auto-copy the prompt."
fi

echo

# --- Final User Options ---
LAST_FAILED_SERVICE_FILE="$SCRIPT_DIR/../logs/.last_failed_service"

# Check if there's a failed service to get logs from
echo
if [ -f "$LAST_FAILED_SERVICE_FILE" ]; then
    FAILED_SERVICE=$(cat "$LAST_FAILED_SERVICE_FILE")
    read -p "Choose an option (1: Delete Log, 2: Append Full Logs for '$FAILED_SERVICE', Enter: Do Nothing): " choice
else
    read -p "Choose an option (1: Delete Log, Enter: Do Nothing): " choice
fi

case "$choice" in
  1)
    log_info "Clearing $LOG_FILE..."
    > "$LOG_FILE"
    rm -f "$LAST_FAILED_SERVICE_FILE"
    log_info "Log file cleared."
    ;;
  2)
    # This case is only reachable if LAST_FAILED_SERVICE_FILE exists.
    log_info "Capturing all logs for '$FAILED_SERVICE' and appending to $LOG_FILE..."
    {
        echo -e "\n\n--- FULL LOGS CAPTURED AT $(date) for service: $FAILED_SERVICE ---"
        docker compose logs --no-color "$FAILED_SERVICE"
        echo "--- END FULL LOGS ---"
    } >> "$LOG_FILE"
    rm -f "$LAST_FAILED_SERVICE_FILE" # Clean up after use
    log_info "✅ Full logs appended. The new content is NOT on your clipboard, but is in the log file."
    ;;
  *)
    log_info "Log file was not cleared."
    rm -f "$LAST_FAILED_SERVICE_FILE"
    ;;
esac