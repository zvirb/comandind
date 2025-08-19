#!/usr/bin/env python3
"""Simple in-memory Redis alternative for MCP"""

import json
from typing import Any, Dict, Set
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Redis Alternative", version="1.0.0")

# In-memory storage
storage: Dict[str, Any] = {}
sets: Dict[str, Set[str]] = {}
sorted_sets: Dict[str, Dict[str, float]] = {}

@app.get("/health")
async def health():
    return {"status": "healthy", "type": "redis_alternative"}

@app.post("/set")
async def set_key(key: str, value: str):
    storage[key] = value
    return {"success": True}

@app.get("/get/{key}")
async def get_key(key: str):
    return {"value": storage.get(key)}

@app.post("/hset")
async def hset(key: str, field: str, value: str):
    if key not in storage:
        storage[key] = {}
    storage[key][field] = value
    return {"success": True}

@app.get("/hget/{key}/{field}")
async def hget(key: str, field: str):
    if key in storage and isinstance(storage[key], dict):
        return {"value": storage[key].get(field)}
    return {"value": None}

@app.get("/hgetall/{key}")
async def hgetall(key: str):
    if key in storage and isinstance(storage[key], dict):
        return {"value": storage[key]}
    return {"value": {}}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=6379)
