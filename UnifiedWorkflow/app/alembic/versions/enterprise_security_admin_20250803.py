"""Enterprise Security Administration Models

Revision ID: enterprise_security_admin_20250803
Revises: unified_memory_integration_20250803
Create Date: 2025-08-03 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'enterprise_security_admin_20250803'
down_revision = 'unified_memory_integration_20250803'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create enterprise security administration tables."""
    
    # Create audit schema if it doesn't exist
    op.execute("CREATE SCHEMA IF NOT EXISTS audit")
    
    # Create enterprise_audit_events table
    op.create_table('enterprise_audit_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('event_id', sa.String(length=64), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('event_category', 
                  sa.Enum('authentication', 'authorization', 'data_access', 'data_modification', 
                         'system_administration', 'security_event', 'compliance_event', 
                         'user_management', 'policy_enforcement', 
                         name='auditeventcategory'), nullable=False),
        sa.Column('event_severity', 
                  sa.Enum('informational', 'low', 'medium', 'high', 'critical', 
                         name='auditeventseverity'), nullable=False),
        sa.Column('event_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('processing_timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.String(length=255), nullable=True),
        sa.Column('service_name', sa.String(length=100), nullable=False),
        sa.Column('component_name', sa.String(length=100), nullable=True),
        sa.Column('source_ip', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('request_id', sa.String(length=100), nullable=True),
        sa.Column('event_description', sa.Text(), nullable=False),
        sa.Column('event_outcome', sa.String(length=20), nullable=False),
        sa.Column('affected_resources', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('data_classification', sa.String(length=20), nullable=True),
        sa.Column('event_context', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('request_parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('response_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('compliance_relevant', sa.Boolean(), nullable=False, default=False),
        sa.Column('compliance_standards', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('retention_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('data_volume_bytes', sa.BigInteger(), nullable=True),
        sa.Column('risk_score', sa.Float(), nullable=True),
        sa.Column('risk_factors', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('hash_value', sa.String(length=128), nullable=True),
        sa.Column('previous_event_id', sa.String(length=64), nullable=True),
        sa.Column('digital_signature', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id'),
        schema='audit'
    )
    
    # Create indexes for enterprise_audit_events
    op.create_index('idx_enterprise_audit_timestamp', 'enterprise_audit_events', ['event_timestamp'], schema='audit')
    op.create_index('idx_enterprise_audit_user', 'enterprise_audit_events', ['user_id'], schema='audit')
    op.create_index('idx_enterprise_audit_category', 'enterprise_audit_events', ['event_category'], schema='audit')
    op.create_index('idx_enterprise_audit_severity', 'enterprise_audit_events', ['event_severity'], schema='audit')
    op.create_index('idx_enterprise_audit_compliance', 'enterprise_audit_events', ['compliance_relevant'], schema='audit')
    op.create_index('idx_enterprise_audit_ip', 'enterprise_audit_events', ['source_ip'], schema='audit')
    op.create_index('idx_enterprise_audit_event_type', 'enterprise_audit_events', ['event_type'], schema='audit')
    op.create_index('idx_enterprise_audit_service', 'enterprise_audit_events', ['service_name'], schema='audit')
    op.create_index('idx_enterprise_audit_outcome', 'enterprise_audit_events', ['event_outcome'], schema='audit')
    op.create_index('idx_enterprise_audit_classification', 'enterprise_audit_events', ['data_classification'], schema='audit')
    op.create_index('idx_enterprise_audit_request_id', 'enterprise_audit_events', ['request_id'], schema='audit')
    op.create_index('idx_enterprise_audit_session', 'enterprise_audit_events', ['session_id'], schema='audit')
    
    # Create threat_intelligence_events table
    op.create_table('threat_intelligence_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('threat_id', sa.String(length=64), nullable=False),
        sa.Column('threat_type', 
                  sa.Enum('brute_force', 'privilege_escalation', 'data_exfiltration', 'malware_detection',
                         'suspicious_login', 'insider_threat', 'phishing_attempt', 'sql_injection',
                         'xss_attack', 'ddos_attack', name='threattype'), nullable=False),
        sa.Column('threat_name', sa.String(length=200), nullable=False),
        sa.Column('threat_description', sa.Text(), nullable=False),
        sa.Column('severity', 
                  sa.Enum('informational', 'low', 'medium', 'high', 'critical', 
                         name='auditeventseverity'), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('false_positive_probability', sa.Float(), nullable=False, default=0.0),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('detection_method', sa.String(length=100), nullable=False),
        sa.Column('detection_rule', sa.String(length=200), nullable=True),
        sa.Column('source_ip', postgresql.INET(), nullable=True),
        sa.Column('source_country', sa.String(length=2), nullable=True),
        sa.Column('source_asn', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('attack_vector', sa.String(length=100), nullable=True),
        sa.Column('target_resource', sa.String(length=200), nullable=True),
        sa.Column('attack_payload', sa.Text(), nullable=True),
        sa.Column('indicators_of_compromise', postgresql.ARRAY(sa.String()), nullable=False, default=[]),
        sa.Column('threat_actor', sa.String(length=100), nullable=True),
        sa.Column('campaign_id', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, default='DETECTED'),
        sa.Column('response_actions', postgresql.ARRAY(sa.String()), nullable=False, default=[]),
        sa.Column('mitigation_steps', sa.Text(), nullable=True),
        sa.Column('first_seen', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('affected_systems', postgresql.ARRAY(sa.String()), nullable=False, default=[]),
        sa.Column('data_compromised', sa.Boolean(), nullable=False, default=False),
        sa.Column('business_impact', sa.String(length=20), nullable=True),
        sa.Column('threat_context', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('external_references', postgresql.ARRAY(sa.String()), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('threat_id'),
        schema='audit'
    )
    
    # Create indexes for threat_intelligence_events
    op.create_index('idx_threat_timestamp', 'threat_intelligence_events', ['detected_at'], schema='audit')
    op.create_index('idx_threat_type', 'threat_intelligence_events', ['threat_type'], schema='audit')
    op.create_index('idx_threat_severity', 'threat_intelligence_events', ['severity'], schema='audit')
    op.create_index('idx_threat_status', 'threat_intelligence_events', ['status'], schema='audit')
    op.create_index('idx_threat_ip', 'threat_intelligence_events', ['source_ip'], schema='audit')
    op.create_index('idx_threat_user', 'threat_intelligence_events', ['user_id'], schema='audit')
    op.create_index('idx_threat_confidence', 'threat_intelligence_events', ['confidence_score'], schema='audit')
    
    # Create compliance_assessments table
    op.create_table('compliance_assessments',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('assessment_id', sa.String(length=64), nullable=False),
        sa.Column('compliance_standard', 
                  sa.Enum('SOX', 'HIPAA', 'GDPR', 'ISO27001', 'PCI_DSS', 'NIST', 'CCPA', 
                         name='compliancestandard'), nullable=False),
        sa.Column('assessment_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('scope_description', sa.Text(), nullable=False),
        sa.Column('assessed_systems', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('assessed_processes', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('overall_status', 
                  sa.Enum('compliant', 'non_compliant', 'partial_compliant', 'under_review', 'exempt', 
                         name='compliancestatus'), nullable=False),
        sa.Column('overall_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('total_controls', sa.Integer(), nullable=False, default=0),
        sa.Column('passed_controls', sa.Integer(), nullable=False, default=0),
        sa.Column('failed_controls', sa.Integer(), nullable=False, default=0),
        sa.Column('not_applicable_controls', sa.Integer(), nullable=False, default=0),
        sa.Column('control_results', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('identified_gaps', postgresql.ARRAY(sa.String()), nullable=False, default=[]),
        sa.Column('remediation_recommendations', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('compliance_risk_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('risk_factors', postgresql.ARRAY(sa.String()), nullable=False, default=[]),
        sa.Column('assessor_id', sa.Integer(), nullable=True),
        sa.Column('assessment_method', sa.String(length=50), nullable=False, default='AUTOMATED'),
        sa.Column('evidence_collected', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('assessment_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('assessed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('next_assessment_due', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_by', sa.Integer(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['assessor_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('assessment_id'),
        sa.UniqueConstraint('compliance_standard', 'assessment_date', name='uq_compliance_daily')
    )
    
    # Create indexes for compliance_assessments
    op.create_index('idx_compliance_standard', 'compliance_assessments', ['compliance_standard'])
    op.create_index('idx_compliance_status', 'compliance_assessments', ['overall_status'])
    op.create_index('idx_compliance_assessed', 'compliance_assessments', ['assessed_at'])
    op.create_index('idx_compliance_score', 'compliance_assessments', ['overall_score'])
    op.create_index('idx_compliance_assessor', 'compliance_assessments', ['assessor_id'])
    
    # Create forensic_investigations table
    op.create_table('forensic_investigations',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('case_id', sa.String(length=64), nullable=False),
        sa.Column('case_name', sa.String(length=200), nullable=False),
        sa.Column('case_description', sa.Text(), nullable=False),
        sa.Column('case_type', sa.String(length=50), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=False, default='MEDIUM'),
        sa.Column('incident_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('discovery_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reported_by', sa.Integer(), nullable=True),
        sa.Column('primary_investigator_id', sa.Integer(), nullable=False),
        sa.Column('investigation_team', postgresql.ARRAY(sa.Integer()), nullable=False, default=[]),
        sa.Column('affected_systems', postgresql.ARRAY(sa.String()), nullable=False, default=[]),
        sa.Column('affected_users', postgresql.ARRAY(sa.Integer()), nullable=False, default=[]),
        sa.Column('estimated_impact', sa.String(length=20), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, default='INITIATED'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('investigation_started', sa.DateTime(timezone=True), nullable=True),
        sa.Column('investigation_completed', sa.DateTime(timezone=True), nullable=True),
        sa.Column('evidence_items', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('key_findings', postgresql.ARRAY(sa.String()), nullable=False, default=[]),
        sa.Column('investigation_notes', sa.Text(), nullable=True),
        sa.Column('legal_hold', sa.Boolean(), nullable=False, default=False),
        sa.Column('law_enforcement_notified', sa.Boolean(), nullable=False, default=False),
        sa.Column('regulatory_reporting_required', sa.Boolean(), nullable=False, default=False),
        sa.Column('custody_chain', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default=[]),
        sa.Column('evidence_hash', sa.String(length=128), nullable=True),
        sa.Column('final_report', sa.Text(), nullable=True),
        sa.Column('recommendations', postgresql.ARRAY(sa.String()), nullable=False, default=[]),
        sa.ForeignKeyConstraint(['primary_investigator_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['reported_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('case_id')
    )
    
    # Create indexes for forensic_investigations
    op.create_index('idx_forensic_status', 'forensic_investigations', ['status'])
    op.create_index('idx_forensic_priority', 'forensic_investigations', ['priority'])
    op.create_index('idx_forensic_created', 'forensic_investigations', ['created_at'])
    op.create_index('idx_forensic_investigator', 'forensic_investigations', ['primary_investigator_id'])
    op.create_index('idx_forensic_case_type', 'forensic_investigations', ['case_type'])
    op.create_index('idx_forensic_incident_date', 'forensic_investigations', ['incident_date'])
    
    # Create data_retention_logs table
    op.create_table('data_retention_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('policy_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('table_name', sa.String(length=64), nullable=False),
        sa.Column('retention_action', sa.String(length=20), nullable=False),
        sa.Column('records_affected', sa.Integer(), nullable=False, default=0),
        sa.Column('criteria_applied', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('executed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('execution_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('execution_status', sa.String(length=20), nullable=False, default='SUCCESS'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('warnings', postgresql.ARRAY(sa.String()), nullable=False, default=[]),
        sa.Column('compliance_reason', sa.String(length=100), nullable=False),
        sa.Column('legal_basis', sa.String(length=100), nullable=True),
        sa.Column('verification_hash', sa.String(length=128), nullable=True),
        sa.Column('executed_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['executed_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['policy_id'], ['data_retention_policies.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='audit'
    )
    
    # Create indexes for data_retention_logs
    op.create_index('idx_retention_table', 'data_retention_logs', ['table_name'], schema='audit')
    op.create_index('idx_retention_action', 'data_retention_logs', ['retention_action'], schema='audit')
    op.create_index('idx_retention_executed', 'data_retention_logs', ['executed_at'], schema='audit')
    op.create_index('idx_retention_policy', 'data_retention_logs', ['policy_id'], schema='audit')
    op.create_index('idx_retention_status', 'data_retention_logs', ['execution_status'], schema='audit')


def downgrade() -> None:
    """Drop enterprise security administration tables."""
    
    # Drop tables in reverse order due to foreign key dependencies
    op.drop_table('data_retention_logs', schema='audit')
    op.drop_table('forensic_investigations')
    op.drop_table('compliance_assessments')
    op.drop_table('threat_intelligence_events', schema='audit')
    op.drop_table('enterprise_audit_events', schema='audit')
    
    # Drop custom enums
    op.execute("DROP TYPE IF EXISTS threattype")
    op.execute("DROP TYPE IF EXISTS compliancestandard")
    op.execute("DROP TYPE IF EXISTS compliancestatus")
    op.execute("DROP TYPE IF EXISTS auditeventseverity")
    op.execute("DROP TYPE IF EXISTS auditeventcategory")