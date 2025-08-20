# Development Workflow Scripts

This guide covers the essential scripts and workflows for daily development tasks in the AI Workflow Engine project.

## 🚀 Quick Start Development Workflow

### Initial Setup (First Time)
```bash
# 1. Clone and enter project
git clone <repository-url>
cd ai_workflow_engine

# 2. Fix permissions and make scripts executable
sudo ./scripts/fix_permissions.sh
./scripts/_make_scripts_executable.sh

# 3. Complete initial setup
./scripts/_setup.sh

# 4. Start the application
./run.sh
```

### Daily Development Workflow
```bash
# 1. Start development environment (preserves data)
./run.sh --soft-reset

# 2. Make your code changes
# Edit files in app/, docker/, config/, etc.

# 3. Generate migration if needed
./scripts/_generate_migration.sh "Add new feature"

# 4. Test changes
# Access application at https://localhost:8080

# 5. Fix any permission issues
sudo ./scripts/fix_permissions.sh  # If needed
```

---

## 🔄 Development Reset Options

### Soft Reset (Recommended for Development)
**Use when:** Code changes, dependency updates, configuration changes
**Preserves:** User data, AI models, certificates, chat history
**Removes:** Application containers, build cache

```bash
./run.sh --soft-reset
```

**What it preserves:**
- ✅ User accounts and authentication
- ✅ Chat history and conversations
- ✅ AI model downloads (several GB)
- ✅ Vector embeddings (Qdrant data)
- ✅ SSL certificates and secrets
- ✅ Session data and login tokens

**What it resets:**
- ❌ Application containers (rebuilt)
- ❌ Monitoring data (Prometheus/Grafana)
- ❌ Temporary build artifacts

### Full Reset (Use with Caution)
**Use when:** Major structural changes, database schema changes, corrupted data
**Removes:** Everything including user data and AI models

```bash
./run.sh --reset
```

**⚠️ Warning:** This removes ALL data including user accounts and AI models.

### Build Only (Quick Updates)
**Use when:** Minor code changes, UI updates
**Preserves:** All data and running state
**Updates:** Docker images only

```bash
./run.sh --build
```

---

## 🗃️ Database Development Workflow

### Making Model Changes
```bash
# 1. Edit your model files
vim app/shared/database/models/_models.py

# 2. Generate migration
./scripts/_generate_migration.sh "Add user preferences table"

# 3. Review the generated migration
cat app/alembic/versions/latest_migration_*.py

# 4. Apply migration (automatic on restart)
./run.sh --soft-reset

# 5. Verify migration applied
python ./scripts/migrate_check.py
```

### Database Management
```bash
# Check migration status
python ./scripts/migrate_check.py

# Create admin user
./scripts/create_admin.sh

# Seed test data
python ./scripts/seed_initial_data.py

# Fix database issues
./scripts/fix_database_users.sh
```

---

## 🔐 Certificate and Security Development

### Working with Certificates
```bash
# Generate development certificates
./scripts/generate_dev_certificates.sh

# Full mTLS setup (production-like)
./scripts/security/setup_mtls_infrastructure.sh setup

# Validate SSL configuration
./scripts/validate_ssl_configuration.sh

# Fix certificate issues
./scripts/security/setup_mtls_infrastructure.sh validate
```

### Security Testing
```bash
# Validate security implementation
./scripts/security/validate_security_implementation.sh

# Test SSL configuration
python ./scripts/validate_ssl_fix.py

# Monitor security events
./scripts/validate_security_monitoring.sh
```

---

## 🧪 Testing and Validation Workflow

### Automated Testing
```bash
# Setup test environment
python ./scripts/setup_playwright_user.py

# Run web UI tests
python ./scripts/test_webui_playwright.py

# Test SSL/TLS configuration
python ./scripts/test_webui_ssl.py

# Validate domain configuration
python ./scripts/validate_domain_configuration.py
```

### Health Checks
```bash
# Check overall stack health
./scripts/_check_stack_health.sh

# Monitor container health
./scripts/_container_inspector.sh

# Test worker health
./scripts/test_worker_healthcheck.sh
```

---

## 🔧 Troubleshooting Development Issues

### Permission Issues
```bash
# Fix all permission problems
sudo ./scripts/fix_permissions.sh

# Make scripts executable
./scripts/_make_scripts_executable.sh

# Check ownership
ls -la scripts/
```

### Service Issues
```bash
# Universal worker fixes
./scripts/worker_universal_fix.sh

# Debug worker environment
./scripts/debug_worker_env.sh

# Diagnose specific issues
./scripts/diagnose_worker.sh

# Fix database connections
./scripts/fix_worker_database.sh
```

### Container Issues
```bash
# Check container status
docker compose ps

# View service logs
docker compose logs <service_name>

# Restart specific service
docker compose restart <service_name>

# Force rebuild problem service
docker compose build --no-cache <service_name>
```

### Development Environment Issues
```bash
# Reset development environment
./scripts/_dev_restart.sh

# Fix startup issues
./scripts/post_startup_fixes.sh

# Check service health
./scripts/_check_stack_health.sh
```

---

## 🤖 AI Integration Development

### MCP Server for AI Sessions
```bash
# Start Redis MCP server for Claude/Gemini
./scripts/mcp-redis-start.sh

# Manage AI coding sessions
./scripts/mcp-session-manager.sh list

# Stop MCP server when done
./scripts/mcp-redis-stop.sh
```

