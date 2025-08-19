#!/usr/bin/env python3
"""
Integrated MCP Server - Combines Memory and Redis functionality
Simplified implementation for AI Workflow Orchestration
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import hashlib
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Storage paths
STORAGE_PATH = Path("./storage")
ENTITIES_PATH = STORAGE_PATH / "entities"
KNOWLEDGE_GRAPH_PATH = STORAGE_PATH / "knowledge_graph"
INDEX_PATH = STORAGE_PATH / "index.json"

# Create storage directories
ENTITIES_PATH.mkdir(parents=True, exist_ok=True)
KNOWLEDGE_GRAPH_PATH.mkdir(parents=True, exist_ok=True)

# In-memory Redis alternative storage
redis_storage: Dict[str, Any] = {}
redis_sets: Dict[str, Set[str]] = {}
redis_sorted_sets: Dict[str, Dict[str, float]] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Integrated MCP Server...")
    yield
    # Shutdown
    logger.info("Shutting down Integrated MCP Server...")

app = FastAPI(
    title="Integrated MCP Server",
    version="1.0.0",
    description="Combined Memory and Redis MCP functionality",
    lifespan=lifespan
)

# ============ Pydantic Models ============

class Entity(BaseModel):
    name: str
    entityType: str
    observations: List[str]
    metadata: Optional[Dict[str, Any]] = {}

class SearchQuery(BaseModel):
    query: str
    entityType: Optional[str] = None
    limit: int = 10

class HashSetRequest(BaseModel):
    key: str
    field: str
    value: str

class SetAddRequest(BaseModel):
    key: str
    members: List[str]

class SortedSetAddRequest(BaseModel):
    key: str
    members: Dict[str, float]

# ============ Memory MCP Functions ============

def generate_entity_id(name: str) -> str:
    """Generate unique entity ID"""
    timestamp = datetime.utcnow().isoformat()
    hash_input = f"{name}_{timestamp}"
    return hashlib.md5(hash_input.encode()).hexdigest()[:12]

def save_entity(entity_id: str, entity: Dict) -> bool:
    """Save entity to storage"""
    try:
        entity_file = ENTITIES_PATH / f"{entity_id}.json"
        with open(entity_file, 'w') as f:
            json.dump(entity, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save entity: {e}")
        return False

def load_entity(entity_id: str) -> Optional[Dict]:
    """Load entity from storage"""
    try:
        entity_file = ENTITIES_PATH / f"{entity_id}.json"
        if entity_file.exists():
            with open(entity_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load entity: {e}")
    return None

def search_entities(query: str, entity_type: Optional[str] = None, limit: int = 10) -> List[Dict]:
    """Simple search implementation"""
    results = []
    for entity_file in ENTITIES_PATH.glob("*.json"):
        try:
            with open(entity_file, 'r') as f:
                entity = json.load(f)
                # Check type match
                if entity_type and entity.get("entityType") != entity_type:
                    continue
                # Check query match in name or observations
                if query.lower() in entity.get("name", "").lower():
                    results.append({
                        "entity_id": entity_file.stem,
                        "name": entity["name"],
                        "type": entity["entityType"],
                        "observations": entity["observations"][:3]
                    })
                    if len(results) >= limit:
                        break
                else:
                    # Check in observations
                    for obs in entity.get("observations", []):
                        if query.lower() in obs.lower():
                            results.append({
                                "entity_id": entity_file.stem,
                                "name": entity["name"],
                                "type": entity["entityType"],
                                "observations": entity["observations"][:3]
                            })
                            break
                    if len(results) >= limit:
                        break
        except Exception as e:
            logger.error(f"Error searching entity {entity_file}: {e}")
    return results

# ============ API Endpoints ============

@app.get("/health")
async def health_check():
    """Combined health check"""
    entity_count = len(list(ENTITIES_PATH.glob("*.json")))
    return {
        "status": "healthy",
        "service": "integrated_mcp",
        "memory_entities": entity_count,
        "redis_keys": len(redis_storage)
    }

# ============ Memory MCP Endpoints ============

@app.post("/mcp/memory/create_entities")
async def create_entities(entities: List[Entity]):
    """Create one or more entities"""
    results = []
    for entity in entities:
        entity_dict = entity.dict()
        entity_dict["created_at"] = datetime.utcnow().isoformat()
        entity_dict["updated_at"] = entity_dict["created_at"]
        
        entity_id = generate_entity_id(entity.name)
        success = save_entity(entity_id, entity_dict)
        
        results.append({
            "entity_id": entity_id,
            "name": entity.name,
            "success": success
        })
    
    return {
        "success": all(r["success"] for r in results),
        "entities": results
    }

@app.post("/mcp/memory/search_nodes")
async def search_nodes(search: SearchQuery):
    """Search for entities"""
    results = search_entities(search.query, search.entityType, search.limit)
    return {
        "success": True,
        "query": search.query,
        "results": results,
        "count": len(results)
    }

@app.get("/mcp/memory/get_entity/{entity_id}")
async def get_entity(entity_id: str):
    """Get specific entity by ID"""
    entity = load_entity(entity_id)
    if entity:
        return {"success": True, "entity": entity}
    raise HTTPException(status_code=404, detail="Entity not found")

@app.get("/mcp/memory/stats")
async def memory_stats():
    """Get memory storage statistics"""
    entity_count = len(list(ENTITIES_PATH.glob("*.json")))
    total_size = sum(f.stat().st_size for f in STORAGE_PATH.rglob("*.json"))
    
    return {
        "entities": entity_count,
        "storage_size_bytes": total_size,
        "storage_size_mb": round(total_size / (1024 * 1024), 2)
    }

# ============ Redis MCP Endpoints ============

@app.post("/mcp/redis/hset")
async def redis_hset(request: HashSetRequest):
    """Set hash field value"""
    if request.key not in redis_storage:
        redis_storage[request.key] = {}
    redis_storage[request.key][request.field] = request.value
    return {"success": True}

@app.post("/mcp/redis/hget")
async def redis_hget(key: str, field: Optional[str] = None):
    """Get hash field value or all fields"""
    if key in redis_storage and isinstance(redis_storage[key], dict):
        if field:
            return {"success": True, "value": redis_storage[key].get(field)}
        else:
            return {"success": True, "value": redis_storage[key]}
    return {"success": True, "value": None}

@app.post("/mcp/redis/hgetall")
async def redis_hgetall(key: str):
    """Get all hash fields and values"""
    if key in redis_storage and isinstance(redis_storage[key], dict):
        return {"success": True, "value": redis_storage[key]}
    return {"success": True, "value": {}}

@app.post("/mcp/redis/sadd")
async def redis_sadd(request: SetAddRequest):
    """Add members to set"""
    if request.key not in redis_sets:
        redis_sets[request.key] = set()
    redis_sets[request.key].update(request.members)
    return {"success": True, "added": len(request.members)}

@app.post("/mcp/redis/smembers")
async def redis_smembers(key: str):
    """Get all set members"""
    members = list(redis_sets.get(key, set()))
    return {"success": True, "members": members}

@app.post("/mcp/redis/zadd")
async def redis_zadd(request: SortedSetAddRequest):
    """Add members to sorted set with scores"""
    if request.key not in redis_sorted_sets:
        redis_sorted_sets[request.key] = {}
    redis_sorted_sets[request.key].update(request.members)
    return {"success": True, "added": len(request.members)}

@app.post("/mcp/redis/zrange")
async def redis_zrange(key: str, start: int = 0, stop: int = -1, withscores: bool = False):
    """Get sorted set members by range"""
    if key not in redis_sorted_sets:
        return {"success": True, "members": []}
    
    # Sort by score
    sorted_items = sorted(redis_sorted_sets[key].items(), key=lambda x: x[1])
    
    # Apply range
    if stop == -1:
        items = sorted_items[start:]
    else:
        items = sorted_items[start:stop+1]
    
    if withscores:
        result = [[item[0], item[1]] for item in items]
    else:
        result = [item[0] for item in items]
    
    return {"success": True, "members": result}

@app.get("/mcp/redis/keys/{pattern}")
async def redis_keys(pattern: str = "*"):
    """Get keys matching pattern"""
    if pattern == "*":
        keys = list(redis_storage.keys()) + list(redis_sets.keys()) + list(redis_sorted_sets.keys())
    else:
        # Simple pattern matching
        keys = []
        pattern_prefix = pattern.replace("*", "")
        for key in list(redis_storage.keys()) + list(redis_sets.keys()) + list(redis_sorted_sets.keys()):
            if pattern_prefix in key:
                keys.append(key)
    return {"success": True, "keys": list(set(keys))}

# ============ Combined Status Endpoint ============

@app.get("/status")
async def get_status():
    """Get complete server status"""
    entity_count = len(list(ENTITIES_PATH.glob("*.json")))
    return {
        "service": "Integrated MCP Server",
        "status": "operational",
        "memory_mcp": {
            "entities": entity_count,
            "storage_path": str(STORAGE_PATH)
        },
        "redis_mcp": {
            "hash_keys": len(redis_storage),
            "set_keys": len(redis_sets),
            "sorted_set_keys": len(redis_sorted_sets)
        },
        "endpoints": {
            "memory": [
                "/mcp/memory/create_entities",
                "/mcp/memory/search_nodes",
                "/mcp/memory/get_entity/{entity_id}",
                "/mcp/memory/stats"
            ],
            "redis": [
                "/mcp/redis/hset",
                "/mcp/redis/hget",
                "/mcp/redis/hgetall",
                "/mcp/redis/sadd",
                "/mcp/redis/smembers",
                "/mcp/redis/zadd",
                "/mcp/redis/zrange",
                "/mcp/redis/keys/{pattern}"
            ]
        }
    }

if __name__ == "__main__":
    print("🚀 Starting Integrated MCP Server on port 8000...")
    print("📊 API Documentation: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)