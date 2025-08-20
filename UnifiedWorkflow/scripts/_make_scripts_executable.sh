#!/bin/bash
# scripts/_make_scripts_executable.sh
# Makes all .sh scripts in the project executable.
source "$(dirname "$0")/_common_functions.sh"
log_info "Making all .sh scripts executable..."
find . -type f -name "*.sh" -exec sudo chmod +x {} +
log_info "All .sh scripts are now executable."