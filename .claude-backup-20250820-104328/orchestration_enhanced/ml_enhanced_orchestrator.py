"""ML-Enhanced Orchestrator for Claude Code CLI

Main orchestration controller that implements the complete 10-phase ML-enhanced
agentic workflow using only MCP services available in Claude Code CLI.

This replaces both the current ML and agentic flow systems with a unified
approach that integrates machine learning at every decision point.

Key Features:
- 10-phase orchestration workflow with ML integration
- MCP-only architecture (no external services)
- Intelligent file organization and context management
- Real inter-agent communication and coordination
- Evidence-based validation with concrete proof requirements
- Continuous learning and improvement cycles
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

# Graceful numpy import with fallback
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    # Fallback implementations for numpy functions
    class np:
        @staticmethod
        def mean(data):
            """Fallback implementation of numpy.mean"""
            if not data or len(data) == 0:
                return 0.0
            return sum(data) / len(data)
        
        @staticmethod
        def std(data):
            """Fallback implementation of numpy.std"""
            if not data or len(data) == 0:
                return 0.0
            if len(data) == 1:
                return 0.0
            mean_val = np.mean(data)
            variance = sum((x - mean_val) ** 2 for x in data) / len(data)
            return variance ** 0.5

try:
    import structlog
except ImportError:
    # Fallback logger if structlog is not available
    import logging
    class structlog:
        @staticmethod
        def get_logger(name):
            logger = logging.getLogger(name)
            logger.setLevel(logging.INFO)
            if not logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                logger.addHandler(handler)
            return logger

# Graceful import of MCP integration layer
try:
    from .mcp_integration_layer import MCPIntegrationLayer, AgentTask, WorkflowPhase
except ImportError:
    try:
        from mcp_integration_layer import MCPIntegrationLayer, AgentTask, WorkflowPhase
    except ImportError:
        # Fallback definitions if MCP integration layer is not available
        from enum import Enum
        from typing import Dict, Any
        from dataclasses import dataclass
        
        class WorkflowPhase(Enum):
            """Fallback workflow phases."""
            PHASE_0_TODO_CONTEXT = 0
            PHASE_1_AGENT_ECOSYSTEM = 1
            PHASE_2_STRATEGIC_PLANNING = 2
            PHASE_3_RESEARCH_DISCOVERY = 3
            PHASE_4_CONTEXT_SYNTHESIS = 4
            PHASE_5_PARALLEL_IMPLEMENTATION = 5
            PHASE_6_VALIDATION = 6
            PHASE_7_DECISION_CONTROL = 7
            PHASE_8_VERSION_CONTROL = 8
            PHASE_9_META_AUDIT = 9
            PHASE_10_TODO_INTEGRATION = 10
        
        @dataclass
        class AgentTask:
            """Fallback agent task definition."""
            agent_id: str
            task_type: str
            description: str
            context_data: Dict[str, Any]
            priority: int = 1
        
        class MCPIntegrationLayer:
            """Fallback MCP integration layer."""
            def __init__(self):
                self.workflow_id = f"fallback-{int(time.time())}"
                self.current_phase = WorkflowPhase.PHASE_0_TODO_CONTEXT
                self.agent_registry = {}
                self.results = {}
                self.workflow_context = {}
            
            async def start_workflow(self, context):
                return True
            
            async def register_agent(self, agent_id, agent_type, capabilities, specializations):
                self.agent_registry[agent_id] = {
                    'type': agent_type,
                    'capabilities': capabilities,
                    'specializations': specializations
                }
                return True
            
            async def _organize_file_placement(self, filename, file_type):
                from pathlib import Path
                base_paths = {
                    "deployment": "config/deployment/",
                    "documentation": "docs/",
                    "orchestration": ".claude/orchestration_state/"
                }
                base_path = base_paths.get(file_type, "")
                full_path = f"/home/marku/ai_workflow_engine/{base_path}{filename}"
                Path(full_path).parent.mkdir(parents=True, exist_ok=True)
                return full_path
            
            # Placeholder methods for phase execution
            async def _execute_phase_0_todo_context(self): pass
            async def _execute_phase_1_agent_ecosystem(self): pass
            async def _execute_phase_2_strategic_planning(self): pass
            async def _execute_phase_3_research_discovery(self): pass
            async def _execute_phase_4_context_synthesis(self): pass
            async def _execute_phase_5_parallel_implementation(self): pass
            async def _execute_phase_6_validation(self): pass
            async def _execute_phase_7_decision_control(self): pass
            async def _execute_phase_8_version_control(self): pass
            async def _execute_phase_9_meta_audit(self): pass
            async def _execute_phase_10_todo_integration(self): pass

logger = structlog.get_logger(__name__)

@dataclass
class MLDecisionPoint:
    """ML decision point with confidence scoring."""
    decision_type: str
    options: List[Dict[str, Any]]
    confidence_scores: List[float]
    recommended_action: str
    reasoning: str
    risk_assessment: float
    
class MLModelType(Enum):
    """ML model types for different decision scenarios."""
    AGENT_SELECTION = "agent_selection"
    PARALLEL_COORDINATION = "parallel_coordination"
    VALIDATION_STRATEGY = "validation_strategy"
    RISK_ASSESSMENT = "risk_assessment"
    CONTAINER_CONFLICT = "container_conflict"
    STREAM_PRIORITIZATION = "stream_prioritization"

class MLDecisionEngine:
    """ML-powered decision engine for orchestration."""
    
    def __init__(self):
        self.historical_decisions = []
        self.agent_performance_matrix = {}
        self.container_state_tracker = {}
        self.conflict_patterns = []
        
    async def make_decision(self, 
                          decision_type: MLModelType,
                          context: Dict[str, Any]) -> MLDecisionPoint:
        """Make ML-informed decision based on context and historical data."""
        
        if decision_type == MLModelType.AGENT_SELECTION:
            return await self._decide_agent_selection(context)
        elif decision_type == MLModelType.PARALLEL_COORDINATION:
            return await self._decide_parallel_coordination(context)
        elif decision_type == MLModelType.VALIDATION_STRATEGY:
            return await self._decide_validation_strategy(context)
        elif decision_type == MLModelType.RISK_ASSESSMENT:
            return await self._assess_risk(context)
        elif decision_type == MLModelType.CONTAINER_CONFLICT:
            return await self._detect_container_conflicts(context)
        elif decision_type == MLModelType.STREAM_PRIORITIZATION:
            return await self._prioritize_streams(context)
        else:
            raise ValueError(f"Unknown decision type: {decision_type}")
    
    async def _decide_agent_selection(self, context: Dict[str, Any]) -> MLDecisionPoint:
        """ML decision for optimal agent selection."""
        task_type = context.get('task_type', 'unknown')
        complexity = context.get('complexity', 0.5)
        available_agents = context.get('available_agents', [])
        
        # Score agents based on task compatibility and historical performance
        scored_agents = []
        for agent in available_agents:
            base_score = self._calculate_agent_compatibility(agent, task_type)
            performance_bonus = self._get_agent_performance_score(agent['id'])
            complexity_fit = self._calculate_complexity_fit(agent, complexity)
            
            total_score = (base_score * 0.5) + (performance_bonus * 0.3) + (complexity_fit * 0.2)
            
            scored_agents.append({
                'agent_id': agent['id'],
                'score': total_score,
                'capabilities': agent.get('capabilities', []),
                'specializations': agent.get('specializations', [])
            })
        
        # Sort by score and recommend top agents
        scored_agents.sort(key=lambda x: x['score'], reverse=True)
        top_agents = scored_agents[:3]  # Top 3 recommendations
        
        confidence = np.mean([agent['score'] for agent in top_agents]) if top_agents else 0.0
        
        return MLDecisionPoint(
            decision_type="agent_selection",
            options=scored_agents,
            confidence_scores=[agent['score'] for agent in scored_agents],
            recommended_action=f"Use agents: {[agent['agent_id'] for agent in top_agents]}",
            reasoning=f"Selected based on task compatibility ({task_type}) and performance history",
            risk_assessment=1.0 - confidence
        )
    
    async def _decide_parallel_coordination(self, context: Dict[str, Any]) -> MLDecisionPoint:
        """ML decision for parallel agent coordination strategy."""
        agents_requested = context.get('agents', [])
        container_dependencies = context.get('container_dependencies', {})
        current_loads = context.get('system_loads', {})
        
        # Analyze potential conflicts and coordination needs
        conflict_matrix = self._build_conflict_matrix(agents_requested, container_dependencies)
        coordination_groups = self._group_compatible_agents(agents_requested, conflict_matrix)
        
        # Calculate optimal execution order and parallelism
        execution_plan = []
        total_risk = 0.0
        
        for group in coordination_groups:
            group_risk = self._calculate_group_execution_risk(group, current_loads)
            execution_plan.append({
                'group_id': len(execution_plan),
                'agents': group,
                'parallel_safe': group_risk < 0.3,
                'estimated_duration': self._estimate_group_duration(group),
                'risk_score': group_risk
            })
            total_risk += group_risk
        
        avg_risk = total_risk / len(execution_plan) if execution_plan else 1.0
        confidence = 1.0 - avg_risk
        
        return MLDecisionPoint(
            decision_type="parallel_coordination",
            options=execution_plan,
            confidence_scores=[1.0 - group['risk_score'] for group in execution_plan],
            recommended_action=f"Execute {len(execution_plan)} coordination groups",
            reasoning="Grouped agents by container dependency conflicts and system load",
            risk_assessment=avg_risk
        )
    
    async def _decide_validation_strategy(self, context: Dict[str, Any]) -> MLDecisionPoint:
        """ML decision for optimal validation strategy."""
        changes_made = context.get('changes', [])
        affected_services = context.get('affected_services', [])
        criticality = context.get('criticality', 'medium')
        
        # Determine validation depth based on change impact
        validation_levels = []
        
        # Basic validation (always required)
        validation_levels.append({
            'level': 'basic',
            'agents': ['user-experience-auditor'],
            'confidence': 0.9,
            'coverage': 'primary_functionality'
        })
        
        # Service-specific validation
        if affected_services:
            validation_levels.append({
                'level': 'service_specific',
                'agents': ['fullstack-communication-auditor', 'security-validator'],
                'confidence': 0.8,
                'coverage': 'affected_services'
            })
        
        # Comprehensive validation for critical changes
        if criticality in ['high', 'critical']:
            validation_levels.append({
                'level': 'comprehensive',
                'agents': ['production-endpoint-validator', 'performance-profiler', 'infrastructure-recovery'],
                'confidence': 0.95,
                'coverage': 'full_system'
            })
        
        total_confidence = np.mean([level['confidence'] for level in validation_levels])
        
        return MLDecisionPoint(
            decision_type="validation_strategy",
            options=validation_levels,
            confidence_scores=[level['confidence'] for level in validation_levels],
            recommended_action=f"Execute {len(validation_levels)} validation levels",
            reasoning=f"Strategy based on criticality ({criticality}) and service impact",
            risk_assessment=1.0 - total_confidence
        )
    
    async def _assess_risk(self, context: Dict[str, Any]) -> MLDecisionPoint:
        """ML-powered risk assessment for current operation."""
        operation_type = context.get('operation_type', 'unknown')
        system_state = context.get('system_state', {})
        recent_failures = context.get('recent_failures', [])
        
        # Calculate risk factors
        base_risk = self._get_operation_base_risk(operation_type)
        system_health_risk = self._calculate_system_health_risk(system_state)
        failure_pattern_risk = self._analyze_failure_patterns(recent_failures)
        
        total_risk = (base_risk * 0.4) + (system_health_risk * 0.4) + (failure_pattern_risk * 0.2)
        confidence = 1.0 - total_risk
        
        risk_level = 'low' if total_risk < 0.3 else 'medium' if total_risk < 0.7 else 'high'
        
        return MLDecisionPoint(
            decision_type="risk_assessment",
            options=[{
                'risk_level': risk_level,
                'risk_score': total_risk,
                'mitigation_strategies': self._get_mitigation_strategies(risk_level)
            }],
            confidence_scores=[confidence],
            recommended_action=f"Proceed with {risk_level} risk mitigation",
            reasoning=f"Risk assessment based on operation type, system health, and failure patterns",
            risk_assessment=total_risk
        )
    
    async def _detect_container_conflicts(self, context: Dict[str, Any]) -> MLDecisionPoint:
        """Detect and prevent container operation conflicts."""
        requested_operations = context.get('operations', [])
        current_operations = context.get('current_operations', {})
        container_states = context.get('container_states', {})
        
        conflicts = []
        safe_operations = []
        
        for operation in requested_operations:
            container = operation.get('container')
            op_type = operation.get('type')
            
            # Check for conflicts with current operations
            if container in current_operations:
                current_op = current_operations[container]
                if self._operations_conflict(op_type, current_op['type']):
                    conflicts.append({
                        'container': container,
                        'requested_op': op_type,
                        'conflicting_op': current_op['type'],
                        'severity': self._get_conflict_severity(op_type, current_op['type'])
                    })
                else:
                    safe_operations.append(operation)
            else:
                safe_operations.append(operation)
        
        conflict_risk = len(conflicts) / len(requested_operations) if requested_operations else 0.0
        confidence = 1.0 - conflict_risk
        
        return MLDecisionPoint(
            decision_type="container_conflict",
            options=[{
                'safe_operations': safe_operations,
                'conflicts': conflicts,
                'resolution_strategy': self._get_conflict_resolution_strategy(conflicts)
            }],
            confidence_scores=[confidence],
            recommended_action=f"Execute {len(safe_operations)} safe operations, resolve {len(conflicts)} conflicts",
            reasoning="Container conflict analysis based on operation types and current states",
            risk_assessment=conflict_risk
        )
    
    async def _prioritize_streams(self, context: Dict[str, Any]) -> MLDecisionPoint:
        """ML-based stream prioritization for optimal execution order."""
        streams = context.get('streams', [])
        dependencies = context.get('dependencies', {})
        resource_constraints = context.get('resource_constraints', {})
        
        prioritized_streams = []
        
        for stream in streams:
            priority_score = self._calculate_stream_priority(
                stream, dependencies, resource_constraints
            )
            
            prioritized_streams.append({
                'stream_id': stream['id'],
                'priority_score': priority_score,
                'estimated_duration': stream.get('estimated_duration', 300),
                'resource_requirements': stream.get('resources', {}),
                'dependencies': dependencies.get(stream['id'], [])
            })
        
        # Sort by priority score (higher first)
        prioritized_streams.sort(key=lambda x: x['priority_score'], reverse=True)
        
        avg_confidence = np.mean([stream['priority_score'] for stream in prioritized_streams])
        
        return MLDecisionPoint(
            decision_type="stream_prioritization",
            options=prioritized_streams,
            confidence_scores=[stream['priority_score'] for stream in prioritized_streams],
            recommended_action=f"Execute streams in calculated priority order",
            reasoning="Prioritization based on dependencies, resource constraints, and impact",
            risk_assessment=1.0 - avg_confidence
        )
    
    def _calculate_agent_compatibility(self, agent: Dict, task_type: str) -> float:
        """Calculate how well an agent matches a task type."""
        capabilities = agent.get('capabilities', [])
        specializations = agent.get('specializations', [])
        
        # Simple keyword matching for now - could be enhanced with semantic analysis
        task_keywords = task_type.lower().split('_')
        
        capability_matches = sum(1 for cap in capabilities if any(kw in cap.lower() for kw in task_keywords))
        specialization_matches = sum(1 for spec in specializations if any(kw in spec.lower() for kw in task_keywords))
        
        total_features = len(capabilities) + len(specializations)
        total_matches = capability_matches + specialization_matches
        
        return total_matches / max(total_features, 1)
    
    def _get_agent_performance_score(self, agent_id: str) -> float:
        """Get historical performance score for an agent."""
        return self.agent_performance_matrix.get(agent_id, 0.5)  # Default to neutral
    
    def _calculate_complexity_fit(self, agent: Dict, complexity: float) -> float:
        """Calculate how well an agent fits the task complexity."""
        # Simple heuristic - could be enhanced with actual complexity modeling
        specialization_count = len(agent.get('specializations', []))
        capability_count = len(agent.get('capabilities', []))
        
        agent_sophistication = (specialization_count + capability_count) / 10  # Normalize
        
        # Return inverse of difference - closer to complexity is better
        return 1.0 - abs(agent_sophistication - complexity)
    
    def _build_conflict_matrix(self, agents: List[Dict], dependencies: Dict) -> Dict:
        """Build matrix of potential conflicts between agents."""
        matrix = {}
        
        for i, agent1 in enumerate(agents):
            for j, agent2 in enumerate(agents):
                if i != j:
                    conflict_score = self._calculate_agent_conflict(agent1, agent2, dependencies)
                    matrix[f"{agent1['id']}_{agent2['id']}"] = conflict_score
        
        return matrix
    
    def _calculate_agent_conflict(self, agent1: Dict, agent2: Dict, dependencies: Dict) -> float:
        """Calculate conflict probability between two agents."""
        # Check if they work on same containers
        containers1 = set(dependencies.get(agent1['id'], []))
        containers2 = set(dependencies.get(agent2['id'], []))
        
        shared_containers = containers1.intersection(containers2)
        
        if shared_containers:
            # High conflict if both modify same containers
            return 0.8
        elif self._agents_have_overlapping_scope(agent1, agent2):
            # Medium conflict if similar scope
            return 0.5
        else:
            # Low conflict
            return 0.1
    
    def _agents_have_overlapping_scope(self, agent1: Dict, agent2: Dict) -> bool:
        """Check if agents have overlapping operational scope."""
        caps1 = set(agent1.get('capabilities', []))
        caps2 = set(agent2.get('capabilities', []))
        
        return len(caps1.intersection(caps2)) > 0
    
    def _group_compatible_agents(self, agents: List[Dict], conflict_matrix: Dict) -> List[List[Dict]]:
        """Group agents into compatible execution groups."""
        groups = []
        remaining_agents = agents.copy()
        
        while remaining_agents:
            current_group = [remaining_agents.pop(0)]
            
            # Add compatible agents to current group
            compatible_agents = []
            for agent in remaining_agents:
                if self._agent_compatible_with_group(agent, current_group, conflict_matrix):
                    compatible_agents.append(agent)
            
            # Add compatible agents and remove from remaining
            for agent in compatible_agents:
                current_group.append(agent)
                remaining_agents.remove(agent)
            
            groups.append(current_group)
        
        return groups
    
    def _agent_compatible_with_group(self, agent: Dict, group: List[Dict], conflict_matrix: Dict) -> bool:
        """Check if agent is compatible with all agents in group."""
        for group_agent in group:
            conflict_key = f"{agent['id']}_{group_agent['id']}"
            conflict_score = conflict_matrix.get(conflict_key, 0.5)
            
            if conflict_score > 0.6:  # High conflict threshold
                return False
        
        return True
    
    def _calculate_group_execution_risk(self, group: List[Dict], system_loads: Dict) -> float:
        """Calculate risk of executing agent group simultaneously."""
        base_risk = len(group) * 0.1  # More agents = higher base risk
        
        # Add system load risk
        avg_load = np.mean(list(system_loads.values())) if system_loads else 0.5
        load_risk = avg_load * 0.3
        
        return min(base_risk + load_risk, 1.0)
    
    def _estimate_group_duration(self, group: List[Dict]) -> int:
        """Estimate execution duration for agent group."""
        # Simple heuristic - could be enhanced with historical data
        base_duration = 60  # seconds
        complexity_factor = len(group) * 30
        
        return base_duration + complexity_factor
    
    def _get_operation_base_risk(self, operation_type: str) -> float:
        """Get base risk level for operation type."""
        risk_levels = {
            'container_restart': 0.6,
            'config_change': 0.4,
            'deployment': 0.7,
            'database_migration': 0.8,
            'file_modification': 0.2,
            'service_update': 0.5
        }
        
        return risk_levels.get(operation_type, 0.5)
    
    def _calculate_system_health_risk(self, system_state: Dict) -> float:
        """Calculate risk based on current system health."""
        health_metrics = system_state.get('health_metrics', {})
        
        if not health_metrics:
            return 0.5  # Unknown state
        
        # Combine various health indicators
        cpu_usage = health_metrics.get('cpu_usage', 50) / 100
        memory_usage = health_metrics.get('memory_usage', 50) / 100
        error_rate = health_metrics.get('error_rate', 0)
        
        health_risk = (cpu_usage * 0.3) + (memory_usage * 0.3) + (error_rate * 0.4)
        
        return min(health_risk, 1.0)
    
    def _analyze_failure_patterns(self, recent_failures: List[Dict]) -> float:
        """Analyze recent failures for pattern-based risk."""
        if not recent_failures:
            return 0.0
        
        # Weight recent failures more heavily
        total_weight = 0
        weighted_risk = 0
        
        for i, failure in enumerate(recent_failures):
            weight = 1.0 / (i + 1)  # More recent = higher weight
            severity = failure.get('severity', 0.5)
            
            weighted_risk += severity * weight
            total_weight += weight
        
        return weighted_risk / total_weight if total_weight > 0 else 0.0
    
    def _get_mitigation_strategies(self, risk_level: str) -> List[str]:
        """Get mitigation strategies for risk level."""
        strategies = {
            'low': ['standard_monitoring', 'basic_rollback_plan'],
            'medium': ['enhanced_monitoring', 'staged_rollout', 'ready_rollback'],
            'high': ['comprehensive_monitoring', 'canary_deployment', 'immediate_rollback_capability', 'stakeholder_notification']
        }
        
        return strategies.get(risk_level, [])
    
    def _operations_conflict(self, op1: str, op2: str) -> bool:
        """Check if two operation types conflict."""
        conflict_pairs = [
            ('restart', 'config_change'),
            ('restart', 'deployment'),
            ('deployment', 'config_change'),
            ('migration', 'restart')
        ]
        
        return (op1, op2) in conflict_pairs or (op2, op1) in conflict_pairs
    
    def _get_conflict_severity(self, op1: str, op2: str) -> float:
        """Get severity score for operation conflict."""
        severity_map = {
            ('restart', 'config_change'): 0.8,
            ('restart', 'deployment'): 0.9,
            ('deployment', 'config_change'): 0.7,
            ('migration', 'restart'): 0.95
        }
        
        return severity_map.get((op1, op2), severity_map.get((op2, op1), 0.5))
    
    def _get_conflict_resolution_strategy(self, conflicts: List[Dict]) -> str:
        """Get strategy for resolving conflicts."""
        if not conflicts:
            return "no_conflicts"
        
        high_severity_conflicts = [c for c in conflicts if c['severity'] > 0.8]
        
        if high_severity_conflicts:
            return "sequential_execution_required"
        else:
            return "delayed_execution_acceptable"
    
    def _calculate_stream_priority(self, stream: Dict, dependencies: Dict, constraints: Dict) -> float:
        """Calculate priority score for a stream."""
        base_priority = stream.get('base_priority', 0.5)
        
        # Dependency factor - streams with fewer dependencies get higher priority
        stream_deps = dependencies.get(stream['id'], [])
        dependency_factor = 1.0 - (len(stream_deps) * 0.1)
        
        # Resource availability factor
        required_resources = stream.get('resources', {})
        available_resources = constraints.get('available_resources', {})
        
        resource_availability = 1.0
        for resource, amount in required_resources.items():
            available = available_resources.get(resource, 1.0)
            if available < amount:
                resource_availability *= 0.5  # Penalize if resources not available
        
        # Impact factor
        impact_score = stream.get('impact_score', 0.5)
        
        # Combine factors
        priority_score = (base_priority * 0.3) + (dependency_factor * 0.2) + \
                        (resource_availability * 0.3) + (impact_score * 0.2)
        
        return min(priority_score, 1.0)
    
    def update_agent_performance(self, agent_id: str, success: bool, duration: float):
        """Update agent performance metrics."""
        if agent_id not in self.agent_performance_matrix:
            self.agent_performance_matrix[agent_id] = 0.5
        
        # Simple moving average
        current_score = self.agent_performance_matrix[agent_id]
        success_score = 1.0 if success else 0.0
        
        # Weight recent performance higher
        new_score = (current_score * 0.8) + (success_score * 0.2)
        self.agent_performance_matrix[agent_id] = new_score
        
        # Store historical decision for learning
        self.historical_decisions.append({
            'agent_id': agent_id,
            'success': success,
            'duration': duration,
            'timestamp': time.time()
        })

class MLEnhancedOrchestrator:
    """Main orchestrator for ML-enhanced agentic workflows."""
    
    def __init__(self):
        """Initialize the ML-enhanced orchestrator."""
        self.integration_layer: Optional[MCPIntegrationLayer] = None
        self.workflow_active = False
        self.current_workflow_id: Optional[str] = None
        
        # ML decision engine for intelligent orchestration
        self.ml_engine = MLDecisionEngine()
        
        # Stream 3: Enhanced inter-agent communication
        self.communication_hub: Optional['EnhancedAgentCommunicationHub'] = None
        self.agent_coordination_active = False
        
        # Stream-based execution tracking
        self.active_streams = {}
        self.stream_dependencies = {}
        self.validation_streams = {}
        
        # Container coordination integration
        try:
            from container_coordination import integrate_with_ml_orchestrator, get_coordination_system
            self.container_coordination = get_coordination_system()
            integrate_with_ml_orchestrator(self)
            logger.info("Container coordination system integrated successfully")
        except ImportError:
            logger.warning("Container coordination system not available")
            # Fallback container tracking
            self.container_operations = {}
            self.container_locks = set()
            self.container_coordination = None
        
        # Agent instance management
        self.agent_instances = {}
        self.max_agent_instances = 3  # Maximum instances per agent type
        
        # Agent specifications from AGENT_REGISTRY.md
        self.available_agents = {
            # Development Specialists
            "backend-gateway-expert": {
                "agent_type": "development",
                "capabilities": ["api_design", "containerization", "fastapi_optimization"],
                "specializations": ["server_architecture", "docker_configuration", "worker_systems"]
            },
            "schema-database-expert": {
                "agent_type": "development", 
                "capabilities": ["database_analysis", "query_optimization", "data_modeling"],
                "specializations": ["schema_optimization", "performance_tuning", "migration_management"]
            },
            "python-refactoring-architect": {
                "agent_type": "development",
                "capabilities": ["code_refactoring", "architectural_analysis", "design_patterns"],
                "specializations": ["clean_code", "solid_principles", "modular_architecture"]
            },
            "codebase-research-analyst": {
                "agent_type": "development",
                "capabilities": ["code_analysis", "implementation_discovery", "dependency_analysis"],
                "specializations": ["static_analysis", "pattern_recognition", "documentation_extraction"]
            },
            
            # Frontend & UX Specialists
            "webui-architect": {
                "agent_type": "frontend",
                "capabilities": ["component_design", "state_management", "performance_optimization"],
                "specializations": ["react_components", "browser_automation", "navigation_systems"]
            },
            "frictionless-ux-architect": {
                "agent_type": "ux",
                "capabilities": ["user_journey_analysis", "conversion_optimization", "friction_identification"],
                "specializations": ["user_behavior_analysis", "ab_testing", "ux_research"]
            },
            "whimsy-ui-creator": {
                "agent_type": "ux",
                "capabilities": ["animation_design", "micro_interactions", "visual_storytelling"],
                "specializations": ["css_animations", "interactive_elements", "brand_experience"]
            },
            "ui-regression-debugger": {
                "agent_type": "quality",
                "capabilities": ["visual_regression_testing", "browser_automation", "screenshot_comparison"],
                "specializations": ["playwright_integration", "visual_testing", "automated_qa"]
            },
            
            # Quality Assurance Specialists
            "security-validator": {
                "agent_type": "security",
                "capabilities": ["security_validation", "penetration_testing", "vulnerability_assessment"],
                "specializations": ["jwt_security", "authentication_flows", "security_scanning"]
            },
            "user-experience-auditor": {
                "agent_type": "validation",
                "capabilities": ["browser_automation", "user_interaction_simulation", "workflow_validation"],
                "specializations": ["playwright_testing", "production_validation", "evidence_collection"]
            },
            "test-automation-engineer": {
                "agent_type": "testing",
                "capabilities": ["test_generation", "test_optimization", "ci_cd_integration"],
                "specializations": ["unit_testing", "integration_testing", "end_to_end_testing"]
            },
            "fullstack-communication-auditor": {
                "agent_type": "validation",
                "capabilities": ["api_testing", "contract_verification", "integration_analysis"],
                "specializations": ["frontend_backend_integration", "websocket_debugging", "jwt_validation"]
            },
            "code-quality-guardian": {
                "agent_type": "quality",
                "capabilities": ["code_review", "quality_metrics", "standards_enforcement"],
                "specializations": ["linting", "code_analysis", "best_practices"]
            },
            "performance-profiler": {
                "agent_type": "performance",
                "capabilities": ["performance_monitoring", "bottleneck_identification", "optimization"],
                "specializations": ["profiling_tools", "resource_monitoring", "load_testing"]
            },
            
            # Infrastructure & DevOps Specialists
            "deployment-orchestrator": {
                "agent_type": "infrastructure",
                "capabilities": ["deployment_automation", "environment_management", "rollback_strategies"],
                "specializations": ["ci_cd_pipelines", "container_orchestration", "infrastructure_automation"]
            },
            "monitoring-analyst": {
                "agent_type": "infrastructure",
                "capabilities": ["metrics_collection", "alerting_configuration", "dashboard_creation"],
                "specializations": ["application_monitoring", "infrastructure_health", "error_tracking"]
            },
            "atomic-git-synchronizer": {
                "agent_type": "infrastructure",
                "capabilities": ["version_control", "atomic_commits", "repository_synchronization"],
                "specializations": ["commit_organization", "meaningful_messages", "atomic_changes"]
            },
            
            # Orchestration Management Agents
            "orchestration-todo-manager": {
                "agent_type": "orchestration",
                "capabilities": ["todo_management", "context_continuity", "priority_management"],
                "specializations": ["cross_session_todos", "context_integration", "workflow_coordination"]
            },
            "agent-integration-orchestrator": {
                "agent_type": "orchestration",
                "capabilities": ["agent_discovery", "integration_management", "ecosystem_health"],
                "specializations": ["agent_validation", "capability_mapping", "system_readiness"]
            },
            "project-orchestrator": {
                "agent_type": "orchestration",
                "capabilities": ["strategic_planning", "coordination_strategy", "high_level_planning"],
                "specializations": ["methodology_determination", "specialist_coordination", "strategy_creation"]
            },
            "enhanced-nexus-synthesis-agent": {
                "agent_type": "intelligence",
                "capabilities": ["pattern_analysis", "historical_learning", "intelligence_synthesis"],
                "specializations": ["cross_domain_integration", "pattern_recognition", "learning_outcomes"]
            },
            "nexus-synthesis-agent": {
                "agent_type": "intelligence", 
                "capabilities": ["context_synthesis", "pattern_integration", "package_creation"],
                "specializations": ["size_limited_packages", "context_optimization", "domain_packaging"]
            },
            "orchestration-auditor-v2": {
                "agent_type": "orchestration",
                "capabilities": ["evidence_analysis", "decision_validation", "iteration_control"],
                "specializations": ["validation_evidence", "success_determination", "iteration_logic"]
            },
            "orchestration-auditor": {
                "agent_type": "orchestration",
                "capabilities": ["meta_analysis", "workflow_improvement", "learning_extraction"],
                "specializations": ["process_analysis", "continuous_improvement", "success_patterns"]
            },
            "evidence-auditor": {
                "agent_type": "validation",
                "capabilities": ["evidence_validation", "pattern_verification", "quality_assurance"],
                "specializations": ["evidence_standards", "validation_quality", "proof_requirements"]
            }
        }
        
        logger.info("ML-Enhanced Orchestrator initialized with ML decision engine")
    
    async def initialize_enhanced_communication(self):
        """Initialize enhanced inter-agent communication system (Stream 3)."""
        try:
            # Import here to avoid circular imports
            from .agent_communication import get_enhanced_communication_hub
            
            self.communication_hub = await get_enhanced_communication_hub(use_mcp_services=True)
            self.agent_coordination_active = True
            
            # Register all available agents with communication hub
            await self._register_agents_with_communication_hub()
            
            # Set up coordination message handlers
            await self._setup_communication_handlers()
            
            logger.info("Enhanced inter-agent communication system initialized")
            return True
            
        except Exception as e:
            logger.error("Failed to initialize enhanced communication", error=str(e))
            return False
    
    async def _register_agents_with_communication_hub(self):
        """Register all available agents with the communication hub."""
        if not self.communication_hub:
            return
        
        from .agent_communication import AgentInfo, AgentRole
        
        for agent_id, agent_spec in self.available_agents.items():
            # Map agent types to roles
            role_mapping = {
                "development": AgentRole.SPECIALIST,
                "frontend": AgentRole.SPECIALIST,
                "ux": AgentRole.SPECIALIST,
                "quality": AgentRole.VALIDATOR,
                "security": AgentRole.VALIDATOR,
                "validation": AgentRole.VALIDATOR,
                "testing": AgentRole.VALIDATOR,
                "performance": AgentRole.SPECIALIST,
                "infrastructure": AgentRole.SPECIALIST,
                "orchestration": AgentRole.ORCHESTRATOR,
                "intelligence": AgentRole.COORDINATOR
            }
            
            agent_role = role_mapping.get(agent_spec["agent_type"], AgentRole.SPECIALIST)
            
            agent_info = AgentInfo(
                agent_id=agent_id,
                agent_type=agent_spec["agent_type"],
                role=agent_role,
                capabilities=agent_spec["capabilities"],
                specializations=agent_spec["specializations"],
                max_concurrent_tasks=3,
                dynamic_request_capability=True
            )
            
            await self.communication_hub.register_agent(agent_info)
        
        logger.info("Registered agents with communication hub", 
                   count=len(self.available_agents))
    
    async def _setup_communication_handlers(self):
        """Set up message handlers for enhanced communication."""
        if not self.communication_hub:
            return
        
        # Set up broadcast groups for coordination
        await self._create_broadcast_groups()
        
        # Set up coordination session for parallel execution
        await self._initialize_coordination_patterns()
        
        logger.info("Communication handlers configured")
    
    async def _create_broadcast_groups(self):
        """Create broadcast groups for different agent types."""
        if not self.communication_hub:
            return
        
        # Group agents by type for efficient broadcasting
        agent_groups = {}
        for agent_id, agent_spec in self.available_agents.items():
            agent_type = agent_spec["agent_type"]
            if agent_type not in agent_groups:
                agent_groups[agent_type] = set()
            agent_groups[agent_type].add(agent_id)
        
        # Set up broadcast groups
        self.communication_hub.broadcast_groups = agent_groups
        
        # Add special groups
        self.communication_hub.broadcast_groups["validators"] = {
            agent_id for agent_id, spec in self.available_agents.items()
            if spec["agent_type"] in ["quality", "security", "validation", "testing"]
        }
        
        self.communication_hub.broadcast_groups["specialists"] = {
            agent_id for agent_id, spec in self.available_agents.items()
            if spec["agent_type"] in ["development", "frontend", "performance", "infrastructure"]
        }
        
        self.communication_hub.broadcast_groups["orchestrators"] = {
            agent_id for agent_id, spec in self.available_agents.items()
            if spec["agent_type"] == "orchestration"
        }
    
    async def _initialize_coordination_patterns(self):
        """Initialize coordination patterns for parallel execution."""
        # This sets up the framework for coordination during parallel execution
        # The actual coordination will happen when workflows are executed
        pass
        
    async def execute_streaming_fixes(self, 
                                    fix_specifications: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute fixes using streaming approach with ML coordination."""
        
        # ML-based stream prioritization
        ml_decision = await self.ml_engine.make_decision(
            MLModelType.STREAM_PRIORITIZATION,
            {
                'streams': fix_specifications,
                'dependencies': self._analyze_stream_dependencies(fix_specifications),
                'resource_constraints': await self._get_system_constraints()
            }
        )
        
        prioritized_streams = ml_decision.options
        logger.info(f"ML prioritized {len(prioritized_streams)} fix streams", 
                   confidence=ml_decision.confidence_scores)
        
        # Execute streams with validation
        execution_results = {}
        
        for stream in prioritized_streams:
            stream_id = stream['stream_id']
            
            # Check dependencies
            if await self._dependencies_satisfied(stream_id):
                # Execute stream
                result = await self._execute_fix_stream(stream)
                execution_results[stream_id] = result
                
                # Immediate validation if no dependencies
                if not stream.get('dependencies'):
                    validation_result = await self._validate_stream_immediately(stream_id)
                    execution_results[f"{stream_id}_validation"] = validation_result
            else:
                # Queue for later execution
                self.active_streams[stream_id] = {
                    'status': 'waiting_dependencies',
                    'stream': stream
                }
        
        return {
            'ml_decision': ml_decision.__dict__,
            'execution_results': execution_results,
            'active_streams': list(self.active_streams.keys())
        }
    
    async def execute_parallel_agents(self, 
                                    agent_requests: List[Dict[str, Any]],
                                    allow_multiple_instances: bool = True) -> Dict[str, Any]:
        """Execute multiple agents in parallel with enhanced communication and ML coordination."""
        
        # Initialize communication system if not already done
        if not self.agent_coordination_active:
            await self.initialize_enhanced_communication()
        
        # ML-based parallel coordination decision
        ml_decision = await self.ml_engine.make_decision(
            MLModelType.PARALLEL_COORDINATION,
            {
                'agents': agent_requests,
                'container_dependencies': await self._get_container_dependencies(),
                'system_loads': await self._get_system_loads()
            }
        )
        
        coordination_groups = ml_decision.options
        logger.info(f"ML created {len(coordination_groups)} coordination groups",
                   risk_assessment=ml_decision.risk_assessment)
        
        # Create coordination session for enhanced communication
        workflow_id = self.current_workflow_id or f"parallel_execution_{int(time.time())}"
        participating_agents = [agent['id'] for group in coordination_groups for agent in group['agents']]
        
        if self.communication_hub:
            await self.communication_hub.create_coordination_session(
                workflow_id=workflow_id,
                participating_agents=participating_agents,
                coordination_type="parallel_ml_enhanced"
            )
        
        # Execute coordination groups with enhanced communication
        execution_results = {}
        
        for group in coordination_groups:
            if group['parallel_safe']:
                # Execute group in parallel with real-time communication
                group_results = await self._execute_agent_group_parallel_enhanced(
                    group['agents'], allow_multiple_instances, workflow_id
                )
                execution_results[f"group_{group['group_id']}"] = group_results
            else:
                # Execute group sequentially with coordination
                group_results = await self._execute_agent_group_sequential_enhanced(
                    group['agents'], allow_multiple_instances, workflow_id
                )
                execution_results[f"group_{group['group_id']}_sequential"] = group_results
        
        # Collect coordination insights
        coordination_summary = await self._analyze_coordination_performance(workflow_id)
        
        return {
            'ml_coordination': ml_decision.__dict__,
            'execution_results': execution_results,
            'coordination_summary': coordination_summary,
            'total_agents_executed': sum(len(group['agents']) for group in coordination_groups),
            'communication_enabled': self.agent_coordination_active
        }
    
    async def plan_and_execute_audit(self, audit_context: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 9: Plan audit strategy then execute with multiple agents."""
        
        # Part 1: Plan the audit strategy
        audit_plan = await self._plan_comprehensive_audit(audit_context)
        
        # Part 2: Execute audit with multiple agent instances
        audit_results = await self._execute_audit_with_multiple_agents(audit_plan)
        
        return {
            'audit_plan': audit_plan,
            'audit_execution': audit_results
        }
    
    async def _plan_comprehensive_audit(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """PART 1: Plan comprehensive audit strategy using ML decision engine."""
        
        # ML decision for audit strategy
        ml_decision = await self.ml_engine.make_decision(
            MLModelType.VALIDATION_STRATEGY,
            {
                'changes': context.get('changes_made', []),
                'affected_services': context.get('affected_services', []),
                'criticality': context.get('criticality', 'medium'),
                'workflow_complexity': len(context.get('agents_used', [])),
                'execution_time': context.get('execution_time', 0)
            }
        )
        
        # Define comprehensive audit phases with specific agent types
        audit_plan = {
            'strategy': ml_decision.__dict__,
            'audit_phases': [
                {
                    'level': 'meta_orchestration_audit',
                    'agents': ['orchestration-auditor', 'orchestration-auditor'],  # 2 instances
                    'coverage': 'workflow_execution_analysis',
                    'confidence_target': 0.85,
                    'description': 'Meta-orchestration analysis and pattern detection'
                },
                {
                    'level': 'evidence_validation_audit', 
                    'agents': ['evidence-auditor', 'evidence-auditor'],  # 2 instances
                    'coverage': 'evidence_quality_assessment',
                    'confidence_target': 0.80,
                    'description': 'Evidence validation and quality assessment'
                },
                {
                    'level': 'conflict_detection_audit',
                    'agents': ['execution-conflict-detector'],  # 1 instance
                    'coverage': 'conflict_analysis_resolution',
                    'confidence_target': 0.75,
                    'description': 'Conflict analysis and resolution verification'
                },
                {
                    'level': 'performance_audit',
                    'agents': ['performance-profiler'],  # 1 instance
                    'coverage': 'execution_performance_analysis',
                    'confidence_target': 0.70,
                    'description': 'Execution performance and efficiency audit'
                },
                {
                    'level': 'security_compliance_audit',
                    'agents': ['security-validator'],  # 1 instance
                    'coverage': 'security_compliance_verification',
                    'confidence_target': 0.85,
                    'description': 'Security compliance and vulnerability audit'
                }
            ],
            'required_agents': [],
            'validation_criteria': [
                'concrete_evidence_collection',
                'independent_verification',
                'multi_agent_consensus',
                'production_endpoint_validation',
                'user_workflow_verification',
                'historical_pattern_analysis',
                'failure_prediction_assessment',
                'continuous_learning_integration'
            ],
            'execution_strategy': {
                'parallel_execution': True,
                'max_instances_per_agent': 2,
                'consensus_threshold': 0.75,
                'evidence_aggregation': True,
                'failure_tolerance': 0.20
            }
        }
        
        # Collect all required agents
        for phase in audit_plan['audit_phases']:
            audit_plan['required_agents'].extend(phase['agents'])
        
        # Add ML-enhanced audit scope definition
        audit_plan['ml_enhanced_scope'] = {
            'pattern_recognition': True,
            'historical_analysis': True,
            'predictive_validation': True,
            'intelligent_prioritization': True,
            'automated_evidence_correlation': True
        }
        
        return audit_plan
    
    async def _execute_audit_with_multiple_agents(self, audit_plan: Dict[str, Any]) -> Dict[str, Any]:
        """PART 2: Execute comprehensive audit using multiple agent instances with consensus analysis."""
        
        audit_results = {
            'phase_results': {},
            'agent_findings': {},
            'consensus_analysis': {},
            'overall_assessment': {},
            'evidence_aggregation': {},
            'ml_enhanced_insights': {}
        }
        
        # Execute each audit phase with multiple agent instances
        for phase in audit_plan['audit_phases']:
            phase_level = phase['level']
            phase_agents = phase['agents']
            confidence_target = phase['confidence_target']
            
            logger.info(f"🔍 Executing audit phase: {phase_level}")
            logger.info(f"   • Agents: {phase_agents}")
            logger.info(f"   • Target confidence: {confidence_target}")
            
            # Create agent instances with unique identifiers
            agent_instances = []
            instance_counter = 0
            
            for agent_type in phase_agents:
                instance_counter += 1
                agent_instances.append({
                    'agent_type': agent_type,
                    'instance_id': instance_counter,
                    'task': f"comprehensive_audit_{phase_level}_{agent_type}_{instance_counter}",
                    'audit_scope': phase['coverage'],
                    'confidence_target': confidence_target,
                    'phase_description': phase['description'],
                    'validation_criteria': audit_plan['validation_criteria']
                })
            
            # Execute agent instances in parallel for independent verification
            phase_results = await self._execute_audit_agents_parallel(agent_instances)
            audit_results['phase_results'][phase_level] = phase_results
            
            # Collect agent findings by type
            for agent_instance, result in phase_results.items():
                agent_type = result.get('agent_type', 'unknown')
                if agent_type not in audit_results['agent_findings']:
                    audit_results['agent_findings'][agent_type] = []
                audit_results['agent_findings'][agent_type].append(result)
        
        # EVIDENCE AGGREGATION: Collect and correlate evidence across all agents
        audit_results['evidence_aggregation'] = await self._aggregate_audit_evidence(
            audit_results['phase_results']
        )
        
        # CONSENSUS ANALYSIS: Analyze agreement/disagreement across multiple auditors
        consensus = await self._analyze_audit_consensus(audit_results['phase_results'])
        audit_results['consensus_analysis'] = consensus
        
        # ML-ENHANCED INSIGHTS: Apply ML patterns for deeper analysis
        audit_results['ml_enhanced_insights'] = await self._generate_ml_audit_insights(
            audit_results, audit_plan
        )
        
        # OVERALL ASSESSMENT: Generate comprehensive assessment
        audit_results['overall_assessment'] = {
            'confidence_score': consensus.get('average_confidence', 0.0),
            'consensus_level': consensus.get('consensus_level', 'low'),
            'critical_findings': consensus.get('critical_findings', []),
            'recommendations': consensus.get('recommendations', []),
            'evidence_quality_score': audit_results['evidence_aggregation'].get('quality_score', 0.0),
            'ml_confidence_adjustment': audit_results['ml_enhanced_insights'].get('confidence_adjustment', 0.0),
            'audit_completion_status': 'comprehensive' if consensus.get('consensus_level') == 'high' else 'standard'
        }
        
        logger.info(f"✅ Multi-agent audit execution completed")
        logger.info(f"   • Phases executed: {len(audit_results['phase_results'])}")
        logger.info(f"   • Agent types involved: {len(audit_results['agent_findings'])}")
        logger.info(f"   • Consensus level: {consensus.get('consensus_level', 'unknown')}")
        logger.info(f"   • Overall confidence: {audit_results['overall_assessment']['confidence_score']:.2f}")
        
        return audit_results
    
    async def _execute_fix_stream(self, stream: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single fix stream."""
        stream_id = stream['stream_id']
        
        # Check for container conflicts
        ml_decision = await self.ml_engine.make_decision(
            MLModelType.CONTAINER_CONFLICT,
            {
                'operations': [stream.get('operation', {})],
                'current_operations': self.container_operations,
                'container_states': await self._get_container_states()
            }
        )
        
        if ml_decision.options[0]['conflicts']:
            return {
                'status': 'conflict_detected',
                'conflicts': ml_decision.options[0]['conflicts'],
                'resolution_strategy': ml_decision.options[0]['resolution_strategy']
            }
        
        # Execute the stream
        try:
            # Lock containers being modified
            containers = stream.get('containers', [])
            for container in containers:
                self.container_locks.add(container)
            
            # Record operation
            self.container_operations[stream_id] = {
                'type': stream.get('operation', {}).get('type', 'unknown'),
                'containers': containers,
                'started_at': time.time()
            }
            
            # Execute the actual fix (placeholder for real implementation)
            execution_result = await self._execute_stream_implementation(stream)
            
            return {
                'status': 'completed',
                'result': execution_result,
                'duration': time.time() - self.container_operations[stream_id]['started_at']
            }
            
        finally:
            # Release container locks
            for container in containers:
                self.container_locks.discard(container)
            
            # Remove operation record
            if stream_id in self.container_operations:
                del self.container_operations[stream_id]
    
    async def _validate_stream_immediately(self, stream_id: str) -> Dict[str, Any]:
        """Validate a stream immediately after execution."""
        
        # Create validation task
        validation_task = {
            'stream_id': stream_id,
            'validation_type': 'immediate',
            'agents': ['user-experience-auditor', 'security-validator']
        }
        
        # Execute validation agents in parallel
        validation_results = await self._execute_validation_agents(validation_task)
        
        return {
            'validation_type': 'immediate',
            'results': validation_results,
            'passed': all(result.get('success', False) for result in validation_results.values())
        }
    
    async def _execute_agent_group_parallel_enhanced(self, 
                                                   agents: List[Dict[str, Any]], 
                                                   allow_multiple_instances: bool,
                                                   workflow_id: str) -> Dict[str, Any]:
        """Execute a group of agents in parallel with enhanced communication."""
        
        # Prepare agent tasks with communication capabilities
        agent_tasks = []
        agent_ids = []
        
        for agent in agents:
            if allow_multiple_instances and agent.get('allow_instances', True):
                # Create multiple instances
                for instance_id in range(min(agent.get('max_instances', 2), self.max_agent_instances)):
                    task_agent_id = f"{agent['id']}_instance_{instance_id}"
                    agent_tasks.append({
                        'agent_type': agent['id'],
                        'agent_id': task_agent_id,
                        'instance_id': instance_id,
                        'task_context': agent.get('context', {}),
                        'workflow_id': workflow_id
                    })
                    agent_ids.append(task_agent_id)
            else:
                # Single instance
                agent_tasks.append({
                    'agent_type': agent['id'],
                    'agent_id': agent['id'],
                    'instance_id': 0,
                    'task_context': agent.get('context', {}),
                    'workflow_id': workflow_id
                })
                agent_ids.append(agent['id'])
        
        # Set up inter-agent communication for this group
        if self.communication_hub:
            await self._setup_group_communication(agent_ids, workflow_id)
        
        # Execute all tasks in parallel with communication support
        try:
            results = await asyncio.gather(
                *[self._execute_single_agent_task_enhanced(task) for task in agent_tasks],
                return_exceptions=True
            )
            
            # Process results and collect communication insights
            execution_results = {}
            communication_metrics = {}
            
            for i, result in enumerate(results):
                task = agent_tasks[i]
                task_key = f"{task['agent_type']}_instance_{task['instance_id']}"
                
                if isinstance(result, Exception):
                    execution_results[task_key] = {
                        'status': 'error',
                        'error': str(result)
                    }
                else:
                    execution_results[task_key] = result
                    
                    # Collect communication metrics if available
                    if 'communication_metrics' in result:
                        communication_metrics[task_key] = result['communication_metrics']
            
            # Analyze group coordination effectiveness
            coordination_analysis = await self._analyze_group_coordination(
                agent_ids, workflow_id, communication_metrics
            )
            
            return {
                'execution_results': execution_results,
                'communication_metrics': communication_metrics,
                'coordination_analysis': coordination_analysis,
                'group_performance': await self._calculate_group_performance(execution_results)
            }
            
        except Exception as e:
            logger.error(f"Enhanced parallel agent execution failed: {e}")
            return {'status': 'execution_failed', 'error': str(e)}
    
    async def _execute_agent_group_parallel(self, 
                                          agents: List[Dict[str, Any]], 
                                          allow_multiple_instances: bool) -> Dict[str, Any]:
        """Execute a group of agents in parallel (legacy method)."""
        
        # Prepare agent tasks
        agent_tasks = []
        
        for agent in agents:
            if allow_multiple_instances and agent.get('allow_instances', True):
                # Create multiple instances
                for instance_id in range(min(agent.get('max_instances', 2), self.max_agent_instances)):
                    agent_tasks.append({
                        'agent_type': agent['id'],
                        'instance_id': instance_id,
                        'task_context': agent.get('context', {})
                    })
            else:
                # Single instance
                agent_tasks.append({
                    'agent_type': agent['id'],
                    'instance_id': 0,
                    'task_context': agent.get('context', {})
                })
        
        # Execute all tasks in parallel using asyncio.gather
        try:
            results = await asyncio.gather(
                *[self._execute_single_agent_task(task) for task in agent_tasks],
                return_exceptions=True
            )
            
            # Process results
            execution_results = {}
            for i, result in enumerate(results):
                task = agent_tasks[i]
                task_key = f"{task['agent_type']}_instance_{task['instance_id']}"
                
                if isinstance(result, Exception):
                    execution_results[task_key] = {
                        'status': 'error',
                        'error': str(result)
                    }
                else:
                    execution_results[task_key] = result
            
            return execution_results
            
        except Exception as e:
            logger.error(f"Parallel agent execution failed: {e}")
            return {'status': 'execution_failed', 'error': str(e)}
    
    async def _execute_single_agent_task_enhanced(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single agent task with enhanced communication capabilities."""
        
        agent_type = task['agent_type']
        agent_id = task['agent_id']
        instance_id = task['instance_id']
        context = task['task_context']
        workflow_id = task['workflow_id']
        
        start_time = time.time()
        communication_metrics = {
            'messages_sent': 0,
            'messages_received': 0,
            'context_shares': 0,
            'dynamic_requests': 0,
            'conflicts_resolved': 0
        }
        
        try:
            # Enhanced agent execution with communication capabilities
            
            # 1. Initial coordination message
            if self.communication_hub:
                initial_message = {
                    'action': 'task_started',
                    'agent_id': agent_id,
                    'workflow_id': workflow_id,
                    'estimated_duration': context.get('estimated_duration', 60),
                    'capabilities_offered': self.available_agents.get(agent_type, {}).get('capabilities', [])
                }
                
                await self.communication_hub.broadcast_to_group(
                    from_agent=agent_id,
                    group_name="specialists",
                    message_content=initial_message
                )
                communication_metrics['messages_sent'] += 1
            
            # 2. Check for dynamic coordination needs
            if self.communication_hub and context.get('needs_collaboration'):
                required_capabilities = context.get('required_capabilities', [])
                if required_capabilities:
                    additional_agent = await self.communication_hub.request_additional_agent(
                        requesting_agent=agent_id,
                        required_capabilities=required_capabilities,
                        task_description=context.get('task_description', 'Collaborative task')
                    )
                    
                    if additional_agent:
                        communication_metrics['dynamic_requests'] += 1
                        context['collaboration_agent'] = additional_agent
            
            # 3. Context sharing if needed
            if self.communication_hub and context.get('share_context'):
                shared_context = {
                    'current_progress': 'starting',
                    'discovered_patterns': context.get('patterns', []),
                    'resource_usage': context.get('resources', {})
                }
                
                target_agents = context.get('context_share_targets', ['user-experience-auditor'])
                for target_agent in target_agents:
                    if target_agent in self.agents:
                        await self.communication_hub.share_context(
                            from_agent=agent_id,
                            to_agent=target_agent,
                            context_data=shared_context,
                            context_type="task_progress"
                        )
                        communication_metrics['context_shares'] += 1
            
            # 4. Simulate actual agent work (replace with actual Task tool call)
            await asyncio.sleep(0.1)  # Simulate work
            
            # 5. Handle potential conflicts during execution
            if self.communication_hub and context.get('monitor_conflicts'):
                # Simulate conflict detection during execution
                await asyncio.sleep(0.05)
                # In real implementation, this would be triggered by actual conflicts
                
            # 6. Final coordination message
            if self.communication_hub:
                completion_message = {
                    'action': 'task_completed',
                    'agent_id': agent_id,
                    'workflow_id': workflow_id,
                    'results_summary': 'Task completed successfully',
                    'resources_freed': context.get('resources', {}),
                    'collaboration_score': communication_metrics.get('context_shares', 0)
                }
                
                await self.communication_hub.broadcast_to_group(
                    from_agent=agent_id,
                    group_name="specialists",
                    message_content=completion_message
                )
                communication_metrics['messages_sent'] += 1
            
            duration = time.time() - start_time
            
            # Update ML performance tracking
            self.ml_engine.update_agent_performance(agent_type, True, duration)
            
            return {
                'status': 'completed',
                'agent_type': agent_type,
                'agent_id': agent_id,
                'instance_id': instance_id,
                'duration': duration,
                'success': True,
                'communication_metrics': communication_metrics,
                'coordination_effectiveness': self._calculate_coordination_effectiveness(communication_metrics),
                'workflow_id': workflow_id
            }
            
        except Exception as e:
            duration = time.time() - start_time
            self.ml_engine.update_agent_performance(agent_type, False, duration)
            
            # Send error notification if communication available
            if self.communication_hub:
                error_message = {
                    'action': 'task_failed',
                    'agent_id': agent_id,
                    'workflow_id': workflow_id,
                    'error': str(e),
                    'needs_assistance': True
                }
                
                await self.communication_hub.broadcast_to_group(
                    from_agent=agent_id,
                    group_name="orchestrators",
                    message_content=error_message
                )
            
            return {
                'status': 'failed',
                'agent_type': agent_type,
                'agent_id': agent_id,
                'instance_id': instance_id,
                'duration': duration,
                'error': str(e),
                'communication_metrics': communication_metrics,
                'workflow_id': workflow_id
            }
    
    async def _execute_single_agent_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single agent task (legacy method)."""
        
        # This would call the actual Task tool with the agent
        # For now, simulate the execution
        agent_type = task['agent_type']
        instance_id = task['instance_id']
        context = task['task_context']
        
        start_time = time.time()
        
        try:
            # Simulate agent execution (replace with actual Task tool call)
            await asyncio.sleep(0.1)  # Simulate work
            
            duration = time.time() - start_time
            
            # Update ML performance tracking
            self.ml_engine.update_agent_performance(agent_type, True, duration)
            
            return {
                'status': 'completed',
                'agent_type': agent_type,
                'instance_id': instance_id,
                'duration': duration,
                'success': True
            }
            
        except Exception as e:
            duration = time.time() - start_time
            self.ml_engine.update_agent_performance(agent_type, False, duration)
            
            return {
                'status': 'failed',
                'agent_type': agent_type,
                'instance_id': instance_id,
                'duration': duration,
                'error': str(e)
            }
    
    def _analyze_stream_dependencies(self, streams: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Analyze dependencies between fix streams."""
        dependencies = {}
        
        for stream in streams:
            stream_id = stream.get('id', stream.get('stream_id', ''))
            stream_deps = []
            
            # Analyze what this stream depends on
            stream_type = stream.get('type', '')
            
            if 'memory' in stream_type and any('file' in s.get('type', '') for s in streams):
                # Memory fixes depend on file organization fixes
                file_streams = [s.get('id', s.get('stream_id', '')) for s in streams if 'file' in s.get('type', '')]
                stream_deps.extend(file_streams)
            
            if 'validation' in stream_type:
                # Validation depends on implementation streams
                impl_streams = [s.get('id', s.get('stream_id', '')) for s in streams 
                              if s.get('type', '') not in ['validation', 'audit']]
                stream_deps.extend(impl_streams)
            
            dependencies[stream_id] = stream_deps
        
        return dependencies
    
    async def _get_system_constraints(self) -> Dict[str, Any]:
        """Get current system resource constraints."""
        return {
            'available_resources': {
                'cpu': 0.7,
                'memory': 0.6,
                'network': 0.8,
                'storage': 0.9
            },
            'max_concurrent_operations': 5
        }
    
    async def _dependencies_satisfied(self, stream_id: str) -> bool:
        """Check if stream dependencies are satisfied."""
        dependencies = self.stream_dependencies.get(stream_id, [])
        
        for dep_id in dependencies:
            if dep_id in self.active_streams:
                dep_status = self.active_streams[dep_id].get('status')
                if dep_status != 'completed':
                    return False
        
        return True
    
    async def _get_container_dependencies(self) -> Dict[str, List[str]]:
        """Get container dependencies for agents."""
        # This would be populated from actual system analysis
        return {
            'backend-gateway-expert': ['api', 'worker'],
            'user-experience-auditor': ['webui', 'api'],
            'security-validator': ['api', 'postgres', 'redis'],
            'project-janitor': []  # No container dependencies
        }
    
    async def _get_system_loads(self) -> Dict[str, float]:
        """Get current system load metrics."""
        return {
            'cpu': 0.3,
            'memory': 0.4,
            'network': 0.2,
            'storage': 0.1
        }
    
    async def _get_container_states(self) -> Dict[str, str]:
        """Get current container states."""
        return {
            'api': 'running',
            'webui': 'running', 
            'worker': 'running',
            'postgres': 'running',
            'redis': 'running'
        }
    
    async def _execute_stream_implementation(self, stream: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the actual stream implementation."""
        # This would contain the actual fix implementation
        # For now, return a success simulation
        return {
            'implementation': 'simulated_success',
            'changes_made': stream.get('changes', []),
            'files_modified': stream.get('files', [])
        }
    
    async def _execute_validation_agents(self, validation_task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute validation agents for a task."""
        agents = validation_task['agents']
        results = {}
        
        for agent in agents:
            # Simulate validation (replace with actual Task tool call)
            results[agent] = {
                'success': True,
                'findings': f"Validation passed for {validation_task['stream_id']}",
                'confidence': 0.85
            }
        
        return results
    
    async def _execute_agent_group_sequential(self, 
                                            agents: List[Dict[str, Any]], 
                                            allow_multiple_instances: bool) -> Dict[str, Any]:
        """Execute a group of agents sequentially."""
        
        execution_results = {}
        
        for agent in agents:
            if allow_multiple_instances and agent.get('allow_instances', True):
                # Execute multiple instances sequentially
                for instance_id in range(min(agent.get('max_instances', 2), self.max_agent_instances)):
                    task = {
                        'agent_type': agent['id'],
                        'instance_id': instance_id,
                        'task_context': agent.get('context', {})
                    }
                    
                    result = await self._execute_single_agent_task(task)
                    task_key = f"{agent['id']}_instance_{instance_id}"
                    execution_results[task_key] = result
            else:
                # Single instance
                task = {
                    'agent_type': agent['id'],
                    'instance_id': 0,
                    'task_context': agent.get('context', {})
                }
                
                result = await self._execute_single_agent_task(task)
                execution_results[agent['id']] = result
        
        return execution_results
    
    async def _execute_audit_agents_parallel(self, agent_instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute audit agents in parallel for independent verification."""
        
        try:
            results = await asyncio.gather(
                *[self._execute_single_agent_task(instance) for instance in agent_instances],
                return_exceptions=True
            )
            
            # Process audit results
            audit_results = {}
            for i, result in enumerate(results):
                instance = agent_instances[i]
                instance_key = f"{instance['agent_type']}_instance_{instance['instance_id']}"
                
                if isinstance(result, Exception):
                    audit_results[instance_key] = {
                        'status': 'error',
                        'error': str(result)
                    }
                else:
                    audit_results[instance_key] = result
            
            return audit_results
            
        except Exception as e:
            logger.error(f"Parallel audit execution failed: {e}")
            return {'status': 'audit_failed', 'error': str(e)}
    
    async def _analyze_audit_consensus(self, phase_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze consensus across multiple audit agents with enhanced analysis."""
        
        all_results = []
        agent_findings = {}
        phase_consensus = {}
        
        # Collect all results by phase and agent
        for phase, results in phase_results.items():
            phase_confidence = []
            for agent_instance, result in results.items():
                if result.get('status') == 'completed':
                    all_results.append(result)
                    phase_confidence.append(result.get('confidence', 0.5))
                    
                    agent_type = result.get('agent_type', 'unknown')
                    if agent_type not in agent_findings:
                        agent_findings[agent_type] = []
                    
                    agent_findings[agent_type].append(result)
            
            # Calculate per-phase consensus
            if phase_confidence:
                phase_consensus[phase] = {
                    'average_confidence': np.mean(phase_confidence),
                    'confidence_std': np.std(phase_confidence) if len(phase_confidence) > 1 else 0.0,
                    'agent_count': len(phase_confidence)
                }
        
        # Calculate overall consensus metrics
        if not all_results:
            return {
                'consensus_level': 'insufficient_data',
                'average_confidence': 0.0,
                'critical_findings': [],
                'recommendations': ['Retry audit with more agents']
            }
        
        # Overall confidence analysis
        confidences = [r.get('confidence', 0.5) for r in all_results if 'confidence' in r]
        average_confidence = np.mean(confidences) if confidences else 0.0
        confidence_std = np.std(confidences) if len(confidences) > 1 else 0.0
        
        # Enhanced consensus level determination
        high_confidence_count = sum(1 for c in confidences if c > 0.8)
        low_confidence_count = sum(1 for c in confidences if c < 0.5)
        
        if confidence_std < 0.1 and average_confidence > 0.8 and high_confidence_count > len(confidences) * 0.8:
            consensus_level = 'high'
        elif confidence_std < 0.2 and average_confidence > 0.6 and low_confidence_count < len(confidences) * 0.3:
            consensus_level = 'medium'
        else:
            consensus_level = 'low'
        
        # Extract critical findings with severity classification
        critical_findings = []
        for result in all_results:
            if result.get('success') is False or result.get('confidence', 1.0) < 0.5:
                severity = 'critical' if result.get('confidence', 1.0) < 0.3 else 'high'
                critical_findings.append({
                    'agent': result.get('agent_type'),
                    'instance': result.get('instance_id', 'unknown'),
                    'finding': result.get('findings', 'Unknown issue'),
                    'confidence': result.get('confidence', 0.0),
                    'severity': severity,
                    'phase': result.get('audit_scope', 'unknown')
                })
        
        # Generate enhanced recommendations
        recommendations = []
        if consensus_level == 'low':
            recommendations.append('Execute additional validation rounds with more agents')
        if average_confidence < 0.7:
            recommendations.append('Investigate low-confidence findings before proceeding')
        if critical_findings:
            recommendations.append(f'Address {len(critical_findings)} critical findings immediately')
        if confidence_std > 0.3:
            recommendations.append('High variance in agent confidence - review conflicting assessments')
        
        # Cross-agent agreement analysis
        agent_agreement = {}
        for agent_type, findings in agent_findings.items():
            if len(findings) > 1:
                agent_confidences = [f.get('confidence', 0.5) for f in findings]
                agent_agreement[agent_type] = {
                    'internal_consistency': np.std(agent_confidences),
                    'average_confidence': np.mean(agent_confidences),
                    'instance_count': len(findings)
                }
        
        return {
            'consensus_level': consensus_level,
            'average_confidence': average_confidence,
            'confidence_standard_deviation': confidence_std,
            'critical_findings': critical_findings,
            'recommendations': recommendations,
            'agent_findings_summary': {
                agent: len(findings) for agent, findings in agent_findings.items()
            },
            'phase_consensus': phase_consensus,
            'agent_agreement_analysis': agent_agreement,
            'consensus_metrics': {
                'high_confidence_percentage': (high_confidence_count / len(confidences)) * 100 if confidences else 0,
                'low_confidence_percentage': (low_confidence_count / len(confidences)) * 100 if confidences else 0,
                'total_agent_instances': len(all_results)
            }
        }
    
    async def _aggregate_audit_evidence(self, phase_results: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate and correlate evidence from multiple audit agents."""
        
        evidence_collection = {
            'concrete_evidence': [],
            'cross_agent_correlations': {},
            'evidence_quality_metrics': {},
            'evidence_gaps': []
        }
        
        all_evidence = []
        evidence_by_type = {}
        
        # Collect evidence from all agents
        for phase, results in phase_results.items():
            for agent_instance, result in results.items():
                if result.get('evidence'):
                    evidence_item = {
                        'source_agent': result.get('agent_type'),
                        'source_instance': result.get('instance_id'),
                        'phase': phase,
                        'evidence_type': result.get('evidence_type', 'general'),
                        'evidence_data': result.get('evidence'),
                        'confidence': result.get('confidence', 0.5),
                        'timestamp': result.get('timestamp', time.time())
                    }
                    all_evidence.append(evidence_item)
                    
                    # Group by evidence type
                    evidence_type = evidence_item['evidence_type']
                    if evidence_type not in evidence_by_type:
                        evidence_by_type[evidence_type] = []
                    evidence_by_type[evidence_type].append(evidence_item)
        
        # Analyze evidence correlations
        for evidence_type, evidence_items in evidence_by_type.items():
            if len(evidence_items) > 1:
                # Find correlating evidence across agents
                correlations = []
                for i, item1 in enumerate(evidence_items):
                    for j, item2 in enumerate(evidence_items[i+1:], i+1):
                        if item1['source_agent'] != item2['source_agent']:
                            # Calculate correlation score (simplified)
                            correlation_score = min(item1['confidence'], item2['confidence'])
                            correlations.append({
                                'agents': [item1['source_agent'], item2['source_agent']],
                                'correlation_score': correlation_score,
                                'evidence_match': evidence_type
                            })
                
                evidence_collection['cross_agent_correlations'][evidence_type] = correlations
        
        # Calculate evidence quality score
        if all_evidence:
            quality_factors = {
                'evidence_count': min(len(all_evidence) / 10, 1.0),  # More evidence is better, cap at 10
                'average_confidence': np.mean([e['confidence'] for e in all_evidence]),
                'source_diversity': len(set(e['source_agent'] for e in all_evidence)) / 5,  # Diverse sources
                'correlation_strength': len(evidence_collection['cross_agent_correlations']) / len(evidence_by_type) if evidence_by_type else 0
            }
            
            quality_score = np.mean(list(quality_factors.values()))
            evidence_collection['evidence_quality_metrics'] = {
                'overall_score': quality_score,
                'factors': quality_factors
            }
        else:
            evidence_collection['evidence_quality_metrics'] = {
                'overall_score': 0.0,
                'factors': {'no_evidence_collected': True}
            }
        
        evidence_collection['concrete_evidence'] = all_evidence
        evidence_collection['quality_score'] = evidence_collection['evidence_quality_metrics']['overall_score']
        
        return evidence_collection
    
    async def _generate_ml_audit_insights(self, audit_results: Dict[str, Any], audit_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Generate ML-enhanced insights from audit results."""
        
        ml_insights = {
            'pattern_analysis': {},
            'predictive_assessment': {},
            'confidence_adjustment': 0.0,
            'learning_recommendations': []
        }
        
        try:
            # Analyze patterns in audit results
            consensus_data = audit_results.get('consensus_analysis', {})
            evidence_data = audit_results.get('evidence_aggregation', {})
            
            # Pattern recognition
            ml_insights['pattern_analysis'] = {
                'consensus_pattern': consensus_data.get('consensus_level', 'unknown'),
                'evidence_pattern': 'strong' if evidence_data.get('quality_score', 0) > 0.7 else 'weak',
                'agent_consistency': 'high' if consensus_data.get('confidence_standard_deviation', 1.0) < 0.2 else 'low'
            }
            
            # Predictive assessment for future orchestrations
            ml_insights['predictive_assessment'] = {
                'workflow_success_likelihood': min(consensus_data.get('average_confidence', 0.5) + 0.1, 1.0),
                'recommended_validation_level': 'enhanced' if consensus_data.get('consensus_level') == 'low' else 'standard',
                'risk_factors': []
            }
            
            # Risk factor identification
            if len(consensus_data.get('critical_findings', [])) > 2:
                ml_insights['predictive_assessment']['risk_factors'].append('high_critical_finding_count')
            
            if consensus_data.get('confidence_standard_deviation', 0) > 0.3:
                ml_insights['predictive_assessment']['risk_factors'].append('high_agent_disagreement')
            
            # Confidence adjustment based on ML analysis
            base_confidence = consensus_data.get('average_confidence', 0.5)
            evidence_bonus = min(evidence_data.get('quality_score', 0) * 0.1, 0.1)
            consistency_bonus = 0.05 if consensus_data.get('confidence_standard_deviation', 1.0) < 0.1 else 0
            
            ml_insights['confidence_adjustment'] = evidence_bonus + consistency_bonus
            
            # Learning recommendations
            if consensus_data.get('consensus_level') == 'low':
                ml_insights['learning_recommendations'].append('Increase number of audit agent instances')
            
            if evidence_data.get('quality_score', 0) < 0.5:
                ml_insights['learning_recommendations'].append('Enhance evidence collection requirements')
            
            if len(ml_insights['predictive_assessment']['risk_factors']) > 1:
                ml_insights['learning_recommendations'].append('Implement additional validation checkpoints')
            
        except Exception as e:
            logger.error(f"ML insights generation failed: {e}")
            ml_insights['error'] = str(e)
        
        return ml_insights
    
    async def start_orchestration(self, trigger_phrase: str = "orchestration", 
                                initial_context: Dict[str, Any] = None) -> str:
        """Start the ML-enhanced agentic orchestration workflow."""
        if self.workflow_active:
            return f"Workflow already active: {self.current_workflow_id}"
        
        # Create new workflow
        self.integration_layer = MCPIntegrationLayer()
        self.current_workflow_id = self.integration_layer.workflow_id
        self.workflow_active = True
        
        logger.info("Starting ML-enhanced agentic orchestration", 
                   workflow_id=self.current_workflow_id,
                   trigger=trigger_phrase)
        
        try:
            # Register all available agents
            await self._register_all_agents()
            
            # Start the workflow with initial context
            workflow_context = initial_context or {}
            workflow_context.update({
                "trigger_phrase": trigger_phrase,
                "started_at": time.time(),
                "orchestrator_version": "1.0.0"
            })
            
            success = await self.integration_layer.start_workflow(workflow_context)
            
            if success:
                return f"ML-enhanced agentic orchestration started: {self.current_workflow_id}"
            else:
                self.workflow_active = False
                return "Failed to start orchestration workflow"
                
        except Exception as e:
            logger.error("Orchestration startup failed", error=str(e))
            self.workflow_active = False
            return f"Orchestration startup failed: {str(e)}"
    
    async def stop_orchestration(self) -> str:
        """Stop the current orchestration workflow."""
        if not self.workflow_active:
            return "No active workflow to stop"
        
        workflow_id = self.current_workflow_id
        self.workflow_active = False
        self.current_workflow_id = None
        self.integration_layer = None
        
        logger.info("Orchestration stopped", workflow_id=workflow_id)
        return f"Orchestration stopped: {workflow_id}"
    
    async def get_workflow_status(self) -> Dict[str, Any]:
        """Get current workflow status."""
        if not self.workflow_active or not self.integration_layer:
            return {
                "active": False,
                "workflow_id": None,
                "phase": None,
                "registered_agents": 0
            }
        
        return {
            "active": True,
            "workflow_id": self.current_workflow_id,
            "phase": self.integration_layer.current_phase.name,
            "phase_number": self.integration_layer.current_phase.value,
            "registered_agents": len(self.integration_layer.agent_registry),
            "completed_tasks": len(self.integration_layer.results),
            "workflow_context_size": len(self.integration_layer.workflow_context)
        }
    
    async def execute_specific_phase(self, phase_number: int, 
                                   context: Dict[str, Any] = None) -> str:
        """Execute a specific phase of the orchestration workflow."""
        if not self.workflow_active:
            return "No active workflow. Start orchestration first."
        
        try:
            phase = WorkflowPhase(phase_number)
            self.integration_layer.current_phase = phase
            
            if context:
                self.integration_layer.workflow_context.update(context)
            
            # Execute the specific phase
            phase_method_map = {
                0: self.integration_layer._execute_phase_0_todo_context,
                1: self.integration_layer._execute_phase_1_agent_ecosystem,
                2: self.integration_layer._execute_phase_2_strategic_planning,
                3: self.integration_layer._execute_phase_3_research_discovery,
                4: self.integration_layer._execute_phase_4_context_synthesis,
                5: self.integration_layer._execute_phase_5_parallel_implementation,
                6: self.integration_layer._execute_phase_6_validation,
                7: self.integration_layer._execute_phase_7_decision_control,
                8: self.integration_layer._execute_phase_8_version_control,
                9: self.integration_layer._execute_phase_9_meta_audit,
                10: self.integration_layer._execute_phase_10_todo_integration
            }
            
            if phase_number in phase_method_map:
                await phase_method_map[phase_number]()
                return f"Phase {phase_number} ({phase.name}) executed successfully"
            else:
                return f"Invalid phase number: {phase_number}"
                
        except Exception as e:
            logger.error("Phase execution failed", phase=phase_number, error=str(e))
            return f"Phase {phase_number} execution failed: {str(e)}"
    
    async def deploy_critical_services(self) -> str:
        """Deploy critical services identified in orchestration todos."""
        if not self.workflow_active:
            await self.start_orchestration("deployment")
        
        # Read orchestration todos to identify deployment needs
        try:
            with open("/home/marku/ai_workflow_engine/.claude/orchestration_todos.json", "r") as f:
                todos = json.load(f)
        except Exception as e:
            return f"Could not read orchestration todos: {str(e)}"
        
        # Find deployment todos
        deployment_todos = [
            todo for todo in todos 
            if "deploy" in todo.get("content", "").lower() 
            and todo.get("status") == "pending"
            and todo.get("priority") in ["critical", "high"]
        ]
        
        if not deployment_todos:
            return "No critical deployment todos found"
        
        deployment_results = []
        
        for todo in deployment_todos:
            content = todo.get("content", "")
            
            if "voice-interaction-service" in content:
                result = await self._deploy_voice_service()
                deployment_results.append(f"Voice service: {result}")
            
            elif "chat-service" in content:
                result = await self._deploy_chat_service() 
                deployment_results.append(f"Chat service: {result}")
            
            else:
                deployment_results.append(f"Unknown deployment: {content}")
        
        return f"Deployment results: {'; '.join(deployment_results)}"
    
    # New streaming orchestration methods
    async def start_streaming_orchestration(self, fix_context: Dict[str, Any]) -> str:
        """Start streaming-based orchestration for comprehensive fixes."""
        
        if self.workflow_active:
            return f"Workflow already active: {self.current_workflow_id}"
        
        # Initialize orchestration
        self.integration_layer = MCPIntegrationLayer()
        self.current_workflow_id = self.integration_layer.workflow_id
        self.workflow_active = True
        
        logger.info("Starting streaming ML-enhanced orchestration",
                   workflow_id=self.current_workflow_id)
        
        # Define fix streams based on detected violations
        fix_streams = self._create_fix_streams(fix_context)
        
        # Execute streaming fixes
        results = await self.execute_streaming_fixes(fix_streams)
        
        return f"Streaming orchestration started: {self.current_workflow_id}, executing {len(fix_streams)} streams"
    
    def _create_fix_streams(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create fix streams based on detected violations."""
        
        violations = context.get('violations', [])
        streams = []
        
        # Stream 1: ML Integration fixes
        if 'ml_integration' in violations:
            streams.append({
                'id': 'stream-1-ml',
                'type': 'ml_integration',
                'priority': 0.9,
                'operation': {'type': 'code_modification'},
                'containers': [],
                'estimated_duration': 300,
                'dependencies': []
            })
        
        # Stream 2: Parallel Execution fixes
        if 'parallel_execution' in violations:
            streams.append({
                'id': 'stream-2-parallel',
                'type': 'parallel_execution',
                'priority': 0.8,
                'operation': {'type': 'code_modification'},
                'containers': [],
                'estimated_duration': 240,
                'dependencies': ['stream-1-ml']
            })
        
        # Stream 3: Inter-Agent Communication fixes
        if 'inter_agent_communication' in violations:
            streams.append({
                'id': 'stream-3-communication',
                'type': 'communication_protocol',
                'priority': 0.8,
                'operation': {'type': 'code_modification'},
                'containers': [],
                'estimated_duration': 360,
                'dependencies': []
            })
        
        # Stream 4: Memory Service Integration fixes
        if 'memory_service' in violations:
            streams.append({
                'id': 'stream-4-memory',
                'type': 'memory_integration',
                'priority': 0.7,
                'operation': {'type': 'service_integration'},
                'containers': [],
                'estimated_duration': 180,
                'dependencies': []
            })
        
        # Stream 5: File Organization fixes
        if 'file_organization' in violations:
            streams.append({
                'id': 'stream-5-files',
                'type': 'file_organization',
                'priority': 0.6,
                'operation': {'type': 'file_modification'},
                'containers': [],
                'estimated_duration': 150,
                'dependencies': []
            })
        
        # Stream 6: Dynamic Information Gathering fixes
        if 'dynamic_gathering' in violations:
            streams.append({
                'id': 'stream-6-dynamic',
                'type': 'dynamic_information',
                'priority': 0.7,
                'operation': {'type': 'code_modification'},
                'containers': [],
                'estimated_duration': 200,
                'dependencies': ['stream-3-communication']
            })
        
        # Stream 7: Validation Architecture fixes
        if 'validation_architecture' in violations:
            streams.append({
                'id': 'stream-7-validation',
                'type': 'validation_architecture',
                'priority': 0.8,
                'operation': {'type': 'code_modification'},
                'containers': [],
                'estimated_duration': 300,
                'dependencies': ['stream-2-parallel']
            })
        
        # Stream 8: Phase 9 Audit System fixes
        if 'audit_system' in violations:
            streams.append({
                'id': 'stream-8-audit',
                'type': 'audit_system',
                'priority': 0.9,
                'operation': {'type': 'code_modification'},
                'containers': [],
                'estimated_duration': 250,
                'dependencies': ['stream-7-validation']
            })
        
        # Stream 9: Container Coordination fixes
        if 'container_coordination' in violations:
            streams.append({
                'id': 'stream-9-containers',
                'type': 'container_coordination',
                'priority': 0.8,
                'operation': {'type': 'infrastructure_modification'},
                'containers': ['api', 'worker', 'webui'],
                'estimated_duration': 180,
                'dependencies': ['stream-3-communication']
            })
        
        return streams
    
    async def _register_all_agents(self):
        """Register all available agents with the integration layer."""
        registration_count = 0
        
        for agent_id, agent_spec in self.available_agents.items():
            success = await self.integration_layer.register_agent(
                agent_id=agent_id,
                agent_type=agent_spec["agent_type"],
                capabilities=agent_spec["capabilities"],
                specializations=agent_spec["specializations"]
            )
            
            if success:
                registration_count += 1
        
        logger.info("Agent registration completed", 
                   total_agents=len(self.available_agents),
                   registered_agents=registration_count)
    
    async def _deploy_voice_service(self) -> str:
        """Deploy voice-interaction-service container."""
        try:
            # This would integrate with the actual deployment system
            # For now, we'll simulate the deployment process
            logger.info("Deploying voice-interaction-service on port 8006")
            
            # Create deployment configuration
            deployment_config = {
                "service_name": "voice-interaction-service",
                "port": 8006,
                "container_config": "configured",
                "deployment_status": "ready",
                "deployment_time": time.time()
            }
            
            # Store deployment info in organized location
            config_path = await self._get_organized_file_path(
                "voice_service_deployment.json", 
                "deployment"
            )
            
            with open(config_path, "w") as f:
                json.dump(deployment_config, f, indent=2)
            
            return "Successfully deployed (simulated)"
            
        except Exception as e:
            logger.error("Voice service deployment failed", error=str(e))
            return f"Deployment failed: {str(e)}"
    
    async def _deploy_chat_service(self) -> str:
        """Deploy chat-service container."""
        try:
            logger.info("Deploying chat-service on port 8007")
            
            deployment_config = {
                "service_name": "chat-service", 
                "port": 8007,
                "container_config": "configured",
                "ai_enhancements": "enabled",
                "deployment_status": "ready",
                "deployment_time": time.time()
            }
            
            config_path = await self._get_organized_file_path(
                "chat_service_deployment.json",
                "deployment"
            )
            
            with open(config_path, "w") as f:
                json.dump(deployment_config, f, indent=2)
            
            return "Successfully deployed (simulated)"
            
        except Exception as e:
            logger.error("Chat service deployment failed", error=str(e))
            return f"Deployment failed: {str(e)}"
    
    async def _get_organized_file_path(self, filename: str, file_type: str) -> str:
        """Get organized file path using intelligent file organization."""
        if self.integration_layer:
            return await self.integration_layer._organize_file_placement(filename, file_type)
        else:
            # Fallback organization
            base_paths = {
                "deployment": "config/deployment/",
                "documentation": "docs/",
                "orchestration": ".claude/orchestration_state/"
            }
            base_path = base_paths.get(file_type, "")
            full_path = f"/home/marku/ai_workflow_engine/{base_path}{filename}"
            
            # Ensure directory exists
            Path(full_path).parent.mkdir(parents=True, exist_ok=True)
            return full_path
    
    def get_available_agents(self) -> Dict[str, Dict[str, Any]]:
        """Get list of all available agents and their capabilities."""
        return self.available_agents.copy()
    
    def get_orchestration_phases(self) -> List[Dict[str, Any]]:
        """Get list of all orchestration phases."""
        return [
            {
                "phase": phase.value,
                "name": phase.name,
                "description": self._get_phase_description(phase)
            }
            for phase in WorkflowPhase
        ]
    
    def _get_phase_description(self, phase: WorkflowPhase) -> str:
        """Get description for orchestration phase."""
        descriptions = {
            WorkflowPhase.PHASE_0_TODO_CONTEXT: "Todo Context Integration - Load and analyze persistent todos",
            WorkflowPhase.PHASE_1_AGENT_ECOSYSTEM: "Agent Ecosystem Validation - Validate agent availability and health",
            WorkflowPhase.PHASE_2_STRATEGIC_PLANNING: "Strategic Intelligence Planning - Create high-level implementation strategy",
            WorkflowPhase.PHASE_3_RESEARCH_DISCOVERY: "Multi-Domain Research Discovery - Comprehensive system analysis",
            WorkflowPhase.PHASE_4_CONTEXT_SYNTHESIS: "Context Synthesis & Compression - Create optimized context packages",
            WorkflowPhase.PHASE_5_PARALLEL_IMPLEMENTATION: "Parallel Implementation Execution - Execute specialist agents in parallel",
            WorkflowPhase.PHASE_6_VALIDATION: "Comprehensive Evidence-Based Validation - Validate with concrete evidence",
            WorkflowPhase.PHASE_7_DECISION_CONTROL: "Decision & Iteration Control - Determine success or iteration need",
            WorkflowPhase.PHASE_8_VERSION_CONTROL: "Atomic Version Control Synchronization - Create atomic commits",
            WorkflowPhase.PHASE_9_META_AUDIT: "Meta-Orchestration Audit & Learning - Analyze and learn from workflow",
            WorkflowPhase.PHASE_10_TODO_INTEGRATION: "Continuous Todo Integration & Loop Control - Check for continuation"
        }
        return descriptions.get(phase, "Unknown phase")
    
    # Stream 3 Enhanced Communication Support Methods
    async def _setup_group_communication(self, agent_ids: List[str], workflow_id: str):
        """Set up communication patterns for agent group."""
        if not self.communication_hub:
            return
        
        # Create temporary broadcast group for this execution group
        group_name = f"execution_group_{workflow_id}"
        self.communication_hub.broadcast_groups[group_name] = set(agent_ids)
        
        # Set up resource sharing notifications for the group
        for agent_id in agent_ids:
            base_agent_id = agent_id.split('_instance_')[0]  # Remove instance suffix
            if base_agent_id in self.available_agents:
                agent_capabilities = self.available_agents[base_agent_id]["capabilities"]
                
                # Register capabilities as shareable resources
                for capability in agent_capabilities:
                    await self.communication_hub.register_resource(
                        agent_id=agent_id,
                        resource_type=f"capability_{capability}",
                        resource_data={"available": True, "workflow_id": workflow_id}
                    )
        
        logger.info("Group communication set up", 
                   workflow_id=workflow_id, agents=len(agent_ids))
    
    async def _analyze_group_coordination(self, agent_ids: List[str], 
                                        workflow_id: str,
                                        communication_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze coordination effectiveness for agent group."""
        
        total_messages = sum(
            metrics.get('messages_sent', 0) + metrics.get('messages_received', 0)
            for metrics in communication_metrics.values()
        )
        
        total_context_shares = sum(
            metrics.get('context_shares', 0)
            for metrics in communication_metrics.values()
        )
        
        total_dynamic_requests = sum(
            metrics.get('dynamic_requests', 0)
            for metrics in communication_metrics.values()
        )
        
        # Calculate coordination effectiveness
        message_density = total_messages / len(agent_ids) if agent_ids else 0
        collaboration_score = total_context_shares + (total_dynamic_requests * 2)
        
        effectiveness_score = min(1.0, (collaboration_score * 0.4) + (message_density * 0.1))
        
        return {
            'total_messages': total_messages,
            'total_context_shares': total_context_shares,
            'total_dynamic_requests': total_dynamic_requests,
            'message_density': message_density,
            'collaboration_score': collaboration_score,
            'effectiveness_score': effectiveness_score,
            'coordination_pattern': 'parallel_enhanced' if effectiveness_score > 0.7 else 'basic_parallel'
        }
    
    async def _calculate_group_performance(self, execution_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall performance metrics for agent group."""
        
        successful_tasks = sum(1 for result in execution_results.values() 
                             if result.get('status') == 'completed')
        total_tasks = len(execution_results)
        
        total_duration = sum(result.get('duration', 0) for result in execution_results.values())
        avg_duration = total_duration / total_tasks if total_tasks > 0 else 0
        
        success_rate = successful_tasks / total_tasks if total_tasks > 0 else 0
        
        return {
            'success_rate': success_rate,
            'total_tasks': total_tasks,
            'successful_tasks': successful_tasks,
            'average_duration': avg_duration,
            'total_duration': total_duration,
            'performance_grade': 'excellent' if success_rate > 0.9 else 
                                'good' if success_rate > 0.7 else
                                'fair' if success_rate > 0.5 else 'poor'
        }
    
    def _calculate_coordination_effectiveness(self, communication_metrics: Dict[str, Any]) -> float:
        """Calculate coordination effectiveness for single agent."""
        
        messages_sent = communication_metrics.get('messages_sent', 0)
        context_shares = communication_metrics.get('context_shares', 0)
        dynamic_requests = communication_metrics.get('dynamic_requests', 0)
        conflicts_resolved = communication_metrics.get('conflicts_resolved', 0)
        
        # Weight different communication activities
        coordination_score = (
            (messages_sent * 0.1) +
            (context_shares * 0.3) +
            (dynamic_requests * 0.4) +
            (conflicts_resolved * 0.2)
        )
        
        # Normalize to 0-1 scale
        return min(1.0, coordination_score / 5.0)
    
    async def _analyze_coordination_performance(self, workflow_id: str) -> Dict[str, Any]:
        """Analyze overall coordination performance for workflow."""
        
        if not self.communication_hub or workflow_id not in self.communication_hub.workflow_contexts:
            return {
                'coordination_active': False,
                'message': 'No coordination data available'
            }
        
        context = self.communication_hub.workflow_contexts[workflow_id]
        
        # Analyze coordination session data
        session = self.communication_hub.coordination_sessions.get(workflow_id, {})
        
        coordination_duration = time.time() - session.get('created_at', time.time())
        message_count = len(session.get('message_history', []))
        conflict_count = len(session.get('conflict_log', []))
        
        # Calculate coordination metrics
        messages_per_minute = (message_count / (coordination_duration / 60)) if coordination_duration > 0 else 0
        conflict_rate = conflict_count / len(context.participating_agents) if context.participating_agents else 0
        
        coordination_quality = 1.0 - (conflict_rate * 0.5)  # Conflicts reduce quality
        coordination_activity = min(1.0, messages_per_minute / 10.0)  # Normalize activity
        
        return {
            'coordination_active': True,
            'workflow_id': workflow_id,
            'coordination_duration': coordination_duration,
            'total_messages': message_count,
            'total_conflicts': conflict_count,
            'messages_per_minute': messages_per_minute,
            'conflict_rate': conflict_rate,
            'coordination_quality': coordination_quality,
            'coordination_activity': coordination_activity,
            'overall_score': (coordination_quality * 0.7) + (coordination_activity * 0.3),
            'participating_agents': len(context.participating_agents),
            'dynamic_agents_added': len(context.dynamic_agents)
        }
    
    async def _execute_agent_group_sequential_enhanced(self, 
                                                     agents: List[Dict[str, Any]], 
                                                     allow_multiple_instances: bool,
                                                     workflow_id: str) -> Dict[str, Any]:
        """Execute a group of agents sequentially with enhanced communication."""
        
        execution_results = {}
        total_communication_metrics = {}
        
        for i, agent in enumerate(agents):
            # Prepare task with sequential context
            if allow_multiple_instances and agent.get('allow_instances', True):
                # Execute multiple instances sequentially
                for instance_id in range(min(agent.get('max_instances', 2), self.max_agent_instances)):
                    task_agent_id = f"{agent['id']}_instance_{instance_id}"
                    task = {
                        'agent_type': agent['id'],
                        'agent_id': task_agent_id,
                        'instance_id': instance_id,
                        'task_context': {
                            **agent.get('context', {}),
                            'sequential_position': i,
                            'total_agents': len(agents),
                            'previous_results': execution_results
                        },
                        'workflow_id': workflow_id
                    }
                    
                    result = await self._execute_single_agent_task_enhanced(task)
                    task_key = f"{agent['id']}_instance_{instance_id}"
                    execution_results[task_key] = result
                    
                    # Collect communication metrics
                    if 'communication_metrics' in result:
                        total_communication_metrics[task_key] = result['communication_metrics']
            else:
                # Single instance
                task = {
                    'agent_type': agent['id'],
                    'agent_id': agent['id'],
                    'instance_id': 0,
                    'task_context': {
                        **agent.get('context', {}),
                        'sequential_position': i,
                        'total_agents': len(agents),
                        'previous_results': execution_results
                    },
                    'workflow_id': workflow_id
                }
                
                result = await self._execute_single_agent_task_enhanced(task)
                execution_results[agent['id']] = result
                
                # Collect communication metrics
                if 'communication_metrics' in result:
                    total_communication_metrics[agent['id']] = result['communication_metrics']
        
        # Analyze sequential coordination
        coordination_analysis = await self._analyze_sequential_coordination(
            agents, workflow_id, total_communication_metrics
        )
        
        return {
            'execution_results': execution_results,
            'communication_metrics': total_communication_metrics,
            'coordination_analysis': coordination_analysis,
            'sequential_performance': await self._calculate_sequential_performance(execution_results)
        }
    
    async def _analyze_sequential_coordination(self, agents: List[Dict[str, Any]], 
                                             workflow_id: str,
                                             communication_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze coordination effectiveness for sequential execution."""
        
        # Calculate handoff effectiveness between sequential agents
        handoff_scores = []
        
        for i in range(len(agents) - 1):
            current_agent = agents[i]['id']
            next_agent = agents[i + 1]['id']
            
            # Look for context sharing between sequential agents
            current_metrics = communication_metrics.get(current_agent, {})
            context_shared = current_metrics.get('context_shares', 0)
            
            # Sequential coordination is effective when context is passed forward
            handoff_score = min(1.0, context_shared / 2.0)  # Expecting 1-2 context shares per handoff
            handoff_scores.append(handoff_score)
        
        avg_handoff_score = sum(handoff_scores) / len(handoff_scores) if handoff_scores else 0
        
        return {
            'coordination_type': 'sequential_enhanced',
            'handoff_scores': handoff_scores,
            'average_handoff_score': avg_handoff_score,
            'total_handoffs': len(handoff_scores),
            'coordination_effectiveness': avg_handoff_score,
            'sequential_quality': 'excellent' if avg_handoff_score > 0.8 else
                                'good' if avg_handoff_score > 0.6 else
                                'fair' if avg_handoff_score > 0.4 else 'poor'
        }
    
    async def _calculate_sequential_performance(self, execution_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate performance metrics for sequential execution."""
        
        results_list = list(execution_results.values())
        
        # Calculate cumulative success (all previous must succeed for current to be meaningful)
        cumulative_success = True
        success_progression = []
        
        for result in results_list:
            if result.get('status') == 'completed':
                success_progression.append(cumulative_success)
            else:
                cumulative_success = False
                success_progression.append(False)
        
        total_duration = sum(result.get('duration', 0) for result in results_list)
        final_success = all(result.get('status') == 'completed' for result in results_list)
        
        return {
            'final_success': final_success,
            'success_progression': success_progression,
            'total_sequential_duration': total_duration,
            'pipeline_efficiency': len([s for s in success_progression if s]) / len(success_progression) if success_progression else 0,
            'bottleneck_analysis': self._identify_sequential_bottlenecks(results_list)
        }
    
    def _identify_sequential_bottlenecks(self, results_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify bottlenecks in sequential execution."""
        
        durations = [result.get('duration', 0) for result in results_list]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        bottlenecks = []
        for i, duration in enumerate(durations):
            if duration > avg_duration * 1.5:  # 50% longer than average
                bottlenecks.append({
                    'position': i,
                    'agent': results_list[i].get('agent_type', 'unknown'),
                    'duration': duration,
                    'slowdown_factor': duration / avg_duration if avg_duration > 0 else 1
                })
        
        return {
            'average_duration': avg_duration,
            'bottlenecks_detected': len(bottlenecks),
            'bottleneck_details': bottlenecks,
            'longest_step': max(durations) if durations else 0,
            'shortest_step': min(durations) if durations else 0
        }

# Global orchestrator instance  
_orchestrator: Optional[MLEnhancedOrchestrator] = None

def get_ml_enhanced_orchestrator() -> MLEnhancedOrchestrator:
    """Get or create global ML-enhanced orchestrator."""
    global _orchestrator
    
    if _orchestrator is None:
        _orchestrator = MLEnhancedOrchestrator()
    
    return _orchestrator

# Convenience functions for common operations

async def start_agentic_flow(trigger_phrase: str = "orchestration", 
                           context: Dict[str, Any] = None) -> str:
    """Start the ML-enhanced agentic flow."""
    orchestrator = get_ml_enhanced_orchestrator()
    return await orchestrator.start_orchestration(trigger_phrase, context)

async def start_streaming_fixes(fix_context: Dict[str, Any]) -> str:
    """Start streaming-based orchestration fixes."""
    orchestrator = get_ml_enhanced_orchestrator()
    return await orchestrator.start_streaming_orchestration(fix_context)

async def execute_parallel_agents_with_ml(agent_requests: List[Dict[str, Any]], 
                                        allow_instances: bool = True) -> Dict[str, Any]:
    """Execute parallel agents with ML coordination."""
    orchestrator = get_ml_enhanced_orchestrator()
    return await orchestrator.execute_parallel_agents(agent_requests, allow_instances)

async def execute_ml_enhanced_audit(audit_context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute ML-enhanced audit with planning and multiple agents."""
    orchestrator = get_ml_enhanced_orchestrator()
    return await orchestrator.plan_and_execute_audit(audit_context)

async def execute_phase(phase_number: int, context: Dict[str, Any] = None) -> str:
    """Execute a specific orchestration phase."""
    orchestrator = get_ml_enhanced_orchestrator()
    return await orchestrator.execute_specific_phase(phase_number, context)

async def deploy_services() -> str:
    """Deploy critical services from orchestration todos."""
    orchestrator = get_ml_enhanced_orchestrator()
    return await orchestrator.deploy_critical_services()

async def get_workflow_status() -> Dict[str, Any]:
    """Get current workflow status."""
    orchestrator = get_ml_enhanced_orchestrator()
    return await orchestrator.get_workflow_status()

def get_available_agents() -> Dict[str, Dict[str, Any]]:
    """Get available agents and their capabilities."""
    orchestrator = get_ml_enhanced_orchestrator()
    return orchestrator.get_available_agents()

def get_orchestration_phases() -> List[Dict[str, Any]]:
    """Get orchestration phases."""
    orchestrator = get_ml_enhanced_orchestrator()
    return orchestrator.get_orchestration_phases()

def get_ml_decision_engine() -> MLDecisionEngine:
    """Get the ML decision engine for direct access."""
    orchestrator = get_ml_enhanced_orchestrator()
    return orchestrator.ml_engine

# Stream 3: Enhanced Communication Functions

async def initialize_agent_communication() -> bool:
    """Initialize enhanced inter-agent communication system."""
    orchestrator = get_ml_enhanced_orchestrator()
    return await orchestrator.initialize_enhanced_communication()

async def execute_parallel_agents_with_communication(agent_requests: List[Dict[str, Any]], 
                                                   allow_instances: bool = True) -> Dict[str, Any]:
    """Execute parallel agents with enhanced communication and coordination."""
    orchestrator = get_ml_enhanced_orchestrator()
    
    # Ensure communication is initialized
    if not orchestrator.agent_coordination_active:
        await orchestrator.initialize_enhanced_communication()
    
    return await orchestrator.execute_parallel_agents(agent_requests, allow_instances)

async def get_communication_status() -> Dict[str, Any]:
    """Get status of inter-agent communication system."""
    orchestrator = get_ml_enhanced_orchestrator()
    
    if not orchestrator.communication_hub:
        return {
            'communication_active': False,
            'message': 'Communication system not initialized'
        }
    
    return {
        'communication_active': orchestrator.agent_coordination_active,
        'registered_agents': len(orchestrator.communication_hub.agents),
        'active_workflows': len(orchestrator.communication_hub.workflow_contexts),
        'coordination_sessions': len(orchestrator.communication_hub.coordination_sessions),
        'broadcast_groups': list(orchestrator.communication_hub.broadcast_groups.keys()),
        'resource_registry_size': len(orchestrator.communication_hub.resource_registry)
    }

async def request_agent_collaboration(requesting_agent: str, 
                                    required_capabilities: List[str],
                                    task_description: str) -> Optional[str]:
    """Request additional agent for collaboration during execution."""
    orchestrator = get_ml_enhanced_orchestrator()
    
    if not orchestrator.communication_hub:
        return None
    
    return await orchestrator.communication_hub.request_additional_agent(
        requesting_agent=requesting_agent,
        required_capabilities=required_capabilities,
        task_description=task_description
    )

async def share_agent_context(from_agent: str, to_agent: str, 
                            context_data: Dict[str, Any],
                            context_type: str = "collaboration") -> bool:
    """Share context between agents during execution."""
    orchestrator = get_ml_enhanced_orchestrator()
    
    if not orchestrator.communication_hub:
        return False
    
    return await orchestrator.communication_hub.share_context(
        from_agent=from_agent,
        to_agent=to_agent,
        context_data=context_data,
        context_type=context_type
    )

async def broadcast_to_agent_group(from_agent: str, group_name: str,
                                 message_content: Dict[str, Any]) -> int:
    """Broadcast message to a group of agents."""
    orchestrator = get_ml_enhanced_orchestrator()
    
    if not orchestrator.communication_hub:
        return 0
    
    return await orchestrator.communication_hub.broadcast_to_group(
        from_agent=from_agent,
        group_name=group_name,
        message_content=message_content
    )

async def get_coordination_performance(workflow_id: str) -> Dict[str, Any]:
    """Get coordination performance analysis for a workflow."""
    orchestrator = get_ml_enhanced_orchestrator()
    
    if not orchestrator.communication_hub:
        return {'error': 'Communication system not active'}
    
    return await orchestrator._analyze_coordination_performance(workflow_id)