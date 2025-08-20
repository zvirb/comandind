"""Add user profile table

Revision ID: 6e8f9a0b1c2d
Revises: 5b7c8d9e2f4a
Create Date: 2025-07-17 22:06:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '6e8f9a0b1c2d'
down_revision = '7f3e9d2c4b8a'
branch_labels = None
depends_on = None


def upgrade():
    # Create user_profiles table
    op.create_table('user_profiles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('first_name', sa.String(), nullable=True),
    sa.Column('last_name', sa.String(), nullable=True),
    sa.Column('display_name', sa.String(), nullable=True),
    sa.Column('date_of_birth', sa.String(), nullable=True),
    sa.Column('phone_number', sa.String(), nullable=True),
    sa.Column('alternate_phone', sa.String(), nullable=True),
    sa.Column('personal_address', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('job_title', sa.String(), nullable=True),
    sa.Column('company', sa.String(), nullable=True),
    sa.Column('department', sa.String(), nullable=True),
    sa.Column('work_phone', sa.String(), nullable=True),
    sa.Column('work_email', sa.String(), nullable=True),
    sa.Column('work_address', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('preferred_contact_method', sa.String(), nullable=True),
    sa.Column('emergency_contact', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('bio', sa.Text(), nullable=True),
    sa.Column('website', sa.String(), nullable=True),
    sa.Column('linkedin', sa.String(), nullable=True),
    sa.Column('twitter', sa.String(), nullable=True),
    sa.Column('github', sa.String(), nullable=True),
    sa.Column('timezone', sa.String(), nullable=True),
    sa.Column('language', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_user_profiles_id'), 'user_profiles', ['id'], unique=False)
    op.create_index(op.f('ix_user_profiles_user_id'), 'user_profiles', ['user_id'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index(op.f('ix_user_profiles_user_id'), table_name='user_profiles')
    op.drop_index(op.f('ix_user_profiles_id'), table_name='user_profiles')
    
    # Drop table
    op.drop_table('user_profiles')