#!/usr/bin/env python3
"""
Orchestration Execution Logger
Standalone logging system for orchestration workflows
Generates detailed logs for auditing and self-improvement
"""

import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import uuid

class OrchestrationLogger:
    """Comprehensive logging system for orchestration workflows"""
    
    def __init__(self):
        self.base_path = Path("/home/marku/ai_workflow_engine")
        self.logs_dir = self.base_path / ".claude" / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for organization
        (self.logs_dir / "executions").mkdir(exist_ok=True)
        (self.logs_dir / "agents").mkdir(exist_ok=True)
        (self.logs_dir / "phases").mkdir(exist_ok=True)
        (self.logs_dir / "validations").mkdir(exist_ok=True)
        
        # Current execution context
        self.current_execution_id = None
        self.current_phase = None
        self.execution_start_time = None
        self.agent_activities = []
        self.phase_activities = []
        self.validation_results = []
        
        # Setup logging
        self.setup_logging()
        
        # Thread lock for concurrent logging
        self.log_lock = threading.Lock()
        
    def setup_logging(self):
        """Configure orchestration-specific logging"""
        
        # Main orchestration execution log
        self.main_log = self.logs_dir / "orchestration_executions.log"
        
        # Configure logger
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s UTC] [%(levelname)s] [orchestration-logger] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # File handler for main orchestration log
        file_handler = logging.FileHandler(self.main_log)
        file_handler.setFormatter(logging.Formatter(
            '[%(asctime)s UTC] [%(levelname)s] [orchestration-logger] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(file_handler)
    
    def start_orchestration_execution(self, trigger_reason: str = "manual", context: Dict[str, Any] = None) -> str:
        """Start a new orchestration execution and return execution ID"""
        
        with self.log_lock:
            self.current_execution_id = f"exec_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            self.execution_start_time = datetime.utcnow()
            self.current_phase = None
            
            # Reset tracking
            self.agent_activities = []
            self.phase_activities = []
            self.validation_results = []
            
            # Create execution-specific log file
            execution_log = self.logs_dir / "executions" / f"{self.current_execution_id}.log"
            
            # Log execution start
            execution_data = {
                "execution_id": self.current_execution_id,
                "start_time": self.execution_start_time.isoformat(),
                "trigger_reason": trigger_reason,
                "context": context or {}
            }
            
            with open(execution_log, 'w') as f:
                f.write(f"[{self.execution_start_time.isoformat()} UTC] [INFO] [orchestration-executor] EXECUTION STARTED\n")
                f.write(f"[{self.execution_start_time.isoformat()} UTC] [INFO] [orchestration-executor] Execution ID: {self.current_execution_id}\n")
                f.write(f"[{self.execution_start_time.isoformat()} UTC] [INFO] [orchestration-executor] Trigger: {trigger_reason}\n")
                if context:
                    f.write(f"[{self.execution_start_time.isoformat()} UTC] [INFO] [orchestration-executor] Context: {json.dumps(context, indent=2)}\n")
                f.write(f"[{self.execution_start_time.isoformat()} UTC] [INFO] [orchestration-executor] Starting 9-phase orchestration workflow\n")
            
            # Log to main orchestration log
            self.logger.info(f"🚀 ORCHESTRATION STARTED - ID: {self.current_execution_id}, Trigger: {trigger_reason}")
            
            return self.current_execution_id
    
    def start_phase(self, phase_number: int, phase_name: str, description: str = ""):
        """Log the start of an orchestration phase"""
        
        if not self.current_execution_id:
            raise RuntimeError("No active orchestration execution. Call start_orchestration_execution() first.")
        
        with self.log_lock:
            self.current_phase = f"phase_{phase_number}"
            phase_start_time = datetime.utcnow()
            
            # Log to execution file
            execution_log = self.logs_dir / "executions" / f"{self.current_execution_id}.log"
            
            with open(execution_log, 'a') as f:
                f.write(f"[{phase_start_time.isoformat()} UTC] [INFO] [orchestration-executor] === PHASE {phase_number}: {phase_name.upper()} ===\n")
                f.write(f"[{phase_start_time.isoformat()} UTC] [INFO] [orchestration-executor] Phase {phase_number} STARTED: {phase_name}\n")
                if description:
                    f.write(f"[{phase_start_time.isoformat()} UTC] [INFO] [orchestration-executor] Description: {description}\n")
            
            # Create phase-specific log
            phase_log = self.logs_dir / "phases" / f"{self.current_execution_id}_phase_{phase_number}_{phase_name.lower().replace(' ', '_')}.log"
            
            with open(phase_log, 'w') as f:
                f.write(f"[{phase_start_time.isoformat()} UTC] [INFO] [phase-{phase_number}] Phase {phase_number} started: {phase_name}\n")
                if description:
                    f.write(f"[{phase_start_time.isoformat()} UTC] [INFO] [phase-{phase_number}] Description: {description}\n")
            
            # Track phase activity
            phase_activity = {
                "phase_number": phase_number,
                "phase_name": phase_name,
                "description": description,
                "start_time": phase_start_time.isoformat(),
                "status": "in_progress"
            }
            self.phase_activities.append(phase_activity)
            
            # Log to main log
            self.logger.info(f"📋 PHASE {phase_number} STARTED: {phase_name}")
    
    def log_agent_activity(self, agent_name: str, action: str, details: Dict[str, Any] = None, status: str = "info"):
        """Log agent activity during orchestration"""
        
        if not self.current_execution_id:
            return
        
        with self.log_lock:
            activity_time = datetime.utcnow()
            
            # Log to execution file
            execution_log = self.logs_dir / "executions" / f"{self.current_execution_id}.log"
            
            log_level = status.upper() if status in ["info", "warning", "error", "critical"] else "INFO"
            
            with open(execution_log, 'a') as f:
                f.write(f"[{activity_time.isoformat()} UTC] [{log_level}] [orchestration-executor] AGENT: {agent_name} - {action}\n")
                if details:
                    f.write(f"[{activity_time.isoformat()} UTC] [{log_level}] [orchestration-executor] Details: {json.dumps(details, indent=2)}\n")
            
            # Create/append to agent-specific log
            agent_log = self.logs_dir / "agents" / f"{self.current_execution_id}_{agent_name.replace('-', '_')}.log"
            
            with open(agent_log, 'a') as f:
                f.write(f"[{activity_time.isoformat()} UTC] [{log_level}] [{agent_name}] {action}\n")
                if details:
                    f.write(f"[{activity_time.isoformat()} UTC] [{log_level}] [{agent_name}] Details: {json.dumps(details, indent=2)}\n")
            
            # Track agent activity
            agent_activity = {
                "agent_name": agent_name,
                "action": action,
                "details": details or {},
                "status": status,
                "timestamp": activity_time.isoformat(),
                "phase": self.current_phase
            }
            self.agent_activities.append(agent_activity)
            
            # Log to main log
            status_emoji = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "critical": "🚨"}.get(status, "📝")
            self.logger.info(f"{status_emoji} AGENT {agent_name}: {action}")
    
    def complete_phase(self, phase_number: int, success: bool = True, summary: str = "", evidence: Dict[str, Any] = None):
        """Log the completion of an orchestration phase"""
        
        if not self.current_execution_id:
            return
        
        with self.log_lock:
            completion_time = datetime.utcnow()
            status = "COMPLETED" if success else "FAILED"
            log_level = "INFO" if success else "ERROR"
            
            # Log to execution file
            execution_log = self.logs_dir / "executions" / f"{self.current_execution_id}.log"
            
            with open(execution_log, 'a') as f:
                f.write(f"[{completion_time.isoformat()} UTC] [{log_level}] [orchestration-executor] Phase {phase_number} {status}\n")
                if summary:
                    f.write(f"[{completion_time.isoformat()} UTC] [{log_level}] [orchestration-executor] Summary: {summary}\n")
                if evidence:
                    f.write(f"[{completion_time.isoformat()} UTC] [{log_level}] [orchestration-executor] Evidence: {json.dumps(evidence, indent=2)}\n")
            
            # Update phase activity
            for phase_activity in self.phase_activities:
                if phase_activity["phase_number"] == phase_number and phase_activity["status"] == "in_progress":
                    phase_activity.update({
                        "status": "completed" if success else "failed",
                        "completion_time": completion_time.isoformat(),
                        "summary": summary,
                        "evidence": evidence or {}
                    })
                    break
            
            # Log to main log
            status_emoji = "✅" if success else "❌"
            self.logger.info(f"{status_emoji} PHASE {phase_number} {status}: {summary}")
    
    def log_validation_result(self, validator: str, check_name: str, success: bool, details: Dict[str, Any] = None):
        """Log validation results for orchestration auditing"""
        
        if not self.current_execution_id:
            return
        
        with self.log_lock:
            validation_time = datetime.utcnow()
            
            # Create validation log entry
            validation_result = {
                "validator": validator,
                "check_name": check_name,
                "success": success,
                "details": details or {},
                "timestamp": validation_time.isoformat(),
                "execution_id": self.current_execution_id,
                "phase": self.current_phase
            }
            self.validation_results.append(validation_result)
            
            # Log to validation file
            validation_log = self.logs_dir / "validations" / f"{self.current_execution_id}_validations.log"
            
            log_level = "INFO" if success else "ERROR"
            status_text = "PASSED" if success else "FAILED"
            
            with open(validation_log, 'a') as f:
                f.write(f"[{validation_time.isoformat()} UTC] [{log_level}] [{validator}] VALIDATION {status_text}: {check_name}\n")
                if details:
                    f.write(f"[{validation_time.isoformat()} UTC] [{log_level}] [{validator}] Details: {json.dumps(details, indent=2)}\n")
            
            # Log to execution file
            execution_log = self.logs_dir / "executions" / f"{self.current_execution_id}.log"
            
            with open(execution_log, 'a') as f:
                f.write(f"[{validation_time.isoformat()} UTC] [{log_level}] [orchestration-executor] VALIDATION {status_text}: {validator} - {check_name}\n")
            
            # Log to main log
            status_emoji = "✅" if success else "❌"
            self.logger.info(f"{status_emoji} VALIDATION {validator}: {check_name} - {status_text}")
    
    def complete_orchestration_execution(self, success: bool = True, final_summary: str = ""):
        """Complete orchestration execution and generate final logs"""
        
        if not self.current_execution_id:
            return
        
        with self.log_lock:
            completion_time = datetime.utcnow()
            duration = (completion_time - self.execution_start_time).total_seconds()
            
            # Generate comprehensive execution summary
            execution_summary = {
                "execution_id": self.current_execution_id,
                "start_time": self.execution_start_time.isoformat(),
                "completion_time": completion_time.isoformat(),
                "duration_seconds": duration,
                "success": success,
                "final_summary": final_summary,
                "phases_completed": len([p for p in self.phase_activities if p["status"] == "completed"]),
                "phases_failed": len([p for p in self.phase_activities if p["status"] == "failed"]),
                "agent_activities_count": len(self.agent_activities),
                "validations_passed": len([v for v in self.validation_results if v["success"]]),
                "validations_failed": len([v for v in self.validation_results if not v["success"]]),
                "phase_activities": self.phase_activities,
                "agent_activities": self.agent_activities,
                "validation_results": self.validation_results
            }
            
            # Save execution summary
            summary_file = self.logs_dir / "executions" / f"{self.current_execution_id}_summary.json"
            
            with open(summary_file, 'w') as f:
                json.dump(execution_summary, f, indent=2)
            
            # Log to execution file
            execution_log = self.logs_dir / "executions" / f"{self.current_execution_id}.log"
            
            status_text = "COMPLETED SUCCESSFULLY" if success else "FAILED"
            log_level = "INFO" if success else "ERROR"
            
            with open(execution_log, 'a') as f:
                f.write(f"[{completion_time.isoformat()} UTC] [{log_level}] [orchestration-executor] === ORCHESTRATION {status_text} ===\n")
                f.write(f"[{completion_time.isoformat()} UTC] [{log_level}] [orchestration-executor] Duration: {duration:.2f} seconds\n")
                f.write(f"[{completion_time.isoformat()} UTC] [{log_level}] [orchestration-executor] Phases completed: {execution_summary['phases_completed']}\n")
                f.write(f"[{completion_time.isoformat()} UTC] [{log_level}] [orchestration-executor] Phases failed: {execution_summary['phases_failed']}\n")
                f.write(f"[{completion_time.isoformat()} UTC] [{log_level}] [orchestration-executor] Validations passed: {execution_summary['validations_passed']}\n")
                f.write(f"[{completion_time.isoformat()} UTC] [{log_level}] [orchestration-executor] Validations failed: {execution_summary['validations_failed']}\n")
                f.write(f"[{completion_time.isoformat()} UTC] [{log_level}] [orchestration-executor] Final summary: {final_summary}\n")
                f.write(f"[{completion_time.isoformat()} UTC] [{log_level}] [orchestration-executor] Summary file: {summary_file}\n")
            
            # Log to main log
            status_emoji = "🎉" if success else "💥"
            self.logger.info(f"{status_emoji} ORCHESTRATION {status_text} - ID: {self.current_execution_id}, Duration: {duration:.2f}s")
            
            # Reset current execution
            self.current_execution_id = None
            self.current_phase = None
            self.execution_start_time = None
            
            return execution_summary
    
    def verify_log_generation(self) -> Dict[str, Any]:
        """Verify that all expected logs are being generated"""
        
        verification = {
            "main_log_exists": self.main_log.exists(),
            "main_log_size_bytes": self.main_log.stat().st_size if self.main_log.exists() else 0,
            "executions_dir_exists": (self.logs_dir / "executions").exists(),
            "agents_dir_exists": (self.logs_dir / "agents").exists(),
            "phases_dir_exists": (self.logs_dir / "phases").exists(),
            "validations_dir_exists": (self.logs_dir / "validations").exists(),
            "execution_logs_count": len(list((self.logs_dir / "executions").glob("*.log"))),
            "execution_summaries_count": len(list((self.logs_dir / "executions").glob("*.json"))),
            "agent_logs_count": len(list((self.logs_dir / "agents").glob("*.log"))),
            "phase_logs_count": len(list((self.logs_dir / "phases").glob("*.log"))),
            "validation_logs_count": len(list((self.logs_dir / "validations").glob("*.log"))),
            "verification_timestamp": datetime.utcnow().isoformat()
        }
        
        return verification

# Example usage and testing
if __name__ == "__main__":
    # Test the orchestration logger
    logger = OrchestrationLogger()
    
    # Simulate a complete orchestration execution
    execution_id = logger.start_orchestration_execution("test_trigger", {"test": True})
    
    # Phase 1
    logger.start_phase(1, "Agent Integration Check", "Testing agent integration")
    logger.log_agent_activity("agent-integration-orchestrator", "Scanning for new agents")
    logger.log_agent_activity("agent-integration-orchestrator", "No new agents found")
    logger.complete_phase(1, True, "Agent integration check completed successfully")
    
    # Phase 2
    logger.start_phase(2, "Strategic Planning", "Creating execution strategy")
    logger.log_agent_activity("project-orchestrator", "Analyzing system failures")
    logger.log_agent_activity("project-orchestrator", "Creating remediation plan")
    logger.complete_phase(2, True, "Strategic plan created")
    
    # Log some validations
    logger.log_validation_result("test-validator", "endpoint_health_check", True, {"endpoint": "test", "status": 200})
    logger.log_validation_result("test-validator", "authentication_check", False, {"error": "Redis auth failed"})
    
    # Complete execution
    summary = logger.complete_orchestration_execution(False, "Test execution completed with validation failures")
    
    # Verify log generation
    verification = logger.verify_log_generation()
    print("Log generation verification:", json.dumps(verification, indent=2))