"""Add OAuth tokens table for Google services integration

Revision ID: 4a8b9c2d1e3f
Revises: 3d2f4e5a6b7c
Create Date: 2025-07-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4a8b9c2d1e3f'
down_revision = '3d2f4e5a6b7c'
branch_labels = None
depends_on = None


def upgrade():
    # Create the GoogleService enum (idempotent)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE googleservice AS ENUM ('calendar', 'drive', 'gmail');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create user_oauth_tokens table (idempotent)
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_tables = inspector.get_table_names()
    
    if 'user_oauth_tokens' not in existing_tables:
        google_service_enum = postgresql.ENUM(
            'calendar', 'drive', 'gmail', 
            name='googleservice'
        )
        
        op.create_table('user_oauth_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('service', google_service_enum, nullable=False),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expiry', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scope', sa.Text(), nullable=True),
        sa.Column('service_user_id', sa.String(), nullable=True),
        sa.Column('service_email', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'service', name='_user_service_token')
        )
        op.create_index(op.f('ix_user_oauth_tokens_id'), 'user_oauth_tokens', ['id'], unique=False)
        op.create_index(op.f('ix_user_oauth_tokens_user_id'), 'user_oauth_tokens', ['user_id'], unique=False)


def downgrade():
    # Drop the table and indexes
    op.drop_index(op.f('ix_user_oauth_tokens_user_id'), table_name='user_oauth_tokens')
    op.drop_index(op.f('ix_user_oauth_tokens_id'), table_name='user_oauth_tokens')
    op.drop_table('user_oauth_tokens')
    
    # Drop the enum
    google_service_enum = postgresql.ENUM(
        'calendar', 'drive', 'gmail', 
        name='googleservice'
    )
    google_service_enum.drop(op.get_bind())