# Secure Database Migration Implementation Guide

## Overview

This document provides comprehensive guidance for deploying and managing the secure database migration with user isolation and comprehensive audit trails for the Helios platform integration.

## Security Architecture

### 1. Row-Level Security (RLS)

**Implementation**: PostgreSQL Row-Level Security policies enforce user-level data isolation across all sensitive tables.

**Coverage**:
- `users` - Users can only access their own records
- `user_profiles` - Profile data isolated by user_id
- `chat_mode_sessions` - Session data isolated by user_id
- `simple_chat_context` - Context isolated via session ownership
- `router_decision_log` - Routing decisions isolated via session ownership
- `unified_memory_vectors` - Vector data isolated by user_id
- `consensus_memory_nodes` - Consensus memory isolated by user_id
- `agent_context_states` - Agent context isolated by user_id
- `blackboard_events` - Event stream isolated by user_id
- `tasks` - Task data isolated by user_id
- `documents` - Document data isolated by user_id
- `chat_messages` - Message data isolated by user_id

**Security Context Functions**:
```sql
-- Set security context for current session
SELECT set_security_context(user_id, session_id, service_name);

-- Get current user context
SELECT get_current_user_id();
```

### 2. Comprehensive Audit System

**Audit Schema**: Dedicated `audit` schema contains all security tracking tables.

**Core Tables**:
- `audit.audit_log` - Complete operation audit trail
- `audit.security_violations` - Security breach detection and logging
- `audit.data_access_log` - Cross-service data access tracking
- `audit.security_metrics` - Performance and security metrics

**Audit Triggers**: Automatic triggers on all sensitive tables capture:
- INSERT, UPDATE, DELETE operations
- Field-level change tracking
- Security context information
- Transaction details

### 3. Data Protection & Privacy

**Encryption**:
- `encrypted_fields` table for sensitive data storage
- AES-256-GCM encryption for high-security fields
- PBKDF2 key derivation for password-based encryption

**Privacy Compliance**:
- `privacy_requests` table for GDPR compliance
- `data_retention_policies` for automated data lifecycle
- Anonymization functions for user data removal

**Functions**:
```sql
-- Anonymize user data (GDPR compliance)
SELECT anonymize_user_data(user_id);

-- Clean up old data according to retention policies
SELECT audit.cleanup_old_data();
```

### 4. Vector Database Security

**Qdrant Access Control**:
- `qdrant_access_control` table manages vector database permissions
- Granular access levels: READ, WRITE, DELETE, ADMIN
- Time-based access expiration
- Conditions-based access control

**Vector Operation Logging**:
```sql
-- Log vector database operations
SELECT audit.log_vector_operation(user_id, operation, collection, point_ids, metadata);
```

### 5. Cross-Service Authentication

**Enhanced JWT Service**:
- Service-to-service authentication tokens
- Cross-service permission management
- Token lifecycle tracking and revocation
- Encrypted payload support for sensitive data

**Cross-Service Auth Table**:
- `cross_service_auth` tracks all inter-service tokens
- Token hash storage (never plaintext)
- Permission and scope management
- Automatic expiration and revocation

## Deployment Guide

### Prerequisites

1. **Database Running**: Ensure PostgreSQL is running and accessible
2. **Backup Strategy**: Automated backup creation before migration
3. **Permission Check**: Verify database user has sufficient privileges
4. **Environment**: Confirm all services are properly configured

### Deployment Steps

1. **Run Deployment Script**:
```bash
./scripts/deploy_security_migration.sh
```

2. **Verify Deployment**:
```bash
# Check audit schema
docker-compose exec postgres psql -U app_user -d ai_workflow_db -c "\dn audit"

# Verify RLS policies
docker-compose exec postgres psql -U app_user -d ai_workflow_db -c "\dp users"

# Check security functions
docker-compose exec postgres psql -U app_user -d ai_workflow_db -c "\df get_current_user_id"
```

3. **Test Security Features**:
```bash
# Run security validation
./scripts/security_monitor.sh
```

### Migration Components

**Files Created/Modified**:
- `secure_database_migration_20250803.py` - Main migration file
- `security_models.py` - Security-related database models
- `security_audit_service.py` - Audit and monitoring service
- `security_validation_service.py` - Validation and testing framework
- `enhanced_jwt_service.py` - Cross-service authentication
- `deploy_security_migration.sh` - Deployment automation

## Usage Guide

### Setting Security Context

**In Application Code**:
```python
from shared.services.security_audit_service import security_audit_service

# Set security context for database session
await security_audit_service.set_security_context(
    session=session,
    user_id=user_id,
    session_id=session_id,
    service_name="api",
    ip_address=request.client.host,
    user_agent=request.headers.get("user-agent")
)
```

