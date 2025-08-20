# AI Workflow Engine - Test Execution Guide

## 🚀 Quick Test Commands

### Backend Testing
```bash
# All backend tests with coverage
pytest --cov=app --cov-report=html

# Unit tests only (fast)
pytest tests/unit -v

# Integration tests with real services
pytest tests/integration --integration-db -v

# API endpoint tests
pytest tests/api -v

# Database migration tests
pytest -m migration -v
```

### Frontend Testing
```bash
cd app/webui

# Unit tests for Svelte components
npm run test

# E2E tests with Playwright
npm run test:e2e

# Watch mode for development
npm run test:watch
```

### Performance Testing
```bash
# Quick smoke test (5 users, 2 minutes)
python tests/performance/performance_test_runner.py --profile smoke

# Load test (50 users, 10 minutes)  
python tests/performance/performance_test_runner.py --profile load

# Full performance test suite
python tests/performance/performance_test_runner.py --suite

# Continuous monitoring (24 hours)
python tests/performance/performance_test_runner.py --monitor 24
```

### Security Testing
```bash
# Comprehensive security validation
pytest tests/security --run-external -v

# Authentication security tests only
pytest -m "security and auth" -v
```

### Docker-based Testing
```bash
# Start test environment
docker compose -f docker-compose.test.yml up -d

# Run integration tests against containers
pytest tests/integration -v

# Full E2E testing with all services
docker compose -f docker-compose.test.yml exec api pytest tests/e2e -v
```

## 📊 Coverage and Reporting

### Generate Coverage Reports
```bash
# HTML coverage report
pytest --cov=app --cov-report=html
# Report available at: coverage_html/index.html

# XML report for CI/CD
pytest --cov=app --cov-report=xml

# Terminal coverage with missing lines
pytest --cov=app --cov-report=term-missing
```

### Test Markers
```bash
# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only  
pytest -m api           # API tests only
pytest -m e2e           # End-to-end tests only
pytest -m auth          # Authentication tests
pytest -m security      # Security tests
pytest -m performance   # Performance tests
pytest -m slow          # Long-running tests
pytest -m database      # Database tests
```

## 🎯 Test Quality Gates

- **Code Coverage:** Minimum 80% line coverage required
- **Test Success Rate:** 100% test pass rate required  
- **Performance:** Average response time < 2 seconds
- **Security:** No critical vulnerabilities allowed
- **Code Quality:** All linting and formatting checks must pass

## 🔍 Debugging Tests

```bash
# Run with verbose output and print statements
pytest -v -s tests/unit/test_specific.py

# Run single test with debugger
pytest --pdb tests/unit/test_specific.py::test_function

# Show test coverage gaps
pytest --cov=app --cov-report=term-missing

# Frontend debugging
cd app/webui && npm run test -- --reporter=verbose
```

## 🚀 CI/CD Pipeline Testing

The GitHub Actions pipeline automatically runs:

1. **Pre-flight Checks** - Repository structure validation
2. **Code Quality** - Linting, formatting, security scans  
3. **Unit Tests** - Fast isolated component testing
4. **Integration Tests** - Multi-component interaction testing
5. **API Tests** - Endpoint validation with real services
6. **Frontend Tests** - Component and UI testing
7. **E2E Tests** - Complete user workflow validation  
8. **Security Tests** - Vulnerability assessment
9. **Performance Tests** - Load and stress testing (scheduled)
10. **Deployment Readiness** - Final validation gates

## 📈 Performance Test Profiles

- **smoke** - 5 users, 2 minutes (basic validation)
- **load** - 50 users, 10 minutes (normal expected load)
- **stress** - 200 users, 15 minutes (beyond normal capacity)  
- **spike** - 100 users, rapid spawn (sudden load increases)
- **endurance** - 30 users, 60 minutes (sustained load)
- **capacity** - 500 users, 20 minutes (maximum capacity)

## 🔧 Test Development

### Writing New Tests

1. **Unit Tests:** Test individual functions/classes in isolation
2. **Integration Tests:** Test component interactions with real services
3. **API Tests:** Test endpoints with authentication and validation
4. **E2E Tests:** Test complete user workflows with browser automation
5. **Performance Tests:** Add new user classes to Locust framework

### Test Fixtures

The comprehensive `conftest.py` provides:
- Database fixtures with PostgreSQL containers
- Authentication fixtures with JWT tokens
- Mock service fixtures for external dependencies  
- Test data factories for consistent test data
- Resource monitoring for performance testing

## 🎯 Best Practices

- **Isolation:** Tests should not depend on each other
- **Repeatability:** Tests should produce consistent results
- **Fast Feedback:** Unit tests should run quickly
- **Comprehensive Coverage:** Test happy paths and edge cases
- **Clear Names:** Test names should describe what they verify
- **Arrange-Act-Assert:** Structure tests with clear sections