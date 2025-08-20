# MCP Server Testing Framework

This directory contains a comprehensive testing framework for the MCP (Model Context Protocol) Server with proper validation, cleanup, and error handling.

## Overview

The testing framework addresses critical issues found in the original tests:

- ✅ **Proper Assertions**: Tests validate actual response data, not just HTTP status codes
- ✅ **Data Cleanup**: Automatic cleanup prevents database pollution
- ✅ **Robust Error Handling**: Network failures and edge cases are properly handled
- ✅ **Meaningful Test Scenarios**: Tests verify server logic and fail when logic is incorrect
- ✅ **Performance Testing**: Load and performance validation
- ✅ **Security Testing**: Basic security vulnerability checks

## Test Files

### Core Test Suites

1. **`test_integrated_mcp.py`** - Comprehensive standalone test suite
2. **`test_mcp_pytest.py`** - PyTest-based advanced test suite
3. **`run_comprehensive_tests.py`** - Test runner with CI/CD integration

### Configuration Files

- **`pytest.ini`** - PyTest configuration with markers and coverage
- **`test_requirements.txt`** - Python dependencies for testing
- **`TESTING_README.md`** - This documentation file

## Quick Start

### 1. Install Dependencies

```bash
# Install test dependencies
pip install -r test_requirements.txt

# Or if using virtual environment
python3 -m venv test_venv
source test_venv/bin/activate
pip install -r test_requirements.txt
```

### 2. Start MCP Server

```bash
# Start the MCP server
./start_integrated_mcp.sh

# Wait for server to be ready (check health)
curl http://localhost:8000/health
```

### 3. Run Tests

#### Option A: Standalone Test Suite
```bash
# Run comprehensive standalone tests
python test_integrated_mcp.py
```

#### Option B: PyTest Suite
```bash
# Run all tests
pytest

# Run specific test categories
pytest -m "not slow"  # Skip slow tests
pytest -m "integration"  # Only integration tests
pytest -m "performance"  # Only performance tests

# Run with coverage
pytest --cov=. --cov-report=html
```

#### Option C: Comprehensive Test Runner
```bash
# Basic tests only
python run_comprehensive_tests.py

# Include load and security tests
python run_comprehensive_tests.py --include-load --include-security

# CI mode (exit with error code on failure)
python run_comprehensive_tests.py --ci --output ci_results.json
```

## Test Categories

### 1. Health & Connectivity Tests
- Server accessibility
- Health endpoint validation
- Response time verification
- Basic connectivity checks

### 2. Memory MCP Tests
- Entity creation with validation
- Search functionality verification
- Data persistence validation
- Edge case handling (empty queries, invalid data)

### 3. Redis MCP Tests
- Hash operations (HSET/HGET)
- Set operations (SADD/SMEMBERS)
- Sorted set operations (ZADD/ZRANGE)
- Data validation and retrieval verification

### 4. Status Endpoint Tests
- Status endpoint accessibility
- Response structure validation
- Service status verification

### 5. Error Handling Tests
- Invalid endpoint handling (404s)
- Malformed request handling
- Unsupported HTTP methods
- Input validation testing

### 6. Performance Tests
- Response time measurement
- Concurrent request handling
- Load testing under moderate stress
- Performance threshold validation

### 7. Security Tests (Optional)
- Basic SQL injection pattern detection
- XSS pattern validation
- Oversized request handling
- Input sanitization checks

## Key Improvements Over Original Tests

### 1. Proper Data Validation

**Before (Original):**
```python
if response.status_code == 200:
    print("✅ Test passed")
    return True
```

**After (Improved):**
```python
# Validate HTTP status
assert response.status_code == 200

# Validate JSON structure
data = response.json()
validate_response_structure(data, required_fields, "Test name")

# Validate actual data values
assert data['entity_id'] == expected_entity_id
assert entity_found_in_search_results(entity_id, search_results)
```

### 2. Automatic Cleanup

**Before (Original):**
```python
# Create test data
entity = {...}
response = requests.post(url, json=[entity])
# No cleanup - data remains in database forever
```

**After (Improved):**
```python
with cleanup_guard():
    # Create test data
    entity_id = create_test_entity()
    test_entities_created.append(entity_id)  # Track for cleanup
    
    # Run tests...
    
# Automatic cleanup happens even if tests fail
```

### 3. Robust Error Handling

**Before (Original):**
```python
try:
    response = requests.get(url)
    # Would crash on network failures
except Exception as e:
    print(f"Failed: {e}")  # Minimal error info
```

**After (Improved):**
```python
def make_request(method, url, json_data=None):
    for attempt in range(MAX_RETRIES):
        try:
            return requests.request(method, url, json=json_data, timeout=TIMEOUT)
        except requests.exceptions.Timeout:
            if attempt == MAX_RETRIES - 1:
                raise NetworkError("Request timed out after retries")
            time.sleep(RETRY_DELAY)
        except requests.exceptions.ConnectionError:
            # Handle connection failures with retries
```

### 4. Meaningful Test Scenarios

