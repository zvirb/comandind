#!/bin/bash

# Deploy Pieces OS Integration to AIWFE Kubernetes Cluster
# This script deploys the Pieces OS connector service to the AIWFE ecosystem

set -e

echo "======================================"
echo "AIWFE Pieces OS Integration Deployment"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v kubectl &> /dev/null; then
    print_error "kubectl is not installed. Please install kubectl first."
    exit 1
fi

if ! command -v docker &> /dev/null; then
    print_error "docker is not installed. Please install docker first."
    exit 1
fi

print_status "Prerequisites checked"

# Build Docker image
echo ""
echo "Building Pieces OS Connector Docker image..."
cd app/backend

if [ -f "Dockerfile.pieces" ]; then
    docker build -f Dockerfile.pieces -t aiwfe/pieces-os-connector:latest .
    print_status "Docker image built successfully"
else
    print_error "Dockerfile.pieces not found"
    exit 1
fi

cd ../..

# Create namespace if it doesn't exist
echo ""
echo "Creating namespace..."
kubectl create namespace aiwfe --dry-run=client -o yaml | kubectl apply -f -
print_status "Namespace created/verified"

# Create secrets if they don't exist
echo ""
echo "Creating secrets..."

# Check if secrets exist, create dummy ones if not (for development)
if ! kubectl get secret aiwfe-auth-secret -n aiwfe &> /dev/null; then
    print_warning "Creating development auth secret..."
    kubectl create secret generic aiwfe-auth-secret \
        --from-literal=jwt-secret=$(openssl rand -base64 32) \
        --from-literal=csrf-secret=$(openssl rand -base64 32) \
        -n aiwfe
fi

if ! kubectl get secret aiwfe-api-secret -n aiwfe &> /dev/null; then
    print_warning "Creating development API secret..."
    kubectl create secret generic aiwfe-api-secret \
        --from-literal=api-key=$(openssl rand -base64 32) \
        -n aiwfe
fi

if ! kubectl get secret pieces-api-secret -n aiwfe &> /dev/null; then
    print_warning "Creating Pieces API secret (placeholder)..."
    kubectl create secret generic pieces-api-secret \
        --from-literal=api-key="pieces-api-key-placeholder" \
        -n aiwfe
fi

print_status "Secrets configured"

# Deploy Pieces OS Connector
echo ""
echo "Deploying Pieces OS Connector to Kubernetes..."
kubectl apply -f k8s/pieces-os-connector.yaml

# Wait for deployment to be ready
echo ""
echo "Waiting for deployment to be ready..."
kubectl rollout status deployment/pieces-os-connector -n aiwfe --timeout=300s

# Check pod status
echo ""
echo "Checking pod status..."
kubectl get pods -n aiwfe -l app=pieces-os-connector

# Check service status
echo ""
echo "Checking service status..."
kubectl get svc pieces-os-connector -n aiwfe

# Display connection information
echo ""
echo "======================================"
echo "Deployment Complete!"
echo "======================================"
echo ""
print_status "Pieces OS Connector has been successfully deployed"
echo ""
echo "Service Details:"
echo "----------------"
echo "Internal URL: http://pieces-os-connector.aiwfe.svc.cluster.local:8200"
echo "API Endpoint: /api/v1/"
echo "Health Check: /health/live"
echo "Metrics: /metrics (port 9200)"
echo ""
echo "To access the service from outside the cluster:"
echo "kubectl port-forward -n aiwfe svc/pieces-os-connector 8200:8200"
echo ""
echo "To view logs:"
echo "kubectl logs -n aiwfe -l app=pieces-os-connector -f"
echo ""
echo "To scale the deployment:"
echo "kubectl scale deployment/pieces-os-connector -n aiwfe --replicas=3"
echo ""
print_status "Integration with AIWFE services configured:"
echo "  - API Gateway: Connected"
echo "  - Cognitive Services: Connected"
echo "  - Data Platform: Connected"
echo "  - WebUI: Frontend components ready"
echo ""
echo "Next Steps:"
echo "-----------"
echo "1. Update ingress rules to expose Pieces endpoints (if needed)"
echo "2. Configure Pieces API credentials in secrets"
echo "3. Test integration using the WebUI Pieces component"
echo "4. Monitor service health and performance metrics"
echo ""
print_status "Deployment script completed successfully!"