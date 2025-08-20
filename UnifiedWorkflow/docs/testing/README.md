# Testing & Validation

Comprehensive testing documentation covering testing strategies, frameworks, automation, and validation procedures for the AI Workflow Engine.

## 🧪 Testing Overview

The AI Workflow Engine testing strategy emphasizes:
- **Test-Driven Development (TDD)**: Mandatory for all testable changes
- **Comprehensive Coverage**: Unit, integration, and end-to-end testing
- **Security Testing**: Authentication, authorization, and vulnerability testing
- **Performance Testing**: Load testing and performance validation
- **Automated Testing**: CI/CD integration and automated test execution

## 📋 Testing Documentation

### [📊 Testing Best Practices](best-practices.md)
Testing strategies and best practices:
- TDD workflow and implementation
- Test organization and structure
- Code coverage requirements
- Testing patterns and conventions
- Quality assurance processes

### [🤖 Test Automation](automation.md)
Automated testing infrastructure:
- CI/CD test integration
- Automated test execution
- Test reporting and analysis
- Performance benchmarking
- Security scan automation

### [🔗 Integration Testing](integration.md)
Integration and system testing:
- API integration testing
- Database integration testing
- Service-to-service testing
- End-to-end workflow testing
- Cross-service communication testing

### [⚡ Performance Testing](performance.md)
Performance testing and optimization:
- Load testing procedures
- Stress testing scenarios
- Performance benchmarking
- Scalability testing
- Performance monitoring

## 🚨 Mandatory TDD Workflow

### **TDD Requirements** (from CLAUDE.md)
For ANY changes that can be tested, you MUST follow Test-Driven Development:

1. **Write Tests First**: Write failing tests before implementation
2. **Confirm Failure**: Verify tests fail as expected
3. **Write Code**: Implement minimal code to pass tests
4. **Verify Success**: Confirm tests pass
5. **Refactor**: Improve code while maintaining test success

### TDD Implementation Example
```python
# 1. Write failing test first
import pytest
from shared.services.user_service import UserService

class TestUserService:
    async def test_create_user_with_security_context(self):
        # Arrange: Setup test data
        user_data = {"username": "test", "email": "test@example.com"}
        
        # Act: Execute functionality (will fail initially)
        result = await UserService.create_user(user_data)
        
        # Assert: Define expected behavior
        assert result.success
        assert result.user.username == "test"
        assert result.user.email == "test@example.com"

# 2. Confirm test fails
# pytest tests/test_user_service.py::TestUserService::test_create_user_with_security_context

# 3. Write minimal code to pass test
# 4. Verify test passes
# 5. Refactor while keeping tests green
```

## 🏗️ Testing Architecture

### Test Structure
```
tests/
├── unit/                    # Unit tests
│   ├── api/                # API layer tests
│   ├── services/           # Service layer tests
│   ├── models/             # Model tests
│   └── utils/              # Utility tests
├── integration/            # Integration tests
│   ├── api_integration/    # API integration tests
│   ├── database/           # Database integration tests
│   └── services/           # Service integration tests
├── e2e/                    # End-to-end tests
│   ├── auth_flow/          # Authentication flow tests
│   ├── user_workflows/     # User workflow tests
│   └── admin_workflows/    # Admin workflow tests
├── performance/            # Performance tests
└── security/               # Security tests
```

### Test Categories

#### **Unit Tests**
```python
# Example unit test with security context
import pytest
from shared.services.enhanced_jwt_service import enhanced_jwt_service
from shared.services.security_audit_service import security_audit_service

class TestJWTService:
    async def test_create_service_token(self):
        # Setup security context (required)
        await security_audit_service.set_security_context(
            session=self.session,
            user_id="test_user",
            service_name="test"
        )
        
        # Test token creation
        token = await enhanced_jwt_service.create_service_token(
            user_id="test_user",
            service_name="api"
        )
        
        assert token is not None
        assert enhanced_jwt_service.validate_token(token)
```

