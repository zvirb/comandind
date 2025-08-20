#!/usr/bin/env python3
"""
PyTest-based MCP Server Test Suite
Advanced testing with fixtures, parameterization, and detailed reporting
"""

import pytest
import requests
import json
import time
import threading
from datetime import datetime
from typing import Dict, List, Any, Generator
from unittest.mock import patch, MagicMock

# Configuration
SERVER_URL = "http://localhost:8000"
REQUEST_TIMEOUT = 10

# Test data tracking for cleanup
@pytest.fixture(scope="session")
def test_data_tracker():
    """Track test data for cleanup"""
    tracker = {
        "entities": [],
        "redis_keys": []
    }
    yield tracker
    
    # Cleanup after all tests
    cleanup_test_data(tracker)

def cleanup_test_data(tracker: Dict[str, List[str]]):
    """Clean up test data"""
    print("\n🧹 Cleaning up test data...")
    
    # Clean memory entities
    for entity_id in tracker["entities"]:
        try:
            requests.post(f"{SERVER_URL}/mcp/memory/delete_entity", 
                         json={"entity_id": entity_id}, timeout=5)
        except:
            pass
    
    # Clean Redis keys
    for key in tracker["redis_keys"]:
        try:
            requests.post(f"{SERVER_URL}/mcp/redis/delete", 
                         json={"key": key}, timeout=5)
        except:
            pass

@pytest.fixture(scope="session")
def server_health():
    """Ensure server is healthy before running tests"""
    response = requests.get(f"{SERVER_URL}/health", timeout=10)
    assert response.status_code == 200, "Server is not healthy"
    return response.json()

class TestServerHealth:
    """Test server health and basic connectivity"""
    
    def test_health_endpoint_accessibility(self):
        """Test that health endpoint is accessible"""
        response = requests.get(f"{SERVER_URL}/health", timeout=REQUEST_TIMEOUT)
        assert response.status_code == 200
    
    def test_health_response_structure(self, server_health):
        """Test health response has required structure"""
        assert "memory_entities" in server_health
        assert "redis_keys" in server_health
        assert isinstance(server_health["memory_entities"], int)
        assert isinstance(server_health["redis_keys"], int)
    
    def test_health_response_values(self, server_health):
        """Test health response has reasonable values"""
        assert server_health["memory_entities"] >= 0
        assert server_health["redis_keys"] >= 0
    
    def test_health_endpoint_response_time(self):
        """Test health endpoint responds quickly"""
        start_time = time.time()
        response = requests.get(f"{SERVER_URL}/health", timeout=REQUEST_TIMEOUT)
        response_time = time.time() - start_time
        
        assert response.status_code == 200
        assert response_time < 1.0, f"Health endpoint too slow: {response_time:.3f}s"

