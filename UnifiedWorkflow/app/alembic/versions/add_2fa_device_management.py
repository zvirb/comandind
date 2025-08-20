"""Add 2FA and device management tables

Revision ID: add_2fa_device_management
Revises: add_password_reset_tokens
Create Date: 2025-07-28 07:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_2fa_device_management'
down_revision = 'd1e2f3g4h5i6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add 2FA and device management tables."""
    
    # Enums are already created in the database, so we just create tables
    
    # Create registered_devices table
    op.create_table(
        'registered_devices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('device_name', sa.String(255), nullable=False),
        sa.Column('device_fingerprint', sa.String(512), nullable=False, unique=True),
        sa.Column('user_agent', sa.Text(), nullable=False),
        sa.Column('device_type', sa.Enum('desktop', 'mobile', 'tablet', 'unknown', name='devicetype'), nullable=False, server_default='unknown'),
        sa.Column('security_level', sa.Enum('always_login', 'auto_login', 'always_2fa', name='devicesecuritylevel'), nullable=False, server_default='always_login'),
        sa.Column('is_remembered', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('remember_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_ip_address', sa.String(45), nullable=True),
        sa.Column('location_info', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_trusted', sa.Boolean(), nullable=False, server_default='false'),
    )
    
    # Create user_two_factor_auth table
    op.create_table(
        'user_two_factor_auth',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, unique=True, index=True),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('default_method', sa.Enum('totp', 'passkey', 'backup_codes', name='twofactormethod'), nullable=True),
        sa.Column('totp_secret', sa.String(32), nullable=True),
        sa.Column('totp_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('totp_backup_codes', sa.JSON(), nullable=True),
        sa.Column('passkey_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('recovery_email', sa.String(255), nullable=True),
        sa.Column('recovery_phone', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    
    # Create passkey_credentials table
    op.create_table(
        'passkey_credentials',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('credential_id', sa.String(1024), nullable=False, unique=True),
        sa.Column('public_key', sa.Text(), nullable=False),
        sa.Column('sign_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('authenticator_type', sa.String(50), nullable=True),
        sa.Column('backup_eligible', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('backup_state', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('registered_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('registered_devices.id'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
    )
    
    # Create two_factor_challenges table
    op.create_table(
        'two_factor_challenges',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('challenge_type', sa.Enum('totp', 'passkey', 'backup_codes', name='twofactormethod'), nullable=False),
        sa.Column('challenge_data', sa.JSON(), nullable=False),
        sa.Column('session_token', sa.String(255), nullable=False, unique=True),
        sa.Column('device_fingerprint', sa.String(512), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_completed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    
    # Create device_login_attempts table
    op.create_table(
        'device_login_attempts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True, index=True),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('registered_devices.id'), nullable=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('device_fingerprint', sa.String(512), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=False),
        sa.Column('user_agent', sa.Text(), nullable=False),
        sa.Column('was_successful', sa.Boolean(), nullable=False),
        sa.Column('failure_reason', sa.String(255), nullable=True),
        sa.Column('used_2fa', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('two_factor_method', sa.Enum('totp', 'passkey', 'backup_codes', name='twofactormethod'), nullable=True),
        sa.Column('attempted_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    
    # Create indexes
    op.create_index('ix_registered_devices_device_fingerprint', 'registered_devices', ['device_fingerprint'])
    op.create_index('ix_passkey_credentials_credential_id', 'passkey_credentials', ['credential_id'])
    op.create_index('ix_two_factor_challenges_session_token', 'two_factor_challenges', ['session_token'])
    op.create_index('ix_device_login_attempts_email', 'device_login_attempts', ['email'])
    op.create_index('ix_device_login_attempts_attempted_at', 'device_login_attempts', ['attempted_at'])


def downgrade() -> None:
    """Drop 2FA and device management tables."""
    
    # Drop indexes first
    op.drop_index('ix_device_login_attempts_attempted_at', 'device_login_attempts')
    op.drop_index('ix_device_login_attempts_email', 'device_login_attempts')
    op.drop_index('ix_two_factor_challenges_session_token', 'two_factor_challenges')
    op.drop_index('ix_passkey_credentials_credential_id', 'passkey_credentials')
    op.drop_index('ix_registered_devices_device_fingerprint', 'registered_devices')
    
    # Drop tables
    op.drop_table('device_login_attempts')
    op.drop_table('two_factor_challenges')
    op.drop_table('passkey_credentials')
    op.drop_table('user_two_factor_auth')
    op.drop_table('registered_devices')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS devicetype')
    op.execute('DROP TYPE IF EXISTS twofactormethod')
    op.execute('DROP TYPE IF EXISTS devicesecuritylevel')