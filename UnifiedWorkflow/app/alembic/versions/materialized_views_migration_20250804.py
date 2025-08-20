"""Create Materialized Views for Dashboard Aggregations

This migration creates materialized views for common dashboard queries to
improve performance for real-time analytics and reporting.

Revision ID: materialized_views_20250804
Revises: performance_optimization_20250804
Create Date: 2025-08-04 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'materialized_views_20250804'
down_revision = 'performance_optimization_20250804'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create materialized views for dashboard performance."""
    
    print("📊 Creating materialized views for dashboard aggregations...")
    
    # =============================================================================
    # USER DASHBOARD SUMMARY VIEW
    # =============================================================================
    op.execute("""
        CREATE MATERIALIZED VIEW user_dashboard_summary AS
        SELECT 
            u.id as user_id,
            u.email,
            u.status,
            u.role,
            u.is_active,
            u.created_at as user_created_at,
            
            -- Task Statistics
            COALESCE(task_stats.total_tasks, 0) as total_tasks,
            COALESCE(task_stats.pending_tasks, 0) as pending_tasks,
            COALESCE(task_stats.in_progress_tasks, 0) as in_progress_tasks,
            COALESCE(task_stats.completed_tasks, 0) as completed_tasks,
            COALESCE(task_stats.high_priority_tasks, 0) as high_priority_tasks,
            COALESCE(task_stats.overdue_tasks, 0) as overdue_tasks,
            COALESCE(task_stats.avg_completion_percentage, 0) as avg_task_completion,
            
            -- Project Statistics  
            COALESCE(project_stats.total_projects, 0) as total_projects,
            COALESCE(project_stats.active_projects, 0) as active_projects,
            
            -- Chat Statistics
            COALESCE(chat_stats.total_sessions, 0) as total_chat_sessions,
            COALESCE(chat_stats.total_messages, 0) as total_chat_messages,
            COALESCE(chat_stats.avg_session_rating, 0) as avg_session_rating,
            
            -- Document Statistics
            COALESCE(doc_stats.total_documents, 0) as total_documents,
            COALESCE(doc_stats.processed_documents, 0) as processed_documents,
            
            -- Calendar Statistics
            COALESCE(cal_stats.total_events, 0) as total_events,
            COALESCE(cal_stats.upcoming_events, 0) as upcoming_events,
            
            -- Device Statistics
            COALESCE(device_stats.total_devices, 0) as total_devices,
            COALESCE(device_stats.active_devices, 0) as active_devices,
            COALESCE(device_stats.trusted_devices, 0) as trusted_devices,
            
            -- Last Activity
            GREATEST(
                u.updated_at,
                COALESCE(task_stats.last_task_update, u.updated_at),
                COALESCE(chat_stats.last_chat_activity, u.updated_at),
                COALESCE(device_stats.last_device_activity, u.updated_at)
            ) as last_activity,
            
            NOW() as view_updated_at
            
        FROM users u
        
        -- Task Statistics Subquery
        LEFT JOIN (
            SELECT 
                user_id,
                COUNT(*) as total_tasks,
                COUNT(*) FILTER (WHERE status = 'pending') as pending_tasks,
                COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress_tasks,
                COUNT(*) FILTER (WHERE status = 'completed') as completed_tasks,
                COUNT(*) FILTER (WHERE priority = 'high' OR priority = 'urgent') as high_priority_tasks,
                COUNT(*) FILTER (WHERE due_date < NOW() AND status != 'completed') as overdue_tasks,
                AVG(completion_percentage) as avg_completion_percentage,
                MAX(updated_at) as last_task_update
            FROM tasks
            GROUP BY user_id
        ) task_stats ON u.id = task_stats.user_id
        
        -- Project Statistics Subquery
        LEFT JOIN (
            SELECT 
                user_id,
                COUNT(*) as total_projects,
                COUNT(*) FILTER (WHERE status = 'active') as active_projects
            FROM projects
            GROUP BY user_id
        ) project_stats ON u.id = project_stats.user_id
        
        -- Chat Statistics Subquery
        LEFT JOIN (
            SELECT 
                user_id,
                COUNT(*) as total_sessions,
                SUM(message_count) as total_messages,
                AVG(session_rating) as avg_session_rating,
                MAX(ended_at) as last_chat_activity
            FROM chat_session_summaries
            GROUP BY user_id
        ) chat_stats ON u.id = chat_stats.user_id
        
        -- Document Statistics Subquery
        LEFT JOIN (
            SELECT 
                user_id,
                COUNT(*) as total_documents,
                COUNT(*) FILTER (WHERE status = 'completed') as processed_documents
            FROM documents
            GROUP BY user_id
        ) doc_stats ON u.id = doc_stats.user_id
        
        -- Calendar Statistics Subquery
        LEFT JOIN (
            SELECT 
                c.user_id,
                COUNT(e.id) as total_events,
                COUNT(e.id) FILTER (WHERE e.start_time > NOW()) as upcoming_events
            FROM calendars c
            LEFT JOIN events e ON c.id = e.calendar_id
            GROUP BY c.user_id
        ) cal_stats ON u.id = cal_stats.user_id
        
        -- Device Statistics Subquery
        LEFT JOIN (
            SELECT 
                user_id,
                COUNT(*) as total_devices,
                COUNT(*) FILTER (WHERE is_active = true) as active_devices,
                COUNT(*) FILTER (WHERE is_trusted = true) as trusted_devices,
                MAX(last_seen_at) as last_device_activity
            FROM registered_devices
            GROUP BY user_id
        ) device_stats ON u.id = device_stats.user_id
        
        WHERE u.is_active = true;
    """)
    
    # Create indexes on the materialized view
    op.execute("CREATE UNIQUE INDEX idx_user_dashboard_summary_user_id ON user_dashboard_summary (user_id);")
    op.execute("CREATE INDEX idx_user_dashboard_summary_status ON user_dashboard_summary (status);")
    op.execute("CREATE INDEX idx_user_dashboard_summary_last_activity ON user_dashboard_summary (last_activity);")
    
    # =============================================================================
    # TASK ANALYTICS VIEW
    # =============================================================================
    op.execute("""
        CREATE MATERIALIZED VIEW task_analytics AS
        SELECT 
            t.user_id,
            t.status,
            t.priority,
            t.category,
            t.task_type,
            t.programming_language,
            EXTRACT(YEAR FROM t.created_at) as year,
            EXTRACT(MONTH FROM t.created_at) as month,
            EXTRACT(WEEK FROM t.created_at) as week,
            
            -- Counts
            COUNT(*) as task_count,
            COUNT(*) FILTER (WHERE t.due_date < NOW() AND t.status != 'completed') as overdue_count,
            COUNT(*) FILTER (WHERE t.completion_percentage = 100) as fully_completed_count,
            
            -- Averages
            AVG(t.completion_percentage) as avg_completion_percentage,
            AVG(t.estimated_hours) as avg_estimated_hours,
            AVG(t.actual_hours) as avg_actual_hours,
            
            -- Time analysis
            AVG(EXTRACT(EPOCH FROM (t.updated_at - t.created_at)) / 3600) as avg_hours_to_update,
            AVG(CASE 
                WHEN t.status = 'completed' THEN 
                    EXTRACT(EPOCH FROM (t.updated_at - t.created_at)) / 3600
                ELSE NULL 
            END) as avg_hours_to_completion,
            
            -- Feedback integration
            AVG(tf.difficulty) as avg_difficulty_rating,
            AVG(tf.energy) as avg_energy_rating,
            COUNT(tf.id) FILTER (WHERE tf.feeling = 'positive') as positive_feedback_count,
            COUNT(tf.id) FILTER (WHERE tf.feeling = 'negative') as negative_feedback_count,
            
            NOW() as view_updated_at
            
        FROM tasks t
        LEFT JOIN task_feedback tf ON t.id = tf.opportunity_id
        WHERE t.created_at >= NOW() - INTERVAL '1 year'
        GROUP BY 
            t.user_id, t.status, t.priority, t.category, t.task_type, t.programming_language,
            EXTRACT(YEAR FROM t.created_at), EXTRACT(MONTH FROM t.created_at), EXTRACT(WEEK FROM t.created_at);
    """)
    
    # Create indexes on task analytics view
    op.execute("CREATE INDEX idx_task_analytics_user_status ON task_analytics (user_id, status);")
    op.execute("CREATE INDEX idx_task_analytics_year_month ON task_analytics (year, month);")
    op.execute("CREATE INDEX idx_task_analytics_category ON task_analytics (category);")
    op.execute("CREATE INDEX idx_task_analytics_priority ON task_analytics (priority);")
    
    # =============================================================================
    # CHAT SESSION ANALYTICS VIEW
    # =============================================================================
    op.execute("""
        CREATE MATERIALIZED VIEW chat_session_analytics AS
        SELECT 
            css.user_id,
            css.conversation_domain,
            css.complexity_level,
            css.resolution_status,
            EXTRACT(YEAR FROM css.started_at) as year,
            EXTRACT(MONTH FROM css.started_at) as month,
            EXTRACT(WEEK FROM css.started_at) as week,
            EXTRACT(DOW FROM css.started_at) as day_of_week,
            EXTRACT(HOUR FROM css.started_at) as hour_of_day,
            
            -- Session counts and metrics
            COUNT(*) as session_count,
            AVG(css.message_count) as avg_messages_per_session,
            AVG(css.total_tokens_used) as avg_tokens_per_session,
            AVG(css.session_rating) as avg_session_rating,
            AVG(css.plans_created) as avg_plans_per_session,
            AVG(css.expert_questions_asked) as avg_expert_questions,
            
            -- Duration analysis
            AVG(EXTRACT(EPOCH FROM (css.ended_at - css.started_at)) / 60) as avg_session_duration_minutes,
            
            -- Tool usage
            AVG(array_length(css.tools_used, 1)) as avg_tools_per_session,
            
            -- Follow-up analysis
            COUNT(*) FILTER (WHERE css.follow_up_suggested = true) as sessions_with_followup,
            AVG(array_length(css.follow_up_tasks, 1)) as avg_followup_tasks,
            
            -- Quality metrics
            COUNT(*) FILTER (WHERE css.resolution_status = 'completed') as completed_sessions,
            COUNT(*) FILTER (WHERE css.session_rating >= 4.0) as high_rated_sessions,
            
            NOW() as view_updated_at
            
        FROM chat_session_summaries css
        WHERE css.started_at >= NOW() - INTERVAL '1 year'
        GROUP BY 
            css.user_id, css.conversation_domain, css.complexity_level, css.resolution_status,
            EXTRACT(YEAR FROM css.started_at), EXTRACT(MONTH FROM css.started_at), 
            EXTRACT(WEEK FROM css.started_at), EXTRACT(DOW FROM css.started_at), 
            EXTRACT(HOUR FROM css.started_at);
    """)
    
    # Create indexes on chat analytics view
    op.execute("CREATE INDEX idx_chat_analytics_user_domain ON chat_session_analytics (user_id, conversation_domain);")
    op.execute("CREATE INDEX idx_chat_analytics_year_month ON chat_session_analytics (year, month);")
    op.execute("CREATE INDEX idx_chat_analytics_complexity ON chat_session_analytics (complexity_level);")
    op.execute("CREATE INDEX idx_chat_analytics_hour ON chat_session_analytics (hour_of_day);")
    
    # =============================================================================
    # AUTHENTICATION SECURITY VIEW  
    # =============================================================================  
    op.execute("""
        CREATE MATERIALIZED VIEW auth_security_summary AS
        SELECT 
            u.id as user_id,
            u.email,
            u.status,
            u.tfa_enabled,
            
            -- Two-factor authentication status
            CASE WHEN utf.is_enabled THEN 'enabled' ELSE 'disabled' END as tfa_status,
            utf.default_method as tfa_default_method,
            utf.totp_enabled,
            utf.passkey_enabled,
            
            -- Device statistics
            COALESCE(device_stats.total_devices, 0) as total_devices,
            COALESCE(device_stats.active_devices, 0) as active_devices,
            COALESCE(device_stats.trusted_devices, 0) as trusted_devices,
            COALESCE(device_stats.remembered_devices, 0) as remembered_devices,
            
            -- Login attempt statistics (last 30 days)
            COALESCE(login_stats.total_attempts, 0) as login_attempts_30d,
            COALESCE(login_stats.successful_attempts, 0) as successful_logins_30d,
            COALESCE(login_stats.failed_attempts, 0) as failed_logins_30d,
            COALESCE(login_stats.with_2fa, 0) as logins_with_2fa_30d,
            
            -- Security risk indicators
            CASE 
                WHEN login_stats.failed_attempts > 10 THEN 'high'
                WHEN login_stats.failed_attempts > 5 THEN 'medium'
                ELSE 'low'
            END as failed_login_risk,
            
            CASE 
                WHEN device_stats.active_devices > 5 THEN 'high'
                WHEN device_stats.active_devices > 3 THEN 'medium'
                ELSE 'low'
            END as device_count_risk,
            
            -- Last activity timestamps
            device_stats.last_device_seen,
            login_stats.last_login_attempt,
            
            NOW() as view_updated_at
            
        FROM users u
        LEFT JOIN user_two_factor_auth utf ON u.id = utf.user_id
        
        -- Device statistics
        LEFT JOIN (
            SELECT 
                user_id,
                COUNT(*) as total_devices,
                COUNT(*) FILTER (WHERE is_active = true) as active_devices,
                COUNT(*) FILTER (WHERE is_trusted = true) as trusted_devices,
                COUNT(*) FILTER (WHERE is_remembered = true) as remembered_devices,
                MAX(last_seen_at) as last_device_seen
            FROM registered_devices
            GROUP BY user_id
        ) device_stats ON u.id = device_stats.user_id
        
        -- Login attempt statistics (last 30 days)
        LEFT JOIN (
            SELECT 
                user_id,
                COUNT(*) as total_attempts,
                COUNT(*) FILTER (WHERE was_successful = true) as successful_attempts,
                COUNT(*) FILTER (WHERE was_successful = false) as failed_attempts,
                COUNT(*) FILTER (WHERE used_2fa = true) as with_2fa,
                MAX(attempted_at) as last_login_attempt
            FROM device_login_attempts
            WHERE attempted_at >= NOW() - INTERVAL '30 days'
            GROUP BY user_id
        ) login_stats ON u.id = login_stats.user_id
        
        WHERE u.is_active = true;
    """)
    
    # Create indexes on auth security view
    op.execute("CREATE UNIQUE INDEX idx_auth_security_user_id ON auth_security_summary (user_id);")
    op.execute("CREATE INDEX idx_auth_security_tfa_status ON auth_security_summary (tfa_status);")
    op.execute("CREATE INDEX idx_auth_security_failed_risk ON auth_security_summary (failed_login_risk);")
    op.execute("CREATE INDEX idx_auth_security_device_risk ON auth_security_summary (device_count_risk);")
    
    # =============================================================================
    # SYSTEM PERFORMANCE VIEW
    # =============================================================================
    op.execute("""
        CREATE MATERIALIZED VIEW system_performance_summary AS
        SELECT 
            -- User activity metrics
            (SELECT COUNT(*) FROM users WHERE is_active = true) as total_active_users,
            (SELECT COUNT(*) FROM users WHERE last_login_date >= NOW() - INTERVAL '7 days') as users_active_7d,
            (SELECT COUNT(*) FROM users WHERE last_login_date >= NOW() - INTERVAL '30 days') as users_active_30d,
            
            -- Task metrics
            (SELECT COUNT(*) FROM tasks WHERE created_at >= NOW() - INTERVAL '24 hours') as tasks_created_24h,
            (SELECT COUNT(*) FROM tasks WHERE status = 'completed' AND updated_at >= NOW() - INTERVAL '24 hours') as tasks_completed_24h,
            (SELECT COUNT(*) FROM tasks WHERE status = 'pending') as tasks_pending_total,
            (SELECT COUNT(*) FROM tasks WHERE status = 'in_progress') as tasks_in_progress_total,
            
            -- Chat metrics
            (SELECT COUNT(*) FROM chat_session_summaries WHERE started_at >= NOW() - INTERVAL '24 hours') as chat_sessions_24h,
            (SELECT COUNT(*) FROM chat_messages WHERE created_at >= NOW() - INTERVAL '24 hours') as chat_messages_24h,
            (SELECT AVG(session_rating) FROM chat_session_summaries WHERE ended_at >= NOW() - INTERVAL '7 days') as avg_chat_rating_7d,
            
            -- Document processing metrics
            (SELECT COUNT(*) FROM documents WHERE created_at >= NOW() - INTERVAL '24 hours') as documents_uploaded_24h,
            (SELECT COUNT(*) FROM documents WHERE status = 'processing') as documents_processing,
            (SELECT COUNT(*) FROM documents WHERE status = 'failed') as documents_failed,
            
            -- Security metrics
            (SELECT COUNT(*) FROM device_login_attempts WHERE attempted_at >= NOW() - INTERVAL '24 hours') as login_attempts_24h,
            (SELECT COUNT(*) FROM device_login_attempts WHERE was_successful = false AND attempted_at >= NOW() - INTERVAL '24 hours') as failed_logins_24h,
            (SELECT COUNT(*) FROM registered_devices WHERE last_seen_at >= NOW() - INTERVAL '24 hours') as active_devices_24h,
            
            -- Performance indicators
            (SELECT COUNT(*) FROM two_factor_challenges WHERE expires_at < NOW()) as expired_challenges,
            (SELECT COUNT(*) FROM session_state WHERE updated_at < NOW() - INTERVAL '1 hour') as stale_sessions,
            
            NOW() as view_updated_at;
    """)
    
    # =============================================================================
    # CREATE REFRESH FUNCTIONS
    # =============================================================================
    
    print("🔄 Creating materialized view refresh functions...")
    
    # Function to refresh all dashboard views
    op.execute("""
        CREATE OR REPLACE FUNCTION refresh_dashboard_views()
        RETURNS void AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW user_dashboard_summary;
            REFRESH MATERIALIZED VIEW task_analytics;
            REFRESH MATERIALIZED VIEW chat_session_analytics;
            REFRESH MATERIALIZED VIEW auth_security_summary;
            REFRESH MATERIALIZED VIEW system_performance_summary;
            
            -- Log the refresh
            INSERT INTO system_settings (key, value, description, updated_at)
            VALUES ('last_dashboard_refresh', EXTRACT(epoch from NOW())::text, 'Last dashboard views refresh timestamp', NOW())
            ON CONFLICT (key) DO UPDATE SET 
                value = EXCLUDED.value,
                updated_at = EXCLUDED.updated_at;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Function to refresh specific view
    op.execute("""
        CREATE OR REPLACE FUNCTION refresh_dashboard_view(view_name text)
        RETURNS void AS $$
        BEGIN
            EXECUTE 'REFRESH MATERIALIZED VIEW ' || quote_ident(view_name);
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    print("✅ Materialized views for dashboard aggregations created successfully!")


def downgrade() -> None:
    """Remove materialized views and functions."""
    
    print("🔄 Removing materialized views and functions...")
    
    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS refresh_dashboard_view(text);")
    op.execute("DROP FUNCTION IF EXISTS refresh_dashboard_views();")
    
    # Drop materialized views
    op.execute("DROP MATERIALIZED VIEW IF EXISTS system_performance_summary;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS auth_security_summary;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS chat_session_analytics;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS task_analytics;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS user_dashboard_summary;")
    
    print("✅ Materialized views removed successfully!")