class TestMemoryOperations:
    """Test Memory MCP operations"""
    
    @pytest.fixture
    def unique_id(self):
        """Generate unique ID for test data"""
        return datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    
    @pytest.fixture
    def test_entity(self, unique_id):
        """Create test entity data"""
        return {
            "name": f"test-entity-{unique_id}",
            "entityType": "test",
            "observations": [
                f"Test observation 1 - {unique_id}",
                f"Test observation 2 - {unique_id}",
                f"Test observation 3 - {unique_id}"
            ]
        }
    
    def test_entity_creation_success(self, test_entity, test_data_tracker):
        """Test successful entity creation"""
        response = requests.post(f"{SERVER_URL}/mcp/memory/create_entities", 
                               json=[test_entity], timeout=REQUEST_TIMEOUT)
        
        assert response.status_code == 200
        result = response.json()
        
        assert "entities" in result
        assert len(result["entities"]) == 1
        assert "entity_id" in result["entities"][0]
        
        entity_id = result["entities"][0]["entity_id"]
        test_data_tracker["entities"].append(entity_id)
        
        assert isinstance(entity_id, str)
        assert len(entity_id) > 0
    
    def test_entity_search_functionality(self, test_entity, test_data_tracker, unique_id):
        """Test entity search finds created entities"""
        # Create entity
        response = requests.post(f"{SERVER_URL}/mcp/memory/create_entities", 
                               json=[test_entity], timeout=REQUEST_TIMEOUT)
        assert response.status_code == 200
        
        result = response.json()
        entity_id = result["entities"][0]["entity_id"]
        test_data_tracker["entities"].append(entity_id)
        
        # Search for entity
        search_query = f"Test observation 1 - {unique_id}"
        search = {"query": search_query, "limit": 5}
        
        response = requests.post(f"{SERVER_URL}/mcp/memory/search_nodes", 
                               json=search, timeout=REQUEST_TIMEOUT)
        
        assert response.status_code == 200
        results = response.json()
        
        assert "count" in results
        assert "nodes" in results
        assert isinstance(results["count"], int)
        assert isinstance(results["nodes"], list)
        assert results["count"] > 0
        
        # Verify our entity is in results
        found = any(node.get("entity_id") == entity_id for node in results["nodes"])
        assert found, "Created entity not found in search results"
    
    @pytest.mark.parametrize("invalid_entity", [
        {},  # Empty entity
        {"name": "test"},  # Missing required fields
        {"entityType": "test"},  # Missing name
        {"observations": ["test"]},  # Missing name and type
    ])
    def test_entity_creation_validation(self, invalid_entity):
        """Test entity creation rejects invalid data"""
        response = requests.post(f"{SERVER_URL}/mcp/memory/create_entities", 
                               json=[invalid_entity], timeout=REQUEST_TIMEOUT)
        
        # Should reject with 400 or 422
        assert response.status_code in [400, 422]
    
    @pytest.mark.parametrize("search_params", [
        {"query": "", "limit": 5},  # Empty query
        {"query": "test", "limit": 0},  # Zero limit
        {"query": "test", "limit": -1},  # Negative limit
        {"query": "test", "limit": 10000},  # Very large limit
    ])
    def test_search_edge_cases(self, search_params):
        """Test search handles edge cases gracefully"""
        response = requests.post(f"{SERVER_URL}/mcp/memory/search_nodes", 
                               json=search_params, timeout=REQUEST_TIMEOUT)
        
        # Should either succeed or reject appropriately
        if response.status_code == 200:
            result = response.json()
            assert "count" in result
            assert "nodes" in result
        else:
            assert response.status_code in [400, 422]

class TestRedisOperations:
    """Test Redis MCP operations"""
    
    @pytest.fixture
    def unique_id(self):
        """Generate unique ID for test data"""
        return datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    
    def test_hash_operations(self, unique_id, test_data_tracker):
        """Test Redis hash operations"""
        key = f"test:hash:{unique_id}"
        test_data_tracker["redis_keys"].append(key)
        
        # Test HSET
        hash_req = {
            "key": key,
            "field": "field1",
            "value": f"value1_{unique_id}"
        }
        
        response = requests.post(f"{SERVER_URL}/mcp/redis/hset", 
                               json=hash_req, timeout=REQUEST_TIMEOUT)
        assert response.status_code == 200
        
        # Test HGET
        get_req = {"key": key, "field": "field1"}
        response = requests.post(f"{SERVER_URL}/mcp/redis/hget", 
                               json=get_req, timeout=REQUEST_TIMEOUT)
        
        if response.status_code == 200:
            result = response.json()
            assert result.get("value") == f"value1_{unique_id}"
    
    def test_set_operations(self, unique_id, test_data_tracker):
        """Test Redis set operations"""
        key = f"test:set:{unique_id}"
        test_data_tracker["redis_keys"].append(key)
        
        members = [f"member1_{unique_id}", f"member2_{unique_id}", f"member3_{unique_id}"]
        
        # Test SADD
        set_req = {"key": key, "members": members}
        response = requests.post(f"{SERVER_URL}/mcp/redis/sadd", 
                               json=set_req, timeout=REQUEST_TIMEOUT)
        assert response.status_code == 200
        
        # Test SMEMBERS
        members_req = {"key": key}
        response = requests.post(f"{SERVER_URL}/mcp/redis/smembers", 
                               json=members_req, timeout=REQUEST_TIMEOUT)
        
        if response.status_code == 200:
            result = response.json()
            returned_members = set(result.get("members", []))
            expected_members = set(members)
            assert expected_members.issubset(returned_members)
    
    def test_sorted_set_operations(self, unique_id, test_data_tracker):
        """Test Redis sorted set operations"""
        key = f"test:zset:{unique_id}"
        test_data_tracker["redis_keys"].append(key)
        
        # Test ZADD
        zset_req = {
            "key": key,
            "members": {
                f"item1_{unique_id}": 1.0,
                f"item2_{unique_id}": 2.0,
                f"item3_{unique_id}": 3.0
            }
        }
        
        response = requests.post(f"{SERVER_URL}/mcp/redis/zadd", 
                               json=zset_req, timeout=REQUEST_TIMEOUT)
        assert response.status_code == 200
        
        # Test ZRANGE
        range_req = {"key": key, "start": 0, "stop": -1}
        response = requests.post(f"{SERVER_URL}/mcp/redis/zrange", 
                               json=range_req, timeout=REQUEST_TIMEOUT)
        
        if response.status_code == 200:
            result = response.json()
            members = result.get("members", [])
            assert len(members) >= 3

