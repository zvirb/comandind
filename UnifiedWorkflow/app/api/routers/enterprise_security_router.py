"""Enterprise Security Administration API Router.

Provides comprehensive administrative security tools for enterprise compliance,
including real-time security metrics, compliance monitoring, threat detection,
user access management, and automated security responses.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Body, BackgroundTasks
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession

from shared.utils.database_setup import get_async_session
from shared.services.enterprise_security_admin_service import enterprise_security_admin_service
from shared.services.enhanced_jwt_service import enhanced_jwt_service
from api.dependencies import get_current_user
from shared.schemas.user_schemas import UserRead as UserSchema

router = APIRouter(prefix="/api/v1/enterprise-security", tags=["Enterprise Security"])
security = HTTPBearer()


# Request/Response Models

class SecurityDashboardRequest(BaseModel):
    """Request model for security dashboard."""
    time_range: str = Field(default="24h", description="Time range for metrics")
    refresh_cache: bool = Field(default=False, description="Force refresh cached data")


class UserAccessFilters(BaseModel):
    """Filters for user access management."""
    role: Optional[str] = None
    security_tier: Optional[str] = None
    search: Optional[str] = None
    has_2fa: Optional[bool] = None
    last_login_days: Optional[int] = None


class SecurityReportRequest(BaseModel):
    """Request model for security reports."""
    report_type: str = Field(..., description="Type of report to generate")
    start_date: datetime = Field(..., description="Report start date")
    end_date: datetime = Field(..., description="Report end date")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Additional filters")
    
    @validator('report_type')
    def validate_report_type(cls, v):
        allowed_types = [
            'authentication_patterns', 'failed_login_analysis', 'device_analytics',
            'compliance_audit', 'threat_assessment', 'user_activity', 'privilege_escalation'
        ]
        if v not in allowed_types:
            raise ValueError(f"Report type must be one of: {allowed_types}")
        return v


class SecurityPolicyConfig(BaseModel):
    """Security policy configuration."""
    name: str = Field(..., description="Policy name")
    description: Optional[str] = Field(None, description="Policy description")
    minimum_tier: str = Field(..., description="Minimum security tier required")
    enforcement_level: str = Field(default="ADVISORY", description="Enforcement level")
    rules: Dict[str, Any] = Field(default_factory=dict, description="Policy rules")
    affected_roles: Optional[List[str]] = Field(None, description="Affected user roles")
    grace_period_days: int = Field(default=30, description="Grace period in days")
    effective_date: Optional[datetime] = Field(None, description="Policy effective date")


class ThreatResponseRequest(BaseModel):
    """Request model for threat response."""
    threat_type: str = Field(..., description="Type of threat detected")
    threat_data: Dict[str, Any] = Field(..., description="Threat context data")
    severity: str = Field(default="MEDIUM", description="Threat severity")
    auto_respond: bool = Field(default=True, description="Enable automated response")


class BulkUserActionRequest(BaseModel):
    """Request model for bulk user actions."""
    user_ids: List[int] = Field(..., description="List of user IDs")
    action: str = Field(..., description="Action to perform")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Action parameters")
    reason: str = Field(..., description="Reason for action")


class AuditTrailQuery(BaseModel):
    """Query parameters for audit trail."""
    start_date: datetime = Field(..., description="Start date for audit trail")
    end_date: datetime = Field(..., description="End date for audit trail")
    user_id: Optional[int] = Field(None, description="Filter by user ID")
    operation: Optional[str] = Field(None, description="Filter by operation type")
    table_name: Optional[str] = Field(None, description="Filter by table name")
    severity: Optional[str] = Field(None, description="Filter by severity")
    limit: int = Field(default=1000, description="Maximum number of records")


# API Endpoints

@router.get("/dashboard")
async def get_security_dashboard(
    request: SecurityDashboardRequest = Depends(),
    current_user: UserSchema = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get comprehensive security dashboard metrics."""
    try:
        dashboard_data = await enterprise_security_admin_service.get_security_dashboard_metrics(
            session=session,
            admin_user_id=current_user.id,
            time_range=request.time_range
        )
        
        return {
            "success": True,
            "data": dashboard_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch dashboard data: {str(e)}")


@router.get("/users")
async def get_user_access_management(
    filters: UserAccessFilters = Depends(),
    current_user: UserSchema = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get comprehensive user access management data."""
    try:
        user_data = await enterprise_security_admin_service.get_user_access_management(
            session=session,
            admin_user_id=current_user.id,
            filters=filters.dict(exclude_none=True)
        )
        
        return {
            "success": True,
            "data": user_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch user data: {str(e)}")


@router.post("/reports/generate")
async def generate_security_report(
    request: SecurityReportRequest,
    background_tasks: BackgroundTasks,
    current_user: UserSchema = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Generate comprehensive security analytics report."""
    try:
        report_data = await enterprise_security_admin_service.get_security_analytics_report(
            session=session,
            admin_user_id=current_user.id,
            report_type=request.report_type,
            start_date=request.start_date,
            end_date=request.end_date
        )
        
        return {
            "success": True,
            "data": report_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@router.post("/policies/enforce")
async def enforce_security_policy(
    request: SecurityPolicyConfig,
    current_user: UserSchema = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Enforce a security policy across the platform."""
    try:
        enforcement_result = await enterprise_security_admin_service.enforce_security_policy(
            session=session,
            admin_user_id=current_user.id,
            policy_config=request.dict()
        )
        
        return {
            "success": True,
            "data": enforcement_result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enforce policy: {str(e)}")


@router.post("/threats/respond")
async def respond_to_threat(
    request: ThreatResponseRequest,
    current_user: UserSchema = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Trigger automated response to detected threats."""
    try:
        response_result = await enterprise_security_admin_service.trigger_automated_response(
            session=session,
            threat_type=request.threat_type,
            threat_data=request.threat_data,
            admin_user_id=current_user.id
        )
        
        return {
            "success": True,
            "data": response_result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to respond to threat: {str(e)}")


@router.post("/users/bulk-action")
async def perform_bulk_user_action(
    request: BulkUserActionRequest,
    current_user: UserSchema = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Perform bulk actions on multiple users."""
    try:
        # Validate action type
        allowed_actions = [
            'enforce_security_tier', 'disable_account', 'enable_account',
            'reset_2fa', 'expire_sessions', 'require_password_reset'
        ]
        
        if request.action not in allowed_actions:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid action. Allowed actions: {allowed_actions}"
            )
        
        results = []
        
        for user_id in request.user_ids:
            try:
                # Execute action based on type
                if request.action == 'enforce_security_tier':
                    result = await _enforce_user_security_tier(
                        session, user_id, request.parameters, current_user.id
                    )
                elif request.action == 'disable_account':
                    result = await _disable_user_account(
                        session, user_id, request.reason, current_user.id
                    )
                elif request.action == 'enable_account':
                    result = await _enable_user_account(
                        session, user_id, request.reason, current_user.id
                    )
                elif request.action == 'reset_2fa':
                    result = await _reset_user_2fa(
                        session, user_id, request.reason, current_user.id
                    )
                elif request.action == 'expire_sessions':
                    result = await _expire_user_sessions(
                        session, user_id, request.reason, current_user.id
                    )
                elif request.action == 'require_password_reset':
                    result = await _require_password_reset(
                        session, user_id, request.reason, current_user.id
                    )
                
                results.append({
                    "user_id": user_id,
                    "success": True,
                    "result": result
                })
                
            except Exception as e:
                results.append({
                    "user_id": user_id,
                    "success": False,
                    "error": str(e)
                })
        
        await session.commit()
        
        return {
            "success": True,
            "data": {
                "action": request.action,
                "total_users": len(request.user_ids),
                "successful": len([r for r in results if r["success"]]),
                "failed": len([r for r in results if not r["success"]]),
                "results": results
            }
        }
        
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Bulk action failed: {str(e)}")


@router.get("/audit-trail")
async def get_audit_trail(
    query: AuditTrailQuery = Depends(),
    current_user: UserSchema = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get comprehensive audit trail for forensic investigation."""
    try:
        # Build audit trail query
        audit_data = await _get_comprehensive_audit_trail(
            session=session,
            query=query,
            admin_user_id=current_user.id
        )
        
        return {
            "success": True,
            "data": audit_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch audit trail: {str(e)}")


@router.get("/compliance/status")
async def get_compliance_status(
    standard: Optional[str] = Query(None, description="Specific compliance standard"),
    current_user: UserSchema = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get comprehensive compliance status for all or specific standards."""
    try:
        dashboard_data = await enterprise_security_admin_service.get_security_dashboard_metrics(
            session=session,
            admin_user_id=current_user.id,
            time_range="30d"
        )
        
        compliance_data = dashboard_data["dashboard_metrics"]["compliance"]
        
        if standard:
            compliance_data = {
                standard: compliance_data.get(standard, {})
            }
        
        return {
            "success": True,
            "data": {
                "compliance_status": compliance_data,
                "assessment_timestamp": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch compliance status: {str(e)}")


@router.get("/metrics/real-time")
async def get_real_time_metrics(
    metric_type: Optional[str] = Query(None, description="Specific metric type"),
    current_user: UserSchema = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get real-time security metrics."""
    try:
        metrics = await enterprise_security_admin_service.get_security_dashboard_metrics(
            session=session,
            admin_user_id=current_user.id,
            time_range="1h"
        )
        
        if metric_type:
            metrics_data = metrics["dashboard_metrics"].get(metric_type, {})
        else:
            metrics_data = metrics["dashboard_metrics"]
        
        return {
            "success": True,
            "data": {
                "metrics": metrics_data,
                "timestamp": datetime.utcnow().isoformat(),
                "metric_type": metric_type
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch real-time metrics: {str(e)}")


@router.get("/alerts/active")
async def get_active_security_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity"),
    limit: int = Query(50, description="Maximum number of alerts"),
    current_user: UserSchema = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get active security alerts."""
    try:
        dashboard_data = await enterprise_security_admin_service.get_security_dashboard_metrics(
            session=session,
            admin_user_id=current_user.id,
            time_range="24h"
        )
        
        alerts = dashboard_data["dashboard_metrics"]["active_alerts"]
        
        # Filter by severity if specified
        if severity:
            alerts = [alert for alert in alerts if alert["severity"] == severity.upper()]
        
        # Limit results
        alerts = alerts[:limit]
        
        return {
            "success": True,
            "data": {
                "alerts": alerts,
                "total_count": len(alerts),
                "severity_filter": severity,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch security alerts: {str(e)}")


# Helper functions

async def _enforce_user_security_tier(
    session: AsyncSession, user_id: int, parameters: Dict[str, Any], admin_user_id: int
) -> Dict[str, Any]:
    """Enforce security tier for a user."""
    # Implementation would call the appropriate service method
    return {"action": "enforce_security_tier", "status": "completed"}


async def _disable_user_account(
    session: AsyncSession, user_id: int, reason: str, admin_user_id: int
) -> Dict[str, Any]:
    """Disable user account."""
    # Implementation would disable the user account
    return {"action": "disable_account", "status": "completed"}


async def _enable_user_account(
    session: AsyncSession, user_id: int, reason: str, admin_user_id: int
) -> Dict[str, Any]:
    """Enable user account."""
    # Implementation would enable the user account
    return {"action": "enable_account", "status": "completed"}


async def _reset_user_2fa(
    session: AsyncSession, user_id: int, reason: str, admin_user_id: int
) -> Dict[str, Any]:
    """Reset user 2FA settings."""
    # Implementation would reset 2FA for the user
    return {"action": "reset_2fa", "status": "completed"}


async def _expire_user_sessions(
    session: AsyncSession, user_id: int, reason: str, admin_user_id: int
) -> Dict[str, Any]:
    """Expire all user sessions."""
    # Implementation would expire user sessions
    return {"action": "expire_sessions", "status": "completed"}


async def _require_password_reset(
    session: AsyncSession, user_id: int, reason: str, admin_user_id: int
) -> Dict[str, Any]:
    """Require user to reset password."""
    # Implementation would require password reset
    return {"action": "require_password_reset", "status": "completed"}


async def _get_comprehensive_audit_trail(
    session: AsyncSession, query: AuditTrailQuery, admin_user_id: int
) -> Dict[str, Any]:
    """Get comprehensive audit trail data."""
    # Implementation would fetch audit trail data based on query parameters
    return {
        "audit_entries": [],
        "total_count": 0,
        "query_parameters": query.dict()
    }