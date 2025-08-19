#!/usr/bin/env python3
"""
Memory MCP Server Implementation
Provides persistent storage for agent outputs and knowledge graph
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Memory MCP Server", version="1.0.0")

# Storage configuration
STORAGE_PATH = Path("./memory/storage")
ENTITIES_PATH = STORAGE_PATH / "entities"
KNOWLEDGE_GRAPH_PATH = STORAGE_PATH / "knowledge_graph"
INDEX_PATH = STORAGE_PATH / "index.json"
TOKEN_LIMIT = 8000

# Create storage directories
ENTITIES_PATH.mkdir(parents=True, exist_ok=True)
KNOWLEDGE_GRAPH_PATH.mkdir(parents=True, exist_ok=True)


# Pydantic models
class Entity(BaseModel):
    name: str
    entityType: str
    observations: List[str]
    metadata: Optional[Dict[str, Any]] = {}
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class SearchQuery(BaseModel):
    query: str
    entityType: Optional[str] = None
    limit: int = 10


class Relationship(BaseModel):
    source: str
    target: str
    relationship_type: str
    metadata: Optional[Dict[str, Any]] = {}


# Index management
class EntityIndex:
    def __init__(self):
        self.index_file = INDEX_PATH
        self.index = self.load_index()

    def load_index(self) -> Dict:
        """Load or create index"""
        if self.index_file.exists():
            with open(self.index_file, 'r') as f:
                return json.load(f)
        return {
            "entities": {},
            "types": {},
            "keywords": {}
        }

    def save_index(self):
        """Save index to disk"""
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2)

    def add_entity(self, entity_id: str, entity: Entity):
        """Add entity to index"""
        # Add to entities index
        self.index["entities"][entity_id] = {
            "name": entity.name,
            "type": entity.entityType,
            "created_at": entity.created_at
        }
        
        # Add to type index
        if entity.entityType not in self.index["types"]:
            self.index["types"][entity.entityType] = []
        if entity_id not in self.index["types"][entity.entityType]:
            self.index["types"][entity.entityType].append(entity_id)
        
        # Add keywords from observations
        for observation in entity.observations:
            words = observation.lower().split()
            for word in words:
                if len(word) > 3:  # Only index words longer than 3 chars
                    if word not in self.index["keywords"]:
                        self.index["keywords"][word] = []
                    if entity_id not in self.index["keywords"][word]:
                        self.index["keywords"][word].append(entity_id)
        
        self.save_index()

    def search(self, query: str, entity_type: Optional[str] = None) -> List[str]:
        """Search entities by query"""
        results = set()
        
        # Search by type if specified
        if entity_type and entity_type in self.index["types"]:
            results.update(self.index["types"][entity_type])
        
        # Search by keywords
        query_words = query.lower().split()
        for word in query_words:
            if word in self.index["keywords"]:
                if entity_type:
                    # Filter by type if specified
                    type_entities = set(self.index["types"].get(entity_type, []))
                    word_entities = set(self.index["keywords"][word])
                    results.update(type_entities.intersection(word_entities))
                else:
                    results.update(self.index["keywords"][word])
        
        # Search in entity names
        for entity_id, entity_info in self.index["entities"].items():
            if query.lower() in entity_info["name"].lower():
                if not entity_type or entity_info["type"] == entity_type:
                    results.add(entity_id)
        
        return list(results)

    def remove_entity(self, entity_id: str):
        """Remove entity from index"""
        if entity_id in self.index["entities"]:
            entity_info = self.index["entities"][entity_id]
            
            # Remove from entities
            del self.index["entities"][entity_id]
            
            # Remove from types
            entity_type = entity_info["type"]
            if entity_type in self.index["types"]:
                self.index["types"][entity_type].remove(entity_id)
                if not self.index["types"][entity_type]:
                    del self.index["types"][entity_type]
            
            # Remove from keywords
            for word, entities in list(self.index["keywords"].items()):
                if entity_id in entities:
                    entities.remove(entity_id)
                    if not entities:
                        del self.index["keywords"][word]
            
            self.save_index()


# Initialize index
entity_index = EntityIndex()


# Utility functions
def generate_entity_id(name: str) -> str:
    """Generate unique entity ID"""
    timestamp = datetime.utcnow().isoformat()
    hash_input = f"{name}_{timestamp}"
    return hashlib.md5(hash_input.encode()).hexdigest()[:12]


def estimate_tokens(text: str) -> int:
    """Estimate token count (rough approximation)"""
    # Rough estimate: 1 token ≈ 4 characters
    return len(text) // 4


def save_entity(entity_id: str, entity: Entity) -> bool:
    """Save entity to storage"""
    try:
        # Check token limit
        entity_json = entity.json()
        if estimate_tokens(entity_json) > TOKEN_LIMIT:
            raise ValueError(f"Entity exceeds token limit of {TOKEN_LIMIT}")
        
        # Save entity file
        entity_file = ENTITIES_PATH / f"{entity_id}.json"
        with open(entity_file, 'w') as f:
            json.dump(entity.dict(), f, indent=2)
        
        # Update index
        entity_index.add_entity(entity_id, entity)
        
        return True
    except Exception as e:
        logger.error(f"Failed to save entity: {e}")
        return False


def load_entity(entity_id: str) -> Optional[Entity]:
    """Load entity from storage"""
    try:
        entity_file = ENTITIES_PATH / f"{entity_id}.json"
        if entity_file.exists():
            with open(entity_file, 'r') as f:
                data = json.load(f)
                return Entity(**data)
    except Exception as e:
        logger.error(f"Failed to load entity {entity_id}: {e}")
    return None


# API endpoints
@app.get("/health")
async def health_check():
    """Check service health"""
    return {
        "status": "healthy",
        "service": "memory_mcp",
        "storage_path": str(STORAGE_PATH),
        "entity_count": len(entity_index.index["entities"])
    }


@app.post("/mcp/memory/create_entities")
async def mcp_memory_create_entities(entities: List[Entity]):
    """Create one or more entities"""
    results = []
    for entity in entities:
        # Set timestamps
        entity.created_at = datetime.utcnow().isoformat()
        entity.updated_at = entity.created_at
        
        # Generate ID and save
        entity_id = generate_entity_id(entity.name)
        success = save_entity(entity_id, entity)
        
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
async def mcp_memory_search_nodes(search: SearchQuery):
    """Search for entities"""
    try:
        # Search in index
        entity_ids = entity_index.search(search.query, search.entityType)
        
        # Load entities
        entities = []
        for entity_id in entity_ids[:search.limit]:
            entity = load_entity(entity_id)
            if entity:
                entities.append({
                    "entity_id": entity_id,
                    "name": entity.name,
                    "type": entity.entityType,
                    "observations": entity.observations[:3],  # Return first 3 observations
                    "created_at": entity.created_at
                })
        
        return {
            "success": True,
            "query": search.query,
            "results": entities,
            "count": len(entities)
        }
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mcp/memory/get_entity/{entity_id}")
async def mcp_memory_get_entity(entity_id: str):
    """Get specific entity by ID"""
    entity = load_entity(entity_id)
    if entity:
        return {
            "success": True,
            "entity": entity.dict()
        }
    raise HTTPException(status_code=404, detail="Entity not found")


@app.put("/mcp/memory/update_entity/{entity_id}")
async def mcp_memory_update_entity(entity_id: str, entity: Entity):
    """Update existing entity"""
    existing = load_entity(entity_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    # Preserve creation time, update modification time
    entity.created_at = existing.created_at
    entity.updated_at = datetime.utcnow().isoformat()
    
    success = save_entity(entity_id, entity)
    return {
        "success": success,
        "entity_id": entity_id
    }


@app.delete("/mcp/memory/delete_entity/{entity_id}")
async def mcp_memory_delete_entity(entity_id: str):
    """Delete entity"""
    try:
        entity_file = ENTITIES_PATH / f"{entity_id}.json"
        if entity_file.exists():
            entity_file.unlink()
            entity_index.remove_entity(entity_id)
            return {"success": True, "entity_id": entity_id}
        raise HTTPException(status_code=404, detail="Entity not found")
    except Exception as e:
        logger.error(f"Delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Knowledge Graph operations
@app.post("/mcp/memory/create_relationship")
async def mcp_memory_create_relationship(relationship: Relationship):
    """Create relationship between entities"""
    try:
        rel_id = hashlib.md5(
            f"{relationship.source}_{relationship.target}_{relationship.relationship_type}".encode()
        ).hexdigest()[:12]
        
        rel_file = KNOWLEDGE_GRAPH_PATH / f"{rel_id}.json"
        with open(rel_file, 'w') as f:
            json.dump(relationship.dict(), f, indent=2)
        
        return {
            "success": True,
            "relationship_id": rel_id
        }
    except Exception as e:
        logger.error(f"Relationship creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mcp/memory/get_relationships/{entity_id}")
async def mcp_memory_get_relationships(entity_id: str):
    """Get all relationships for an entity"""
    try:
        relationships = []
        for rel_file in KNOWLEDGE_GRAPH_PATH.glob("*.json"):
            with open(rel_file, 'r') as f:
                rel = json.load(f)
                if rel["source"] == entity_id or rel["target"] == entity_id:
                    relationships.append(rel)
        
        return {
            "success": True,
            "entity_id": entity_id,
            "relationships": relationships
        }
    except Exception as e:
        logger.error(f"Relationship query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mcp/memory/stats")
async def mcp_memory_stats():
    """Get memory storage statistics"""
    entity_count = len(list(ENTITIES_PATH.glob("*.json")))
    relationship_count = len(list(KNOWLEDGE_GRAPH_PATH.glob("*.json")))
    
    # Calculate storage size
    total_size = 0
    for file in STORAGE_PATH.rglob("*.json"):
        total_size += file.stat().st_size
    
    return {
        "entities": entity_count,
        "relationships": relationship_count,
        "types": list(entity_index.index["types"].keys()),
        "storage_size_bytes": total_size,
        "storage_size_mb": round(total_size / (1024 * 1024), 2)
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)