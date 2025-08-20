"""
Security Monitoring Router
Real-time security validation and monitoring endpoints
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse

import sys
sys.path.append('/project/app')

from shared.services.security_validation_service import SecurityValidator, SecurityTestResult
from api.dependencies import get_current_user
from shared.database.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/security", tags=["security-monitoring"])

# Global security validator instance
security_validator = SecurityValidator()

@router.get("/health", summary="Security monitoring health check")
async def security_health():
    """Basic health check for security monitoring service"""
    return {
        "status": "healthy",
        "service": "security-monitoring",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.get("/validate", summary="Run comprehensive security validation")
async def run_security_validation(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Run comprehensive security validation tests.
    
    Requires authentication to prevent abuse.
    """
    try:
        # Run validation in background to avoid timeout
        results = await security_validator.run_all_validations()
        report = security_validator.generate_security_report()
        
        logger.info(f"Security validation completed by user {current_user.id}, score: {report['summary']['security_score']}%")
        
        return JSONResponse(
            content=report,
            status_code=200
        )
        
    except Exception as e:
        logger.error(f"Security validation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Security validation failed: {str(e)}"
        )

@router.get("/status", summary="Get current security status")
async def get_security_status():
    """
    Get current security status without running full validation.
    Public endpoint for status dashboard.
    """
    try:
        # Run lightweight checks only
        https_check = await security_validator.validate_https_availability()
        
        # Generate basic status
        status = {
            "https_status": https_check.status,
            "https_message": https_check.message,
            "last_check": https_check.timestamp.isoformat(),
            "service_status": "operational" if https_check.status == "pass" else "degraded"
        }
        
        return JSONResponse(content=status, status_code=200)
        
    except Exception as e:
        logger.error(f"Security status check failed: {e}")
        return JSONResponse(
            content={
                "service_status": "error",
                "error": str(e),
                "last_check": datetime.now(timezone.utc).isoformat()
            },
            status_code=500
        )

@router.get("/headers", summary="Check security headers")
async def check_security_headers():
    """
    Check current security headers configuration.
    Public endpoint for header validation.
    """
    try:
        https_result = await security_validator.validate_https_availability()
        
        if https_result.details and "security_headers" in https_result.details:
            headers_info = https_result.details["security_headers"]
            
            return JSONResponse(
                content={
                    "status": "success",
                    "headers": headers_info["headers"],
                    "score": headers_info["score"],
                    "percentage": headers_info["percentage"],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                status_code=200
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Unable to retrieve security headers information"
            )
            
    except Exception as e:
        logger.error(f"Security headers check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Security headers check failed: {str(e)}"
        )

@router.get("/certificate", summary="Check SSL certificate status")
async def check_ssl_certificate():
    """
    Check SSL certificate validity and expiration.
    Public endpoint for certificate monitoring.
    """
    try:
        cert_result = await security_validator.validate_ssl_certificate()
        
        return JSONResponse(
            content={
                "status": cert_result.status,
                "message": cert_result.message,
                "details": cert_result.details,
                "timestamp": cert_result.timestamp.isoformat()
            },
            status_code=200
        )
        
    except Exception as e:
        logger.error(f"SSL certificate check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"SSL certificate check failed: {str(e)}"
        )

@router.get("/dashboard", summary="Security monitoring dashboard data")
async def get_security_dashboard(
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive security dashboard data.
    
    Requires authentication for detailed security information.
    """
    try:
        # Run all validations for dashboard
        results = await security_validator.run_all_validations()
        report = security_validator.generate_security_report()
        
        # Enhanced dashboard data
        dashboard_data = {
            "overview": report["summary"],
            "tests": [
                {
                    "name": result.test_name,
                    "status": result.status,
                    "message": result.message,
                    "timestamp": result.timestamp.isoformat()
                }
                for result in results
            ],
            "recommendations": report["recommendations"],
            "alerts": [
                {
                    "level": "critical" if result.status == "fail" else "warning",
                    "message": result.message,
                    "test": result.test_name
                }
                for result in results
                if result.status in ["fail", "warning"]
            ],
            "metrics": {
                "uptime_status": "operational" if any(r.status == "pass" for r in results) else "down",
                "security_score": report["summary"]["security_score"],
                "ssl_valid": any(r.test_name == "ssl_certificate" and r.status == "pass" for r in results),
                "auth_secure": any(r.test_name == "authentication_endpoints" and r.status == "pass" for r in results)
            }
        }
        
        return JSONResponse(content=dashboard_data, status_code=200)
        
    except Exception as e:
        logger.error(f"Security dashboard data retrieval failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Dashboard data retrieval failed: {str(e)}"
        )

@router.post("/alert", summary="Create security alert")
async def create_security_alert(
    alert_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """
    Create a security alert for monitoring.
    
    Requires authentication to prevent abuse.
    """
    try:
        # Log security alert
        logger.warning(
            f"Security alert created by user {current_user.id}: {alert_data.get('message', 'No message')}"
        )
        
        # In a production system, this would integrate with alerting systems
        # like PagerDuty, Slack, email notifications, etc.
        
        alert_response = {
            "status": "alert_created",
            "alert_id": f"sec-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "message": alert_data.get("message", "Security alert"),
            "severity": alert_data.get("severity", "medium"),
            "created_by": current_user.email,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return JSONResponse(content=alert_response, status_code=201)
        
    except Exception as e:
        logger.error(f"Security alert creation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Alert creation failed: {str(e)}"
        )

@router.get("/metrics", summary="Security metrics for monitoring systems")
async def get_security_metrics():
    """
    Get security metrics in Prometheus-compatible format.
    Public endpoint for monitoring system integration.
    """
    try:
        # Run lightweight validation
        results = await security_validator.run_all_validations()
        
        # Generate Prometheus-style metrics
        metrics = []
        
        # Overall security score
        security_score = sum(1 for r in results if r.status == "pass") / len(results) if results else 0
        metrics.append(f"aiwfe_security_score {security_score:.2f}")
        
        # Individual test metrics
        for result in results:
            test_name = result.test_name.replace("-", "_")
            status_value = 1 if result.status == "pass" else 0
            metrics.append(f"aiwfe_security_test{{test=\"{test_name}\"}} {status_value}")
        
        # SSL certificate days until expiry
        for result in results:
            if result.test_name == "ssl_certificate" and result.details:
                days_until_expiry = result.details.get("days_until_expiry", 0)
                metrics.append(f"aiwfe_ssl_cert_days_until_expiry {days_until_expiry}")
        
        return "\n".join(metrics)
        
    except Exception as e:
        logger.error(f"Security metrics generation failed: {e}")
        return f"# Error generating metrics: {str(e)}"