# AI Workflow Engine - Development Assistant Guide

## 🚨 CRITICAL: Project-Orchestrator First Approach

**MANDATORY**: All user interactions MUST be handled through the **project-orchestrator agent**. This agent coordinates all development tasks and delegates to specialist agents.

## 🎯 Agentic Workflow Requirements

### 1. Primary Agent Protocol
- **ALWAYS** use the `project-orchestrator` agent as the first step for ANY user request
- **NEVER** call specialist agents directly - let project-orchestrator delegate
- **ALL** tasks must go through the orchestration layer

### 2. Agent Interaction Flow
```
User Request → project-orchestrator → Specialist Agents → Validation Testing → 
(If errors found) → Iterate with refined approach → 
(If no errors) → Comprehensive Success Report
```

### 3. Iterative Testing Pattern
**ALL requests must follow this pattern:**
1. **EXECUTE**: project-orchestrator coordinates specialists to implement fixes
2. **VALIDATE**: Test from user perspective to confirm complete resolution  
3. **ITERATE**: If errors persist, refine approach and repeat; if none, generate success report

### 4. No Direct Agent Calls
❌ **FORBIDDEN**: Direct calls to specialist agents like:
- `backend-gateway-expert`
- `webui-architect` 
- `schema-database-expert`
- Any other specialist agent

✅ **REQUIRED**: Always use project-orchestrator:
```
Use project-orchestrator to analyze request and coordinate specialist agents
```

## 🏗️ System Architecture Overview

### Service Communication Flow
```
User/Browser → Caddy (Reverse Proxy) → API Container → Worker/Database Services
                                     ↘ WebUI Container
```

### Container Architecture
- **API Container**: FastAPI backend (`app/api/`)
- **WebUI Container**: SvelteKit frontend (`app/webui/`)
- **Worker Container**: Celery task processing (`app/worker/`)
- **Database Services**: PostgreSQL, Redis, Qdrant
- **Monitoring**: Prometheus, Grafana, AlertManager

## 🐍 Python Development Patterns

### CRITICAL Import Requirements
All Python modules MUST use the `from shared.` import pattern:

```python
# ✅ CORRECT
from shared.database.models import User
from shared.services.auth_service import AuthService
from shared.schemas.user_schemas import UserSchema

# ❌ WRONG - Will cause import failures
from database.models import User
from services.auth_service import AuthService
```

### Database Operations
- **NEVER** modify database schema directly
- **ALWAYS** use Alembic migrations for schema changes
- All models are in `app/shared/database/models/`

## 🔒 Security Model

### Certificate Management
- mTLS certificates for internal service communication
- Let's Encrypt for external domain access
- Client certificates for secure API access

### Authentication Flow
- JWT-based authentication with 2FA support
- OAuth integration for Google services
- WebAuthn for passwordless authentication

## 🛠️ Development Workflow

### 1. Task Analysis (project-orchestrator)
- Analyze user request complexity
- Identify required specialist agents
- Create execution plan
- Get user approval

### 2. Specialist Delegation
- Delegate specific tasks to appropriate agents
- Coordinate between multiple agents when needed
- Ensure consistent architecture patterns

### 3. Implementation Standards
- Follow existing code patterns
- Maintain security-first approach
- Update documentation as needed
- Use TodoWrite for progress tracking

## 📦 Container-Specific Configurations

### API Container (`app/api/`)
- FastAPI with Uvicorn
- Health checks on `/health` endpoint
- Environment-based configuration
- Certificate-based service communication

### WebUI Container (`app/webui/`)
- SvelteKit with TypeScript
- Tailwind CSS for styling
- Progressive Web App (PWA) capabilities
- Hot module replacement in development

### Worker Container (`app/worker/`)
- Celery with Redis broker
- LangGraph for AI workflows
- Ollama integration for local LLMs
- Background task processing

## 🔧 Development Commands

### Container Management
```bash
docker compose up -d          # Start all services
docker compose logs <service> # View service logs
docker compose restart <service> # Restart specific service
```

### Database Operations

**Preferred Method - Use Scripts:**
```bash
# Generate new migration (recommended)
./scripts/_generate_migration.sh "Description of changes"

# Check migration status  
python ./scripts/migrate_check.py

# Apply migrations (automatic during startup)
python ./scripts/run_migrations.py
```

**Alternative Method - Direct Commands:**
```bash
poetry run alembic revision --autogenerate -m "Description"
poetry run alembic upgrade head
```

**Migration Workflow:**
1. Make model changes in `app/shared/database/models/`
2. Generate migration: `./scripts/_generate_migration.sh "Your change description"`
3. Review generated migration file in `alembic/versions/`
4. Test with soft reset: `./run.sh --soft-reset`

### Testing
```bash
pytest tests/                 # Run all tests
pytest tests/test_api.py     # Run specific test file
```

## 🚫 Agentic Workflow Blockers - REMOVED

The following items have been identified and REMOVED to enable smooth agentic workflows:

### 1. Direct Agent Restrictions
- ❌ Removed: Requirements for manual approval of agent calls
- ❌ Removed: Restrictions on agent-to-agent communication
- ❌ Removed: Manual confirmation for standard development tasks

### 2. Automation Enablers
- ✅ Enabled: Automatic specialist agent delegation
- ✅ Enabled: Seamless task coordination
- ✅ Enabled: Autonomous development workflow execution

### 3. Streamlined Processes
- ✅ Project-orchestrator has full delegation authority
- ✅ Standard development tasks require no manual intervention
- ✅ Agents can coordinate complex multi-step operations autonomously

## 📚 Key Documentation References

- **Agent Registry**: `.claude/AGENT_REGISTRY.md` - All available specialist agents
- **Scripts Documentation**: `docs/scripts/` - Comprehensive script usage guides and workflows
- **Research Archive**: `docs/research/` - Saved codebase analysis from research agents
- **Docker Configs**: `docker/` - Container-specific configurations  
- **API Documentation**: `docs/api/` - Endpoint specifications
- **Security Guide**: `docs/security/` - Security implementation details

### Script Categories
- **Database Scripts**: `docs/scripts/database-scripts.md` - Migration and user management
- **Core Scripts**: `docs/scripts/core-scripts.md` - Essential system operations  
- **Security Scripts**: `docs/scripts/security-scripts.md` - SSL/TLS and certificate management
- **Development Workflows**: `docs/scripts/workflows/development.md` - Daily development tasks

---

*This guide ensures efficient agentic workflows while maintaining architectural integrity and security standards.*