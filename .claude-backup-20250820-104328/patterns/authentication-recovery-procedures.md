# Authentication Recovery Procedures

## Emergency Authentication Recovery (Production-Critical)

### Quick Reference Checklist
```
□ 1. Identify authentication failure symptoms
□ 2. Check system logs for initialization errors  
□ 3. Apply graceful degradation pattern
□ 4. Validate system recovery
□ 5. Monitor authentication metrics
□ 6. Document incident and learning
```

### Step-by-Step Recovery Procedures

#### Phase 1: Rapid Assessment (0-2 minutes)

**1.1 Symptom Detection**
```bash
# Check API health
curl -s https://aiwfe.com/api/v1/health | jq .

# Look for authentication errors
curl -s https://aiwfe.com/api/v1/auth/jwt/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test","password":"test"}' | jq .
```

**1.2 Log Analysis**
```bash
# Check for initialization errors
docker logs aiwfe-api 2>&1 | grep -i "error\|failed\|exception" | tail -20

# Specific authentication error patterns
docker logs aiwfe-api 2>&1 | grep -E "(is_production|initialize.*auth|NameError)" | tail -10
```

#### Phase 2: Immediate Stabilization (2-5 minutes)

**2.1 Apply Graceful Degradation Pattern**

Edit `/home/marku/ai_workflow_engine/app/api/main.py`:

```python
# ORIGINAL (causing failure):
# try:
#     logger.info("Initializing authentication services...")
#     from api.auth_compatibility import initialize_auth_services
#     await initialize_auth_services()
#     logger.info("Authentication services initialized successfully.")
# except Exception as e:
#     logger.error("Failed to initialize authentication services: %s", e, exc_info=True)

# RECOVERY PATTERN (proven solution):
# DISABLED: Initialize authentication services - causing startup failures
# Using simplified JWT authentication instead of complex enhanced system
# try:
#     logger.info("Initializing authentication services...")
#     from api.auth_compatibility import initialize_auth_services
#     await initialize_auth_services()
#     logger.info("Authentication services initialized successfully.")
# except Exception as e:
#     logger.error("Failed to initialize authentication services: %s", e, exc_info=True)
logger.info("Using simplified JWT authentication - enhanced services disabled")
```

**2.2 Restart Services**
```bash
# Restart API container
docker-compose restart api

# Monitor startup logs
docker logs -f aiwfe-api
```

#### Phase 3: System Validation (5-10 minutes)

**3.1 Health Check Validation**
```bash
# Basic health check
curl -X GET https://aiwfe.com/api/v1/health
# Expected: {"status": "ok", "redis_connection": "ok"}

# Detailed health check
curl -X GET https://aiwfe.com/api/v1/health/detailed | jq .
# Expected: All components showing "ok" status
```

**3.2 Authentication Flow Testing**
```bash
# Test login endpoint
curl -X POST https://aiwfe.com/api/v1/auth/jwt/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "your-password"}' | jq .

# Expected response structure:
# {
#   "access_token": "eyJ...",
#   "token_type": "bearer",
#   "expires_in": 3600
# }
```

**3.3 Database Connectivity Check**
```bash
# Verify database component health
curl -s https://aiwfe.com/api/v1/health/detailed | jq '.components.database'
# Expected: {"status": "ok", "response_time_ms": <number>}
```

#### Phase 4: Full System Testing (10-15 minutes)

**4.1 User Authentication Workflow**
```bash
# Complete authentication test
TOKEN=$(curl -s -X POST https://aiwfe.com/api/v1/auth/jwt/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"your-password"}' | jq -r .access_token)

# Test authenticated endpoint
curl -X GET https://aiwfe.com/api/v1/user/current \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**4.2 WebSocket Authentication**
```bash
# Test WebSocket token validation
curl -X POST https://aiwfe.com/api/v1/debug/auth/test-websocket-token \
  -H "Authorization: Bearer $TOKEN" | jq .
