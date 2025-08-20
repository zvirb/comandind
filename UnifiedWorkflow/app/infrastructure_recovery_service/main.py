"""
Infrastructure Recovery Service - Main Entry Point
Orchestrates all resilience enhancement components
"""
import asyncio
import logging
import signal
import sys
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import infrastructure_recovery_config
from predictive_monitor import predictive_monitor
from automated_recovery import automated_recovery
from rollback_manager import rollback_manager
from dependency_monitor import dependency_monitor
from auto_scaler import auto_scaler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Infrastructure Recovery Service",
    description="Predictive monitoring and automated recovery system with self-healing capabilities",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global service instances
services = {
    "predictive_monitor": predictive_monitor,
    "automated_recovery": automated_recovery,
    "rollback_manager": rollback_manager,
    "dependency_monitor": dependency_monitor,
    "auto_scaler": auto_scaler
}

# Service status
service_status = {
    "running": False,
    "services_initialized": False,
    "services_running": {}
}


class InfrastructureRecoveryService:
    """Main infrastructure recovery service orchestrator"""
    
    def __init__(self):
        self.config = infrastructure_recovery_config
        self.running = False
        self.tasks = []
    
    async def initialize_services(self):
        """Initialize all recovery service components"""
        try:
            logger.info("Initializing Infrastructure Recovery Service components...")
            
            # Initialize services in order
            await predictive_monitor.initialize()
            logger.info("✓ Predictive Monitor initialized")
            
            await automated_recovery.initialize()
            logger.info("✓ Automated Recovery initialized")
            
            await rollback_manager.initialize()
            logger.info("✓ Rollback Manager initialized")
            
            await dependency_monitor.initialize()
            logger.info("✓ Dependency Monitor initialized")
            
            await auto_scaler.initialize()
            logger.info("✓ Auto Scaler initialized")
            
            service_status["services_initialized"] = True
            logger.info("All Infrastructure Recovery Service components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise
    
    async def start_services(self):
        """Start all recovery service components"""
        try:
            logger.info("Starting Infrastructure Recovery Service components...")
            
            # Start services
            self.tasks = [
                asyncio.create_task(predictive_monitor.start_monitoring()),
                asyncio.create_task(automated_recovery.start_recovery_system()),
                asyncio.create_task(rollback_manager.start_rollback_manager()),
                asyncio.create_task(dependency_monitor.start_dependency_monitoring()),
                asyncio.create_task(auto_scaler.start_auto_scaling())
            ]
            
            # Update service status
            for service_name in services.keys():
                service_status["services_running"][service_name] = True
            
            self.running = True
            service_status["running"] = True
            
            logger.info("All Infrastructure Recovery Service components started successfully")
            
            # Wait for all tasks
            await asyncio.gather(*self.tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"Error starting services: {e}")
            await self.stop_services()
            raise
    
    async def stop_services(self):
        """Stop all recovery service components"""
        try:
            logger.info("Stopping Infrastructure Recovery Service components...")
            
            self.running = False
            service_status["running"] = False
            
            # Cancel all tasks
            for task in self.tasks:
                if not task.done():
                    task.cancel()
            
            # Stop services
            await predictive_monitor.stop_monitoring()
            await automated_recovery.stop_recovery_system()
            await rollback_manager.stop_rollback_manager()
            await dependency_monitor.stop_dependency_monitoring()
            await auto_scaler.stop_auto_scaling()
            
            # Update service status
            for service_name in services.keys():
                service_status["services_running"][service_name] = False
            
            logger.info("All Infrastructure Recovery Service components stopped")
            
        except Exception as e:
            logger.error(f"Error stopping services: {e}")


# Global service instance
recovery_service = InfrastructureRecoveryService()


# API Endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy" if service_status["running"] else "stopped",
        "service": "infrastructure-recovery-service",
        "version": "1.0.0",
        "components": service_status["services_running"]
    }

@app.get("/status")
async def get_service_status():
    """Get comprehensive service status"""
    try:
        status = {
            "infrastructure_recovery_service": service_status,
            "predictive_monitor": await predictive_monitor.get_all_health_scores(),
            "automated_recovery": await automated_recovery.get_recovery_status(),
            "rollback_manager": await rollback_manager.get_rollback_status(),
            "dependency_monitor": await dependency_monitor.get_dependency_status(),
            "auto_scaler": await auto_scaler.get_autoscaler_status()
        }
        return status
    except Exception as e:
        logger.error(f"Error getting service status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health-scores")
