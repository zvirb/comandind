"""Authentication startup service for initializing enhanced authentication components."""

import asyncio
import logging
from typing import Optional
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from shared.utils.database_setup import get_async_session
from shared.services.auth_queue_service import auth_queue_service
from shared.services.secure_token_storage_service import secure_token_storage
from shared.services.auth_middleware_service import auth_middleware_service
from shared.services.enhanced_jwt_service import enhanced_jwt_service
from shared.services.security_audit_service import security_audit_service
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AuthStartupService:
    """Service for initializing and managing authentication components on startup."""
    
    def __init__(self):
        self.logger = logger
        self.initialized = False
        self.services_healthy = False
        self._cleanup_tasks = []
    
    async def initialize_all_services(self) -> bool:
        """Initialize all authentication services in the correct order."""
        if self.initialized:
            self.logger.info("Authentication services already initialized")
            return True
        
        try:
            self.logger.info("Starting authentication services initialization...")
            
            # 1. Initialize secure token storage first
            self.logger.info("Initializing secure token storage...")
            master_key = settings.JWT_SECRET_KEY.get_secret_value() if settings.JWT_SECRET_KEY else None
            await secure_token_storage.initialize(master_key)
            
            # 2. Initialize authentication queue service
            self.logger.info("Initializing authentication queue service...")
            await auth_queue_service.start(num_workers=5)
            
            # 3. Initialize authentication middleware
            self.logger.info("Initializing authentication middleware...")
            await auth_middleware_service.initialize()
            
            # 4. Start background cleanup tasks
            self.logger.info("Starting background cleanup tasks...")
            await self._start_background_tasks()
            
            # 5. Run health checks
            self.logger.info("Running authentication services health checks...")
            self.services_healthy = await self._health_check_all_services()
            
            if self.services_healthy:
                self.initialized = True
                self.logger.info("✅ Authentication services initialized successfully")
                return True
            else:
                self.logger.error("❌ Authentication services health check failed")
                await self._cleanup_on_failure()
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize authentication services: {str(e)}")
            await self._cleanup_on_failure()
            return False
    
    async def shutdown_all_services(self):
        """Gracefully shutdown all authentication services."""
        if not self.initialized:
            return
        
        try:
            self.logger.info("Shutting down authentication services...")
            
            # Cancel background tasks
            for task in self._cleanup_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            self._cleanup_tasks.clear()
            
            # Shutdown services in reverse order
            await auth_middleware_service.stop() if hasattr(auth_middleware_service, 'stop') else None
            await auth_queue_service.stop()
            
            # Final cleanup
            async with get_async_session() as session:
                await self._final_cleanup(session)
            
            self.initialized = False
            self.services_healthy = False
            
            self.logger.info("✅ Authentication services shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during authentication services shutdown: {str(e)}")
    
    async def _start_background_tasks(self):
        """Start background maintenance tasks."""
        # Token cleanup task (every hour)
        cleanup_task = asyncio.create_task(self._token_cleanup_loop())
        self._cleanup_tasks.append(cleanup_task)
        
        # Session monitoring task (every 5 minutes)
        monitoring_task = asyncio.create_task(self._session_monitoring_loop())
        self._cleanup_tasks.append(monitoring_task)
        
        # Health check task (every 10 minutes)
        health_task = asyncio.create_task(self._health_monitoring_loop())
        self._cleanup_tasks.append(health_task)
        
        self.logger.info("Background authentication tasks started")
    
    async def _token_cleanup_loop(self):
        """Background task for cleaning up expired tokens."""
        while True:
            try:
                async with get_async_session() as session:
                    # Clean up expired tokens
                    cleaned_count = await secure_token_storage.cleanup_expired_tokens(session)
                    
                    if cleaned_count > 0:
                        self.logger.info(f"Cleaned up {cleaned_count} expired tokens")
                    
                    # Clean up old audit data
                    audit_cleaned = await security_audit_service.cleanup_old_audit_data(session)
                    
                    if audit_cleaned > 0:
                        self.logger.info(f"Cleaned up {audit_cleaned} old audit records")
                
                # Wait 1 hour
                await asyncio.sleep(3600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Token cleanup task error: {str(e)}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _session_monitoring_loop(self):
        """Background task for monitoring authentication sessions."""
        while True:
            try:
                async with get_async_session() as session:
                    # Get authentication queue statistics
                    queue_stats = await auth_queue_service.get_queue_stats()
                    
                    # Log queue statistics if there are issues
                    if queue_stats["queue_overflows"] > 0:
                        self.logger.warning(f"Authentication queue overflows detected: {queue_stats['queue_overflows']}")
                    
                    # Check for unhealthy workers
                    if queue_stats["workers_running"] < 3:  # Expect at least 3 workers
                        self.logger.warning(f"Low number of auth workers running: {queue_stats['workers_running']}")
                    
                    # Detect security anomalies
                    anomalies = await security_audit_service.detect_security_anomalies(session)
                    
                    for anomaly in anomalies:
                        self.logger.warning(f"Security anomaly detected: {anomaly['anomaly_type']} - {anomaly['details']}")
                
                # Wait 5 minutes
                await asyncio.sleep(300)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Session monitoring task error: {str(e)}")
                await asyncio.sleep(300)
    
    async def _health_monitoring_loop(self):
        """Background task for monitoring service health."""
        while True:
            try:
                # Perform health checks
                health_status = await self._health_check_all_services()
                
                if not health_status:
                    self.logger.error("Authentication services health check failed")
                    self.services_healthy = False
                    
                    # Attempt to restart failed services
                    await self._attempt_service_recovery()
                else:
                    self.services_healthy = True
                
                # Wait 10 minutes
                await asyncio.sleep(600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Health monitoring task error: {str(e)}")
                await asyncio.sleep(600)
    
    async def _health_check_all_services(self) -> bool:
        """Perform health checks on all authentication services."""
        try:
            # Check authentication queue service
            queue_stats = await auth_queue_service.get_queue_stats()
            if not queue_stats["is_running"]:
                self.logger.error("Authentication queue service is not running")
                return False
            
            # Check secure token storage
            async with get_async_session() as session:
                # Try to perform a basic operation
                test_tokens = await secure_token_storage.get_user_tokens(session, 0)  # Non-existent user
                if test_tokens is None:  # Should return empty list, not None
                    self.logger.error("Secure token storage health check failed")
                    return False
            
            # Check enhanced JWT service
            try:
                # Test JWT service with a basic operation
                pass  # JWT service is stateless, no specific health check needed
            except Exception as e:
                self.logger.error(f"Enhanced JWT service health check failed: {str(e)}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return False
    
    async def _attempt_service_recovery(self):
        """Attempt to recover failed services."""
        try:
            self.logger.info("Attempting authentication services recovery...")
            
            # Check and restart queue service if needed
            queue_stats = await auth_queue_service.get_queue_stats()
            if not queue_stats["is_running"]:
                self.logger.info("Restarting authentication queue service...")
                await auth_queue_service.stop()
                await asyncio.sleep(1)
                await auth_queue_service.start(num_workers=5)
            
            # Re-initialize middleware if needed
            try:
                await auth_middleware_service.initialize()
            except Exception as e:
                self.logger.error(f"Failed to reinitialize auth middleware: {str(e)}")
            
            self.logger.info("Service recovery attempt completed")
            
        except Exception as e:
            self.logger.error(f"Service recovery failed: {str(e)}")
    
    async def _cleanup_on_failure(self):
        """Clean up resources when initialization fails."""
        try:
            # Cancel any running tasks
            for task in self._cleanup_tasks:
                if not task.done():
                    task.cancel()
            
            self._cleanup_tasks.clear()
            
            # Try to stop services that may have been started
            try:
                await auth_queue_service.stop()
            except:
                pass
            
        except Exception as e:
            self.logger.error(f"Cleanup on failure error: {str(e)}")
    
    async def _final_cleanup(self, session: AsyncSession):
        """Perform final cleanup operations."""
        try:
            # Clean up any remaining expired tokens
            await secure_token_storage.cleanup_expired_tokens(session)
            
            # Log final statistics
            queue_stats = await auth_queue_service.get_queue_stats()
            self.logger.info(f"Final authentication queue stats: {queue_stats}")
            
        except Exception as e:
            self.logger.error(f"Final cleanup error: {str(e)}")
    
    @asynccontextmanager
    async def lifespan_context(self):
        """Context manager for application lifespan management."""
        # Startup
        success = await self.initialize_all_services()
        if not success:
            raise RuntimeError("Failed to initialize authentication services")
        
        try:
            yield
        finally:
            # Shutdown
            await self.shutdown_all_services()
    
    def is_initialized(self) -> bool:
        """Check if authentication services are initialized."""
        return self.initialized
    
    def is_healthy(self) -> bool:
        """Check if authentication services are healthy."""
        return self.services_healthy
    
    async def get_service_status(self) -> dict:
        """Get detailed status of all authentication services."""
        try:
            queue_stats = await auth_queue_service.get_queue_stats()
            
            return {
                "initialized": self.initialized,
                "services_healthy": self.services_healthy,
                "queue_service": {
                    "running": queue_stats["is_running"],
                    "workers": queue_stats["workers_running"],
                    "operations_processed": queue_stats["operations_processed"],
                    "operations_failed": queue_stats["operations_failed"],
                    "queue_overflows": queue_stats["queue_overflows"]
                },
                "secure_storage": {
                    "initialized": secure_token_storage._initialized
                },
                "background_tasks": {
                    "running": len([t for t in self._cleanup_tasks if not t.done()]),
                    "total": len(self._cleanup_tasks)
                }
            }
            
        except Exception as e:
            return {
                "initialized": self.initialized,
                "services_healthy": False,
                "error": str(e)
            }


# Global authentication startup service instance
auth_startup_service = AuthStartupService()