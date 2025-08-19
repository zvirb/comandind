#!/usr/bin/env python3
"""
Test script for MCP servers
Verifies that both Memory and Redis MCP servers are functioning correctly
"""

import requests
import json
import time
from datetime import datetime

# Server endpoints
REDIS_MCP_URL = "http://localhost:8001"
MEMORY_MCP_URL = "http://localhost:8002"

def test_health(name, url):
    """Test server health endpoint"""
    try:
        response = requests.get(f"{url}/health")
        if response.status_code == 200:
            print(f"✅ {name} health check: PASSED")
            return True
        else:
            print(f"❌ {name} health check: FAILED (status {response.status_code})")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ {name} health check: FAILED (connection error)")
        return False

def test_memory_mcp():
    """Test Memory MCP operations"""
    print("\n📝 Testing Memory MCP Server...")
    
    # Create an entity
    entity_data = {
        "name": "test-agent-output-" + datetime.now().strftime("%Y%m%d-%H%M%S"),
        "entityType": "agent-output",
        "observations": [
            "This is a test observation",
            "Successfully stored in Memory MCP",
            "Ready for workflow orchestration"
        ],
        "metadata": {
            "test": True,
            "timestamp": datetime.now().isoformat()
        }
    }
    
    try:
        # Create entity
        response = requests.post(
            f"{MEMORY_MCP_URL}/mcp/memory/create_entities",
            json=[entity_data]
        )
        if response.status_code == 200:
            result = response.json()
            entity_id = result["entities"][0]["entity_id"]
            print(f"✅ Entity creation: PASSED (ID: {entity_id})")
            
            # Search for entity
            search_data = {
                "query": "test observation",
                "entityType": "agent-output"
            }
            response = requests.post(
                f"{MEMORY_MCP_URL}/mcp/memory/search_nodes",
                json=search_data
            )
            if response.status_code == 200:
                results = response.json()
                if results["count"] > 0:
                    print(f"✅ Entity search: PASSED (found {results['count']} results)")
                else:
                    print("⚠️  Entity search: No results found")
            
            # Get statistics
            response = requests.get(f"{MEMORY_MCP_URL}/mcp/memory/stats")
            if response.status_code == 200:
                stats = response.json()
                print(f"✅ Memory stats: {stats['entities']} entities, {stats['storage_size_mb']} MB")
            
            return True
        else:
            print(f"❌ Entity creation: FAILED (status {response.status_code})")
            return False
            
    except Exception as e:
        print(f"❌ Memory MCP test failed: {e}")
        return False

def test_redis_mcp():
    """Test Redis MCP operations"""
    print("\n🔴 Testing Redis MCP Server...")
    
    try:
        # Test hash operations
        hash_data = {
            "key": "test:workspace",
            "field": "status",
            "value": "testing"
        }
        response = requests.post(f"{REDIS_MCP_URL}/mcp/redis/hset", json=hash_data)
        if response.status_code == 200:
            print("✅ Redis HSET: PASSED")
        else:
            print(f"❌ Redis HSET: FAILED (status {response.status_code})")
            return False
        
        # Get hash value
        get_data = {
            "key": "test:workspace",
            "field": "status"
        }
        response = requests.post(f"{REDIS_MCP_URL}/mcp/redis/hget", json=get_data)
        if response.status_code == 200:
            result = response.json()
            if result["value"] == "testing":
                print("✅ Redis HGET: PASSED")
            else:
                print(f"⚠️  Redis HGET: Unexpected value {result['value']}")
        
        # Test set operations
        set_data = {
            "key": "test:notifications",
            "members": ["agent1", "agent2", "agent3"]
        }
        response = requests.post(f"{REDIS_MCP_URL}/mcp/redis/sadd", json=set_data)
        if response.status_code == 200:
            print("✅ Redis SADD: PASSED")
        
        # Get set members
        members_data = {"key": "test:notifications"}
        response = requests.post(f"{REDIS_MCP_URL}/mcp/redis/smembers", json=members_data)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Redis SMEMBERS: PASSED ({len(result['members'])} members)")
        
        # Test sorted set operations
        zset_data = {
            "key": "test:timeline",
            "members": {
                "event1": 1.0,
                "event2": 2.0,
                "event3": 3.0
            }
        }
        response = requests.post(f"{REDIS_MCP_URL}/mcp/redis/zadd", json=zset_data)
        if response.status_code == 200:
            print("✅ Redis ZADD: PASSED")
        
        # Get sorted set range
        range_data = {
            "key": "test:timeline",
            "start": 0,
            "stop": -1,
            "withscores": True
        }
        response = requests.post(f"{REDIS_MCP_URL}/mcp/redis/zrange", json=range_data)
        if response.status_code == 200:
            print("✅ Redis ZRANGE: PASSED")
        
        return True
        
    except Exception as e:
        print(f"❌ Redis MCP test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 MCP Server Test Suite")
    print("=" * 50)
    
    # Test health endpoints
    redis_health = test_health("Redis MCP", REDIS_MCP_URL)
    memory_health = test_health("Memory MCP", MEMORY_MCP_URL)
    
    if not (redis_health and memory_health):
        print("\n⚠️  Some servers are not running. Please start them first with:")
        print("   ./start_simple.sh")
        return
    
    # Test functionality
    memory_ok = test_memory_mcp()
    redis_ok = test_redis_mcp()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    if memory_ok and redis_ok:
        print("✅ All tests PASSED! MCP servers are ready for orchestration.")
    else:
        print("❌ Some tests failed. Please check the logs.")
    
    # Show API documentation links
    print("\n📚 API Documentation:")
    print(f"   Redis MCP:  {REDIS_MCP_URL}/docs")
    print(f"   Memory MCP: {MEMORY_MCP_URL}/docs")

if __name__ == "__main__":
    main()