#### **Integration Tests**
```python
# Example integration test
import pytest
from tests.integration.base import IntegrationTestCase

class TestAuthenticationIntegration(IntegrationTestCase):
    async def test_complete_auth_flow(self):
        # Test complete authentication workflow
        login_response = await self.api_client.post(
            "/auth/login",
            json={"username": "test", "password": "test"}
        )
        
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Test authenticated request
        profile_response = await self.api_client.get(
            "/user/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert profile_response.status_code == 200
```

#### **Security Tests**
```python
# Example security test
import pytest
from tests.security.base import SecurityTestCase

class TestSecurityValidation(SecurityTestCase):
    async def test_unauthorized_access_blocked(self):
        # Test that unauthorized requests are blocked
        response = await self.api_client.get("/admin/users")
        assert response.status_code == 401
        
    async def test_jwt_token_validation(self):
        # Test JWT token validation
        invalid_token = "invalid.jwt.token"
        response = await self.api_client.get(
            "/user/profile",
            headers={"Authorization": f"Bearer {invalid_token}"}
        )
        assert response.status_code == 401
```

## 🔧 Testing Tools & Framework

### Core Testing Stack
- **pytest**: Primary testing framework
- **pytest-asyncio**: Async test support
- **pytest-cov**: Code coverage reporting
- **httpx**: HTTP client for API testing
- **factory-boy**: Test data factories
- **faker**: Fake data generation

### Testing Configuration
```python
# pytest configuration (pytest.ini)
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
addopts = 
    --cov=app
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
```

### Test Environment Setup
```python
# Test base class with security context
import pytest
from shared.services.security_audit_service import security_audit_service
from shared.database.session import get_test_session

class BaseTestCase:
    @pytest.fixture(autouse=True)
    async def setup_test_environment(self):
        # Setup test database session
        self.session = await get_test_session()
        
        # Setup security context for tests
        await security_audit_service.set_security_context(
            session=self.session,
            user_id="test_user",
            service_name="test"
        )
        
        yield
        
        # Cleanup
        await self.session.close()
```

## 🚀 Test Execution

### Running Tests
```bash
# Run all tests
pytest

# Run specific test category
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/api/test_auth.py

# Run with verbose output
pytest -v

# Run tests in parallel
pytest -n auto
```

### Continuous Integration
```yaml
# GitHub Actions test workflow
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
          
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install
          
      - name: Setup security infrastructure
        run: ./scripts/security/setup_mtls_infrastructure.sh setup
        
      - name: Run tests
        run: |
          docker-compose -f docker-compose-mtls.yml up -d
          poetry run pytest --cov=app
          
      - name: Upload coverage
        uses: codecov/codecov-action@v1
```

## 📊 Test Coverage & Quality

### Coverage Requirements
- **Minimum Coverage**: 80% overall
- **Critical Paths**: 95% coverage
- **New Code**: 90% coverage
- **Security Code**: 100% coverage

### Quality Metrics
```bash
# Generate coverage report
pytest --cov=app --cov-report=html --cov-report=term

# Quality checks
pylint app/
mypy app/
bandit -r app/

# Performance benchmarks
pytest tests/performance/ --benchmark-only
```

## 🔒 Security Testing

### Security Test Types
- **Authentication Testing**: Login flows, token validation
- **Authorization Testing**: Permission enforcement, access control
- **Input Validation**: SQL injection, XSS protection
- **Certificate Testing**: mTLS validation, certificate rotation
- **Vulnerability Scanning**: Dependency vulnerabilities, code analysis

### Security Test Example
```python
class TestSecurityVulnerabilities:
    async def test_sql_injection_protection(self):
        # Test SQL injection protection
        malicious_input = "'; DROP TABLE users; --"
        response = await self.api_client.post(
            "/search",
            json={"query": malicious_input}
        )
        
        # Should not return 500 error or expose database info
        assert response.status_code != 500
        assert "database" not in response.text.lower()
```

## 🔗 Related Documentation

- [Development Environment](../development/environment-setup.md)
- [Security Testing](../security/overview.md#security-testing)
- [API Testing](../api/reference.md#testing)
- [Troubleshooting Tests](../troubleshooting/common-issues.md)

---

**⚠️ TDD Mandate**: All testable changes MUST follow the TDD workflow as specified in [CLAUDE.md](../../CLAUDE.md).