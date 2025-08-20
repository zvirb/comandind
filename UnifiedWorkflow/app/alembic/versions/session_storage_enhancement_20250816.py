"""Session Storage Enhancement - Redis-Database Hybrid

Revision ID: session_storage_enhancement_20250816
Revises: auth_performance_indexes_20250816
Create Date: 2025-08-16 10:30:00.000000

Adds session storage table for Redis-database hybrid session management.
Provides session persistence, failover, and performance optimization.

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'session_storage_enhancement_20250816'
down_revision = 'auth_performance_indexes_20250816'
branch_labels = None
depends_on = None


def upgrade():
    """Add session storage table and related enhancements."""
    
    # === Session Storage Table ===
    
    op.create_table(
        'session_store',
        sa.Column('session_id', sa.String(255), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_activity', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', postgresql.JSON()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, 
                 server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('session_id')
    )
    
    # === Performance Indexes for Session Storage ===
    
    # Primary lookup indexes
    op.create_index(
        'idx_session_store_user_active', 
        'session_store', 
        ['user_id', 'status', 'expires_at'],
        postgresql_where=sa.text("status = 'active' AND expires_at > NOW()"),
        postgresql_using='btree'
    )
    
    # Session cleanup index
    op.create_index(
        'idx_session_store_cleanup', 
        'session_store', 
        ['expires_at', 'status'],
        postgresql_using='btree'
    )
    
    # Activity-based queries
    op.create_index(
        'idx_session_store_activity', 
        'session_store', 
        ['last_activity'],
        postgresql_using='btree'
    )
    
    # Email-based session lookup
    op.create_index(
        'idx_session_store_email', 
        'session_store', 
        ['email', 'status'],
        postgresql_using='btree'
    )
    
    # Session metadata search (GIN index for JSON)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_session_metadata_gin 
        ON session_store USING gin (metadata)
        WHERE metadata IS NOT NULL
    """)
    
    # === Session Audit and Security ===
    
    # Create session audit table for security tracking
    op.create_table(
        'session_audit',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('session_id', sa.String(255), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),  # created, accessed, invalidated, expired
        sa.Column('ip_address', sa.String(45)),  # IPv4 and IPv6 support
        sa.Column('user_agent', sa.Text()),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('details', postgresql.JSON()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Session audit indexes
    op.create_index(
        'idx_session_audit_session', 
        'session_audit', 
        ['session_id', 'timestamp'],
        postgresql_using='btree'
    )
    
    op.create_index(
        'idx_session_audit_user', 
        'session_audit', 
        ['user_id', 'timestamp'],
        postgresql_using='btree'
    )
    
    op.create_index(
        'idx_session_audit_action', 
        'session_audit', 
        ['action', 'timestamp'],
        postgresql_using='btree'
    )
    
    # Security monitoring index
    op.execute("""
        CREATE INDEX CONCURRENTLY IF EXISTS idx_session_security_events 
        ON session_audit (timestamp DESC) 
        WHERE action IN ('security_violation', 'concurrent_login', 'suspicious_activity')
    """)
    
    # === Session Configuration Table ===
    
    # Global session configuration
    op.create_table(
        'session_config',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('key', sa.String(100), nullable=False, unique=True),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, 
                 server_default=sa.func.now()),
        sa.Column('updated_by', sa.Integer()),  # admin user_id
        sa.PrimaryKeyConstraint('id')
    )
    
    # Insert default session configuration
    op.execute("""
        INSERT INTO session_config (key, value, description) VALUES
        ('session_timeout', '3600', 'Default session timeout in seconds (1 hour)'),
        ('max_concurrent_sessions', '5', 'Maximum concurrent sessions per user'),
        ('session_extension_threshold', '300', 'Auto-extend session if activity within N seconds of expiry'),
        ('enable_session_audit', 'true', 'Enable session audit logging'),
        ('redis_primary', 'true', 'Use Redis as primary session storage'),
        ('database_backup', 'true', 'Enable database backup for sessions'),
        ('cleanup_interval', '300', 'Session cleanup interval in seconds'),
        ('security_monitoring', 'true', 'Enable session security monitoring')
    """)
    
    # === Enhanced User Sessions Table ===
    
    # Check if user_sessions table exists, if not create it
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            session_token VARCHAR(255) NOT NULL UNIQUE,
            device_fingerprint VARCHAR(255),
            ip_address VARCHAR(45),
            user_agent TEXT,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT NOW(),
            last_activity TIMESTAMP DEFAULT NOW(),
            expires_at TIMESTAMP NOT NULL,
            metadata JSON
        );
    """)
    
    # Add foreign key constraint if not exists
    op.execute("""
        ALTER TABLE user_sessions 
        ADD CONSTRAINT IF NOT EXISTS fk_user_sessions_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
    """)
    
    # === Triggers for Automatic Session Management ===
    
    # Trigger to update session_store.updated_at automatically
    op.execute("""
        CREATE OR REPLACE FUNCTION update_session_timestamp()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        
        CREATE TRIGGER session_store_update_timestamp
            BEFORE UPDATE ON session_store
            FOR EACH ROW
            EXECUTE FUNCTION update_session_timestamp();
    """)
    
    # Trigger for session audit logging
    op.execute("""
        CREATE OR REPLACE FUNCTION log_session_changes()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                INSERT INTO session_audit (session_id, user_id, action, details)
                VALUES (NEW.session_id, NEW.user_id, 'created', 
                       json_build_object('status', NEW.status, 'expires_at', NEW.expires_at));
                RETURN NEW;
            ELSIF TG_OP = 'UPDATE' THEN
                IF OLD.status != NEW.status THEN
                    INSERT INTO session_audit (session_id, user_id, action, details)
                    VALUES (NEW.session_id, NEW.user_id, 'status_changed', 
                           json_build_object('old_status', OLD.status, 'new_status', NEW.status));
                END IF;
                RETURN NEW;
            ELSIF TG_OP = 'DELETE' THEN
                INSERT INTO session_audit (session_id, user_id, action, details)
                VALUES (OLD.session_id, OLD.user_id, 'deleted', 
                       json_build_object('final_status', OLD.status));
                RETURN OLD;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        
        CREATE TRIGGER session_audit_trigger
            AFTER INSERT OR UPDATE OR DELETE ON session_store
            FOR EACH ROW
            EXECUTE FUNCTION log_session_changes();
    """)
    
    # === Performance Views ===
    
    # Active sessions view for monitoring
    op.execute("""
        CREATE VIEW active_sessions AS
        SELECT 
            ss.session_id,
            ss.user_id,
            u.email,
            ss.role,
            ss.created_at,
            ss.last_activity,
            ss.expires_at,
            EXTRACT(EPOCH FROM (ss.expires_at - NOW())) AS seconds_until_expiry,
            ss.metadata
        FROM session_store ss
        JOIN users u ON ss.user_id = u.id
        WHERE ss.status = 'active' 
        AND ss.expires_at > NOW();
    """)
    
    # Session statistics view
    op.execute("""
        CREATE VIEW session_statistics AS
        SELECT 
            COUNT(*) as total_sessions,
            COUNT(*) FILTER (WHERE status = 'active') as active_sessions,
            COUNT(*) FILTER (WHERE expires_at > NOW()) as non_expired_sessions,
            COUNT(DISTINCT user_id) as unique_users,
            AVG(EXTRACT(EPOCH FROM (expires_at - created_at))) as avg_session_duration,
            MIN(created_at) as oldest_session,
            MAX(last_activity) as most_recent_activity
        FROM session_store;
    """)
    
    # Update table statistics for optimal query planning
    op.execute("ANALYZE session_store;")
    op.execute("ANALYZE session_audit;")
    op.execute("ANALYZE session_config;")


def downgrade():
    """Remove session storage enhancements."""
    
    # Drop views
    op.execute("DROP VIEW IF EXISTS session_statistics;")
    op.execute("DROP VIEW IF EXISTS active_sessions;")
    
    # Drop triggers and functions
    op.execute("DROP TRIGGER IF EXISTS session_audit_trigger ON session_store;")
    op.execute("DROP TRIGGER IF EXISTS session_store_update_timestamp ON session_store;")
    op.execute("DROP FUNCTION IF EXISTS log_session_changes();")
    op.execute("DROP FUNCTION IF EXISTS update_session_timestamp();")
    
    # Drop indexes
    op.drop_index('idx_session_store_user_active', table_name='session_store')
    op.drop_index('idx_session_store_cleanup', table_name='session_store')
    op.drop_index('idx_session_store_activity', table_name='session_store')
    op.drop_index('idx_session_store_email', table_name='session_store')
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_session_metadata_gin;")
    
    op.drop_index('idx_session_audit_session', table_name='session_audit')
    op.drop_index('idx_session_audit_user', table_name='session_audit')
    op.drop_index('idx_session_audit_action', table_name='session_audit')
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_session_security_events;")
    
    # Drop tables
    op.drop_table('session_config')
    op.drop_table('session_audit')
    op.drop_table('session_store')