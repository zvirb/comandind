"""Field-Level Encryption Enhancement

Revision ID: field_encryption_enhancement_20250816
Revises: session_storage_enhancement_20250816
Create Date: 2025-08-16 11:00:00.000000

Adds field-level encryption support for sensitive data:
- Encrypted field columns for PII and sensitive data
- Encryption key management table
- Audit trail for encrypted field access
- Security hardening for sensitive operations

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'field_encryption_enhancement_20250816'
down_revision = 'session_storage_enhancement_20250816'
branch_labels = None
depends_on = None


def upgrade():
    """Add field-level encryption enhancements."""
    
    # === Encryption Key Management ===
    
    op.create_table(
        'encryption_keys',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('key_id', sa.String(100), nullable=False, unique=True),
        sa.Column('key_hash', sa.String(256), nullable=False),  # Hash for verification
        sa.Column('algorithm', sa.String(50), nullable=False, default='AES-256-GCM'),
        sa.Column('status', sa.String(20), nullable=False, default='active'),  # active, rotated, revoked
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime()),
        sa.Column('rotated_at', sa.DateTime()),
        sa.Column('metadata', postgresql.JSON()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Key management indexes
    op.create_index(
        'idx_encryption_keys_status', 
        'encryption_keys', 
        ['status', 'created_at'],
        postgresql_using='btree'
    )
    
    op.create_index(
        'idx_encryption_keys_expiry', 
        'encryption_keys', 
        ['expires_at'],
        postgresql_where=sa.text("status = 'active'"),
        postgresql_using='btree'
    )
    
    # === Encrypted Field Audit ===
    
    op.create_table(
        'field_encryption_audit',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('table_name', sa.String(100), nullable=False),
        sa.Column('field_name', sa.String(100), nullable=False),
        sa.Column('operation', sa.String(20), nullable=False),  # encrypt, decrypt, rotate
        sa.Column('key_id', sa.String(100), nullable=False),
        sa.Column('user_id', sa.Integer()),
        sa.Column('session_id', sa.String(255)),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('data_size', sa.Integer()),
        sa.Column('success', sa.Boolean(), nullable=False, default=True),
        sa.Column('error_message', sa.Text()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Audit indexes
    op.create_index(
        'idx_field_audit_table_field', 
        'field_encryption_audit', 
        ['table_name', 'field_name', 'timestamp'],
        postgresql_using='btree'
    )
    
    op.create_index(
        'idx_field_audit_operation', 
        'field_encryption_audit', 
        ['operation', 'timestamp'],
        postgresql_using='btree'
    )
    
    op.create_index(
        'idx_field_audit_key', 
        'field_encryption_audit', 
        ['key_id', 'timestamp'],
        postgresql_using='btree'
    )
    
    # Security monitoring index
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_field_audit_failed_operations 
        ON field_encryption_audit (timestamp DESC) 
        WHERE success = false
    """)
    
    # === Encrypted Columns for Sensitive Data ===
    
    # Users table - Add encrypted fields for PII
    try:
        op.add_column('users', sa.Column('email_encrypted', sa.Text()))
        op.add_column('users', sa.Column('phone_encrypted', sa.Text()))
        op.add_column('users', sa.Column('ssn_encrypted', sa.Text()))
        op.add_column('users', sa.Column('address_encrypted', sa.Text()))
    except Exception as e:
        # Columns might already exist
        pass
    
    # Session store - Encrypt metadata
    try:
        op.add_column('session_store', sa.Column('metadata_encrypted', sa.Text()))
    except Exception as e:
        # Column might already exist
        pass
    
    # Audit logs - Encrypt event details
    try:
        op.add_column('audit_logs', sa.Column('event_details_encrypted', sa.Text()))
    except Exception as e:
        # Column might already exist
        pass
    
    # === Security Configuration Table ===
    
    op.create_table(
        'security_config',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('category', sa.String(50), nullable=False),  # encryption, audit, access_control
        sa.Column('key', sa.String(100), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('is_sensitive', sa.Boolean(), default=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_by', sa.Integer()),
        sa.UniqueConstraint('category', 'key'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Insert default security configuration
    op.execute("""
        INSERT INTO security_config (category, key, value, description, is_sensitive) VALUES
        ('encryption', 'algorithm', 'AES-256-GCM', 'Primary encryption algorithm', false),
        ('encryption', 'key_rotation_days', '90', 'Key rotation interval in days', false),
        ('encryption', 'enable_field_encryption', 'true', 'Enable field-level encryption', false),
        ('encryption', 'cache_decryption', 'true', 'Cache decrypted values for performance', false),
        ('audit', 'log_encryption_operations', 'true', 'Log all encryption/decryption operations', false),
        ('audit', 'retention_days', '2555', 'Audit log retention period (7 years)', false),
        ('audit', 'alert_failed_operations', 'true', 'Alert on failed encryption operations', false),
        ('access_control', 'max_failed_attempts', '5', 'Maximum failed encryption attempts', false),
        ('access_control', 'lockout_duration_minutes', '30', 'Account lockout duration', false),
        ('security', 'enable_advanced_monitoring', 'true', 'Enable advanced security monitoring', false)
    """)
    
    # === Data Migration Functions ===
    
    # Function to migrate existing data to encrypted format
    op.execute("""
        CREATE OR REPLACE FUNCTION migrate_sensitive_data()
        RETURNS TABLE(table_name text, migrated_count integer) AS $$
        DECLARE
            rec RECORD;
            migrated integer;
        BEGIN
            -- This function would be implemented by the application
            -- to migrate existing sensitive data to encrypted format
            -- It's a placeholder for the migration process
            
            RAISE NOTICE 'Sensitive data migration should be performed by application code';
            RAISE NOTICE 'Use the FieldEncryptionService to encrypt existing data';
            
            RETURN QUERY SELECT 'placeholder'::text, 0;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # === Security Views ===
    
    # Encryption status view
    op.execute("""
        CREATE VIEW encryption_status AS
        SELECT 
            ek.key_id,
            ek.algorithm,
            ek.status,
            ek.created_at,
            ek.expires_at,
            COUNT(fea.id) as usage_count,
            MAX(fea.timestamp) as last_used
        FROM encryption_keys ek
        LEFT JOIN field_encryption_audit fea ON ek.key_id = fea.key_id
        GROUP BY ek.key_id, ek.algorithm, ek.status, ek.created_at, ek.expires_at
        ORDER BY ek.created_at DESC;
    """)
    
    # Security metrics view
    op.execute("""
        CREATE VIEW security_metrics AS
        SELECT 
            DATE_TRUNC('day', timestamp) as date,
            operation,
            COUNT(*) as operation_count,
            COUNT(*) FILTER (WHERE success = false) as failed_count,
            COUNT(DISTINCT table_name) as tables_affected,
            COUNT(DISTINCT user_id) as unique_users
        FROM field_encryption_audit
        WHERE timestamp >= NOW() - INTERVAL '30 days'
        GROUP BY DATE_TRUNC('day', timestamp), operation
        ORDER BY date DESC, operation;
    """)
    
    # === Security Triggers ===
    
    # Trigger to audit configuration changes
    op.execute("""
        CREATE OR REPLACE FUNCTION audit_security_config_changes()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO field_encryption_audit (
                table_name, field_name, operation, key_id, 
                timestamp, data_size, success
            ) VALUES (
                'security_config', 
                COALESCE(NEW.key, OLD.key), 
                TG_OP::text, 
                'system',
                NOW(), 
                0, 
                true
            );
            
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            ELSE
                RETURN NEW;
            END IF;
        END;
        $$ LANGUAGE plpgsql;
        
        CREATE TRIGGER security_config_audit_trigger
            AFTER INSERT OR UPDATE OR DELETE ON security_config
            FOR EACH ROW
            EXECUTE FUNCTION audit_security_config_changes();
    """)
    
    # === Automatic Cleanup ===
    
    # Function for automatic cleanup of old audit records
    op.execute("""
        CREATE OR REPLACE FUNCTION cleanup_encryption_audit()
        RETURNS integer AS $$
        DECLARE
            retention_days integer;
            deleted_count integer;
        BEGIN
            -- Get retention period from configuration
            SELECT value::integer INTO retention_days
            FROM security_config 
            WHERE category = 'audit' AND key = 'retention_days';
            
            IF retention_days IS NULL THEN
                retention_days := 2555; -- Default 7 years
            END IF;
            
            -- Delete old audit records
            DELETE FROM field_encryption_audit 
            WHERE timestamp < NOW() - (retention_days || ' days')::interval;
            
            GET DIAGNOSTICS deleted_count = ROW_COUNT;
            
            RAISE NOTICE 'Cleaned up % old encryption audit records', deleted_count;
            RETURN deleted_count;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # === Performance Optimizations ===
    
    # Partial indexes for encrypted fields
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_encrypted_fields 
        ON users (id) 
        WHERE email_encrypted IS NOT NULL 
        OR phone_encrypted IS NOT NULL 
        OR ssn_encrypted IS NOT NULL 
        OR address_encrypted IS NOT NULL;
    """)
    
    # Index for session metadata encryption
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_session_encrypted_metadata 
        ON session_store (session_id) 
        WHERE metadata_encrypted IS NOT NULL;
    """)
    
    # Update statistics
    op.execute("ANALYZE encryption_keys;")
    op.execute("ANALYZE field_encryption_audit;")
    op.execute("ANALYZE security_config;")


def downgrade():
    """Remove field-level encryption enhancements."""
    
    # Drop views
    op.execute("DROP VIEW IF EXISTS security_metrics;")
    op.execute("DROP VIEW IF EXISTS encryption_status;")
    
    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS cleanup_encryption_audit();")
    op.execute("DROP FUNCTION IF EXISTS migrate_sensitive_data();")
    
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS security_config_audit_trigger ON security_config;")
    op.execute("DROP FUNCTION IF EXISTS audit_security_config_changes();")
    
    # Drop indexes
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_users_encrypted_fields;")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_session_encrypted_metadata;")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_field_audit_failed_operations;")
    
    op.drop_index('idx_encryption_keys_status', table_name='encryption_keys')
    op.drop_index('idx_encryption_keys_expiry', table_name='encryption_keys')
    op.drop_index('idx_field_audit_table_field', table_name='field_encryption_audit')
    op.drop_index('idx_field_audit_operation', table_name='field_encryption_audit')
    op.drop_index('idx_field_audit_key', table_name='field_encryption_audit')
    
    # Drop encrypted columns
    try:
        op.drop_column('users', 'email_encrypted')
        op.drop_column('users', 'phone_encrypted')
        op.drop_column('users', 'ssn_encrypted')
        op.drop_column('users', 'address_encrypted')
    except Exception:
        pass
    
    try:
        op.drop_column('session_store', 'metadata_encrypted')
    except Exception:
        pass
    
    try:
        op.drop_column('audit_logs', 'event_details_encrypted')
    except Exception:
        pass
    
    # Drop tables
    op.drop_table('security_config')
    op.drop_table('field_encryption_audit')
    op.drop_table('encryption_keys')