#!/usr/bin/env python3
"""
Redis MCP Server Implementation
Provides MCP interface for Redis operations
"""

import json
import logging
from typing import Any, Dict, List, Optional
import redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Redis MCP Server", version="1.0.0")

# Redis connection configuration
REDIS_CONFIG = {
    "host": "localhost",
    "port": 6379,
    "db": 0,
    "decode_responses": True,
    # "password": "your_redis_password_here"  # Uncomment if using authentication
}

# Initialize Redis client
try:
    redis_client = redis.Redis(**REDIS_CONFIG)
    redis_client.ping()
    logger.info("Redis connection established")
except redis.ConnectionError as e:
    logger.error(f"Failed to connect to Redis: {e}")
    redis_client = None


# Pydantic models for request/response
class HashSetRequest(BaseModel):
    key: str
    field: str
    value: str


class HashGetRequest(BaseModel):
    key: str
    field: Optional[str] = None


class SetAddRequest(BaseModel):
    key: str
    members: List[str]


class SetMembersRequest(BaseModel):
    key: str


class SortedSetAddRequest(BaseModel):
    key: str
    members: Dict[str, float]  # {member: score}


class SortedSetRangeRequest(BaseModel):
    key: str
    start: int = 0
    stop: int = -1
    withscores: bool = False


# Health check endpoint
@app.get("/health")
async def health_check():
    """Check Redis connectivity"""
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Redis not connected")
    try:
        redis_client.ping()
        return {"status": "healthy", "service": "redis_mcp"}
    except redis.ConnectionError:
        raise HTTPException(status_code=503, detail="Redis connection lost")


# Hash operations
@app.post("/mcp/redis/hset")
async def mcp_redis_hset(request: HashSetRequest):
    """Set hash field value"""
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Redis not connected")
    try:
        result = redis_client.hset(request.key, request.field, request.value)
        return {"success": True, "created": bool(result)}
    except Exception as e:
        logger.error(f"HSET error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mcp/redis/hget")
async def mcp_redis_hget(request: HashGetRequest):
    """Get hash field value"""
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Redis not connected")
    try:
        if request.field:
            result = redis_client.hget(request.key, request.field)
        else:
            result = redis_client.hgetall(request.key)
        return {"success": True, "value": result}
    except Exception as e:
        logger.error(f"HGET error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mcp/redis/hgetall")
async def mcp_redis_hgetall(key: str):
    """Get all hash fields and values"""
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Redis not connected")
    try:
        result = redis_client.hgetall(key)
        return {"success": True, "value": result}
    except Exception as e:
        logger.error(f"HGETALL error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Set operations
@app.post("/mcp/redis/sadd")
async def mcp_redis_sadd(request: SetAddRequest):
    """Add members to set"""
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Redis not connected")
    try:
        result = redis_client.sadd(request.key, *request.members)
        return {"success": True, "added": result}
    except Exception as e:
        logger.error(f"SADD error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mcp/redis/smembers")
async def mcp_redis_smembers(request: SetMembersRequest):
    """Get all set members"""
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Redis not connected")
    try:
        result = redis_client.smembers(request.key)
        return {"success": True, "members": list(result)}
    except Exception as e:
        logger.error(f"SMEMBERS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Sorted set operations
@app.post("/mcp/redis/zadd")
async def mcp_redis_zadd(request: SortedSetAddRequest):
    """Add members to sorted set with scores"""
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Redis not connected")
    try:
        mapping = {member: score for member, score in request.members.items()}
        result = redis_client.zadd(request.key, mapping)
        return {"success": True, "added": result}
    except Exception as e:
        logger.error(f"ZADD error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mcp/redis/zrange")
async def mcp_redis_zrange(request: SortedSetRangeRequest):
    """Get sorted set members by range"""
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Redis not connected")
    try:
        result = redis_client.zrange(
            request.key,
            request.start,
            request.stop,
            withscores=request.withscores
        )
        return {"success": True, "members": result}
    except Exception as e:
        logger.error(f"ZRANGE error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Utility operations
@app.delete("/mcp/redis/del/{key}")
async def mcp_redis_delete(key: str):
    """Delete a key"""
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Redis not connected")
    try:
        result = redis_client.delete(key)
        return {"success": True, "deleted": bool(result)}
    except Exception as e:
        logger.error(f"DELETE error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mcp/redis/exists/{key}")
async def mcp_redis_exists(key: str):
    """Check if key exists"""
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Redis not connected")
    try:
        result = redis_client.exists(key)
        return {"success": True, "exists": bool(result)}
    except Exception as e:
        logger.error(f"EXISTS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mcp/redis/keys/{pattern}")
async def mcp_redis_keys(pattern: str = "*"):
    """Get keys matching pattern"""
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Redis not connected")
    try:
        result = redis_client.keys(pattern)
        return {"success": True, "keys": result}
    except Exception as e:
        logger.error(f"KEYS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)