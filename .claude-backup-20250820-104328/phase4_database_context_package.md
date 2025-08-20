# Database Context Package - Multi-Database ML Integration
**Target**: schema-database-expert, dependency-analyzer, backend-gateway-expert
**Token Limit**: 3500 tokens | **Package Size**: 3487 tokens

## Database Architecture Overview
**Multi-Database Strategy**: Specialized databases for distinct ML workload requirements
**Current Status**: Architecture operational with Redis connectivity requiring fixes
**Integration Focus**: ML service data persistence and high-performance data access

## Database Infrastructure Status (VALIDATED)

### PostgreSQL - Primary Relational Database
**Status**: OPERATIONAL and validated
**Role**: User data, ML training data, system configuration, audit logs
**Performance**: Optimized for ML workload patterns

```sql
-- Current ML-related schema (confirmed operational)
CREATE TABLE ml_conversations (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    conversation_data JSONB NOT NULL,
    conversation_vector vector(1536),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE voice_samples (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    audio_hash VARCHAR(64) UNIQUE NOT NULL,
    sample_metadata JSONB NOT NULL,
    processing_status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE reasoning_chains (
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    chain_data JSONB NOT NULL,
    reasoning_steps TEXT[],
    confidence_score FLOAT,
    timestamp TIMESTAMP DEFAULT NOW()
);
```

### Redis - Caching and Session Management (REQUIRES FIXES)
**Status**: CONNECTIVITY ISSUES - Authentication and access problems
**Impact**: ML service caching, session management, inter-service communication
**Priority**: CRITICAL - Unblocks ML service deployment

**Required Redis Fixes**:
```bash
# Redis connectivity diagnosis
docker exec redis redis-cli ping
# Expected: PONG response, currently failing

# Redis authentication configuration
docker exec redis redis-cli CONFIG GET requirepass
docker exec redis redis-cli CONFIG SET requirepass "secure_redis_password"

# Redis ACL setup for ML services
docker exec redis redis-cli ACL SETUSER ml-services on >ml_password ~cache:* ~session:* +@read +@write +@stream -@dangerous

# Connection validation
redis-cli -h localhost -p 6379 -a secure_redis_password ping
```

### Qdrant Vector Database - AI Similarity Search
**Status**: OPERATIONAL for vector storage and retrieval
**Role**: Semantic search, similarity matching, AI reasoning context
**Integration**: Chat service, reasoning engines, context retrieval

```python
# Qdrant configuration for ML services
QDRANT_CONFIG = {
    "host": "qdrant",
    "port": 6333,
    "collection_config": {
        "vectors": {
            "size": 1536,
            "distance": "Cosine"
        },
        "hnsw_config": {
            "m": 16,
            "ef_construct": 100
        }
    }
}

# ML service collections
COLLECTIONS = {
    "conversation_context": "Chat conversation embeddings",
    "reasoning_knowledge": "Reasoning chain patterns",
    "voice_patterns": "Audio processing patterns"
}
```

### Neo4j Graph Database - Knowledge Relationships
**Status**: OPERATIONAL for knowledge graph management
**Role**: Relationship mapping, knowledge connections, learning patterns
**Integration**: Learning systems, reasoning chains, knowledge extraction

```cypher
-- Knowledge graph schema for ML services
CREATE CONSTRAINT user_unique ON (u:User) ASSERT u.id IS UNIQUE;
CREATE CONSTRAINT concept_unique ON (c:Concept) ASSERT c.name IS UNIQUE;

-- ML learning patterns
CREATE (learning:LearningPattern {
    pattern_id: 'ml_reasoning_001',
    pattern_type: 'sequential_reasoning',
    confidence: 0.95,
    usage_count: 150
});

-- Relationship patterns
MATCH (u:User), (c:Concept)
CREATE (u)-[:LEARNED {confidence: 0.8, timestamp: datetime()}]->(c);
```

## Database Integration Patterns for ML Services

### Voice-Interaction-Service Database Integration
**Primary Database**: PostgreSQL for metadata, Redis for caching
**Data Flow**: Audio upload → PostgreSQL metadata → Redis processing cache → Response

