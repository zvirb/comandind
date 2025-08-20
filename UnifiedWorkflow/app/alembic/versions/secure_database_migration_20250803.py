"""Secure database migration with user isolation and comprehensive audit trails

Revision ID: secure_database_migration_20250803
Revises: unified_memory_integration_20250803
Create Date: 2025-08-03 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'secure_database_migration_20250803'
down_revision: Union[str, Sequence[str], None] = 'unified_memory_integration_20250803'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Deploy secure database migration with user isolation and audit trails."""
    
    # ============================================================================
    # PHASE 1: AUDIT INFRASTRUCTURE
    # ============================================================================
    
    # Create audit schema for security tracking
    op.execute("CREATE SCHEMA IF NOT EXISTS audit;")
    
    # Create audit operations enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE audit.audit_operation AS ENUM (
                'INSERT', 'UPDATE', 'DELETE', 'SELECT', 'TRUNCATE'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create comprehensive audit log table
    op.create_table('audit_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('table_name', sa.String(64), nullable=False),
        sa.Column('operation', sa.Enum('INSERT', 'UPDATE', 'DELETE', 'SELECT', 'TRUNCATE', name='audit_operation'), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.String(), nullable=True),
        sa.Column('row_id', sa.String(), nullable=True),  # Primary key of affected row
        sa.Column('old_values', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('new_values', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('changed_fields', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('application_name', sa.String(100), nullable=True),
        sa.Column('transaction_id', sa.BigInteger(), nullable=True),
        sa.Column('query', sa.Text(), nullable=True),
        sa.Column('security_context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema='audit'
    )
    
    # Create security violations table
    op.create_table('security_violations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('violation_type', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),  # LOW, MEDIUM, HIGH, CRITICAL
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.String(), nullable=True),
        sa.Column('table_name', sa.String(64), nullable=True),
        sa.Column('attempted_operation', sa.String(20), nullable=True),
        sa.Column('violation_details', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('blocked', sa.Boolean(), nullable=False, default=True),
        sa.Column('resolved', sa.Boolean(), nullable=False, default=False),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        schema='audit'
    )
    
    # Create data access log for cross-service tracking
    op.create_table('data_access_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('service_name', sa.String(50), nullable=False),
        sa.Column('access_type', sa.String(20), nullable=False),  # READ, WRITE, DELETE
        sa.Column('table_name', sa.String(64), nullable=False),
        sa.Column('row_count', sa.Integer(), nullable=False, default=0),
        sa.Column('sensitive_data_accessed', sa.Boolean(), nullable=False, default=False),
        sa.Column('access_pattern', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('session_id', sa.String(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='audit'
    )
    
    # ============================================================================
    # PHASE 2: SECURITY ROLES AND POLICIES
    # ============================================================================
    
    # Create security context function for RLS
    op.execute("""
        CREATE OR REPLACE FUNCTION get_current_user_id() RETURNS INTEGER AS $$
        BEGIN
            -- Get user_id from current session context
            RETURN COALESCE(
                current_setting('app.current_user_id', true)::INTEGER,
                0  -- Default to 0 for system operations
            );
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)
    
    # Create function to set security context
    op.execute("""
        CREATE OR REPLACE FUNCTION set_security_context(
            p_user_id INTEGER,
            p_session_id TEXT DEFAULT NULL,
            p_service_name TEXT DEFAULT NULL
        ) RETURNS VOID AS $$
        BEGIN
            PERFORM set_config('app.current_user_id', p_user_id::TEXT, false);
            PERFORM set_config('app.current_session_id', COALESCE(p_session_id, ''), false);
            PERFORM set_config('app.current_service', COALESCE(p_service_name, 'unknown'), false);
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)
    
    # ============================================================================
    # PHASE 3: ROW-LEVEL SECURITY POLICIES
    # ============================================================================
    
    # Enable RLS on sensitive tables
    sensitive_tables = [
        'users', 'user_profiles', 'registered_devices', 'user_two_factor_auth',
        'passkey_credentials', 'chat_mode_sessions', 'simple_chat_context',
        'router_decision_log', 'unified_memory_vectors', 'consensus_memory_nodes',
        'agent_context_states', 'blackboard_events', 'tasks', 'documents',
        'document_chunks', 'chat_messages', 'chat_session_summaries'
    ]
    
    for table in sensitive_tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
    
    # Create RLS policies for user data isolation
    
    # Users table - users can only see their own record
    op.execute("""
        CREATE POLICY user_isolation_policy ON users
        FOR ALL TO PUBLIC
        USING (id = get_current_user_id())
        WITH CHECK (id = get_current_user_id());
    """)
    
    # User profiles - linked to user
    op.execute("""
        CREATE POLICY user_profile_isolation_policy ON user_profiles
        FOR ALL TO PUBLIC
        USING (user_id = get_current_user_id())
        WITH CHECK (user_id = get_current_user_id());
    """)
    
    # Registered devices - linked to user
    op.execute("""
        CREATE POLICY device_isolation_policy ON registered_devices
        FOR ALL TO PUBLIC
        USING (user_id = get_current_user_id())
        WITH CHECK (user_id = get_current_user_id());
    """)
    
    # Two-factor auth - linked to user
    op.execute("""
        CREATE POLICY tfa_isolation_policy ON user_two_factor_auth
        FOR ALL TO PUBLIC
        USING (user_id = get_current_user_id())
        WITH CHECK (user_id = get_current_user_id());
    """)
    
    # Passkey credentials - linked to user
    op.execute("""
        CREATE POLICY passkey_isolation_policy ON passkey_credentials
        FOR ALL TO PUBLIC
        USING (user_id = get_current_user_id())
        WITH CHECK (user_id = get_current_user_id());
    """)
    
    # Chat mode sessions - linked to user
    op.execute("""
        CREATE POLICY chat_session_isolation_policy ON chat_mode_sessions
        FOR ALL TO PUBLIC
        USING (user_id = get_current_user_id())
        WITH CHECK (user_id = get_current_user_id());
    """)
    
    # Simple chat context - linked to user via session
    op.execute("""
        CREATE POLICY chat_context_isolation_policy ON simple_chat_context
        FOR ALL TO PUBLIC
        USING (session_id IN (
            SELECT session_id FROM chat_mode_sessions 
            WHERE user_id = get_current_user_id()
        ))
        WITH CHECK (session_id IN (
            SELECT session_id FROM chat_mode_sessions 
            WHERE user_id = get_current_user_id()
        ));
    """)
    
    # Router decision log - linked to user via session
    op.execute("""
        CREATE POLICY router_log_isolation_policy ON router_decision_log
        FOR ALL TO PUBLIC
        USING (session_id IN (
            SELECT session_id FROM chat_mode_sessions 
            WHERE user_id = get_current_user_id()
        ))
        WITH CHECK (session_id IN (
            SELECT session_id FROM chat_mode_sessions 
            WHERE user_id = get_current_user_id()
        ));
    """)
    
    # Unified memory vectors - linked to user
    op.execute("""
        CREATE POLICY memory_vector_isolation_policy ON unified_memory_vectors
        FOR ALL TO PUBLIC
        USING (user_id = get_current_user_id())
        WITH CHECK (user_id = get_current_user_id());
    """)
    
    # Consensus memory nodes - linked to user
    op.execute("""
        CREATE POLICY consensus_memory_isolation_policy ON consensus_memory_nodes
        FOR ALL TO PUBLIC
        USING (user_id = get_current_user_id())
        WITH CHECK (user_id = get_current_user_id());
    """)
    
    # Agent context states - linked to user
    op.execute("""
        CREATE POLICY agent_context_isolation_policy ON agent_context_states
        FOR ALL TO PUBLIC
        USING (user_id = get_current_user_id())
        WITH CHECK (user_id = get_current_user_id());
    """)
    
    # Blackboard events - linked to user
    op.execute("""
        CREATE POLICY blackboard_isolation_policy ON blackboard_events
        FOR ALL TO PUBLIC
        USING (user_id = get_current_user_id())
        WITH CHECK (user_id = get_current_user_id());
    """)
    
    # Tasks - linked to user
    op.execute("""
        CREATE POLICY task_isolation_policy ON tasks
        FOR ALL TO PUBLIC
        USING (user_id = get_current_user_id())
        WITH CHECK (user_id = get_current_user_id());
    """)
    
    # Documents - linked to user
    op.execute("""
        CREATE POLICY document_isolation_policy ON documents
        FOR ALL TO PUBLIC
        USING (user_id = get_current_user_id())
        WITH CHECK (user_id = get_current_user_id());
    """)
    
    # Document chunks - linked to user via document
    op.execute("""
        CREATE POLICY document_chunk_isolation_policy ON document_chunks
        FOR ALL TO PUBLIC
        USING (document_id IN (
            SELECT id FROM documents 
            WHERE user_id = get_current_user_id()
        ))
        WITH CHECK (document_id IN (
            SELECT id FROM documents 
            WHERE user_id = get_current_user_id()
        ));
    """)
    
    # Chat messages - linked to user
    op.execute("""
        CREATE POLICY chat_message_isolation_policy ON chat_messages
        FOR ALL TO PUBLIC
        USING (user_id = get_current_user_id())
        WITH CHECK (user_id = get_current_user_id());
    """)
    
    # Chat session summaries - linked to user
    op.execute("""
        CREATE POLICY chat_summary_isolation_policy ON chat_session_summaries
        FOR ALL TO PUBLIC
        USING (user_id = get_current_user_id())
        WITH CHECK (user_id = get_current_user_id());
    """)
    
    # ============================================================================
    # PHASE 4: AUDIT TRIGGER FUNCTIONS
    # ============================================================================
    
    # Create comprehensive audit trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION audit.audit_trigger_function()
        RETURNS TRIGGER AS $$
        DECLARE
            audit_row audit.audit_log%ROWTYPE;
            include_values BOOLEAN = true;
            log_diffs BOOLEAN = true;
            h_old JSON;
            h_new JSON;
            excluded_cols TEXT[] = ARRAY[]::TEXT[];
        BEGIN
            -- Skip if this is an audit table operation
            IF TG_TABLE_SCHEMA = 'audit' THEN
                RETURN COALESCE(NEW, OLD);
            END IF;
            
            -- Initialize audit record
            audit_row.id = gen_random_uuid();
            audit_row.table_name = TG_TABLE_SCHEMA||'.'||TG_TABLE_NAME;
            audit_row.operation = TG_OP;
            audit_row.user_id = NULLIF(current_setting('app.current_user_id', true), '')::INTEGER;
            audit_row.session_id = NULLIF(current_setting('app.current_session_id', true), '');
            audit_row.ip_address = NULLIF(current_setting('app.current_ip', true), '');
            audit_row.user_agent = NULLIF(current_setting('app.current_user_agent', true), '');
            audit_row.application_name = NULLIF(current_setting('app.current_service', true), '');
            audit_row.transaction_id = txid_current();
            audit_row.created_at = NOW();
            
            -- Handle different operations
            IF TG_OP = 'UPDATE' THEN
                h_old = to_json(OLD);
                h_new = to_json(NEW);
                audit_row.old_values = h_old;
                audit_row.new_values = h_new;
                
                -- Get primary key for row identification
                IF TG_TABLE_NAME = 'users' THEN
                    audit_row.row_id = OLD.id::TEXT;
                ELSIF TG_TABLE_NAME IN ('documents', 'tasks', 'consensus_memory_nodes') THEN
                    audit_row.row_id = OLD.id::TEXT;
                ELSIF TG_TABLE_NAME IN ('registered_devices', 'passkey_credentials') THEN
                    audit_row.row_id = OLD.id::TEXT;
                ELSE
                    audit_row.row_id = COALESCE(OLD.id::TEXT, 'unknown');
                END IF;
                
                -- Track changed fields
                SELECT array_agg(key) INTO audit_row.changed_fields
                FROM json_each(h_old) old_vals
                JOIN json_each(h_new) new_vals ON old_vals.key = new_vals.key
                WHERE old_vals.value IS DISTINCT FROM new_vals.value;
                
            ELSIF TG_OP = 'DELETE' THEN
                audit_row.old_values = to_json(OLD);
                audit_row.row_id = COALESCE(OLD.id::TEXT, 'unknown');
                
            ELSIF TG_OP = 'INSERT' THEN
                audit_row.new_values = to_json(NEW);
                audit_row.row_id = COALESCE(NEW.id::TEXT, 'unknown');
                
            END IF;
            
            -- Add security context
            audit_row.security_context = json_build_object(
                'rls_active', (SELECT setting FROM pg_settings WHERE name = 'row_security'),
                'current_role', current_role,
                'session_user', session_user,
                'table_has_rls', EXISTS(
                    SELECT 1 FROM pg_policy 
                    WHERE schemaname = TG_TABLE_SCHEMA 
                    AND tablename = TG_TABLE_NAME
                )
            );
            
            -- Insert audit record
            INSERT INTO audit.audit_log VALUES (audit_row.*);
            
            -- Return appropriate value
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            ELSE
                RETURN NEW;
            END IF;
            
        EXCEPTION
            WHEN others THEN
                -- Log error but don't fail the operation
                INSERT INTO audit.security_violations (
                    violation_type, severity, violation_details, created_at
                ) VALUES (
                    'AUDIT_TRIGGER_ERROR', 'HIGH',
                    json_build_object(
                        'error_message', SQLERRM,
                        'error_state', SQLSTATE,
                        'table_name', TG_TABLE_SCHEMA||'.'||TG_TABLE_NAME,
                        'operation', TG_OP
                    ),
                    NOW()
                );
                
                -- Return appropriate value
                IF TG_OP = 'DELETE' THEN
                    RETURN OLD;
                ELSE
                    RETURN NEW;
                END IF;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)
    
    # Create security violation detection function
    op.execute("""
        CREATE OR REPLACE FUNCTION audit.check_security_violation()
        RETURNS TRIGGER AS $$
        DECLARE
            current_user_id INTEGER;
            violation_detected BOOLEAN = false;
            violation_details JSON;
        BEGIN
            current_user_id = get_current_user_id();
            
            -- Check for suspicious patterns
            IF TG_OP = 'SELECT' THEN
                -- Log excessive data access
                IF current_setting('app.rows_examined', true)::INTEGER > 1000 THEN
                    violation_detected = true;
                    violation_details = json_build_object(
                        'reason', 'excessive_data_access',
                        'rows_examined', current_setting('app.rows_examined', true)::INTEGER,
                        'threshold', 1000
                    );
                END IF;
            END IF;
            
            -- Check for cross-user access attempts
            IF TG_TABLE_NAME IN ('users', 'chat_mode_sessions', 'simple_chat_context') THEN
                IF TG_OP = 'UPDATE' OR TG_OP = 'DELETE' THEN
                    IF OLD.user_id != current_user_id AND current_user_id != 0 THEN
                        violation_detected = true;
                        violation_details = json_build_object(
                            'reason', 'cross_user_access_attempt',
                            'target_user_id', OLD.user_id,
                            'current_user_id', current_user_id,
                            'operation', TG_OP
                        );
                    END IF;
                END IF;
            END IF;
            
            -- Log violation if detected
            IF violation_detected THEN
                INSERT INTO audit.security_violations (
                    violation_type, severity, user_id, table_name, 
                    attempted_operation, violation_details, 
                    ip_address, blocked, created_at
                ) VALUES (
                    'UNAUTHORIZED_ACCESS', 'HIGH', current_user_id, 
                    TG_TABLE_SCHEMA||'.'||TG_TABLE_NAME, TG_OP,
                    violation_details,
                    NULLIF(current_setting('app.current_ip', true), ''),
                    true, NOW()
                );
                
                -- Block the operation for high-severity violations
                RAISE EXCEPTION 'Security violation detected: %', violation_details->>'reason';
            END IF;
            
            -- Return appropriate value
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            ELSE
                RETURN NEW;
            END IF;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)
    
    # ============================================================================
    # PHASE 5: APPLY AUDIT TRIGGERS
    # ============================================================================
    
    # Apply audit triggers to sensitive tables
    audit_tables = [
        'users', 'user_profiles', 'registered_devices', 'user_two_factor_auth',
        'passkey_credentials', 'chat_mode_sessions', 'simple_chat_context',
        'router_decision_log', 'unified_memory_vectors', 'consensus_memory_nodes',
        'agent_context_states', 'blackboard_events', 'tasks', 'documents',
        'chat_messages', 'chat_session_summaries'
    ]
    
    for table in audit_tables:
        # Create audit trigger
        op.execute(f"""
            CREATE TRIGGER audit_trigger_{table}
            AFTER INSERT OR UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION audit.audit_trigger_function();
        """)
        
        # Create security violation check trigger
        op.execute(f"""
            CREATE TRIGGER security_check_{table}
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION audit.check_security_violation();
        """)
    
    # ============================================================================
    # PHASE 6: DATA RETENTION AND PRIVACY CONTROLS
    # ============================================================================
    
    # Create data retention policy table
    op.create_table('data_retention_policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('table_name', sa.String(64), nullable=False),
        sa.Column('retention_period_days', sa.Integer(), nullable=False),
        sa.Column('policy_type', sa.String(20), nullable=False),  # 'ARCHIVE', 'DELETE', 'ANONYMIZE'
        sa.Column('conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('table_name', 'policy_type', name='_table_policy_type_uc')
    )
    
    # Create function for data anonymization
    op.execute("""
        CREATE OR REPLACE FUNCTION anonymize_user_data(target_user_id INTEGER)
        RETURNS VOID AS $$
        BEGIN
            -- Anonymize user profile data
            UPDATE users SET 
                email = 'anonymized_' || id || '@deleted.user',
                hashed_password = 'ANONYMIZED',
                mission_statement = NULL,
                personal_goals = NULL,
                work_style_preferences = NULL,
                productivity_patterns = NULL,
                interview_insights = NULL
            WHERE id = target_user_id;
            
            -- Anonymize user profile
            UPDATE user_profiles SET
                first_name = 'Anonymized',
                last_name = 'User',
                display_name = 'Anonymized User',
                phone_number = NULL,
                personal_address = NULL,
                work_phone = NULL,
                work_email = NULL,
                work_address = NULL,
                emergency_contact = NULL,
                bio = NULL,
                website = NULL,
                linkedin = NULL,
                twitter = NULL,
                github = NULL
            WHERE user_id = target_user_id;
            
            -- Remove sensitive context data
            UPDATE simple_chat_context SET
                context_value = '{"anonymized": true}'::jsonb
            WHERE session_id IN (
                SELECT session_id FROM chat_mode_sessions WHERE user_id = target_user_id
            );
            
            -- Log anonymization
            INSERT INTO audit.audit_log (
                table_name, operation, user_id, new_values, created_at
            ) VALUES (
                'data_anonymization', 'UPDATE', target_user_id,
                json_build_object('anonymized_at', NOW(), 'target_user_id', target_user_id),
                NOW()
            );
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)
    
    # ============================================================================
    # PHASE 7: PERFORMANCE OPTIMIZATION WITH SECURITY
    # ============================================================================
    
    # Create indexes for audit tables
    op.create_index('idx_audit_log_user_time', 'audit_log', ['user_id', 'created_at'], schema='audit')
    op.create_index('idx_audit_log_table_operation', 'audit_log', ['table_name', 'operation'], schema='audit')
    op.create_index('idx_audit_log_transaction', 'audit_log', ['transaction_id'], schema='audit')
    op.create_index('idx_audit_log_session', 'audit_log', ['session_id'], schema='audit')
    op.create_index('idx_audit_log_security_gin', 'audit_log', ['security_context'], postgresql_using='gin', schema='audit')
    
    op.create_index('idx_security_violations_severity', 'security_violations', ['severity', 'created_at'], schema='audit')
    op.create_index('idx_security_violations_user', 'security_violations', ['user_id', 'resolved'], schema='audit')
    op.create_index('idx_security_violations_type', 'security_violations', ['violation_type'], schema='audit')
    
    op.create_index('idx_data_access_log_user_service', 'data_access_log', ['user_id', 'service_name', 'created_at'], schema='audit')
    op.create_index('idx_data_access_log_sensitive', 'data_access_log', ['sensitive_data_accessed', 'created_at'], schema='audit')
    
    # ============================================================================
    # PHASE 8: VECTOR DATABASE SECURITY INTEGRATION
    # ============================================================================
    
    # Create Qdrant access control table
    op.create_table('qdrant_access_control',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('collection_name', sa.String(100), nullable=False),
        sa.Column('access_level', sa.String(20), nullable=False),  # 'READ', 'WRITE', 'DELETE', 'ADMIN'
        sa.Column('conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'collection_name', 'access_level', name='_user_collection_access_uc')
    )
    
    # Create vector operation audit function
    op.execute("""
        CREATE OR REPLACE FUNCTION audit.log_vector_operation(
            p_user_id INTEGER,
            p_operation TEXT,
            p_collection_name TEXT,
            p_point_ids TEXT[],
            p_metadata JSONB DEFAULT NULL
        ) RETURNS VOID AS $$
        BEGIN
            INSERT INTO audit.data_access_log (
                user_id, service_name, access_type, table_name,
                row_count, sensitive_data_accessed, access_pattern,
                session_id, created_at
            ) VALUES (
                p_user_id, 'qdrant', p_operation, 'vector_' || p_collection_name,
                COALESCE(array_length(p_point_ids, 1), 0),
                true,  -- Vector data is considered sensitive
                json_build_object(
                    'collection', p_collection_name,
                    'point_ids', p_point_ids,
                    'metadata', p_metadata
                ),
                NULLIF(current_setting('app.current_session_id', true), ''),
                NOW()
            );
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)
    
    # ============================================================================
    # PHASE 9: DEFAULT SECURITY POLICIES
    # ============================================================================
    
    # Insert default data retention policies
    op.execute("""
        INSERT INTO data_retention_policies (table_name, retention_period_days, policy_type, conditions) VALUES
        ('audit.audit_log', 2555, 'ARCHIVE', '{"high_severity_retain": 3650}'),  -- 7 years for audit, 10 for high severity
        ('audit.security_violations', 3650, 'ARCHIVE', '{"resolved_only": true}'),  -- 10 years
        ('audit.data_access_log', 365, 'ARCHIVE', '{"sensitive_data_retain": 1095}'),  -- 1 year, 3 for sensitive
        ('chat_messages', 1095, 'ANONYMIZE', '{"user_requested_only": true}'),  -- 3 years
        ('chat_session_summaries', 1825, 'ARCHIVE', '{}'),  -- 5 years
        ('simple_chat_context', 90, 'DELETE', '{"temporary_context_only": true}'),  -- 90 days for temporary
        ('router_decision_log', 365, 'ARCHIVE', '{}'),  -- 1 year
        ('device_login_attempts', 180, 'DELETE', '{"failed_attempts_only": true}');  -- 6 months
    """)
    
    # Create default Qdrant access controls for admin users
    op.execute("""
        INSERT INTO qdrant_access_control (user_id, collection_name, access_level, conditions)
        SELECT id, 'default', 'ADMIN', '{}'::jsonb
        FROM users WHERE role = 'admin' AND is_active = true;
    """)
    
    # ============================================================================
    # PHASE 10: SECURITY MONITORING FUNCTIONS
    # ============================================================================
    
    # Create function to check for security anomalies
    op.execute("""
        CREATE OR REPLACE FUNCTION audit.detect_security_anomalies()
        RETURNS TABLE(
            anomaly_type TEXT,
            severity TEXT,
            details JSONB,
            detected_at TIMESTAMPTZ
        ) AS $$
        BEGIN
            -- Detect unusual data access patterns
            RETURN QUERY
            SELECT 
                'UNUSUAL_ACCESS_PATTERN'::TEXT,
                'MEDIUM'::TEXT,
                json_build_object(
                    'user_id', dal.user_id,
                    'access_count', COUNT(*),
                    'tables_accessed', array_agg(DISTINCT dal.table_name),
                    'time_window', '1 hour'
                ),
                NOW()
            FROM audit.data_access_log dal
            WHERE dal.created_at >= NOW() - INTERVAL '1 hour'
            GROUP BY dal.user_id
            HAVING COUNT(*) > 100;  -- More than 100 operations per hour
            
            -- Detect failed security violations
            RETURN QUERY
            SELECT 
                'SECURITY_VIOLATION_SPIKE'::TEXT,
                'HIGH'::TEXT,
                json_build_object(
                    'violation_count', COUNT(*),
                    'violation_types', array_agg(DISTINCT sv.violation_type),
                    'time_window', '15 minutes'
                ),
                NOW()
            FROM audit.security_violations sv
            WHERE sv.created_at >= NOW() - INTERVAL '15 minutes'
              AND sv.blocked = true
            HAVING COUNT(*) > 5;  -- More than 5 violations in 15 minutes
            
            -- Detect cross-user access attempts
            RETURN QUERY
            SELECT 
                'CROSS_USER_ACCESS'::TEXT,
                'CRITICAL'::TEXT,
                json_build_object(
                    'source_user_id', al.user_id,
                    'target_data', al.old_values,
                    'operation', al.operation,
                    'table', al.table_name
                ),
                al.created_at
            FROM audit.audit_log al
            WHERE al.created_at >= NOW() - INTERVAL '1 hour'
              AND al.security_context->>'violation_detected' = 'true';
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)
    
    # Create cleanup function for old audit data
    op.execute("""
        CREATE OR REPLACE FUNCTION audit.cleanup_old_data()
        RETURNS INTEGER AS $$
        DECLARE
            rows_deleted INTEGER = 0;
            policy_record RECORD;
        BEGIN
            -- Process each retention policy
            FOR policy_record IN 
                SELECT * FROM data_retention_policies WHERE is_active = true
            LOOP
                IF policy_record.policy_type = 'DELETE' THEN
                    EXECUTE format('DELETE FROM %I WHERE created_at < NOW() - INTERVAL ''%s days''',
                        policy_record.table_name, policy_record.retention_period_days);
                    GET DIAGNOSTICS rows_deleted = ROW_COUNT;
                    
                ELSIF policy_record.policy_type = 'ANONYMIZE' THEN
                    -- Custom anonymization logic would go here
                    -- For now, just log the requirement
                    INSERT INTO audit.audit_log (table_name, operation, new_values, created_at)
                    VALUES (policy_record.table_name, 'ANONYMIZE_REQUIRED', 
                           json_build_object('policy_id', policy_record.id, 'due_date', 
                           NOW() - (policy_record.retention_period_days || ' days')::INTERVAL),
                           NOW());
                END IF;
                
                -- Update last run timestamp
                UPDATE data_retention_policies 
                SET last_run_at = NOW() 
                WHERE id = policy_record.id;
            END LOOP;
            
            RETURN rows_deleted;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)


def downgrade() -> None:
    """Remove secure database migration."""
    
    # Drop triggers first
    audit_tables = [
        'users', 'user_profiles', 'registered_devices', 'user_two_factor_auth',
        'passkey_credentials', 'chat_mode_sessions', 'simple_chat_context',
        'router_decision_log', 'unified_memory_vectors', 'consensus_memory_nodes',
        'agent_context_states', 'blackboard_events', 'tasks', 'documents',
        'chat_messages', 'chat_session_summaries'
    ]
    
    for table in audit_tables:
        op.execute(f"DROP TRIGGER IF EXISTS audit_trigger_{table} ON {table};")
        op.execute(f"DROP TRIGGER IF EXISTS security_check_{table} ON {table};")
    
    # Disable RLS on tables
    sensitive_tables = [
        'users', 'user_profiles', 'registered_devices', 'user_two_factor_auth',
        'passkey_credentials', 'chat_mode_sessions', 'simple_chat_context',
        'router_decision_log', 'unified_memory_vectors', 'consensus_memory_nodes',
        'agent_context_states', 'blackboard_events', 'tasks', 'documents',
        'document_chunks', 'chat_messages', 'chat_session_summaries'
    ]
    
    for table in sensitive_tables:
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
        op.execute(f"DROP POLICY IF EXISTS {table}_isolation_policy ON {table};")
    
    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS audit.cleanup_old_data();")
    op.execute("DROP FUNCTION IF EXISTS audit.detect_security_anomalies();")
    op.execute("DROP FUNCTION IF EXISTS audit.log_vector_operation(INTEGER, TEXT, TEXT, TEXT[], JSONB);")
    op.execute("DROP FUNCTION IF EXISTS anonymize_user_data(INTEGER);")
    op.execute("DROP FUNCTION IF EXISTS audit.check_security_violation();")
    op.execute("DROP FUNCTION IF EXISTS audit.audit_trigger_function();")
    op.execute("DROP FUNCTION IF EXISTS set_security_context(INTEGER, TEXT, TEXT);")
    op.execute("DROP FUNCTION IF EXISTS get_current_user_id();")
    
    # Drop tables
    op.drop_table('qdrant_access_control')
    op.drop_table('data_retention_policies')
    op.drop_table('data_access_log', schema='audit')
    op.drop_table('security_violations', schema='audit')
    op.drop_table('audit_log', schema='audit')
    
    # Drop types and schema
    op.execute("DROP TYPE IF EXISTS audit.audit_operation;")
    op.execute("DROP SCHEMA IF EXISTS audit CASCADE;")