### Logging Data Access

```python
# Log sensitive data access
await security_audit_service.log_data_access(
    session=session,
    user_id=user_id,
    service_name="simple_chat",
    access_type="READ",
    table_name="chat_messages",
    row_count=10,
    sensitive_data_accessed=True,
    access_pattern={"query_type": "conversation_history"}
)
```

### Security Violation Reporting

```python
# Report security violation
violation_id = await security_audit_service.log_security_violation(
    session=session,
    violation_type="UNAUTHORIZED_ACCESS_ATTEMPT",
    severity="HIGH",
    violation_details={
        "attempted_resource": "user_profile",
        "target_user_id": target_user_id,
        "reason": "Cross-user access attempt"
    },
    user_id=current_user_id,
    blocked=True
)
```

### Cross-Service Authentication

```python
from shared.services.enhanced_jwt_service import enhanced_jwt_service

# Create service token
service_token = await enhanced_jwt_service.create_service_token(
    session=session,
    user_id=user_id,
    source_service="api",
    target_service="worker",
    permissions={"read": ["tasks"], "write": ["task_results"]},
    scope=["task_execution"]
)

# Verify token
token_data = await enhanced_jwt_service.verify_token(
    session=session,
    token=token,
    required_scopes=["read"]
)
```

### Vector Database Security

```python
# Check vector access permission
has_permission = await security_audit_service.check_vector_access_permission(
    session=session,
    user_id=user_id,
    collection_name="user_embeddings",
    access_level="READ"
)

if has_permission:
    # Proceed with vector operation
    # Log the operation
    await session.execute(
        text("SELECT audit.log_vector_operation(:user_id, :op, :collection, :points, :metadata)"),
        {
            "user_id": user_id,
            "op": "SEARCH",
            "collection": "user_embeddings",
            "points": ["point1", "point2"],
            "metadata": {"query_type": "similarity_search"}
        }
    )
```

## Monitoring & Maintenance

### Security Monitoring

**Automated Monitoring**:
```bash
# Run security monitor (set up as cron job)
./scripts/security_monitor.sh
```

**Manual Security Checks**:
```sql
-- Check recent security violations
SELECT violation_type, severity, COUNT(*) as count
FROM audit.security_violations
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY violation_type, severity
ORDER BY severity DESC;

-- Monitor data access patterns
SELECT user_id, service_name, table_name, COUNT(*) as access_count
FROM audit.data_access_log
WHERE created_at >= NOW() - INTERVAL '1 hour'
  AND sensitive_data_accessed = true
GROUP BY user_id, service_name, table_name
HAVING COUNT(*) > 50;

-- Check audit system health
SELECT 
    COUNT(*) as total_entries,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(DISTINCT table_name) as tables_audited
FROM audit.audit_log
WHERE created_at >= NOW() - INTERVAL '24 hours';
```

### Data Retention Management

**Automated Cleanup**:
```sql
-- Run data cleanup according to retention policies
SELECT audit.cleanup_old_data();
```

**Manual Retention Policy Updates**:
```sql
-- Update retention period for audit logs
UPDATE data_retention_policies 
SET retention_period_days = 2555  -- 7 years
WHERE table_name = 'audit.audit_log';

-- Add new retention policy
INSERT INTO data_retention_policies (table_name, retention_period_days, policy_type)
VALUES ('chat_messages', 1095, 'ANONYMIZE');  -- 3 years, then anonymize
```

### Performance Monitoring

**Query Performance**:
```sql
-- Monitor slow queries in audit logs
SELECT 
    table_name,
    operation,
    AVG(EXTRACT(EPOCH FROM (created_at - LAG(created_at) OVER (ORDER BY created_at)))) as avg_duration
FROM audit.audit_log
WHERE created_at >= NOW() - INTERVAL '1 hour'
GROUP BY table_name, operation
HAVING COUNT(*) > 10
ORDER BY avg_duration DESC;
```

