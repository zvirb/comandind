"""Performance Optimization Migration - Critical Database Performance Fixes

This migration implements immediate performance optimizations that are independent
of SSL/authentication changes and can be deployed in parallel.

Revision ID: performance_optimization_20250804
Revises: secure_database_migration_20250803
Create Date: 2025-08-04 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'performance_optimization_20250804'
down_revision = 'secure_database_migration_20250803'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Deploy critical database performance optimizations."""
    
    # =============================================================================
    # PART 1: CRITICAL AUTHENTICATION TABLE INDEXES
    # =============================================================================
    print("🚀 Creating critical authentication indexes...")
    
    # Users table performance indexes
    op.create_index('idx_users_email_status', 'users', ['email', 'status'])
    op.create_index('idx_users_role_active', 'users', ['role', 'is_active'])
    op.create_index('idx_users_created_at', 'users', ['created_at'])
    op.create_index('idx_users_status_verified', 'users', ['status', 'is_verified'])
    
    # Registered devices performance indexes  
    op.create_index('idx_registered_devices_user_active', 'registered_devices', ['user_id', 'is_active'])
    op.create_index('idx_registered_devices_fingerprint_user', 'registered_devices', ['device_fingerprint', 'user_id'])
    op.create_index('idx_registered_devices_last_seen', 'registered_devices', ['last_seen_at'])
    op.create_index('idx_registered_devices_security_level', 'registered_devices', ['security_level', 'is_trusted'])
    op.create_index('idx_registered_devices_remember_expires', 'registered_devices', ['remember_expires_at'])
    
    # Two-factor auth indexes
    op.create_index('idx_user_two_factor_auth_enabled', 'user_two_factor_auth', ['is_enabled', 'default_method'])
    op.create_index('idx_user_two_factor_auth_totp', 'user_two_factor_auth', ['totp_enabled'])
    op.create_index('idx_user_two_factor_auth_passkey', 'user_two_factor_auth', ['passkey_enabled'])
    
    # Passkey credentials indexes
    op.create_index('idx_passkey_credentials_user_active', 'passkey_credentials', ['user_id', 'is_active'])
    op.create_index('idx_passkey_credentials_last_used', 'passkey_credentials', ['last_used_at'])
    op.create_index('idx_passkey_credentials_device', 'passkey_credentials', ['device_id'])
    
    # Two-factor challenges indexes
    op.create_index('idx_two_factor_challenges_expires', 'two_factor_challenges', ['expires_at'])
    op.create_index('idx_two_factor_challenges_session', 'two_factor_challenges', ['session_token', 'is_completed'])
    op.create_index('idx_two_factor_challenges_user_type', 'two_factor_challenges', ['user_id', 'challenge_type'])
    
    # Device login attempts indexes
    op.create_index('idx_device_login_attempts_email_time', 'device_login_attempts', ['email', 'attempted_at'])
    op.create_index('idx_device_login_attempts_success', 'device_login_attempts', ['was_successful', 'attempted_at'])
    op.create_index('idx_device_login_attempts_ip', 'device_login_attempts', ['ip_address', 'attempted_at'])
    op.create_index('idx_device_login_attempts_fingerprint', 'device_login_attempts', ['device_fingerprint'])
    
    # =============================================================================
    # PART 2: CHAT AND MESSAGING PERFORMANCE INDEXES
    # =============================================================================
    print("💬 Creating chat and messaging performance indexes...")
    
    # Chat history indexes
    op.create_index('idx_chat_history_session_created', 'chat_history', ['session_id', 'created_at'])
    op.create_index('idx_chat_history_created_at', 'chat_history', ['created_at'])
    
    # Chat messages indexes
    op.create_index('idx_chat_messages_session_order', 'chat_messages', ['session_id', 'message_order'])
    op.create_index('idx_chat_messages_user_type', 'chat_messages', ['user_id', 'message_type'])
    op.create_index('idx_chat_messages_domain', 'chat_messages', ['conversation_domain'])
    op.create_index('idx_chat_messages_qdrant', 'chat_messages', ['qdrant_point_id'])
    op.create_index('idx_chat_messages_tool_used', 'chat_messages', ['tool_used'])
    op.create_index('idx_chat_messages_confidence', 'chat_messages', ['confidence_score'])
    
    # Chat session summaries indexes
    op.create_index('idx_chat_session_summaries_user_ended', 'chat_session_summaries', ['user_id', 'ended_at'])
    op.create_index('idx_chat_session_summaries_domain', 'chat_session_summaries', ['conversation_domain'])
    op.create_index('idx_chat_session_summaries_rating', 'chat_session_summaries', ['session_rating'])
    op.create_index('idx_chat_session_summaries_complexity', 'chat_session_summaries', ['complexity_level'])
    op.create_index('idx_chat_session_summaries_follow_up', 'chat_session_summaries', ['follow_up_suggested'])
    
    # Unified memory models indexes
    op.create_index('idx_chat_mode_sessions_user_active', 'chat_mode_sessions', ['user_id', 'is_active'])
    op.create_index('idx_chat_mode_sessions_mode_created', 'chat_mode_sessions', ['chat_mode', 'created_at'])
    op.create_index('idx_chat_mode_sessions_ended', 'chat_mode_sessions', ['ended_at'])
    
    # Simple chat context indexes  
    op.create_index('idx_simple_chat_context_session_key', 'simple_chat_context', ['session_id', 'context_key'])
    op.create_index('idx_simple_chat_context_type_access', 'simple_chat_context', ['context_type', 'access_level'])
    op.create_index('idx_simple_chat_context_persistent', 'simple_chat_context', ['is_persistent', 'expires_at'])
    
    # =============================================================================
    # PART 3: TASK AND WORKFLOW DASHBOARD INDEXES
    # =============================================================================
    print("📊 Creating task and workflow dashboard indexes...")
    
    # Tasks table indexes
    op.create_index('idx_tasks_user_status', 'tasks', ['user_id', 'status'])
    op.create_index('idx_tasks_user_priority', 'tasks', ['user_id', 'priority'])
    op.create_index('idx_tasks_project_status', 'tasks', ['project_id', 'status'])
    op.create_index('idx_tasks_due_date', 'tasks', ['due_date'])
    op.create_index('idx_tasks_status_priority', 'tasks', ['status', 'priority'])
    op.create_index('idx_tasks_category_status', 'tasks', ['category', 'status'])
    op.create_index('idx_tasks_task_type', 'tasks', ['task_type'])
    op.create_index('idx_tasks_completion', 'tasks', ['completion_percentage'])
    op.create_index('idx_tasks_score', 'tasks', ['calculated_score'])
    op.create_index('idx_tasks_semantic_category', 'tasks', ['semantic_category'])
    op.create_index('idx_tasks_language', 'tasks', ['programming_language'])
    op.create_index('idx_tasks_created_updated', 'tasks', ['created_at', 'updated_at'])
    
    # Projects table indexes
    op.create_index('idx_projects_user_status', 'projects', ['user_id', 'status'])
    op.create_index('idx_projects_type_language', 'projects', ['project_type', 'programming_language'])
    op.create_index('idx_projects_framework', 'projects', ['framework'])
    op.create_index('idx_projects_created', 'projects', ['created_at'])
    
    # Task feedback indexes
    op.create_index('idx_task_feedback_user_completed', 'task_feedback', ['user_id', 'completed_at'])
    op.create_index('idx_task_feedback_feeling', 'task_feedback', ['feeling'])
    op.create_index('idx_task_feedback_difficulty', 'task_feedback', ['difficulty'])
    op.create_index('idx_task_feedback_energy', 'task_feedback', ['energy'])
    op.create_index('idx_task_feedback_category', 'task_feedback', ['category'])
    
    # User categories indexes
    op.create_index('idx_user_categories_user_type', 'user_categories', ['user_id', 'category_type'])
    op.create_index('idx_user_categories_weight', 'user_categories', ['weight'])
    op.create_index('idx_user_categories_ai_generated', 'user_categories', ['ai_generated'])
    
    # =============================================================================
    # PART 4: DOCUMENT AND CONTENT INDEXES
    # =============================================================================
    print("📄 Creating document and content performance indexes...")
    
    # Documents indexes
    op.create_index('idx_documents_user_status', 'documents', ['user_id', 'status'])
    op.create_index('idx_documents_status_created', 'documents', ['status', 'created_at'])
    op.create_index('idx_documents_filename', 'documents', ['filename'])
    
    # Document chunks indexes
    op.create_index('idx_document_chunks_doc_index', 'document_chunks', ['document_id', 'chunk_index'])
    op.create_index('idx_document_chunks_vector_id', 'document_chunks', ['vector_id'])
    op.create_index('idx_document_chunks_semantic_category', 'document_chunks', ['semantic_category'])
    
    # =============================================================================
    # PART 5: CALENDAR AND EVENT INDEXES
    # =============================================================================
    print("📅 Creating calendar and event performance indexes...")
    
    # Events indexes
    op.create_index('idx_events_calendar_start', 'events', ['calendar_id', 'start_time'])
    op.create_index('idx_events_start_end_time', 'events', ['start_time', 'end_time'])
    op.create_index('idx_events_category', 'events', ['category'])
    op.create_index('idx_events_movability', 'events', ['is_movable', 'movability_score'])
    op.create_index('idx_events_google_id', 'events', ['google_event_id'])
    op.create_index('idx_events_semantic_category', 'events', ['semantic_category'])
    op.create_index('idx_events_importance', 'events', ['importance_weight'])
    
    # Calendars indexes
    op.create_index('idx_calendars_user_name', 'calendars', ['user_id', 'name'])
    
    # =============================================================================
    # PART 6: JSONB PERFORMANCE INDEXES (GIN indexes for JSON fields)
    # =============================================================================
    print("🔍 Creating JSONB performance indexes...")
    
    # Users JSONB indexes
    op.create_index('idx_users_personal_goals_gin', 'users', ['personal_goals'], postgresql_using='gin')
    op.create_index('idx_users_work_style_gin', 'users', ['work_style_preferences'], postgresql_using='gin')
    op.create_index('idx_users_productivity_patterns_gin', 'users', ['productivity_patterns'], postgresql_using='gin')
    op.create_index('idx_users_interview_insights_gin', 'users', ['interview_insights'], postgresql_using='gin')
    op.create_index('idx_users_project_preferences_gin', 'users', ['project_preferences'], postgresql_using='gin')
    op.create_index('idx_users_agent_settings_gin', 'users', ['agent_settings'], postgresql_using='gin')
    
    # Chat messages JSONB content search
    op.execute("CREATE INDEX idx_chat_messages_content_trgm ON chat_messages USING gin (content gin_trgm_ops)")
    
    # Tasks JSONB indexes
    op.create_index('idx_tasks_semantic_keywords_gin', 'tasks', ['semantic_keywords'], postgresql_using='gin')
    op.create_index('idx_tasks_semantic_tags_gin', 'tasks', ['semantic_tags'], postgresql_using='gin')
    op.create_index('idx_tasks_code_context_gin', 'tasks', ['code_context'], postgresql_using='gin')
    
    # Events JSONB indexes
    op.create_index('idx_events_semantic_keywords_gin', 'events', ['semantic_keywords'], postgresql_using='gin')
    op.create_index('idx_events_semantic_tags_gin', 'events', ['semantic_tags'], postgresql_using='gin')
    op.create_index('idx_events_attendees_gin', 'events', ['attendees'], postgresql_using='gin')
    
    # Document chunks JSONB indexes
    op.create_index('idx_document_chunks_keywords_gin', 'document_chunks', ['semantic_keywords'], postgresql_using='gin')
    op.create_index('idx_document_chunks_entities_gin', 'document_chunks', ['extracted_entities'], postgresql_using='gin')
    
    # Chat session summaries JSONB indexes
    op.create_index('idx_chat_session_summaries_topics_gin', 'chat_session_summaries', ['key_topics'], postgresql_using='gin')
    op.create_index('idx_chat_session_summaries_decisions_gin', 'chat_session_summaries', ['decisions_made'], postgresql_using='gin')
    op.create_index('idx_chat_session_summaries_preferences_gin', 'chat_session_summaries', ['user_preferences'], postgresql_using='gin')
    op.create_index('idx_chat_session_summaries_tools_gin', 'chat_session_summaries', ['tools_used'], postgresql_using='gin')
    op.create_index('idx_chat_session_summaries_keywords_gin', 'chat_session_summaries', ['search_keywords'], postgresql_using='gin')
    
    # =============================================================================
    # PART 7: SESSION AND TOKEN MANAGEMENT INDEXES
    # =============================================================================  
    print("🔐 Creating session and token management indexes...")
    
    # Session state indexes
    op.create_index('idx_session_state_updated', 'session_state', ['updated_at'])
    
    # OAuth tokens indexes
    op.create_index('idx_user_oauth_tokens_user_service', 'user_oauth_tokens', ['user_id', 'service'])
    op.create_index('idx_user_oauth_tokens_expiry', 'user_oauth_tokens', ['token_expiry'])
    op.create_index('idx_user_oauth_tokens_created', 'user_oauth_tokens', ['created_at'])
    
    # System settings indexes
    op.create_index('idx_system_settings_key', 'system_settings', ['key'])
    op.create_index('idx_system_settings_updated', 'system_settings', ['updated_at'])
    
    # User profiles indexes
    op.create_index('idx_user_profiles_company', 'user_profiles', ['company'])
    op.create_index('idx_user_profiles_timezone', 'user_profiles', ['timezone'])
    op.create_index('idx_user_profiles_updated', 'user_profiles', ['updated_at'])
    
    # =============================================================================
    # PART 8: SPECIALIZED PERFORMANCE INDEXES
    # =============================================================================
    print("⚡ Creating specialized performance indexes...")
    
    # Compound indexes for common dashboard queries
    op.create_index('idx_tasks_user_status_priority_due', 'tasks', ['user_id', 'status', 'priority', 'due_date'])
    op.create_index('idx_events_calendar_category_time', 'events', ['calendar_id', 'category', 'start_time'])
    op.create_index('idx_chat_messages_user_session_created', 'chat_messages', ['user_id', 'session_id', 'created_at'])
    
    # Performance indexes for analytics queries
    op.create_index('idx_task_feedback_user_feeling_completed', 'task_feedback', ['user_id', 'feeling', 'completed_at'])
    op.create_index('idx_device_login_attempts_user_success_time', 'device_login_attempts', ['user_id', 'was_successful', 'attempted_at'])
    
    # Memory and context indexes
    op.create_index('idx_simple_chat_context_session_priority', 'simple_chat_context', ['session_id', 'priority', 'version'])
    op.create_index('idx_router_decision_log_session_success', 'router_decision_log', ['session_id', 'success', 'created_at'])
    
    print("✅ Critical database performance indexes created successfully!")


