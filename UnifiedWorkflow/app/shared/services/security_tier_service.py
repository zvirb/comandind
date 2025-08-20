"""Security tier management service for graduated security implementation."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from shared.database.models.security_models import (
    UserSecurityTier, SecurityRequirement, SecurityTierPolicy, CertificateRequest,
    SecurityTierUpgradeLog, SecurityTier, SecurityRequirementType, SecurityRequirementStatus
)
from shared.database.models._models import User
from shared.database.models.auth_models import UserTwoFactorAuth
from shared.services.security_audit_service import security_audit_service
from shared.utils.database_setup import get_async_session

logger = logging.getLogger(__name__)


class SecurityTierService:
    """Comprehensive security tier management and upgrade orchestration."""
    
    def __init__(self):
        self.logger = logger
        
        # Security tier definitions with requirements and features
        self.tier_definitions = {
            SecurityTier.STANDARD: {
                "name": "Standard Security",
                "description": "Basic security with username/password + mandatory 2FA",
                "requirements": [SecurityRequirementType.TWO_FACTOR_AUTH],
                "features": [
                    "Username/password authentication",
                    "Mandatory TOTP 2FA", 
                    "Basic HTTPS encryption",
                    "Standard monitoring",
                    "Basic audit trail"
                ],
                "target_audience": "Personal users, basic enterprise needs",
                "icon": "🟢",
                "upgrade_time_estimate": "5-10 minutes"
            },
            SecurityTier.ENHANCED: {
                "name": "Enhanced Security",
                "description": "Standard + automatic client certificates + device trust",
                "requirements": [
                    SecurityRequirementType.TWO_FACTOR_AUTH,
                    SecurityRequirementType.CLIENT_CERTIFICATE,
                    SecurityRequirementType.DEVICE_TRUST
                ],
                "features": [
                    "All Standard features",
                    "Automatic client certificate provisioning",
                    "mTLS encryption",
                    "Device trust management",
                    "Enhanced monitoring",
                    "Advanced audit trails",
                    "Certificate automation"
                ],
                "target_audience": "Business users, security-conscious individuals",
                "icon": "🟡",
                "upgrade_time_estimate": "15-30 minutes"
            },
            SecurityTier.ENTERPRISE: {
                "name": "Enterprise Security",
                "description": "Enhanced + hardware security keys + advanced threat detection",
                "requirements": [
                    SecurityRequirementType.TWO_FACTOR_AUTH,
                    SecurityRequirementType.CLIENT_CERTIFICATE,
                    SecurityRequirementType.DEVICE_TRUST,
                    SecurityRequirementType.HARDWARE_KEY,
                    SecurityRequirementType.THREAT_DETECTION,
                    SecurityRequirementType.COMPLIANCE_REPORTING
                ],
                "features": [
                    "All Enhanced features",
                    "WebAuthn/FIDO2 hardware keys",
                    "Advanced threat detection",
                    "Real-time security monitoring",
                    "Compliance reporting",
                    "Zero-trust architecture",
                    "Advanced device management",
                    "Enterprise audit logs"
                ],
                "target_audience": "Enterprise customers, high-security environments",
                "icon": "🔴",
                "upgrade_time_estimate": "30-60 minutes"
            }
        }
    
    async def get_user_security_tier(
        self, 
        session: AsyncSession, 
        user_id: int
    ) -> UserSecurityTier:
        """Get or create user security tier configuration."""
        try:
            # Try to get existing security tier
            result = await session.execute(
                select(UserSecurityTier).where(UserSecurityTier.user_id == user_id)
            )
            user_tier = result.scalar_one_or_none()
            
            if not user_tier:
                # Create default security tier for new user
                user_tier = UserSecurityTier(
                    user_id=user_id,
                    current_tier=SecurityTier.STANDARD,
                    security_config={},
                    tier_features=self.tier_definitions[SecurityTier.STANDARD]["features"]
                )
                session.add(user_tier)
                await session.commit()
                
                # Initialize default requirements
                await self._initialize_user_requirements(session, user_id)
                
                self.logger.info(f"Created default security tier for user {user_id}")
            
            return user_tier
            
        except Exception as e:
            self.logger.error(f"Failed to get user security tier: {str(e)}")
            await session.rollback()
            raise
    
    async def assess_tier_eligibility(
        self, 
        session: AsyncSession, 
        user_id: int,
        target_tier: SecurityTier
    ) -> Dict[str, Any]:
        """Assess user's eligibility for a security tier upgrade."""
        try:
            current_tier = await self.get_user_security_tier(session, user_id)
            
            # Get current requirement status
            requirements_result = await session.execute(
                select(SecurityRequirement).where(
                    and_(
                        SecurityRequirement.user_id == user_id,
                        SecurityRequirement.required_for_tier == target_tier
                    )
                )
            )
            requirements = list(requirements_result.scalars().all())
            
            # Check each requirement
            requirement_status = {}
            total_requirements = len(self.tier_definitions[target_tier]["requirements"])
            completed_requirements = 0
            
            for req_type in self.tier_definitions[target_tier]["requirements"]:
                req = next((r for r in requirements if r.requirement_type == req_type), None)
                
                if req:
                    status = req.status
                    if status == SecurityRequirementStatus.COMPLETED:
                        completed_requirements += 1
                else:
                    # Create missing requirement
                    status = SecurityRequirementStatus.NOT_CONFIGURED
                    await self._create_requirement(session, user_id, req_type, target_tier)
                
                requirement_status[req_type.value] = {
                    "status": status.value if req else SecurityRequirementStatus.NOT_CONFIGURED.value,
                    "completed": status == SecurityRequirementStatus.COMPLETED if req else False,
                    "error_message": req.error_message if req else None,
                    "last_validated": req.last_validated_at.isoformat() if req and req.last_validated_at else None
                }
            
            # Calculate eligibility
            completion_percentage = (completed_requirements / total_requirements * 100) if total_requirements > 0 else 0
            is_eligible = completed_requirements == total_requirements
            
            # Check administrative policies
            policy_restrictions = await self._check_policy_restrictions(session, user_id, target_tier)
            
            return {
                "current_tier": current_tier.current_tier.value,
                "target_tier": target_tier.value,
                "is_eligible": is_eligible and not policy_restrictions["blocked"],
                "completion_percentage": completion_percentage,
                "completed_requirements": completed_requirements,
                "total_requirements": total_requirements,
                "requirement_status": requirement_status,
                "tier_definition": self.tier_definitions[target_tier],
                "policy_restrictions": policy_restrictions,
                "upgrade_in_progress": current_tier.upgrade_in_progress,
                "estimated_upgrade_time": self.tier_definitions[target_tier]["upgrade_time_estimate"]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to assess tier eligibility: {str(e)}")
            raise
    
    async def start_tier_upgrade(
        self, 
        session: AsyncSession, 
        user_id: int,
        target_tier: SecurityTier,
        upgrade_reason: Optional[str] = None
    ) -> str:
        """Start security tier upgrade process."""
        try:
            current_tier = await self.get_user_security_tier(session, user_id)
            
            # Check if upgrade is already in progress
            if current_tier.upgrade_in_progress:
                raise ValueError("Security tier upgrade already in progress")
            
            # Verify eligibility
            eligibility = await self.assess_tier_eligibility(session, user_id, target_tier)
            if not eligibility["is_eligible"]:
                missing_reqs = [
                    req_type for req_type, status in eligibility["requirement_status"].items()
                    if not status["completed"]
                ]
                raise ValueError(f"User not eligible for upgrade. Missing requirements: {missing_reqs}")
            
            # Create upgrade log
            upgrade_log = SecurityTierUpgradeLog(
                user_id=user_id,
                from_tier=current_tier.current_tier,
                to_tier=target_tier,
                status="STARTED",
                progress_percentage=0,
                current_step="Initializing upgrade",
                upgrade_reason=upgrade_reason,
                upgrade_method="USER_INITIATED"
            )
            session.add(upgrade_log)
            
            # Update user tier status
            current_tier.upgrade_in_progress = True
            current_tier.requested_tier = target_tier
            current_tier.upgrade_started_at = datetime.utcnow()
            
            await session.commit()
            
            # Start async upgrade process
            await self._execute_tier_upgrade(session, user_id, str(upgrade_log.id), target_tier)
            
            self.logger.info(f"Started security tier upgrade for user {user_id} to {target_tier.value}")
            return str(upgrade_log.id)
            
        except Exception as e:
            self.logger.error(f"Failed to start tier upgrade: {str(e)}")
            await session.rollback()
            raise
    
    async def get_upgrade_progress(
        self, 
        session: AsyncSession, 
        upgrade_id: str
    ) -> Dict[str, Any]:
        """Get security tier upgrade progress."""
        try:
            result = await session.execute(
                select(SecurityTierUpgradeLog).where(SecurityTierUpgradeLog.id == upgrade_id)
            )
            upgrade_log = result.scalar_one_or_none()
            
            if not upgrade_log:
                raise ValueError("Upgrade log not found")
            
            return {
                "upgrade_id": str(upgrade_log.id),
                "status": upgrade_log.status,
                "progress_percentage": upgrade_log.progress_percentage,
                "current_step": upgrade_log.current_step,
                "from_tier": upgrade_log.from_tier.value,
                "to_tier": upgrade_log.to_tier.value,
                "started_at": upgrade_log.started_at.isoformat(),
                "completed_at": upgrade_log.completed_at.isoformat() if upgrade_log.completed_at else None,
                "requirements_completed": upgrade_log.requirements_completed,
                "requirements_failed": upgrade_log.requirements_failed,
                "error_details": upgrade_log.error_details,
                "retry_count": upgrade_log.retry_count
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get upgrade progress: {str(e)}")
            raise
    
    async def validate_requirement(
        self, 
        session: AsyncSession, 
        user_id: int,
        requirement_type: SecurityRequirementType
    ) -> bool:
        """Validate a specific security requirement."""
        try:
            if requirement_type == SecurityRequirementType.TWO_FACTOR_AUTH:
                return await self._validate_2fa_requirement(session, user_id)
            elif requirement_type == SecurityRequirementType.CLIENT_CERTIFICATE:
                return await self._validate_certificate_requirement(session, user_id)
            elif requirement_type == SecurityRequirementType.DEVICE_TRUST:
                return await self._validate_device_trust_requirement(session, user_id)
            elif requirement_type == SecurityRequirementType.HARDWARE_KEY:
                return await self._validate_hardware_key_requirement(session, user_id)
            elif requirement_type == SecurityRequirementType.THREAT_DETECTION:
                return await self._validate_threat_detection_requirement(session, user_id)
            elif requirement_type == SecurityRequirementType.COMPLIANCE_REPORTING:
                return await self._validate_compliance_requirement(session, user_id)
            else:
                self.logger.warning(f"Unknown requirement type: {requirement_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to validate requirement {requirement_type}: {str(e)}")
            return False
    
    async def get_security_dashboard_data(
        self, 
        session: AsyncSession, 
        user_id: int
    ) -> Dict[str, Any]:
        """Get comprehensive security dashboard data."""
        try:
            current_tier = await self.get_user_security_tier(session, user_id)
            
            # Get available tiers with eligibility
            available_tiers = {}
            for tier in SecurityTier:
                if tier != current_tier.current_tier:
                    eligibility = await self.assess_tier_eligibility(session, user_id, tier)
                    available_tiers[tier.value] = eligibility
            
            # Get recent upgrade history
            upgrades_result = await session.execute(
                select(SecurityTierUpgradeLog)
                .where(SecurityTierUpgradeLog.user_id == user_id)
                .order_by(desc(SecurityTierUpgradeLog.started_at))
                .limit(5)
            )
            recent_upgrades = [
                {
                    "id": str(upgrade.id),
                    "from_tier": upgrade.from_tier.value,
                    "to_tier": upgrade.to_tier.value,
                    "status": upgrade.status,
                    "started_at": upgrade.started_at.isoformat(),
                    "completed_at": upgrade.completed_at.isoformat() if upgrade.completed_at else None
                }
                for upgrade in upgrades_result.scalars().all()
            ]
            
            # Get security metrics
            security_metrics = await self._get_user_security_metrics(session, user_id)
            
            return {
                "current_tier": {
                    "tier": current_tier.current_tier.value,
                    "definition": self.tier_definitions[current_tier.current_tier],
                    "upgrade_in_progress": current_tier.upgrade_in_progress,
                    "requested_tier": current_tier.requested_tier.value if current_tier.requested_tier else None,
                    "features": current_tier.tier_features,
                    "security_config": current_tier.security_config
                },
                "available_tiers": available_tiers,
                "recent_upgrades": recent_upgrades,
                "security_metrics": security_metrics,
                "tier_definitions": {tier.value: definition for tier, definition in self.tier_definitions.items()}
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get security dashboard data: {str(e)}")
            raise
    
    async def _initialize_user_requirements(
        self, 
        session: AsyncSession, 
        user_id: int
    ) -> None:
        """Initialize security requirements for a new user."""
        try:
            for tier, definition in self.tier_definitions.items():
                for req_type in definition["requirements"]:
                    await self._create_requirement(session, user_id, req_type, tier)
            
            await session.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to initialize user requirements: {str(e)}")
            await session.rollback()
            raise
    
    async def _create_requirement(
        self, 
        session: AsyncSession, 
        user_id: int,
        requirement_type: SecurityRequirementType,
        required_for_tier: SecurityTier
    ) -> SecurityRequirement:
        """Create a security requirement record."""
        requirement = SecurityRequirement(
            user_id=user_id,
            requirement_type=requirement_type,
            required_for_tier=required_for_tier,
            status=SecurityRequirementStatus.NOT_CONFIGURED
        )
        session.add(requirement)
        return requirement
    
    async def _execute_tier_upgrade(
        self, 
        session: AsyncSession, 
        user_id: int,
        upgrade_id: str,
        target_tier: SecurityTier
    ) -> None:
        """Execute the actual tier upgrade process."""
        try:
            # Get upgrade log
            result = await session.execute(
                select(SecurityTierUpgradeLog).where(SecurityTierUpgradeLog.id == upgrade_id)
            )
            upgrade_log = result.scalar_one()
            
            # Update progress
            upgrade_log.status = "IN_PROGRESS"
            upgrade_log.progress_percentage = 10
            upgrade_log.current_step = "Validating requirements"
            
            # Validate all requirements
            requirements = self.tier_definitions[target_tier]["requirements"]
            completed_requirements = []
            failed_requirements = []
            
            for i, req_type in enumerate(requirements):
                progress = 20 + (i * 60 // len(requirements))
                upgrade_log.progress_percentage = progress
                upgrade_log.current_step = f"Validating {req_type.value}"
                await session.commit()
                
                is_valid = await self.validate_requirement(session, user_id, req_type)
                
                if is_valid:
                    completed_requirements.append(req_type.value)
                    # Update requirement status
                    await self._update_requirement_status(
                        session, user_id, req_type, SecurityRequirementStatus.COMPLETED
                    )
                else:
                    failed_requirements.append(req_type.value)
                    await self._update_requirement_status(
                        session, user_id, req_type, SecurityRequirementStatus.FAILED
                    )
            
            upgrade_log.requirements_completed = completed_requirements
            upgrade_log.requirements_failed = failed_requirements
            
            # Check if all requirements are met
            if len(failed_requirements) == 0:
                # Complete upgrade
                upgrade_log.status = "COMPLETED"
                upgrade_log.progress_percentage = 100
                upgrade_log.current_step = "Upgrade completed successfully"
                upgrade_log.completed_at = datetime.utcnow()
                
                # Update user tier
                user_tier = await self.get_user_security_tier(session, user_id)
                user_tier.current_tier = target_tier
                user_tier.requested_tier = None
                user_tier.upgrade_in_progress = False
                user_tier.upgrade_completed_at = datetime.utcnow()
                user_tier.tier_features = self.tier_definitions[target_tier]["features"]
                
                self.logger.info(f"Successfully upgraded user {user_id} to {target_tier.value}")
                
            else:
                # Upgrade failed
                upgrade_log.status = "FAILED"
                upgrade_log.error_details = {
                    "failed_requirements": failed_requirements,
                    "message": "One or more security requirements failed validation"
                }
                
                # Reset user tier upgrade status
                user_tier = await self.get_user_security_tier(session, user_id)
                user_tier.upgrade_in_progress = False
                user_tier.requested_tier = None
                
                self.logger.warning(f"Failed to upgrade user {user_id} to {target_tier.value}: {failed_requirements}")
            
            await session.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to execute tier upgrade: {str(e)}")
            # Update upgrade log with error
            try:
                upgrade_log.status = "FAILED"
                upgrade_log.error_details = {"error": str(e)}
                await session.commit()
            except:
                pass
            raise
    
    async def _update_requirement_status(
        self, 
        session: AsyncSession, 
        user_id: int,
        requirement_type: SecurityRequirementType,
        status: SecurityRequirementStatus
    ) -> None:
        """Update the status of a security requirement."""
        result = await session.execute(
            select(SecurityRequirement).where(
                and_(
                    SecurityRequirement.user_id == user_id,
                    SecurityRequirement.requirement_type == requirement_type
                )
            )
        )
        
        for requirement in result.scalars().all():
            requirement.status = status
            requirement.last_validated_at = datetime.utcnow()
            if status == SecurityRequirementStatus.COMPLETED:
                requirement.completed_at = datetime.utcnow()
    
    async def _validate_2fa_requirement(self, session: AsyncSession, user_id: int) -> bool:
        """Validate 2FA requirement."""
        try:
            # Check if user has 2FA enabled
            result = await session.execute(
                select(UserTwoFactorAuth).where(UserTwoFactorAuth.user_id == user_id)
            )
            tfa_record = result.scalar_one_or_none()
            
            return tfa_record is not None and tfa_record.totp_enabled
            
        except Exception as e:
            self.logger.error(f"Failed to validate 2FA requirement: {str(e)}")
            return False
    
    async def _validate_certificate_requirement(self, session: AsyncSession, user_id: int) -> bool:
        """Validate client certificate requirement."""
        try:
            # Check if user has valid client certificates
            result = await session.execute(
                select(CertificateRequest).where(
                    and_(
                        CertificateRequest.user_id == user_id,
                        CertificateRequest.status == "READY",
                        CertificateRequest.expires_at > datetime.utcnow()
                    )
                )
            )
            
            active_certs = list(result.scalars().all())
            return len(active_certs) > 0
            
        except Exception as e:
            self.logger.error(f"Failed to validate certificate requirement: {str(e)}")
            return False
    
    async def _validate_device_trust_requirement(self, session: AsyncSession, user_id: int) -> bool:
        """Validate device trust requirement."""
        try:
            # Check if user has registered trusted devices
            from shared.database.models.auth_models import RegisteredDevice
            
            result = await session.execute(
                select(RegisteredDevice).where(
                    and_(
                        RegisteredDevice.user_id == user_id,
                        RegisteredDevice.is_trusted == True,
                        RegisteredDevice.is_active == True
                    )
                )
            )
            
            trusted_devices = list(result.scalars().all())
            return len(trusted_devices) > 0
            
        except Exception as e:
            self.logger.error(f"Failed to validate device trust requirement: {str(e)}")
            return False
    
    async def _validate_hardware_key_requirement(self, session: AsyncSession, user_id: int) -> bool:
        """Validate hardware key requirement."""
        try:
            # Check if user has registered hardware security keys (WebAuthn/FIDO2)
            from shared.database.models.auth_models import PasskeyCredential
            
            result = await session.execute(
                select(PasskeyCredential).where(
                    and_(
                        PasskeyCredential.user_id == user_id,
                        PasskeyCredential.is_active == True
                    )
                )
            )
            
            hardware_keys = list(result.scalars().all())
            return len(hardware_keys) > 0
            
        except Exception as e:
            self.logger.error(f"Failed to validate hardware key requirement: {str(e)}")
            return False
    
    async def _validate_threat_detection_requirement(self, session: AsyncSession, user_id: int) -> bool:
        """Validate threat detection requirement."""
        try:
            # For now, this is automatically enabled at the system level
            # In a real implementation, this would check if advanced threat detection is active
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to validate threat detection requirement: {str(e)}")
            return False
    
    async def _validate_compliance_requirement(self, session: AsyncSession, user_id: int) -> bool:
        """Validate compliance reporting requirement."""
        try:
            # For now, this is automatically enabled at the system level
            # In a real implementation, this would check compliance reporting configuration
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to validate compliance requirement: {str(e)}")
            return False
    
    async def _check_policy_restrictions(
        self, 
        session: AsyncSession, 
        user_id: int,
        target_tier: SecurityTier
    ) -> Dict[str, Any]:
        """Check if administrative policies restrict tier upgrades."""
        try:
            # Get active policies that might affect this user
            result = await session.execute(
                select(SecurityTierPolicy).where(
                    and_(
                        SecurityTierPolicy.is_active == True,
                        SecurityTierPolicy.minimum_tier <= target_tier
                    )
                )
            )
            
            policies = list(result.scalars().all())
            
            # Check if any policies block this upgrade
            blocked = False
            blocking_policies = []
            recommendations = []
            
            for policy in policies:
                # Check if policy applies to this user
                applies = await self._policy_applies_to_user(session, policy, user_id)
                
                if applies and target_tier.value not in policy.allowed_tiers:
                    blocked = True
                    blocking_policies.append({
                        "policy_name": policy.policy_name,
                        "description": policy.description,
                        "enforcement_level": policy.enforcement_level
                    })
            
            return {
                "blocked": blocked,
                "blocking_policies": blocking_policies,
                "recommendations": recommendations
            }
            
        except Exception as e:
            self.logger.error(f"Failed to check policy restrictions: {str(e)}")
            return {"blocked": False, "blocking_policies": [], "recommendations": []}
    
    async def _policy_applies_to_user(
        self, 
        session: AsyncSession, 
        policy: SecurityTierPolicy,
        user_id: int
    ) -> bool:
        """Check if a security policy applies to a specific user."""
        try:
            # Get user details
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one()
            
            # Check role-based application
            if policy.applies_to_roles and user.role.value not in policy.applies_to_roles:
                return False
            
            # Check user-specific inclusion
            if policy.applies_to_users and str(user_id) not in policy.applies_to_users:
                return False
            
            # Check user-specific exclusion
            if policy.exclude_users and str(user_id) in policy.exclude_users:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to check policy application: {str(e)}")
            return False
    
    async def _get_user_security_metrics(
        self, 
        session: AsyncSession, 
        user_id: int
    ) -> Dict[str, Any]:
        """Get security metrics for a user."""
        try:
            # Get recent security events
            metrics = await security_audit_service.get_security_metrics(
                session=session,
                user_id=user_id,
                time_window="7d"
            )
            
            return {
                "security_score": self._calculate_security_score(session, user_id),
                "recent_violations": metrics.get("violations_by_severity", {}),
                "access_patterns": metrics.get("access_statistics", []),
                "last_security_check": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get user security metrics: {str(e)}")
            return {}
    
    def _calculate_security_score(self, session: AsyncSession, user_id: int) -> int:
        """Calculate a security score for the user (0-100)."""
        # This is a simplified implementation
        # In a real system, this would consider various security factors
        base_score = 60  # Standard tier baseline
        
        # This would be implemented with actual security metrics
        # For now, return a reasonable score
        return base_score


# Global security tier service instance
security_tier_service = SecurityTierService()