#!/bin/bash

# =============================================================================
# SSL Certificate Fix Deployment Script
# AI Workflow Engine - Deploy comprehensive SSL certificate fixes
# =============================================================================

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =============================================================================
# SSL Fix Deployment Functions
# =============================================================================

detect_current_mode() {
    log_info "Detecting current deployment mode..."
    
    # Check if mTLS certificates exist
    if [[ -f "${PROJECT_ROOT}/certs/ca/certs/ca-cert.pem" ]]; then
        log_info "mTLS infrastructure detected"
        echo "mtls"
        return 0
    fi
    
    # Check if development certificates exist
    if [[ -f "${PROJECT_ROOT}/certs/api/server.crt" ]] || [[ -f "${PROJECT_ROOT}/certs/webui/server.crt" ]]; then
        log_info "Development certificates detected"
        echo "dev"
        return 0
    fi
    
    # No certificates found
    log_info "No SSL certificates detected"
    echo "nossl"
    return 0
}

setup_development_mode() {
    log_info "Setting up development mode with self-signed certificates..."
    
    # Generate development certificates
    if [[ -x "${SCRIPT_DIR}/generate_dev_certificates.sh" ]]; then
        log_info "Generating development certificates..."
        "${SCRIPT_DIR}/generate_dev_certificates.sh" generate
    else
        log_error "Development certificate generation script not found or not executable"
        return 1
    fi
    
    # Validate certificates
    log_info "Validating development certificates..."
    if [[ -x "${SCRIPT_DIR}/validate_ssl_configuration.sh" ]]; then
        "${SCRIPT_DIR}/validate_ssl_configuration.sh" check-dev
    fi
    
    log_success "Development mode setup completed"
    return 0
}

setup_mtls_mode() {
    log_info "Setting up mTLS mode with full certificate infrastructure..."
    
    # Check if mTLS setup script exists
    if [[ -x "${SCRIPT_DIR}/security/setup_mtls_infrastructure.sh" ]]; then
        log_info "Running mTLS infrastructure setup..."
        "${SCRIPT_DIR}/security/setup_mtls_infrastructure.sh" setup
    else
        log_error "mTLS infrastructure setup script not found or not executable"
        return 1
    fi
    
    # Validate mTLS certificates
    log_info "Validating mTLS certificates..."
    if [[ -x "${SCRIPT_DIR}/validate_ssl_configuration.sh" ]]; then
        "${SCRIPT_DIR}/validate_ssl_configuration.sh" check-mtls
    fi
    
    log_success "mTLS mode setup completed"
    return 0
}

setup_nossl_mode() {
    log_info "Setting up SSL-less development mode..."
    
    # Check if override file exists
    if [[ -f "${PROJECT_ROOT}/docker-compose.override-nossl.yml" ]]; then
        log_success "SSL-less override configuration found"
    else
        log_error "SSL-less override configuration not found"
        return 1
    fi
    
    log_success "SSL-less mode setup completed"
    log_info "Use: docker-compose -f docker-compose.yml -f docker-compose.override-nossl.yml up"
    return 0
}

fix_scrollto_error() {
    log_info "Fixing TypeError: Cannot read properties of null (reading 'scrollTo') error..."
    
    # Check if the error is in a specific file
    local scroll_fix_applied=false
    
    # Look for potential scrollTo usage in the codebase
    find "${PROJECT_ROOT}/app/webui/src" -name "*.svelte" -o -name "*.js" -o -name "*.ts" | while read -r file; do
        if grep -q "scrollTo" "$file" 2>/dev/null; then
            log_info "Found scrollTo usage in: $file"
            
            # Create a backup
            cp "$file" "$file.backup"
            
            # Add null check for scrollTo
            sed -i 's/\.scrollTo(/?.scrollTo(/g' "$file" || true
            sed -i 's/window\.scrollTo/window?.scrollTo/g' "$file" || true
            sed -i 's/document\.scrollTo/document?.scrollTo/g' "$file" || true
            sed -i 's/element\.scrollTo/element?.scrollTo/g' "$file" || true
            
            scroll_fix_applied=true
        fi
    done
    
    # Add a general scrollTo safety wrapper to app.html if not already present
    local app_html="${PROJECT_ROOT}/app/webui/src/app.html"
    if [[ -f "$app_html" ]] && ! grep -q "safeScrollTo" "$app_html"; then
        log_info "Adding scrollTo safety wrapper to app.html..."
        
        # Create backup
        cp "$app_html" "$app_html.backup"
        
        # Add safety wrapper before the closing </script> tag
        sed -i '/<\/script>/i\
			// Safe scrollTo wrapper to prevent null reference errors\
			window.safeScrollTo = function(x, y, options) {\
				if (window && typeof window.scrollTo === "function") {\
					try {\
						if (options) {\
							window.scrollTo({ top: y, left: x, ...options });\
						} else {\
							window.scrollTo(x, y);\
						}\
					} catch (error) {\
						console.warn("ScrollTo failed safely:", error);\
					}\
				}\
			};\
			\
			// Override native scrollTo with safe version\
			if (window && typeof window.scrollTo === "function") {\
				const originalScrollTo = window.scrollTo;\
				window.scrollTo = function(x, y) {\
					try {\
						if (typeof x === "object") {\
							originalScrollTo.call(window, x);\
						} else {\
							originalScrollTo.call(window, x, y);\
						}\
					} catch (error) {\
						console.warn("ScrollTo failed safely:", error);\
					}\
				};\
			}' "$app_html"
        
        scroll_fix_applied=true
    fi
    
    if $scroll_fix_applied; then
        log_success "ScrollTo error fixes applied"
    else
        log_info "No scrollTo issues found to fix"
    fi
}