def downgrade() -> None:
    """Remove performance optimization indexes."""
    
    print("🔄 Removing performance optimization indexes...")
    
    # Remove specialized performance indexes
    op.drop_index('idx_router_decision_log_session_success', table_name='router_decision_log')
    op.drop_index('idx_simple_chat_context_session_priority', table_name='simple_chat_context')
    op.drop_index('idx_device_login_attempts_user_success_time', table_name='device_login_attempts')
    op.drop_index('idx_task_feedback_user_feeling_completed', table_name='task_feedback')
    op.drop_index('idx_chat_messages_user_session_created', table_name='chat_messages')
    op.drop_index('idx_events_calendar_category_time', table_name='events')
    op.drop_index('idx_tasks_user_status_priority_due', table_name='tasks')
    
    # Remove user profiles indexes
    op.drop_index('idx_user_profiles_updated', table_name='user_profiles')
    op.drop_index('idx_user_profiles_timezone', table_name='user_profiles')
    op.drop_index('idx_user_profiles_company', table_name='user_profiles')
    
    # Remove system settings indexes
    op.drop_index('idx_system_settings_updated', table_name='system_settings')
    op.drop_index('idx_system_settings_key', table_name='system_settings')
    
    # Remove OAuth tokens indexes
    op.drop_index('idx_user_oauth_tokens_created', table_name='user_oauth_tokens')
    op.drop_index('idx_user_oauth_tokens_expiry', table_name='user_oauth_tokens')
    op.drop_index('idx_user_oauth_tokens_user_service', table_name='user_oauth_tokens')
    
    # Remove session state indexes
    op.drop_index('idx_session_state_updated', table_name='session_state')
    
    # Remove JSONB indexes
    op.drop_index('idx_chat_session_summaries_keywords_gin', table_name='chat_session_summaries')
    op.drop_index('idx_chat_session_summaries_tools_gin', table_name='chat_session_summaries')
    op.drop_index('idx_chat_session_summaries_preferences_gin', table_name='chat_session_summaries')
    op.drop_index('idx_chat_session_summaries_decisions_gin', table_name='chat_session_summaries')
    op.drop_index('idx_chat_session_summaries_topics_gin', table_name='chat_session_summaries')
    op.drop_index('idx_document_chunks_entities_gin', table_name='document_chunks')
    op.drop_index('idx_document_chunks_keywords_gin', table_name='document_chunks')
    op.drop_index('idx_events_attendees_gin', table_name='events')
    op.drop_index('idx_events_semantic_tags_gin', table_name='events')
    op.drop_index('idx_events_semantic_keywords_gin', table_name='events')
    op.drop_index('idx_tasks_code_context_gin', table_name='tasks')
    op.drop_index('idx_tasks_semantic_tags_gin', table_name='tasks')
    op.drop_index('idx_tasks_semantic_keywords_gin', table_name='tasks')
    op.execute("DROP INDEX IF EXISTS idx_chat_messages_content_trgm")
    op.drop_index('idx_users_agent_settings_gin', table_name='users')
    op.drop_index('idx_users_project_preferences_gin', table_name='users')
    op.drop_index('idx_users_interview_insights_gin', table_name='users')
    op.drop_index('idx_users_productivity_patterns_gin', table_name='users')
    op.drop_index('idx_users_work_style_gin', table_name='users')
    op.drop_index('idx_users_personal_goals_gin', table_name='users')
    
    # Remove calendar and event indexes
    op.drop_index('idx_calendars_user_name', table_name='calendars')
    op.drop_index('idx_events_importance', table_name='events')
    op.drop_index('idx_events_semantic_category', table_name='events')
    op.drop_index('idx_events_google_id', table_name='events')
    op.drop_index('idx_events_movability', table_name='events')
    op.drop_index('idx_events_category', table_name='events')
    op.drop_index('idx_events_start_end_time', table_name='events')
    op.drop_index('idx_events_calendar_start', table_name='events')
    
    # Remove document and content indexes
    op.drop_index('idx_document_chunks_semantic_category', table_name='document_chunks')
    op.drop_index('idx_document_chunks_vector_id', table_name='document_chunks')
    op.drop_index('idx_document_chunks_doc_index', table_name='document_chunks')
    op.drop_index('idx_documents_filename', table_name='documents')
    op.drop_index('idx_documents_status_created', table_name='documents')
    op.drop_index('idx_documents_user_status', table_name='documents')
    
    # Remove user categories indexes
    op.drop_index('idx_user_categories_ai_generated', table_name='user_categories')
    op.drop_index('idx_user_categories_weight', table_name='user_categories')
    op.drop_index('idx_user_categories_user_type', table_name='user_categories')
    
    # Remove task feedback indexes
    op.drop_index('idx_task_feedback_category', table_name='task_feedback')
    op.drop_index('idx_task_feedback_energy', table_name='task_feedback')
    op.drop_index('idx_task_feedback_difficulty', table_name='task_feedback')
    op.drop_index('idx_task_feedback_feeling', table_name='task_feedback')
    op.drop_index('idx_task_feedback_user_completed', table_name='task_feedback')
    
    # Remove projects indexes
    op.drop_index('idx_projects_created', table_name='projects')
    op.drop_index('idx_projects_framework', table_name='projects')
    op.drop_index('idx_projects_type_language', table_name='projects')
    op.drop_index('idx_projects_user_status', table_name='projects')
    
    # Remove tasks indexes
    op.drop_index('idx_tasks_created_updated', table_name='tasks')
    op.drop_index('idx_tasks_language', table_name='tasks')
    op.drop_index('idx_tasks_semantic_category', table_name='tasks')
    op.drop_index('idx_tasks_score', table_name='tasks')
    op.drop_index('idx_tasks_completion', table_name='tasks')
    op.drop_index('idx_tasks_task_type', table_name='tasks')
    op.drop_index('idx_tasks_category_status', table_name='tasks')
    op.drop_index('idx_tasks_status_priority', table_name='tasks')
    op.drop_index('idx_tasks_due_date', table_name='tasks')
    op.drop_index('idx_tasks_project_status', table_name='tasks')
    op.drop_index('idx_tasks_user_priority', table_name='tasks')
    op.drop_index('idx_tasks_user_status', table_name='tasks')
    
    # Remove unified memory indexes
    op.drop_index('idx_simple_chat_context_persistent', table_name='simple_chat_context')
    op.drop_index('idx_simple_chat_context_type_access', table_name='simple_chat_context')
    op.drop_index('idx_simple_chat_context_session_key', table_name='simple_chat_context')
    op.drop_index('idx_chat_mode_sessions_ended', table_name='chat_mode_sessions')
    op.drop_index('idx_chat_mode_sessions_mode_created', table_name='chat_mode_sessions')
    op.drop_index('idx_chat_mode_sessions_user_active', table_name='chat_mode_sessions')
    
    # Remove chat session summaries indexes
    op.drop_index('idx_chat_session_summaries_follow_up', table_name='chat_session_summaries')
    op.drop_index('idx_chat_session_summaries_complexity', table_name='chat_session_summaries')
    op.drop_index('idx_chat_session_summaries_rating', table_name='chat_session_summaries')
    op.drop_index('idx_chat_session_summaries_domain', table_name='chat_session_summaries')
    op.drop_index('idx_chat_session_summaries_user_ended', table_name='chat_session_summaries')
    
    # Remove chat messages indexes
    op.drop_index('idx_chat_messages_confidence', table_name='chat_messages')
    op.drop_index('idx_chat_messages_tool_used', table_name='chat_messages')
    op.drop_index('idx_chat_messages_qdrant', table_name='chat_messages')
    op.drop_index('idx_chat_messages_domain', table_name='chat_messages')
    op.drop_index('idx_chat_messages_user_type', table_name='chat_messages')
    op.drop_index('idx_chat_messages_session_order', table_name='chat_messages')
    
    # Remove chat history indexes
    op.drop_index('idx_chat_history_created_at', table_name='chat_history')
    op.drop_index('idx_chat_history_session_created', table_name='chat_history')
    
    # Remove device login attempts indexes
    op.drop_index('idx_device_login_attempts_fingerprint', table_name='device_login_attempts')
    op.drop_index('idx_device_login_attempts_ip', table_name='device_login_attempts')
    op.drop_index('idx_device_login_attempts_success', table_name='device_login_attempts')
    op.drop_index('idx_device_login_attempts_email_time', table_name='device_login_attempts')
    
    # Remove two-factor challenges indexes
    op.drop_index('idx_two_factor_challenges_user_type', table_name='two_factor_challenges')
    op.drop_index('idx_two_factor_challenges_session', table_name='two_factor_challenges')
    op.drop_index('idx_two_factor_challenges_expires', table_name='two_factor_challenges')
    
    # Remove passkey credentials indexes
    op.drop_index('idx_passkey_credentials_device', table_name='passkey_credentials')
    op.drop_index('idx_passkey_credentials_last_used', table_name='passkey_credentials')
    op.drop_index('idx_passkey_credentials_user_active', table_name='passkey_credentials')
    
    # Remove two-factor auth indexes
    op.drop_index('idx_user_two_factor_auth_passkey', table_name='user_two_factor_auth')
    op.drop_index('idx_user_two_factor_auth_totp', table_name='user_two_factor_auth')
    op.drop_index('idx_user_two_factor_auth_enabled', table_name='user_two_factor_auth')
    
    # Remove registered devices indexes
    op.drop_index('idx_registered_devices_remember_expires', table_name='registered_devices')
    op.drop_index('idx_registered_devices_security_level', table_name='registered_devices')
    op.drop_index('idx_registered_devices_last_seen', table_name='registered_devices')
    op.drop_index('idx_registered_devices_fingerprint_user', table_name='registered_devices')
    op.drop_index('idx_registered_devices_user_active', table_name='registered_devices')
    
    # Remove users indexes
    op.drop_index('idx_users_status_verified', table_name='users')
    op.drop_index('idx_users_created_at', table_name='users')
    op.drop_index('idx_users_role_active', table_name='users')
    op.drop_index('idx_users_email_status', table_name='users')
    
    print("✅ Performance optimization indexes removed successfully!")