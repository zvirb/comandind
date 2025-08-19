#!/usr/bin/env python3
"""
Predictive Failure Detection System
Predicts and prevents failures before execution using historical patterns and resource analysis
"""
import json
import os
import psutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
import hashlib
import subprocess


@dataclass
class Risk:
    """Risk assessment for task execution"""
    type: str
    probability: float  # 0.0 to 1.0
    severity: int  # 1-10
    description: str
    mitigation: str
    evidence: Dict = None


@dataclass
class ValidationResult:
    """Result of pre-execution validation"""
    safe_to_execute: bool
    risks: List[Risk]
    recommendations: List[str]
    estimated_success_probability: float
    resource_requirements: Dict[str, Union[int, float]]


class PredictiveValidator:
    """Predict and prevent failures before execution"""
    
    def __init__(self):
        self.failure_history_file = Path(".claude/logs/failure_history.json").resolve()
        self.resource_baseline_file = Path(".claude/logs/resource_baseline.json").resolve()
        self.dependency_map_file = Path(".claude/logs/dependency_map.json").resolve()
        
        self.failure_patterns = self._load_failure_patterns()
        self.resource_baselines = self._load_resource_baselines()
        self.dependency_conflicts = self._load_dependency_conflicts()
        
        # Initialize baseline if not exists
        if not self.resource_baseline_file.exists():
            self._establish_resource_baseline()
    
    def _load_failure_patterns(self) -> Dict:
        """Load historical failure patterns"""
        if self.failure_history_file.exists():
            try:
                with open(self.failure_history_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load failure history: {e}")
        
        return {
            "agent_failures": {},
            "task_patterns": {},
            "resource_failures": {},
            "dependency_failures": {},
            "time_patterns": {}
        }
    
    def _load_resource_baselines(self) -> Dict:
        """Load resource usage baselines"""
        if self.resource_baseline_file.exists():
            try:
                with open(self.resource_baseline_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load resource baselines: {e}")
        
        return {
            "cpu_baseline": 20.0,  # percentage
            "memory_baseline": 1024,  # MB
            "disk_baseline": 1024,  # MB
            "network_baseline": 100  # Mbps
        }
    
    def _load_dependency_conflicts(self) -> Dict:
        """Load known dependency conflicts"""
        if self.dependency_map_file.exists():
            try:
                with open(self.dependency_map_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        return {
            "conflicts": {},
            "version_issues": {},
            "missing_dependencies": []
        }
    
    def _establish_resource_baseline(self):
        """Establish baseline resource usage"""
        print("🔍 Establishing resource baseline...")
        
        # Collect samples over 30 seconds
        samples = []
        for _ in range(10):
            sample = {
                "cpu": psutil.cpu_percent(interval=1),
                "memory": psutil.virtual_memory().percent,
                "disk_io": sum([d.read_bytes + d.write_bytes for d in psutil.disk_io_counters(perdisk=True).values()]),
                "network_io": sum([n.bytes_sent + n.bytes_recv for n in psutil.net_io_counters(pernic=True).values()])
            }
            samples.append(sample)
            time.sleep(3)
        
        # Calculate averages
        baseline = {
            "cpu_baseline": sum(s["cpu"] for s in samples) / len(samples),
            "memory_baseline": sum(s["memory"] for s in samples) / len(samples),
            "disk_io_baseline": sum(s["disk_io"] for s in samples) / len(samples),
            "network_io_baseline": sum(s["network_io"] for s in samples) / len(samples),
            "established": datetime.now().isoformat()
        }
        
        with open(self.resource_baseline_file, 'w') as f:
            json.dump(baseline, f, indent=2)
        
        self.resource_baselines = baseline
        print(f"✅ Resource baseline established: CPU {baseline['cpu_baseline']:.1f}%, Memory {baseline['memory_baseline']:.1f}%")
    
    def validate_before_execution(self, agent: str, task: Dict, context: Dict = None) -> ValidationResult:
        """Comprehensive pre-execution validation"""
        risks = []
        recommendations = []
        
        # 1. Check historical failure patterns
        historical_risks = self._check_historical_failures(agent, task)
        risks.extend(historical_risks)
        
        # 2. Check resource availability
        resource_risks = self._check_resource_availability(agent, task)
        risks.extend(resource_risks)
        
        # 3. Check dependency conflicts
        dependency_risks = self._check_dependency_conflicts(task)
        risks.extend(dependency_risks)
        
        # 4. Check system health
        system_risks = self._check_system_health()
        risks.extend(system_risks)
        
        # 5. Check timing patterns
        timing_risks = self._check_timing_patterns(agent, task)
        risks.extend(timing_risks)
        
        # 6. Check concurrent execution conflicts
        concurrency_risks = self._check_concurrency_conflicts(agent, task, context)
        risks.extend(concurrency_risks)
        
        # Calculate overall risk assessment
        high_risks = [r for r in risks if r.probability > 0.7]
        medium_risks = [r for r in risks if 0.3 <= r.probability <= 0.7]
        
        # Determine if safe to execute
        safe_to_execute = len(high_risks) == 0 and len(medium_risks) <= 2
        
        # Calculate success probability
        if not risks:
            success_probability = 0.95
        else:
            # Use inverse of weighted risk score
            weighted_risk = sum(r.probability * r.severity for r in risks) / 10
            success_probability = max(0.1, 1.0 - (weighted_risk / len(risks)))
        
        # Generate recommendations
        if high_risks:
            recommendations.append("⚠️ High-risk execution detected - consider alternative approach")
        if medium_risks:
            recommendations.append("⚡ Medium risks present - monitor execution closely")
        
        for risk in risks:
            if risk.mitigation:
                recommendations.append(f"🔧 {risk.mitigation}")
        
        # Estimate resource requirements
        resource_requirements = self._estimate_resource_requirements(agent, task)
        
        return ValidationResult(
            safe_to_execute=safe_to_execute,
            risks=risks,
            recommendations=recommendations,
            estimated_success_probability=success_probability,
            resource_requirements=resource_requirements
        )
    
    def _check_historical_failures(self, agent: str, task: Dict) -> List[Risk]:
        """Check for historical failure patterns"""
        risks = []
        
        # Create task signature for pattern matching
        task_signature = self._create_task_signature(task)
        
        # Check agent-specific failures
        if agent in self.failure_patterns.get("agent_failures", {}):
            agent_failures = self.failure_patterns["agent_failures"][agent]
            failure_rate = agent_failures.get("failure_rate", 0.0)
            
            if failure_rate > 0.3:
                risks.append(Risk(
                    type="historical_failure",
                    probability=failure_rate,
                    severity=6,
                    description=f"{agent} has {failure_rate:.1%} failure rate",
                    mitigation="Consider using alternative agent or add extra validation",
                    evidence={"recent_failures": agent_failures.get("recent_failures", [])}
                ))
        
        # Check task pattern failures
        if task_signature in self.failure_patterns.get("task_patterns", {}):
            pattern_data = self.failure_patterns["task_patterns"][task_signature]
            if pattern_data["failure_count"] > 2:
                probability = min(0.8, pattern_data["failure_count"] / pattern_data["total_count"])
                risks.append(Risk(
                    type="task_pattern_failure",
                    probability=probability,
                    severity=7,
                    description=f"This task pattern has failed {pattern_data['failure_count']} times",
                    mitigation="Review task parameters or break down into smaller steps",
                    evidence=pattern_data
                ))
        
        return risks
    
    def _check_resource_availability(self, agent: str, task: Dict) -> List[Risk]:
        """Check if sufficient resources are available"""
        risks = []
        
        try:
            # Current system resources
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Compare against baselines
            cpu_baseline = self.resource_baselines.get("cpu_baseline", 20.0)
            memory_baseline = self.resource_baselines.get("memory_baseline", 50.0)
            
            # CPU check
            if cpu_percent > 80:
                risks.append(Risk(
                    type="resource_shortage",
                    probability=0.8,
                    severity=8,
                    description=f"High CPU usage: {cpu_percent:.1f}%",
                    mitigation="Wait for CPU usage to decrease or use less intensive agent",
                    evidence={"current_cpu": cpu_percent, "baseline": cpu_baseline}
                ))
            
            # Memory check
            if memory.percent > 85:
                risks.append(Risk(
                    type="resource_shortage",
                    probability=0.9,
                    severity=9,
                    description=f"High memory usage: {memory.percent:.1f}%",
                    mitigation="Free memory or use memory-efficient alternatives",
                    evidence={"current_memory": memory.percent, "available_gb": memory.available / (1024**3)}
                ))
            
            # Disk space check
            if disk.percent > 90:
                risks.append(Risk(
                    type="resource_shortage",
                    probability=0.95,
                    severity=10,
                    description=f"Low disk space: {100 - disk.percent:.1f}% free",
                    mitigation="Free up disk space before execution",
                    evidence={"disk_usage": disk.percent, "free_gb": disk.free / (1024**3)}
                ))
            
        except Exception as e:
            risks.append(Risk(
                type="resource_check_failed",
                probability=0.3,
                severity=4,
                description=f"Could not check system resources: {e}",
                mitigation="Proceed with caution and monitor system performance"
            ))
        
        return risks
    
    def _check_dependency_conflicts(self, task: Dict) -> List[Risk]:
        """Check for known dependency conflicts"""
        risks = []
        
        # Check for known problematic combinations
        task_tools = task.get("tools_required", [])
        
        # Check if Docker is available when needed
        if "docker" in task_tools or "docker-compose" in task_tools:
            try:
                result = subprocess.run(["docker", "ps"], 
                                     capture_output=True, timeout=5)
                if result.returncode != 0:
                    risks.append(Risk(
                        type="dependency_conflict",
                        probability=0.9,
                        severity=8,
                        description="Docker is required but not accessible",
                        mitigation="Check Docker installation and permissions",
                        evidence={"docker_error": result.stderr.decode() if result.stderr else "Unknown error"}
                    ))
            except (subprocess.TimeoutExpired, FileNotFoundError):
                risks.append(Risk(
                    type="dependency_conflict",
                    probability=0.8,
                    severity=7,
                    description="Docker command not found or not responding",
                    mitigation="Install Docker or check system PATH"
                ))
        
        # Check Node.js dependencies
        if "npm" in task_tools or "node" in task_tools:
            if not Path("package.json").exists():
                risks.append(Risk(
                    type="dependency_conflict",
                    probability=0.6,
                    severity=5,
                    description="Node.js tools required but no package.json found",
                    mitigation="Ensure you're in the correct project directory"
                ))
        
        # Check Python dependencies
        if "python" in task_tools or "pip" in task_tools:
            if not any(Path(f).exists() for f in ["requirements.txt", "pyproject.toml", "setup.py"]):
                risks.append(Risk(
                    type="dependency_conflict",
                    probability=0.4,
                    severity=4,
                    description="Python tools required but no dependency file found",
                    mitigation="Verify Python environment and dependencies"
                ))
        
        return risks
    
    def _check_system_health(self) -> List[Risk]:
        """Check overall system health"""
        risks = []
        
        try:
            # Check load average (Unix systems)
            if hasattr(os, 'getloadavg'):
                load_avg = os.getloadavg()[0]  # 1-minute average
                cpu_count = psutil.cpu_count()
                
                if load_avg > cpu_count * 1.5:
                    risks.append(Risk(
                        type="system_health",
                        probability=0.6,
                        severity=6,
                        description=f"High system load: {load_avg:.2f} (cores: {cpu_count})",
                        mitigation="Wait for system load to decrease"
                    ))
            
            # Check for processes with high resource usage
            high_cpu_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    if proc.info['cpu_percent'] and proc.info['cpu_percent'] > 30:
                        high_cpu_processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if len(high_cpu_processes) > 3:
                risks.append(Risk(
                    type="system_health",
                    probability=0.4,
                    severity=5,
                    description=f"Multiple high-CPU processes detected: {len(high_cpu_processes)}",
                    mitigation="Consider closing unnecessary applications",
                    evidence={"high_cpu_processes": high_cpu_processes[:5]}
                ))
            
        except Exception as e:
            # Non-critical error
            pass
        
        return risks
    
    def _check_timing_patterns(self, agent: str, task: Dict) -> List[Risk]:
        """Check for time-based failure patterns"""
        risks = []
        
        current_hour = datetime.now().hour
        
        # Check if this is typically a high-failure time
        time_patterns = self.failure_patterns.get("time_patterns", {})
        hour_key = f"hour_{current_hour}"
        
        if hour_key in time_patterns:
            hour_data = time_patterns[hour_key]
            if hour_data["failure_rate"] > 0.4:
                risks.append(Risk(
                    type="timing_pattern",
                    probability=hour_data["failure_rate"],
                    severity=4,
                    description=f"Higher failure rate at {current_hour}:00 ({hour_data['failure_rate']:.1%})",
                    mitigation="Consider scheduling for a different time",
                    evidence=hour_data
                ))
        
        return risks
    
    def _check_concurrency_conflicts(self, agent: str, task: Dict, context: Dict = None) -> List[Risk]:
        """Check for conflicts with concurrent executions"""
        risks = []
        
        if not context or "active_agents" not in context:
            return risks
        
        active_agents = context["active_agents"]
        
        # Check for problematic agent combinations
        problematic_combinations = [
            (["ui-regression-debugger", "playwright"], "Browser resource conflict"),
            (["docker", "system"], "Docker resource conflict"),
            (["database", "schema"], "Database lock conflict")
        ]
        
        for conflict_agents, description in problematic_combinations:
            active_conflicts = [a for a in active_agents if any(ca in a.lower() for ca in conflict_agents)]
            if len(active_conflicts) > 1 and any(ca in agent.lower() for ca in conflict_agents):
                risks.append(Risk(
                    type="concurrency_conflict",
                    probability=0.5,
                    severity=6,
                    description=description,
                    mitigation="Wait for conflicting agents to complete or use sequential execution",
                    evidence={"conflicting_agents": active_conflicts}
                ))
        
        return risks
    
    def _create_task_signature(self, task: Dict) -> str:
        """Create a unique signature for task pattern matching"""
        # Create signature based on task characteristics
        signature_data = {
            "action": task.get("action", "unknown"),
            "domain": task.get("domain", "unknown"),
            "tools": sorted(task.get("tools_required", [])),
            "complexity": task.get("complexity", 0)
        }
        
        signature_str = json.dumps(signature_data, sort_keys=True)
        return hashlib.md5(signature_str.encode()).hexdigest()[:12]
    
    def _estimate_resource_requirements(self, agent: str, task: Dict) -> Dict[str, Union[int, float]]:
        """Estimate resource requirements for task execution"""
        # Default requirements
        requirements = {
            "cpu_percent": 10.0,
            "memory_mb": 256,
            "disk_mb": 100,
            "execution_time_minutes": 5.0
        }
        
        # Adjust based on agent type
        agent_multipliers = {
            "ui-regression-debugger": {"cpu_percent": 20.0, "memory_mb": 512},
            "backend-gateway-expert": {"cpu_percent": 15.0, "memory_mb": 384},
            "security-validator": {"cpu_percent": 25.0, "memory_mb": 512},
            "nexus-synthesis-agent": {"cpu_percent": 30.0, "memory_mb": 768}
        }
        
        if agent in agent_multipliers:
            for key, value in agent_multipliers[agent].items():
                requirements[key] = value
        
        # Adjust based on task complexity
        complexity = task.get("complexity", 5)
        complexity_factor = complexity / 5.0
        
        requirements["cpu_percent"] *= complexity_factor
        requirements["memory_mb"] *= complexity_factor
        requirements["execution_time_minutes"] *= complexity_factor
        
        return requirements
    
    def record_execution_outcome(self, agent: str, task: Dict, success: bool, 
                               duration: float, error: str = None):
        """Record execution outcome for future predictions"""
        task_signature = self._create_task_signature(task)
        current_hour = datetime.now().hour
        timestamp = datetime.now().isoformat()
        
        # Update agent failures
        if agent not in self.failure_patterns["agent_failures"]:
            self.failure_patterns["agent_failures"][agent] = {
                "total_executions": 0,
                "failed_executions": 0,
                "recent_failures": []
            }
        
        agent_data = self.failure_patterns["agent_failures"][agent]
        agent_data["total_executions"] += 1
        
        if not success:
            agent_data["failed_executions"] += 1
            agent_data["recent_failures"].append({
                "timestamp": timestamp,
                "error": error,
                "task_signature": task_signature
            })
            # Keep only last 20 failures
            agent_data["recent_failures"] = agent_data["recent_failures"][-20:]
        
        agent_data["failure_rate"] = agent_data["failed_executions"] / agent_data["total_executions"]
        
        # Update task patterns
        if task_signature not in self.failure_patterns["task_patterns"]:
            self.failure_patterns["task_patterns"][task_signature] = {
                "total_count": 0,
                "failure_count": 0,
                "avg_duration": 0.0
            }
        
        pattern_data = self.failure_patterns["task_patterns"][task_signature]
        pattern_data["total_count"] += 1
        
        if not success:
            pattern_data["failure_count"] += 1
        
        # Update average duration
        pattern_data["avg_duration"] = (pattern_data["avg_duration"] * (pattern_data["total_count"] - 1) + duration) / pattern_data["total_count"]
        
        # Update time patterns
        hour_key = f"hour_{current_hour}"
        if hour_key not in self.failure_patterns["time_patterns"]:
            self.failure_patterns["time_patterns"][hour_key] = {
                "total_executions": 0,
                "failed_executions": 0
            }
        
        time_data = self.failure_patterns["time_patterns"][hour_key]
        time_data["total_executions"] += 1
        
        if not success:
            time_data["failed_executions"] += 1
        
        time_data["failure_rate"] = time_data["failed_executions"] / time_data["total_executions"]
        
        # Save updated patterns
        self._save_failure_patterns()
    
    def _save_failure_patterns(self):
        """Save failure patterns to disk"""
        self.failure_history_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.failure_history_file, 'w') as f:
            json.dump(self.failure_patterns, f, indent=2)


# Global validator instance
validator = PredictiveValidator()

def validate_execution(agent: str, task: Dict, context: Dict = None) -> ValidationResult:
    """Convenience function for pre-execution validation"""
    return validator.validate_before_execution(agent, task, context)

def record_outcome(agent: str, task: Dict, success: bool, duration: float, error: str = None):
    """Convenience function for recording execution outcomes"""
    return validator.record_execution_outcome(agent, task, success, duration, error)


if __name__ == "__main__":
    # Test the predictive validator
    print("Testing Predictive Failure Detection...")
    
    test_task = {
        "action": "ui_testing",
        "domain": "frontend",
        "tools_required": ["playwright", "read"],
        "complexity": 6
    }
    
    result = validate_execution("ui-regression-debugger", test_task)
    
    print(f"\n🔍 Validation Result:")
    print(f"  Safe to execute: {'✅' if result.safe_to_execute else '❌'}")
    print(f"  Success probability: {result.estimated_success_probability:.1%}")
    print(f"  Risks detected: {len(result.risks)}")
    
    for risk in result.risks:
        print(f"    ⚠️ {risk.type}: {risk.description} ({risk.probability:.1%})")
    
    if result.recommendations:
        print(f"  Recommendations:")
        for rec in result.recommendations:
            print(f"    {rec}")