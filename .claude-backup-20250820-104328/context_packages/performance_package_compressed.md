# Performance Context Package (Compressed)
**Target Agents**: performance-profiler, monitoring-analyst  
**Token Limit**: 4000 | **Estimated Size**: 3,600 tokens | **Compression Ratio**: 72%

## ⚡ CURRENT PERFORMANCE BASELINE

### Response Time Analysis
```yaml
Current Performance Metrics:
  API Endpoints:
    /api/health: 45ms avg, 120ms p99
    /api/calendar/events: 180ms avg, 450ms p99
    /api/tasks: 95ms avg, 280ms p99
    /api/auth/refresh: 110ms avg, 340ms p99
    
  Database Queries:
    Simple SELECT: 15ms avg, 45ms p99
    Complex JOIN: 85ms avg, 220ms p99
    Calendar aggregations: 140ms avg, 380ms p99
    
  Redis Operations:
    GET: 2ms avg, 8ms p99
    SET: 3ms avg, 12ms p99
    Session lookup: 5ms avg, 18ms p99
```

### Resource Utilization
```yaml
Container Resource Usage:
  API Container:
    CPU: 35% avg, 75% peak
    Memory: 280MB avg, 450MB peak
    Connections: 45 avg, 120 peak
    
  Worker Container:
    CPU: 20% avg, 60% peak
    Memory: 180MB avg, 320MB peak
    Queue depth: 8 avg, 35 peak
    
  Database:
    CPU: 25% avg, 55% peak
    Memory: 512MB avg, 800MB peak
    Connections: 12 avg, 25 peak
    Storage I/O: 45 IOPS avg, 180 peak
```

## 🎯 PERFORMANCE BOTTLENECKS IDENTIFIED

### Critical Performance Issues
```python
# 1. N+1 Query Problems in Calendar Module
# Current inefficient pattern:
async def get_user_events_slow(user_id: int):
    events = await get_events(user_id)
    for event in events:
        event.attendees = await get_attendees(event.id)  # N+1!
    return events

# Optimized solution:
async def get_user_events_fast(user_id: int):
    query = select(Event).options(
        selectinload(Event.attendees)
    ).where(Event.user_id == user_id)
    return await session.execute(query)

# 2. Inefficient Pagination
# Current: OFFSET-based pagination (slow for large datasets)
SELECT * FROM tasks WHERE user_id = ? ORDER BY created_at OFFSET ? LIMIT ?

# Optimized: Cursor-based pagination
SELECT * FROM tasks WHERE user_id = ? AND created_at > ? ORDER BY created_at LIMIT ?
```

### Database Performance Issues
```sql
-- Missing Indexes (High Impact)
CREATE INDEX CONCURRENTLY idx_tasks_user_status ON tasks(user_id, status);
CREATE INDEX CONCURRENTLY idx_events_user_date ON calendar_events(user_id, event_date);
CREATE INDEX CONCURRENTLY idx_sessions_token ON user_sessions(session_token);

-- Query Optimization Required
-- Before: Full table scan
SELECT * FROM tasks WHERE description ILIKE '%keyword%';

-- After: Full-text search
ALTER TABLE tasks ADD COLUMN search_vector tsvector;
CREATE INDEX idx_tasks_fts ON tasks USING gin(search_vector);
```

### Caching Strategy Issues
```python
# Current: No caching for expensive operations
# Target: Aggressive caching with invalidation

CACHE_STRATEGIES = {
    'user_profile': {'ttl': 3600, 'invalidate_on': ['profile_update']},
    'calendar_monthly': {'ttl': 1800, 'invalidate_on': ['event_create', 'event_update']},
    'task_counters': {'ttl': 300, 'invalidate_on': ['task_status_change']},
    'oauth_userinfo': {'ttl': 7200, 'invalidate_on': ['token_refresh']},
}
```

## 🚀 OPTIMIZATION IMPLEMENTATION PLAN

### API Performance Enhancements
```python
# 1. Response Compression
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 2. Background Tasks for Heavy Operations
@app.post("/api/calendar/sync")
async def sync_calendar(background_tasks: BackgroundTasks):
    background_tasks.add_task(perform_google_calendar_sync, user_id)
    return {"status": "sync_initiated"}

# 3. Connection Pooling Optimization
DATABASE_CONFIG = {
    'pool_size': 20,
    'max_overflow': 30,
    'pool_pre_ping': True,
    'pool_recycle': 3600,
    'pool_timeout': 30,
}

# 4. Async Database Operations
async def bulk_create_tasks(tasks: List[TaskCreate], db: AsyncSession):
    db_tasks = [Task(**task.dict()) for task in tasks]
    db.add_all(db_tasks)
    await db.commit()
    return db_tasks
```

### Frontend Performance Optimizations
```typescript
// 1. Virtual Scrolling for Large Lists
import { VirtualList } from '@sveltejs/virtual-list';

// 2. Lazy Loading Components
const CalendarView = lazy(() => import('./CalendarView.svelte'));

// 3. API Response Caching
const apiCache = new Map();
async function fetchWithCache(url: string, ttl: number = 300000) {
    const cached = apiCache.get(url);
    if (cached && Date.now() - cached.timestamp < ttl) {
        return cached.data;
    }
    const data = await fetch(url).then(r => r.json());
    apiCache.set(url, { data, timestamp: Date.now() });
    return data;
}

// 4. Bundle Optimization
// vite.config.js
export default {
    build: {
        rollupOptions: {
            output: {
                manualChunks: {
                    vendor: ['svelte', '@sveltejs/kit'],
                    ui: ['@smui/button', '@smui/textfield'],
                    calendar: ['./src/lib/calendar/']
                }
            }
        }
    }
}
```

