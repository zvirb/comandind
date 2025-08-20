#!/usr/bin/env python3
"""
Enhanced Coordination Metadata Standardization Framework
Intelligent Cross-Agent Coordination with Standardized Metadata Protocols

AIWFE Context Optimization Implementation
Version: 2.0_enhanced | Date: 2025-08-14
"""

import json
import time
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path

class CoordinationPriority(Enum):
    """Coordination priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    BACKGROUND = "background"

class ExecutionPhase(Enum):
    """Orchestration execution phases"""
    PHASE_0_TODO_CONTEXT = "phase_0_todo_context"
    PHASE_1_ECOSYSTEM_VALIDATION = "phase_1_ecosystem_validation"  
    PHASE_2_STRATEGIC_PLANNING = "phase_2_strategic_planning"
    PHASE_3_RESEARCH_DISCOVERY = "phase_3_research_discovery"
    PHASE_4_CONTEXT_SYNTHESIS = "phase_4_context_synthesis"
    PHASE_5_PARALLEL_IMPLEMENTATION = "phase_5_parallel_implementation"
    PHASE_6_VALIDATION = "phase_6_validation"
    PHASE_7_ITERATION_CONTROL = "phase_7_iteration_control"
    PHASE_8_VERSION_CONTROL = "phase_8_version_control"
    PHASE_9_META_AUDIT = "phase_9_meta_audit"

class CoordinationStatus(Enum):
    """Coordination status indicators"""
    INITIALIZED = "initialized"
    IN_PROGRESS = "in_progress"
    WAITING_DEPENDENCY = "waiting_dependency"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"

@dataclass
class AgentCapability:
    """Agent capability specification"""
    capability_id: str
    capability_name: str
    domain_expertise: List[str]
    tool_requirements: List[str]
    input_formats: List[str]
    output_formats: List[str]
    performance_metrics: Dict[str, float]
    resource_requirements: Dict[str, Any]

@dataclass
class CoordinationDependency:
    """Coordination dependency specification"""
    dependency_id: str
    source_agent: str
    target_agent: str
    dependency_type: str  # "data", "completion", "resource", "validation"
    required_outputs: List[str]
    timing_constraints: Dict[str, Any]
    priority_level: CoordinationPriority
    resolution_strategy: str

@dataclass
class ResourceAllocation:
    """Resource allocation specification"""
    allocation_id: str
    resource_type: str  # "computational", "memory", "storage", "network"
    allocated_amount: float
    allocation_unit: str
    allocation_duration: float
    sharing_policy: str
    optimization_hints: List[str]

@dataclass
class ValidationCriteria:
    """Validation criteria for coordination outcomes"""
    criteria_id: str
    validation_type: str  # "functional", "performance", "security", "integration"
    success_metrics: Dict[str, float]
    failure_thresholds: Dict[str, float]
    validation_methods: List[str]
    evidence_requirements: List[str]
    automation_level: str  # "manual", "semi_automated", "automated"

@dataclass
class IntelligenceMetadata:
    """AI and ML intelligence integration metadata"""
    intelligence_features: List[str]
    prediction_models: Dict[str, Any]
    automation_level: float
    learning_integration: bool
    adaptation_capabilities: List[str]
    feedback_loops: List[str]
    optimization_algorithms: List[str]

@dataclass
class CoordinationMetadata:
    """Comprehensive coordination metadata specification"""
    
    # Core Identification
    coordination_id: str
    package_id: str
    agent_target: str
    domain: str
    execution_phase: ExecutionPhase
    creation_timestamp: float
    last_updated: float
    
    # Agent and Capability Information
    agent_capabilities: List[AgentCapability]
    required_tools: List[str]
    resource_allocations: List[ResourceAllocation]
    
    # Coordination Dependencies
    dependencies: List[CoordinationDependency]
    coordination_status: CoordinationStatus
    parallel_execution_support: bool
    cross_stream_coordination: bool
    
    # Token and Performance Management
    token_allocation: int
    actual_token_usage: int
    compression_applied: bool
    optimization_strategy: str
    performance_targets: Dict[str, float]
    
    # Validation and Quality Assurance
    validation_criteria: List[ValidationCriteria]
    evidence_requirements: List[str]
    quality_gates: Dict[str, float]
    success_metrics: Dict[str, Any]
    
    # Intelligence and Automation
    intelligence_metadata: IntelligenceMetadata
    automation_features: List[str]
    predictive_capabilities: List[str]
    
    # Execution Control
    priority_level: CoordinationPriority
    timeout_constraints: Dict[str, float]
    retry_policies: Dict[str, Any]
    fallback_strategies: List[str]
    
    # Context and State Management
    context_version: str
    state_checkpoints: List[str]
    rollback_points: List[str]
    recovery_procedures: List[str]
    
    # Monitoring and Observability
    monitoring_endpoints: List[str]
    logging_configuration: Dict[str, Any]
    alert_thresholds: Dict[str, float]
    performance_metrics: Dict[str, Any]
    
    # Cross-Integration Protocols
    api_contracts: List[Dict[str, Any]]
    event_subscriptions: List[str]
    data_sharing_protocols: List[str]
    security_requirements: List[str]

class CoordinationMetadataBuilder:
    """
    Builder for creating standardized coordination metadata
    Implements intelligence-enhanced metadata generation
    """
    
    def __init__(self):
        self.agent_registry = self._load_agent_registry()
        self.domain_templates = self._load_domain_templates()
        self.intelligence_patterns = self._load_intelligence_patterns()
        self.validation_templates = self._load_validation_templates()
        
    def _load_agent_registry(self) -> Dict[str, Dict[str, Any]]:
        """Load agent capability registry"""
        return {
            "backend-gateway-expert": {
                "domain_expertise": ["backend", "api", "microservices", "database"],
                "tool_requirements": ["Read", "Edit", "Bash", "Grep"],
                "input_formats": ["code", "configuration", "documentation"],
                "output_formats": ["implementation", "api_specs", "configuration"],
                "performance_metrics": {"accuracy": 0.9, "speed": 0.8, "reliability": 0.95},
                "resource_requirements": {"memory": "2GB", "cpu": "2 cores", "storage": "1GB"}
            },
            "webui-architect": {
                "domain_expertise": ["frontend", "ui", "react", "styling"],
                "tool_requirements": ["Read", "Edit", "Browser", "Bash"],
                "input_formats": ["jsx", "css", "design_specs", "user_requirements"],
                "output_formats": ["components", "styles", "interactions"],
                "performance_metrics": {"accuracy": 0.85, "speed": 0.9, "usability": 0.9},
                "resource_requirements": {"memory": "1.5GB", "cpu": "1 core", "storage": "500MB"}
            },
            "security-validator": {
                "domain_expertise": ["security", "authentication", "encryption", "threats"],
                "tool_requirements": ["Read", "Bash", "Grep", "Browser"],
                "input_formats": ["code", "configuration", "security_policies"],
                "output_formats": ["security_reports", "recommendations", "fixes"],
                "performance_metrics": {"accuracy": 0.95, "speed": 0.7, "thoroughness": 0.9},
                "resource_requirements": {"memory": "3GB", "cpu": "2 cores", "storage": "2GB"}
            },
            "performance-profiler": {
                "domain_expertise": ["performance", "optimization", "monitoring", "analytics"],
                "tool_requirements": ["Read", "Bash", "Grep", "Browser"],
                "input_formats": ["code", "metrics", "logs", "configuration"],
                "output_formats": ["performance_reports", "optimizations", "monitoring_setup"],
                "performance_metrics": {"accuracy": 0.9, "speed": 0.8, "insight_depth": 0.85},
                "resource_requirements": {"memory": "2.5GB", "cpu": "3 cores", "storage": "1.5GB"}
            },
            "k8s-architecture-specialist": {
                "domain_expertise": ["kubernetes", "containers", "orchestration", "cloud"],
                "tool_requirements": ["Read", "Edit", "Bash", "Grep"],
                "input_formats": ["yaml", "dockerfile", "helm_charts", "manifests"],
                "output_formats": ["k8s_manifests", "deployment_configs", "scaling_policies"],
                "performance_metrics": {"accuracy": 0.9, "speed": 0.75, "scalability": 0.95},
                "resource_requirements": {"memory": "2GB", "cpu": "2 cores", "storage": "1GB"}
            }
        }
    
    def _load_domain_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load domain-specific coordination templates"""
        return {
            "backend": {
                "typical_dependencies": ["database", "authentication", "logging"],
                "common_validations": ["api_functionality", "data_integrity", "performance"],
                "resource_patterns": {"memory": "2-4GB", "cpu": "2-4 cores", "storage": "1-2GB"},
                "intelligence_features": ["predictive_scaling", "automated_optimization", "intelligent_routing"]
            },
            "frontend": {
                "typical_dependencies": ["api", "authentication", "assets"],
                "common_validations": ["ui_functionality", "responsiveness", "accessibility"],
                "resource_patterns": {"memory": "1-2GB", "cpu": "1-2 cores", "storage": "0.5-1GB"},
                "intelligence_features": ["adaptive_ui", "behavioral_optimization", "intelligent_prefetching"]
            },
            "security": {
                "typical_dependencies": ["authentication", "encryption", "audit_logging"],
                "common_validations": ["vulnerability_scanning", "penetration_testing", "compliance_check"],
                "resource_patterns": {"memory": "2-6GB", "cpu": "2-4 cores", "storage": "1-3GB"},
                "intelligence_features": ["threat_prediction", "automated_response", "behavioral_analysis"]
            },
            "performance": {
                "typical_dependencies": ["monitoring", "metrics", "profiling_tools"],
                "common_validations": ["load_testing", "performance_benchmarking", "resource_utilization"],
                "resource_patterns": {"memory": "2-8GB", "cpu": "2-8 cores", "storage": "1-5GB"},
                "intelligence_features": ["predictive_optimization", "automated_tuning", "intelligent_caching"]
            },
            "infrastructure": {
                "typical_dependencies": ["container_runtime", "orchestration", "monitoring"],
                "common_validations": ["deployment_success", "scaling_tests", "disaster_recovery"],
                "resource_patterns": {"memory": "1-4GB", "cpu": "1-4 cores", "storage": "1-10GB"},
                "intelligence_features": ["predictive_scaling", "automated_recovery", "intelligent_monitoring"]
            }
        }
    
    def _load_intelligence_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load AI intelligence integration patterns"""
        return {
            "predictive_algorithms": {
                "resource_forecasting": {
                    "models": ["linear_regression", "lstm", "arima"],
                    "data_sources": ["historical_usage", "request_patterns", "system_metrics"],
                    "prediction_horizon": "1h-24h",
                    "accuracy_target": 0.8
                },
                "failure_prediction": {
                    "models": ["random_forest", "svm", "neural_network"],
                    "data_sources": ["error_logs", "performance_metrics", "resource_usage"],
                    "prediction_horizon": "5min-2h",
                    "accuracy_target": 0.9
                }
            },
            "automation_frameworks": {
                "response_automation": {
                    "triggers": ["threshold_breach", "anomaly_detection", "pattern_recognition"],
                    "actions": ["scaling", "restart", "notification", "rollback"],
                    "approval_required": ["high_impact", "production"],
                    "automation_level": 0.8
                },
                "optimization_automation": {
                    "triggers": ["performance_degradation", "resource_inefficiency", "cost_increase"],
                    "actions": ["parameter_tuning", "resource_reallocation", "caching_adjustment"],
                    "approval_required": ["major_changes", "production"],
                    "automation_level": 0.7
                }
            },
            "learning_systems": {
                "continuous_learning": {
                    "data_collection": ["execution_results", "user_feedback", "performance_metrics"],
                    "learning_algorithms": ["reinforcement_learning", "online_learning", "transfer_learning"],
                    "adaptation_frequency": "daily",
                    "model_updates": "weekly"
                },
                "pattern_recognition": {
                    "pattern_types": ["usage_patterns", "failure_patterns", "optimization_opportunities"],
                    "detection_algorithms": ["clustering", "anomaly_detection", "sequence_mining"],
                    "confidence_threshold": 0.8,
                    "action_threshold": 0.9
                }
            }
        }
    
    def _load_validation_templates(self) -> Dict[str, List[ValidationCriteria]]:
        """Load validation criteria templates"""
        return {
            "backend": [
                ValidationCriteria(
                    criteria_id="api_functionality",
                    validation_type="functional",
                    success_metrics={"response_success_rate": 0.99, "data_accuracy": 0.95},
                    failure_thresholds={"error_rate": 0.05, "timeout_rate": 0.02},
                    validation_methods=["automated_testing", "integration_testing"],
                    evidence_requirements=["test_results", "api_logs", "performance_metrics"],
                    automation_level="automated"
                ),
                ValidationCriteria(
                    criteria_id="performance_validation",
                    validation_type="performance",
                    success_metrics={"response_time_p95": 200, "throughput_rps": 1000},
                    failure_thresholds={"response_time_p95": 500, "error_rate": 0.1},
                    validation_methods=["load_testing", "stress_testing"],
                    evidence_requirements=["performance_reports", "load_test_results"],
                    automation_level="automated"
                )
            ],
            "frontend": [
                ValidationCriteria(
                    criteria_id="ui_functionality",
                    validation_type="functional",
                    success_metrics={"ui_responsiveness": 0.95, "interaction_success": 0.98},
                    failure_thresholds={"broken_interactions": 0.05, "rendering_errors": 0.02},
                    validation_methods=["browser_automation", "ui_testing"],
                    evidence_requirements=["test_screenshots", "interaction_logs", "browser_console_logs"],
                    automation_level="semi_automated"
                ),
                ValidationCriteria(
                    criteria_id="accessibility_validation",
                    validation_type="functional",
                    success_metrics={"wcag_compliance": 0.9, "screen_reader_compatibility": 0.95},
                    failure_thresholds={"accessibility_violations": 0.1, "keyboard_nav_failures": 0.05},
                    validation_methods=["accessibility_scanning", "manual_testing"],
                    evidence_requirements=["accessibility_reports", "manual_test_results"],
                    automation_level="semi_automated"
                )
            ],
            "security": [
                ValidationCriteria(
                    criteria_id="vulnerability_assessment",
                    validation_type="security",
                    success_metrics={"vulnerability_score": 8.0, "penetration_resistance": 0.95},
                    failure_thresholds={"critical_vulnerabilities": 0, "high_risk_issues": 2},
                    validation_methods=["vulnerability_scanning", "penetration_testing"],
                    evidence_requirements=["security_scan_results", "penetration_test_reports"],
                    automation_level="semi_automated"
                )
            ],
            "performance": [
                ValidationCriteria(
                    criteria_id="performance_benchmarking",
                    validation_type="performance",
                    success_metrics={"cpu_efficiency": 0.8, "memory_efficiency": 0.85},
                    failure_thresholds={"cpu_utilization": 0.9, "memory_utilization": 0.9},
                    validation_methods=["benchmarking", "profiling", "monitoring"],
                    evidence_requirements=["benchmark_results", "profiling_reports", "monitoring_data"],
                    automation_level="automated"
                )
            ],
            "infrastructure": [
                ValidationCriteria(
                    criteria_id="deployment_validation",
                    validation_type="integration",
                    success_metrics={"deployment_success_rate": 0.98, "service_availability": 0.99},
                    failure_thresholds={"deployment_failures": 0.02, "downtime_minutes": 5},
                    validation_methods=["deployment_testing", "health_checks", "monitoring"],
                    evidence_requirements=["deployment_logs", "health_check_results", "uptime_metrics"],
                    automation_level="automated"
                )
            ]
        }
    
    def build_coordination_metadata(self, package_id: str, agent_name: str, domain: str, 
                                  phase: ExecutionPhase, **kwargs) -> CoordinationMetadata:
        """
        Build comprehensive coordination metadata for agent package
        """
        
        # Get agent capabilities
        agent_info = self.agent_registry.get(agent_name, {})
        domain_template = self.domain_templates.get(domain, self.domain_templates["backend"])
        
        # Generate unique coordination ID
        coordination_id = self._generate_coordination_id(package_id, agent_name, phase)
        
        # Build agent capabilities
        agent_capabilities = [self._build_agent_capability(agent_name, agent_info)]
        
        # Build resource allocations
        resource_allocations = self._build_resource_allocations(agent_info, domain_template)
        
        # Build dependencies
        dependencies = self._build_dependencies(agent_name, domain, phase, kwargs.get('task_requirements', []))
        
        # Build validation criteria
        validation_criteria = self._build_validation_criteria(domain)
        
        # Build intelligence metadata
        intelligence_metadata = self._build_intelligence_metadata(domain, kwargs.get('intelligence_features', []))
        
        # Get current timestamp
        current_time = time.time()
        
        return CoordinationMetadata(
            # Core Identification
            coordination_id=coordination_id,
            package_id=package_id,
            agent_target=agent_name,
            domain=domain,
            execution_phase=phase,
            creation_timestamp=current_time,
            last_updated=current_time,
            
            # Agent and Capability Information
            agent_capabilities=agent_capabilities,
            required_tools=agent_info.get('tool_requirements', []),
            resource_allocations=resource_allocations,
            
            # Coordination Dependencies
            dependencies=dependencies,
            coordination_status=CoordinationStatus.INITIALIZED,
            parallel_execution_support=kwargs.get('parallel_execution_support', True),
            cross_stream_coordination=kwargs.get('cross_stream_coordination', True),
            
            # Token and Performance Management
            token_allocation=kwargs.get('token_allocation', 4000),
            actual_token_usage=kwargs.get('actual_token_usage', 0),
            compression_applied=kwargs.get('compression_applied', False),
            optimization_strategy=kwargs.get('optimization_strategy', 'balanced'),
            performance_targets=kwargs.get('performance_targets', {"efficiency": 0.8, "quality": 0.85}),
            
            # Validation and Quality Assurance
            validation_criteria=validation_criteria,
            evidence_requirements=self._build_evidence_requirements(domain, validation_criteria),
            quality_gates=kwargs.get('quality_gates', {"minimum_quality": 0.7, "minimum_performance": 0.75}),
            success_metrics=kwargs.get('success_metrics', {}),
            
            # Intelligence and Automation
            intelligence_metadata=intelligence_metadata,
            automation_features=kwargs.get('automation_features', []),
            predictive_capabilities=kwargs.get('predictive_capabilities', []),
            
            # Execution Control
            priority_level=kwargs.get('priority_level', CoordinationPriority.MEDIUM),
            timeout_constraints=kwargs.get('timeout_constraints', {"execution": 300, "validation": 120}),
            retry_policies=kwargs.get('retry_policies', {"max_retries": 3, "backoff_factor": 2}),
            fallback_strategies=kwargs.get('fallback_strategies', ["compression_fallback", "simplified_execution"]),
            
            # Context and State Management
            context_version=kwargs.get('context_version', 'v1.0'),
            state_checkpoints=[],
            rollback_points=[],
            recovery_procedures=kwargs.get('recovery_procedures', ["checkpoint_recovery", "graceful_degradation"]),
            
            # Monitoring and Observability
            monitoring_endpoints=kwargs.get('monitoring_endpoints', []),
            logging_configuration=kwargs.get('logging_configuration', {"level": "INFO", "format": "json"}),
            alert_thresholds=kwargs.get('alert_thresholds', {"error_rate": 0.1, "latency_p95": 1000}),
            performance_metrics={},
            
            # Cross-Integration Protocols
            api_contracts=kwargs.get('api_contracts', []),
            event_subscriptions=kwargs.get('event_subscriptions', []),
            data_sharing_protocols=kwargs.get('data_sharing_protocols', ["json", "protobuf"]),
            security_requirements=kwargs.get('security_requirements', ["authentication", "authorization"])
        )
    
    def _generate_coordination_id(self, package_id: str, agent_name: str, phase: ExecutionPhase) -> str:
        """Generate unique coordination ID"""
        source = f"{package_id}:{agent_name}:{phase.value}:{time.time()}"
        return hashlib.md5(source.encode()).hexdigest()[:16]
    
    def _build_agent_capability(self, agent_name: str, agent_info: Dict[str, Any]) -> AgentCapability:
        """Build agent capability specification"""
        return AgentCapability(
            capability_id=f"{agent_name}_capability",
            capability_name=agent_name.replace('-', ' ').title(),
            domain_expertise=agent_info.get('domain_expertise', []),
            tool_requirements=agent_info.get('tool_requirements', []),
            input_formats=agent_info.get('input_formats', []),
            output_formats=agent_info.get('output_formats', []),
            performance_metrics=agent_info.get('performance_metrics', {}),
            resource_requirements=agent_info.get('resource_requirements', {})
        )
    
    def _build_resource_allocations(self, agent_info: Dict[str, Any], 
                                  domain_template: Dict[str, Any]) -> List[ResourceAllocation]:
        """Build resource allocation specifications"""
        allocations = []
        
        resource_reqs = agent_info.get('resource_requirements', {})
        
        # Memory allocation
        if 'memory' in resource_reqs:
            allocations.append(ResourceAllocation(
                allocation_id=f"memory_{int(time.time())}",
                resource_type="memory",
                allocated_amount=self._parse_resource_amount(resource_reqs['memory']),
                allocation_unit="MB",
                allocation_duration=3600.0,  # 1 hour
                sharing_policy="exclusive",
                optimization_hints=["garbage_collection", "memory_pooling"]
            ))
        
        # CPU allocation
        if 'cpu' in resource_reqs:
            allocations.append(ResourceAllocation(
                allocation_id=f"cpu_{int(time.time())}",
                resource_type="computational",
                allocated_amount=self._parse_cpu_cores(resource_reqs['cpu']),
                allocation_unit="cores",
                allocation_duration=3600.0,
                sharing_policy="shared",
                optimization_hints=["load_balancing", "cpu_affinity"]
            ))
        
        # Storage allocation
        if 'storage' in resource_reqs:
            allocations.append(ResourceAllocation(
                allocation_id=f"storage_{int(time.time())}",
                resource_type="storage",
                allocated_amount=self._parse_resource_amount(resource_reqs['storage']),
                allocation_unit="MB",
                allocation_duration=7200.0,  # 2 hours
                sharing_policy="exclusive",
                optimization_hints=["ssd_preferred", "compression"]
            ))
        
        return allocations
    
    def _build_dependencies(self, agent_name: str, domain: str, phase: ExecutionPhase, 
                           task_requirements: List[str]) -> List[CoordinationDependency]:
        """Build coordination dependencies"""
        dependencies = []
        
        # Phase-based dependencies
        if phase in [ExecutionPhase.PHASE_5_PARALLEL_IMPLEMENTATION, ExecutionPhase.PHASE_6_VALIDATION]:
            # Implementation phase needs research data
            dependencies.append(CoordinationDependency(
                dependency_id=f"research_data_{int(time.time())}",
                source_agent="codebase-research-analyst",
                target_agent=agent_name,
                dependency_type="data",
                required_outputs=["research_findings", "analysis_results"],
                timing_constraints={"max_wait_time": 600, "preferred_delivery": 300},
                priority_level=CoordinationPriority.HIGH,
                resolution_strategy="parallel_execution"
            ))
        
        # Domain-specific dependencies
        domain_template = self.domain_templates.get(domain, {})
        typical_deps = domain_template.get('typical_dependencies', [])
        
        for dep in typical_deps:
            dependencies.append(CoordinationDependency(
                dependency_id=f"{dep}_dependency_{int(time.time())}",
                source_agent=self._map_dependency_to_agent(dep),
                target_agent=agent_name,
                dependency_type="completion",
                required_outputs=[f"{dep}_setup", f"{dep}_configuration"],
                timing_constraints={"max_wait_time": 300, "preferred_delivery": 180},
                priority_level=CoordinationPriority.MEDIUM,
                resolution_strategy="sequential_execution"
            ))
        
        return dependencies
    
    def _build_validation_criteria(self, domain: str) -> List[ValidationCriteria]:
        """Build validation criteria for domain"""
        return self.validation_templates.get(domain, [])
    
    def _build_intelligence_metadata(self, domain: str, intelligence_features: List[str]) -> IntelligenceMetadata:
        """Build intelligence metadata for domain"""
        
        domain_template = self.domain_templates.get(domain, {})
        domain_intelligence = domain_template.get('intelligence_features', [])
        
        # Combine domain and specified features
        all_features = list(set(domain_intelligence + intelligence_features))
        
        return IntelligenceMetadata(
            intelligence_features=all_features,
            prediction_models=self._build_prediction_models(domain, all_features),
            automation_level=0.8,  # Default high automation
            learning_integration=True,
            adaptation_capabilities=["parameter_tuning", "strategy_adjustment", "pattern_recognition"],
            feedback_loops=["performance_feedback", "quality_feedback", "user_feedback"],
            optimization_algorithms=["gradient_descent", "genetic_algorithm", "reinforcement_learning"]
        )
    
    def _build_prediction_models(self, domain: str, features: List[str]) -> Dict[str, Any]:
        """Build prediction models configuration"""
        models = {}
        
        intelligence_patterns = self.intelligence_patterns.get('predictive_algorithms', {})
        
        for feature in features:
            if 'predictive' in feature or 'prediction' in feature:
                if 'resource' in feature or 'scaling' in feature:
                    models['resource_forecasting'] = intelligence_patterns.get('resource_forecasting', {})
                elif 'failure' in feature or 'error' in feature:
                    models['failure_prediction'] = intelligence_patterns.get('failure_prediction', {})
        
        return models
    
    def _build_evidence_requirements(self, domain: str, validation_criteria: List[ValidationCriteria]) -> List[str]:
        """Build evidence requirements from validation criteria"""
        evidence_reqs = []
        
        for criteria in validation_criteria:
            evidence_reqs.extend(criteria.evidence_requirements)
        
        # Add domain-specific evidence requirements
        domain_evidence = {
            "backend": ["api_test_results", "database_queries", "performance_metrics"],
            "frontend": ["ui_screenshots", "browser_compatibility", "interaction_recordings"],
            "security": ["security_scan_results", "vulnerability_assessments", "penetration_test_reports"],
            "performance": ["benchmark_results", "profiling_data", "monitoring_metrics"],
            "infrastructure": ["deployment_logs", "health_checks", "resource_utilization"]
        }
        
        evidence_reqs.extend(domain_evidence.get(domain, []))
        
        return list(set(evidence_reqs))  # Remove duplicates
    
    def _parse_resource_amount(self, resource_str: str) -> float:
        """Parse resource amount from string (e.g., '2GB' -> 2048)"""
        if 'GB' in resource_str:
            return float(resource_str.replace('GB', '').strip()) * 1024
        elif 'MB' in resource_str:
            return float(resource_str.replace('MB', '').strip())
        elif 'KB' in resource_str:
            return float(resource_str.replace('KB', '').strip()) / 1024
        else:
            return 1024.0  # Default 1GB
    
    def _parse_cpu_cores(self, cpu_str: str) -> float:
        """Parse CPU cores from string (e.g., '2 cores' -> 2.0)"""
        if 'core' in cpu_str:
            return float(cpu_str.split()[0])
        else:
            return 1.0  # Default 1 core
    
    def _map_dependency_to_agent(self, dependency: str) -> str:
        """Map dependency type to responsible agent"""
        dependency_mapping = {
            "database": "schema-database-expert",
            "authentication": "security-validator",
            "api": "backend-gateway-expert",
            "monitoring": "performance-profiler",
            "logging": "monitoring-analyst",
            "assets": "webui-architect",
            "container_runtime": "k8s-architecture-specialist",
            "orchestration": "deployment-orchestrator"
        }
        
        return dependency_mapping.get(dependency, "backend-gateway-expert")

class CoordinationMetadataManager:
    """
    Manager for coordination metadata operations
    Handles storage, retrieval, and synchronization of coordination metadata
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("/home/marku/ai_workflow_engine/.claude/context_packages/coordination_metadata")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.active_coordinations: Dict[str, CoordinationMetadata] = {}
        self.builder = CoordinationMetadataBuilder()
        
    def create_coordination_metadata(self, package_id: str, agent_name: str, domain: str, 
                                   phase: ExecutionPhase, **kwargs) -> CoordinationMetadata:
        """Create and store new coordination metadata"""
        
        metadata = self.builder.build_coordination_metadata(
            package_id, agent_name, domain, phase, **kwargs
        )
        
        # Store in active coordinations
        self.active_coordinations[metadata.coordination_id] = metadata
        
        # Persist to storage
        self._persist_metadata(metadata)
        
        return metadata
    
    def update_coordination_status(self, coordination_id: str, status: CoordinationStatus, 
                                 performance_metrics: Optional[Dict[str, Any]] = None):
        """Update coordination status and metrics"""
        
        if coordination_id not in self.active_coordinations:
            raise ValueError(f"Coordination {coordination_id} not found")
        
        metadata = self.active_coordinations[coordination_id]
        metadata.coordination_status = status
        metadata.last_updated = time.time()
        
        if performance_metrics:
            metadata.performance_metrics.update(performance_metrics)
        
        # Persist update
        self._persist_metadata(metadata)
    
    def add_state_checkpoint(self, coordination_id: str, checkpoint_data: Dict[str, Any]):
        """Add state checkpoint for coordination"""
        
        if coordination_id not in self.active_coordinations:
            raise ValueError(f"Coordination {coordination_id} not found")
        
        metadata = self.active_coordinations[coordination_id]
        
        checkpoint_id = f"checkpoint_{int(time.time())}"
        metadata.state_checkpoints.append(checkpoint_id)
        
        # Store checkpoint data separately
        checkpoint_path = self.storage_path / f"{checkpoint_id}.json"
        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
        
        metadata.last_updated = time.time()
        self._persist_metadata(metadata)
    
    def get_coordination_metadata(self, coordination_id: str) -> Optional[CoordinationMetadata]:
        """Retrieve coordination metadata"""
        
        # Check active coordinations first
        if coordination_id in self.active_coordinations:
            return self.active_coordinations[coordination_id]
        
        # Try to load from storage
        metadata_path = self.storage_path / f"{coordination_id}.json"
        if metadata_path.exists():
            return self._load_metadata(metadata_path)
        
        return None
    
    def get_active_coordinations(self, domain: Optional[str] = None, 
                               phase: Optional[ExecutionPhase] = None) -> List[CoordinationMetadata]:
        """Get active coordinations with optional filtering"""
        
        coordinations = list(self.active_coordinations.values())
        
        if domain:
            coordinations = [c for c in coordinations if c.domain == domain]
        
        if phase:
            coordinations = [c for c in coordinations if c.execution_phase == phase]
        
        return coordinations
    
    def get_dependency_graph(self, coordination_id: str) -> Dict[str, List[str]]:
        """Get dependency graph for coordination"""
        
        metadata = self.get_coordination_metadata(coordination_id)
        if not metadata:
            return {}
        
        dependency_graph = {}
        
        for dep in metadata.dependencies:
            if dep.source_agent not in dependency_graph:
                dependency_graph[dep.source_agent] = []
            dependency_graph[dep.source_agent].append(dep.target_agent)
        
        return dependency_graph
    
    def validate_coordination_readiness(self, coordination_id: str) -> Dict[str, Any]:
        """Validate coordination readiness"""
        
        metadata = self.get_coordination_metadata(coordination_id)
        if not metadata:
            return {"valid": False, "errors": ["Coordination metadata not found"]}
        
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "readiness_score": 0.0
        }
        
        # Check dependencies
        unresolved_deps = [d for d in metadata.dependencies 
                          if d.dependency_type == "completion" and d.priority_level in [CoordinationPriority.CRITICAL, CoordinationPriority.HIGH]]
        
        if unresolved_deps:
            validation_results["warnings"].append(f"Unresolved high-priority dependencies: {len(unresolved_deps)}")
        
        # Check resource allocations
        if not metadata.resource_allocations:
            validation_results["warnings"].append("No resource allocations specified")
        
        # Check validation criteria
        if not metadata.validation_criteria:
            validation_results["errors"].append("No validation criteria specified")
            validation_results["valid"] = False
        
        # Calculate readiness score
        score = 1.0
        score -= len(validation_results["errors"]) * 0.3
        score -= len(validation_results["warnings"]) * 0.1
        score = max(0.0, score)
        
        validation_results["readiness_score"] = score
        
        return validation_results
    
    def _persist_metadata(self, metadata: CoordinationMetadata):
        """Persist metadata to storage"""
        
        metadata_path = self.storage_path / f"{metadata.coordination_id}.json"
        
        # Convert to serializable format
        metadata_dict = asdict(metadata)
        
        # Handle enum serialization
        metadata_dict['execution_phase'] = metadata.execution_phase.value
        metadata_dict['coordination_status'] = metadata.coordination_status.value
        metadata_dict['priority_level'] = metadata.priority_level.value
        
        # Handle nested objects
        for dep in metadata_dict['dependencies']:
            dep['priority_level'] = dep['priority_level'].value
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata_dict, f, indent=2, default=str)
    
    def _load_metadata(self, metadata_path: Path) -> CoordinationMetadata:
        """Load metadata from storage"""
        
        with open(metadata_path, 'r') as f:
            data = json.load(f)
        
        # Convert enum values back
        data['execution_phase'] = ExecutionPhase(data['execution_phase'])
        data['coordination_status'] = CoordinationStatus(data['coordination_status'])
        data['priority_level'] = CoordinationPriority(data['priority_level'])
        
        for dep in data['dependencies']:
            dep['priority_level'] = CoordinationPriority(dep['priority_level'])
        
        # Reconstruct objects (simplified for this example)
        # In production, would need full deserialization logic
        return CoordinationMetadata(**data)