async def get_health_scores():
    """Get current health scores for all services"""
    try:
        return await predictive_monitor.get_all_health_scores()
    except Exception as e:
        logger.error(f"Error getting health scores: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/predictions/{service}")
async def get_service_prediction(service: str):
    """Get failure prediction for a specific service"""
    try:
        prediction = await predictive_monitor.get_service_prediction(service)
        return prediction
    except Exception as e:
        logger.error(f"Error getting prediction for {service}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/recovery/manual/{service}")
async def trigger_manual_recovery(service: str, recovery_type: str = "restart"):
    """Trigger manual recovery for a service"""
    try:
        # This would integrate with the automated recovery system
        result = {"message": f"Manual recovery triggered for {service}", "type": recovery_type}
        logger.info(f"Manual recovery triggered for {service}: {recovery_type}")
        return result
    except Exception as e:
        logger.error(f"Error triggering manual recovery for {service}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/rollback/manual/{service}")
async def trigger_manual_rollback(service: str, snapshot_id: str = None):
    """Trigger manual rollback for a service"""
    try:
        rollback_id = await rollback_manager.manual_rollback(service, snapshot_id)
        return {"message": f"Manual rollback triggered for {service}", "rollback_id": rollback_id}
    except Exception as e:
        logger.error(f"Error triggering manual rollback for {service}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/snapshots")
async def get_snapshots():
    """Get available rollback snapshots"""
    try:
        snapshots = []
        for snapshot_id, snapshot in rollback_manager.snapshots.items():
            snapshots.append({
                "snapshot_id": snapshot_id,
                "timestamp": snapshot.timestamp.isoformat(),
                "rollback_safe": snapshot.rollback_safe,
                "services": list(snapshot.services.keys()),
                "health_scores": snapshot.health_scores
            })
        
        # Sort by timestamp (most recent first)
        snapshots.sort(key=lambda x: x["timestamp"], reverse=True)
        return {"snapshots": snapshots}
        
    except Exception as e:
        logger.error(f"Error getting snapshots: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dependencies")
async def get_dependency_status():
    """Get dependency monitoring status"""
    try:
        return await dependency_monitor.get_dependency_status()
    except Exception as e:
        logger.error(f"Error getting dependency status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/scaling")
async def get_scaling_status():
    """Get auto-scaling status"""
    try:
        return await auto_scaler.get_autoscaler_status()
    except Exception as e:
        logger.error(f"Error getting scaling status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/scaling/manual/{service}")
async def trigger_manual_scaling(service: str, action: str, instances: int = None):
    """Trigger manual scaling action"""
    try:
        # This would integrate with the auto-scaler
        result = {
            "message": f"Manual scaling triggered for {service}",
            "action": action,
            "instances": instances
        }
        logger.info(f"Manual scaling triggered for {service}: {action} (instances: {instances})")
        return result
    except Exception as e:
        logger.error(f"Error triggering manual scaling for {service}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics/{service}")
async def get_service_metrics(service: str):
    """Get current metrics for a specific service"""
    try:
        metrics = auto_scaler.performance_metrics.get(service, {})
        if not metrics:
            raise HTTPException(status_code=404, detail=f"No metrics found for service {service}")
        
        return {
            "service": service,
            "metrics": metrics,
            "timestamp": asyncio.get_event_loop().time()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metrics for {service}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Event handlers

@app.on_event("startup")
async def startup_event():
    """Initialize and start services on startup"""
    try:
        await recovery_service.initialize_services()
        
        # Start services in background
        asyncio.create_task(recovery_service.start_services())
        
        logger.info("Infrastructure Recovery Service started successfully")
    except Exception as e:
        logger.error(f"Failed to start Infrastructure Recovery Service: {e}")
        sys.exit(1)

@app.on_event("shutdown")
async def shutdown_event():
    """Stop services on shutdown"""
    try:
        await recovery_service.stop_services()
        logger.info("Infrastructure Recovery Service shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Signal handlers

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    asyncio.create_task(recovery_service.stop_services())
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# Main entry point

if __name__ == "__main__":
    try:
        uvicorn.run(
            app,
            host=infrastructure_recovery_config.HOST,
            port=infrastructure_recovery_config.PORT,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)