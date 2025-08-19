#!/usr/bin/env python3
"""
Continuous Orchestration Health Monitor
Monitors system health and triggers orchestration when failures detected
Generates logs in .claude/logs/ for orchestration auditing
"""

import time
import json
import logging
import requests
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import signal
import sys

class OrchestrationHealthMonitor:
    """Continuous health monitoring with orchestration triggering"""
    
    def __init__(self):
        self.base_path = Path("/home/marku/ai_workflow_engine")
        self.logs_dir = self.base_path / ".claude" / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure logging
        self.setup_logging()
        
        # Monitoring configuration
        self.monitoring_interval = 30  # seconds
        self.failure_threshold = 3     # consecutive failures before triggering orchestration
        self.running = False
        
        # Health check endpoints
        self.health_checks = {
            "api_health": "http://localhost:8080/health",
            "api_metrics": "http://localhost:8080/api/v1/monitoring/metrics", 
            "categories_api": "https://aiwfe.com/api/v1/categories",
            "calendar_events_api": "https://aiwfe.com/api/v1/calendar/events",
            "tasks_api": "https://aiwfe.com/api/v1/tasks"
        }
        
        # Failure tracking
        self.failure_counts = {check: 0 for check in self.health_checks}
        self.last_health_status = {}
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
        
    def setup_logging(self):
        """Configure comprehensive logging to orchestration directory"""
        
        # Main orchestration log
        self.orchestration_log = self.logs_dir / "orchestration_health_monitor.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s UTC] [%(levelname)s] [orchestration-monitor] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Create file handler for orchestration logs
        file_handler = logging.FileHandler(self.orchestration_log)
        file_handler.setFormatter(logging.Formatter(
            '[%(asctime)s UTC] [%(levelname)s] [orchestration-monitor] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(file_handler)
        
    def check_endpoint_health(self, name: str, url: str) -> Dict[str, Any]:
        """Check health of a specific endpoint"""
        try:
            response = requests.get(url, timeout=10)
            is_healthy = response.status_code < 500
            
            result = {
                "endpoint": name,
                "url": url,
                "status_code": response.status_code,
                "healthy": is_healthy,
                "response_time_ms": response.elapsed.total_seconds() * 1000,
                "timestamp": datetime.utcnow().isoformat(),
                "error": None
            }
            
            if not is_healthy:
                result["error"] = f"HTTP {response.status_code}"
                
            return result
            
        except Exception as e:
            return {
                "endpoint": name,
                "url": url,
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def perform_health_checks(self) -> Dict[str, Any]:
        """Perform all health checks and return results"""
        results = {}
        
        for name, url in self.health_checks.items():
            result = self.check_endpoint_health(name, url)
            results[name] = result
            
            # Log individual check results
            if result["healthy"]:
                self.logger.info(f"✅ {name} healthy: {result.get('status_code', 'N/A')}")
                self.failure_counts[name] = 0  # Reset failure count
            else:
                self.failure_counts[name] += 1
                self.logger.error(f"❌ {name} failed ({self.failure_counts[name]}/{self.failure_threshold}): {result['error']}")
        
        return results
    
    def check_for_orchestration_triggers(self, health_results: Dict[str, Any]) -> bool:
        """Check if orchestration should be triggered based on health results"""
        
        critical_failures = []
        
        for check_name, failure_count in self.failure_counts.items():
            if failure_count >= self.failure_threshold:
                critical_failures.append({
                    "check": check_name,
                    "failure_count": failure_count,
                    "last_result": health_results.get(check_name, {})
                })
        
        if critical_failures:
            self.logger.critical(f"🚨 ORCHESTRATION TRIGGER: {len(critical_failures)} critical failures detected")
            
            # Log orchestration trigger details
            trigger_log = self.logs_dir / f"orchestration_trigger_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            trigger_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "trigger_reason": "health_check_failures",
                "critical_failures": critical_failures,
                "all_health_results": health_results
            }
            
            with open(trigger_log, 'w') as f:
                json.dump(trigger_data, f, indent=2)
            
            self.logger.info(f"📝 Orchestration trigger logged: {trigger_log}")
            return True
        
        return False
    
    def trigger_orchestration(self, health_results: Dict[str, Any]):
        """Trigger orchestration workflow to address failures"""
        
        self.logger.info("🚀 Triggering orchestration workflow...")
        
        # Create orchestration execution log
        execution_id = f"health_trigger_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        execution_log = self.logs_dir / f"orchestration_execution_{execution_id}.log"
        
        # Log orchestration start
        with open(execution_log, 'w') as f:
            f.write(f"[{datetime.utcnow().isoformat()} UTC] [INFO] [orchestration-executor] Starting orchestration due to health check failures\n")
            f.write(f"[{datetime.utcnow().isoformat()} UTC] [INFO] [orchestration-executor] Execution ID: {execution_id}\n")
            
            # Log detected failures
            for check_name, failure_count in self.failure_counts.items():
                if failure_count >= self.failure_threshold:
                    f.write(f"[{datetime.utcnow().isoformat()} UTC] [ERROR] [orchestration-executor] Critical failure: {check_name} ({failure_count} consecutive failures)\n")
        
        # Note: In real implementation, this would trigger the actual orchestration
        # For now, we simulate orchestration response
        self.simulate_orchestration_response(execution_id, execution_log, health_results)
        
    def simulate_orchestration_response(self, execution_id: str, execution_log: Path, health_results: Dict[str, Any]):
        """Simulate orchestration response (placeholder for actual implementation)"""
        
        time.sleep(2)  # Simulate processing time
        
        with open(execution_log, 'a') as f:
            f.write(f"[{datetime.utcnow().isoformat()} UTC] [INFO] [orchestration-executor] Phase 1: Agent Integration Check - STARTED\n")
            f.write(f"[{datetime.utcnow().isoformat()} UTC] [INFO] [orchestration-executor] Phase 1: Agent Integration Check - COMPLETED\n")
            f.write(f"[{datetime.utcnow().isoformat()} UTC] [INFO] [orchestration-executor] Phase 2: Strategic Planning - STARTED\n")
            f.write(f"[{datetime.utcnow().isoformat()} UTC] [INFO] [orchestration-executor] Phase 2: Strategic Planning - Health monitoring identified API failures\n")
            f.write(f"[{datetime.utcnow().isoformat()} UTC] [INFO] [orchestration-executor] Phase 2: Strategic Planning - COMPLETED\n")
            f.write(f"[{datetime.utcnow().isoformat()} UTC] [WARNING] [orchestration-executor] Orchestration framework needs actual implementation\n")
            f.write(f"[{datetime.utcnow().isoformat()} UTC] [INFO] [orchestration-executor] Execution completed: {execution_id}\n")
        
        self.logger.info(f"📋 Orchestration execution logged: {execution_log}")
        
        # Reset failure counts after triggering orchestration
        for check in self.failure_counts:
            self.failure_counts[check] = 0
    
    def generate_periodic_summary(self):
        """Generate periodic summary of orchestration activity"""
        
        summary_file = self.logs_dir / f"orchestration_summary_{datetime.utcnow().strftime('%Y%m%d')}.json"
        
        summary = {
            "date": datetime.utcnow().strftime('%Y-%m-%d'),
            "monitoring_interval_seconds": self.monitoring_interval,
            "failure_threshold": self.failure_threshold,
            "health_checks_configured": list(self.health_checks.keys()),
            "current_failure_counts": self.failure_counts.copy(),
            "last_summary_time": datetime.utcnow().isoformat(),
            "log_generation_verified": self.verify_log_generation()
        }
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        self.logger.info(f"📊 Daily summary generated: {summary_file}")
        
    def verify_log_generation(self) -> Dict[str, Any]:
        """Verify that orchestration logs are being generated correctly"""
        
        log_verification = {
            "main_log_exists": self.orchestration_log.exists(),
            "main_log_size_bytes": self.orchestration_log.stat().st_size if self.orchestration_log.exists() else 0,
            "logs_directory_exists": self.logs_dir.exists(),
            "total_log_files": len(list(self.logs_dir.glob("orchestration_*.log"))),
            "total_json_files": len(list(self.logs_dir.glob("orchestration_*.json"))),
            "verification_timestamp": datetime.utcnow().isoformat()
        }
        
        return log_verification
    
    def run_monitoring_cycle(self):
        """Run a single monitoring cycle"""
        
        self.logger.info("🔍 Starting health monitoring cycle")
        
        # Perform health checks
        health_results = self.perform_health_checks()
        
        # Check if orchestration should be triggered
        should_trigger = self.check_for_orchestration_triggers(health_results)
        
        if should_trigger:
            self.trigger_orchestration(health_results)
        
        # Log cycle completion
        healthy_count = sum(1 for result in health_results.values() if result["healthy"])
        total_count = len(health_results)
        
        self.logger.info(f"✅ Monitoring cycle completed: {healthy_count}/{total_count} endpoints healthy")
        
    def start_monitoring(self):
        """Start continuous health monitoring"""
        
        self.running = True
        self.logger.info("🚀 Starting Orchestration Health Monitor")
        self.logger.info(f"📋 Monitoring {len(self.health_checks)} endpoints every {self.monitoring_interval} seconds")
        
        last_summary_day = None
        
        while self.running:
            try:
                # Run monitoring cycle
                self.run_monitoring_cycle()
                
                # Generate daily summary if day changed
                current_day = datetime.utcnow().strftime('%Y-%m-%d')
                if last_summary_day != current_day:
                    self.generate_periodic_summary()
                    last_summary_day = current_day
                
                # Wait for next cycle
                time.sleep(self.monitoring_interval)
                
            except KeyboardInterrupt:
                self.logger.info("🛑 Received shutdown signal")
                break
            except Exception as e:
                self.logger.error(f"❌ Error in monitoring cycle: {e}")
                time.sleep(self.monitoring_interval)
        
        self.logger.info("🏁 Orchestration Health Monitor stopped")
    
    def shutdown(self, signum, frame):
        """Graceful shutdown handler"""
        self.logger.info(f"📡 Received signal {signum}, shutting down gracefully...")
        self.running = False

def main():
    """Main entry point"""
    monitor = OrchestrationHealthMonitor()
    monitor.start_monitoring()

if __name__ == "__main__":
    main()