def main():
    """Test the coordination metadata framework"""
    
    # Initialize manager
    manager = CoordinationMetadataManager()
    
    # Test metadata creation
    metadata = manager.create_coordination_metadata(
        package_id="backend_optimization_20250814",
        agent_name="backend-gateway-expert",
        domain="backend",
        phase=ExecutionPhase.PHASE_5_PARALLEL_IMPLEMENTATION,
        task_requirements=["Optimize API performance", "Implement caching", "Add monitoring"],
        intelligence_features=["predictive_scaling", "automated_optimization"],
        parallel_execution_support=True,
        cross_stream_coordination=True,
        token_allocation=3500,
        priority_level=CoordinationPriority.HIGH
    )
    
    print("=== Enhanced Coordination Metadata Framework Test ===\n")
    print(f"Created coordination metadata:")
    print(f"  Coordination ID: {metadata.coordination_id}")
    print(f"  Agent Target: {metadata.agent_target}")
    print(f"  Domain: {metadata.domain}")
    print(f"  Execution Phase: {metadata.execution_phase.value}")
    print(f"  Dependencies: {len(metadata.dependencies)}")
    print(f"  Validation Criteria: {len(metadata.validation_criteria)}")
    print(f"  Intelligence Features: {metadata.intelligence_metadata.intelligence_features}")
    print()
    
    # Test status update
    manager.update_coordination_status(
        metadata.coordination_id, 
        CoordinationStatus.IN_PROGRESS,
        {"execution_progress": 0.3, "token_usage": 1200}
    )
    print("Updated coordination status to IN_PROGRESS")
    print()
    
    # Test checkpoint
    manager.add_state_checkpoint(
        metadata.coordination_id,
        {"phase": "implementation_started", "progress": 30, "next_steps": ["api_optimization", "caching_setup"]}
    )
    print("Added state checkpoint")
    print()
    
    # Test validation
    validation_result = manager.validate_coordination_readiness(metadata.coordination_id)
    print(f"Coordination readiness validation:")
    print(f"  Valid: {validation_result['valid']}")
    print(f"  Readiness Score: {validation_result['readiness_score']:.2f}")
    print(f"  Errors: {validation_result['errors']}")
    print(f"  Warnings: {validation_result['warnings']}")
    print()
    
    # Test dependency graph
    dep_graph = manager.get_dependency_graph(metadata.coordination_id)
    print(f"Dependency graph: {dep_graph}")
    print()
    
    # Test active coordinations
    active_coords = manager.get_active_coordinations(domain="backend")
    print(f"Active backend coordinations: {len(active_coords)}")
    
    print("\n=== Enhanced Coordination Metadata Framework Complete ===")

if __name__ == "__main__":
    main()