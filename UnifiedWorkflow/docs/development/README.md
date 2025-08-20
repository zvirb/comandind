# Development Guides

Comprehensive development documentation including environment setup, coding standards, workflows, and best practices for the AI Workflow Engine project.

## 💻 Development Overview

The AI Workflow Engine development environment emphasizes:
- **Security-First Development**: mTLS and comprehensive security from the start
- **Test-Driven Development**: TDD workflow for all changes
- **Modular Architecture**: Clean separation of concerns
- **Code Quality**: Strict coding standards and automated checks
- **Documentation**: Code and changes must be well-documented

## 📋 Development Documentation

### [🔧 Environment Setup](environment-setup.md)
Complete development environment configuration:
- Prerequisites and dependencies
- mTLS development setup (mandatory)
- IDE configuration and extensions
- Local development workflow

### [📏 Coding Standards](standards.md)
Project coding standards and conventions:
- Python coding standards
- JavaScript/TypeScript standards
- Database schema standards
- API design standards
- Documentation standards

### [🌿 Git Workflow](git-workflow.md)
Git workflow and branching strategy:
- Branch naming conventions
- Commit message standards
- Pull request process
- Code review guidelines
- Release workflow

### [🤝 Contributing Guidelines](contributing.md)
How to contribute to the project:
- Contribution process
- Issue reporting
- Feature requests
- Documentation contributions
- Community guidelines

## 🚨 Mandatory Development Patterns

### **Critical Requirements** (from CLAUDE.md)
1. **mTLS for Development**: MUST use `docker-compose-mtls.yml`
2. **Security Setup**: MUST run security infrastructure setup first
3. **Dependency Updates**: MUST run `./run.sh --soft-reset` after `pyproject.toml` changes
4. **Python Imports**: MUST use `shared.` prefix for shared code
5. **Security Context**: MUST set security context before database operations
6. **JWT Service**: MUST use `enhanced_jwt_service` for tokens
7. **Tool Execution**: MUST use `tool_sandbox_service` for tool execution
8. **TDD Workflow**: MUST follow Test-Driven Development for testable changes

### Development Environment Commands
```bash
# Required security setup
./scripts/security/setup_mtls_infrastructure.sh setup

# Start development environment (MANDATORY)
docker-compose -f docker-compose-mtls.yml up

# Soft reset after dependency changes (MANDATORY)
./run.sh --soft-reset
```

## 🏗️ Development Architecture

### Required Code Patterns

#### Security Context Setup (MANDATORY)
```python
from shared.services.security_audit_service import security_audit_service

async def database_operation(session, user_id):
    # MUST set security context before ANY database operation
    await security_audit_service.set_security_context(
        session=session, 
        user_id=user_id, 
        service_name="api"
    )
    # ... database operations
```

#### Enhanced JWT Service (MANDATORY)
```python
from shared.services.enhanced_jwt_service import enhanced_jwt_service

# MUST use enhanced_jwt_service for all token operations
token = await enhanced_jwt_service.create_service_token(
    user_id=user_id,
    service_name="api"
)
```

#### Tool Execution (MANDATORY)
```python
from shared.services.tool_sandbox_service import tool_sandbox_service

# ALL tools MUST be executed through sandbox
result = await tool_sandbox_service.execute_tool_safely(
    tool_name="data_processor",
    parameters=params,
    security_context=security_context
)
```

#### Import Standards (MANDATORY)
```python
# CORRECT: Use shared. prefix for all shared code imports
from shared.database.models import User
from shared.services.enhanced_jwt_service import enhanced_jwt_service
from shared.utils.validation import validate_input

# INCORRECT: Direct imports without shared prefix
from database.models import User  # ❌ Wrong
from services.jwt_service import jwt_service  # ❌ Wrong
```

## 🧪 Test-Driven Development

### TDD Workflow (MANDATORY for testable changes)
1. **Write Test**: Write failing test first
2. **Confirm Failure**: Verify test fails as expected
3. **Write Code**: Write minimal code to pass test
4. **Verify**: Confirm test passes
5. **Refactor**: Improve code while keeping tests green

### Testing Requirements
```python
# Example TDD test structure
import pytest
from shared.services.test_service import TestService

class TestFeature:
    async def test_feature_functionality(self):
        # Arrange: Setup test data and context
        test_data = await self.setup_test_data()
        
        # Act: Execute the functionality
        result = await service.process_feature(test_data)
        
        # Assert: Verify expected behavior
        assert result.success
        assert result.data.contains_expected_value()
```

## 🔧 Development Tools

### Required Tools
- **Python 3.9+**: Managed with `pyenv`
- **Poetry**: Dependency management
- **Docker & Docker Compose**: Containerization
- **Git**: Version control
- **PostgreSQL**: Database (via Docker)
- **Redis**: Caching and sessions (via Docker)

### Recommended IDE Extensions
- **Python**: Pylint, Black, isort
- **Docker**: Docker extension
- **Git**: GitLens
- **Database**: PostgreSQL extension
- **Testing**: pytest integration

### Code Quality Tools
```bash
# Code formatting and linting
black .
isort .
pylint app/

# Type checking
mypy app/

# Security scanning
bandit -r app/

# Dependency checking
safety check
```

## 🚀 Development Workflow

### Daily Development Process
1. **Pull Latest**: `git pull origin master`
2. **Setup Security**: `./scripts/security/setup_mtls_infrastructure.sh setup`
3. **Start Environment**: `docker-compose -f docker-compose-mtls.yml up`
4. **Create Branch**: `git checkout -b feature/PROJ-123-description`
5. **TDD Development**: Write tests → Code → Verify
6. **Quality Checks**: Run linting and security checks
7. **Commit**: Follow commit message standards
8. **Push & PR**: Create pull request for review

### Feature Development Checklist
- [ ] Security infrastructure setup completed
- [ ] Development environment running with mTLS
- [ ] Tests written before code (TDD)
- [ ] Security context properly set
- [ ] Shared imports use `shared.` prefix
- [ ] Tool execution uses sandbox service
- [ ] Code passes all quality checks
- [ ] Documentation updated
- [ ] PR created with proper description

## 📊 Performance Considerations

### Development Performance
- **Database Queries**: Use connection pooling and query optimization
- **Memory Usage**: Monitor memory usage during development
- **Build Times**: Optimize Docker build times with layer caching
- **Test Execution**: Parallel test execution where possible

### Debugging Tools
- **Database Queries**: SQL query logging and analysis
- **API Requests**: Request/response logging
- **Performance Profiling**: Python profiling tools
- **Memory Analysis**: Memory leak detection

## 🔗 Related Documentation

- [Security Implementation](../security/overview.md)
- [Architecture Overview](../architecture/system-overview.md)
- [API Development](../api/reference.md)
- [Testing Best Practices](../testing/best-practices.md)
- [Troubleshooting](../troubleshooting/common-issues.md)

## 📚 Quick References

### Common Commands
```bash
# Start development environment
docker-compose -f docker-compose-mtls.yml up

# Run tests
pytest tests/

# Code formatting
black . && isort .

# Dependency update
poetry add package-name
./run.sh --soft-reset

# Generate migration
./scripts/database/_generate_migration.sh "description"
```

### Environment Variables
```bash
# Development environment
export ENVIRONMENT=development
export DATABASE_URL=postgresql://user:pass@localhost/db
export REDIS_URL=redis://localhost:6379
export JWT_SECRET=your-secret-key
```

---

**⚠️ Critical Reminder**: All development MUST follow the mandatory patterns outlined in [CLAUDE.md](../../CLAUDE.md). No exceptions.