"""Authentication and Audit Performance Indexes

Revision ID: auth_performance_indexes_20250816
Revises: 8f0a4749be16
Create Date: 2025-08-16 10:00:00.000000

Adds critical performance indexes for:
1. Authentication queries (user lookup, session validation)
2. Audit system queries (audit trails, security events)  
3. Session storage queries (session data, expiration)
4. Connection pool optimization support

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'auth_performance_indexes_20250816'
down_revision = '8f0a4749be16'
branch_labels = None
depends_on = None


def upgrade():
    """Add performance indexes for authentication and audit systems."""
    
    # === Authentication Performance Indexes ===
    
    # 1. Users table - Critical authentication indexes
    # Email lookup optimization (most frequent auth query)
    op.create_index(
        'idx_users_email_active', 
        'users', 
        ['email'], 
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        postgresql_using='btree'
    )
    
    # Status-based queries for user management
    op.create_index(
        'idx_users_status_created', 
        'users', 
        ['status', 'created_at'], 
        postgresql_using='btree'
    )
    
    # Role-based authorization queries
    op.create_index(
        'idx_users_role_status', 
        'users', 
        ['role', 'status'], 
        postgresql_using='btree'
    )
    
    # 2. Session storage indexes for Redis-backed database sessions
    # Note: These indexes support both Redis and database session storage
    
    # Session validation queries (high frequency during auth)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_user_active 
        ON user_sessions (user_id, is_active, expires_at) 
        WHERE is_active = true AND expires_at > NOW()
    """)
    
    # Session cleanup queries (automated maintenance)
    op.create_index(
        'idx_sessions_expires_cleanup', 
        'user_sessions', 
        ['expires_at'], 
        postgresql_where=sa.text("is_active = false OR expires_at < NOW()"),
        postgresql_using='btree'
    )
    
    # Device-based session management
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_device_fingerprint 
        ON user_sessions USING hash (device_fingerprint) 
        WHERE device_fingerprint IS NOT NULL
    """)
    
    # === Audit System Performance Indexes ===
    
    # 3. Security audit trails - High-performance audit queries
    
    # User activity audit (security monitoring)
    op.create_index(
        'idx_audit_user_timestamp', 
        'audit_logs', 
        ['user_id', 'timestamp'], 
        postgresql_using='btree'
    )
    
    # Event type filtering (security analysis)
    op.create_index(
        'idx_audit_event_timestamp', 
        'audit_logs', 
        ['event_type', 'timestamp'], 
        postgresql_using='btree'
    )
    
    # IP-based security analysis
    op.create_index(
        'idx_audit_ip_timestamp', 
        'audit_logs', 
        ['ip_address', 'timestamp'], 
        postgresql_using='btree'
    )
    
    # Critical security events (real-time monitoring)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_critical_events 
        ON audit_logs (timestamp DESC) 
        WHERE event_type IN ('login_failed', 'security_violation', 'unauthorized_access')
    """)
    
    # 4. JSON field indexes for session and audit data
    
    # Session data GIN index for fast JSON queries
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_data_gin 
        ON user_sessions USING gin (session_data)
        WHERE session_data IS NOT NULL
    """)
    
    # Audit details GIN index for security investigation
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_details_gin 
        ON audit_logs USING gin (event_details)
        WHERE event_details IS NOT NULL
    """)
    
    # === Performance Monitoring Indexes ===
    
    # 5. Connection pool and performance monitoring
    
    # API performance tracking
    op.create_index(
        'idx_performance_endpoint_timestamp', 
        'performance_metrics', 
        ['endpoint', 'timestamp'], 
        postgresql_using='btree'
    )
    
    # Database query performance tracking
    op.create_index(
        'idx_performance_slow_queries', 
        'performance_metrics', 
        ['execution_time'], 
        postgresql_where=sa.text("execution_time > 100"),  # Queries over 100ms
        postgresql_using='btree'
    )
    
    # === Table Partitioning for Large Audit Tables ===
    
    # 6. Audit log partitioning by month for better performance
    op.execute("""
        -- Create partitioned audit table for future high-volume audit data
        CREATE TABLE IF NOT EXISTS audit_logs_partitioned (
            LIKE audit_logs INCLUDING ALL
        ) PARTITION BY RANGE (timestamp);
        
        -- Create current month partition
        CREATE TABLE IF NOT EXISTS audit_logs_current PARTITION OF audit_logs_partitioned
        FOR VALUES FROM (date_trunc('month', CURRENT_DATE)) 
        TO (date_trunc('month', CURRENT_DATE + INTERVAL '1 month'));
        
        -- Create next month partition
        CREATE TABLE IF NOT EXISTS audit_logs_next PARTITION OF audit_logs_partitioned
        FOR VALUES FROM (date_trunc('month', CURRENT_DATE + INTERVAL '1 month')) 
        TO (date_trunc('month', CURRENT_DATE + INTERVAL '2 month'));
    """)
    
    # === Statistics Update for Query Planner ===
    
    # Update table statistics for optimal query planning
    op.execute("ANALYZE users;")
    op.execute("ANALYZE user_sessions;")
    op.execute("ANALYZE audit_logs;")
    op.execute("ANALYZE performance_metrics;")


def downgrade():
    """Remove performance indexes."""
    
    # Remove authentication indexes
    op.drop_index('idx_users_email_active', table_name='users')
    op.drop_index('idx_users_status_created', table_name='users')
    op.drop_index('idx_users_role_status', table_name='users')
    
    # Remove session indexes
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_sessions_user_active;")
    op.drop_index('idx_sessions_expires_cleanup', table_name='user_sessions')
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_sessions_device_fingerprint;")
    
    # Remove audit indexes
    op.drop_index('idx_audit_user_timestamp', table_name='audit_logs')
    op.drop_index('idx_audit_event_timestamp', table_name='audit_logs')
    op.drop_index('idx_audit_ip_timestamp', table_name='audit_logs')
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_audit_critical_events;")
    
    # Remove JSON indexes
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_sessions_data_gin;")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_audit_details_gin;")
    
    # Remove performance indexes
    op.drop_index('idx_performance_endpoint_timestamp', table_name='performance_metrics')
    op.drop_index('idx_performance_slow_queries', table_name='performance_metrics')
    
    # Remove partitioned tables
    op.execute("DROP TABLE IF EXISTS audit_logs_current;")
    op.execute("DROP TABLE IF EXISTS audit_logs_next;")
    op.execute("DROP TABLE IF EXISTS audit_logs_partitioned;")