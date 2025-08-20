# Pieces OS Integration for AIWFE

## Overview

The Pieces OS/Developers connectivity container has been successfully integrated into the AIWFE Kubernetes ecosystem. This integration enhances developer productivity by providing AI-powered code assistance, snippet management, and workflow context synchronization.

## Architecture

### Components

1. **Pieces OS Connector Service** (`pieces-os-connector`)
   - Kubernetes deployment with 2 replicas
   - Exposes REST API on port 8200
   - Metrics endpoint on port 9200
   - Health checks on port 9201

2. **Backend Integration** (`pieces_integration.py`)
   - FastAPI-based service
   - JWT authentication
   - Redis caching
   - Integration with AIWFE services

3. **Frontend Components** (`PiecesIntegration.tsx`)
   - React component for WebUI
   - Code snippet management
   - AI assistance interface
   - Workflow context visualization

4. **API Route Handler** (`app/api/pieces/[...path]/route.ts`)
   - Next.js API proxy
   - Authentication forwarding
   - Request routing

## Deployment

### Prerequisites

- Kubernetes cluster with AIWFE deployed
- Docker for building images
- kubectl configured for cluster access

### Quick Deployment

```bash
# Run the deployment script
./deploy-pieces-integration.sh
```

### Manual Deployment

1. **Build Docker Image**
```bash
cd app/backend
docker build -f Dockerfile.pieces -t aiwfe/pieces-os-connector:latest .
```

2. **Apply Kubernetes Manifests**
```bash
kubectl apply -f k8s/pieces-os-connector.yaml
```

3. **Verify Deployment**
```bash
kubectl get pods -n aiwfe -l app=pieces-os-connector
kubectl get svc pieces-os-connector -n aiwfe
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GATEWAY_URL` | AIWFE API Gateway URL | `http://aiwfe-unified-gateway:8000` |
| `COGNITIVE_SERVICES_URL` | Cognitive Services URL | `http://aiwfe-cognitive-services:8001` |
| `DATA_PLATFORM_URL` | Data Platform URL | `http://aiwfe-data-platform:8100` |
| `REDIS_URL` | Redis connection URL | `redis://aiwfe-data-platform:6379/2` |
| `JWT_SECRET_KEY` | JWT signing secret | (from secret) |
| `API_KEY` | Internal API key | (from secret) |
| `PIECES_API_KEY` | Pieces API key | (optional) |

### Secrets Management

Create required secrets:
```bash
# Auth secret
kubectl create secret generic aiwfe-auth-secret \
  --from-literal=jwt-secret=<your-jwt-secret> \
  --from-literal=csrf-secret=<your-csrf-secret> \
  -n aiwfe

# API secret
kubectl create secret generic aiwfe-api-secret \
  --from-literal=api-key=<your-api-key> \
  -n aiwfe

# Pieces API secret (if using Pieces cloud services)
kubectl create secret generic pieces-api-secret \
  --from-literal=api-key=<pieces-api-key> \
  -n aiwfe
```

## API Endpoints

### Code Snippets

- `POST /api/v1/snippets` - Create a new code snippet
- `GET /api/v1/snippets` - List user's snippets
- `GET /api/v1/snippets/{snippet_id}` - Get specific snippet

### AI Assistance

- `POST /api/v1/ai-assist` - Get AI assistance for development tasks

### Workflow Context

- `POST /api/v1/workflow-context` - Update workflow context

### Health & Monitoring

- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe
- `GET /metrics` - Prometheus metrics

## Integration Points

### 1. API Gateway Integration
The Pieces connector integrates with the unified API gateway for:
- Authentication and authorization
- Request routing
- Rate limiting

### 2. Cognitive Services Integration
Connects to cognitive services for:
- AI-powered code analysis
- Snippet enrichment
- Development assistance

### 3. Data Platform Integration
Synchronizes with the data platform for:
- Snippet persistence
- User context storage
- Analytics data

### 4. WebUI Integration
Frontend components provide:
- Code snippet management UI
- AI assistance interface
- Workflow visualization

## Usage

### In the WebUI

1. Navigate to the Pieces section in the AIWFE dashboard
2. Use the Code Snippets tab to save and manage code
3. Use the AI Assistance tab for development help
4. Monitor workflow context in the Workflow tab

### Via API

```bash
# Save a code snippet
curl -X POST https://aiwfe.com/api/pieces/v1/snippets \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Example Function",
    "code": "def hello(): return \"Hello World\"",
    "language": "python",
    "tags": ["example", "function"]
  }'

# Get AI assistance
curl -X POST https://aiwfe.com/api/pieces/v1/ai-assist \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How can I optimize this function?",
    "context": {"current_code": "def hello(): return \"Hello World\""}
  }'
```

## Monitoring

### Metrics

The service exposes Prometheus metrics including:
- Request counts and latencies
- Active connections
- Error rates
- Cache hit rates

### Logging

View logs:
```bash
kubectl logs -n aiwfe -l app=pieces-os-connector -f
```

### Health Checks

The service includes:
- Liveness probe: Checks if service is running
- Readiness probe: Checks Redis connectivity

## Scaling

### Horizontal Scaling

The deployment includes HPA (Horizontal Pod Autoscaler):
- Min replicas: 2
- Max replicas: 5
- CPU target: 70%
- Memory target: 80%

Manual scaling:
```bash
kubectl scale deployment/pieces-os-connector -n aiwfe --replicas=3
```

## Security

### Network Policies

The service implements strict network policies:
- Ingress: Only from API gateway
- Egress: Only to AIWFE services and external HTTPS

### Authentication

- JWT-based authentication
- Token validation on all endpoints
- Secure secret management

## Troubleshooting

### Common Issues

1. **Pod not starting**
   - Check secrets are created
   - Verify image is built and available
   - Check resource limits

2. **Connection errors**
   - Verify service discovery
   - Check network policies
   - Validate Redis connectivity

3. **Authentication failures**
   - Verify JWT secret matches
   - Check token expiry
   - Validate CORS settings

### Debug Commands

```bash
# Check pod status
kubectl describe pod -n aiwfe -l app=pieces-os-connector

# View recent events
kubectl get events -n aiwfe --sort-by='.lastTimestamp'

# Test service connectivity
kubectl run -it --rm debug --image=alpine --restart=Never -n aiwfe -- \
  wget -qO- http://pieces-os-connector:8200/health/live

# Port forward for local testing
kubectl port-forward -n aiwfe svc/pieces-os-connector 8200:8200
```

## Performance Optimization

### Caching Strategy

- Redis caching for snippets (24-hour TTL)
- Workflow context caching (1-hour TTL)
- Connection pooling for database access

### Resource Limits

Current configuration:
- Request: 256Mi memory, 250m CPU
- Limit: 512Mi memory, 500m CPU

Adjust based on usage patterns.

## Future Enhancements

1. **Advanced AI Features**
   - Code review automation
   - Refactoring suggestions
   - Bug detection

2. **Collaboration Features**
   - Snippet sharing
   - Team workspaces
   - Code review workflows

3. **Integration Extensions**
   - IDE plugins
   - CI/CD integration
   - Git hooks

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review logs for error messages
3. Contact the AIWFE team

## Version History

- **v1.0.0** (2024-08-13): Initial integration
  - Core functionality implemented
  - Kubernetes deployment configured
  - WebUI components added
  - API endpoints established