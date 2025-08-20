#!/usr/bin/env python3
"""
Enhanced Orchestration Wrapper
Integrates comprehensive logging with Claude Code Task tool usage
"""
import json
import os
import sys
import inspect
import yaml
from datetime import datetime
from pathlib import Path
import agent_logger
import workflow_enforcement


class OrchestrationWrapper:
    """Wrapper to add comprehensive logging to Task tool executions"""
    
    def __init__(self):
        self.logger = agent_logger.AgentLogger()
        self.enforcer = workflow_enforcement.WorkflowEnforcer()
        
        # Track multi-agent executions
        self.current_execution_context = None
        self.parallel_groups = []
        self.agent_results = {}
        
        # Context package validation and size management
        self.context_package_templates = self._load_context_templates()
        self.size_limits = {
            "markdown_file_max": 8000,
            "context_package_max": 4000,
            "strategic_context_max": 3000,
            "technical_context_max": 4000,
            "frontend_context_max": 3000
        }
        
    def start_multi_agent_execution(self, execution_type, agents_list, description=""):
        """Initialize multi-agent execution with proper logging"""
        timestamp = datetime.now().isoformat()
        
        # Validate execution request
        validation_result = self.enforcer.validate_execution_request(
            "orchestration", len(agents_list), agents_list
        )
        
        if validation_result["status"] != "approved":
            raise Exception(f"Execution validation failed: {validation_result}")
        
        execution_id = validation_result["execution_id"] or f"multi_agent_{timestamp.replace(':', '').replace('-', '').replace('.', '')}"
        
        self.current_execution_context = {
            "execution_id": execution_id,
            "type": execution_type,
            "agents": agents_list,
            "description": description,
            "started": timestamp,
            "phase": "initialization",
            "total_agents": len(agents_list),
            "completed_agents": 0,
            "failed_agents": 0
        }
        
        # Log execution start
        self.logger.log_orchestrator_plan(description, agents_list)
        self.logger.log_meta_audit_data("multi_agent_execution_start", self.current_execution_context)
        
        print(f"🚀 Starting multi-agent execution: {execution_id}")
        print(f"   Type: {execution_type}")
        print(f"   Agents: {len(agents_list)} agents")
        print(f"   Description: {description}")
        
        return execution_id
    
    def log_agent_task_start(self, agent_name, task_description, phase=None):
        """Log when an agent task starts"""
        timestamp = datetime.now().isoformat()
        
        if self.current_execution_context:
            self.current_execution_context["current_agent"] = agent_name
            self.current_execution_context["current_task"] = task_description
            if phase:
                self.current_execution_context["phase"] = phase
        
        # Log agent action start
        self.logger.log_agent_action(
            agent_name, 
            f"task_start: {task_description}",
            input_data={"phase": phase, "execution_context": self.current_execution_context},
            tools_used=["Task"],
            result="task_started"
        )
        
        print(f"🔄 [{agent_name}] Starting: {task_description}")
        if phase:
            print(f"   Phase: {phase}")
    
    def log_agent_task_result(self, agent_name, task_description, result, success=True, evidence=None):
        """Log agent task completion with result"""
        timestamp = datetime.now().isoformat()
        
        # Update execution context
        if self.current_execution_context:
            if success:
                self.current_execution_context["completed_agents"] += 1
            else:
                self.current_execution_context["failed_agents"] += 1
        
        # Store agent result
        self.agent_results[agent_name] = {
            "task": task_description,
            "result": result,
            "success": success,
            "evidence": evidence,
            "timestamp": timestamp
        }
        
        # Check if evidence is required
        claim_type = self._determine_claim_type(task_description)
        if success and claim_type:
            evidence_req = self.enforcer.require_evidence(agent_name, claim_type, task_description)
            
            if evidence_req["status"] == "evidence_required":
                print(f"📋 [{agent_name}] Evidence required for success claim")
                print(f"   Required types: {evidence_req['evidence_types']}")
                
                # If evidence provided, validate it
                if evidence:
                    validation_result = self.enforcer.validate_evidence(
                        evidence_req["requirement_id"], evidence
                    )
                    print(f"   Evidence validation: {validation_result['status']}")
        
        # Log agent action completion
        self.logger.log_agent_action(
            agent_name,
            f"task_complete: {task_description}",
            input_data={"execution_context": self.current_execution_context},
            result=result,
            tools_used=["Task"],
            verification=evidence
        )
        
        status_icon = "✅" if success else "❌"
        print(f"{status_icon} [{agent_name}] Completed: {task_description}")
        if not success:
            print(f"   Error: {result}")
    
    def log_parallel_phase_start(self, phase_name, agents_list):
        """Log start of parallel phase execution"""
        timestamp = datetime.now().isoformat()
        
        if self.current_execution_context:
            self.current_execution_context["phase"] = phase_name
            self.current_execution_context["parallel_active"] = True
        
        group_id = self.logger.log_parallel_execution(phase_name, agents_list)
        self.parallel_groups.append(group_id)
        
        print(f"⚡ Starting parallel phase: {phase_name}")
        print(f"   Agents executing simultaneously: {', '.join(agents_list)}")
        
        return group_id
    
    def log_parallel_phase_complete(self, group_id, phase_results):
        """Log completion of parallel phase"""
        if group_id in self.parallel_groups:
            self.logger.log_parallel_completion(group_id, phase_results)
            
            # Update execution context
            if self.current_execution_context:
                self.current_execution_context["parallel_active"] = False
            
            print(f"⚡ Parallel phase completed: {group_id}")
            
            # Log results summary
            successful = sum(1 for r in phase_results.values() if r.get("success", False))
            total = len(phase_results)
            print(f"   Results: {successful}/{total} agents successful")
    
    def log_synthesis_requirement(self, requesting_agent, synthesis_type, context_data):
        """Log when synthesis is required"""
        self.logger.log_synthesis_requirement(requesting_agent, True, synthesis_type)
        
        print(f"🧠 Synthesis required by {requesting_agent}: {synthesis_type}")
    
    def log_quality_checkpoint(self, checkpoint_name, agent_name, passed, evidence=None):
        """Log quality gate checkpoint"""
        checkpoint = self.logger.log_quality_checkpoint(checkpoint_name, agent_name, passed, evidence)
        
        status_icon = "✅" if passed else "❌"
        print(f"{status_icon} Quality gate: {checkpoint_name} ({agent_name})")
        
        return checkpoint
    
    def complete_execution(self):
        """Complete multi-agent execution with comprehensive summary"""
        if not self.current_execution_context:
            print("⚠️ No active execution to complete")
            return None
        
        timestamp = datetime.now().isoformat()
        
        # Check evidence completeness
        evidence_status = self.enforcer.check_execution_completeness()
        
        # Update execution context
        self.current_execution_context.update({
            "completed": timestamp,
            "final_phase": "completed",
            "evidence_status": evidence_status,
            "total_agent_results": len(self.agent_results),
            "success_rate": self.current_execution_context["completed_agents"] / self.current_execution_context["total_agents"] if self.current_execution_context["total_agents"] > 0 else 0
        })
        
        # Generate comprehensive logs
        execution_summary = self.logger.generate_execution_summary()
        enforcement_report = self.enforcer.generate_enforcement_report()
        
        # Create final execution report
        final_report = {
            "execution_context": self.current_execution_context,
            "agent_results": self.agent_results,
            "parallel_groups": self.parallel_groups,
            "execution_summary": execution_summary,
            "enforcement_report": enforcement_report,
            "evidence_status": evidence_status
        }
        
        # Save final report
        report_file = Path(f".claude/logs/execution_report_{self.current_execution_context['execution_id']}.json")
        with open(report_file, 'w') as f:
            json.dump(final_report, f, indent=2)
        
        # Log completion
        self.logger.log_meta_audit_data("multi_agent_execution_complete", final_report)
        
        print(f"\n🎉 Multi-agent execution completed: {self.current_execution_context['execution_id']}")
        print(f"   Total agents: {self.current_execution_context['total_agents']}")
        print(f"   Successful: {self.current_execution_context['completed_agents']}")
        print(f"   Failed: {self.current_execution_context['failed_agents']}")
        print(f"   Success rate: {final_report['execution_context']['success_rate']:.1%}")
        print(f"   Evidence status: {evidence_status['status']}")
        print(f"   Full report: {report_file}")
        
        # Reset context for next execution
        self.current_execution_context = None
        self.parallel_groups = []
        self.agent_results = {}
        
        return final_report
    
    def _determine_claim_type(self, task_description):
        """Determine claim type from task description for evidence requirements"""
        task_lower = task_description.lower()
        
        if any(word in task_lower for word in ["auth", "login", "token", "session"]):
            return "authentication_fix"
        elif any(word in task_lower for word in ["performance", "speed", "optimize", "faster"]):
            return "performance_improvement"  
        elif any(word in task_lower for word in ["api", "endpoint", "request", "response"]):
            return "api_fix"
        elif any(word in task_lower for word in ["frontend", "ui", "css", "html", "javascript"]):
            return "frontend_optimization"
        elif any(word in task_lower for word in ["security", "vulnerability", "encrypt", "secure"]):
            return "security_enhancement"
        elif any(word in task_lower for word in ["database", "query", "schema", "migration"]):
            return "database_optimization"
        else:
            return "general_fix"
    
    def _load_context_templates(self):
        """Load context package templates from configuration file"""
        try:
            template_file = Path(".claude/context-package-templates.yaml")
            if template_file.exists():
                with open(template_file, 'r') as f:
                    return yaml.safe_load(f)
            else:
                print("⚠️ Context package templates not found, using defaults")
                return {}
        except Exception as e:
            print(f"⚠️ Error loading context package templates: {e}")
            return {}
    
    def validate_context_package(self, package_content, agent_type):
        """Validate context package size and content for specific agent type"""
        # Estimate token count (rough approximation: 1 token ≈ 4 characters)
        estimated_tokens = len(package_content) // 4
        
        # Get appropriate size limit for agent type
        if agent_type == "project-orchestrator":
            max_tokens = self.size_limits["strategic_context_max"]
        elif agent_type in ["backend-gateway-expert", "schema-database-expert", "python-refactoring-architect"]:
            max_tokens = self.size_limits["technical_context_max"]
        elif agent_type in ["webui-architect", "frictionless-ux-architect", "ui-regression-debugger"]:
            max_tokens = self.size_limits["frontend_context_max"]
        else:
            max_tokens = self.size_limits["context_package_max"]
        
        validation_result = {
            "agent_type": agent_type,
            "estimated_tokens": estimated_tokens,
            "max_allowed_tokens": max_tokens,
            "valid": estimated_tokens <= max_tokens,
            "size_ratio": estimated_tokens / max_tokens
        }
        
        if not validation_result["valid"]:
            print(f"❌ Context package validation FAILED for {agent_type}")
            print(f"   Estimated tokens: {estimated_tokens} (limit: {max_tokens})")
            print(f"   Size ratio: {validation_result['size_ratio']:.1%}")
        else:
            print(f"✅ Context package validated for {agent_type}")
            print(f"   Tokens: {estimated_tokens}/{max_tokens} ({validation_result['size_ratio']:.1%})")
        
        return validation_result
    
    def check_markdown_file_size(self, file_path):
        """Check if markdown file exceeds size limits and trigger documentation-specialist"""
        try:
            if not os.path.exists(file_path):
                return {"status": "file_not_found", "action": "none"}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Estimate token count
            estimated_tokens = len(content) // 4
            max_tokens = self.size_limits["markdown_file_max"]
            
            if estimated_tokens > max_tokens:
                size_violation = {
                    "file_path": file_path,
                    "estimated_tokens": estimated_tokens,
                    "max_allowed_tokens": max_tokens,
                    "size_ratio": estimated_tokens / max_tokens,
                    "action": "size_reduction_required"
                }
                
                print(f"🚨 SIZE LIMIT VIOLATION DETECTED: {file_path}")
                print(f"   Estimated tokens: {estimated_tokens} (limit: {max_tokens})")
                print(f"   Size ratio: {size_violation['size_ratio']:.1%}")
                print(f"   ACTION REQUIRED: Trigger documentation-specialist for size reduction")
                
                # Log the size violation
                self.logger.log_meta_audit_data("markdown_size_violation", size_violation)
                
                return size_violation
            else:
                return {
                    "status": "size_ok",
                    "estimated_tokens": estimated_tokens,
                    "max_allowed_tokens": max_tokens,
                    "action": "none"
                }
                
        except Exception as e:
            print(f"⚠️ Error checking file size for {file_path}: {e}")
            return {"status": "check_error", "error": str(e), "action": "manual_review"}
    
    def log_context_synthesis_phase(self, synthesis_agent, context_packages):
        """Log the context synthesis phase and validate packages"""
        timestamp = datetime.now().isoformat()
        
        print(f"🧠 Context Synthesis Phase initiated by {synthesis_agent}")
        print(f"   Timestamp: {timestamp}")
        print(f"   Context packages created: {len(context_packages)}")
        
        # Validate each context package
        validation_results = []
        for package in context_packages:
            agent_type = package.get("target_agent", "unknown")
            content = package.get("content", "")
            
            validation = self.validate_context_package(content, agent_type)
            validation_results.append(validation)
            
            # Store validation in package
            package["validation_result"] = validation
        
        # Log synthesis phase
        synthesis_data = {
            "synthesis_agent": synthesis_agent,
            "timestamp": timestamp,
            "packages_created": len(context_packages),
            "validation_results": validation_results,
            "all_packages_valid": all(v["valid"] for v in validation_results)
        }
        
        if self.current_execution_context:
            self.current_execution_context["context_synthesis"] = synthesis_data
        
        self.logger.log_meta_audit_data("context_synthesis_phase", synthesis_data)
        
        # Report validation summary
        valid_packages = sum(1 for v in validation_results if v["valid"])
        total_packages = len(validation_results)
        print(f"📊 Context Package Validation Summary: {valid_packages}/{total_packages} valid")
        
        return synthesis_data