### AI Model Management
```bash
# Download required AI models
./scripts/pull_models_if_needed.sh

# Check model availability
docker exec ollama ollama list

# Pull specific model
docker exec ollama ollama pull llama2:7b
```

---

## 📊 Monitoring During Development

### Real-time Monitoring
```bash
# View real-time errors
tail -f logs/runtime_errors.log

# Monitor specific service
docker logs -f <service_name>

# Watch Docker events
./scripts/_docker_watch.sh

# Monitor system events
./scripts/_watch_events.sh
```

### Log Analysis
```bash
# View comprehensive error log
cat logs/error_log.txt

# Find specific errors
./scripts/_find_error_source.sh

# Get AI-powered diagnostics
./scripts/_ask_gemini.sh
```

---

## 🚀 Performance Optimization Workflow

### Development Performance
```bash
# Optimize Docker performance
docker system prune -f

# Monitor resource usage
docker stats

# Check container health
./scripts/_container_inspector.sh

# Apply performance optimizations
./scripts/deploy_performance_optimizations.sh
```

### Database Performance
```bash
# Check database performance
docker exec postgres pg_stat_statements

# Monitor connection pools
docker exec pgbouncer cat /etc/pgbouncer/pgbouncer.ini

# Optimize queries and indexes
./scripts/_generate_migration.sh "Add performance indexes"
```

---

## 🔄 Git Workflow Integration

### Pre-commit Workflow
```bash
# Before committing changes
1. ./scripts/validate_ssl_configuration.sh  # Validate security
2. python ./scripts/test_webui_playwright.py  # Run tests
3. ./scripts/_check_stack_health.sh  # Verify health
4. git add .
5. git commit -m "feature: Add new functionality"
```

### Branch Management
```bash
# Create feature branch
git checkout -b feature/PROJ-123-add-new-feature

# Make changes and test
./run.sh --soft-reset
# ... development work ...

# Validate before merge
./scripts/validate_ssl_configuration.sh
python ./scripts/test_webui_playwright.py

# Merge to main
git checkout main
git merge feature/PROJ-123-add-new-feature
```

---

## 🎯 Development Best Practices

### Efficient Development Loop
1. **Use Soft Reset:** Preserves data while updating code
2. **Monitor Logs:** Keep logs open to catch issues early
3. **Validate Changes:** Use health checks after modifications
4. **Fix Permissions:** Run permission fixes when needed
5. **Test Early:** Run tests frequently during development

### Resource Management
1. **Docker Cleanup:** Regular `docker system prune` to free space
2. **Log Rotation:** Logs are automatically rotated
3. **Model Management:** Only download needed AI models
4. **Certificate Management:** Use development certificates for speed

### Security During Development
1. **Certificate Validation:** Regular SSL validation
2. **Security Monitoring:** Monitor security events
3. **Access Control:** Use proper authentication even in development
4. **Secrets Management:** Never commit secrets to git

### Performance Considerations
1. **Build Cache:** Use Docker build cache when possible
2. **Service Optimization:** Only restart services that changed
3. **Resource Monitoring:** Monitor container resource usage
4. **Database Optimization:** Keep database healthy

---

## 🚨 Common Development Issues and Solutions

### "Permission Denied" Errors
```bash
# Solution: Fix file permissions
sudo ./scripts/fix_permissions.sh
./scripts/_make_scripts_executable.sh
```

### "Service Unhealthy" Errors
```bash
# Solution: Check service logs and restart
docker compose logs <service_name>
docker compose restart <service_name>
./run.sh --soft-reset  # If needed
```

### "Database Connection" Errors
```bash
# Solution: Fix database issues
./scripts/fix_database_users.sh
./scripts/post_startup_fixes.sh
./scripts/create_admin.sh  # Recreate admin if needed
```

### "Certificate" Errors
```bash
# Solution: Regenerate certificates
./scripts/generate_dev_certificates.sh
./scripts/validate_ssl_configuration.sh
```

### "Migration" Errors
```bash
# Solution: Fix migration issues
python ./scripts/migrate_check.py
./scripts/_generate_migration.sh "Fix migration issue"
./run.sh --reset  # Last resort - loses data
```

---

## 📝 Development Checklist

### Before Starting Development
- [ ] Repository cloned and permissions fixed
- [ ] Initial setup completed (`./scripts/_setup.sh`)
- [ ] Application starts successfully (`./run.sh`)
- [ ] Can access web UI at https://localhost:8080
- [ ] Admin user can log in

### During Development
- [ ] Use soft reset for quick iterations
- [ ] Monitor logs for errors
- [ ] Generate migrations for model changes
- [ ] Test changes in browser
- [ ] Fix permission issues promptly

### Before Committing
- [ ] All services healthy
- [ ] Tests pass
- [ ] Security validation passes
- [ ] No sensitive data in commits
- [ ] Migration files reviewed

### Code Review Preparation
- [ ] Clear commit messages
- [ ] Documentation updated
- [ ] Tests included for new features
- [ ] Security implications considered
- [ ] Performance impact assessed

---

*For production deployment workflows, see [Deployment Workflow](./deployment.md).  
For troubleshooting specific issues, see [Troubleshooting Guide](./troubleshooting.md).*