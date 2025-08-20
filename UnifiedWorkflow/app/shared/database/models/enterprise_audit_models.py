"""Enterprise Audit and Compliance Models.

Enhanced audit trail models for enterprise compliance requirements,
forensic investigation, and comprehensive security monitoring.
"""

import enum
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import Boolean, String, DateTime, Integer, Text, Float, BigInteger
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, INET
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey, Enum as SQLAlchemyEnum, Index, UniqueConstraint

from shared.utils.database_setup import Base


class ComplianceStandard(str, enum.Enum):
    """Compliance standards supported by the system."""
    SOX = "SOX"
    HIPAA = "HIPAA"
    GDPR = "GDPR"
    ISO27001 = "ISO27001"
    PCI_DSS = "PCI_DSS"
    NIST = "NIST"
    CCPA = "CCPA"


class AuditEventCategory(str, enum.Enum):
    """Categories for audit events."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    SYSTEM_ADMINISTRATION = "system_administration"
    SECURITY_EVENT = "security_event"
    COMPLIANCE_EVENT = "compliance_event"
    USER_MANAGEMENT = "user_management"
    POLICY_ENFORCEMENT = "policy_enforcement"


class AuditEventSeverity(str, enum.Enum):
    """Severity levels for audit events."""
    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceStatus(str, enum.Enum):
    """Compliance status values."""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIAL_COMPLIANT = "partial_compliant"
    UNDER_REVIEW = "under_review"
    EXEMPT = "exempt"


class ThreatType(str, enum.Enum):
    """Types of security threats."""
    BRUTE_FORCE = "brute_force"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    MALWARE_DETECTION = "malware_detection"
    SUSPICIOUS_LOGIN = "suspicious_login"
    INSIDER_THREAT = "insider_threat"
    PHISHING_ATTEMPT = "phishing_attempt"
    SQL_INJECTION = "sql_injection"
    XSS_ATTACK = "xss_attack"
    DDOS_ATTACK = "ddos_attack"


class EnterpriseAuditEvent(Base):
    """Comprehensive enterprise audit events for compliance and forensics."""
    __tablename__ = "enterprise_audit_events"
    __table_args__ = (
        Index("idx_enterprise_audit_timestamp", "event_timestamp"),
        Index("idx_enterprise_audit_user", "user_id"),
        Index("idx_enterprise_audit_category", "event_category"),
        Index("idx_enterprise_audit_severity", "event_severity"),
        Index("idx_enterprise_audit_compliance", "compliance_relevant"),
        Index("idx_enterprise_audit_ip", "source_ip"),
        {'schema': 'audit'}
    )
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=func.gen_random_uuid()
    )
    
    # Event identification
    event_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_category: Mapped[AuditEventCategory] = mapped_column(
        SQLAlchemyEnum(AuditEventCategory), 
        nullable=False, 
        index=True
    )
    event_severity: Mapped[AuditEventSeverity] = mapped_column(
        SQLAlchemyEnum(AuditEventSeverity), 
        nullable=False, 
        index=True
    )
    
    # Timing
    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        index=True
    )
    processing_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    
    # Source information
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), 
        nullable=True, 
        index=True
    )
    session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    service_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    component_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Network information
    source_ip: Mapped[Optional[str]] = mapped_column(INET, nullable=True, index=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    # Event details
    event_description: Mapped[str] = mapped_column(Text, nullable=False)
    event_outcome: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # Outcomes: SUCCESS, FAILURE, ERROR, PARTIAL, BLOCKED
    
    # Data involved
    affected_resources: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    data_classification: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    # Classifications: PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED
    
    # Event context
    event_context: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    request_parameters: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    response_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Compliance tracking
    compliance_relevant: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    compliance_standards: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    retention_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Performance metrics
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    data_volume_bytes: Mapped[Optional[BigInteger]] = mapped_column(BigInteger, nullable=True)
    
    # Risk assessment
    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    risk_factors: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    
    # Chain of custody
    hash_value: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    previous_event_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    digital_signature: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    user: Mapped[Optional["User"]] = relationship("User")


class ThreatIntelligenceEvent(Base):
    """Threat intelligence and security event tracking."""
    __tablename__ = "threat_intelligence_events"
    __table_args__ = (
        Index("idx_threat_timestamp", "detected_at"),
        Index("idx_threat_type", "threat_type"),
        Index("idx_threat_severity", "severity"),
        Index("idx_threat_status", "status"),
        Index("idx_threat_ip", "source_ip"),
        {'schema': 'audit'}
    )
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=func.gen_random_uuid()
    )
    
    # Threat identification
    threat_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    threat_type: Mapped[ThreatType] = mapped_column(
        SQLAlchemyEnum(ThreatType), 
        nullable=False, 
        index=True
    )
    threat_name: Mapped[str] = mapped_column(String(200), nullable=False)
    threat_description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Severity and classification
    severity: Mapped[AuditEventSeverity] = mapped_column(
        SQLAlchemyEnum(AuditEventSeverity), 
        nullable=False, 
        index=True
    )
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    false_positive_probability: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    
    # Detection information
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        index=True
    )
    detection_method: Mapped[str] = mapped_column(String(100), nullable=False)
    detection_rule: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # Source information
    source_ip: Mapped[Optional[str]] = mapped_column(INET, nullable=True, index=True)
    source_country: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    source_asn: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), 
        nullable=True, 
        index=True
    )
    
    # Attack details
    attack_vector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    target_resource: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    attack_payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Threat intelligence
    indicators_of_compromise: Mapped[List[str]] = mapped_column(
        ARRAY(String), 
        nullable=False, 
        default=list
    )
    threat_actor: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    campaign_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Response and status
    status: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        default="DETECTED", 
        index=True
    )
    # Status: DETECTED, INVESTIGATING, CONTAINED, MITIGATED, CLOSED, FALSE_POSITIVE
    
    response_actions: Mapped[List[str]] = mapped_column(
        ARRAY(String), 
        nullable=False, 
        default=list
    )
    mitigation_steps: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timeline
    first_seen: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Impact assessment
    affected_systems: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    data_compromised: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    business_impact: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # Impact: NONE, LOW, MEDIUM, HIGH, CRITICAL
    
    # Additional context
    threat_context: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    external_references: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    
    # Relationships
    user: Mapped[Optional["User"]] = relationship("User")


class ComplianceAssessment(Base):
    """Compliance assessments and audit results."""
    __tablename__ = "compliance_assessments"
    __table_args__ = (
        Index("idx_compliance_standard", "compliance_standard"),
        Index("idx_compliance_status", "overall_status"),
        Index("idx_compliance_assessed", "assessed_at"),
        UniqueConstraint("compliance_standard", "assessment_date", name="uq_compliance_daily"),
    )
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=func.gen_random_uuid()
    )
    
    # Assessment identification
    assessment_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    compliance_standard: Mapped[ComplianceStandard] = mapped_column(
        SQLAlchemyEnum(ComplianceStandard), 
        nullable=False, 
        index=True
    )
    assessment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Assessment scope
    scope_description: Mapped[str] = mapped_column(Text, nullable=False)
    assessed_systems: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False)
    assessed_processes: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False)
    
    # Overall results
    overall_status: Mapped[ComplianceStatus] = mapped_column(
        SQLAlchemyEnum(ComplianceStatus), 
        nullable=False, 
        index=True
    )
    overall_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # Score from 0.0 to 100.0
    
    # Control results
    total_controls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    passed_controls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_controls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    not_applicable_controls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Detailed results
    control_results: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    # Structure: {control_id: {status, evidence, notes, remediation}}
    
    # Gap analysis
    identified_gaps: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    remediation_recommendations: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, 
        nullable=False, 
        default=dict
    )
    
    # Risk assessment
    compliance_risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    risk_factors: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    
    # Assessment metadata
    assessor_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), 
        nullable=True
    )
    assessment_method: Mapped[str] = mapped_column(String(50), nullable=False, default="AUTOMATED")
    # Methods: AUTOMATED, MANUAL, HYBRID
    
    evidence_collected: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    assessment_duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Timeline
    assessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    next_assessment_due: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )
    
    # Approval and sign-off
    approved_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    assessor: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assessor_id])
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by])


class ForensicInvestigation(Base):
    """Forensic investigation cases and evidence tracking."""
    __tablename__ = "forensic_investigations"
    __table_args__ = (
        Index("idx_forensic_status", "status"),
        Index("idx_forensic_priority", "priority"),
        Index("idx_forensic_created", "created_at"),
        Index("idx_forensic_investigator", "primary_investigator_id"),
    )
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=func.gen_random_uuid()
    )
    
    # Case identification
    case_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    case_name: Mapped[str] = mapped_column(String(200), nullable=False)
    case_description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Case classification
    case_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Types: SECURITY_INCIDENT, DATA_BREACH, INSIDER_THREAT, COMPLIANCE_VIOLATION
    
    priority: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        default="MEDIUM", 
        index=True
    )
    # Priority: LOW, MEDIUM, HIGH, CRITICAL, EMERGENCY
    
    # Investigation details
    incident_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    discovery_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reported_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    # Investigation team
    primary_investigator_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), 
        nullable=False, 
        index=True
    )
    investigation_team: Mapped[List[int]] = mapped_column(ARRAY(Integer), nullable=False, default=list)
    
    # Scope and impact
    affected_systems: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    affected_users: Mapped[List[int]] = mapped_column(ARRAY(Integer), nullable=False, default=list)
    estimated_impact: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Investigation status
    status: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        default="INITIATED", 
        index=True
    )
    # Status: INITIATED, EVIDENCE_COLLECTION, ANALYSIS, REPORTING, CLOSED
    
    # Timeline
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    investigation_started: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )
    investigation_completed: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )
    
    # Evidence and findings
    evidence_items: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    key_findings: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    investigation_notes: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Legal and compliance
    legal_hold: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    law_enforcement_notified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    regulatory_reporting_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # Chain of custody
    custody_chain: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB, 
        nullable=False, 
        default=list
    )
    evidence_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    
    # Final report
    final_report: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommendations: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    
    # Relationships
    reporter: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reported_by])
    primary_investigator: Mapped["User"] = relationship("User", foreign_keys=[primary_investigator_id])


class DataRetentionLog(Base):
    """Data retention and lifecycle management log."""
    __tablename__ = "data_retention_logs"
    __table_args__ = (
        Index("idx_retention_table", "table_name"),
        Index("idx_retention_action", "retention_action"),
        Index("idx_retention_executed", "executed_at"),
        {'schema': 'audit'}
    )
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=func.gen_random_uuid()
    )
    
    # Retention details
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("data_retention_policies.id"), 
        nullable=False
    )
    table_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    retention_action: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        index=True
    )
    # Actions: ARCHIVE, DELETE, ANONYMIZE, PURGE
    
    # Execution details
    records_affected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    criteria_applied: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    
    # Timing
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    execution_duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Results
    execution_status: Mapped[str] = mapped_column(String(20), nullable=False, default="SUCCESS")
    # Status: SUCCESS, FAILURE, PARTIAL, SKIPPED
    
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    warnings: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    
    # Compliance tracking
    compliance_reason: Mapped[str] = mapped_column(String(100), nullable=False)
    legal_basis: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Verification
    verification_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    executed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    # Relationships
    policy: Mapped["DataRetentionPolicy"] = relationship("DataRetentionPolicy")
    executor: Mapped[Optional["User"]] = relationship("User")