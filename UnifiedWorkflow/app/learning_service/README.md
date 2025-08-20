# Learning Service - Adaptive Intelligence Foundation

The Learning Service is the adaptive intelligence foundation of the AI Workflow Engine (AIWFE) cognitive architecture, providing pattern recognition, knowledge graph management, and continuous learning capabilities.

## 🎯 Overview

The learning service implements a sophisticated pattern recognition and learning system that continuously improves from cognitive service outcomes, achieving >80% pattern recognition accuracy with semantic similarity matching and knowledge graph relationship tracking.

### Key Features

- **Pattern Recognition Engine**: >80% accuracy with historical learning
- **Knowledge Graph Management**: Neo4j integration for pattern relationships
- **Continuous Learning**: Feedback loops from cognitive services
- **Semantic Search**: Qdrant vector-based pattern matching
- **Performance Analysis**: Agent and workflow performance tracking
- **Meta-learning**: Learning about learning strategies

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Learning Service (Port 8005)             │
├─────────────────────────────────────────────────────────────┤
│  Pattern Recognition Engine                                 │
│  ├─ Pattern Extraction         ├─ Similarity Matching      │
│  ├─ Context Analysis           ├─ Pattern Adaptation       │
│  └─ Success Validation         └─ Performance Tracking     │
├─────────────────────────────────────────────────────────────┤
│  Knowledge Graph Service                                    │
│  ├─ Neo4j Integration          ├─ Relationship Discovery   │
│  ├─ Graph Traversal            ├─ Pattern Evolution        │
│  └─ Analytics & Insights       └─ Community Detection      │
├─────────────────────────────────────────────────────────────┤
│  Learning Engine                                            │
│  ├─ Continuous Learning        ├─ Cross-Pattern Analysis   │
│  ├─ Session Management         ├─ Performance Optimization │
│  └─ Insight Generation         └─ Statistics Tracking      │
├─────────────────────────────────────────────────────────────┤
│  Performance Analyzer                                       │
│  ├─ Trend Analysis            ├─ Bottleneck Detection      │
│  ├─ Predictive Modeling       ├─ Comparative Analysis      │
│  └─ Optimization Recommendations                           │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Core Components

### Pattern Recognition Engine
- **Pattern Extraction**: Learns from cognitive service outcomes
- **Semantic Matching**: Qdrant vector-based similarity search
- **Pattern Adaptation**: Context-aware pattern modification
- **Success Validation**: >85% validation accuracy target

### Knowledge Graph Service
- **Neo4j Integration**: Graph database for pattern relationships
- **Relationship Discovery**: Automatic pattern relationship detection
- **Graph Analytics**: Centrality, clustering, and community detection
- **Pattern Evolution**: Tracks how patterns change over time

### Learning Engine
- **Continuous Learning**: Real-time learning from system outcomes
- **Session Management**: Groups related learning events
- **Cross-Pattern Analysis**: Identifies relationships between patterns
- **Performance Optimization**: Improves learning effectiveness

### Performance Analyzer
- **Trend Analysis**: Identifies performance patterns over time
- **Bottleneck Detection**: Finds system performance issues
- **Predictive Modeling**: Forecasts future performance
- **Optimization Recommendations**: AI-driven improvement suggestions

## 📊 Performance Targets

| Metric | Target | Current |
|--------|---------|---------|
| Pattern Recognition Accuracy | >80% | Configurable |
| Application Success Rate | >75% | Tracked |
| Similarity Threshold | >85% | 0.85 |
| Monthly Improvement Rate | >10% | Monitored |
| Response Time | <2s | Optimized |

## 🚀 API Endpoints

### Core Learning APIs

#### Learn from Outcome
```http
POST /learn/outcome
Content-Type: application/json

{
    "outcome_type": "reasoning_success",
    "service_name": "reasoning-service", 
    "context": {"workflow_id": "abc123"},
    "input_data": {"query": "analyze data"},
    "output_data": {"result": "analysis complete"},
    "performance_metrics": {"execution_time": 2.5}
}
```

#### Search Patterns
```http
POST /patterns/search
Content-Type: application/json

{
    "context": {"domain": "data_analysis"},
    "search_scope": "global",
    "similarity_threshold": 0.85,
    "max_results": 10
}
```

#### Apply Pattern
```http
POST /patterns/apply
Content-Type: application/json

{
    "pattern_id": "pattern_123",
    "current_context": {"domain": "data_analysis"},
    "adaptation_enabled": true,
    "confidence_threshold": 0.7
}
```