## 📊 MONITORING & METRICS IMPLEMENTATION

### Performance Monitoring Stack
```yaml
Metrics Collection:
  Application Metrics:
    - Prometheus client in FastAPI
    - Custom business metrics (task completion rate, calendar sync success)
    - Response time histograms per endpoint
    - Database query performance
    
  Infrastructure Metrics:
    - Node exporter for system metrics
    - PostgreSQL exporter for database metrics
    - Redis exporter for cache performance
    - Caddy metrics for proxy performance
    
  Frontend Metrics:
    - Core Web Vitals (LCP, FID, CLS)
    - Time to Interactive (TTI)
    - Bundle size monitoring
    - Error rate tracking
```

### Real-time Performance Dashboards
```yaml
Grafana Dashboards:
  API Performance:
    - Request rate, response time, error rate (RED metrics)
    - P50, P95, P99 latency percentiles
    - Database connection pool usage
    - Cache hit/miss ratios
    
  User Experience:
    - Page load times by route
    - API call success rates
    - Frontend error boundaries triggered
    - Session duration and engagement
    
  System Health:
    - Container resource usage
    - Database performance metrics
    - Queue depth and processing times
    - SSL certificate status
```

### Alerting Rules
```yaml
Critical Performance Alerts:
  - API response time P95 > 1000ms for 5 minutes
  - Database query time P95 > 500ms for 3 minutes
  - Error rate > 5% for any endpoint for 2 minutes
  - Memory usage > 85% for any container for 10 minutes
  - Queue depth > 100 items for 15 minutes
  - Cache hit rate < 70% for 10 minutes
  
Warning Alerts:
  - API response time P95 > 500ms for 10 minutes
  - CPU usage > 70% for any container for 15 minutes
  - Database connection pool > 80% for 5 minutes
  - Frontend bundle size increase > 20%
```

## ⚡ IMMEDIATE PERFORMANCE ACTIONS

### Phase 5 Implementation Tasks
```python
# 1. Database Index Creation
async def create_performance_indexes():
    indexes = [
        "CREATE INDEX CONCURRENTLY idx_tasks_user_status ON tasks(user_id, status)",
        "CREATE INDEX CONCURRENTLY idx_events_user_date ON calendar_events(user_id, event_date)",
        "CREATE INDEX CONCURRENTLY idx_sessions_token ON user_sessions(session_token)",
    ]
    for index in indexes:
        await database.execute(index)

# 2. Redis Caching Implementation
from redis import Redis
redis_client = Redis(host='redis', port=6379, decode_responses=True)

async def cache_user_profile(user_id: int, profile: dict):
    await redis_client.setex(f"profile:{user_id}", 3600, json.dumps(profile))

# 3. Query Optimization
async def get_user_dashboard_data(user_id: int):
    # Single query instead of multiple
    query = text("""
        SELECT 
            (SELECT COUNT(*) FROM tasks WHERE user_id = :user_id AND status = 'pending') as pending_tasks,
            (SELECT COUNT(*) FROM calendar_events WHERE user_id = :user_id AND event_date >= CURRENT_DATE) as upcoming_events,
            (SELECT COUNT(*) FROM notifications WHERE user_id = :user_id AND read_at IS NULL) as unread_notifications
    """)
    return await database.fetch_one(query, {"user_id": user_id})
```

### Performance Testing Strategy
```bash
# Load Testing with wrk
wrk -t12 -c400 -d30s --latency https://aiwfe.com/api/health
wrk -t8 -c200 -d60s --script=load_test.lua https://aiwfe.com/api/calendar/events

# Database Performance Testing
pgbench -c 10 -j 2 -T 60 -S aiwfe_db

# Frontend Performance Testing  
lighthouse https://aiwfe.com --chrome-flags="--headless" --output=json
```

### Success Metrics for Step 6 Validation
```yaml
Performance Targets:
  API Response Times:
    - P95 latency < 500ms for all endpoints
    - P99 latency < 1000ms for all endpoints
    - Error rate < 0.1%
    
  Database Performance:
    - Query time P95 < 100ms
    - Connection pool usage < 70%
    - No missing indexes on frequent queries
    
  Frontend Performance:
    - Core Web Vitals: All "Good" ratings
    - Time to Interactive < 3 seconds
    - Bundle size < 500KB gzipped
    
  System Resource Usage:
    - CPU usage < 50% average per container
    - Memory usage < 70% average per container
    - Database storage I/O < 100 IOPS average
```

### Critical Files for Performance Optimization
- `app/api/dependencies/database.py`: Connection pooling, query optimization
- `app/api/middleware/performance.py`: Response compression, caching headers
- `app/worker/tasks/`: Background task optimization
- `monitoring/prometheus/`: Metrics collection configuration
- `monitoring/grafana/`: Performance dashboards
- `load_tests/`: Performance testing scripts

**CRITICAL**: All performance optimizations require load testing validation with concrete metrics (response times, throughput, resource usage) demonstrating improvement before Step 6 approval.