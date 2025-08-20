"""
Comprehensive Health Check Module for All Services
Provides standardized health check endpoints with import validation
"""

import sys
import os
import importlib
import traceback
from typing import Dict, Any, List, Optional
from datetime import datetime
import psutil
import json


class HealthCheckManager:
    """Manages comprehensive health checks for services"""
    
    def __init__(self, service_name: str, required_imports: Optional[List[str]] = None):
        """
        Initialize health check manager
        
        Args:
            service_name: Name of the service
            required_imports: List of module names that must be importable
        """
        self.service_name = service_name
        self.required_imports = required_imports or []
        self.start_time = datetime.utcnow()
        
    def check_imports(self) -> Dict[str, Any]:
        """Validate that all required imports are available"""
        import_status = {}
        all_imports_ok = True
        
        for module_name in self.required_imports:
            try:
                importlib.import_module(module_name)
                import_status[module_name] = {
                    "status": "ok",
                    "message": f"Module {module_name} imported successfully"
                }
            except ImportError as e:
                all_imports_ok = False
                import_status[module_name] = {
                    "status": "error",
                    "message": str(e),
                    "traceback": traceback.format_exc()
                }
            except Exception as e:
                all_imports_ok = False
                import_status[module_name] = {
                    "status": "error",
                    "message": f"Unexpected error importing {module_name}: {str(e)}",
                    "traceback": traceback.format_exc()
                }
        
        return {
            "all_imports_ok": all_imports_ok,
            "imports": import_status
        }
    
    def check_python_path(self) -> Dict[str, Any]:
        """Check Python path configuration"""
        return {
            "pythonpath": os.environ.get("PYTHONPATH", "Not set"),
            "sys_path": sys.path[:10],  # First 10 entries
            "working_directory": os.getcwd(),
            "shared_module_exists": os.path.exists("/app/shared")
        }
    
    def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            cpu_percent = process.cpu_percent(interval=0.1)
            
            return {
                "memory": {
                    "rss_mb": memory_info.rss / 1024 / 1024,
                    "vms_mb": memory_info.vms / 1024 / 1024,
                    "percent": process.memory_percent()
                },
                "cpu": {
                    "percent": cpu_percent,
                    "num_threads": process.num_threads()
                },
                "disk": {
                    "cwd_usage": psutil.disk_usage('/').percent
                }
            }
        except Exception as e:
            return {
                "error": f"Failed to get system resources: {str(e)}"
            }
    
    def check_database_connection(self, db_url: Optional[str] = None) -> Dict[str, Any]:
        """Check database connectivity"""
        if not db_url:
            db_url = os.environ.get("DATABASE_URL")
        
        if not db_url:
            return {"status": "skipped", "message": "No database URL configured"}
        
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(db_url)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                return {
                    "status": "healthy",
                    "message": "Database connection successful"
                }
        except ImportError:
            return {"status": "skipped", "message": "SQLAlchemy not installed"}
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Database connection failed: {str(e)}"
            }
    
    def check_redis_connection(self, redis_url: Optional[str] = None) -> Dict[str, Any]:
        """Check Redis connectivity"""
        if not redis_url:
            redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        
        try:
            import redis
            client = redis.from_url(redis_url)
            client.ping()
            return {
                "status": "healthy",
                "message": "Redis connection successful"
            }
        except ImportError:
            return {"status": "skipped", "message": "Redis not installed"}
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Redis connection failed: {str(e)}"
            }
    
    def check_service_dependencies(self, dependencies: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Check connectivity to dependent services
        
        Args:
            dependencies: List of dicts with 'name' and 'url' keys
        """
        import requests
        results = {}
        
        for dep in dependencies:
            try:
                response = requests.get(
                    f"{dep['url']}/health",
                    timeout=5
                )
                results[dep['name']] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "status_code": response.status_code
                }
            except requests.exceptions.RequestException as e:
                results[dep['name']] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        
        return results
    
    def get_comprehensive_health(
        self,
        check_db: bool = False,
        check_redis: bool = False,
        service_dependencies: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive health status
        
        Args:
            check_db: Whether to check database connectivity
            check_redis: Whether to check Redis connectivity
            service_dependencies: List of dependent services to check
        """
        uptime_seconds = (datetime.utcnow() - self.start_time).total_seconds()
        
        health = {
            "service": self.service_name,
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": uptime_seconds,
            "checks": {}
        }
        
        # Check imports
        import_check = self.check_imports()
        health["checks"]["imports"] = import_check
        if not import_check["all_imports_ok"]:
            health["status"] = "degraded"
        
        # Check Python path
        health["checks"]["python_path"] = self.check_python_path()
        
        # Check system resources
        health["checks"]["resources"] = self.check_system_resources()
        
        # Check database if requested
        if check_db:
            db_check = self.check_database_connection()
            health["checks"]["database"] = db_check
            if db_check.get("status") == "unhealthy":
                health["status"] = "degraded"
        
        # Check Redis if requested
        if check_redis:
            redis_check = self.check_redis_connection()
            health["checks"]["redis"] = redis_check
            if redis_check.get("status") == "unhealthy":
                health["status"] = "degraded"
        
        # Check service dependencies
        if service_dependencies:
            dep_check = self.check_service_dependencies(service_dependencies)
            health["checks"]["dependencies"] = dep_check
            if any(d.get("status") == "unhealthy" for d in dep_check.values()):
                health["status"] = "degraded"
        
        # Determine overall status
        if health["status"] == "degraded":
            health["message"] = "Service is running with degraded functionality"
        else:
            health["message"] = "Service is healthy"
        
        return health


def create_fastapi_health_endpoint(
    app,
    service_name: str,
    required_imports: Optional[List[str]] = None,
    check_db: bool = False,
    check_redis: bool = False,
    service_dependencies: Optional[List[Dict[str, str]]] = None
):
    """
    Create a FastAPI health endpoint
    
    Args:
        app: FastAPI application instance
        service_name: Name of the service
        required_imports: List of required module names
        check_db: Whether to check database connectivity
        check_redis: Whether to check Redis connectivity
        service_dependencies: List of dependent services
    """
    from fastapi import Response
    
    health_manager = HealthCheckManager(service_name, required_imports)
    
    @app.get("/health")
    async def health_check(response: Response):
        """Comprehensive health check endpoint"""
        health = health_manager.get_comprehensive_health(
            check_db=check_db,
            check_redis=check_redis,
            service_dependencies=service_dependencies
        )
        
        # Set appropriate status code
        if health["status"] == "unhealthy":
            response.status_code = 503
        elif health["status"] == "degraded":
            response.status_code = 200  # Still return 200 for degraded
        
        return health
    
    @app.get("/health/simple")
    async def simple_health_check():
        """Simple health check for basic liveness probe"""
        return {"status": "ok"}
    
    return health_manager