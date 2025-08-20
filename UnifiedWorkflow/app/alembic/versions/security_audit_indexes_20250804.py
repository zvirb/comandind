"""Add optimized indexes for security audit queries

Revision ID: security_audit_indexes_20250804
Revises: 
Create Date: 2025-08-04 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'security_audit_indexes_20250804'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Add optimized indexes for security audit queries."""
    
    # === AUDIT LOG INDEXES ===
    
    # Composite index for common audit queries (user + time range)
    op.create_index(
        'idx_audit_log_user_created_time',
        'audit_log',
        ['user_id', 'created_at'],
        schema='audit'
    )
    
    # Composite index for table operations queries
    op.create_index(
        'idx_audit_log_table_operation_time',
        'audit_log',
        ['table_name', 'operation', 'created_at'],
        schema='audit'
    )
    
    # Index for transaction-based queries
    op.create_index(
        'idx_audit_log_transaction_id',
        'audit_log',
        ['transaction_id'],
        schema='audit',
        postgresql_where=sa.text("transaction_id IS NOT NULL")
    )
    
    # Index for IP-based security analysis
    op.create_index(
        'idx_audit_log_ip_time',
        'audit_log',
        ['ip_address', 'created_at'],
        schema='audit',
        postgresql_where=sa.text("ip_address IS NOT NULL")
    )
    
    # === SECURITY VIOLATIONS INDEXES ===
    
    # Composite index for violation analysis by user and severity
    op.create_index(
        'idx_security_violations_user_severity_time',
        'security_violations',
        ['user_id', 'severity', 'created_at'],
        schema='audit'
    )
    
    # Composite index for violation type analysis
    op.create_index(
        'idx_security_violations_type_time',
        'security_violations',
        ['violation_type', 'created_at'],
        schema='audit'
    )
    
    # Index for unresolved violations (admin queries)
    op.create_index(
        'idx_security_violations_unresolved',
        'security_violations',
        ['resolved', 'severity', 'created_at'],
        schema='audit',
        postgresql_where=sa.text("resolved = false")
    )
    
    # Index for blocked violations
    op.create_index(
        'idx_security_violations_blocked_time',
        'security_violations',
        ['blocked', 'created_at'],
        schema='audit'
    )
    
    # Composite index for IP-based violation tracking
    op.create_index(
        'idx_security_violations_ip_time',
        'security_violations',
        ['ip_address', 'created_at'],
        schema='audit',
        postgresql_where=sa.text("ip_address IS NOT NULL")
    )
    
    # === DATA ACCESS LOG INDEXES ===
    
    # Composite index for user access patterns
    op.create_index(
        'idx_data_access_log_user_service_time',
        'data_access_log',
        ['user_id', 'service_name', 'created_at'],
        schema='audit'
    )
    
    # Index for sensitive data access tracking
    op.create_index(
        'idx_data_access_log_sensitive_time',
        'data_access_log',
        ['sensitive_data_accessed', 'user_id', 'created_at'],
        schema='audit',
        postgresql_where=sa.text("sensitive_data_accessed = true")
    )
    
    # Composite index for table access patterns
    op.create_index(
        'idx_data_access_log_table_access_time',
        'data_access_log',
        ['table_name', 'access_type', 'created_at'],
        schema='audit'
    )
    
    # Index for session-based access analysis
    op.create_index(
        'idx_data_access_log_session_time',
        'data_access_log',
        ['session_id', 'created_at'],
        schema='audit',
        postgresql_where=sa.text("session_id IS NOT NULL")
    )
    
    # Index for performance analysis (slow queries)
    op.create_index(
        'idx_data_access_log_slow_queries',
        'data_access_log',
        ['response_time_ms', 'created_at'],
        schema='audit',
        postgresql_where=sa.text("response_time_ms > 1000")
    )
    
    # === SECURITY METRICS INDEXES ===
    
    # Composite index for metric queries
    op.create_index(
        'idx_security_metrics_name_time',
        'security_metrics',
        ['metric_name', 'recorded_at'],
        schema='audit'
    )
    
    # Index for service-specific metrics
    op.create_index(
        'idx_security_metrics_service_time',
        'security_metrics',
        ['service_name', 'recorded_at'],
        schema='audit',
        postgresql_where=sa.text("service_name IS NOT NULL")
    )
    
    # Index for threshold violations
    op.create_index(
        'idx_security_metrics_threshold_violations',
        'security_metrics',
        ['threshold_violated', 'recorded_at'],
        schema='audit',
        postgresql_where=sa.text("threshold_violated = true")
    )
    
    # === QDRANT ACCESS CONTROL INDEXES ===
    
    # Composite index for permission checks (most common query)
    op.create_index(
        'idx_qdrant_access_user_collection_level',
        'qdrant_access_control',
        ['user_id', 'collection_name', 'access_level', 'is_active']
    )
    
    # Index for active permissions with expiration
    op.create_index(
        'idx_qdrant_access_active_expires',
        'qdrant_access_control',
        ['is_active', 'expires_at'],
        postgresql_where=sa.text("is_active = true")
    )
    
    # === SECURITY ACTIONS INDEXES ===
    
    # Composite index for action analysis
    op.create_index(
        'idx_security_actions_type_status_time',
        'security_actions',
        ['action_type', 'status', 'created_at']
    )
    
    # Index for active actions with expiration
    op.create_index(
        'idx_security_actions_active_expires',
        'security_actions',
        ['status', 'expiration'],
        postgresql_where=sa.text("status = 'active' AND expiration IS NOT NULL")
    )
    
    # Index for target-based queries (IP blocks, user suspensions)
    op.create_index(
        'idx_security_actions_target_active',
        'security_actions',
        ['target', 'status', 'created_at']
    )
    
    # === USER SECURITY TIER INDEXES ===
    
    # Index for tier-based queries
    op.create_index(
        'idx_user_security_tier_current',
        'user_security_tiers',
        ['current_tier', 'admin_enforced']
    )
    
    # Index for upgrade tracking
    op.create_index(
        'idx_user_security_tier_upgrade_progress',
        'user_security_tiers',
        ['upgrade_in_progress', 'upgrade_started_at']
    )
    
    # === SECURITY REQUIREMENTS INDEXES ===
    
    # Composite index for requirement status queries
    op.create_index(
        'idx_security_requirements_user_tier_status',
        'security_requirements',
        ['user_id', 'required_for_tier', 'status']
    )
    
    # Index for incomplete requirements
    op.create_index(
        'idx_security_requirements_incomplete',
        'security_requirements',
        ['status', 'required_for_tier', 'updated_at'],
        postgresql_where=sa.text("status IN ('not_configured', 'in_progress', 'failed')")
    )
    
    # Index for expired requirements
    op.create_index(
        'idx_security_requirements_expired',
        'security_requirements',
        ['expires_at', 'auto_renew'],
        postgresql_where=sa.text("expires_at IS NOT NULL AND expires_at < NOW()")
    )
    
    # === CROSS SERVICE AUTH INDEXES ===
    
    # Index for token validation (most common query)
    op.create_index(
        'idx_cross_service_auth_token_active',
        'cross_service_auth',
        ['token_hash', 'is_active', 'expires_at']
    )
    
    # Index for expired tokens cleanup
    op.create_index(
        'idx_cross_service_auth_expires',
        'cross_service_auth',
        ['expires_at', 'is_active']
    )
    
    # Index for user token management
    op.create_index(
        'idx_cross_service_auth_user_service',
        'cross_service_auth',
        ['user_id', 'source_service', 'target_service', 'is_active']
    )
    
    # === PRIVACY REQUEST INDEXES ===
    
    # Index for pending privacy requests
    op.create_index(
        'idx_privacy_requests_pending',
        'privacy_requests',
        ['status', 'due_date'],
        postgresql_where=sa.text("status IN ('PENDING', 'IN_PROGRESS')")
    )
    
    # Index for user privacy history
    op.create_index(
        'idx_privacy_requests_user_type',
        'privacy_requests',
        ['user_id', 'request_type', 'requested_at']
    )
    
    print("Successfully created optimized indexes for security audit queries")


