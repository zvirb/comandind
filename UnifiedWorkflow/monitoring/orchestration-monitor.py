#!/usr/bin/env python3
"""
Orchestration Monitoring and Validation System
Real-time monitoring of the 12-phase workflow execution
"""

import json
import time
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class PhaseMetrics:
    """Metrics for a single workflow phase"""
    phase_id: str
    phase_name: str
    status: str  # pending, in_progress, completed, failed
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    agent_count: int = 0
    token_usage: int = 0
    success_criteria_met: bool = False
    evidence_collected: bool = False
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

@dataclass
class AgentMetrics:
    """Metrics for individual agent execution"""
    agent_name: str
    domain: str
    phase: str
    status: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    tool_usage: Dict[str, int] = None
    context_package_size: int = 0
    output_size: int = 0
    validation_passed: bool = False
    errors: List[str] = None
    
    def __post_init__(self):
        if self.tool_usage is None:
            self.tool_usage = {}
        if self.errors is None:
            self.errors = []

@dataclass
class WorkflowMetrics:
    """Overall workflow execution metrics"""
    workflow_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    current_phase: str = "phase_0"
    total_duration: Optional[float] = None
    phases_completed: int = 0
    phases_failed: int = 0
    loop_iterations: int = 0
    total_token_usage: int = 0
    success: bool = False
    completion_reason: str = ""

