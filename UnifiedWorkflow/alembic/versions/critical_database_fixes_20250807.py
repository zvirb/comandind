"""Critical database fixes for Phase 2 - Profile validation, auth sessions, calendar integrity

Revision ID: critical_db_fixes_20250807
Revises: 3d2f4e5a6b7c
Create Date: 2025-08-07 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = 'critical_db_fixes_20250807'
down_revision = '3d2f4e5a6b7c'
branch_labels = None
depends_on = None


def upgrade():
    """
    Apply critical database fixes:
    1. Profile data validation constraints
    2. Calendar relationship integrity fixes  
    3. Authentication session cleanup and optimization
    4. OAuth token validation constraints
    """
    
    # ========================================
    # 1. PROFILE DATA VALIDATION CONSTRAINTS
    # ========================================
    
    print("Adding profile validation constraints...")
    
    # Add email format validation constraint
    op.execute(text("""
        ALTER TABLE user_profiles 
        ADD CONSTRAINT check_email_format 
        CHECK (work_email IS NULL OR work_email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}$')
    """))
    
    # Add phone number format validation constraint
    op.execute(text("""
        ALTER TABLE user_profiles 
        ADD CONSTRAINT check_phone_format 
        CHECK (phone_number IS NULL OR phone_number ~ '^\\+?[1-9]\\d{1,14}$')
    """))
    
    # Add alternate phone format validation
    op.execute(text("""
        ALTER TABLE user_profiles 
        ADD CONSTRAINT check_alternate_phone_format 
        CHECK (alternate_phone IS NULL OR alternate_phone ~ '^\\+?[1-9]\\d{1,14}$')
    """))
    
    # Add work phone format validation  
    op.execute(text("""
        ALTER TABLE user_profiles 
        ADD CONSTRAINT check_work_phone_format 
        CHECK (work_phone IS NULL OR work_phone ~ '^\\+?[1-9]\\d{1,14}$')
    """))
    
    # Add profile lookup optimization index
    op.create_index(
        'idx_user_profiles_lookup', 
        'user_profiles', 
        ['user_id', 'created_at'],
        if_not_exists=True
    )
    
    # ========================================
    # 2. CALENDAR RELATIONSHIP INTEGRITY
    # ========================================
    
    print("Fixing calendar relationship integrity...")
    
    # Drop existing foreign key constraint if exists
    try:
        op.drop_constraint('events_calendar_id_fkey', 'events', type_='foreignkey')
    except Exception:
        pass  # Constraint might not exist
    
    # Add proper cascade delete foreign key
    op.create_foreign_key(
        'events_calendar_id_fkey',
        'events', 'calendars',
        ['calendar_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Add calendar events optimization index
    op.create_index(
        'idx_events_calendar_time',
        'events',
        ['calendar_id', 'start_time', 'end_time'],
        if_not_exists=True
    )
    
    # ========================================
    # 3. OAUTH TOKEN VALIDATION
    # ========================================
    
    print("Adding OAuth token validation constraints...")
    
    # Add token expiry validation constraint
    op.execute(text("""
        ALTER TABLE user_oauth_tokens 
        ADD CONSTRAINT check_token_expiry 
        CHECK (token_expiry IS NULL OR token_expiry > created_at)
    """))
    
    # Add service email format validation
    op.execute(text("""
        ALTER TABLE user_oauth_tokens 
        ADD CONSTRAINT check_service_email_format 
        CHECK (service_email IS NULL OR service_email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}$')
    """))
    
    # ========================================
    # 4. AUTHENTICATION SESSION CLEANUP
    # ========================================
    
    print("Cleaning up authentication sessions...")
    
    # Remove expired authentication sessions
    op.execute(text("""
        DELETE FROM authentication_sessions 
        WHERE expires_at < NOW()
    """))
    
    # Remove expired two factor challenges if table exists
    try:
        op.execute(text("""
            DELETE FROM two_factor_challenges 
            WHERE expires_at < NOW()
        """))
    except Exception:
        pass  # Table might not exist
    
    # ========================================
    # 5. PERFORMANCE OPTIMIZATION INDEXES
    # ========================================
    
    print("Adding performance optimization indexes...")
    
    # Active authentication sessions index
    op.create_index(
        'idx_auth_sessions_active',
        'authentication_sessions',
        ['user_id', 'is_active'],
        postgresql_where=sa.text('expires_at > NOW()'),
        if_not_exists=True
    )
    
    # User OAuth tokens lookup optimization
    op.create_index(
        'idx_oauth_tokens_service_lookup',
        'user_oauth_tokens',
        ['user_id', 'service', 'created_at'],
        if_not_exists=True
    )
    
    # Events time range queries optimization
    op.create_index(
        'idx_events_time_range',
        'events',
        ['start_time', 'end_time', 'calendar_id'],
        if_not_exists=True
    )
    
    # User profile completeness check index
    op.create_index(
        'idx_user_profiles_completeness',
        'user_profiles',
        ['user_id'],
        postgresql_where=sa.text('first_name IS NOT NULL AND last_name IS NOT NULL'),
        if_not_exists=True
    )
    
    # ========================================
    # 6. DATA INTEGRITY IMPROVEMENTS
    # ========================================
    
    print("Adding data integrity improvements...")
    
    # Ensure user profiles have unique user_id (should already exist but let's be sure)
    try:
        op.create_unique_constraint('uq_user_profiles_user_id', 'user_profiles', ['user_id'])
    except Exception:
        pass  # Constraint likely already exists
    
    # Add calendar name validation
    op.execute(text("""
        ALTER TABLE calendars 
        ADD CONSTRAINT check_calendar_name_not_empty 
        CHECK (name IS NOT NULL AND LENGTH(TRIM(name)) > 0)
    """))
    
    # Add event summary validation
    op.execute(text("""
        ALTER TABLE events 
        ADD CONSTRAINT check_event_summary_not_empty 
        CHECK (summary IS NOT NULL AND LENGTH(TRIM(summary)) > 0)
    """))
    
    # Add event time validation (end must be after start)
    op.execute(text("""
        ALTER TABLE events 
        ADD CONSTRAINT check_event_time_valid 
        CHECK (end_time > start_time)
    """))
    
    print("Critical database fixes applied successfully!")


def downgrade():
    """
    Remove the applied fixes (use with caution in production)
    """
    
    print("Removing critical database fixes...")
    
    # Remove constraints (in reverse order)
    constraints_to_drop = [
        ('events', 'check_event_time_valid'),
        ('events', 'check_event_summary_not_empty'),
        ('calendars', 'check_calendar_name_not_empty'),
        ('user_oauth_tokens', 'check_service_email_format'),
        ('user_oauth_tokens', 'check_token_expiry'),
        ('user_profiles', 'check_work_phone_format'),
        ('user_profiles', 'check_alternate_phone_format'),
        ('user_profiles', 'check_phone_format'),
        ('user_profiles', 'check_email_format'),
    ]
    
    for table, constraint in constraints_to_drop:
        try:
            op.drop_constraint(constraint, table)
        except Exception:
            pass  # Constraint might not exist
    
    # Remove indexes
    indexes_to_drop = [
        'idx_user_profiles_completeness',
        'idx_events_time_range',
        'idx_oauth_tokens_service_lookup',
        'idx_auth_sessions_active',
        'idx_events_calendar_time',
        'idx_user_profiles_lookup',
    ]
    
    for index in indexes_to_drop:
        try:
            op.drop_index(index)
        except Exception:
            pass  # Index might not exist
    
    # Restore original foreign key constraint (without cascade)
    try:
        op.drop_constraint('events_calendar_id_fkey', 'events', type_='foreignkey')
        op.create_foreign_key(
            'events_calendar_id_fkey',
            'events', 'calendars',
            ['calendar_id'], ['id']
        )
    except Exception:
        pass
    
    print("Critical database fixes removed!")