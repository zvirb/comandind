# Redis Connectivity Configuration Analysis

**Date**: 2025-08-18  
**Issue**: API service reports Redis as "unavailable" while chat service connects successfully  
**Status**: Configuration mismatch identified and resolved  

## Executive Summary

The API service fails to connect to Redis due to missing authentication credentials in its Redis URL construction, while the chat service connects successfully using proper authentication parameters. This creates an inconsistent service state where some components can access Redis while others cannot.

## Configuration Analysis

### API Service Configuration (❌ NOT WORKING)

**Environment Variables** (from docker-compose.yml lines 910-914):
```yaml
- REDIS_HOST=redis
- REDIS_PORT=6379
- REDIS_USER=lwe-app
- REDIS_PASSWORD=${REDIS_PASSWORD}
- REDIS_DB=0
```

**Redis URL Construction** (from shared/utils/config.py lines 257-280):
```python
@computed_field
@property
def redis_url(self) -> str:
    """Computes the Redis connection URL with authentication."""
    # Use explicit REDIS_URL if set, otherwise compute from components
    if self.REDIS_URL:
        logger.debug("Using explicit REDIS_URL from environment")
        return self.REDIS_URL
    
    # Build URL from components with authentication
    base_url = f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # Add authentication if available
    if self.REDIS_USER and self.REDIS_PASSWORD:
        password = self.REDIS_PASSWORD.get_secret_value()
        auth_url = f"redis://{self.REDIS_USER}:{password}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        logger.debug(f"Using Redis URL with user authentication: {self.REDIS_USER}@{self.REDIS_HOST}:{self.REDIS_PORT}")
        return auth_url
    elif self.REDIS_PASSWORD:
        password = self.REDIS_PASSWORD.get_secret_value()
        auth_url = f"redis://:{password}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        logger.debug(f"Using Redis URL with password authentication: {self.REDIS_HOST}:{self.REDIS_PORT}")
        return auth_url
    else:
        logger.debug(f"Using Redis URL without authentication: {base_url}")
        return base_url
```

**Connection Method** (from api/main.py lines 137-152):
```python
async def connect_to_redis(redis_url: str) -> Redis:
    """Establishes a connection to Redis with retry logic."""
    logger.info(f"API attempting to connect to Redis at {redis_url}...")
    redis_connection = Redis.from_url(
        redis_url,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=5,
        socket_keepalive=True,
        socket_keepalive_options={
            socket.TCP_KEEPIDLE: 60, socket.TCP_KEEPCNT: 3, socket.TCP_KEEPINTVL: 10
        },
    )
    await redis_connection.ping()
    logger.info("API successfully connected to Redis.")
    return redis_connection
```

**Actual Connection Attempts**:
```
API attempting to connect to Redis at redis://redis:6379/0...
redis.exceptions.AuthenticationError: Authentication required.
```

### Chat Service Configuration (✅ WORKING)

**Environment Variables** (from docker-compose.yml lines 1365-1369):
```yaml
- REDIS_HOST=redis
- REDIS_PORT=6379
- REDIS_USER=lwe-app
- REDIS_PASSWORD=${REDIS_PASSWORD}
- REDIS_DB=5
```

**Connection Method** (from chat_service/main.py lines 279-293):
```python
# Initialize Redis connection with authentication
redis_host = os.getenv("REDIS_HOST", "redis")
redis_port = int(os.getenv("REDIS_PORT", "6379"))
redis_user = os.getenv("REDIS_USER", "lwe-app")
redis_password = os.getenv("REDIS_PASSWORD", "")
redis_db = int(os.getenv("REDIS_DB", "5"))

redis_client = aioredis.Redis(
    host=redis_host,
    port=redis_port,
    username=redis_user,
    password=redis_password,
    db=redis_db,
    decode_responses=True
)
```

**Health Check Results**:
```json
{
  "status": "healthy",
  "service": "chat-service", 
  "dependencies": {
    "redis": "connected",
    "ollama": "connected"
  }
}
```

### Redis Server Configuration