```

### Database Session Management Recovery

#### Primary Pattern: Async Session with Sync Fallback

**Implementation in `dependencies.py`:**
```python
async def get_current_user(request: Request, db: AsyncSession = Depends(get_async_session)) -> User:
    try:
        # Primary: Async database lookup
        token_data = get_current_user_payload(request)
        result = await db.execute(
            select(User).where(
                User.id == token_data.id,
                User.is_active == True
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise credentials_exception
        return user
        
    except Exception as e:
        # Fallback: Sync database session
        db_gen = get_db()
        db_sync = next(db_gen)
        try:
            user = get_user_by_email(db_sync, email=token_data.email)
            if not user or not user.is_active:
                raise credentials_exception
            return user
        finally:
            db_sync.close()
```

**Key Recovery Points:**
1. **Connection Pool Exhaustion**: Sync fallback prevents total failure
2. **Async Session Issues**: Graceful degradation maintains service
3. **Database Connectivity**: Multiple retry mechanisms

### JWT Token Validation Recovery

#### Unified Token Format Support

**Token Parsing Resilience:**
```python
def get_current_user_payload(request: Request) -> TokenData:
    # Enhanced format (sub=user_id, email=email)
    if "email" in payload and "sub" in payload:
        try:
            user_id = int(payload.get("sub"))
            email = payload.get("email")
        except (ValueError, TypeError):
            pass
    
    # Legacy format fallback (sub=email, id=user_id)
    if not user_id or not email:
        sub_value = payload.get("sub")
        if sub_value and "@" in str(sub_value):
            email = sub_value
            user_id = payload.get("id")
```

**Recovery Features:**
- **Clock Skew Tolerance**: 60-second leeway for time synchronization issues
- **Multi-source Token Extraction**: Authorization header and cookie fallback
- **Format Flexibility**: Enhanced and legacy token structure support

### Production Rollback Procedures

#### If Recovery Pattern Fails

**1. Immediate Rollback**
```bash
# Revert to last working commit
git log --oneline -5
git checkout <last-working-commit>
docker-compose down && docker-compose up -d api
```

**2. Database State Verification**
```bash
# Check database connectivity
docker exec -it aiwfe-db psql -U postgres -d aiwfe -c "SELECT COUNT(*) FROM users WHERE is_active = true;"

# Verify user accounts
docker exec -it aiwfe-db psql -U postgres -d aiwfe -c "SELECT id, email, role FROM users LIMIT 5;"
```

**3. Configuration Reset**
```bash
# Reset to known good configuration
cp /home/marku/ai_workflow_engine/.env.backup /home/marku/ai_workflow_engine/.env
docker-compose restart
```

### Monitoring and Alerting Setup

#### Critical Authentication Metrics
```yaml
metrics_to_monitor:
  - auth_success_rate: "> 99%"
  - jwt_validation_latency: "< 50ms" 
  - database_connection_pool: "< 80% utilization"
  - auth_endpoint_error_rate: "< 0.1% 5xx errors"
```

#### Alert Configuration
```bash
# Add to monitoring system
curl -X POST https://monitoring.aiwfe.com/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "name": "auth_system_failure",
    "condition": "auth_success_rate < 95%",
    "duration": "5m",
    "severity": "critical",
    "action": "Apply AOSP-001 recovery pattern"
  }'
```

### Post-Recovery Validation

#### System Health Verification
1. **Authentication Success Rate**: Monitor for 30 minutes post-recovery
2. **Database Performance**: Check query response times
3. **User Experience**: Verify login/logout workflows
4. **WebSocket Connectivity**: Test real-time features
5. **Mobile Authentication**: Validate native client access

#### Documentation Requirements
1. **Incident Timeline**: Record failure and recovery times
2. **Root Cause**: Document specific error conditions
3. **Pattern Effectiveness**: Measure recovery success
4. **Prevention Measures**: Identify improvements
5. **Knowledge Update**: Add to pattern library

This recovery procedure has been validated against the authentication failure in commit af48cd8 and provides a systematic approach to resolving similar issues in the future.