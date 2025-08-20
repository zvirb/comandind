#!/bin/bash
set -e

# Sequential Thinking Service Entrypoint Wrapper
# Handles mTLS certificate setup and service initialization

SERVICE_NAME="sequentialthinking-service"

echo "🧠 Starting Sequential Thinking Service initialization..."

# Function to setup mTLS certificates
setup_mtls_certificates() {
    if [ "$MTLS_ENABLED" = "true" ] && [ -n "$MTLS_CA_CERT_FILE" ]; then
        echo "🔐 Setting up mTLS certificates for $SERVICE_NAME..."
        
        # Create certificate directory
        mkdir -p "/etc/certs/$SERVICE_NAME"
        
        # Copy certificates if they exist
        if [ -f "$MTLS_CA_CERT_FILE" ]; then
            cp "$MTLS_CA_CERT_FILE" "/etc/certs/$SERVICE_NAME/rootCA.pem"
            echo "✓ Root CA certificate copied"
        fi
        
        if [ -f "$MTLS_CERT_FILE" ]; then
            cp "$MTLS_CERT_FILE" "/etc/certs/$SERVICE_NAME/unified-cert.pem" 
            echo "✓ Service certificate copied"
        fi
        
        if [ -f "$MTLS_KEY_FILE" ]; then
            cp "$MTLS_KEY_FILE" "/etc/certs/$SERVICE_NAME/unified-key.pem"
            chmod 600 "/etc/certs/$SERVICE_NAME/unified-key.pem"
            echo "✓ Service private key copied"
        fi
        
        echo "🔐 mTLS certificates setup completed"
    else
        echo "ℹ️  mTLS not enabled or certificates not configured"
    fi
}

# Function to validate environment
validate_environment() {
    echo "🔍 Validating environment configuration..."
    
    # Check Redis configuration
    if [ -z "$REDIS_URL" ]; then
        echo "⚠️  Warning: REDIS_URL not set, using default redis://redis:6379"
        export REDIS_URL="redis://redis:6379"
    fi
    
    # Check Ollama configuration
    if [ -z "$OLLAMA_URL" ]; then
        echo "⚠️  Warning: OLLAMA_URL not set, using default https://ollama:11435"
        export OLLAMA_URL="https://ollama:11435"
    fi
    
    # Check Memory Service configuration
    if [ -z "$MEMORY_SERVICE_URL" ]; then
        echo "⚠️  Warning: MEMORY_SERVICE_URL not set, using default http://memory-service:8001"
        export MEMORY_SERVICE_URL="http://memory-service:8001"
    fi
    
    echo "✅ Environment validation completed"
}

# Function to wait for dependencies
wait_for_dependencies() {
    echo "⏳ Waiting for service dependencies..."
    
    # Function to check if service is available
    check_service() {
        local service_url=$1
        local service_name=$2
        local max_attempts=30
        local attempt=1
        
        while [ $attempt -le $max_attempts ]; do
            if curl -s --connect-timeout 5 "$service_url" > /dev/null 2>&1; then
                echo "✅ $service_name is available"
                return 0
            fi
            
            echo "⏳ Waiting for $service_name (attempt $attempt/$max_attempts)..."
            sleep 5
            attempt=$((attempt + 1))
        done
        
        echo "❌ $service_name is not available after $max_attempts attempts"
        return 1
    }
    
    # Wait for Redis (basic TCP check)
    echo "⏳ Checking Redis connectivity..."
    if ! timeout 30 bash -c 'until echo > /dev/tcp/redis/6379; do sleep 2; done' 2>/dev/null; then
        echo "❌ Redis connection failed"
        exit 1
    fi
    echo "✅ Redis is reachable"
    
    # Wait for Ollama service
    if ! check_service "$OLLAMA_URL/api/tags" "Ollama"; then
        echo "⚠️  Ollama service not immediately available - will retry during operation"
    fi
    
    # Wait for Memory Service (optional)
    if ! check_service "$MEMORY_SERVICE_URL/health" "Memory Service"; then
        echo "⚠️  Memory service not immediately available - will work without memory integration"
    fi
    
    echo "✅ Dependency checks completed"
}

# Function to perform health checks
perform_health_checks() {
    echo "🏥 Performing service health checks..."
    
    # Check Python environment
    python --version
    pip list | grep -E "(langgraph|redis|fastapi)" || echo "⚠️  Some packages might be missing"
    
    # Check Redis connection with authentication
    if [ -n "$REDIS_PASSWORD" ]; then
        echo "🔍 Testing Redis connection with authentication..."
        python -c "
import redis, os
try:
    r = redis.from_url(os.environ.get('REDIS_URL', 'redis://redis:6379'), password=os.environ.get('REDIS_PASSWORD'))
    r.ping()
    print('✅ Redis authentication successful')
except Exception as e:
    print(f'⚠️  Redis auth issue: {e}')
" || echo "⚠️  Redis connection test failed"
    fi
    
    echo "✅ Health checks completed"
}

# Function to start the service
start_service() {
    echo "🚀 Starting Sequential Thinking Service..."
    echo "📊 Service Configuration:"
    echo "   • Port: ${PORT:-8002}"
    echo "   • Debug Mode: ${DEBUG:-false}"
    echo "   • Redis URL: $REDIS_URL"
    echo "   • Ollama URL: $OLLAMA_URL"
    echo "   • Memory Service URL: $MEMORY_SERVICE_URL"
    echo "   • Max Thinking Steps: ${MAX_THINKING_STEPS:-20}"
    echo "   • Checkpoint Enabled: ${ENABLE_SELF_HEALING:-true}"
    echo "   • mTLS Enabled: ${MTLS_ENABLED:-false}"
    
    # Set default Python path if not set
    if [ -z "$PYTHONPATH" ]; then
        export PYTHONPATH="/app:/app/sequentialthinking_service"
    fi
    
    echo "🧠 Executing: $@"
}

# Main execution flow
main() {
    echo "🎯 Sequential Thinking Service Initialization Starting..."
    echo "🆔 Service: $SERVICE_NAME"
    echo "🕒 Timestamp: $(date -Iseconds)"
    
    # Setup certificates
    setup_mtls_certificates
    
    # Validate environment
    validate_environment
    
    # Wait for dependencies
    wait_for_dependencies
    
    # Perform health checks
    perform_health_checks
    
    # Start the service
    start_service
    
    echo "🎉 Initialization completed successfully!"
    echo "🚀 Starting Sequential Thinking Service..."
    
    # Execute the main command
    exec "$@"
}

# Trap signals for graceful shutdown
trap 'echo "🛑 Received shutdown signal, stopping Sequential Thinking Service..."; exit 0' SIGTERM SIGINT

# Run main function
main "$@"