class TestStatusEndpoint:
    """Test status endpoint functionality"""
    
    def test_status_endpoint_accessibility(self):
        """Test status endpoint is accessible"""
        response = requests.get(f"{SERVER_URL}/status", timeout=REQUEST_TIMEOUT)
        assert response.status_code == 200
    
    def test_status_response_structure(self):
        """Test status response has required structure"""
        response = requests.get(f"{SERVER_URL}/status", timeout=REQUEST_TIMEOUT)
        assert response.status_code == 200
        
        status = response.json()
        
        # Top-level fields
        assert "status" in status
        assert "memory_mcp" in status
        assert "redis_mcp" in status
        
        # Memory MCP structure
        assert "entities" in status["memory_mcp"]
        assert isinstance(status["memory_mcp"]["entities"], int)
        
        # Redis MCP structure
        redis_fields = ["hash_keys", "set_keys", "sorted_set_keys"]
        for field in redis_fields:
            assert field in status["redis_mcp"]
            assert isinstance(status["redis_mcp"][field], int)

class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_nonexistent_endpoint(self):
        """Test accessing non-existent endpoint"""
        response = requests.get(f"{SERVER_URL}/nonexistent", timeout=REQUEST_TIMEOUT)
        assert response.status_code == 404
    
    def test_malformed_json(self):
        """Test sending malformed JSON"""
        headers = {'Content-Type': 'application/json'}
        
        with pytest.raises(Exception):  # Should fail to send invalid JSON
            requests.post(f"{SERVER_URL}/mcp/memory/create_entities", 
                         data="invalid json", headers=headers, timeout=REQUEST_TIMEOUT)
    
    def test_missing_content_type(self):
        """Test sending JSON without proper content type"""
        response = requests.post(f"{SERVER_URL}/mcp/memory/create_entities", 
                               data='{"test": "data"}', timeout=REQUEST_TIMEOUT)
        
        # Server should handle this gracefully
        assert response.status_code in [200, 400, 415, 422]
    
    @pytest.mark.parametrize("method", ["PUT", "DELETE", "PATCH"])
    def test_unsupported_methods(self, method):
        """Test unsupported HTTP methods"""
        response = requests.request(method, f"{SERVER_URL}/health", timeout=REQUEST_TIMEOUT)
        assert response.status_code in [405, 501]  # Method not allowed or not implemented

class TestPerformance:
    """Test performance characteristics"""
    
    def test_response_time_health(self):
        """Test health endpoint response time"""
        times = []
        for _ in range(5):
            start = time.time()
            response = requests.get(f"{SERVER_URL}/health", timeout=REQUEST_TIMEOUT)
            end = time.time()
            
            assert response.status_code == 200
            times.append(end - start)
        
        avg_time = sum(times) / len(times)
        assert avg_time < 0.5, f"Average response time too slow: {avg_time:.3f}s"
    
    def test_concurrent_requests(self):
        """Test handling concurrent requests"""
        def make_request():
            return requests.get(f"{SERVER_URL}/health", timeout=REQUEST_TIMEOUT)
        
        # Start 5 concurrent requests
        threads = []
        results = []
        
        def worker():
            result = make_request()
            results.append(result)
        
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # All should succeed
        assert len(results) == 5
        for result in results:
            assert result.status_code == 200
    
    @pytest.mark.slow
    def test_load_handling(self):
        """Test server under moderate load"""
        success_count = 0
        total_requests = 20
        
        def make_requests():
            nonlocal success_count
            for _ in range(5):
                try:
                    response = requests.get(f"{SERVER_URL}/health", timeout=REQUEST_TIMEOUT)
                    if response.status_code == 200:
                        success_count += 1
                except:
                    pass
        
        # Start 4 threads, each making 5 requests
        threads = []
        for _ in range(4):
            thread = threading.Thread(target=make_requests)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # At least 80% should succeed
        success_rate = (success_count / total_requests) * 100
        assert success_rate >= 80, f"Success rate too low: {success_rate:.1f}%"

# Custom markers for different test types
def pytest_configure(config):
    """Configure custom pytest markers"""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")

if __name__ == "__main__":
    # Run tests with coverage if executed directly
    pytest.main([__file__, "-v", "--cov=.", "--cov-report=html", "--cov-report=term"])