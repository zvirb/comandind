# advanced_orchestration_tools.py
"""
Advanced orchestration tools with Neo4j knowledge graph and mem0 memory integration
Integrated with existing enhanced orchestration workflow
"""

import json
import subprocess
import atexit
from datetime import datetime
from pathlib import Path
import os
import sys

# Import existing orchestration tools
try:
    from orchestration_tools import (
        OrchestrationKnowledgeClient, 
        OrchestrationCheckpointManager, 
        DocumentCompressionAgent
    )
except ImportError:
    print("Warning: Basic orchestration tools not available. Using minimal implementations.")
    class OrchestrationKnowledgeClient:
        def query_knowledge(self, entity): 
            return {"status": "fallback", "entity": entity, "data": {}}
    class OrchestrationCheckpointManager:
        def create_checkpoint(self, phase, state, workflow_id=None): 
            return f"fallback_{phase}"
    class DocumentCompressionAgent:
        def compress_document(self, content, target_tokens=8000, strategy="technical_compress"):
            return {"status": "no_compression_needed", "compressed_content": content}

# --- Orchestration Knowledge Graph Integration ---
def search_knowledge_graph_for_patterns(error_name: str) -> str:
    """
    Searches our orchestration knowledge graph server for historically successful solutions.
    Uses the MCP server we built earlier.
    """
    print(f"--- TOOL: Searching orchestration KG for successful patterns for '{error_name}' ---")
    
    try:
        # Use our existing orchestration knowledge client
        if kg_client:
            response = kg_client.query_knowledge(error_name)
            
            if response.get("status") == "success":
                data = response.get("data", {})
                
                # Convert our knowledge graph format to success patterns format
                patterns = []
                if "solutions" in data:
                    for i, solution in enumerate(data["solutions"]):
                        patterns.append({
                            "solution": solution,
                            "success_count": 10 - i,  # Higher priority for earlier solutions
                            "pattern_type": data.get("type", "Unknown"),
                            "source": "orchestration_knowledge_graph"
                        })
                
                if patterns:
                    print(f"✅ Found {len(patterns)} patterns from orchestration KG")
                    return json.dumps(patterns)
            
            elif response.get("status") == "partial_match":
                # Handle partial matches from our knowledge graph
                patterns = []
                for match in response.get("matches", []):
                    match_data = match.get("data", {})
                    if "solutions" in match_data:
                        for i, solution in enumerate(match_data["solutions"]):
                            patterns.append({
                                "solution": solution,
                                "success_count": 8 - i,  # Slightly lower for partial matches
                                "pattern_type": match_data.get("type", "Unknown"),
                                "source": "orchestration_knowledge_graph_partial"
                            })
                
                if patterns:
                    print(f"✅ Found {len(patterns)} partial match patterns")
                    return json.dumps(patterns[:5])  # Limit to top 5
    
    except Exception as e:
        print(f"Orchestration KG unavailable: {str(e)}")
    
    # Enhanced fallback patterns based on our orchestration experience
    enhanced_patterns = {
        "authentication_failure": [
            {"solution": "Implement database SSL configuration fix with URL encoding", "success_count": 12, "learned_from": "phase_3_execution"},
            {"solution": "Add three-tier authentication fallback (enhanced->simple->sync)", "success_count": 10, "learned_from": "phase_3_execution"},
            {"solution": "Fix user status creation in registration (active vs pending_approval)", "success_count": 8, "learned_from": "phase_5_iteration"}
        ],
        "orchestration_failure": [
            {"solution": "Implement mandatory parallel execution with checkpoint validation", "success_count": 15, "learned_from": "orchestration_audit"},
            {"solution": "Limit specialist scope (max 10 files, 1000 lines per session)", "success_count": 13, "learned_from": "orchestration_audit"},
            {"solution": "Add truth-based validation with external testing", "success_count": 11, "learned_from": "orchestration_audit"}
        ],
        "csrf_validation_error": [
            {"solution": "Standardize user status creation between endpoints", "success_count": 9, "learned_from": "phase_5_iteration"},
            {"solution": "Review CSRF middleware exemption configuration", "success_count": 7, "learned_from": "phase_4_validation"},
            {"solution": "Check middleware execution order for authentication flow", "success_count": 5, "learned_from": "phase_4_validation"}
        ],
        "database_ssl_error": [
            {"solution": "Fix async URL conversion with special character encoding", "success_count": 14, "learned_from": "phase_3_execution"},
            {"solution": "Handle IPv6 URL parsing edge cases in database passwords", "success_count": 12, "learned_from": "phase_3_execution"},
            {"solution": "Implement sync fallback for async session creation failures", "success_count": 10, "learned_from": "phase_3_execution"}
        ],
        "false_success_reporting": [
            {"solution": "Require end-to-end UI testing for success validation", "success_count": 18, "learned_from": "orchestration_audit"},
            {"solution": "Implement system health monitoring with auto-rollback", "success_count": 16, "learned_from": "orchestration_audit"},
            {"solution": "Add integration testing between specialist changes", "success_count": 14, "learned_from": "orchestration_audit"}
        ]
    }
    
    # Try direct match first
    patterns = enhanced_patterns.get(error_name, [])
    if patterns:
        print(f"✅ Found {len(patterns)} enhanced fallback patterns")
        return json.dumps(patterns)
    
    # Pattern matching fallback
    matching_patterns = []
    for key, value in enhanced_patterns.items():
        if error_name.lower() in key.lower() or any(error_name.lower() in sol["solution"].lower() for sol in value):
            matching_patterns.extend(value)
    
    if matching_patterns:
        # Sort by success count and deduplicate
        unique_patterns = {p["solution"]: p for p in matching_patterns}.values()
        sorted_patterns = sorted(unique_patterns, key=lambda x: x["success_count"], reverse=True)[:5]
        print(f"✅ Found {len(sorted_patterns)} matching enhanced patterns")
        return json.dumps(sorted_patterns)
    
    return "[]"

