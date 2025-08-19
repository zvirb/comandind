#!/bin/sh

# Comprehensive health check script for production deployment
# Used by Docker HEALTHCHECK and external monitoring systems

set -e

# Configuration
HEALTH_URL="http://localhost:8080/health"
DETAILED_HEALTH_URL="http://localhost:8080/health/detailed"
TIMEOUT=10
MAX_RETRIES=3

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo "${RED}$(date '+%Y-%m-%d %H:%M:%S') - ERROR: $1${NC}" >&2
}

log_success() {
    echo "${GREEN}$(date '+%Y-%m-%d %H:%M:%S') - SUCCESS: $1${NC}"
}

log_warning() {
    echo "${YELLOW}$(date '+%Y-%m-%d %H:%M:%S') - WARNING: $1${NC}"
}

# Basic nginx health check
check_nginx() {
    log "Checking Nginx health..."
    
    for i in $(seq 1 $MAX_RETRIES); do
        if curl -f -s -m $TIMEOUT $HEALTH_URL > /dev/null; then
            log_success "Nginx is responding"
            return 0
        fi
        
        if [ $i -lt $MAX_RETRIES ]; then
            log_warning "Nginx check failed, retrying in 2 seconds... (attempt $i/$MAX_RETRIES)"
            sleep 2
        fi
    done
    
    log_error "Nginx health check failed after $MAX_RETRIES attempts"
    return 1
}

# Application health check
check_application() {
    log "Checking application health..."
    
    # Check if the detailed health endpoint returns valid JSON
    RESPONSE=$(curl -f -s -m $TIMEOUT $DETAILED_HEALTH_URL 2>/dev/null || echo "")
    
    if [ -z "$RESPONSE" ]; then
        log_error "Application is not responding"
        return 1
    fi
    
    # Check if it's a valid HTML response (SPA should serve index.html)
    if echo "$RESPONSE" | grep -q "<!DOCTYPE html" || echo "$RESPONSE" | grep -q "<html"; then
        log_success "Application is serving content"
        return 0
    fi
    
    log_error "Application returned unexpected response"
    return 1
}

# Check disk space
check_disk_space() {
    log "Checking disk space..."
    
    DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ "$DISK_USAGE" -gt 90 ]; then
        log_error "Disk usage is at ${DISK_USAGE}% (critical)"
        return 1
    elif [ "$DISK_USAGE" -gt 80 ]; then
        log_warning "Disk usage is at ${DISK_USAGE}% (warning)"
    else
        log_success "Disk usage is at ${DISK_USAGE}% (healthy)"
    fi
    
    return 0
}

# Check memory usage
check_memory() {
    log "Checking memory usage..."
    
    if command -v free > /dev/null; then
        MEMORY_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/($3+$7)}')
        
        if [ "$MEMORY_USAGE" -gt 90 ]; then
            log_error "Memory usage is at ${MEMORY_USAGE}% (critical)"
            return 1
        elif [ "$MEMORY_USAGE" -gt 80 ]; then
            log_warning "Memory usage is at ${MEMORY_USAGE}% (warning)"
        else
            log_success "Memory usage is at ${MEMORY_USAGE}% (healthy)"
        fi
    else
        log_warning "Memory check not available"
    fi
    
    return 0
}

# Main health check function
main() {
    log "Starting comprehensive health check..."
    
    FAILED_CHECKS=0
    
    # Critical checks - failure means unhealthy
    if ! check_nginx; then
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
    
    if ! check_application; then
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
    
    # Warning checks - don't fail health check but log warnings
    check_disk_space || true
    check_memory || true
    
    # Overall health determination
    if [ $FAILED_CHECKS -eq 0 ]; then
        log_success "All health checks passed"
        echo "healthy"
        exit 0
    else
        log_error "$FAILED_CHECKS critical health checks failed"
        echo "unhealthy"
        exit 1
    fi
}

# Handle different check types
case "${1:-full}" in
    "nginx")
        check_nginx
        ;;
    "app")
        check_application
        ;;
    "quick")
        check_nginx
        ;;
    "full"|*)
        main
        ;;
esac