**Before (Original):**
- Only checked for HTTP 200 status
- Would pass even with completely broken server logic
- No verification of actual functionality

**After (Improved):**
- Validates response data structure and content
- Verifies server logic works correctly
- Tests fail when server logic is broken
- Includes negative test cases

## CI/CD Integration

### GitHub Actions Example

```yaml
name: MCP Server Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        cd mcp_servers
        pip install -r test_requirements.txt
    
    - name: Start MCP Server
      run: |
        cd mcp_servers
        ./start_integrated_mcp.sh
        sleep 5
    
    - name: Run Tests
      run: |
        cd mcp_servers
        python run_comprehensive_tests.py --ci --include-load --include-security
    
    - name: Upload Test Results
      uses: actions/upload-artifact@v2
      if: always()
      with:
        name: test-results
        path: mcp_servers/test_results.json
```

### Jenkins Pipeline Example

```groovy
pipeline {
    agent any
    
    stages {
        stage('Setup') {
            steps {
                sh 'cd mcp_servers && pip install -r test_requirements.txt'
            }
        }
        
        stage('Start Server') {
            steps {
                sh 'cd mcp_servers && ./start_integrated_mcp.sh'
                sleep(time: 5, unit: 'SECONDS')
            }
        }
        
        stage('Test') {
            steps {
                sh 'cd mcp_servers && python run_comprehensive_tests.py --ci'
            }
            post {
                always {
                    archiveArtifacts artifacts: 'mcp_servers/test_results.json'
                }
            }
        }
    }
}
```

## Configuration Options

### Environment Variables

```bash
# Server configuration
export MCP_SERVER_URL="http://localhost:8000"
export MCP_REQUEST_TIMEOUT=10
export MCP_MAX_RETRIES=3

# Test configuration
export TEST_INCLUDE_LOAD=true
export TEST_INCLUDE_SECURITY=true
export TEST_OUTPUT_FILE="custom_results.json"
```

### Custom Test Markers

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Run performance tests only
pytest -m performance

# Run security tests only
pytest -m security
```

## Troubleshooting

### Common Issues

1. **Server Not Running**
   ```bash
   # Error: Connection refused
   # Solution: Start the server
   ./start_integrated_mcp.sh
   ```

2. **Test Data Pollution**
   ```bash
   # Error: Tests failing due to existing data
   # Solution: Manual cleanup or restart server
   ./stop_integrated_mcp.sh
   ./start_integrated_mcp.sh
   ```

3. **Timeout Issues**
   ```bash
   # Error: Tests timing out
   # Solution: Increase timeout or check server performance
   export MCP_REQUEST_TIMEOUT=30
   ```

4. **Missing Dependencies**
   ```bash
   # Error: ModuleNotFoundError
   # Solution: Install test requirements
   pip install -r test_requirements.txt
   ```

### Debug Mode

```bash
# Run tests with verbose output
python test_integrated_mcp.py --verbose

# Run pytest with debug info
pytest -v -s --tb=long

# Run with coverage and keep temp files
pytest --cov=. --cov-report=html --keep-duplicates
```

## Performance Benchmarks

### Expected Performance Targets

- **Health Endpoint**: < 100ms response time
- **Entity Creation**: < 500ms response time
- **Search Operations**: < 1s response time
- **Concurrent Requests**: 95%+ success rate with 10 concurrent users
- **Load Testing**: Handle 50 requests with 90%+ success rate

### Performance Monitoring

```bash
# Run performance tests only
pytest -m performance

# Run load tests
python run_comprehensive_tests.py --include-load

# Custom load test
python -c "
from run_comprehensive_tests import TestRunner
runner = TestRunner()
runner.run_load_tests(concurrent_users=20, requests_per_user=10)
"
```

## Security Considerations

### Security Test Coverage

- **Input Validation**: SQL injection, XSS patterns
- **Request Size Limits**: Oversized request handling
- **Error Information**: Sensitive data exposure
- **Rate Limiting**: Basic DoS protection

### Security Test Examples

```bash
# Run security tests only
pytest -m security

# Include security in comprehensive tests
python run_comprehensive_tests.py --include-security

# Manual security test
curl -X POST http://localhost:8000/mcp/memory/create_entities \
  -H "Content-Type: application/json" \
  -d '[{"name": "<script>alert(\"xss\")</script>"}]'
```

## Contributing

### Adding New Tests

1. **For PyTest**: Add test methods to appropriate test classes in `test_mcp_pytest.py`
2. **For Standalone**: Add test functions to `test_integrated_mcp.py`
3. **For Runners**: Extend `run_comprehensive_tests.py` with new test categories

### Test Naming Conventions

- Test files: `test_*.py` or `*_test.py`
- Test classes: `Test*`
- Test methods: `test_*`
- Test markers: Use descriptive markers like `@pytest.mark.slow`

### Code Quality

```bash
# Run linting
flake8 test_*.py

# Run type checking
mypy test_*.py

# Format code
black test_*.py
```

This comprehensive testing framework ensures that the MCP server is thoroughly validated with proper error handling, data cleanup, and meaningful assertions that actually verify server functionality rather than just connectivity.