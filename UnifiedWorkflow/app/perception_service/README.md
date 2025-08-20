# Perception Service

AI-powered image analysis and vector generation service using Ollama's LLaVA model for semantic image understanding.

## Overview

The Perception Service converts images into 1536-dimension concept vectors for semantic similarity search and analysis. It provides a high-performance, async FastAPI interface with comprehensive monitoring and production-ready features.

### Key Features

- **Image-to-Vector Conversion**: Transform images into semantic vectors using LLaVA
- **High Performance**: Async architecture with P95 latency < 2 seconds
- **Production Ready**: Health checks, metrics, security middleware
- **Scalable**: Docker-native with resource management
- **Observable**: Structured logging and Prometheus metrics

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client App    │───▶│ Perception API   │───▶│  Ollama LLaVA   │
│                 │    │  (Port 8001)     │    │  (Port 11434)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │ Vector Database  │
                       │    (Optional)    │
                       └──────────────────┘
```

## API Endpoints

### POST /conceptualize

Convert an image to a 1536-dimension concept vector.

**Request Body:**
```json
{
    "image_data": "base64_encoded_image_data",
    "format": "jpeg|png|webp|gif",
    "prompt": "optional custom analysis prompt",
    "max_tokens": 512,
    "temperature": 0.1
}
```

**Response:**
```json
{
    "vector": [0.1, 0.2, ...], // 1536 dimensions
    "dimensions": 1536,
    "processing_time_ms": 1250.5,
    "request_id": "unique_request_id",
    "metadata": {
        "model": "llava",
        "prompt_tokens": 15,
        "completion_tokens": 128
    }
}
```

### GET /health

Service health check with component status.

**Response:**
```json
{
    "status": "healthy|unhealthy|degraded",
    "timestamp": 1641024000.0,
    "checks": {
        "ollama_service": {
            "healthy": true,
            "latency_ms": 45.2
        },
        "llava_model": {
            "ready": true
        }
    },
    "version": "1.0.0",
    "uptime_seconds": 3600.0
}
```

### GET /metrics

Prometheus metrics endpoint for monitoring.

## Quick Start

### 1. Using Docker Compose (Recommended)

The service is included in the main AIWFE docker-compose configuration:

```bash
# Start all services including perception
docker-compose up perception-service

# Or start full stack
docker-compose up
```

### 2. Standalone Docker

```bash
# Build the image
docker build -t aiwfe/perception-service .

# Run with Ollama dependency
docker run -p 8001:8001 \
  -e PERCEPTION_OLLAMA_URL=http://ollama:11434 \
  --network aiwfe-backend \
  aiwfe/perception-service
```

### 3. Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env

# Run with auto-reload
python -m uvicorn main:app --reload --port 8001
```

## Configuration

All configuration is managed through environment variables with the `PERCEPTION_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `PERCEPTION_PORT` | `8001` | Service port |
| `PERCEPTION_OLLAMA_URL` | `http://ollama:11434` | Ollama service URL |
| `PERCEPTION_OLLAMA_MODEL` | `llava` | Model name for analysis |
| `PERCEPTION_VECTOR_DIMENSIONS` | `1536` | Output vector dimensions |
| `PERCEPTION_MAX_IMAGE_SIZE_MB` | `10` | Maximum image size |
| `PERCEPTION_MAX_CONCURRENT_REQUESTS` | `10` | Concurrent request limit |
| `PERCEPTION_DEBUG` | `false` | Enable debug mode |
| `PERCEPTION_LOG_LEVEL` | `INFO` | Logging level |

See `.env.example` for complete configuration options.

## API Usage Examples

### Python

```python
import base64
import httpx

# Prepare image
with open("image.jpg", "rb") as f:
    image_data = base64.b64encode(f.read()).decode()

# Send request
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8001/conceptualize",
        json={
            "image_data": image_data,
            "format": "jpeg",
            "prompt": "Describe this image for search indexing"
        }
    )
    
    result = response.json()
    vector = result["vector"]  # 1536 dimensions
    print(f"Generated vector with {len(vector)} dimensions")
```

### cURL

```bash
# Convert image to base64
BASE64_IMAGE=$(base64 -w 0 image.jpg)

# Send request
curl -X POST http://localhost:8001/conceptualize \
  -H "Content-Type: application/json" \
  -d "{
    \"image_data\": \"$BASE64_IMAGE\",
    \"format\": \"jpeg\",
    \"prompt\": \"Analyze this image for semantic search\"
  }"
```

### JavaScript/Node.js

```javascript
const fs = require('fs');

// Read and encode image
const imageData = fs.readFileSync('image.jpg', 'base64');

// Send request
const response = await fetch('http://localhost:8001/conceptualize', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        image_data: imageData,
        format: 'jpeg',
        prompt: 'Extract visual concepts from this image'
    })
});

const result = await response.json();
console.log(`Vector dimensions: ${result.dimensions}`);
console.log(`Processing time: ${result.processing_time_ms}ms`);
```

## Performance Characteristics

