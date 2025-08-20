"""Enterprise Security Administration Service.

Comprehensive administrative security tools for enterprise compliance and management.
Provides real-time security metrics, compliance monitoring, threat detection,
user access management, and automated security responses.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, func, text, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.database.models._models import User, UserRole
from shared.database.models.security_models import (
    AuditLog, SecurityViolation, DataAccessLog, SecurityMetric,
    SecurityAction, UserSecurityTier, SecurityTier, SecurityRequirement,
    SecurityTierPolicy, SecurityActionType, ViolationSeverity
)
from shared.database.models.enhanced_2fa_models import (
    TwoFactorAuditLog, TwoFactorComplianceReport, UserTwoFactorGracePeriod,
    TwoFactorAdminOverride
)
from shared.services.security_audit_service import security_audit_service
from shared.services.enhanced_jwt_service import enhanced_jwt_service
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ComplianceStandard:
    """Compliance standard definitions and validators."""
    
    SOX = "SOX"
    HIPAA = "HIPAA" 
    GDPR = "GDPR"
    ISO27001 = "ISO27001"
    PCI_DSS = "PCI_DSS"
    
    @classmethod
    def get_all_standards(cls) -> List[str]:
        return [cls.SOX, cls.HIPAA, cls.GDPR, cls.ISO27001, cls.PCI_DSS]
    
    @classmethod
    def get_requirements(cls, standard: str) -> Dict[str, Any]:
        """Get compliance requirements for a standard."""
        requirements = {
            cls.SOX: {
                "audit_trail_retention_days": 2555,  # 7 years
                "privileged_access_monitoring": True,
                "change_management_controls": True,
                "financial_data_protection": True,
                "executive_certification": True
            },
            cls.HIPAA: {
                "data_encryption_required": True,
                "access_controls": True,
                "audit_trail_retention_days": 2190,  # 6 years
                "breach_notification_hours": 72,
                "workforce_training": True,
                "risk_assessment_frequency_months": 12
            },
            cls.GDPR: {
                "data_minimization": True,
                "explicit_consent": True,
                "right_to_erasure": True,
                "data_portability": True,
                "breach_notification_hours": 72,
                "privacy_by_design": True
            },
            cls.ISO27001: {
                "risk_management_framework": True,
                "information_security_policy": True,
                "access_control_procedures": True,
                "incident_response_plan": True,
                "continuous_monitoring": True,
                "management_review_frequency_months": 12
            },
            cls.PCI_DSS: {
                "network_security_controls": True,
                "encryption_in_transit": True,
                "encryption_at_rest": True,
                "access_control_measures": True,
                "vulnerability_management": True,
                "quarterly_scans": True
            }
        }
        return requirements.get(standard, {})


class ThreatIntelligence:
    """Threat intelligence and risk scoring."""
    
    @staticmethod
    async def calculate_risk_score(
        session: AsyncSession,
        user_id: int,
        context: Dict[str, Any]
    ) -> Tuple[float, List[str]]:
        """Calculate risk score for a user action."""
        risk_factors = []
        base_score = 0.0
        
        # Recent violations
        recent_violations = await session.execute(
            text("""
                SELECT COUNT(*) as violation_count, MAX(severity) as max_severity
                FROM audit.security_violations 
                WHERE user_id = :user_id 
                AND created_at > NOW() - INTERVAL '30 days'
            """),
            {"user_id": user_id}
        )
        violation_data = recent_violations.fetchone()
        
        if violation_data and violation_data.violation_count > 0:
            base_score += min(violation_data.violation_count * 0.2, 0.5)
            risk_factors.append(f"Recent violations: {violation_data.violation_count}")
        
        # Failed authentication attempts
        failed_attempts = await session.execute(
            text("""
                SELECT COUNT(*) as attempt_count
                FROM two_factor_audit_log 
                WHERE user_id = :user_id 
                AND action IN ('authentication_failed', 'setup_failed')
                AND created_at > NOW() - INTERVAL '24 hours'
            """),
            {"user_id": user_id}
        )
        failed_count = failed_attempts.scalar() or 0
        
        if failed_count > 5:
            base_score += min(failed_count * 0.1, 0.3)
            risk_factors.append(f"Failed auth attempts: {failed_count}")
        
        # Unusual time/location (if available in context)
        if context.get("unusual_time"):
            base_score += 0.2
            risk_factors.append("Unusual access time")
            
        if context.get("unusual_location"):
            base_score += 0.3
            risk_factors.append("Unusual access location")
        
        # Privilege escalation
        if context.get("privilege_escalation"):
            base_score += 0.4
            risk_factors.append("Privilege escalation detected")
        
        # Multiple concurrent sessions
        if context.get("concurrent_sessions", 0) > 3:
            base_score += 0.2
            risk_factors.append("Multiple concurrent sessions")
        
        return min(base_score, 1.0), risk_factors


class EnterpriseSecurityAdminService:
    """Enterprise Security Administration Service."""
    
    def __init__(self):
        self.logger = logger
        self.threat_intelligence = ThreatIntelligence()
    
    async def get_security_dashboard_metrics(
        self,
        session: AsyncSession,
        admin_user_id: int,
        time_range: str = "24h"
    ) -> Dict[str, Any]:
        """Get comprehensive security dashboard metrics."""
        
        # Set security context
        await security_audit_service.set_security_context(
            session=session,
            user_id=admin_user_id,
            service_name="enterprise_security_admin"
        )
        
        # Parse time range
        hours = self._parse_time_range(time_range)
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # Core security metrics
        metrics = {}
        
        # User statistics
        user_stats = await self._get_user_security_stats(session)
        metrics["user_security"] = user_stats
        
        # Authentication metrics
        auth_metrics = await self._get_authentication_metrics(session, since)
        metrics["authentication"] = auth_metrics
        
        # Violation metrics
        violation_metrics = await self._get_violation_metrics(session, since)
        metrics["violations"] = violation_metrics
        
        # Compliance status
        compliance_status = await self._get_compliance_status(session)
        metrics["compliance"] = compliance_status
        
        # Threat metrics
        threat_metrics = await self._get_threat_metrics(session, since)
        metrics["threats"] = threat_metrics
        
        # System health
        system_health = await self._get_system_health_metrics(session, since)
        metrics["system_health"] = system_health
        
        # Real-time alerts
        active_alerts = await self._get_active_security_alerts(session)
        metrics["active_alerts"] = active_alerts
        
        return {
            "dashboard_metrics": metrics,
            "generated_at": datetime.utcnow().isoformat(),
            "time_range": time_range,
            "admin_user_id": admin_user_id
        }
    
    async def get_user_access_management(
        self,
        session: AsyncSession,
        admin_user_id: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get comprehensive user access management data."""
        
        await security_audit_service.set_security_context(
            session=session,
            user_id=admin_user_id,
            service_name="enterprise_security_admin"
        )
        
        filters = filters or {}
        
        # Build user query with filters
        query = session.query(User).options(
            selectinload(User.security_tier)
        )
        
        # Apply filters
        if filters.get("role"):
            query = query.filter(User.role == filters["role"])
        
        if filters.get("security_tier"):
            query = query.join(UserSecurityTier).filter(
                UserSecurityTier.current_tier == filters["security_tier"]
            )
        
        if filters.get("search"):
            search_term = f"%{filters['search']}%"
            query = query.filter(
                or_(
                    User.email.ilike(search_term),
                    User.full_name.ilike(search_term)
                )
            )
        
        users = await query.all()
        
        # Get additional user data
        user_data = []
        for user in users:
            user_info = await self._get_user_access_details(session, user)
            user_data.append(user_info)
        
        # Get role statistics
        role_stats = await self._get_role_statistics(session)
        
        # Get privilege escalation events
        privilege_events = await self._get_privilege_escalation_events(session)
        
        return {
            "users": user_data,
            "role_statistics": role_stats,
            "privilege_escalation_events": privilege_events,
            "total_users": len(user_data),
            "filters_applied": filters
        }
    
    async def get_security_analytics_report(
        self,
        session: AsyncSession,
        admin_user_id: int,
        report_type: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Generate comprehensive security analytics report."""
        
        await security_audit_service.set_security_context(
            session=session,
            user_id=admin_user_id,
            service_name="enterprise_security_admin"
        )
        
        report_data = {}
        
        if report_type == "authentication_patterns":
            report_data = await self._generate_authentication_patterns_report(
                session, start_date, end_date
            )
        elif report_type == "failed_login_analysis":
            report_data = await self._generate_failed_login_analysis(
                session, start_date, end_date
            )
        elif report_type == "device_analytics":
            report_data = await self._generate_device_analytics_report(
                session, start_date, end_date
            )
        elif report_type == "compliance_audit":
            report_data = await self._generate_compliance_audit_report(
                session, start_date, end_date
            )
        elif report_type == "threat_assessment":
            report_data = await self._generate_threat_assessment_report(
                session, start_date, end_date
            )
        else:
            raise ValueError(f"Unknown report type: {report_type}")
        
        # Save report to audit log
        await self._log_report_generation(
            session, admin_user_id, report_type, report_data
        )
        
        return {
            "report_type": report_type,
            "generated_by": admin_user_id,
            "generated_at": datetime.utcnow().isoformat(),
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "data": report_data
        }
    
    async def enforce_security_policy(
        self,
        session: AsyncSession,
        admin_user_id: int,
        policy_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enforce a security policy across the platform."""
        
        await security_audit_service.set_security_context(
            session=session,
            user_id=admin_user_id,
            service_name="enterprise_security_admin"
        )
        
        policy_id = uuid4()
        enforcement_results = []
        
        try:
            # Create policy record
            policy = SecurityTierPolicy(
                id=policy_id,
                policy_name=policy_config["name"],
                description=policy_config.get("description", ""),
                minimum_tier=SecurityTier(policy_config["minimum_tier"]),
                allowed_tiers=policy_config.get("allowed_tiers", []),
                policy_rules=policy_config.get("rules", {}),
                enforcement_level=policy_config.get("enforcement_level", "ADVISORY"),
                created_by_user_id=admin_user_id,
                effective_date=datetime.utcnow()
            )
            session.add(policy)
            
            # Apply policy to affected users
            affected_users = await self._identify_affected_users(session, policy_config)
            
            for user in affected_users:
                result = await self._apply_policy_to_user(
                    session, user, policy_config, admin_user_id
                )
                enforcement_results.append(result)
            
            await session.commit()
            
            return {
                "policy_id": str(policy_id),
                "enforcement_results": enforcement_results,
                "affected_users_count": len(affected_users),
                "success": True
            }
            
        except Exception as e:
            await session.rollback()
            self.logger.error(f"Policy enforcement failed: {e}")
            return {
                "policy_id": str(policy_id),
                "error": str(e),
                "success": False
            }
    
    async def trigger_automated_response(
        self,
        session: AsyncSession,
        threat_type: str,
        threat_data: Dict[str, Any],
        admin_user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Trigger automated security response to detected threats."""
        
        if admin_user_id:
            await security_audit_service.set_security_context(
                session=session,
                user_id=admin_user_id,
                service_name="enterprise_security_admin"
            )
        
        response_actions = []
        
        try:
            # Determine appropriate response actions
            actions = await self._determine_response_actions(threat_type, threat_data)
            
            for action in actions:
                result = await self._execute_security_action(
                    session, action, threat_data, admin_user_id
                )
                response_actions.append(result)
            
            await session.commit()
            
            return {
                "threat_type": threat_type,
                "actions_executed": response_actions,
                "success": True,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            await session.rollback()
            self.logger.error(f"Automated response failed: {e}")
            return {
                "threat_type": threat_type,
                "error": str(e),
                "success": False
            }
    
    # Helper methods
    
    def _parse_time_range(self, time_range: str) -> int:
        """Parse time range string to hours."""
        mapping = {
            "1h": 1, "6h": 6, "12h": 12, "24h": 24,
            "7d": 168, "30d": 720, "90d": 2160
        }
        return mapping.get(time_range, 24)
    
    async def _get_user_security_stats(self, session: AsyncSession) -> Dict[str, Any]:
        """Get user security statistics."""
        
        # Total users by tier
        tier_stats = await session.execute(
            text("""
                SELECT 
                    COALESCE(ust.current_tier::text, 'standard') as tier,
                    COUNT(*) as count
                FROM users u
                LEFT JOIN user_security_tiers ust ON u.id = ust.user_id
                GROUP BY ust.current_tier
            """)
        )
        
        tier_distribution = {row.tier: row.count for row in tier_stats}
        
        # 2FA status
        twofa_stats = await session.execute(
            text("""
                SELECT 
                    COUNT(*) as total_users,
                    COUNT(ut.user_id) as users_with_totp,
                    COUNT(up.user_id) as users_with_passkey
                FROM users u
                LEFT JOIN user_totp ut ON u.id = ut.user_id AND ut.is_active = true
                LEFT JOIN user_passkeys up ON u.id = up.user_id AND up.is_active = true
            """)
        )
        twofa_data = twofa_stats.fetchone()
        
        # Active users (last 30 days)
        active_users = await session.execute(
            text("""
                SELECT COUNT(DISTINCT user_id) as active_count
                FROM audit.audit_log
                WHERE created_at > NOW() - INTERVAL '30 days'
                AND user_id IS NOT NULL
            """)
        )
        
        return {
            "tier_distribution": tier_distribution,
            "two_factor_auth": {
                "total_users": twofa_data.total_users,
                "totp_users": twofa_data.users_with_totp,
                "passkey_users": twofa_data.users_with_passkey,
                "coverage_percentage": (
                    (twofa_data.users_with_totp + twofa_data.users_with_passkey) / 
                    max(twofa_data.total_users, 1) * 100
                )
            },
            "active_users_30d": active_users.scalar() or 0
        }
    
    async def _get_authentication_metrics(
        self, session: AsyncSession, since: datetime
    ) -> Dict[str, Any]:
        """Get authentication metrics."""
        
        # Authentication attempts
        auth_stats = await session.execute(
            text("""
                SELECT 
                    action,
                    success,
                    COUNT(*) as count
                FROM two_factor_audit_log
                WHERE created_at > :since
                AND action IN ('authentication_success', 'authentication_failed')
                GROUP BY action, success
            """),
            {"since": since}
        )
        
        auth_data = {"successful": 0, "failed": 0}
        for row in auth_stats:
            if row.success:
                auth_data["successful"] += row.count
            else:
                auth_data["failed"] += row.count
        
        # Geographic distribution (if available)
        geo_stats = await session.execute(
            text("""
                SELECT 
                    COALESCE(ip_address, 'unknown') as location,
                    COUNT(*) as count
                FROM two_factor_audit_log
                WHERE created_at > :since
                AND action = 'authentication_success'
                GROUP BY ip_address
                ORDER BY count DESC
                LIMIT 10
            """),
            {"since": since}
        )
        
        geographic_distribution = [
            {"location": row.location, "count": row.count}
            for row in geo_stats
        ]
        
        return {
            "authentication_attempts": auth_data,
            "success_rate": (
                auth_data["successful"] / 
                max(auth_data["successful"] + auth_data["failed"], 1) * 100
            ),
            "geographic_distribution": geographic_distribution
        }
    
    async def _get_violation_metrics(
        self, session: AsyncSession, since: datetime
    ) -> Dict[str, Any]:
        """Get security violation metrics."""
        
        violation_stats = await session.execute(
            text("""
                SELECT 
                    violation_type,
                    severity,
                    COUNT(*) as count,
                    COUNT(CASE WHEN blocked = true THEN 1 END) as blocked_count
                FROM audit.security_violations
                WHERE created_at > :since
                GROUP BY violation_type, severity
                ORDER BY count DESC
            """),
            {"since": since}
        )
        
        violations_by_type = {}
        violations_by_severity = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        total_blocked = 0
        
        for row in violation_stats:
            violations_by_type[row.violation_type] = {
                "count": row.count,
                "blocked": row.blocked_count,
                "severity": row.severity
            }
            violations_by_severity[row.severity] += row.count
            total_blocked += row.blocked_count
        
        return {
            "violations_by_type": violations_by_type,
            "violations_by_severity": violations_by_severity,
            "total_blocked": total_blocked
        }
    
    async def _get_compliance_status(self, session: AsyncSession) -> Dict[str, Any]:
        """Get compliance status for all standards."""
        
        compliance_status = {}
        
        for standard in ComplianceStandard.get_all_standards():
            requirements = ComplianceStandard.get_requirements(standard)
            status = await self._check_compliance_standard(session, standard, requirements)
            compliance_status[standard] = status
        
        return compliance_status
    
    async def _check_compliance_standard(
        self, session: AsyncSession, standard: str, requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check compliance for a specific standard."""
        
        compliance_checks = []
        overall_score = 0
        
        if standard == ComplianceStandard.SOX:
            # SOX compliance checks
            checks = await self._check_sox_compliance(session, requirements)
            compliance_checks.extend(checks)
        elif standard == ComplianceStandard.HIPAA:
            # HIPAA compliance checks
            checks = await self._check_hipaa_compliance(session, requirements)
            compliance_checks.extend(checks)
        elif standard == ComplianceStandard.GDPR:
            # GDPR compliance checks
            checks = await self._check_gdpr_compliance(session, requirements)
            compliance_checks.extend(checks)
        
        # Calculate overall score
        if compliance_checks:
            passed_checks = sum(1 for check in compliance_checks if check["status"] == "PASS")
            overall_score = (passed_checks / len(compliance_checks)) * 100
        
        return {
            "standard": standard,
            "overall_score": overall_score,
            "status": "COMPLIANT" if overall_score >= 95 else "NON_COMPLIANT",
            "checks": compliance_checks,
            "last_assessed": datetime.utcnow().isoformat()
        }
    
    async def _check_sox_compliance(
        self, session: AsyncSession, requirements: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Check SOX compliance requirements."""
        
        checks = []
        
        # Audit trail retention
        oldest_audit = await session.execute(
            text("SELECT MIN(created_at) FROM audit.audit_log")
        )
        oldest_date = oldest_audit.scalar()
        
        if oldest_date:
            retention_days = (datetime.utcnow() - oldest_date).days
            required_days = requirements.get("audit_trail_retention_days", 2555)
            
            checks.append({
                "requirement": "Audit trail retention (7 years)",
                "status": "PASS" if retention_days >= required_days else "FAIL",
                "details": f"Current retention: {retention_days} days, Required: {required_days} days"
            })
        
        # Privileged access monitoring
        privileged_access_logs = await session.execute(
            text("""
                SELECT COUNT(*) FROM audit.audit_log 
                WHERE created_at > NOW() - INTERVAL '24 hours'
                AND security_context->>'privilege_level' = 'admin'
            """)
        )
        
        checks.append({
            "requirement": "Privileged access monitoring",
            "status": "PASS" if privileged_access_logs.scalar() > 0 else "PARTIAL",
            "details": f"Privileged actions logged in last 24h: {privileged_access_logs.scalar()}"
        })
        
        return checks
    
    async def _check_hipaa_compliance(
        self, session: AsyncSession, requirements: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Check HIPAA compliance requirements."""
        
        checks = []
        
        # Access controls check
        user_2fa_count = await session.execute(
            text("""
                SELECT COUNT(DISTINCT u.id) as total_users,
                       COUNT(DISTINCT ut.user_id) as totp_users,
                       COUNT(DISTINCT up.user_id) as passkey_users
                FROM users u
                LEFT JOIN user_totp ut ON u.id = ut.user_id AND ut.is_active = true
                LEFT JOIN user_passkeys up ON u.id = up.user_id AND up.is_active = true
            """)
        )
        
        user_data = user_2fa_count.fetchone()
        twofa_coverage = (
            (user_data.totp_users + user_data.passkey_users) / 
            max(user_data.total_users, 1) * 100
        )
        
        checks.append({
            "requirement": "Multi-factor authentication",
            "status": "PASS" if twofa_coverage >= 95 else "FAIL",
            "details": f"2FA coverage: {twofa_coverage:.1f}%"
        })
        
        # Audit trail retention
        audit_retention_check = await self._check_audit_retention(
            session, requirements.get("audit_trail_retention_days", 2190)
        )
        checks.append(audit_retention_check)
        
        return checks
    
    async def _check_gdpr_compliance(
        self, session: AsyncSession, requirements: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Check GDPR compliance requirements."""
        
        checks = []
        
        # Data retention policies
        retention_policies = await session.execute(
            text("SELECT COUNT(*) FROM data_retention_policies WHERE is_active = true")
        )
        
        checks.append({
            "requirement": "Data retention policies",
            "status": "PASS" if retention_policies.scalar() > 0 else "FAIL",
            "details": f"Active retention policies: {retention_policies.scalar()}"
        })
        
        # Privacy requests handling
        privacy_requests = await session.execute(
            text("""
                SELECT 
                    COUNT(*) as total_requests,
                    COUNT(CASE WHEN status = 'COMPLETED' THEN 1 END) as completed_requests
                FROM privacy_requests
                WHERE requested_at > NOW() - INTERVAL '30 days'
            """)
        )
        
        request_data = privacy_requests.fetchone()
        completion_rate = (
            request_data.completed_requests / max(request_data.total_requests, 1) * 100
            if request_data.total_requests > 0 else 100
        )
        
        checks.append({
            "requirement": "Privacy request handling",
            "status": "PASS" if completion_rate >= 95 else "PARTIAL",
            "details": f"Completion rate: {completion_rate:.1f}% (last 30 days)"
        })
        
        return checks
    
    async def _check_audit_retention(
        self, session: AsyncSession, required_days: int
    ) -> Dict[str, Any]:
        """Check audit log retention compliance."""
        
        oldest_audit = await session.execute(
            text("SELECT MIN(created_at) FROM audit.audit_log")
        )
        oldest_date = oldest_audit.scalar()
        
        if not oldest_date:
            return {
                "requirement": f"Audit retention ({required_days} days)",
                "status": "UNKNOWN",
                "details": "No audit logs found"
            }
        
        retention_days = (datetime.utcnow() - oldest_date).days
        
        return {
            "requirement": f"Audit retention ({required_days} days)",
            "status": "PASS" if retention_days >= required_days else "FAIL",
            "details": f"Current retention: {retention_days} days"
        }
    
    async def _get_threat_metrics(
        self, session: AsyncSession, since: datetime
    ) -> Dict[str, Any]:
        """Get threat detection metrics."""
        
        # High-risk events
        high_risk_events = await session.execute(
            text("""
                SELECT COUNT(*) FROM audit.security_violations
                WHERE created_at > :since
                AND severity IN ('HIGH', 'CRITICAL')
            """),
            {"since": since}
        )
        
        # Automated responses
        automated_responses = await session.execute(
            text("""
                SELECT 
                    action_type,
                    COUNT(*) as count,
                    COUNT(CASE WHEN success = true THEN 1 END) as successful_count
                FROM security_actions
                WHERE created_at > :since
                AND auto_created = true
                GROUP BY action_type
            """),
            {"since": since}
        )
        
        response_stats = {}
        for row in automated_responses:
            response_stats[row.action_type] = {
                "total": row.count,
                "successful": row.successful_count,
                "success_rate": (row.successful_count / max(row.count, 1)) * 100
            }
        
        return {
            "high_risk_events": high_risk_events.scalar() or 0,
            "automated_responses": response_stats,
            "threat_level": self._calculate_threat_level(high_risk_events.scalar() or 0)
        }
    
    def _calculate_threat_level(self, high_risk_events: int) -> str:
        """Calculate current threat level."""
        if high_risk_events >= 10:
            return "CRITICAL"
        elif high_risk_events >= 5:
            return "HIGH"
        elif high_risk_events >= 2:
            return "MEDIUM"
        else:
            return "LOW"
    
    async def _get_system_health_metrics(
        self, session: AsyncSession, since: datetime
    ) -> Dict[str, Any]:
        """Get system health metrics."""
        
        # Service availability (from security metrics)
        service_metrics = await session.execute(
            text("""
                SELECT 
                    service_name,
                    AVG(metric_value) as avg_value,
                    MAX(metric_value) as max_value
                FROM audit.security_metrics
                WHERE recorded_at > :since
                AND metric_type = 'availability'
                GROUP BY service_name
            """),
            {"since": since}
        )
        
        service_health = {}
        for row in service_metrics:
            service_health[row.service_name] = {
                "average_availability": row.avg_value,
                "max_availability": row.max_value
            }
        
        return {
            "service_health": service_health,
            "overall_health": "HEALTHY"  # TODO: Calculate based on metrics
        }
    
    async def _get_active_security_alerts(self, session: AsyncSession) -> List[Dict[str, Any]]:
        """Get active security alerts."""
        
        active_violations = await session.execute(
            text("""
                SELECT 
                    id,
                    violation_type,
                    severity,
                    user_id,
                    created_at,
                    violation_details
                FROM audit.security_violations
                WHERE resolved = false
                AND created_at > NOW() - INTERVAL '24 hours'
                ORDER BY 
                    CASE severity 
                        WHEN 'CRITICAL' THEN 1
                        WHEN 'HIGH' THEN 2
                        WHEN 'MEDIUM' THEN 3
                        ELSE 4
                    END,
                    created_at DESC
                LIMIT 20
            """)
        )
        
        alerts = []
        for row in active_violations:
            alerts.append({
                "id": str(row.id),
                "type": row.violation_type,
                "severity": row.severity,
                "user_id": row.user_id,
                "created_at": row.created_at.isoformat(),
                "details": row.violation_details
            })
        
        return alerts


# Create global instance
enterprise_security_admin_service = EnterpriseSecurityAdminService()