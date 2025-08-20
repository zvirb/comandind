#!/bin/bash
# scripts/_common_functions.sh

# --- Color Definitions ---
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}${BOLD}INFO:${NC} $*"; }
log_success() { echo -e "${GREEN}${BOLD}SUCCESS:${NC} $*"; }
log_warn() { echo -e "${YELLOW}${BOLD}WARN:${NC} $*"; }
log_error() { echo -e "${RED}${BOLD}ERROR:${NC} $*"; }
log_debug() { echo -e "${CYAN}${BOLD}DEBUG:${NC} $*"; }

# Check if a command exists
check_command() {
    local cmd="$1"
    if [[ "$cmd" == "docker compose" ]]; then
        if ! docker compose version &> /dev/null; then
            log_error "'docker compose' is not available. Please ensure Docker with the Compose V2 plugin is installed."
            exit 1
        fi
    elif [[ "$cmd" == "yq" ]]; then
        if ! command -v yq &> /dev/null || ! yq --version 2>/dev/null | grep -q "mikefarah"; then
            log_error "Incorrect or missing 'yq' version. This project requires the Go-based yq by Mike Farah."
            log_error "The installed 'yq' may be the incompatible Python version."
            log_error "Please see installation instructions at: https://github.com/mikefarah/yq/#install"
            exit 1
        fi
    elif ! command -v "$cmd" &> /dev/null; then
        log_error "'$cmd' is not installed. Please install it to proceed."
        exit 1
    fi
}

# A function to perform a complete system wipe.
nuke_and_pave() {
    local SCRIPT_DIR
    SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
    local CERTS_DIR="$SCRIPT_DIR/../certs"
    echo
    log_warn "You have requested a full system wipe ('nuke and pave')."
    log_warn "This will permanently delete ALL Docker images, containers, volumes, and networks on your system, plus all locally generated certificates."
    read -p "Are you absolutely sure you want to continue? (yes/no): " choice
    if [[ "$choice" != "yes" ]]; then
        log_info "Nuke and pave operation aborted."
        exit 1
    fi
    log_info "Proceeding with nuke and pave..."
    log_info "Stopping all Docker containers..."
    docker stop $(docker ps -aq) || true
    log_info "Pruning all Docker images, containers, volumes, and networks..."
    docker system prune -a --volumes -f
    if [ -d "$CERTS_DIR" ]; then
        log_info "Removing local certificates directory..."
        rm -rf "$CERTS_DIR"
    fi
    log_info "✅ Nuke and pave complete."
}

# A function to log detailed build failures.
log_build_failure() {
    local group_name="$1"
    local build_log_file="$2"
    local SCRIPT_DIR
    SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
    local LOG_FILE="$SCRIPT_DIR/../logs/error_log.txt"
    local INVOCATION_FILE="$SCRIPT_DIR/../logs/.last_invocation_command"
    {
        echo -e "\n\n--- BUILD FAILURE LOGGED AT $(date) for Service Group: $group_name ---"
        if [ -f "$INVOCATION_FILE" ]; then
            echo "Invocation Command: $(cat "$INVOCATION_FILE")"
        else
            echo "Invocation Command: Not captured"
        fi
        echo "Context: The error occurred during the 'docker compose build' phase."
        echo "The Docker image itself could not be created. The full, raw build output is included below for detailed analysis."
        echo
        echo "--- FULL BUILD OUTPUT ---"
        cat "$build_log_file"
        echo "--- END BUILD OUTPUT ---"
    } >> "$LOG_FILE"
}

