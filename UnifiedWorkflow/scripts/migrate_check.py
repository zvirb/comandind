#!/usr/bin/env python3
"""
Production migration verification script.
This script ensures the database schema is correct without relying on Alembic revision tracking.
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text, inspect

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_database_schema():
    """
    Check if the database has all required tables and columns for the comprehensive schema.
    Returns True if schema is complete, False otherwise.
    """
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL not found in environment")
        return False
    
    logger.info(f"Connecting to database...")
    
    try:
        engine = create_engine(database_url)
        inspector = inspect(engine)
        
        # Define expected tables and their critical columns
        expected_schema = {
            'users': ['id', 'email', 'hashed_password', 'theme', 'mission_statement', 'timezone'],
            'events': ['id', 'summary', 'start_time', 'semantic_keywords', 'importance_weight'],
            'documents': ['id', 'filename', 'user_id', 'status'],
            'document_chunks': ['id', 'document_id', 'content', 'semantic_keywords'],
            'projects': ['id', 'user_id', 'name', 'programming_language', 'project_metadata'],
            'tasks': ['id', 'user_id', 'title', 'status', 'priority', 'semantic_keywords', 'importance_weight'],
            'user_categories': ['id', 'user_id', 'category_name', 'weight'],
            'mission_interviews': ['id', 'user_id', 'interview_type', 'questions', 'responses'],
            'semantic_insights': ['id', 'user_id', 'content_type', 'insight_value'],
            'code_templates': ['id', 'user_id', 'name', 'programming_language', 'template_content'],
            'ai_analysis_history': ['id', 'user_id', 'analysis_type', 'input_data', 'output_data'],
            'chat_session_summaries': ['id', 'session_id', 'user_id', 'started_at', 'ended_at', 'summary'],
            'chat_messages': ['id', 'session_id', 'user_id', 'message_type', 'content', 'message_order']
        }
        
        existing_tables = inspector.get_table_names()
        logger.info(f"Found {len(existing_tables)} tables in database")
        
        missing_tables = []
        incomplete_tables = []
        
        for table_name, required_columns in expected_schema.items():
            if table_name not in existing_tables:
                missing_tables.append(table_name)
                logger.error(f"❌ Missing table: {table_name}")
            else:
                # Check if table has required columns
                existing_columns = [col['name'] for col in inspector.get_columns(table_name)]
                missing_columns = [col for col in required_columns if col not in existing_columns]
                
                if missing_columns:
                    incomplete_tables.append(f"{table_name} (missing: {', '.join(missing_columns)})")
                    logger.warning(f"⚠️  Table {table_name} missing columns: {', '.join(missing_columns)}")
                else:
                    logger.info(f"✅ Table {table_name} complete")
        
        # Check alembic_version table
        with engine.connect() as conn:
            try:
                result = conn.execute(text("SELECT version_num FROM alembic_version;"))
                current_revision = result.fetchone()
                if current_revision:
                    logger.info(f"✅ Current database revision: {current_revision[0]}")
                else:
                    logger.warning("⚠️  No revision found in alembic_version table")
            except Exception as e:
                logger.warning(f"⚠️  Could not check alembic_version: {e}")
        
        if missing_tables or incomplete_tables:
            logger.error("❌ Database schema is incomplete")
            if missing_tables:
                logger.error(f"Missing tables: {', '.join(missing_tables)}")
            if incomplete_tables:
                logger.error(f"Incomplete tables: {', '.join(incomplete_tables)}")
            return False
        else:
            logger.info("✅ Database schema is complete and ready!")
            return True
            
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

def main():
    """Main function that checks schema and exits with appropriate code."""
    logger.info("=== Database Schema Verification ===")
    
    if check_database_schema():
        logger.info("✅ SUCCESS: Database schema is complete")
        logger.info("✅ Application is ready to start")
        return 0
    else:
        logger.error("❌ FAILED: Database schema verification failed")
        logger.error("❌ Application cannot start safely")
        return 1

if __name__ == "__main__":
    sys.exit(main())