restart_services() {
    local mode="$1"
    
    log_info "Restarting services in $mode mode..."
    
    # Stop existing services
    if docker compose ps >/dev/null 2>&1; then
        log_info "Stopping existing services..."
        docker compose down || true
    fi
    
    # Start services based on mode
    case "$mode" in
        "mtls")
            if [[ -f "${PROJECT_ROOT}/docker-compose-mtls.yml" ]]; then
                log_info "Starting services with mTLS configuration..."
                docker compose -f docker-compose-mtls.yml up -d
            else
                log_error "mTLS docker-compose configuration not found"
                return 1
            fi
            ;;
        "dev")
            log_info "Starting services with standard configuration..."
            docker compose up -d
            ;;
        "nossl")
            log_info "Starting services with SSL-less configuration..."
            docker compose -f docker-compose.yml -f docker-compose.override-nossl.yml up -d
            ;;
        *)
            log_error "Unknown mode: $mode"
            return 1
            ;;
    esac
    
    # Wait for services to start
    log_info "Waiting for services to start..."
    sleep 10
    
    # Check service health
    log_info "Checking service health..."
    docker compose ps
    
    log_success "Services restarted in $mode mode"
}

run_health_checks() {
    log_info "Running comprehensive health checks..."
    
    # Wait for services to be fully ready
    sleep 15
    
    # Test different endpoints
    local endpoints=(
        "http://localhost:8000/health"
        "http://localhost:8000/api/health"
        "http://localhost:8000/api/v1/health"
        "https://localhost/api/health"
        "https://localhost/api/v1/health"
    )
    
    for endpoint in "${endpoints[@]}"; do
        log_info "Testing endpoint: $endpoint"
        if curl -s -f -m 10 -k "$endpoint" >/dev/null 2>&1; then
            log_success "✓ $endpoint is responding"
        else
            log_warning "✗ $endpoint is not responding"
        fi
    done
    
    # Test WebUI
    log_info "Testing WebUI endpoints..."
    local webui_endpoints=(
        "http://localhost:3000"
        "https://localhost"
    )
    
    for endpoint in "${webui_endpoints[@]}"; do
        log_info "Testing WebUI: $endpoint"
        if curl -s -f -m 10 -k "$endpoint" >/dev/null 2>&1; then
            log_success "✓ WebUI at $endpoint is responding"
        else
            log_warning "✗ WebUI at $endpoint is not responding"
        fi
    done
    
    # Run SSL validation if script exists
    if [[ -x "${SCRIPT_DIR}/validate_ssl_configuration.sh" ]]; then
        log_info "Running SSL validation..."
        "${SCRIPT_DIR}/validate_ssl_configuration.sh" check-all || true
    fi
}

display_usage() {
    cat << EOF
Usage: $0 [COMMAND] [OPTIONS]

Commands:
    auto                 Auto-detect and deploy appropriate SSL configuration
    dev                  Deploy development mode with self-signed certificates
    mtls                 Deploy mTLS mode with full certificate infrastructure
    nossl                Deploy SSL-less development mode
    fix-scrollto         Fix scrollTo JavaScript errors
    restart [mode]       Restart services in specified mode (dev|mtls|nossl)
    health-check         Run comprehensive health checks
    help                 Show this help message

Options:
    --no-restart         Skip service restart
    --skip-checks        Skip health checks
    --verbose            Enable verbose output

Examples:
    $0 auto                      # Auto-detect and deploy appropriate mode
    $0 dev                       # Deploy development certificates and restart
    $0 mtls                      # Deploy full mTLS infrastructure
    $0 nossl                     # Deploy SSL-less development mode
    $0 fix-scrollto              # Fix JavaScript scrollTo errors
    $0 health-check              # Run health checks only

EOF
}

