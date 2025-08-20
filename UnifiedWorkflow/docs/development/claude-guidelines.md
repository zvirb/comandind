# CLAUDE.md - AI Assistant Guidelines

This file provides context and instructions for the Claude AI assistant to ensure smooth collaboration and adherence to project standards.

## 🚨 CRITICAL: Mandatory Security & Development Workflows

**ALL DEVELOPMENT MUST ADHERE TO THE FOLLOWING PATTERNS. NO EXCEPTIONS.**

### **1. Mandatory Development Environment & Commands**
-   **mTLS for Development:** You MUST use `docker-compose-mtls.yml` for all development activities. Standard `docker-compose.yml` is for production-like environments without debugging.
    -   `docker-compose -f docker-compose-mtls.yml up`
-   **Security Setup:** The security infrastructure MUST be set up before running the application.
    -   `./scripts/security/setup_mtls_infrastructure.sh setup`
-   **Dependency Updates:** After modifying `pyproject.toml`, you MUST run `./run.sh --soft-reset` to rebuild containers and update the lock file.

### **2. Mandatory Code Patterns**
-   **Python Imports:** All imports of shared code MUST use the `shared.` prefix. (e.g., `from shared.database.models import User`)
-   **Security Context for DB Operations:** Before ANY database operation, you MUST set the security context.
    ```python
    from shared.services.security_audit_service import security_audit_service
    await security_audit_service.set_security_context(session=session, user_id=user_id, service_name="api")
    ```
-   **Enhanced JWT Service:** You MUST use the `enhanced_jwt_service` for all token creation and validation.
    ```python
    from shared.services.enhanced_jwt_service import enhanced_jwt_service
    token = await enhanced_jwt_service.create_service_token(...)
    ```
-   **Sandboxed Tool Execution:** ALL tools MUST be executed through the `tool_sandbox_service`.
    ```python
    from shared.services.tool_sandbox_service import tool_sandbox_service
    result = await tool_sandbox_service.execute_tool_safely(...)
    ```

### **3. Mandatory Agent Workflow**
-   **Orchestrator First:** For ALL tasks, you MUST use the `project-orchestrator` agent first. Do not call specialist agents directly.
-   **TDD for Changes:** For any changes that can be tested, you MUST follow the Test-Driven Development workflow (Write tests -> Confirm failure -> Write code -> Verify).

## Repository Etiquette

-   **Branch Naming:** `feature/<ticket-id>-<short-description>` (e.g., `feature/PROJ-123-add-login-page`)
-   **Commits:** Follow conventional commit standards.
-   **Merges:** Use rebase and squash merges to maintain a clean history.

## Developer Environment

-   **Python:** Use `pyenv` to manage Python versions. The required version is specified in `.python-version`.
-   **Dependencies:** Use `poetry` for dependency management. Run `poetry install` to set up the environment.

## Project-Specific Notes

-   When generating migrations, use the provided `_generate_migration.sh` script.