# Global orchestration wrapper
orchestration = OrchestrationWrapper()


# Convenience functions for easy usage
def start_orchestrated_execution(execution_type, agents_list, description=""):
    """Start orchestrated multi-agent execution"""
    return orchestration.start_multi_agent_execution(execution_type, agents_list, description)


def log_task_start(agent_name, task_description, phase=None):
    """Log agent task start"""
    return orchestration.log_agent_task_start(agent_name, task_description, phase)


def log_task_result(agent_name, task_description, result, success=True, evidence=None):
    """Log agent task result"""
    return orchestration.log_agent_task_result(agent_name, task_description, result, success, evidence)


def start_parallel_phase(phase_name, agents_list):
    """Start parallel phase execution"""
    return orchestration.log_parallel_phase_start(phase_name, agents_list)


def complete_parallel_phase(group_id, phase_results):
    """Complete parallel phase execution"""
    return orchestration.log_parallel_phase_complete(group_id, phase_results)


def complete_orchestrated_execution():
    """Complete orchestrated execution"""
    return orchestration.complete_execution()


# Context package validation functions
def validate_context_package(package_content, agent_type):
    """Validate context package for specific agent type"""
    return orchestration.validate_context_package(package_content, agent_type)


def check_markdown_size(file_path):
    """Check markdown file size and trigger documentation-specialist if needed"""
    return orchestration.check_markdown_file_size(file_path)