# A detailed function to log container runtime failures.
log_container_failure() {
    local service="$1"
    shift
    local dependencies=("$@")
    local SCRIPT_DIR
    SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
    local LOG_FILE="$SCRIPT_DIR/../logs/error_log.txt"
    local LAST_FAILED_SERVICE_FILE="$SCRIPT_DIR/../logs/.last_failed_service"
    local INVOCATION_FILE="$SCRIPT_DIR/../logs/.last_invocation_command"
    echo "$service" > "$LAST_FAILED_SERVICE_FILE"
    {
        echo -e "\n\n--- CONTAINER FAILURE LOGGED AT $(date) for service: $service ---"
        if [ -f "$INVOCATION_FILE" ]; then
            echo "Invocation Command: $(cat "$INVOCATION_FILE")"
        else
            echo "Invocation Command: Not captured"
        fi
        if ! inspect_output=$(docker inspect "$service" 2>/dev/null); then
            echo "Status: Could not inspect container '$service'. It may have been removed."
        else
            local container_id
            container_id=$(echo "$inspect_output" | jq -r '.[0].Id')
            echo
            echo "--- STATE & HEALTH ---"
            if command -v jq &> /dev/null; then
                echo "Status: $(echo "$inspect_output" | jq -r '.[0].State.Status')"
                echo "ExitCode: $(echo "$inspect_output" | jq -r '.[0].State.ExitCode')"
                echo "OOMKilled: $(echo "$inspect_output" | jq -r '.[0].State.OOMKilled')"
                last_health_log=$(echo "$inspect_output" | jq -r '.[0].State.Health.Log[-1].Output | gsub("\n"; " ")')
                echo "Last Health Check Output: ${last_health_log:-N/A}"
            else
                echo "State: (Install 'jq' for more details)"
            fi
            echo
            echo "--- CONFIGURATION ---"
            echo "Command: $(echo "$inspect_output" | jq -r '.[0].Config.Cmd')"
            echo "Environment Variables:"
            echo "$inspect_output" | jq -r '.[0].Config.Env[]' | sed 's/^/  - /'
            echo "Volume Mounts:"
            echo "$inspect_output" | jq -r '.[0].Mounts | if . == null then "  - None" else .[] | "  - Source: \(.Source)\n    Destination: \(.Destination)\n    Mode: \(if .RW then "rw" else "ro" end)" end'
            echo
            echo "--- ENTRYPOINT SCRIPT ---"
            entrypoint_path=$(echo "$inspect_output" | jq -r '.[0].Config.Entrypoint[0] // empty')
            if [[ -n "$entrypoint_path" ]]; then
                echo "Path inside container: $entrypoint_path"
                echo "--- SCRIPT CONTENT START ---"
                docker cp "${container_id}:${entrypoint_path}" - | tar xO 2>/dev/null || echo "Could not read entrypoint script."
                echo
                echo "--- SCRIPT CONTENT END ---"
            else
                echo "No custom entrypoint defined for this container."
            fi
            echo
            echo "--- RECENT DOCKER EVENTS (last 60s) ---"
            docker events --since '60s' --until "$(date +%s)" --filter "container=$container_id" --format '{{.Time}} {{.Status}} {{.Action}}' || echo "Could not retrieve Docker events."
        fi
        echo
        echo "--- CONTAINER LOGS (last 100 lines) ---"
        # Sleep for a few seconds to allow the Docker log driver to catch up after a container exits.
        sleep 4 
        docker logs --tail 100 "$service"
        echo "--- END ERROR LOG ---"
        if [ ${#dependencies[@]} -gt 0 ]; then
            echo
            echo "--- DEPENDENCY STATE SNAPSHOT ---"
            echo "The following is the state of critical dependencies at the time of failure."
            for dep in "${dependencies[@]}"; do
                echo
                echo "--- Dependency: $dep ---"
                if ! dep_inspect_output=$(docker inspect "$dep" 2>/dev/null); then
                    echo "Status: Could not inspect dependency '$dep'."
                else
                    echo "Status: $(echo "$dep_inspect_output" | jq -r '.[0].State.Status')"
                    echo "Health: $(echo "$dep_inspect_output" | jq -r '.[0].State.Health.Status // "N/A"')"
                    echo "Recent Logs:"
                    docker logs --tail 10 "$dep" | sed 's/^/  /'
                fi
            done
            echo "--- END DEPENDENCY SNAPSHOT ---"
        fi
    } >> "$LOG_FILE"
}

# Select GPU profile
select_profile() {
    # This function is hardcoded to always select the GPU profile, as per your request.
    # The interactive selection and the CPU option have been removed.
    log_info "Deployment profile automatically set to 'gpu-nvidia'." >&2
    echo "gpu-nvidia"
    return
}

# Trigger the Gemini assistant script after an error
_trigger_gemini_assistant() {
    log_info "An error was logged. Running diagnostic search for error source..."
    local common_script_dir
    common_script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
    local find_error_script_path="$common_script_dir/_find_error_source.sh"
    local ask_script_path="$common_script_dir/_ask_gemini.sh"
    if [[ -f "$find_error_script_path" ]]; then
        "$find_error_script_path"
    else
        log_warn "Could not find _find_error_source.sh. Skipping."
    fi
    log_info "Triggering Gemini assistant in 3 seconds..."
    sleep 1
    log_info "Triggering Gemini assistant in 2 seconds..."
    sleep 1
    log_info "Triggering Gemini assistant in 1 second..."
    sleep 1
    if [[ -f "$ask_script_path" ]]; then
        log_info "Running _ask_gemini.sh..."
        "$ask_script_path"
    else
        log_error "Could not find _ask_gemini.sh"
    fi
}