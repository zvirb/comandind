#!/usr/bin/env python3
"""
Test script for Integrated MCP Server
"""

import requests
import json
from datetime import datetime

# Server endpoint
MCP_URL = "http://localhost:8000"

def test_health():
    """Test server health"""
    try:
        response = requests.get(f"{MCP_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check PASSED")
            print(f"   Memory entities: {data['memory_entities']}")
            print(f"   Redis keys: {data['redis_keys']}")
            return True
    except Exception as e:
        print(f"❌ Health check FAILED: {e}")
    return False

def test_memory_operations():
    """Test Memory MCP operations"""
    print("\n📝 Testing Memory MCP operations...")
    
    # Create entity
    entity = {
        "name": f"test-entity-{datetime.now().strftime('%H%M%S')}",
        "entityType": "test",
        "observations": [
            "Test observation 1",
            "Test observation 2",
            "Test observation 3"
        ]
    }
    
    response = requests.post(f"{MCP_URL}/mcp/memory/create_entities", json=[entity])
    if response.status_code == 200:
        result = response.json()
        entity_id = result["entities"][0]["entity_id"]
        print(f"✅ Entity created: {entity_id}")
        
        # Search for entity
        search = {"query": "Test observation", "limit": 5}
        response = requests.post(f"{MCP_URL}/mcp/memory/search_nodes", json=search)
        if response.status_code == 200:
            results = response.json()
            print(f"✅ Search found {results['count']} results")
        
        return True
    return False

def test_redis_operations():
    """Test Redis MCP operations"""
    print("\n🔴 Testing Redis MCP operations...")
    
    # Test hash operations
    hash_req = {
        "key": "test:hash",
        "field": "field1",
        "value": "value1"
    }
    response = requests.post(f"{MCP_URL}/mcp/redis/hset", json=hash_req)
    if response.status_code == 200:
        print("✅ Hash set successful")
    
    # Test set operations
    set_req = {
        "key": "test:set",
        "members": ["member1", "member2", "member3"]
    }
    response = requests.post(f"{MCP_URL}/mcp/redis/sadd", json=set_req)
    if response.status_code == 200:
        print("✅ Set add successful")
    
    # Test sorted set operations
    zset_req = {
        "key": "test:zset",
        "members": {"item1": 1.0, "item2": 2.0, "item3": 3.0}
    }
    response = requests.post(f"{MCP_URL}/mcp/redis/zadd", json=zset_req)
    if response.status_code == 200:
        print("✅ Sorted set add successful")
    
    return True

def test_status():
    """Test status endpoint"""
    print("\n📊 Server Status:")
    response = requests.get(f"{MCP_URL}/status")
    if response.status_code == 200:
        status = response.json()
        print(f"✅ Status: {status['status']}")
        print(f"   Memory entities: {status['memory_mcp']['entities']}")
        print(f"   Redis hash keys: {status['redis_mcp']['hash_keys']}")
        print(f"   Redis set keys: {status['redis_mcp']['set_keys']}")
        print(f"   Redis sorted set keys: {status['redis_mcp']['sorted_set_keys']}")
        return True
    return False

def main():
    print("🧪 Testing Integrated MCP Server")
    print("=" * 50)
    
    if not test_health():
        print("\n❌ Server not running. Start it with: ./start_integrated_mcp.sh")
        return
    
    test_memory_operations()
    test_redis_operations()
    test_status()
    
    print("\n" + "=" * 50)
    print("✅ All tests completed!")
    print(f"\n📊 API Documentation: {MCP_URL}/docs")

if __name__ == "__main__":
    main()