"""API endpoints for security tier management."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
import logging

from shared.utils.database_setup import get_async_session
from shared.services.security_tier_service import security_tier_service, SecurityTier
from shared.services.enhanced_jwt_service import enhanced_jwt_service
from shared.database.models import User
from api.dependencies import get_current_user
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/security-tiers", tags=["Security Tiers"])
security = HTTPBearer()


class SecurityTierUpgradeRequest(BaseModel):
    """Request model for security tier upgrades."""
    target_tier: str
    reason: Optional[str] = None


class SecurityTierAssessmentResponse(BaseModel):
    """Response model for security tier assessment."""
    current_tier: str
    target_tier: str
    is_eligible: bool
    completion_percentage: float
    completed_requirements: int
    total_requirements: int
    requirement_status: Dict[str, Dict[str, Any]]
    tier_definition: Dict[str, Any]
    policy_restrictions: Dict[str, Any]
    upgrade_in_progress: bool
    estimated_upgrade_time: str


class SecurityDashboardResponse(BaseModel):
    """Response model for security dashboard data."""
    current_tier: Dict[str, Any]
    available_tiers: Dict[str, Any]
    recent_upgrades: List[Dict[str, Any]]
    security_metrics: Dict[str, Any]
    tier_definitions: Dict[str, Any]


class UpgradeProgressResponse(BaseModel):
    """Response model for upgrade progress."""
    upgrade_id: str
    status: str
    progress_percentage: int
    current_step: Optional[str]
    from_tier: str
    to_tier: str
    started_at: str
    completed_at: Optional[str]
    requirements_completed: List[str]
    requirements_failed: List[str]
    error_details: Optional[Dict[str, Any]]
    retry_count: int



@router.get("/dashboard", response_model=SecurityDashboardResponse)
async def get_security_dashboard(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get comprehensive security dashboard data for the current user."""
    try:
        dashboard_data = await security_tier_service.get_security_dashboard_data(
            session=session,
            user_id=current_user.id
        )
        
        return SecurityDashboardResponse(**dashboard_data)
        
    except Exception as e:
        logger.error(f"Failed to get security dashboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load security dashboard"
        )


@router.get("/assess/{target_tier}", response_model=SecurityTierAssessmentResponse)
async def assess_tier_eligibility(
    target_tier: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Assess user's eligibility for a specific security tier."""
    try:
        # Validate target tier
        try:
            tier_enum = SecurityTier(target_tier)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid security tier: {target_tier}"
            )
        
        assessment = await security_tier_service.assess_tier_eligibility(
            session=session,
            user_id=current_user.id,
            target_tier=tier_enum
        )
        
        return SecurityTierAssessmentResponse(**assessment)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assess tier eligibility: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assess security tier eligibility"
        )


@router.post("/upgrade")
async def start_security_tier_upgrade(
    request: SecurityTierUpgradeRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Start a security tier upgrade process."""
    try:
        # Validate target tier
        try:
            target_tier = SecurityTier(request.target_tier)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid security tier: {request.target_tier}"
            )
        
        upgrade_id = await security_tier_service.start_tier_upgrade(
            session=session,
            user_id=current_user.id,
            target_tier=target_tier,
            upgrade_reason=request.reason
        )
        
        return {
            "upgrade_id": upgrade_id,
            "message": f"Security tier upgrade to {target_tier.value} initiated",
            "target_tier": target_tier.value
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start tier upgrade: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start security tier upgrade"
        )


@router.get("/upgrade/{upgrade_id}/progress", response_model=UpgradeProgressResponse)
async def get_upgrade_progress(
    upgrade_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get the progress of a security tier upgrade."""
    try:
        progress = await security_tier_service.get_upgrade_progress(
            session=session,
            upgrade_id=upgrade_id
        )
        
        return UpgradeProgressResponse(**progress)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to get upgrade progress: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get upgrade progress"
        )


