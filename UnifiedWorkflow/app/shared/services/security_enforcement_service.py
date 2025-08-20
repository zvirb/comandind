"""Security tier enforcement service for validating user access across the platform."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from shared.database.models.security_models import (
    SecurityTier, 
    UserSecurityTier, 
    SecurityTierPolicy,
    SecurityViolation,
    ViolationSeverity
)
from shared.database.models import User

logger = logging.getLogger(__name__)


class SecurityEnforcementLevel(str, Enum):
    """Security enforcement levels."""
    ADVISORY = "ADVISORY"      # Log violations but allow access
    MANDATORY = "MANDATORY"    # Block access and require upgrade
    STRICT = "STRICT"         # Block access immediately


class SecurityEnforcementService:
    """Service for enforcing security tier requirements across the platform."""
    
    def __init__(self):
        self.logger = logger
        
        # Endpoint security requirements mapping
        self.endpoint_requirements = {
            # Admin endpoints require Enhanced or Enterprise
            "/api/v1/admin/": {
                "minimum_tier": SecurityTier.ENHANCED,
                "enforcement": SecurityEnforcementLevel.MANDATORY,
                "description": "Administrative functions require enhanced security"
            },
            
            # Sensitive data endpoints
            "/api/v1/security-tiers/": {
                "minimum_tier": SecurityTier.STANDARD,
                "enforcement": SecurityEnforcementLevel.ADVISORY,
                "description": "Security configuration access"
            },
            
            # Certificate endpoints require Enhanced
            "/api/v1/certificates/": {
                "minimum_tier": SecurityTier.ENHANCED,
                "enforcement": SecurityEnforcementLevel.MANDATORY,
                "description": "Certificate operations require enhanced security"
            },
            
            # WebAuthn endpoints require Enterprise
            "/api/v1/webauthn/": {
                "minimum_tier": SecurityTier.ENTERPRISE,
                "enforcement": SecurityEnforcementLevel.MANDATORY,
                "description": "Hardware key operations require enterprise security"
            },
            
            # High-value data operations
            "/api/v1/conversation/export": {
                "minimum_tier": SecurityTier.ENHANCED,
                "enforcement": SecurityEnforcementLevel.MANDATORY,
                "description": "Data export requires enhanced security"
            },
            
            # System configuration
            "/api/v1/settings/system": {
                "minimum_tier": SecurityTier.ENHANCED,
                "enforcement": SecurityEnforcementLevel.MANDATORY,
                "description": "System settings require enhanced security"
            }
        }
    
    async def validate_user_access(
        self,
        session: AsyncSession,
        user: User,
        endpoint_path: str,
        request_method: str = "GET"
    ) -> Dict[str, Any]:
        """
        Validate if user has appropriate security tier for the requested endpoint.
        
        Returns:
            Dict with 'allowed' (bool), 'reason' (str), 'required_tier' (str), etc.
        """
        try:
            # Get user's current security tier
            user_tier = await self.get_user_security_tier(session, user.id)
            
            # Get endpoint requirements
            endpoint_requirement = self.get_endpoint_requirement(endpoint_path)
            
            if not endpoint_requirement:
                # No specific requirement for this endpoint
                return {
                    "allowed": True,
                    "user_tier": user_tier.current_tier.value,
                    "required_tier": None,
                    "enforcement_level": None
                }
            
            # Check if user meets minimum requirement
            tier_hierarchy = {
                SecurityTier.STANDARD: 1,
                SecurityTier.ENHANCED: 2,
                SecurityTier.ENTERPRISE: 3
            }
            
            user_tier_level = tier_hierarchy.get(user_tier.current_tier, 0)
            required_tier_level = tier_hierarchy.get(endpoint_requirement["minimum_tier"], 999)
            
            meets_requirement = user_tier_level >= required_tier_level
            
            # Apply enforcement based on level
            enforcement_level = endpoint_requirement["enforcement"]
            
            if meets_requirement:
                return {
                    "allowed": True,
                    "user_tier": user_tier.current_tier.value,
                    "required_tier": endpoint_requirement["minimum_tier"].value,
                    "enforcement_level": enforcement_level.value
                }
            
            # User does not meet requirement
            if enforcement_level == SecurityEnforcementLevel.ADVISORY:
                # Log violation but allow access
                await self.log_security_violation(
                    session, user.id, endpoint_path, 
                    ViolationSeverity.LOW, 
                    f"User accessed {endpoint_path} with insufficient security tier"
                )
                
                return {
                    "allowed": True,
                    "warning": True,
                    "user_tier": user_tier.current_tier.value,
                    "required_tier": endpoint_requirement["minimum_tier"].value,
                    "enforcement_level": enforcement_level.value,
                    "message": "Access granted with security warning"
                }
            
            elif enforcement_level in [SecurityEnforcementLevel.MANDATORY, SecurityEnforcementLevel.STRICT]:
                # Block access
                await self.log_security_violation(
                    session, user.id, endpoint_path,
                    ViolationSeverity.MEDIUM if enforcement_level == SecurityEnforcementLevel.MANDATORY else ViolationSeverity.HIGH,
                    f"User blocked from {endpoint_path} due to insufficient security tier"
                )
                
                return {
                    "allowed": False,
                    "user_tier": user_tier.current_tier.value,
                    "required_tier": endpoint_requirement["minimum_tier"].value,
                    "enforcement_level": enforcement_level.value,
                    "message": endpoint_requirement["description"],
                    "upgrade_required": True
                }
            
        except Exception as e:
            self.logger.error(f"Error validating user access: {str(e)}")
            # On error, allow access but log the issue
            return {
                "allowed": True,
                "error": str(e),
                "message": "Security validation failed - access granted by default"
            }
    
    def get_endpoint_requirement(self, endpoint_path: str) -> Optional[Dict[str, Any]]:
        """Get security requirement for a specific endpoint."""
        # Check for exact match first
        if endpoint_path in self.endpoint_requirements:
            return self.endpoint_requirements[endpoint_path]
        
        # Check for prefix matches
        for path_prefix, requirement in self.endpoint_requirements.items():
            if endpoint_path.startswith(path_prefix):
                return requirement
        
        return None
    
    async def get_user_security_tier(
        self, 
        session: AsyncSession, 
        user_id: int
    ) -> UserSecurityTier:
        """Get user's current security tier, creating default if not exists."""
        try:
            stmt = select(UserSecurityTier).where(UserSecurityTier.user_id == user_id)
            result = await session.execute(stmt)
            user_tier = result.scalar_one_or_none()
            
            if not user_tier:
                # Create default security tier for user
                user_tier = UserSecurityTier(
                    user_id=user_id,
                    current_tier=SecurityTier.STANDARD,
                    security_config={},
                    tier_features=["basic_https", "standard_monitoring"]
                )
                session.add(user_tier)
                await session.commit()
                await session.refresh(user_tier)
            
            return user_tier
            
        except Exception as e:
            self.logger.error(f"Error getting user security tier: {str(e)}")
            raise
    
    async def log_security_violation(
        self,
        session: AsyncSession,
        user_id: int,
        endpoint_path: str,
        severity: ViolationSeverity,
        description: str,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """Log a security violation."""
        try:
            violation = SecurityViolation(
                violation_type="INSUFFICIENT_SECURITY_TIER",
                severity=severity,
                user_id=user_id,
                table_name="security_enforcement",
                attempted_operation=f"ACCESS {endpoint_path}",
                violation_details={
                    "endpoint": endpoint_path,
                    "description": description,
                    "timestamp": datetime.utcnow().isoformat(),
                    **(additional_data or {})
                },
                blocked=severity in [ViolationSeverity.MEDIUM, ViolationSeverity.HIGH]
            )
            
            session.add(violation)
            await session.commit()
            
            self.logger.warning(
                f"Security violation logged: User {user_id} - {description} "
                f"(Severity: {severity.value})"
            )
            
        except Exception as e:
            self.logger.error(f"Error logging security violation: {str(e)}")
    
    async def check_policy_compliance(
        self,
        session: AsyncSession,
        user_id: int
    ) -> Dict[str, Any]:
        """Check if user is compliant with active security policies."""
        try:
            # Get active policies
            stmt = select(SecurityTierPolicy).where(
                SecurityTierPolicy.is_active == True
            )
            result = await session.execute(stmt)
            policies = result.scalars().all()
            
            # Get user's security tier
            user_tier = await self.get_user_security_tier(session, user_id)
            
            compliance_status = {
                "compliant": True,
                "policies_checked": len(policies),
                "violations": [],
                "warnings": []
            }
            
            tier_hierarchy = {
                SecurityTier.STANDARD: 1,
                SecurityTier.ENHANCED: 2,
                SecurityTier.ENTERPRISE: 3
            }
            
            user_tier_level = tier_hierarchy.get(user_tier.current_tier, 0)
            
            for policy in policies:
                required_tier_level = tier_hierarchy.get(policy.minimum_tier, 999)
                
                if user_tier_level < required_tier_level:
                    if policy.enforcement_level == "STRICT":
                        compliance_status["compliant"] = False
                        compliance_status["violations"].append({
                            "policy_name": policy.policy_name,
                            "required_tier": policy.minimum_tier.value,
                            "user_tier": user_tier.current_tier.value,
                            "enforcement": policy.enforcement_level,
                            "grace_period_days": policy.grace_period_days
                        })
                    elif policy.enforcement_level == "MANDATORY":
                        # Check grace period
                        days_since_effective = (datetime.utcnow() - policy.effective_date).days
                        if days_since_effective > policy.grace_period_days:
                            compliance_status["compliant"] = False
                            compliance_status["violations"].append({
                                "policy_name": policy.policy_name,
                                "required_tier": policy.minimum_tier.value,
                                "user_tier": user_tier.current_tier.value,
                                "enforcement": policy.enforcement_level,
                                "grace_period_expired": True
                            })
                        else:
                            compliance_status["warnings"].append({
                                "policy_name": policy.policy_name,
                                "required_tier": policy.minimum_tier.value,
                                "user_tier": user_tier.current_tier.value,
                                "grace_period_remaining": policy.grace_period_days - days_since_effective
                            })
                    else:  # ADVISORY
                        compliance_status["warnings"].append({
                            "policy_name": policy.policy_name,
                            "required_tier": policy.minimum_tier.value,
                            "user_tier": user_tier.current_tier.value,
                            "enforcement": policy.enforcement_level
                        })
            
            return compliance_status
            
        except Exception as e:
            self.logger.error(f"Error checking policy compliance: {str(e)}")
            return {
                "compliant": True,  # Default to compliant on error
                "error": str(e)
            }
    
    async def get_upgrade_recommendations(
        self,
        session: AsyncSession,
        user_id: int
    ) -> List[Dict[str, Any]]:
        """Get security tier upgrade recommendations for a user."""
        try:
            # Check compliance
            compliance = await self.check_policy_compliance(session, user_id)
            user_tier = await self.get_user_security_tier(session, user_id)
            
            recommendations = []
            
            # Add recommendations based on violations
            for violation in compliance.get("violations", []):
                recommendations.append({
                    "type": "policy_requirement",
                    "reason": f"Required by policy: {violation['policy_name']}",
                    "recommended_tier": violation["required_tier"],
                    "urgency": "high" if violation.get("grace_period_expired") else "medium",
                    "description": f"Upgrade to {violation['required_tier']} to comply with security policy"
                })
            
            # Add recommendations based on warnings
            for warning in compliance.get("warnings", []):
                if warning.get("grace_period_remaining", 0) <= 7:  # Within 7 days
                    recommendations.append({
                        "type": "grace_period_ending",
                        "reason": f"Grace period ending for: {warning['policy_name']}",
                        "recommended_tier": warning["required_tier"],
                        "urgency": "medium",
                        "description": f"Consider upgrading to {warning['required_tier']} before grace period expires",
                        "days_remaining": warning.get("grace_period_remaining", 0)
                    })
            
            # Add general recommendations based on usage patterns
            if user_tier.current_tier == SecurityTier.STANDARD:
                recommendations.append({
                    "type": "security_enhancement",
                    "reason": "Enhanced security features available",
                    "recommended_tier": "enhanced",
                    "urgency": "low",
                    "description": "Upgrade to Enhanced for additional security features like client certificates and device trust"
                })
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error getting upgrade recommendations: {str(e)}")
            return []


# Global instance
security_enforcement_service = SecurityEnforcementService()