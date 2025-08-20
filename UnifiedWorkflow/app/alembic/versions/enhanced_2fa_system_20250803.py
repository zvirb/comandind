"""Enhanced 2FA system with comprehensive multi-method support

Revision ID: enhanced_2fa_system_20250803
Revises: secure_database_migration_20250803
Create Date: 2025-08-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'enhanced_2fa_system_20250803'
down_revision = 'secure_database_migration_20250803'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add enhanced 2FA system tables and enums."""
    
    # Create new enum types for enhanced 2FA system
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE twofactorpolicytype AS ENUM ('mandatory_all', 'mandatory_admin', 'optional', 'role_based');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE twofactorgracestatus AS ENUM ('active', 'expired', 'completed', 'extended');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE smsprovider AS ENUM ('twilio', 'aws_sns', 'nexmo', 'custom');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE emailprovider AS ENUM ('smtp', 'sendgrid', 'aws_ses', 'mailgun');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE twofactorauditaction AS ENUM (
                'setup_initiated', 'setup_completed', 'setup_failed',
                'authentication_success', 'authentication_failed',
                'method_disabled', 'backup_codes_generated', 'backup_code_used',
                'admin_override', 'grace_period_extended'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create two_factor_policies table
    op.create_table(
        'two_factor_policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('policy_type', sa.Enum(name='twofactorpolicytype'), nullable=False, server_default='mandatory_all'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('grace_period_days', sa.Integer(), nullable=False, server_default='7'),
        sa.Column('grace_period_warning_days', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('max_grace_extensions', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('allow_admin_override', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('admin_override_duration_hours', sa.Integer(), nullable=False, server_default='24'),
        sa.Column('require_admin_approval_for_disable', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('minimum_methods_required', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('allowed_methods', postgresql.JSONB(), nullable=False, server_default='["totp", "passkey", "backup_codes"]'),
        sa.Column('preferred_method_order', postgresql.JSONB(), nullable=False, server_default='["passkey", "totp", "backup_codes"]'),
        sa.Column('require_backup_method', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('session_timeout_minutes', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('remember_device_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    
    # Create user_two_factor_grace_periods table
    op.create_table(
        'user_two_factor_grace_periods',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('status', sa.Enum(name='twofactorgracestatus'), nullable=False, server_default='active'),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('extension_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('warning_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('final_warning_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('extended_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('extension_reason', sa.Text(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    
    # Create user_sms_two_factor table
    op.create_table(
        'user_sms_two_factor',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, unique=True, index=True),
        sa.Column('phone_number', sa.String(20), nullable=False),
        sa.Column('country_code', sa.String(5), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('verification_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('provider', sa.Enum(name='smsprovider'), nullable=False, server_default='twilio'),
        sa.Column('provider_config', postgresql.JSONB(), nullable=True),
        sa.Column('daily_sms_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('daily_sms_reset_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('max_daily_sms', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('last_code_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_attempts_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    
    # Create user_email_two_factor table
    op.create_table(
        'user_email_two_factor',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, unique=True, index=True),
        sa.Column('email_address', sa.String(255), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('verification_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('provider', sa.Enum(name='emailprovider'), nullable=False, server_default='smtp'),
        sa.Column('provider_config', postgresql.JSONB(), nullable=True),
        sa.Column('daily_email_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('daily_email_reset_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('max_daily_emails', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('last_code_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_attempts_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    
    # Create two_factor_audit_log table
    op.create_table(
        'two_factor_audit_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True, index=True),
        sa.Column('action', sa.Enum(name='twofactorauditaction'), nullable=False),
        sa.Column('method_type', sa.String(50), nullable=True),
        sa.Column('session_id', sa.String(255), nullable=True),
        sa.Column('device_fingerprint', sa.String(512), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('additional_data', postgresql.JSONB(), nullable=True),
        sa.Column('performed_by_admin', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('admin_reason', sa.Text(), nullable=True),
        sa.Column('risk_score', sa.Float(), nullable=True),
        sa.Column('risk_factors', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    
    # Create two_factor_verification_codes table
    op.create_table(
        'two_factor_verification_codes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('code_hash', sa.String(255), nullable=False),
        sa.Column('method_type', sa.String(50), nullable=False),
        sa.Column('destination', sa.String(255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_used', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    
    # Create two_factor_admin_overrides table
    op.create_table(
        'two_factor_admin_overrides',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('admin_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('override_type', sa.String(50), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('requires_approval', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('approved_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_emergency', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('emergency_contact_notified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    
    # Create two_factor_compliance_reports table
    op.create_table(
        'two_factor_compliance_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('report_type', sa.String(50), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('total_users', sa.Integer(), nullable=False),
        sa.Column('users_with_2fa', sa.Integer(), nullable=False),
        sa.Column('users_in_grace_period', sa.Integer(), nullable=False),
        sa.Column('users_overdue', sa.Integer(), nullable=False),
        sa.Column('totp_users', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('passkey_users', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sms_users', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('email_users', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_2fa_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('admin_overrides_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('backup_codes_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('compliance_details', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('recommendations', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('generated_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    
    # Create user_two_factor_settings table
    op.create_table(
        'user_two_factor_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, unique=True, index=True),
        sa.Column('preferred_method', sa.String(50), nullable=True),
        sa.Column('fallback_method', sa.String(50), nullable=True),
        sa.Column('remember_device_preference', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notify_on_new_device', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notify_on_failed_attempt', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notification_email', sa.String(255), nullable=True),
        sa.Column('require_2fa_for_sensitive_actions', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('auto_logout_minutes', sa.Integer(), nullable=True),
        sa.Column('allow_backup_codes', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('setup_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_method_change', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_method_changes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('custom_settings', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    
    # Add refresh_token_hash column to registered_devices if it doesn't exist
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE registered_devices ADD COLUMN refresh_token_hash VARCHAR(512);
        EXCEPTION
            WHEN duplicate_column THEN null;
        END $$;
    """)
    
    # Create indexes for performance
    op.create_index('ix_two_factor_policies_policy_type', 'two_factor_policies', ['policy_type'])
    op.create_index('ix_two_factor_policies_is_active', 'two_factor_policies', ['is_active'])
    
    op.create_index('ix_user_two_factor_grace_periods_status', 'user_two_factor_grace_periods', ['status'])
    op.create_index('ix_user_two_factor_grace_periods_end_date', 'user_two_factor_grace_periods', ['end_date'])
    
    op.create_index('ix_two_factor_audit_log_action', 'two_factor_audit_log', ['action'])
    op.create_index('ix_two_factor_audit_log_created_at', 'two_factor_audit_log', ['created_at'])
    op.create_index('ix_two_factor_audit_log_success', 'two_factor_audit_log', ['success'])
    
    op.create_index('ix_two_factor_verification_codes_expires_at', 'two_factor_verification_codes', ['expires_at'])
    op.create_index('ix_two_factor_verification_codes_method_type', 'two_factor_verification_codes', ['method_type'])
    
    op.create_index('ix_two_factor_admin_overrides_is_active', 'two_factor_admin_overrides', ['is_active'])
    op.create_index('ix_two_factor_admin_overrides_end_time', 'two_factor_admin_overrides', ['end_time'])
    
    op.create_index('ix_two_factor_compliance_reports_report_type', 'two_factor_compliance_reports', ['report_type'])
    op.create_index('ix_two_factor_compliance_reports_period_start', 'two_factor_compliance_reports', ['period_start'])
    
    # Create a default 2FA policy
    op.execute("""
        INSERT INTO two_factor_policies (id, policy_type, is_active, grace_period_days, created_at, updated_at)
        VALUES (gen_random_uuid(), 'mandatory_all', true, 7, NOW(), NOW())
        ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    """Remove enhanced 2FA system tables and enums."""
    
    # Drop indexes first
    op.drop_index('ix_two_factor_compliance_reports_period_start', 'two_factor_compliance_reports')
    op.drop_index('ix_two_factor_compliance_reports_report_type', 'two_factor_compliance_reports')
    
    op.drop_index('ix_two_factor_admin_overrides_end_time', 'two_factor_admin_overrides')
    op.drop_index('ix_two_factor_admin_overrides_is_active', 'two_factor_admin_overrides')
    
    op.drop_index('ix_two_factor_verification_codes_method_type', 'two_factor_verification_codes')
    op.drop_index('ix_two_factor_verification_codes_expires_at', 'two_factor_verification_codes')
    
    op.drop_index('ix_two_factor_audit_log_success', 'two_factor_audit_log')
    op.drop_index('ix_two_factor_audit_log_created_at', 'two_factor_audit_log')
    op.drop_index('ix_two_factor_audit_log_action', 'two_factor_audit_log')
    
    op.drop_index('ix_user_two_factor_grace_periods_end_date', 'user_two_factor_grace_periods')
    op.drop_index('ix_user_two_factor_grace_periods_status', 'user_two_factor_grace_periods')
    
    op.drop_index('ix_two_factor_policies_is_active', 'two_factor_policies')
    op.drop_index('ix_two_factor_policies_policy_type', 'two_factor_policies')
    
    # Drop tables
    op.drop_table('user_two_factor_settings')
    op.drop_table('two_factor_compliance_reports')
    op.drop_table('two_factor_admin_overrides')
    op.drop_table('two_factor_verification_codes')
    op.drop_table('two_factor_audit_log')
    op.drop_table('user_email_two_factor')
    op.drop_table('user_sms_two_factor')
    op.drop_table('user_two_factor_grace_periods')
    op.drop_table('two_factor_policies')
    
    # Remove refresh_token_hash column from registered_devices
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE registered_devices DROP COLUMN IF EXISTS refresh_token_hash;
        EXCEPTION
            WHEN undefined_column THEN null;
        END $$;
    """)
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS twofactorauditaction')
    op.execute('DROP TYPE IF EXISTS emailprovider')
    op.execute('DROP TYPE IF EXISTS smsprovider')
    op.execute('DROP TYPE IF EXISTS twofactorgracestatus')
    op.execute('DROP TYPE IF EXISTS twofactorpolicytype')