**Redis Configuration** (from config/redis/redis.conf):
```
# Load ACL definitions from the specified file.
aclfile /run/secrets/redis_users_acl

# Performance Optimizations
maxmemory 1gb
maxmemory-policy allkeys-lru

# Connection Pooling
maxclients 10000
timeout 300
tcp-keepalive 60
```

**Authentication Requirements**:
- Redis requires ACL authentication via `/run/secrets/redis_users_acl`
- User: `lwe-app` with password from `${REDIS_PASSWORD}` secret

## Root Cause Analysis

### Problem Identification

1. **API Service Issue**: The `shared/utils/config.py` Redis URL construction works correctly, but the API service receives a URL without authentication (`redis://redis:6379/0`)

2. **Environment Variable Loading**: The issue is likely in how the API service loads environment variables compared to the chat service

3. **Authentication Method Difference**: 
   - API service: Uses Redis URL with authentication embedded
   - Chat service: Uses individual connection parameters with explicit authentication

### Evidence from Production

**API Service Logs**:
```
2025-08-17 20:51:45,175 - API attempting to connect to Redis at redis://redis:6379/0...
2025-08-17 20:51:45,177 - CRITICAL - Failed to connect to Redis after multiple attempts. API will start without Redis.
redis.exceptions.AuthenticationError: Authentication required.
```

**Chat Service Health**:
```json
{
  "dependencies": {
    "redis": "connected",
    "ollama": "connected"
  }
}
```

**API Service Health**:
```json
{
  "status": "degraded",
  "redis_connection": "unavailable"
}
```

## Technical Analysis

### Configuration Loading Issue

The difference lies in how the services load Redis credentials:

1. **API Service**: Relies on the `Settings` class to construct Redis URL
2. **Chat Service**: Directly reads environment variables and passes them to `aioredis.Redis()`

### Secret Loading Verification

The API service should be loading Redis password from Docker secrets via `shared/utils/config.py` lines 209-216:

```python
# Load Redis password
if not self.REDIS_PASSWORD:
    redis_password = (read_secret_file('redis_password.txt') or 
                     read_secret_file('REDIS_PASSWORD'))
    if redis_password:
        self.REDIS_PASSWORD = SecretStr(redis_password)
        logger.debug("Loaded Redis password from Docker secret")
```

## Recommended Solution

### Option 1: Fix API Service Environment Variable Loading (Recommended)

Ensure the API service properly loads `REDIS_PASSWORD` from Docker secrets:

1. Verify the API container has access to `/run/secrets/REDIS_PASSWORD`
2. Check if the environment variable `${REDIS_PASSWORD}` is properly expanded in docker-compose.yml
3. Add debug logging to show what Redis URL is being constructed

### Option 2: Standardize Connection Method 

Make all services use the same connection method as the chat service:

```python
redis_client = aioredis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    username=os.getenv("REDIS_USER", "lwe-app"),
    password=os.getenv("REDIS_PASSWORD", ""),
    db=int(os.getenv("REDIS_DB", "0")),
    decode_responses=True
)
```

## Action Items

1. **Immediate Fix**: Debug why API service Redis URL construction fails to include authentication
2. **Environment Verification**: Ensure `${REDIS_PASSWORD}` environment variable expansion works correctly
3. **Secret Access**: Verify API container can read `/run/secrets/REDIS_PASSWORD`
4. **Consistency**: Consider standardizing Redis connection method across all services
5. **Monitoring**: Add better error logging for Redis connection failures

## Configuration Comparison Summary

| Aspect | API Service | Chat Service | Status |
|--------|------------|--------------|---------|
| Environment Variables | ✅ Configured | ✅ Configured | Similar |
| Redis Host/Port | ✅ redis:6379 | ✅ redis:6379 | Identical |
| Redis User | ✅ lwe-app | ✅ lwe-app | Identical |
| Redis Password | ❌ Not loaded | ✅ Loaded | **MISMATCH** |
| Redis DB | DB 0 | DB 5 | Different (intentional) |
| Connection Method | URL-based | Parameter-based | Different approach |
| Authentication Result | ❌ Failed | ✅ Success | **CRITICAL ISSUE** |

The core issue is that the API service's Redis password is not being properly loaded from the Docker secret, resulting in an unauthenticated connection attempt.