def check_memory_for_past_failures(pattern_description: str) -> str:
    """
    Checks mem0 memory for past failures of specific solutions.
    Falls back to local failure tracking if mem0 unavailable.
    """
    print(f"--- TOOL: Checking mem0 for past failures of '{pattern_description}' ---")
    
    # Local failure tracking as fallback
    local_failures = {
        "complex SSL parameter conversion": {
            "failed_attempts": 3,
            "last_failure": "2025-01-07",
            "reason": "Created malformed sslmode parameters causing AsyncPG errors"
        },
        "disable CSRF protection": {
            "failed_attempts": 5,
            "last_failure": "2025-01-06",
            "reason": "Security vulnerability - always maintain CSRF protection"
        },
        "massive file modifications": {
            "failed_attempts": 2,
            "last_failure": "2025-01-07",
            "reason": "Specialist scope explosion - backend agent modified 292,900 lines"
        },
        "unit test success without integration": {
            "failed_attempts": 4,
            "last_failure": "2025-01-07",
            "reason": "False success reporting - tests pass but actual functionality breaks"
        }
    }
    
    try:
        # Try mem0 integration (if available)
        from mem0 import Memory
        
        memory = Memory()
        search_query = f'"{pattern_description}" AND "failed"'
        relevant_memories = memory.search(search_query, limit=3)
        
        if relevant_memories:
            print(f"✅ Found {len(relevant_memories)} failure memories from mem0")
            return json.dumps(relevant_memories)
            
    except Exception as e:
        print(f"mem0 unavailable, using local failure tracking: {str(e)}")
    
    # Fallback to local failure patterns
    matching_failures = []
    for failure_pattern, failure_data in local_failures.items():
        if failure_pattern.lower() in pattern_description.lower() or pattern_description.lower() in failure_pattern.lower():
            matching_failures.append({
                "pattern": failure_pattern,
                "data": failure_data,
                "relevance_score": 0.8
            })
    
    if matching_failures:
        print(f"✅ Found {len(matching_failures)} local failure patterns")
        return json.dumps(matching_failures)
    
    return "[]"

def record_orchestration_outcome(pattern_description: str, success: bool, details: str) -> str:
    """
    Records the outcome of an orchestration attempt for future learning.
    """
    print(f"--- TOOL: Recording orchestration outcome: {pattern_description} -> {'SUCCESS' if success else 'FAILURE'} ---")
    
    outcome_data = {
        "pattern": pattern_description,
        "success": success,
        "details": details,
        "timestamp": datetime.now().isoformat(),
        "workflow_context": "enhanced_orchestration"
    }
    
    try:
        # Try mem0 integration for failure recording
        if not success:
            from mem0 import Memory
            memory = Memory()
            failure_memory = f"Pattern '{pattern_description}' failed: {details}"
            memory.add(failure_memory)
            print("✅ Failure recorded in mem0")
            
    except Exception as e:
        print(f"mem0 recording failed, using local storage: {str(e)}")
    
    # Always record locally as backup
    outcomes_dir = Path("orchestration_outcomes")
    outcomes_dir.mkdir(exist_ok=True)
    
    outcome_file = outcomes_dir / f"outcome_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(outcome_file, 'w') as f:
        json.dump(outcome_data, f, indent=2)
    
    return f"Outcome recorded: {pattern_description} -> {'SUCCESS' if success else 'FAILURE'}"