@router.get("/current")
async def get_current_security_tier(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get the current user's security tier information."""
    try:
        user_tier = await security_tier_service.get_user_security_tier(
            session=session,
            user_id=current_user.id
        )
        
        return {
            "current_tier": user_tier.current_tier.value,
            "requested_tier": user_tier.requested_tier.value if user_tier.requested_tier else None,
            "upgrade_in_progress": user_tier.upgrade_in_progress,
            "upgrade_started_at": user_tier.upgrade_started_at.isoformat() if user_tier.upgrade_started_at else None,
            "upgrade_completed_at": user_tier.upgrade_completed_at.isoformat() if user_tier.upgrade_completed_at else None,
            "tier_features": user_tier.tier_features,
            "security_config": user_tier.security_config,
            "admin_enforced": user_tier.admin_enforced,
            "minimum_required_tier": user_tier.minimum_required_tier.value if user_tier.minimum_required_tier else None
        }
        
    except Exception as e:
        logger.error(f"Failed to get current security tier: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get security tier information"
        )


@router.get("/tiers")
async def get_available_tiers():
    """Get information about all available security tiers."""
    try:
        return {
            "tiers": {
                tier.value: definition 
                for tier, definition in security_tier_service.tier_definitions.items()
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get available tiers: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get available tiers"
        )


@router.post("/validate-requirement/{requirement_type}")
async def validate_security_requirement(
    requirement_type: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Manually validate a specific security requirement."""
    try:
        from shared.database.models.security_models import SecurityRequirementType
        
        # Validate requirement type
        try:
            req_type = SecurityRequirementType(requirement_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid requirement type: {requirement_type}"
            )
        
        is_valid = await security_tier_service.validate_requirement(
            session=session,
            user_id=current_user.id,
            requirement_type=req_type
        )
        
        return {
            "requirement_type": requirement_type,
            "is_valid": is_valid,
            "validated_at": security_tier_service.logger.handlers[0].formatter.formatTime(
                logging.LogRecord("", 0, "", 0, "", (), None)
            ) if security_tier_service.logger.handlers else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate requirement: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate security requirement"
        )


# Admin endpoints (require admin role)
@router.get("/admin/overview")
async def admin_get_security_overview(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Admin endpoint to get platform security overview."""
    try:
        # Check admin permissions
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        
        # Get overall statistics
        from sqlalchemy import select, func
        from shared.database.models.security_models import UserSecurityTier
        
        stmt = select(
            UserSecurityTier.current_tier,
            func.count(UserSecurityTier.id).label('count')
        ).group_by(UserSecurityTier.current_tier)
        
        result = await session.execute(stmt)
        tier_stats = {row.current_tier: row.count for row in result}
        
        # Get recent upgrades
        recent_upgrades_stmt = select(UserSecurityTier).where(
            UserSecurityTier.upgrade_completed_at.isnot(None)
        ).order_by(UserSecurityTier.upgrade_completed_at.desc()).limit(10)
        
        result = await session.execute(recent_upgrades_stmt)
        recent_upgrades = result.scalars().all()
        
        return {
            "tier_statistics": tier_stats,
            "total_users": sum(tier_stats.values()),
            "recent_upgrades": [
                {
                    "user_id": upgrade.user_id,
                    "from_tier": "standard",  # Simplified for demo
                    "to_tier": upgrade.current_tier.value,
                    "completed_at": upgrade.upgrade_completed_at.isoformat()
                }
                for upgrade in recent_upgrades
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin failed to get security overview: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get security overview"
        )


@router.get("/admin/users")
async def admin_get_all_users_security(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Admin endpoint to get all users' security information."""
    try:
        # Check admin permissions
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        
        from sqlalchemy import select
        from shared.database.models import User
        from shared.database.models.security_models import UserSecurityTier
        
        # Join users with their security tiers
        stmt = select(User, UserSecurityTier).outerjoin(
            UserSecurityTier, User.id == UserSecurityTier.user_id
        ).order_by(User.email)
        
        result = await session.execute(stmt)
        user_rows = result.all()
        
        users_data = []
        for user, security_tier in user_rows:
            user_data = {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "current_tier": security_tier.current_tier.value if security_tier else "standard",
                "requested_tier": security_tier.requested_tier.value if security_tier and security_tier.requested_tier else None,
                "upgrade_in_progress": security_tier.upgrade_in_progress if security_tier else False,
                "admin_enforced": security_tier.admin_enforced if security_tier else False,
                "minimum_required_tier": security_tier.minimum_required_tier.value if security_tier and security_tier.minimum_required_tier else None,
                "created_at": user.created_at.isoformat(),
                "updated_at": security_tier.updated_at.isoformat() if security_tier else user.created_at.isoformat()
            }
            users_data.append(user_data)
        
        return {"users": users_data}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin failed to get users security data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get users security data"
        )


@router.get("/admin/policies")
async def admin_get_security_policies(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Admin endpoint to get all security policies."""
    try:
        # Check admin permissions
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        
        from sqlalchemy import select
        from shared.database.models.security_models import SecurityTierPolicy
        
        stmt = select(SecurityTierPolicy).order_by(SecurityTierPolicy.created_at.desc())
        result = await session.execute(stmt)
        policies = result.scalars().all()
        
        policies_data = []
        for policy in policies:
            policy_data = {
                "id": policy.id,
                "policy_name": policy.policy_name,
                "description": policy.description,
                "minimum_tier": policy.minimum_tier.value,
                "enforcement_level": policy.enforcement_level,
                "grace_period_days": policy.grace_period_days,
                "is_active": policy.is_active,
                "created_at": policy.created_at.isoformat(),
                "effective_date": policy.effective_date.isoformat()
            }
            policies_data.append(policy_data)
        
        return {"policies": policies_data}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin failed to get security policies: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get security policies"
        )
@router.get("/admin/users/{user_id}/tier")
async def admin_get_user_security_tier(
    user_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Admin endpoint to get any user's security tier information."""
    try:
        # Check admin permissions
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        
        user_tier = await security_tier_service.get_user_security_tier(
            session=session,
            user_id=user_id
        )
        
        return {
            "user_id": user_id,
            "current_tier": user_tier.current_tier.value,
            "requested_tier": user_tier.requested_tier.value if user_tier.requested_tier else None,
            "upgrade_in_progress": user_tier.upgrade_in_progress,
            "tier_features": user_tier.tier_features,
            "security_config": user_tier.security_config,
            "admin_enforced": user_tier.admin_enforced,
            "minimum_required_tier": user_tier.minimum_required_tier.value if user_tier.minimum_required_tier else None,
            "compliance_notes": user_tier.compliance_notes,
            "created_at": user_tier.created_at.isoformat(),
            "updated_at": user_tier.updated_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin failed to get user security tier: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user security tier"
        )


@router.post("/admin/users/{user_id}/enforce-tier")
async def admin_enforce_security_tier(
    user_id: int,
    request: SecurityTierUpgradeRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Admin endpoint to enforce a minimum security tier for a user."""
    try:
        # Check admin permissions
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        
        # Validate target tier
        try:
            target_tier = SecurityTier(request.target_tier)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid security tier: {request.target_tier}"
            )
        
        # Get user tier and update minimum required tier
        user_tier = await security_tier_service.get_user_security_tier(
            session=session,
            user_id=user_id
        )
        
        user_tier.minimum_required_tier = target_tier
        user_tier.admin_enforced = True
        user_tier.compliance_notes = request.reason or f"Admin enforced {target_tier.value} tier"
        
        await session.commit()
        
        return {
            "message": f"Minimum security tier {target_tier.value} enforced for user {user_id}",
            "user_id": user_id,
            "enforced_tier": target_tier.value,
            "reason": request.reason
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin failed to enforce security tier: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enforce security tier"
        )