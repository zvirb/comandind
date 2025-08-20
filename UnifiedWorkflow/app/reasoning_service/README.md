# Reasoning Service

The Reasoning Service is the foundational component of the AIWFE cognitive architecture, providing evidence-based validation, multi-criteria decision making, hypothesis testing, and multi-step reasoning chains with >85% accuracy requirements.

## Features

### Core Capabilities
- **Evidence Validation**: Systematic validation with >85% accuracy requirement
- **Multi-Criteria Decision Analysis**: Weighted criteria evaluation with confidence scoring
- **Hypothesis Testing**: Reality testing with statistical and Bayesian analysis
- **Reasoning Chains**: Multi-step logical progression with consistency validation

### Technical Features
- **Event-Driven Architecture**: Cognitive event communication via Redis
- **Service Integration**: Seamless integration with memory, perception, and learning services
- **Performance Optimization**: <2s response time for complex reasoning tasks
- **Comprehensive Monitoring**: Prometheus metrics and structured logging
- **Production Ready**: Docker containerization with health checks

## API Endpoints

### Evidence Validation
```
POST /validate/evidence
```
Validates evidence using multiple criteria including source credibility, factual consistency, statistical validity, and bias assessment.

**Request Example:**
```json
{
  "evidence": [
    {
      "content": "Multiple peer-reviewed studies show correlation",
      "source": "Academic research database",
      "confidence": 0.9
    }
  ],
  "context": "Evaluating research findings for policy decisions",
  "require_high_confidence": true
}
```

### Multi-Criteria Decision Making
```
POST /decide/multi-criteria
```
Performs comprehensive decision analysis using weighted criteria, trade-off analysis, and risk assessment.

**Request Example:**
```json
{
  "context": "Selecting software architecture for new system",
  "options": [
    {
      "name": "Microservices",
      "description": "Distributed microservices architecture",
      "attributes": {"complexity": 8, "scalability": 9, "cost": 7}
    }
  ],
  "criteria": [
    {"name": "Scalability", "weight": 0.4, "measurement_type": "numeric"}
  ]
}
```

### Hypothesis Testing
```
POST /test/hypothesis
```
Tests hypotheses using statistical analysis, Bayesian inference, and alternative hypothesis consideration.

**Request Example:**
```json
{
  "hypothesis": "New feature will increase user engagement by 15%",
  "evidence": [
    {
      "content": "A/B test results show 12% increase in session duration",
      "source": "Analytics platform",
      "confidence": 0.88
    }
  ],
  "significance_level": 0.05
}
```

### Reasoning Chains
```
POST /reasoning/chain
```
Processes multi-step reasoning with logical consistency validation and alternative path exploration.

**Request Example:**
```json
{
  "initial_premise": "System shows high CPU usage and memory leaks",
  "goal": "Determine root cause and solution",
  "reasoning_type": "abductive",
  "max_steps": 5
}
```

## Configuration

The service is configured via environment variables:

### Core Settings
- `REASONING_PORT`: Service port (default: 8003)
- `REASONING_LOG_LEVEL`: Logging level (default: INFO)
- `REASONING_DEBUG`: Enable debug mode (default: false)

### Integration URLs
- `REASONING_OLLAMA_URL`: Ollama service URL
- `REASONING_HYBRID_MEMORY_URL`: Memory service URL
- `REASONING_PERCEPTION_SERVICE_URL`: Perception service URL

### Reasoning Parameters
- `REASONING_EVIDENCE_THRESHOLD`: Evidence validation threshold (≥0.85)
- `REASONING_CONFIDENCE_THRESHOLD`: Confidence threshold (default: 0.70)
- `REASONING_MAX_STEPS`: Maximum reasoning steps (default: 10)

### Performance Settings
- `REASONING_MAX_CONCURRENT_REQUESTS`: Max concurrent requests (default: 20)
- `REASONING_REQUEST_TIMEOUT`: Request timeout seconds (default: 30)

## Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python -m uvicorn main:app --host 0.0.0.0 --port 8003 --reload
```

### Testing
```bash
# Run tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ -v --cov=. --cov-report=html
```

### Docker Development
```bash
# Build development image
docker build --target development -t reasoning-service:dev .

# Run development container
docker run -p 8003:8003 reasoning-service:dev
```

## Production Deployment

### Docker
```bash
# Build production image
docker build --target production -t reasoning-service:latest .

# Run production container
docker run -p 8003:8003 reasoning-service:latest
```

### Docker Compose
The service is integrated into the main AIWFE docker-compose setup:

```bash
# Start all services
docker-compose up -d

# View reasoning service logs
docker-compose logs reasoning-service
```

## Monitoring

### Health Check
```
GET /health
```
Returns comprehensive health status including cognitive capabilities.

### Metrics
```
GET /metrics
```
Prometheus metrics endpoint with reasoning-specific metrics:
- `reasoning_requests_total`: Total requests by endpoint and status
- `reasoning_evidence_validation_accuracy`: Evidence validation accuracy scores
- `reasoning_decision_confidence_score`: Decision confidence scores
- `reasoning_chain_steps_count`: Number of steps in reasoning chains

## Architecture

### Service Integration
```
┌─────────────────────┐    ┌──────────────────────┐
│   Reasoning Service │    │   Hybrid Memory      │
│                     │◄──►│   Service            │
│  ┌───────────────┐  │    └──────────────────────┘
│  │ Evidence      │  │
│  │ Validator     │  │    ┌──────────────────────┐
│  └───────────────┘  │    │   Perception         │
│                     │◄──►│   Service            │
│  ┌───────────────┐  │    └──────────────────────┘
│  │ Decision      │  │
│  │ Analyzer      │  │    ┌──────────────────────┐
│  └───────────────┘  │    │   Coordination       │
│                     │◄──►│   Service            │
│  ┌───────────────┐  │    └──────────────────────┘
│  │ Hypothesis    │  │
│  │ Tester        │  │    ┌──────────────────────┐
│  └───────────────┘  │    │   Learning           │
│                     │◄──►│   Service            │
│  ┌───────────────┐  │    └──────────────────────┘
│  │ Reasoning     │  │
│  │ Engine        │  │
│  └───────────────┘  │
└─────────────────────┘
```

### Cognitive Event Flow
1. **Request Processing**: Validate and process reasoning requests
2. **LLM Integration**: Use Ollama for structured reasoning tasks
3. **Memory Integration**: Retrieve context and store results
4. **Event Publishing**: Notify coordination service of completion
5. **Learning Feedback**: Send outcomes to learning service

## Performance Requirements

- **Response Time**: <2s for complex reasoning tasks
- **Accuracy**: >85% evidence validation accuracy
- **Availability**: >99% uptime with health monitoring
- **Throughput**: 20 concurrent requests with graceful degradation

## Error Handling

The service implements comprehensive error handling:
- **Validation Errors** (400): Invalid request data
- **Processing Errors** (500): Internal processing failures
- **Timeout Errors**: Configurable timeouts with fallbacks
- **Service Integration Errors**: Graceful degradation when services unavailable

All errors are logged with structured logging and request tracking.

## License

Part of the AIWFE (AI Workflow Engine) project. See main project LICENSE for details.