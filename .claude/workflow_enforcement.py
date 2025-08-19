#!/usr/bin/env python3
"""
Workflow Enforcement System
Ensures proper orchestration framework usage and prevents Task tool bypass
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path
import agent_logger


class WorkflowEnforcementError(Exception):
    """Raised when workflow enforcement rules are violated"""
    pass


class WorkflowEnforcer:
    """Enforces proper orchestration framework usage and comprehensive logging"""
    
    def __init__(self):
        self.enforcement_dir = Path(".claude/enforcement").resolve()
        self.enforcement_dir.mkdir(parents=True, exist_ok=True)
        self.logger = agent_logger.AgentLogger()
        
        # Load enforcement rules
        self.rules = self._load_enforcement_rules()
        
        # Track current execution context
        self.current_execution = None
        self.agent_count = 0
        self.evidence_requirements = {}
        
    def _load_enforcement_rules(self):
        """Load workflow enforcement rules"""
        rules_file = self.enforcement_dir / "enforcement_rules.json"
        
        default_rules = {
            "multi_agent_execution": {
                "min_agents_for_orchestration": 3,
                "task_tool_forbidden": True,
                "mandatory_logging": True,
                "evidence_validation_required": True
            },
            "agent_success_claims": {
                "evidence_required": True,
                "cross_validation_required": True,
                "observable_validation": True
            },
            "critical_workflows": {
                "authentication_fixes": {
                    "live_test_required": True,
                    "screenshot_evidence": True,
                    "integration_validation": True
                },
                "performance_improvements": {
                    "benchmark_evidence": True,
                    "before_after_comparison": True,
                    "automated_validation": True
                }
            }
        }
        
        if not rules_file.exists():
            with open(rules_file, 'w') as f:
                json.dump(default_rules, f, indent=2)
            return default_rules
        
        with open(rules_file, 'r') as f:
            return json.load(f)
    
    def validate_execution_request(self, request_type, agent_count, agents_list=None):
        """Validate execution request against enforcement rules"""
        timestamp = datetime.now().isoformat()
        
        # Check if multi-agent orchestration is required
        min_agents = self.rules["multi_agent_execution"]["min_agents_for_orchestration"]
        
        if agent_count >= min_agents:
            # Multi-agent execution - enforce orchestration framework
            if request_type == "task_tool":
                violation = {
                    "timestamp": timestamp,
                    "violation_type": "task_tool_bypass",
                    "agent_count": agent_count,
                    "agents": agents_list,
                    "rule_violated": "task_tool_forbidden for 3+ agent workflows"
                }
                
                self._log_violation(violation)
                
                error_msg = (
                    f"WORKFLOW VIOLATION: Task tool usage forbidden for {agent_count} agent execution.\n"
                    f"REQUIRED: Use agent orchestration framework (agent_logger.py) for proper logging.\n"
                    f"Agents attempted: {agents_list}"
                )
                raise WorkflowEnforcementError(error_msg)
            
            # Initialize proper orchestration tracking
            execution_id = f"orchestrated_{timestamp.replace(':', '').replace('-', '').replace('.', '')}"
            self.current_execution = {
                "execution_id": execution_id,
                "started": timestamp,
                "agent_count": agent_count,
                "agents": agents_list or [],
                "orchestration_active": True,
                "logging_active": True
            }
            
            # Log orchestration start
            agent_logger.log_meta_audit_data("orchestration_start", self.current_execution)
            
            return {"status": "approved", "execution_id": execution_id}
        
        return {"status": "approved", "execution_id": None}
    
    def require_evidence(self, agent_name, claim_type, claim_details):
        """Require evidence for agent success claims"""
        if not self.rules["agent_success_claims"]["evidence_required"]:
            return {"status": "evidence_not_required"}
        
        timestamp = datetime.now().isoformat()
        evidence_requirement = {
            "timestamp": timestamp,
            "agent": agent_name,
            "claim_type": claim_type,
            "claim_details": claim_details,
            "evidence_status": "required",
            "validation_pending": True
        }
        
        # Store evidence requirement
        requirement_id = f"{agent_name}_{claim_type}_{timestamp.replace(':', '').replace('-', '').replace('.', '')}"
        self.evidence_requirements[requirement_id] = evidence_requirement
        
        # Log evidence requirement
        agent_logger.log_meta_audit_data("evidence_required", evidence_requirement)
        
        return {
            "status": "evidence_required",
            "requirement_id": requirement_id,
            "evidence_types": self._get_required_evidence_types(claim_type)
        }
    
    def validate_evidence(self, requirement_id, evidence_data):
        """Validate provided evidence against requirements"""
        if requirement_id not in self.evidence_requirements:
            raise WorkflowEnforcementError(f"Unknown evidence requirement: {requirement_id}")
        
        requirement = self.evidence_requirements[requirement_id]
        timestamp = datetime.now().isoformat()
        
        # Validate evidence completeness
        required_types = self._get_required_evidence_types(requirement["claim_type"])
        provided_types = set(evidence_data.keys())
        missing_types = set(required_types) - provided_types
        
        if missing_types:
            validation_result = {
                "timestamp": timestamp,
                "requirement_id": requirement_id,
                "status": "evidence_insufficient",
                "missing_evidence": list(missing_types),
                "provided_evidence": list(provided_types)
            }
            
            agent_logger.log_meta_audit_data("evidence_validation_failed", validation_result)
            return {"status": "insufficient", "missing": list(missing_types)}
        
        # Evidence complete - mark as validated
        requirement["evidence_status"] = "validated"
        requirement["validation_timestamp"] = timestamp
        requirement["evidence_data"] = evidence_data
        requirement["validation_pending"] = False
        
        validation_result = {
            "timestamp": timestamp,
            "requirement_id": requirement_id,
            "status": "evidence_validated",
            "agent": requirement["agent"],
            "claim_type": requirement["claim_type"]
        }
        
        agent_logger.log_meta_audit_data("evidence_validation_success", validation_result)
        return {"status": "validated", "evidence_accepted": True}
    
    def _get_required_evidence_types(self, claim_type):
        """Get required evidence types for different claim types"""
        evidence_mapping = {
            "authentication_fix": ["live_test_results", "screenshot_evidence", "integration_test"],
            "performance_improvement": ["benchmark_results", "before_after_metrics", "automated_test"],
            "api_fix": ["response_validation", "error_log_analysis", "integration_test"],
            "frontend_optimization": ["performance_metrics", "screenshot_evidence", "user_test"],
            "security_enhancement": ["security_scan_results", "penetration_test", "vulnerability_assessment"],
            "database_optimization": ["query_performance", "connection_test", "data_integrity_check"],
            "general_fix": ["test_results", "validation_evidence", "functionality_proof"]
        }
        
        return evidence_mapping.get(claim_type, ["test_results", "validation_evidence"])
    
    def _log_violation(self, violation):
        """Log workflow enforcement violations"""
        violations_log = self.enforcement_dir / "violations.log"
        
        with open(violations_log, 'a') as f:
            f.write(json.dumps(violation, indent=2) + '\n')
        
        print(f"🚨 WORKFLOW VIOLATION: {violation['violation_type']}")
        print(f"   Details: {violation['rule_violated']}")
    
    def check_execution_completeness(self):
        """Check if current execution has proper evidence validation"""
        if not self.current_execution:
            return {"status": "no_active_execution"}
        
        pending_evidence = {k: v for k, v in self.evidence_requirements.items() 
                          if v["validation_pending"]}
        
        if pending_evidence:
            return {
                "status": "incomplete",
                "pending_evidence_count": len(pending_evidence),
                "pending_requirements": list(pending_evidence.keys())
            }
        
        return {"status": "complete", "all_evidence_validated": True}
    
    def generate_enforcement_report(self):
        """Generate comprehensive workflow enforcement report"""
        timestamp = datetime.now().isoformat()
        
        report = {
            "generated": timestamp,
            "current_execution": self.current_execution,
            "evidence_requirements_count": len(self.evidence_requirements),
            "evidence_validated_count": len([r for r in self.evidence_requirements.values() 
                                           if not r["validation_pending"]]),
            "evidence_pending_count": len([r for r in self.evidence_requirements.values() 
                                         if r["validation_pending"]]),
            "enforcement_rules": self.rules
        }
        
        report_file = self.enforcement_dir / f"enforcement_report_{timestamp.replace(':', '').replace('-', '').replace('.', '')}.json"
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        agent_logger.log_meta_audit_data("enforcement_report_generated", report)
        
        return report


# Global enforcer instance
enforcer = WorkflowEnforcer()


def validate_multi_agent_request(agent_count, agents_list=None):
    """Validate multi-agent execution request"""
    return enforcer.validate_execution_request("orchestration", agent_count, agents_list)


def block_task_tool_multi_agent(agent_count, agents_list=None):
    """Block Task tool usage for multi-agent workflows"""
    return enforcer.validate_execution_request("task_tool", agent_count, agents_list)


def require_agent_evidence(agent_name, claim_type, claim_details):
    """Require evidence for agent success claims"""
    return enforcer.require_evidence(agent_name, claim_type, claim_details)


def validate_agent_evidence(requirement_id, evidence_data):
    """Validate agent-provided evidence"""
    return enforcer.validate_evidence(requirement_id, evidence_data)


def check_execution_status():
    """Check current execution completeness"""
    return enforcer.check_execution_completeness()


def generate_enforcement_report():
    """Generate workflow enforcement report"""
    return enforcer.generate_enforcement_report()


if __name__ == "__main__":
    # Test workflow enforcement
    print("Testing Workflow Enforcement System...")
    
    try:
        # This should fail - Task tool blocked for multi-agent
        block_task_tool_multi_agent(5, ["agent1", "agent2", "agent3", "agent4", "agent5"])
        print("❌ Task tool block failed - should have raised exception")
        
    except WorkflowEnforcementError as e:
        print(f"✅ Task tool correctly blocked: {e}")
    
    try:
        # This should work - proper orchestration
        result = validate_multi_agent_request(3, ["agent1", "agent2", "agent3"])
        print(f"✅ Orchestration approved: {result}")
        
        # Test evidence requirement
        evidence_req = require_agent_evidence("test-agent", "authentication_fix", "Fixed login system")
        print(f"✅ Evidence required: {evidence_req}")
        
        # Generate report
        report = generate_enforcement_report()
        print(f"✅ Enforcement report generated")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")