#### Performance Analysis
```http
POST /analyze/performance
Content-Type: application/json

{
    "analysis_type": "agent",
    "subject_id": "reasoning-agent-1",
    "time_range": {
        "start": "2024-01-01T00:00:00Z",
        "end": "2024-01-07T23:59:59Z"
    },
    "metrics": ["success_rate", "accuracy"],
    "granularity": "daily"
}
```

#### Get Recommendations
```http
POST /recommendations
Content-Type: application/json

{
    "context": {"system_load": 0.8},
    "focus_areas": ["performance", "accuracy"],
    "performance_goals": {"success_rate": 0.95},
    "priority": "balanced"
}
```

### Utility APIs

- `GET /health` - Service health check with detailed metrics
- `GET /knowledge/graph` - Knowledge graph visualization data
- `GET /patterns/{pattern_id}/relationships` - Pattern relationships

## 🛠️ Configuration

### Environment Variables

#### Service Configuration
- `LEARNING_PORT`: Service port (default: 8005)
- `LEARNING_LOG_LEVEL`: Logging level (default: INFO)
- `LEARNING_DEBUG`: Debug mode (default: false)

#### Database Configuration
- `LEARNING_NEO4J_URL`: Neo4j connection URL
- `LEARNING_NEO4J_AUTH`: Neo4j authentication (username/password)
- `LEARNING_QDRANT_URL`: Qdrant vector database URL
- `LEARNING_REDIS_URL`: Redis cache URL

#### Learning Parameters
- `LEARNING_PATTERN_THRESHOLD`: Pattern recognition threshold (0.80)
- `LEARNING_SIMILARITY_THRESHOLD`: Similarity matching threshold (0.85)
- `LEARNING_CONFIDENCE_THRESHOLD`: Confidence threshold (0.70)
- `LEARNING_RATE`: Learning rate (0.1)
- `LEARNING_ADAPTATION_RATE`: Pattern adaptation rate (0.05)

#### Performance Configuration
- `LEARNING_MAX_CONCURRENT`: Max concurrent requests (25)
- `LEARNING_BATCH_SIZE`: Batch processing size (50)
- `LEARNING_PATTERN_CACHE_TTL`: Pattern cache TTL (3600s)

## 📈 Monitoring & Metrics

### Health Metrics
- Service connectivity (Neo4j, Qdrant, Redis)
- Pattern recognition accuracy
- Application success rates
- Response times and throughput

### Performance Metrics
- Patterns stored and active
- Knowledge graph nodes and edges
- Learning session statistics
- Cache hit rates and efficiency

### Business Metrics
- Monthly improvement rates
- Pattern application success
- System optimization impact
- User experience improvements

## 🔒 Security Features

- **Authentication**: Integrated with AIWFE security framework
- **Authorization**: Role-based access to learning operations
- **Data Protection**: Encrypted pattern and knowledge storage
- **Audit Logging**: Comprehensive operation tracking
- **Rate Limiting**: Request throttling and DoS protection

## 🧪 Development & Testing

### Running Tests
```bash
# Unit tests
pytest tests/

# Integration tests
pytest tests/test_integration_api.py

# Performance benchmarks
pytest tests/test_performance_benchmarks.py

# Coverage report
pytest --cov=app --cov-report=html
```

### Development Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run in development mode
uvicorn main:app --reload --port 8005

# Run with Docker
docker-compose up learning-service
```

## 📚 Integration Examples

### Learning from Reasoning Service
```python
# Automatically called by reasoning service
await learning_service.learn_from_outcome(
    outcome_type="reasoning_success",
    service_name="reasoning-service",
    context={"agent_id": "reasoning-001"},
    input_data={"hypothesis": "user_intent_classification"},
    output_data={"confidence": 0.92, "result": "classified"},
    performance_metrics={"execution_time": 1.2}
)
```

### Pattern-based Recommendations
```python
# Get optimization recommendations
recommendations = await learning_service.get_recommendations(
    context={"current_performance": 0.75},
    performance_goals={"success_rate": 0.90},
    focus_areas=["accuracy", "speed"]
)
```

## 🎯 Future Enhancements

- **Advanced Meta-learning**: Deep learning strategy optimization
- **Federated Learning**: Cross-system pattern sharing
- **Explainable AI**: Pattern decision explanations
- **Real-time Adaptation**: Sub-second pattern application
- **Predictive Analytics**: Advanced performance forecasting

---

The Learning Service represents the cutting edge of adaptive intelligence, continuously evolving and improving the AIWFE cognitive architecture through sophisticated pattern recognition and knowledge graph management.