def log_context_synthesis(synthesis_agent, context_packages):
    """Log context synthesis phase with validation"""
    return orchestration.log_context_synthesis_phase(synthesis_agent, context_packages)


if __name__ == "__main__":
    # Test orchestration wrapper
    print("Testing Enhanced Orchestration Wrapper...")
    
    # Simulate multi-agent execution
    execution_id = start_orchestrated_execution(
        "Enhanced Parallel Agent Framework",
        ["agent1", "agent2", "agent3"],
        "Test multi-agent coordination"
    )
    
    # Simulate agent tasks
    log_task_start("agent1", "Analyzing codebase", "discovery")
    log_task_result("agent1", "Analyzing codebase", "Analysis complete", success=True, evidence={"test_results": "passed"})
    
    # Simulate parallel phase
    group_id = start_parallel_phase("implementation", ["agent2", "agent3"])
    
    log_task_start("agent2", "Implementing authentication fix", "implementation")
    log_task_result("agent2", "Implementing authentication fix", "Auth fix implemented", success=True)
    
    log_task_start("agent3", "Optimizing performance", "implementation")  
    log_task_result("agent3", "Optimizing performance", "Performance optimized", success=True)
    
    complete_parallel_phase(group_id, {
        "agent2": {"success": True, "summary": "Auth fix completed"},
        "agent3": {"success": True, "summary": "Performance optimized"}
    })
    
    # Complete execution
    final_report = complete_orchestrated_execution()
    
    print("✅ Orchestration wrapper test completed")