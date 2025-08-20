"""
SSL Certificate Health Check Endpoint
Provides health status and metrics for SSL certificates
"""

from fastapi import APIRouter, HTTPException, status
from typing import Dict, Optional
import subprocess
import json
import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/ssl",
    tags=["ssl", "health", "monitoring"]
)

class SSLHealthChecker:
    """SSL certificate health checker"""
    
    def __init__(self):
        # Try multiple paths - container path first, then host path
        possible_paths = [
            Path("/project/metrics/ssl_metrics.json"),  # Inside container (project mounted)
            Path("/app/metrics/ssl_metrics.json"),      # Alternative container path
            Path("/home/marku/ai_workflow_engine/metrics/ssl_metrics.json")  # Host path
        ]
        
        self.metrics_file = None
        for path in possible_paths:
            if path.exists():
                self.metrics_file = path
                logger.info(f"Using metrics file at: {path}")
                break
        
        if not self.metrics_file:
            # Default to expected container path
            self.metrics_file = Path("/project/metrics/ssl_metrics.json")
            logger.warning(f"Metrics file not found, will use: {self.metrics_file}")
        
        self.domain = "aiwfe.com"
        self.warning_threshold_days = 30
        self.critical_threshold_days = 7
        
    def get_certificate_status(self) -> Dict:
        """Get current certificate status from metrics"""
        try:
            if self.metrics_file.exists():
                metrics = json.loads(self.metrics_file.read_text())
                
                # Calculate health score
                cert_data = metrics.get("certificate", {})
                days_remaining = cert_data.get("days_remaining", -1)
                
                if days_remaining < 0:
                    health_score = 0
                    health_status = "CRITICAL"
                elif days_remaining <= self.critical_threshold_days:
                    health_score = 25
                    health_status = "CRITICAL"
                elif days_remaining <= self.warning_threshold_days:
                    health_score = 50
                    health_status = "WARNING"
                else:
                    health_score = 100
                    health_status = "HEALTHY"
                
                return {
                    "status": health_status,
                    "health_score": health_score,
                    "domain": self.domain,
                    "days_remaining": days_remaining,
                    "expiry_date": cert_data.get("expiry_date"),
                    "last_check": metrics.get("timestamp"),
                    "endpoint_status": metrics.get("endpoint", {}),
                    "last_backup": metrics.get("last_backup"),
                    "auto_renewal_enabled": metrics.get("automation", {}).get("auto_renewal_enabled", True)
                }
            else:
                return {
                    "status": "UNKNOWN",
                    "health_score": 0,
                    "domain": self.domain,
                    "error": f"Metrics file not found at {self.metrics_file}"
                }
                
        except Exception as e:
            logger.error(f"Failed to get certificate status: {e}")
            return {
                "status": "ERROR",
                "health_score": 0,
                "domain": self.domain,
                "error": str(e)
            }
    
    def check_caddy_health(self) -> Dict:
        """Check Caddy server health"""
        try:
            # Check if Caddy container is running
            cmd = "docker ps --filter name=caddy_reverse_proxy --format '{{.Status}}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if "Up" in result.stdout and "healthy" in result.stdout:
                caddy_status = "healthy"
            elif "Up" in result.stdout:
                caddy_status = "running"
            else:
                caddy_status = "down"
                
            return {
                "caddy_status": caddy_status,
                "container_status": result.stdout.strip()
            }
            
        except Exception as e:
            logger.error(f"Failed to check Caddy health: {e}")
            return {
                "caddy_status": "error",
                "error": str(e)
            }

# Initialize health checker
ssl_health = SSLHealthChecker()

@router.get("/health", response_model=Dict)
async def get_ssl_health():
    """
    Get SSL certificate health status
    
    Returns comprehensive health information including:
    - Certificate expiry status
    - Days remaining until expiry
    - Endpoint verification results
    - Backup status
    - Caddy server health
    """
    cert_status = ssl_health.get_certificate_status()
    caddy_health = ssl_health.check_caddy_health()
    
    # Combine all health data
    health_data = {
        **cert_status,
        "caddy": caddy_health,
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    # Set appropriate HTTP status based on health
    if cert_status["status"] == "CRITICAL":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_data
        )
    elif cert_status["status"] == "WARNING":
        # Return 200 with warning in body
        health_data["warning"] = f"Certificate expires in {cert_status['days_remaining']} days"
        
    return health_data

@router.get("/metrics", response_model=Dict)
async def get_ssl_metrics():
    """
    Get detailed SSL metrics for monitoring
    
    Returns Prometheus-compatible metrics including:
    - Certificate days remaining
    - Endpoint response times
    - Validation status
    - Backup timestamps
    """
    try:
        # Use the same path resolution as the health checker
        possible_paths = [
            Path("/project/metrics/ssl_metrics.json"),
            Path("/app/metrics/ssl_metrics.json"),
            Path("/home/marku/ai_workflow_engine/metrics/ssl_metrics.json")
        ]
        
        metrics_file = None
        for path in possible_paths:
            if path.exists():
                metrics_file = path
                break
        
        if metrics_file and metrics_file.exists():
            return json.loads(metrics_file.read_text())
        else:
            return {"error": "Metrics not available"}
            
    except Exception as e:
        logger.error(f"Failed to get SSL metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": str(e)}
        )

@router.post("/trigger-renewal")
async def trigger_certificate_renewal():
    """
    Manually trigger certificate renewal
    
    This endpoint allows administrators to manually trigger
    a certificate renewal check through Caddy.
    """
    try:
        # Run renewal script - try container path first, then host path
        script_paths = [
            "/project/scripts/ssl_certificate_automation.py",
            "/home/marku/ai_workflow_engine/scripts/ssl_certificate_automation.py"
        ]
        
        script_path = None
        for path in script_paths:
            if Path(path).exists():
                script_path = path
                break
        
        if not script_path:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "SSL automation script not found"}
            )
        
        cmd = f"python3 {script_path} --renew"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            return {
                "status": "success",
                "message": "Renewal triggered successfully",
                "output": result.stdout
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "status": "failed",
                    "error": result.stderr
                }
            )
            
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={"error": "Renewal timeout"}
        )
    except Exception as e:
        logger.error(f"Failed to trigger renewal: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": str(e)}
        )

@router.post("/backup")
async def backup_certificates():
    """
    Manually trigger certificate backup
    
    Creates a timestamped backup of current SSL certificates.
    """
    try:
        # Run backup script - try container path first, then host path
        script_paths = [
            "/project/scripts/ssl_certificate_automation.py",
            "/home/marku/ai_workflow_engine/scripts/ssl_certificate_automation.py"
        ]
        
        script_path = None
        for path in script_paths:
            if Path(path).exists():
                script_path = path
                break
        
        if not script_path:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "SSL automation script not found"}
            )
        
        cmd = f"python3 {script_path} --backup"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return {
                "status": "success",
                "message": "Backup completed successfully",
                "output": result.stdout
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "status": "failed",
                    "error": result.stderr
                }
            )
            
    except Exception as e:
        logger.error(f"Failed to backup certificates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": str(e)}
        )