### Benchmarks

- **P95 Latency**: < 2 seconds for 1MB images
- **Throughput**: ~10 concurrent requests (configurable)
- **Memory Usage**: ~512MB baseline, ~2GB under load
- **CPU Usage**: 0.5-2 cores depending on load

### Optimization Tips

1. **Image Size**: Keep images under 5MB for optimal performance
2. **Concurrent Requests**: Tune `MAX_CONCURRENT_REQUESTS` based on resources
3. **Caching**: Consider caching vectors for frequently analyzed images
4. **Network**: Place close to Ollama service to reduce latency

## Monitoring

### Health Checks

The service provides comprehensive health monitoring:

```bash
# Check service health
curl http://localhost:8001/health

# Monitor continuously
watch -n 5 'curl -s http://localhost:8001/health | jq .status'
```

### Metrics

Prometheus metrics are exposed at `/metrics`:

- `perception_http_requests_total`: Request count by endpoint and status
- `perception_http_request_duration_seconds`: Request duration histogram  
- `perception_processing_duration_seconds`: Image processing duration
- `perception_active_requests`: Current active requests

### Logging

Structured JSON logs with request tracing:

```bash
# View logs with Docker
docker logs aiwfe-perception-service -f

# Filter by request ID
docker logs aiwfe-perception-service | jq 'select(.request_id == "123")'
```

## Error Handling

The service provides detailed error responses:

### Common Errors

| Status | Error | Description |
|--------|-------|-------------|
| `400` | `INVALID_FORMAT` | Unsupported image format |
| `400` | `IMAGE_TOO_LARGE` | Image exceeds size limit |
| `400` | `INVALID_BASE64` | Corrupted image data |
| `429` | `RATE_LIMITED` | Too many requests |
| `500` | `SERVICE_ERROR` | Ollama service unavailable |
| `503` | `MODEL_NOT_READY` | LLaVA model not loaded |

### Error Response Format

```json
{
    "detail": "Error description",
    "error_code": "ERROR_TYPE",
    "timestamp": 1641024000.0,
    "request_id": "unique_id"
}
```

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .

# Import sorting
isort .
```

### Docker Development

```bash
# Build development image
docker build --target development -t perception-dev .

# Run with volume mount for live reload
docker run -p 8001:8001 -v $(pwd):/app perception-dev
```

## Production Deployment

### Resource Requirements

**Minimum:**
- CPU: 0.5 cores
- Memory: 512MB
- Storage: 100MB

**Recommended:**
- CPU: 2 cores
- Memory: 2GB
- Storage: 1GB

### Environment Configuration

```yaml
# Production docker-compose override
services:
  perception-service:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
    environment:
      - PERCEPTION_DEBUG=false
      - PERCEPTION_LOG_LEVEL=WARNING
      - PERCEPTION_MAX_CONCURRENT_REQUESTS=20
```

### Security Considerations

1. **Network Isolation**: Run on internal Docker network
2. **Input Validation**: All inputs are validated and sanitized
3. **Rate Limiting**: Built-in rate limiting per client
4. **Resource Limits**: Memory and CPU limits prevent abuse
5. **Security Headers**: Standard security headers applied

## Troubleshooting

### Common Issues

#### Service Won't Start

```bash
# Check Ollama connectivity
curl http://ollama:11434/api/tags

# Check container logs
docker logs aiwfe-perception-service
```

#### Slow Response Times

```bash
# Check Ollama model status
curl http://ollama:11434/api/tags | jq '.models[] | select(.name | startswith("llava"))'

# Monitor resource usage
docker stats aiwfe-perception-service
```

#### High Memory Usage

1. Reduce `MAX_CONCURRENT_REQUESTS`
2. Implement request queuing
3. Add memory limits to container

### Debug Mode

Enable debug mode for detailed logging:

```bash
export PERCEPTION_DEBUG=true
export PERCEPTION_LOG_LEVEL=DEBUG
```

## Integration Examples

### With Vector Database

```python
import qdrant_client
from qdrant_client.models import Distance, VectorParams

# Initialize Qdrant client
client = qdrant_client.QdrantClient("localhost", port=6333)

# Create collection for image vectors
client.create_collection(
    collection_name="images",
    vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
)

# Store vector
client.upsert(
    collection_name="images",
    points=[{
        "id": "image_123",
        "vector": vector,
        "payload": {"url": "image.jpg", "description": "..."}
    }]
)
```

### With FastAPI Application

```python
from fastapi import FastAPI
import httpx

app = FastAPI()

@app.post("/analyze-image")
async def analyze_image(image_data: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://perception-service:8001/conceptualize",
            json={"image_data": image_data, "format": "jpeg"}
        )
        return response.json()
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:

1. Check the [troubleshooting guide](#troubleshooting)
2. Review existing issues on GitHub
3. Create a new issue with detailed information
4. Join our community discussions

---

**Version**: 1.0.0  
**Last Updated**: 2025-01-11  
**Compatibility**: Python 3.12+, Docker 20.10+