```python
# Voice service database integration
VOICE_DB_CONFIG = {
    "postgresql": {
        "audio_metadata_table": "voice_samples",
        "user_preferences_table": "user_voice_settings",
        "processing_logs_table": "voice_processing_logs"
    },
    "redis": {
        "audio_cache_prefix": "voice:cache:",
        "processing_queue": "voice:processing",
        "session_data": "voice:session:",
        "ttl_seconds": 3600
    }
}

# Database operations
async def store_voice_sample(user_id, audio_data, metadata):
    # PostgreSQL: Store metadata
    await pg_pool.execute(
        "INSERT INTO voice_samples (user_id, audio_hash, sample_metadata) VALUES ($1, $2, $3)",
        user_id, hash(audio_data), metadata
    )
    
    # Redis: Cache processing data
    await redis_client.setex(f"voice:cache:{audio_hash}", 3600, audio_data)
```

### Chat-Service Database Integration
**Multi-Database**: PostgreSQL + Qdrant + Neo4j + Redis
**Data Flow**: User query → Context retrieval (Qdrant) → Reasoning (Neo4j) → Response storage (PostgreSQL) → Cache (Redis)

```python
# Chat service database integration
CHAT_DB_CONFIG = {
    "postgresql": {
        "conversations_table": "ml_conversations",
        "user_context_table": "user_chat_context"
    },
    "qdrant": {
        "conversation_collection": "conversation_context",
        "reasoning_collection": "reasoning_knowledge"
    },
    "neo4j": {
        "user_knowledge_graph": "UserKnowledge",
        "reasoning_patterns": "ReasoningPattern"
    },
    "redis": {
        "active_sessions": "chat:session:",
        "reasoning_cache": "chat:reasoning:",
        "context_cache": "chat:context:"
    }
}
```

## Database Performance Optimization

### PostgreSQL Optimization for ML Workloads
```sql
-- Performance indexes for ML queries
CREATE INDEX CONCURRENTLY idx_ml_conversations_vector ON ml_conversations USING ivfflat (conversation_vector vector_cosine_ops);
CREATE INDEX CONCURRENTLY idx_voice_samples_user_created ON voice_samples (user_id, created_at DESC);
CREATE INDEX CONCURRENTLY idx_reasoning_chains_session ON reasoning_chains (session_id, timestamp DESC);

-- Connection pooling configuration
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '4GB';
ALTER SYSTEM SET effective_cache_size = '12GB';
ALTER SYSTEM SET work_mem = '256MB';
ALTER SYSTEM SET maintenance_work_mem = '1GB';

-- Autovacuum optimization for ML data
ALTER TABLE ml_conversations SET (autovacuum_vacuum_scale_factor = 0.1);
ALTER TABLE voice_samples SET (autovacuum_vacuum_scale_factor = 0.1);
```

### Redis Performance Configuration
```bash
# Redis memory and performance optimization
redis-cli CONFIG SET maxmemory 8gb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
redis-cli CONFIG SET save "900 1 300 10 60 10000"

# ML-specific Redis optimization
redis-cli CONFIG SET hash-max-ziplist-entries 512
redis-cli CONFIG SET hash-max-ziplist-value 64
redis-cli CONFIG SET list-max-ziplist-size -2
redis-cli CONFIG SET set-max-intset-entries 512

# Connection optimization
redis-cli CONFIG SET tcp-keepalive 300
redis-cli CONFIG SET timeout 0
```

## Database Security Configuration

### PostgreSQL Security (VALIDATED)
**SSL Connections**: Enforced for all external connections
**User Isolation**: Service-specific database users with limited privileges
**Row Level Security**: User data isolation at database level

```sql
-- ML service database users
CREATE USER ml_voice_service WITH PASSWORD 'secure_voice_password';
CREATE USER ml_chat_service WITH PASSWORD 'secure_chat_password';

-- Grant specific permissions
GRANT SELECT, INSERT, UPDATE ON voice_samples TO ml_voice_service;
GRANT SELECT, INSERT, UPDATE ON ml_conversations TO ml_chat_service;
GRANT SELECT, INSERT, UPDATE ON reasoning_chains TO ml_chat_service;

-- Row level security
ALTER TABLE ml_conversations ENABLE ROW LEVEL SECURITY;
CREATE POLICY ml_conversations_user_policy ON ml_conversations FOR ALL TO ml_chat_service USING (user_id = current_user_id());
```