def get_agent_coordination_strategy(agents_status: dict, error_context: str) -> str:
    """
    Generate coordination strategy for parallel agent execution based on current status and error context.
    """
    print(f"--- TOOL: Generating coordination strategy for {len(agents_status)} agents ---")
    
    coordination_patterns = {
        "authentication_error": {
            "primary_agents": ["security-validator", "backend-gateway-expert"],
            "secondary_agents": ["schema-database-expert", "webui-architect"],
            "execution_order": "parallel_with_dependencies",
            "critical_checkpoints": ["database_connectivity", "auth_middleware_config"]
        },
        "database_error": {
            "primary_agents": ["schema-database-expert", "backend-gateway-expert"],
            "secondary_agents": ["security-validator"],
            "execution_order": "sequential_then_parallel",
            "critical_checkpoints": ["connection_validation", "ssl_configuration"]
        },
        "orchestration_failure": {
            "primary_agents": ["orchestration-auditor"],
            "secondary_agents": ["all_specialists"],
            "execution_order": "audit_first_then_constrained_parallel",
            "critical_checkpoints": ["scope_validation", "integration_testing"]
        }
    }
    
    # Determine error type
    error_type = "general_error"
    for pattern_key in coordination_patterns.keys():
        if pattern_key.replace("_", " ") in error_context.lower():
            error_type = pattern_key
            break
    
    strategy = coordination_patterns.get(error_type, {
        "primary_agents": list(agents_status.keys()),
        "secondary_agents": [],
        "execution_order": "parallel",
        "critical_checkpoints": ["basic_validation"]
    })
    
    # Customize based on agent status
    available_agents = [agent for agent, status in agents_status.items() if "ready" in status.lower() or "available" in status.lower()]
    strategy["available_agents"] = available_agents
    strategy["coordination_timestamp"] = datetime.now().isoformat()
    
    return json.dumps(strategy)

def validate_specialist_scope(agent_name: str, proposed_actions: list) -> str:
    """
    Validate that specialist actions don't exceed reasonable scope to prevent explosion.
    """
    print(f"--- TOOL: Validating scope for {agent_name} with {len(proposed_actions)} actions ---")
    
    # Scope limits based on orchestration audit learnings
    scope_limits = {
        "backend-gateway-expert": {
            "max_files_modified": 10,
            "max_lines_changed": 1000,
            "forbidden_actions": ["complete_rewrite", "architecture_change", "framework_migration"]
        },
        "security-validator": {
            "max_files_modified": 5,
            "max_lines_changed": 500,
            "forbidden_actions": ["disable_security", "remove_middleware", "bypass_authentication"]
        },
        "webui-architect": {
            "max_files_modified": 8,
            "max_lines_changed": 800,
            "forbidden_actions": ["framework_change", "complete_redesign", "delete_components"]
        },
        "schema-database-expert": {
            "max_files_modified": 3,
            "max_lines_changed": 300,
            "forbidden_actions": ["schema_migration", "data_deletion", "index_recreation"]
        }
    }
    
    agent_limits = scope_limits.get(agent_name, {
        "max_files_modified": 5,
        "max_lines_changed": 250,
        "forbidden_actions": ["major_changes"]
    })
    
    validation_result = {
        "agent": agent_name,
        "proposed_actions_count": len(proposed_actions),
        "scope_valid": True,
        "warnings": [],
        "blocked_actions": []
    }
    
    # Check action count
    if len(proposed_actions) > agent_limits["max_files_modified"]:
        validation_result["scope_valid"] = False
        validation_result["warnings"].append(f"Too many actions proposed: {len(proposed_actions)} > {agent_limits['max_files_modified']}")
    
    # Check for forbidden actions
    for action in proposed_actions:
        action_text = str(action).lower()
        for forbidden in agent_limits["forbidden_actions"]:
            if forbidden.replace("_", " ") in action_text:
                validation_result["blocked_actions"].append(action)
                validation_result["warnings"].append(f"Forbidden action detected: {forbidden}")
    
    if validation_result["blocked_actions"]:
        validation_result["scope_valid"] = False
    
    return json.dumps(validation_result)

# Initialize global instances
try:
    kg_client = OrchestrationKnowledgeClient()
    checkpoint_manager = OrchestrationCheckpointManager()
    doc_compressor = DocumentCompressionAgent()
except:
    print("Warning: Using fallback implementations for orchestration tools")
    kg_client = None
    checkpoint_manager = None  
    doc_compressor = None

# Enhanced tool list with advanced capabilities
advanced_orchestration_tools = [
    search_knowledge_graph_for_patterns,
    check_memory_for_past_failures,
    record_orchestration_outcome,
    get_agent_coordination_strategy,
    validate_specialist_scope
]

def get_all_orchestration_tools():
    """Return all orchestration tools including basic and advanced."""
    basic_tools = []
    
    # Add basic tools if available
    if kg_client:
        def query_orchestration_knowledge(entity: str) -> str:
            response = kg_client.query_knowledge(entity)
            return json.dumps(response)
        basic_tools.append(query_orchestration_knowledge)
    
    if checkpoint_manager:
        def create_orchestration_checkpoint(phase: str, state: dict, workflow_id: str = None) -> str:
            checkpoint_id = checkpoint_manager.create_checkpoint(phase, state, workflow_id)
            return f"Checkpoint created: {checkpoint_id}"
        basic_tools.append(create_orchestration_checkpoint)
    
    if doc_compressor:
        def compress_orchestration_document(content: str, target_tokens: int = 8000, strategy: str = "technical_compress") -> str:
            result = doc_compressor.compress_document(content, target_tokens, strategy)
            return json.dumps(result)
        basic_tools.append(compress_orchestration_document)
    
    return basic_tools + advanced_orchestration_tools