class OrchestrationMonitor:
    """
    Real-time monitoring system for workflow orchestration
    """
    
    def __init__(self, config_path: str = "monitoring/config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.logger = self._setup_logging()
        self.metrics_storage = Path(self.config.get("metrics_storage", ".monitoring"))
        self.metrics_storage.mkdir(exist_ok=True)
        
        # Current workflow tracking
        self.current_workflow: Optional[WorkflowMetrics] = None
        self.phase_metrics: Dict[str, PhaseMetrics] = {}
        self.agent_metrics: List[AgentMetrics] = []
        
        # Performance thresholds
        self.thresholds = self.config.get("thresholds", {
            "max_phase_duration": 1800,  # 30 minutes
            "max_workflow_duration": 7200,  # 2 hours
            "max_token_usage": 100000,
            "max_error_rate": 0.1
        })
        
    def _load_config(self) -> Dict[str, Any]:
        """Load monitoring configuration"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Default monitoring configuration"""
        return {
            "logging_level": "INFO",
            "metrics_retention_days": 30,
            "alert_thresholds": {
                "phase_timeout": 1800,
                "workflow_timeout": 7200,
                "error_rate": 0.1,
                "token_usage": 100000
            },
            "notification_channels": [],
            "dashboard_enabled": True,
            "real_time_updates": True
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logging.basicConfig(
            level=getattr(logging, self.config.get("logging_level", "INFO")),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.metrics_storage / "orchestration.log"),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger("OrchestrationMonitor")
    
    def start_workflow(self, workflow_id: str) -> None:
        """Start monitoring a new workflow"""
        self.current_workflow = WorkflowMetrics(
            workflow_id=workflow_id,
            start_time=datetime.now()
        )
        self.phase_metrics = {}
        self.agent_metrics = []
        
        self.logger.info(f"Started monitoring workflow: {workflow_id}")
        self._save_metrics()
    
    def start_phase(self, phase_id: str, phase_name: str) -> None:
        """Start monitoring a workflow phase"""
        if not self.current_workflow:
            raise ValueError("No active workflow to monitor")
        
        phase_metric = PhaseMetrics(
            phase_id=phase_id,
            phase_name=phase_name,
            status="in_progress",
            start_time=datetime.now()
        )
        
        self.phase_metrics[phase_id] = phase_metric
        self.current_workflow.current_phase = phase_id
        
        self.logger.info(f"Started phase: {phase_id} - {phase_name}")
        self._save_metrics()
    
    def complete_phase(self, phase_id: str, success: bool = True, 
                      evidence_collected: bool = False) -> None:
        """Mark a phase as completed"""
        if phase_id not in self.phase_metrics:
            self.logger.warning(f"Phase {phase_id} not found in metrics")
            return
        
        phase = self.phase_metrics[phase_id]
        phase.end_time = datetime.now()
        phase.duration = (phase.end_time - phase.start_time).total_seconds()
        phase.status = "completed" if success else "failed"
        phase.success_criteria_met = success
        phase.evidence_collected = evidence_collected
        
        if success:
            self.current_workflow.phases_completed += 1
        else:
            self.current_workflow.phases_failed += 1
        
        self.logger.info(f"Completed phase: {phase_id} (success: {success})")
        self._check_thresholds(phase)
        self._save_metrics()
    
    def start_agent(self, agent_name: str, domain: str, phase: str,
                   context_package_size: int = 0) -> None:
        """Start monitoring an agent execution"""
        agent_metric = AgentMetrics(
            agent_name=agent_name,
            domain=domain,
            phase=phase,
            status="in_progress",
            start_time=datetime.now(),
            context_package_size=context_package_size
        )
        
        self.agent_metrics.append(agent_metric)
        
        # Update phase agent count
        if phase in self.phase_metrics:
            self.phase_metrics[phase].agent_count += 1
        
        self.logger.info(f"Started agent: {agent_name} in {domain} domain")
        self._save_metrics()
    
    def complete_agent(self, agent_name: str, success: bool = True,
                      output_size: int = 0, tool_usage: Dict[str, int] = None) -> None:
        """Mark an agent execution as completed"""
        # Find the most recent agent execution
        agent_metric = None
        for metric in reversed(self.agent_metrics):
            if metric.agent_name == agent_name and metric.status == "in_progress":
                agent_metric = metric
                break
        
        if not agent_metric:
            self.logger.warning(f"Agent {agent_name} not found in active metrics")
            return
        
        agent_metric.end_time = datetime.now()
        agent_metric.duration = (agent_metric.end_time - agent_metric.start_time).total_seconds()
        agent_metric.status = "completed" if success else "failed"
        agent_metric.output_size = output_size
        agent_metric.validation_passed = success
        
        if tool_usage:
            agent_metric.tool_usage = tool_usage
        
        self.logger.info(f"Completed agent: {agent_name} (success: {success})")
        self._save_metrics()
    
    def add_error(self, context: str, error_message: str, 
                 phase: Optional[str] = None, agent: Optional[str] = None) -> None:
        """Record an error during execution"""
        self.logger.error(f"Error in {context}: {error_message}")
        
        if phase and phase in self.phase_metrics:
            self.phase_metrics[phase].errors.append(error_message)
        
        if agent:
            for metric in reversed(self.agent_metrics):
                if metric.agent_name == agent and metric.status == "in_progress":
                    metric.errors.append(error_message)
                    break
    
    def update_token_usage(self, tokens: int, phase: Optional[str] = None) -> None:
        """Update token usage metrics"""
        self.current_workflow.total_token_usage += tokens
        
        if phase and phase in self.phase_metrics:
            self.phase_metrics[phase].token_usage += tokens
    
    def complete_workflow(self, success: bool = True, reason: str = "") -> None:
        """Mark the workflow as completed"""
        if not self.current_workflow:
            return
        
        self.current_workflow.end_time = datetime.now()
        self.current_workflow.total_duration = (
            self.current_workflow.end_time - self.current_workflow.start_time
        ).total_seconds()
        self.current_workflow.success = success
        self.current_workflow.completion_reason = reason
        
        self.logger.info(f"Workflow completed: {success} - {reason}")
        self._generate_summary_report()
        self._save_metrics()
    
    def _check_thresholds(self, phase: PhaseMetrics) -> None:
        """Check if phase metrics exceed thresholds"""
        if phase.duration and phase.duration > self.thresholds["max_phase_duration"]:
            self.logger.warning(f"Phase {phase.phase_id} exceeded duration threshold: {phase.duration}s")
        
        if phase.token_usage > self.thresholds["max_token_usage"]:
            self.logger.warning(f"Phase {phase.phase_id} exceeded token threshold: {phase.token_usage}")
    
    def _save_metrics(self) -> None:
        """Save current metrics to storage"""
        if not self.current_workflow:
            return
        
        metrics_data = {
            "workflow": asdict(self.current_workflow),
            "phases": {k: asdict(v) for k, v in self.phase_metrics.items()},
            "agents": [asdict(agent) for agent in self.agent_metrics],
            "timestamp": datetime.now().isoformat()
        }
        
        # Convert datetime objects to ISO strings for JSON serialization
        def convert_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return obj
        
        metrics_file = self.metrics_storage / f"workflow_{self.current_workflow.workflow_id}.json"
        with open(metrics_file, 'w') as f:
            json.dump(metrics_data, f, default=convert_datetime, indent=2)
    
    def _generate_summary_report(self) -> None:
        """Generate a summary report of the workflow execution"""
        if not self.current_workflow:
            return
        
        report = {
            "workflow_summary": {
                "id": self.current_workflow.workflow_id,
                "duration": self.current_workflow.total_duration,
                "success": self.current_workflow.success,
                "phases_completed": self.current_workflow.phases_completed,
                "phases_failed": self.current_workflow.phases_failed,
                "total_token_usage": self.current_workflow.total_token_usage
            },
            "phase_summary": {},
            "agent_summary": {},
            "performance_analysis": self._analyze_performance(),
            "recommendations": self._generate_recommendations()
        }
        
        # Phase summary
        for phase_id, phase in self.phase_metrics.items():
            report["phase_summary"][phase_id] = {
                "duration": phase.duration,
                "status": phase.status,
                "agent_count": phase.agent_count,
                "token_usage": phase.token_usage,
                "errors": len(phase.errors)
            }
        
        # Agent summary
        agent_stats = {}
        for agent in self.agent_metrics:
            if agent.agent_name not in agent_stats:
                agent_stats[agent.agent_name] = {
                    "executions": 0,
                    "total_duration": 0,
                    "success_rate": 0,
                    "avg_output_size": 0
                }
            
            stats = agent_stats[agent.agent_name]
            stats["executions"] += 1
            if agent.duration:
                stats["total_duration"] += agent.duration
            if agent.validation_passed:
                stats["success_rate"] += 1
            stats["avg_output_size"] += agent.output_size
        
        # Calculate averages
        for agent_name, stats in agent_stats.items():
            if stats["executions"] > 0:
                stats["success_rate"] = stats["success_rate"] / stats["executions"]
                stats["avg_output_size"] = stats["avg_output_size"] / stats["executions"]
        
        report["agent_summary"] = agent_stats
        
        # Save report
        report_file = self.metrics_storage / f"report_{self.current_workflow.workflow_id}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Generated summary report: {report_file}")
    
    def _analyze_performance(self) -> Dict[str, Any]:
        """Analyze workflow performance"""
        analysis = {
            "bottlenecks": [],
            "efficiency_score": 0.0,
            "resource_utilization": {},
            "optimization_opportunities": []
        }
        
        # Find bottleneck phases
        max_duration = 0
        slowest_phase = None
        for phase_id, phase in self.phase_metrics.items():
            if phase.duration and phase.duration > max_duration:
                max_duration = phase.duration
                slowest_phase = phase_id
        
        if slowest_phase:
            analysis["bottlenecks"].append({
                "phase": slowest_phase,
                "duration": max_duration,
                "type": "phase_duration"
            })
        
        # Calculate efficiency score
        if self.current_workflow.total_duration:
            expected_duration = len(self.phase_metrics) * 300  # 5 minutes per phase baseline
            efficiency = min(1.0, expected_duration / self.current_workflow.total_duration)
            analysis["efficiency_score"] = efficiency
        
        return analysis
    
    def _generate_recommendations(self) -> List[str]:
        """Generate optimization recommendations"""
        recommendations = []
        
        # Check for long-running phases
        for phase_id, phase in self.phase_metrics.items():
            if phase.duration and phase.duration > 1200:  # 20 minutes
                recommendations.append(
                    f"Consider breaking down {phase_id} into smaller parallel tasks"
                )
        
        # Check token usage
        if self.current_workflow.total_token_usage > 50000:
            recommendations.append(
                "High token usage detected. Consider implementing context compression"
            )
        
        # Check error rates
        total_errors = sum(len(phase.errors) for phase in self.phase_metrics.values())
        if total_errors > 5:
            recommendations.append(
                "High error rate detected. Review error handling and retry mechanisms"
            )
        
        return recommendations

    def get_real_time_status(self) -> Dict[str, Any]:
        """Get current workflow status for real-time monitoring"""
        if not self.current_workflow:
            return {"status": "no_active_workflow"}
        
        return {
            "workflow_id": self.current_workflow.workflow_id,
            "current_phase": self.current_workflow.current_phase,
            "phases_completed": self.current_workflow.phases_completed,
            "total_duration": (datetime.now() - self.current_workflow.start_time).total_seconds(),
            "active_agents": len([a for a in self.agent_metrics if a.status == "in_progress"]),
            "token_usage": self.current_workflow.total_token_usage,
            "recent_errors": sum(len(phase.errors) for phase in self.phase_metrics.values())
        }

# Example usage and monitoring integration
if __name__ == "__main__":
    monitor = OrchestrationMonitor()
    
    # Example workflow monitoring
    monitor.start_workflow("example-workflow-001")
    monitor.start_phase("phase_0", "Todo Context Integration")
    monitor.start_agent("orchestration-todo-manager", "orchestration", "phase_0", 1200)
    
    # Simulate some processing time
    time.sleep(2)
    
    monitor.complete_agent("orchestration-todo-manager", success=True, output_size=800)
    monitor.complete_phase("phase_0", success=True, evidence_collected=True)
    monitor.complete_workflow(success=True, reason="All phases completed successfully")
    
    print("Monitoring example completed. Check .monitoring/ directory for results.")