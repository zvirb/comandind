"""Add memory service knowledge graph tables

Revision ID: d4e5f6a7b8c9
Revises: 3d2f4e5a6b7c
Create Date: 2025-08-09 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd4e5f6a7b8c9'
down_revision = '3d2f4e5a6b7c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add knowledge graph and memory service tables."""
    
    # Create graph_nodes table for entity storage
    op.execute("""
        CREATE TABLE IF NOT EXISTS graph_nodes (
            id SERIAL PRIMARY KEY,
            entity_id VARCHAR(255) UNIQUE NOT NULL,
            entity_type VARCHAR(100) NOT NULL,
            properties JSONB NOT NULL DEFAULT '{}',
            user_id INTEGER NOT NULL,
            confidence_score FLOAT DEFAULT 0.0,
            source_document VARCHAR(255),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)
    
    # Create indexes for graph_nodes
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_graph_nodes_entity_id ON graph_nodes(entity_id);
        CREATE INDEX IF NOT EXISTS idx_graph_nodes_entity_type ON graph_nodes(entity_type);
        CREATE INDEX IF NOT EXISTS idx_graph_nodes_user_id ON graph_nodes(user_id);
        CREATE INDEX IF NOT EXISTS idx_graph_nodes_user_type ON graph_nodes(user_id, entity_type);
        CREATE INDEX IF NOT EXISTS idx_graph_nodes_entity_user ON graph_nodes(entity_id, user_id);
    """)
    
    # Create graph_edges table for relationship storage
    op.execute("""
        CREATE TABLE IF NOT EXISTS graph_edges (
            id SERIAL PRIMARY KEY,
            source_entity_id VARCHAR(255) NOT NULL,
            target_entity_id VARCHAR(255) NOT NULL,
            relationship_type VARCHAR(100) NOT NULL,
            properties JSONB DEFAULT '{}',
            user_id INTEGER NOT NULL,
            confidence_score FLOAT DEFAULT 0.0,
            source_document VARCHAR(255),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)
    
    # Create indexes for graph_edges
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_graph_edges_source_entity_id ON graph_edges(source_entity_id);
        CREATE INDEX IF NOT EXISTS idx_graph_edges_target_entity_id ON graph_edges(target_entity_id);
        CREATE INDEX IF NOT EXISTS idx_graph_edges_relationship_type ON graph_edges(relationship_type);
        CREATE INDEX IF NOT EXISTS idx_graph_edges_user_id ON graph_edges(user_id);
        CREATE INDEX IF NOT EXISTS idx_graph_edges_source_target ON graph_edges(source_entity_id, target_entity_id);
        CREATE INDEX IF NOT EXISTS idx_graph_edges_user_type ON graph_edges(user_id, relationship_type);
        CREATE INDEX IF NOT EXISTS idx_graph_edges_source_user ON graph_edges(source_entity_id, user_id);
        CREATE INDEX IF NOT EXISTS idx_graph_edges_target_user ON graph_edges(target_entity_id, user_id);
    """)
    
    # Create memory_records table for tracking curation decisions
    op.execute("""
        CREATE TABLE IF NOT EXISTS memory_records (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            content_hash VARCHAR(64) NOT NULL,
            operation VARCHAR(20) NOT NULL,
            reasoning TEXT,
            qdrant_point_id VARCHAR(255),
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)
    
    # Create indexes for memory_records
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_memory_records_user_id ON memory_records(user_id);
        CREATE INDEX IF NOT EXISTS idx_memory_records_content_hash ON memory_records(content_hash);
        CREATE INDEX IF NOT EXISTS idx_memory_records_user_hash ON memory_records(user_id, content_hash);
        CREATE INDEX IF NOT EXISTS idx_memory_records_operation ON memory_records(operation);
    """)
    
    # Create processing_jobs table for tracking document processing
    op.execute("""
        CREATE TABLE IF NOT EXISTS processing_jobs (
            id VARCHAR(255) PRIMARY KEY,
            user_id INTEGER NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'started',
            current_step VARCHAR(100),
            progress_data JSONB DEFAULT '{}',
            error_message TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            completed_at TIMESTAMP WITH TIME ZONE
        );
    """)
    
    # Create indexes for processing_jobs
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_processing_jobs_user_id ON processing_jobs(user_id);
        CREATE INDEX IF NOT EXISTS idx_processing_jobs_status ON processing_jobs(status);
        CREATE INDEX IF NOT EXISTS idx_processing_jobs_created_at ON processing_jobs(created_at);
    """)
    
    # Add trigger to automatically update updated_at timestamp
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Apply triggers to tables with updated_at columns
    for table in ['graph_nodes', 'graph_edges', 'processing_jobs']:
        op.execute(f"""
            DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};
            CREATE TRIGGER update_{table}_updated_at
                BEFORE UPDATE ON {table}
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        """)


def downgrade() -> None:
    """Remove knowledge graph and memory service tables."""
    
    # Drop triggers
    for table in ['graph_nodes', 'graph_edges', 'processing_jobs']:
        op.execute(f"DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};")
    
    # Drop function
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")
    
    # Drop tables in reverse order
    op.execute("DROP TABLE IF EXISTS processing_jobs CASCADE;")
    op.execute("DROP TABLE IF EXISTS memory_records CASCADE;")
    op.execute("DROP TABLE IF EXISTS graph_edges CASCADE;")
    op.execute("DROP TABLE IF EXISTS graph_nodes CASCADE;")