def downgrade():
    """Remove the optimized indexes."""
    
    # === Remove all indexes in reverse order ===
    
    # Privacy requests
    op.drop_index('idx_privacy_requests_user_type', table_name='privacy_requests')
    op.drop_index('idx_privacy_requests_pending', table_name='privacy_requests')
    
    # Cross service auth
    op.drop_index('idx_cross_service_auth_user_service', table_name='cross_service_auth')
    op.drop_index('idx_cross_service_auth_expires', table_name='cross_service_auth')
    op.drop_index('idx_cross_service_auth_token_active', table_name='cross_service_auth')
    
    # Security requirements
    op.drop_index('idx_security_requirements_expired', table_name='security_requirements')
    op.drop_index('idx_security_requirements_incomplete', table_name='security_requirements')
    op.drop_index('idx_security_requirements_user_tier_status', table_name='security_requirements')
    
    # User security tiers
    op.drop_index('idx_user_security_tier_upgrade_progress', table_name='user_security_tiers')
    op.drop_index('idx_user_security_tier_current', table_name='user_security_tiers')
    
    # Security actions
    op.drop_index('idx_security_actions_target_active', table_name='security_actions')
    op.drop_index('idx_security_actions_active_expires', table_name='security_actions')
    op.drop_index('idx_security_actions_type_status_time', table_name='security_actions')
    
    # Qdrant access control
    op.drop_index('idx_qdrant_access_active_expires', table_name='qdrant_access_control')
    op.drop_index('idx_qdrant_access_user_collection_level', table_name='qdrant_access_control')
    
    # Security metrics
    op.drop_index('idx_security_metrics_threshold_violations', table_name='security_metrics', schema='audit')
    op.drop_index('idx_security_metrics_service_time', table_name='security_metrics', schema='audit')
    op.drop_index('idx_security_metrics_name_time', table_name='security_metrics', schema='audit')
    
    # Data access log
    op.drop_index('idx_data_access_log_slow_queries', table_name='data_access_log', schema='audit')
    op.drop_index('idx_data_access_log_session_time', table_name='data_access_log', schema='audit')
    op.drop_index('idx_data_access_log_table_access_time', table_name='data_access_log', schema='audit')
    op.drop_index('idx_data_access_log_sensitive_time', table_name='data_access_log', schema='audit')
    op.drop_index('idx_data_access_log_user_service_time', table_name='data_access_log', schema='audit')
    
    # Security violations
    op.drop_index('idx_security_violations_ip_time', table_name='security_violations', schema='audit')
    op.drop_index('idx_security_violations_blocked_time', table_name='security_violations', schema='audit')
    op.drop_index('idx_security_violations_unresolved', table_name='security_violations', schema='audit')
    op.drop_index('idx_security_violations_type_time', table_name='security_violations', schema='audit')
    op.drop_index('idx_security_violations_user_severity_time', table_name='security_violations', schema='audit')
    
    # Audit log
    op.drop_index('idx_audit_log_ip_time', table_name='audit_log', schema='audit')
    op.drop_index('idx_audit_log_transaction_id', table_name='audit_log', schema='audit')
    op.drop_index('idx_audit_log_table_operation_time', table_name='audit_log', schema='audit')
    op.drop_index('idx_audit_log_user_created_time', table_name='audit_log', schema='audit')
    
    print("Successfully removed optimized indexes for security audit queries")