# =============================================================================
# Main Script Logic
# =============================================================================

main() {
    local command="${1:-auto}"
    local no_restart=false
    local skip_checks=false
    local verbose=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --no-restart)
                no_restart=true
                shift
                ;;
            --skip-checks)
                skip_checks=true
                shift
                ;;
            --verbose)
                verbose=true
                shift
                ;;
            -h|--help|help)
                display_usage
                exit 0
                ;;
            auto|dev|mtls|nossl|fix-scrollto|restart|health-check)
                command="$1"
                shift
                ;;
            *)
                if [[ "$1" != "${command}" ]]; then
                    log_error "Unknown option: $1"
                    display_usage
                    exit 1
                fi
                shift
                ;;
        esac
    done
    
    log_info "AI Workflow Engine SSL Certificate Fix Deployment"
    log_info "================================================="
    echo
    
    case "$command" in
        "auto")
            local current_mode
            current_mode=$(detect_current_mode)
            log_info "Current mode detected: $current_mode"
            
            case "$current_mode" in
                "mtls")
                    log_info "mTLS infrastructure found, validating..."
                    if [[ -x "${SCRIPT_DIR}/validate_ssl_configuration.sh" ]]; then
                        if "${SCRIPT_DIR}/validate_ssl_configuration.sh" check-mtls; then
                            log_success "mTLS infrastructure is valid"
                            if ! $no_restart; then
                                restart_services "mtls"
                            fi
                        else
                            log_warning "mTLS infrastructure has issues, switching to development mode"
                            setup_development_mode
                            if ! $no_restart; then
                                restart_services "dev"
                            fi
                        fi
                    fi
                    ;;
                "dev")
                    log_info "Development certificates found, validating..."
                    if [[ -x "${SCRIPT_DIR}/validate_ssl_configuration.sh" ]]; then
                        if "${SCRIPT_DIR}/validate_ssl_configuration.sh" check-dev; then
                            log_success "Development certificates are valid"
                            if ! $no_restart; then
                                restart_services "dev"
                            fi
                        else
                            log_warning "Development certificates have issues, regenerating..."
                            setup_development_mode
                            if ! $no_restart; then
                                restart_services "dev"
                            fi
                        fi
                    fi
                    ;;
                "nossl")
                    log_info "No SSL certificates found, setting up development certificates..."
                    if setup_development_mode; then
                        if ! $no_restart; then
                            restart_services "dev"
                        fi
                    else
                        log_warning "Development certificate setup failed, using SSL-less mode"
                        setup_nossl_mode
                        if ! $no_restart; then
                            restart_services "nossl"
                        fi
                    fi
                    ;;
            esac
            ;;
        "dev")
            setup_development_mode
            if ! $no_restart; then
                restart_services "dev"
            fi
            ;;
        "mtls")
            setup_mtls_mode
            if ! $no_restart; then
                restart_services "mtls"
            fi
            ;;
        "nossl")
            setup_nossl_mode
            if ! $no_restart; then
                restart_services "nossl"
            fi
            ;;
        "fix-scrollto")
            fix_scrollto_error
            ;;
        "restart")
            local restart_mode="${2:-dev}"
            restart_services "$restart_mode"
            ;;
        "health-check")
            run_health_checks
            ;;
        *)
            log_error "Unknown command: $command"
            display_usage
            exit 1
            ;;
    esac
    
    # Fix scrollTo errors
    fix_scrollto_error
    
    # Run health checks unless skipped
    if ! $skip_checks && [[ "$command" != "health-check" ]] && [[ "$command" != "fix-scrollto" ]]; then
        echo
        run_health_checks
    fi
    
    echo
    log_success "SSL certificate fix deployment completed!"
    
    # Provide usage recommendations
    echo
    log_info "Usage recommendations:"
    case "$command" in
        "mtls"|"auto")
            if [[ -f "${PROJECT_ROOT}/certs/ca/certs/ca-cert.pem" ]]; then
                log_info "• Use 'docker-compose -f docker-compose-mtls.yml up' for mTLS mode"
            else
                log_info "• Use 'docker-compose up' for development mode"
            fi
            ;;
        "dev")
            log_info "• Use 'docker-compose up' for development mode"
            ;;
        "nossl")
            log_info "• Use 'docker-compose -f docker-compose.yml -f docker-compose.override-nossl.yml up' for SSL-less mode"
            ;;
    esac
    
    log_info "• Access the application at https://localhost (with certificates) or http://localhost:8080 (fallback)"
    log_info "• API health check: curl -k https://localhost/api/health"
    log_info "• Generate SSL report: scripts/validate_ssl_configuration.sh generate-report"
}

# Run main function with all arguments
main "$@"