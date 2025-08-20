"""Comprehensive enhancements: tasks, programming, semantic features

Revision ID: 3d2f4e5a6b7c
Revises: c1f348491f8
Create Date: 2025-07-14 10:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '3d2f4e5a6b7c'
down_revision = 'c1f348491f8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add comprehensive enhancements - idempotent operations."""
    # Since the schema changes were already applied manually,
    # this migration checks for existing structures and only adds what's missing
    
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_tables = inspector.get_table_names()
    
    # Create task enums if they don't exist
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE task_status AS ENUM ('pending', 'in_progress', 'completed', 'cancelled', 'on_hold');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE task_priority AS ENUM ('low', 'medium', 'high', 'urgent');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE task_type AS ENUM ('general', 'coding', 'review', 'testing', 'deployment', 'meeting', 'research');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Add user settings columns if they don't exist
    user_columns = [col['name'] for col in inspector.get_columns('users')] if 'users' in existing_tables else []
    
    user_enhancements = [
        'theme', 'notifications_enabled', 'selected_model', 'chat_model',
        'initial_assessment_model', 'tool_selection_model', 'embeddings_model',
        'coding_model', 'calendar_event_weights', 'mission_statement',
        'personal_goals', 'work_style_preferences', 'productivity_patterns',
        'interview_insights', 'last_interview_date', 'project_preferences',
        'default_code_style', 'git_integrations'
    ]
    
    for column in user_enhancements:
        if column not in user_columns:
            if column in ['theme', 'selected_model', 'chat_model', 'initial_assessment_model', 
                         'tool_selection_model', 'embeddings_model', 'coding_model']:
                op.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {column} VARCHAR DEFAULT 'llama3.2:3b';")
            elif column == 'notifications_enabled':
                op.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {column} BOOLEAN DEFAULT TRUE;")
            elif column == 'mission_statement':
                op.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {column} TEXT;")
            elif column == 'last_interview_date':
                op.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {column} TIMESTAMP WITH TIME ZONE;")
            else:
                op.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {column} JSONB;")
    
    # Create new tables only if they don't exist
    if 'projects' not in existing_tables:
        op.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id INTEGER REFERENCES users(id),
                name VARCHAR NOT NULL,
                description TEXT,
                project_type VARCHAR,
                programming_language VARCHAR,
                framework VARCHAR,
                repository_url VARCHAR,
                local_path VARCHAR,
                status VARCHAR DEFAULT 'active',
                project_metadata JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
    
    if 'tasks' not in existing_tables:
        op.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id INTEGER REFERENCES users(id),
                project_id UUID REFERENCES projects(id),
                title VARCHAR NOT NULL,
                description TEXT,
                status task_status DEFAULT 'pending',
                priority task_priority DEFAULT 'medium',
                category VARCHAR,
                due_date TIMESTAMP WITH TIME ZONE,
                estimated_hours FLOAT,
                actual_hours FLOAT,
                completion_percentage INTEGER DEFAULT 0,
                semantic_keywords JSONB,
                semantic_embedding_id VARCHAR,
                semantic_category VARCHAR,
                semantic_tags JSONB,
                semantic_summary TEXT,
                importance_weight FLOAT DEFAULT 1.0,
                urgency_weight FLOAT DEFAULT 1.0,
                complexity_weight FLOAT DEFAULT 1.0,
                user_priority_weight FLOAT DEFAULT 1.0,
                calculated_score FLOAT,
                task_type task_type DEFAULT 'general',
                programming_language VARCHAR,
                difficulty_level VARCHAR,
                code_context JSONB,
                repository_branch VARCHAR,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
    
    # Create other tables similarly
    tables_to_create = [
        ('user_categories', """
            CREATE TABLE IF NOT EXISTS user_categories (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id INTEGER REFERENCES users(id),
                category_name VARCHAR NOT NULL,
                category_type VARCHAR DEFAULT 'custom',
                weight FLOAT DEFAULT 1.0,
                color VARCHAR,
                description TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE(user_id, category_name)
            );
        """),
        ('mission_interviews', """
            CREATE TABLE IF NOT EXISTS mission_interviews (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id INTEGER REFERENCES users(id),
                interview_type VARCHAR DEFAULT 'mission_statement',
                llm_model VARCHAR,
                status VARCHAR DEFAULT 'in_progress',
                questions JSONB,
                responses JSONB,
                analysis_results JSONB,
                recommendations JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                completed_at TIMESTAMP WITH TIME ZONE
            );
        """),
        ('semantic_insights', """
            CREATE TABLE IF NOT EXISTS semantic_insights (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id INTEGER REFERENCES users(id),
                content_type VARCHAR NOT NULL,
                content_id UUID,
                insight_type VARCHAR NOT NULL,
                insight_value JSONB NOT NULL,
                confidence_score FLOAT,
                model_used VARCHAR,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """),
        ('code_templates', """
            CREATE TABLE IF NOT EXISTS code_templates (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id INTEGER REFERENCES users(id),
                name VARCHAR NOT NULL,
                description TEXT,
                category VARCHAR,
                programming_language VARCHAR NOT NULL,
                framework VARCHAR,
                template_content JSONB NOT NULL,
                usage_count INTEGER DEFAULT 0,
                is_public BOOLEAN DEFAULT FALSE,
                tags JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """),
        ('ai_analysis_history', """
            CREATE TABLE IF NOT EXISTS ai_analysis_history (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id INTEGER REFERENCES users(id),
                analysis_type VARCHAR NOT NULL,
                input_data JSONB NOT NULL,
                output_data JSONB NOT NULL,
                model_used VARCHAR,
                processing_time_ms INTEGER,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
    ]
    
    for table_name, create_sql in tables_to_create:
        if table_name not in existing_tables:
            op.execute(create_sql)
    
    # Enhance existing tables
    if 'events' in existing_tables:
        events_columns = [col['name'] for col in inspector.get_columns('events')]
        event_enhancements = [
            'semantic_keywords', 'semantic_embedding_id', 'semantic_category',
            'semantic_tags', 'event_type', 'attendees', 'location',
            'recurrence_rule', 'reminder_minutes', 'importance_weight'
        ]
        
        for column in event_enhancements:
            if column not in events_columns:
                if column in ['event_type', 'semantic_embedding_id', 'semantic_category', 'location', 'recurrence_rule']:
                    op.execute(f"ALTER TABLE events ADD COLUMN IF NOT EXISTS {column} VARCHAR;")
                elif column in ['reminder_minutes']:
                    op.execute(f"ALTER TABLE events ADD COLUMN IF NOT EXISTS {column} INTEGER DEFAULT 15;")
                elif column == 'importance_weight':
                    op.execute(f"ALTER TABLE events ADD COLUMN IF NOT EXISTS {column} FLOAT DEFAULT 1.0;")
                else:
                    op.execute(f"ALTER TABLE events ADD COLUMN IF NOT EXISTS {column} JSONB;")
    
    if 'document_chunks' in existing_tables:
        chunks_columns = [col['name'] for col in inspector.get_columns('document_chunks')]
        chunk_enhancements = ['semantic_keywords', 'semantic_category', 'semantic_summary', 'extracted_entities']
        
        for column in chunk_enhancements:
            if column not in chunks_columns:
                if column in ['semantic_category', 'semantic_summary']:
                    op.execute(f"ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS {column} TEXT;")
                else:
                    op.execute(f"ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS {column} JSONB;")


def downgrade() -> None:
    """Remove comprehensive enhancements."""
    # This is a simplified downgrade - in practice, you might want more careful handling
    op.execute("DROP TABLE IF EXISTS ai_analysis_history CASCADE;")
    op.execute("DROP TABLE IF EXISTS code_templates CASCADE;")
    op.execute("DROP TABLE IF EXISTS semantic_insights CASCADE;")
    op.execute("DROP TABLE IF EXISTS mission_interviews CASCADE;")
    op.execute("DROP TABLE IF EXISTS user_categories CASCADE;")
    op.execute("DROP TABLE IF EXISTS tasks CASCADE;")
    op.execute("DROP TABLE IF EXISTS projects CASCADE;")
    
    op.execute("DROP TYPE IF EXISTS task_status CASCADE;")
    op.execute("DROP TYPE IF EXISTS task_priority CASCADE;")
    op.execute("DROP TYPE IF EXISTS task_type CASCADE;")