**Database Health**:
```sql
-- Check connection health
SELECT state, COUNT(*) as connection_count
FROM pg_stat_activity
WHERE datname = 'ai_workflow_db'
GROUP BY state;

-- Monitor table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname IN ('public', 'audit')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## Troubleshooting

### Common Issues

1. **RLS Policy Violations**:
   - Symptom: "new row violates row-level security policy" errors
   - Solution: Ensure proper security context is set before database operations
   - Check: Verify `get_current_user_id()` returns expected user ID

2. **Audit Trigger Failures**:
   - Symptom: Operations slow or failing with trigger errors
   - Solution: Check audit schema permissions and disk space
   - Debug: Review audit.audit_log for error patterns

3. **Cross-Service Authentication Issues**:
   - Symptom: Service tokens rejected or expired
   - Solution: Verify token generation and cross_service_auth table
   - Check: Token hash matching and expiration dates

4. **Performance Impact**:
   - Symptom: Slow database operations after migration
   - Solution: Analyze query plans and add indexes if needed
   - Monitor: Use security_metrics table for performance tracking

### Debugging Tools

**Security Context Debugging**:
```sql
-- Check current security context
SELECT 
    current_setting('app.current_user_id', true) as user_id,
    current_setting('app.current_session_id', true) as session_id,
    current_setting('app.current_service', true) as service;
```

**Audit System Health**:
```sql
-- Check audit trigger status
SELECT 
    schemaname,
    tablename,
    COUNT(*) as trigger_count
FROM information_schema.triggers
WHERE trigger_name LIKE 'audit_trigger_%'
GROUP BY schemaname, tablename;
```

**Security Validation**:
```python
# Run comprehensive security validation
from shared.services.security_validation_service import security_validation_service

results = await security_validation_service.run_comprehensive_security_validation()
print(f"Security Status: {results['overall_status']}")
for category in results['test_results']:
    for test in category['results']:
        if test['status'] == 'FAIL':
            print(f"FAILED: {test['test']} - {test['message']}")
```

## Rollback Procedures

### Emergency Rollback

**If Critical Issues Arise**:
```bash
# CAUTION: This removes all security enhancements
./scripts/rollback_security_migration.sh
```

**Selective Rollback**:
```sql
-- Disable RLS on specific table if needed
ALTER TABLE users DISABLE ROW LEVEL SECURITY;

-- Drop specific audit trigger if problematic
DROP TRIGGER IF EXISTS audit_trigger_users ON users;
```

### Data Recovery

**From Backup**:
```bash
# Restore from pre-migration backup
BACKUP_DIR="/path/to/backup"
docker-compose exec postgres psql -U app_user -d ai_workflow_db < "$BACKUP_DIR/full_backup.sql"
```

**Partial Recovery**:
```bash
# Restore only schema
docker-compose exec postgres psql -U app_user -d ai_workflow_db < "$BACKUP_DIR/schema_backup.sql"

# Restore only data
docker-compose exec postgres psql -U app_user -d ai_workflow_db < "$BACKUP_DIR/data_backup.sql"
```

## Best Practices

### Development Guidelines

1. **Always Set Security Context**: Set proper security context before database operations
2. **Log Sensitive Operations**: Use audit service for sensitive data access
3. **Validate Permissions**: Check permissions before vector database operations
4. **Handle Errors Gracefully**: Implement proper error handling for security violations
5. **Monitor Performance**: Track security overhead and optimize if needed

### Operational Security

1. **Regular Monitoring**: Set up automated security monitoring
2. **Audit Reviews**: Regularly review security violations and access patterns
3. **Token Management**: Rotate service tokens regularly
4. **Data Cleanup**: Maintain data retention policies
5. **Backup Strategy**: Regular backups before security updates

### Compliance

1. **GDPR Compliance**: Use privacy request workflow for data subject rights
2. **Audit Retention**: Maintain audit logs for required compliance periods
3. **Data Anonymization**: Use anonymization functions for data deletion requests
4. **Access Logging**: Comprehensive logging for compliance audits
5. **Security Reporting**: Regular security reports for stakeholders

## Support & Maintenance

### Regular Tasks

1. **Weekly**: Run security monitoring and review violations
2. **Monthly**: Review and update data retention policies
3. **Quarterly**: Comprehensive security validation and testing
4. **Annually**: Security architecture review and updates

### Update Procedures

When updating the security implementation:

1. **Test in Development**: Always test security changes in development environment
2. **Backup Before Changes**: Create full backup before any security updates
3. **Staged Deployment**: Deploy security changes in stages
4. **Validation After Deployment**: Run security validation after each update
5. **Monitor Post-Deployment**: Increased monitoring after security changes

### Contact & Escalation

For security issues or questions:
1. **Review Documentation**: Check this guide and DATABASE.md
2. **Check Logs**: Review audit logs and security violations
3. **Run Validation**: Use security validation service for diagnosis
4. **Escalate if Needed**: Contact security team for critical issues

---

*This guide covers the comprehensive security implementation for the AI Workflow Engine. Regular updates to this documentation are essential as the security features evolve.*