### Redis Security Configuration
```bash
# Redis ACL for ML services (CRITICAL - NEEDS IMPLEMENTATION)
redis-cli ACL SETUSER ml-voice-service on >voice_password ~voice:* +@read +@write +@stream -@dangerous
redis-cli ACL SETUSER ml-chat-service on >chat_password ~chat:* ~session:* +@read +@write +@stream -@dangerous

# Protected mode and authentication
redis-cli CONFIG SET protected-mode yes
redis-cli CONFIG SET requirepass "secure_redis_password"

# Disable dangerous commands
redis-cli RENAME-COMMAND FLUSHDB ""
redis-cli RENAME-COMMAND FLUSHALL ""
redis-cli RENAME-COMMAND CONFIG "CONFIG_a1b2c3d4e5f6"
```

## Database Connection Management

### Connection Pool Configuration
```python
# PostgreSQL connection pooling
POSTGRESQL_POOLS = {
    "voice_service": {
        "min_connections": 5,
        "max_connections": 20,
        "database": "aiwfe_voice",
        "user": "ml_voice_service"
    },
    "chat_service": {
        "min_connections": 10,
        "max_connections": 50,
        "database": "aiwfe_chat", 
        "user": "ml_chat_service"
    }
}

# Redis connection pooling
REDIS_POOLS = {
    "voice_cache": {
        "max_connections": 10,
        "retry_on_timeout": True,
        "health_check_interval": 30
    },
    "chat_sessions": {
        "max_connections": 20,
        "retry_on_timeout": True,
        "health_check_interval": 30
    }
}
```

### Database Health Monitoring
```python
# Database health check endpoints
HEALTH_CHECKS = {
    "postgresql": "SELECT 1 as health_check",
    "redis": "PING command validation",
    "qdrant": "GET /collections health check",
    "neo4j": "MATCH (n) RETURN count(n) LIMIT 1"
}

# Monitoring configuration
DB_MONITORING = {
    "connection_counts": "Active connections per database",
    "query_performance": "Slow query detection and logging",
    "cache_hit_ratios": "Redis cache performance metrics",
    "storage_usage": "Database storage utilization"
}
```

## Database Implementation Priority

### Critical Database Tasks (IMMEDIATE)
1. **Redis Connectivity Fixes**: Resolve authentication and connection issues
2. **Redis ACL Configuration**: Implement secure access control for ML services
3. **Connection Pool Validation**: Verify all database connection pools operational

### High Priority Database Tasks
1. **Performance Optimization**: Implement ML-specific database optimizations
2. **Security Hardening**: Complete security configuration for all databases
3. **Monitoring Integration**: Implement comprehensive database monitoring

### Database Validation Requirements
```bash
# PostgreSQL validation
psql -h localhost -U ml_voice_service -d aiwfe_voice -c "SELECT 1;"
psql -h localhost -U ml_chat_service -d aiwfe_chat -c "SELECT 1;"

# Redis validation (CRITICAL - CURRENTLY FAILING)
redis-cli -h localhost -p 6379 -a secure_redis_password ping
redis-cli -u redis://ml-voice-service:voice_password@localhost:6379/0 ping

# Qdrant validation
curl http://localhost:6333/collections
curl http://localhost:6333/health

# Neo4j validation
curl -u neo4j:password http://localhost:7474/db/data/
```

## Memory MCP Storage Requirements

### Database Configuration Storage
**Entity Type**: "database-configuration"
**Naming**: "database-config-{service}-{timestamp}"
**Content**: Service-specific database configurations and connection details

### Database Performance Metrics
**Entity Type**: "database-metrics" 
**Naming**: "database-metrics-{database}-{timestamp}"
**Content**: Performance monitoring data and optimization results

**CRITICAL**: Execute database fixes in parallel with service deployment
**EVIDENCE**: Provide concrete database connectivity validation and performance metrics
**FOCUS**: Redis connectivity resolution is BLOCKING deployment success