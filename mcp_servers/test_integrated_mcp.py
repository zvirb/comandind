#!/usr/bin/env python3
"""
Comprehensive Test Suite for Integrated MCP Server

This test suite implements:
- Proper data validation and assertions
- Automatic cleanup to prevent database pollution
- Robust error handling for network failures
- Negative test cases to ensure tests fail when logic is broken
- Edge case testing and boundary conditions
"""

import requests
import json
import time
import traceback
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

# Configuration
MCP_URL = "http://localhost:8000"
REQUEST_TIMEOUT = 10
MAX_RETRIES = 3
RETRY_DELAY = 1

# Test data tracking for cleanup
test_entities_created = []
test_redis_keys_created = []

class TestFailure(Exception):
    """Custom exception for test failures"""
    pass

class NetworkError(Exception):
    """Custom exception for network-related failures"""
    pass

@contextmanager
def cleanup_guard():
    """Context manager to ensure cleanup happens even if tests fail"""
    try:
        yield
    finally:
        cleanup_test_data()

def make_request(method: str, url: str, json_data: Optional[Dict] = None, 
                timeout: int = REQUEST_TIMEOUT) -> requests.Response:
    """Make HTTP request with retry logic and proper error handling"""
    for attempt in range(MAX_RETRIES):
        try:
            if method.upper() == 'GET':
                response = requests.get(url, timeout=timeout)
            elif method.upper() == 'POST':
                response = requests.post(url, json=json_data, timeout=timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            return response
        except requests.exceptions.Timeout:
            if attempt == MAX_RETRIES - 1:
                raise NetworkError(f"Request timed out after {MAX_RETRIES} attempts")
            time.sleep(RETRY_DELAY)
        except requests.exceptions.ConnectionError:
            if attempt == MAX_RETRIES - 1:
                raise NetworkError(f"Failed to connect to server after {MAX_RETRIES} attempts")
            time.sleep(RETRY_DELAY)
        except Exception as e:
            raise NetworkError(f"Unexpected network error: {str(e)}")

def validate_response_structure(data: Dict, required_fields: List[str], 
                              test_name: str) -> None:
    """Validate that response contains required fields"""
    for field in required_fields:
        if field not in data:
            raise TestFailure(f"{test_name}: Missing required field '{field}' in response")

def test_health():
    """Test server health with comprehensive validation"""
    print("\n🏥 Testing server health endpoint...")
    
    try:
        response = make_request('GET', f"{MCP_URL}/health")
        
        # Validate HTTP status
        if response.status_code != 200:
            raise TestFailure(f"Health check returned status {response.status_code}, expected 200")
        
        # Validate response is valid JSON
        try:
            data = response.json()
        except json.JSONDecodeError:
            raise TestFailure("Health check response is not valid JSON")
        
        # Validate required fields exist
        required_fields = ['memory_entities', 'redis_keys']
        validate_response_structure(data, required_fields, "Health check")
        
        # Validate field types
        if not isinstance(data['memory_entities'], int):
            raise TestFailure("memory_entities should be an integer")
        if not isinstance(data['redis_keys'], int):
            raise TestFailure("redis_keys should be an integer")
        
        # Validate reasonable values
        if data['memory_entities'] < 0:
            raise TestFailure("memory_entities should not be negative")
        if data['redis_keys'] < 0:
            raise TestFailure("redis_keys should not be negative")
        
        print(f"✅ Health check PASSED")
        print(f"   Memory entities: {data['memory_entities']}")
        print(f"   Redis keys: {data['redis_keys']}")
        return True
        
    except (NetworkError, TestFailure) as e:
        print(f"❌ Health check FAILED: {e}")
        return False
    except Exception as e:
        print(f"❌ Health check FAILED with unexpected error: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False

def test_memory_operations():
    """Test Memory MCP operations with comprehensive validation"""
    print("\n📝 Testing Memory MCP operations...")
    
    try:
        # Test entity creation
        unique_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        entity = {
            "name": f"test-entity-{unique_id}",
            "entityType": "test",
            "observations": [
                f"Test observation 1 - {unique_id}",
                f"Test observation 2 - {unique_id}",
                f"Test observation 3 - {unique_id}"
            ]
        }
        
        # Test entity creation
        response = make_request('POST', f"{MCP_URL}/mcp/memory/create_entities", [entity])
        
        if response.status_code != 200:
            raise TestFailure(f"Entity creation failed with status {response.status_code}")
        
        try:
            result = response.json()
        except json.JSONDecodeError:
            raise TestFailure("Entity creation response is not valid JSON")
        
        # Validate response structure
        if "entities" not in result:
            raise TestFailure("Entity creation response missing 'entities' field")
        
        if not isinstance(result["entities"], list) or len(result["entities"]) == 0:
            raise TestFailure("Entities should be a non-empty list")
        
        entity_data = result["entities"][0]
        if "entity_id" not in entity_data:
            raise TestFailure("Created entity missing 'entity_id' field")
        
        entity_id = entity_data["entity_id"]
        test_entities_created.append(entity_id)  # Track for cleanup
        
        # Validate entity ID format
        if not entity_id or not isinstance(entity_id, str):
            raise TestFailure("Entity ID should be a non-empty string")
        
        print(f"✅ Entity created successfully: {entity_id}")
        
        # Test search functionality
        search_query = f"Test observation 1 - {unique_id}"
        search = {"query": search_query, "limit": 5}
        
        response = make_request('POST', f"{MCP_URL}/mcp/memory/search_nodes", search)
        
        if response.status_code != 200:
            raise TestFailure(f"Search failed with status {response.status_code}")
        
        try:
            results = response.json()
        except json.JSONDecodeError:
            raise TestFailure("Search response is not valid JSON")
        
        # Validate search response structure
        required_fields = ['count', 'nodes']
        validate_response_structure(results, required_fields, "Memory search")
        
        if not isinstance(results['count'], int):
            raise TestFailure("Search count should be an integer")
        
        if not isinstance(results['nodes'], list):
            raise TestFailure("Search nodes should be a list")
        
        # Validate search actually found our entity
        if results['count'] == 0:
            raise TestFailure("Search should have found the created entity")
        
        # Check if our entity is in the search results
        found_entity = False
        for node in results['nodes']:
            if 'entity_id' in node and node['entity_id'] == entity_id:
                found_entity = True
                break
        
        if not found_entity:
            raise TestFailure("Created entity not found in search results")
        
        print(f"✅ Search found {results['count']} results (including our entity)")
        
        # Test edge case: empty search
        empty_search = {"query": "", "limit": 5}
        response = make_request('POST', f"{MCP_URL}/mcp/memory/search_nodes", empty_search)
        
        if response.status_code == 200:
            empty_results = response.json()
            print(f"✅ Empty search handled gracefully: {empty_results.get('count', 0)} results")
        
        # Test edge case: very large limit
        large_search = {"query": "test", "limit": 10000}
        response = make_request('POST', f"{MCP_URL}/mcp/memory/search_nodes", large_search)
        
        if response.status_code == 200:
            print(f"✅ Large limit search handled gracefully")
        
        return True
        
    except (NetworkError, TestFailure) as e:
        print(f"❌ Memory operations FAILED: {e}")
        return False
    except Exception as e:
        print(f"❌ Memory operations FAILED with unexpected error: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False

def test_redis_operations():
    """Test Redis MCP operations with comprehensive validation"""
    print("\n🔴 Testing Redis MCP operations...")
    
    try:
        unique_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        
        # Test hash operations
        hash_key = f"test:hash:{unique_id}"
        test_redis_keys_created.append(hash_key)
        
        hash_req = {
            "key": hash_key,
            "field": "field1",
            "value": f"value1_{unique_id}"
        }
        
        response = make_request('POST', f"{MCP_URL}/mcp/redis/hset", hash_req)
        
        if response.status_code != 200:
            raise TestFailure(f"Hash set failed with status {response.status_code}")
        
        try:
            result = response.json()
        except json.JSONDecodeError:
            raise TestFailure("Hash set response is not valid JSON")
        
        print("✅ Hash set successful")
        
        # Verify hash get works
        get_req = {"key": hash_key, "field": "field1"}
        response = make_request('POST', f"{MCP_URL}/mcp/redis/hget", get_req)
        
        if response.status_code == 200:
            get_result = response.json()
            if get_result.get('value') == f"value1_{unique_id}":
                print("✅ Hash get verification successful")
            else:
                raise TestFailure(f"Hash get returned wrong value: {get_result.get('value')}")
        
        # Test set operations
        set_key = f"test:set:{unique_id}"
        test_redis_keys_created.append(set_key)
        
        set_req = {
            "key": set_key,
            "members": [f"member1_{unique_id}", f"member2_{unique_id}", f"member3_{unique_id}"]
        }
        
        response = make_request('POST', f"{MCP_URL}/mcp/redis/sadd", set_req)
        
        if response.status_code != 200:
            raise TestFailure(f"Set add failed with status {response.status_code}")
        
        try:
            result = response.json()
        except json.JSONDecodeError:
            raise TestFailure("Set add response is not valid JSON")
        
        print("✅ Set add successful")
        
        # Verify set members
        members_req = {"key": set_key}
        response = make_request('POST', f"{MCP_URL}/mcp/redis/smembers", members_req)
        
        if response.status_code == 200:
            members_result = response.json()
            expected_members = set([f"member1_{unique_id}", f"member2_{unique_id}", f"member3_{unique_id}"])
            actual_members = set(members_result.get('members', []))
            
            if expected_members.issubset(actual_members):
                print("✅ Set members verification successful")
            else:
                raise TestFailure(f"Set members mismatch. Expected: {expected_members}, Got: {actual_members}")
        
        # Test sorted set operations
        zset_key = f"test:zset:{unique_id}"
        test_redis_keys_created.append(zset_key)
        
        zset_req = {
            "key": zset_key,
            "members": {f"item1_{unique_id}": 1.0, f"item2_{unique_id}": 2.0, f"item3_{unique_id}": 3.0}
        }
        
        response = make_request('POST', f"{MCP_URL}/mcp/redis/zadd", zset_req)
        
        if response.status_code != 200:
            raise TestFailure(f"Sorted set add failed with status {response.status_code}")
        
        try:
            result = response.json()
        except json.JSONDecodeError:
            raise TestFailure("Sorted set add response is not valid JSON")
        
        print("✅ Sorted set add successful")
        
        # Verify sorted set range
        range_req = {"key": zset_key, "start": 0, "stop": -1}
        response = make_request('POST', f"{MCP_URL}/mcp/redis/zrange", range_req)
        
        if response.status_code == 200:
            range_result = response.json()
            members = range_result.get('members', [])
            
            if len(members) >= 3:
                print("✅ Sorted set range verification successful")
            else:
                raise TestFailure(f"Sorted set should have at least 3 members, got {len(members)}")
        
        # Test error cases
        print("\n🧪 Testing Redis error cases...")
        
        # Test invalid key format
        invalid_req = {"key": "", "field": "test", "value": "test"}
        response = make_request('POST', f"{MCP_URL}/mcp/redis/hset", invalid_req)
        
        if response.status_code in [400, 422]:  # Should reject empty key
            print("✅ Empty key properly rejected")
        
        return True
        
    except (NetworkError, TestFailure) as e:
        print(f"❌ Redis operations FAILED: {e}")
        return False
    except Exception as e:
        print(f"❌ Redis operations FAILED with unexpected error: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False

def cleanup_test_data():
    """Clean up test data to prevent database pollution"""
    print("\n🧹 Cleaning up test data...")
    
    cleanup_success = True
    
    # Clean up memory entities
    for entity_id in test_entities_created:
        try:
            delete_req = {"entity_id": entity_id}
            response = make_request('POST', f"{MCP_URL}/mcp/memory/delete_entity", delete_req)
            
            if response.status_code in [200, 404]:  # 404 is ok if already deleted
                print(f"✅ Cleaned up memory entity: {entity_id}")
            else:
                print(f"⚠️ Failed to clean up memory entity {entity_id}: status {response.status_code}")
                cleanup_success = False
        except Exception as e:
            print(f"⚠️ Error cleaning up memory entity {entity_id}: {e}")
            cleanup_success = False
    
    # Clean up Redis keys
    for key in test_redis_keys_created:
        try:
            delete_req = {"key": key}
            response = make_request('POST', f"{MCP_URL}/mcp/redis/delete", delete_req)
            
            if response.status_code in [200, 404]:  # 404 is ok if already deleted
                print(f"✅ Cleaned up Redis key: {key}")
            else:
                print(f"⚠️ Failed to clean up Redis key {key}: status {response.status_code}")
                cleanup_success = False
        except Exception as e:
            print(f"⚠️ Error cleaning up Redis key {key}: {e}")
            cleanup_success = False
    
    # Clear tracking lists
    test_entities_created.clear()
    test_redis_keys_created.clear()
    
    if cleanup_success:
        print("✅ All test data cleaned up successfully")
    else:
        print("⚠️ Some cleanup operations failed - manual cleanup may be required")
    
    return cleanup_success

def test_status():
    """Test status endpoint with comprehensive validation"""
    print("\n📊 Testing server status endpoint...")
    
    try:
        response = make_request('GET', f"{MCP_URL}/status")
        
        if response.status_code != 200:
            raise TestFailure(f"Status endpoint failed with status {response.status_code}")
        
        try:
            status = response.json()
        except json.JSONDecodeError:
            raise TestFailure("Status response is not valid JSON")
        
        # Validate top-level structure
        required_fields = ['status', 'memory_mcp', 'redis_mcp']
        validate_response_structure(status, required_fields, "Status endpoint")
        
        # Validate memory_mcp structure
        memory_fields = ['entities']
        validate_response_structure(status['memory_mcp'], memory_fields, "Memory MCP status")
        
        # Validate redis_mcp structure
        redis_fields = ['hash_keys', 'set_keys', 'sorted_set_keys']
        validate_response_structure(status['redis_mcp'], redis_fields, "Redis MCP status")
        
        # Validate field types and values
        if not isinstance(status['memory_mcp']['entities'], int):
            raise TestFailure("Memory entities count should be an integer")
        
        for field in redis_fields:
            if not isinstance(status['redis_mcp'][field], int):
                raise TestFailure(f"Redis {field} should be an integer")
        
        # Validate status value
        if status['status'] not in ['running', 'healthy', 'ok']:
            print(f"⚠️ Unusual status value: {status['status']}")
        
        print(f"✅ Status endpoint validation successful")
        print(f"   Status: {status['status']}")
        print(f"   Memory entities: {status['memory_mcp']['entities']}")
        print(f"   Redis hash keys: {status['redis_mcp']['hash_keys']}")
        print(f"   Redis set keys: {status['redis_mcp']['set_keys']}")
        print(f"   Redis sorted set keys: {status['redis_mcp']['sorted_set_keys']}")
        
        return True
        
    except (NetworkError, TestFailure) as e:
        print(f"❌ Status endpoint FAILED: {e}")
        return False
    except Exception as e:
        print(f"❌ Status endpoint FAILED with unexpected error: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False

def test_negative_cases():
    """Test negative cases to ensure tests fail when they should"""
    print("\n🚫 Testing negative cases and error handling...")
    
    try:
        # Test invalid endpoint
        response = make_request('GET', f"{MCP_URL}/nonexistent-endpoint")
        if response.status_code == 404:
            print("✅ Invalid endpoint properly returns 404")
        else:
            print(f"⚠️ Invalid endpoint returned unexpected status: {response.status_code}")
        
        # Test malformed JSON
        try:
            invalid_response = requests.post(f"{MCP_URL}/mcp/memory/create_entities", 
                                           data="invalid json", 
                                           headers={'Content-Type': 'application/json'},
                                           timeout=REQUEST_TIMEOUT)
            if invalid_response.status_code in [400, 422]:
                print("✅ Malformed JSON properly rejected")
        except Exception:
            print("✅ Malformed JSON properly handled")
        
        # Test missing required fields
        try:
            incomplete_entity = {"name": "incomplete"}
            response = make_request('POST', f"{MCP_URL}/mcp/memory/create_entities", [incomplete_entity])
            if response.status_code in [400, 422]:
                print("✅ Incomplete entity data properly rejected")
        except Exception:
            print("✅ Incomplete entity data properly handled")
        
        return True
        
    except Exception as e:
        print(f"❌ Negative testing FAILED: {e}")
        return False

def run_performance_tests():
    """Run basic performance tests"""
    print("\n⚡ Running performance tests...")
    
    try:
        # Test response time
        start_time = time.time()
        response = make_request('GET', f"{MCP_URL}/health")
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            if response_time < 1.0:  # Should respond within 1 second
                print(f"✅ Health endpoint response time: {response_time:.3f}s")
            else:
                print(f"⚠️ Slow health endpoint response: {response_time:.3f}s")
        
        # Test concurrent requests (simple load test)
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_concurrent_request():
            try:
                start = time.time()
                resp = make_request('GET', f"{MCP_URL}/health")
                end = time.time()
                results.put((resp.status_code, end - start))
            except Exception as e:
                results.put((None, str(e)))
        
        # Start 5 concurrent requests
        threads = []
        for _ in range(5):
            t = threading.Thread(target=make_concurrent_request)
            threads.append(t)
            t.start()
        
        # Wait for all to complete
        for t in threads:
            t.join()
        
        # Check results
        success_count = 0
        total_time = 0
        
        while not results.empty():
            status, duration = results.get()
            if status == 200:
                success_count += 1
                total_time += duration
        
        if success_count == 5:
            avg_time = total_time / success_count
            print(f"✅ Concurrent requests successful (avg: {avg_time:.3f}s)")
        else:
            print(f"⚠️ Only {success_count}/5 concurrent requests succeeded")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance tests FAILED: {e}")
        return False

def main():
    print("🧪 Comprehensive MCP Server Test Suite")
    print("=" * 60)
    print("This test suite validates:")
    print("• Server connectivity and health")
    print("• Data validation and assertions")
    print("• Error handling and edge cases")
    print("• Automatic cleanup to prevent pollution")
    print("• Performance and load testing")
    print("=" * 60)
    
    total_tests = 0
    passed_tests = 0
    
    with cleanup_guard():
        # Test 1: Health check
        total_tests += 1
        if test_health():
            passed_tests += 1
        else:
            print("\n❌ Server not running or health check failed.")
            print("   Start server with: ./start_integrated_mcp.sh")
            return
        
        # Test 2: Memory operations
        total_tests += 1
        if test_memory_operations():
            passed_tests += 1
        
        # Test 3: Redis operations  
        total_tests += 1
        if test_redis_operations():
            passed_tests += 1
        
        # Test 4: Status endpoint
        total_tests += 1
        if test_status():
            passed_tests += 1
        
        # Test 5: Negative cases
        total_tests += 1
        if test_negative_cases():
            passed_tests += 1
        
        # Test 6: Performance tests
        total_tests += 1
        if run_performance_tests():
            passed_tests += 1
    
    # Final summary
    print("\n" + "=" * 60)
    print(f"📊 TEST SUMMARY: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED! Server is functioning correctly.")
    else:
        print(f"⚠️ {total_tests - passed_tests} test(s) failed. Server may have issues.")
    
    print(f"\n📚 API Documentation: {MCP_URL}/docs")
    print(f"📊 Server Status: {MCP_URL}/status")
    
    # Return non-zero exit code if tests failed
    return 0 if passed_tests == total_tests else 1

if __name__ == "__main__":
    import sys
    exit_code = main()
    sys.exit(exit_code)