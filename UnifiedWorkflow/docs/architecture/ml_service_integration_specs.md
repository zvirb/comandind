# ML Service Integration Specifications

## Overview

This document provides detailed technical specifications for integrating the 5 ML services (coordination, learning, memory, reasoning, perception) into every aspect of the agentic workflow system.

## Service Integration Architecture

### 1. Coordination Service Integration

#### Purpose
Real-time agent coordination, resource allocation, and communication routing decisions.

#### Technical Implementation

**Service Interface**:
```python
class CoordinationServiceClient:
    def __init__(self, service_url: str, api_key: str):
        self.base_url = service_url
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    async def assign_optimal_agents(self, task_requirements: Dict) -> List[AgentAssignment]:
        """Assign optimal agents based on task requirements and current system state"""
        payload = {
            "task_requirements": task_requirements,
            "current_system_state": await self.get_system_state(),
            "agent_capabilities": await self.get_agent_capabilities(),
            "performance_history": await self.get_performance_history()
        }
        
        response = await self.post("/api/v1/coordination/assign-agents", payload)
        return [AgentAssignment.from_dict(assignment) for assignment in response["assignments"]]
    
    async def balance_workload(self, active_agents: List[str]) -> WorkloadBalance:
        """Optimize workload distribution across active agents"""
        current_loads = await self.get_agent_workloads(active_agents)
        
        payload = {
            "current_loads": current_loads,
            "system_constraints": await self.get_system_constraints(),
            "optimization_objectives": ["minimize_latency", "maximize_throughput", "balance_load"]
        }
        
        response = await self.post("/api/v1/coordination/balance-workload", payload)
        return WorkloadBalance.from_dict(response)
    
    async def route_agent_message(self, sender: str, recipient: str, message: Dict) -> RoutingDecision:
        """Determine optimal routing for inter-agent communication"""
        payload = {
            "sender_agent": sender,
            "recipient_agent": recipient,
            "message_type": message.get("type"),
            "message_priority": message.get("priority", "normal"),
            "current_communication_graph": await self.get_communication_graph(),
            "recursion_prevention": True
        }
        
        response = await self.post("/api/v1/coordination/route-message", payload)
        return RoutingDecision.from_dict(response)
    
    async def resolve_resource_conflict(self, conflicting_agents: List[str], resource: str) -> ConflictResolution:
        """Resolve resource conflicts between agents"""
        payload = {
            "conflicting_agents": conflicting_agents,
            "resource_identifier": resource,
            "agent_priorities": await self.get_agent_priorities(conflicting_agents),
            "resource_availability": await self.get_resource_availability(resource)
        }
        
        response = await self.post("/api/v1/coordination/resolve-conflict", payload)
        return ConflictResolution.from_dict(response)
```

**Integration Points**:
```python
# Dynamic Agent Assignment
async def orchestrate_task(task_description: str):
    # Analyze task requirements
    task_analysis = await reasoning_service.analyze_task_complexity(task_description)
    
    # Get optimal agent assignments from coordination service
    agent_assignments = await coordination_service.assign_optimal_agents({
        "task_type": task_analysis.type,
        "complexity_score": task_analysis.complexity,
        "required_capabilities": task_analysis.capabilities,
        "estimated_duration": task_analysis.duration,
        "resource_requirements": task_analysis.resources
    })
    
    # Execute with assigned agents
    return await execute_with_agents(agent_assignments, task_description)

# Workload Balancing
async def monitor_and_balance_system():
    while True:
        active_agents = await get_active_agents()
        workload_balance = await coordination_service.balance_workload(active_agents)
        
        if workload_balance.requires_rebalancing:
            await apply_workload_rebalancing(workload_balance.recommendations)
        
        await asyncio.sleep(30)  # Check every 30 seconds

# Inter-Agent Communication Routing
async def send_agent_message(sender: str, recipient: str, message: Dict):
    routing_decision = await coordination_service.route_agent_message(sender, recipient, message)
    
    if routing_decision.direct_allowed:
        return await send_direct_message(recipient, message)
    elif routing_decision.route_through_coordinator:
        return await route_through_coordinator(sender, recipient, message)
    else:
        return await queue_for_later_delivery(sender, recipient, message, routing_decision.delay_reason)
```

### 2. Learning Service Integration

#### Purpose
Historical pattern analysis, performance tracking, and continuous system improvement.

#### Technical Implementation

**Service Interface**:
```python
class LearningServiceClient:
    def __init__(self, service_url: str, api_key: str):
        self.base_url = service_url
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    async def analyze_orchestration_outcome(self, workflow_id: str, execution_results: Dict) -> LearningAnalysis:
        """Analyze orchestration outcome for learning patterns"""
        payload = {
            "workflow_id": workflow_id,
            "execution_results": execution_results,
            "success_metrics": await self.calculate_success_metrics(execution_results),
            "agent_performance": execution_results.get("agent_metrics", {}),
            "resource_utilization": execution_results.get("resource_metrics", {}),
            "user_satisfaction": execution_results.get("user_feedback", {})
        }
        
        response = await self.post("/api/v1/learning/analyze-outcome", payload)
        return LearningAnalysis.from_dict(response)
    
    async def get_optimal_workflow_pattern(self, task_type: str) -> WorkflowPattern:
        """Get optimal workflow pattern based on historical success"""
        payload = {
            "task_type": task_type,
            "success_threshold": 0.8,
            "include_recent_adaptations": True,
            "time_window": "90_days"
        }
        
        response = await self.post("/api/v1/learning/optimal-workflow", payload)
        return WorkflowPattern.from_dict(response)
    
    async def track_agent_performance(self, agent_id: str, task_outcome: Dict) -> PerformanceUpdate:
        """Track individual agent performance for optimization"""
        payload = {
            "agent_id": agent_id,
            "task_outcome": task_outcome,
            "execution_metrics": task_outcome.get("metrics", {}),
            "quality_scores": task_outcome.get("quality", {}),
            "collaboration_effectiveness": task_outcome.get("collaboration", {})
        }
        
        response = await self.post("/api/v1/learning/track-performance", payload)
        return PerformanceUpdate.from_dict(response)
    
    async def predict_workflow_success(self, proposed_workflow: Dict) -> SuccessPrediction:
        """Predict success probability of proposed workflow"""
        payload = {
            "proposed_workflow": proposed_workflow,
            "historical_patterns": await self.get_similar_patterns(proposed_workflow),
            "current_system_state": await self.get_system_state(),
            "agent_availability": await self.get_agent_availability()
        }
        
        response = await self.post("/api/v1/learning/predict-success", payload)
        return SuccessPrediction.from_dict(response)
```

**Learning Pattern Storage**:
```python
@dataclass
class LearningPattern:
    pattern_id: str
    workflow_type: str
    success_rate: float
    optimal_agents: List[str]
    typical_duration: timedelta
    resource_requirements: Dict[str, float]
    common_failure_points: List[str]
    optimization_opportunities: List[str]
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'LearningPattern':
        return cls(**data)

async def store_learning_pattern(workflow_id: str, execution_results: Dict):
    """Store learning pattern for future optimization"""
    learning_analysis = await learning_service.analyze_orchestration_outcome(workflow_id, execution_results)
    
    pattern = LearningPattern(
        pattern_id=f"{workflow_id}_{datetime.now().isoformat()}",
        workflow_type=execution_results["workflow_type"],
        success_rate=learning_analysis.success_score,
        optimal_agents=learning_analysis.high_performing_agents,
        typical_duration=execution_results["duration"],
        resource_requirements=learning_analysis.resource_usage,
        common_failure_points=learning_analysis.failure_points,
        optimization_opportunities=learning_analysis.optimizations
    )
    
    await learning_service.store_pattern(pattern)
```

### 3. Memory Service Integration

#### Purpose
Dynamic context retrieval, intelligent information management, and cross-session continuity.

#### Technical Implementation

**Service Interface**:
```python
class MemoryServiceClient:
    def __init__(self, service_url: str, api_key: str):
        self.base_url = service_url
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    async def get_relevant_context(self, agent_id: str, task_description: str) -> ContextPackage:
        """Get relevant context for agent and task"""
        payload = {
            "agent_id": agent_id,
            "task_description": task_description,
            "agent_capabilities": await self.get_agent_capabilities(agent_id),
            "relevance_threshold": 0.7,
            "include_historical_patterns": True,
            "optimize_for_success": True
        }
        
        response = await self.post("/api/v1/memory/get-context", payload)
        return ContextPackage.from_dict(response)
    
    async def store_execution_context(self, workflow_id: str, context_data: Dict) -> ContextStorage:
        """Store execution context for future retrieval"""
        payload = {
            "workflow_id": workflow_id,
            "context_data": context_data,
            "execution_timestamp": datetime.now().isoformat(),
            "agents_involved": context_data.get("agents", []),
            "success_outcome": context_data.get("success", False),
            "indexing_keywords": await self.extract_keywords(context_data)
        }
        
        response = await self.post("/api/v1/memory/store-context", payload)
        return ContextStorage.from_dict(response)
    
    async def retrieve_historical_patterns(self, task_signature: str) -> List[HistoricalPattern]:
        """Retrieve historical patterns for similar tasks"""
        payload = {
            "task_signature": task_signature,
            "similarity_threshold": 0.75,
            "max_patterns": 10,
            "include_failure_patterns": True,
            "time_relevance_weight": 0.3
        }
        
        response = await self.post("/api/v1/memory/historical-patterns", payload)
        return [HistoricalPattern.from_dict(pattern) for pattern in response["patterns"]]
    
    async def optimize_context_relevance(self, context_package: Dict, task_requirements: Dict) -> OptimizedContext:
        """Optimize context package for specific task requirements"""
        payload = {
            "context_package": context_package,
            "task_requirements": task_requirements,
            "optimization_objectives": ["relevance", "completeness", "efficiency"],
            "agent_preferences": task_requirements.get("agent_preferences", {})
        }
        
        response = await self.post("/api/v1/memory/optimize-context", payload)
        return OptimizedContext.from_dict(response)
```

**Dynamic Context Assembly**:
```python
async def assemble_dynamic_context(agent_id: str, task_description: str) -> Dict:
    """Assemble dynamic context replacing static documents"""
    
    # Get base context from memory service
    base_context = await memory_service.get_relevant_context(agent_id, task_description)
    
    # Enhance with historical patterns
    task_signature = await generate_task_signature(task_description)
    historical_patterns = await memory_service.retrieve_historical_patterns(task_signature)
    
    # Add real-time system state
    current_state = await perception_service.get_system_state()
    
    # Optimize for task success
    optimized_context = await memory_service.optimize_context_relevance(
        context_package={
            "base_context": base_context.content,
            "historical_patterns": [pattern.content for pattern in historical_patterns],
            "system_state": current_state
        },
        task_requirements={
            "agent_id": agent_id,
            "task_type": await classify_task_type(task_description),
            "complexity": await estimate_task_complexity(task_description)
        }
    )
    
    return optimized_context.content

# Example usage replacing static documents
async def get_backend_context(task_description: str) -> Dict:
    """Replace static backend context document with dynamic assembly"""
    return await assemble_dynamic_context("backend-gateway-expert", task_description)

async def get_security_context(task_description: str) -> Dict:
    """Replace static security context document with dynamic assembly"""
    return await assemble_dynamic_context("security-validator", task_description)
```

### 4. Reasoning Service Integration

#### Purpose
Complex decision trees, validation logic, and risk assessment.

#### Technical Implementation

**Service Interface**:
```python
class ReasoningServiceClient:
    def __init__(self, service_url: str, api_key: str):
        self.base_url = service_url
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    async def analyze_failure_risk(self, proposed_changes: Dict) -> RiskAnalysis:
        """Analyze failure risk of proposed changes"""
        payload = {
            "proposed_changes": proposed_changes,
            "current_system_state": await self.get_system_state(),
            "historical_failures": await self.get_historical_failures(proposed_changes),
            "complexity_factors": await self.analyze_complexity(proposed_changes),
            "dependency_impacts": await self.analyze_dependencies(proposed_changes)
        }
        
        response = await self.post("/api/v1/reasoning/analyze-risk", payload)
        return RiskAnalysis.from_dict(response)
    
    async def evaluate_success_probability(self, validation_criteria: Dict) -> SuccessEvaluation:
        """Evaluate success probability based on validation criteria"""
        payload = {
            "validation_criteria": validation_criteria,
            "current_implementation": await self.get_current_implementation(),
            "test_coverage": await self.analyze_test_coverage(),
            "system_health": await self.get_system_health(),
            "historical_success_patterns": await self.get_success_patterns()
        }
        
        response = await self.post("/api/v1/reasoning/evaluate-success", payload)
        return SuccessEvaluation.from_dict(response)
    
    async def determine_optimal_validation_strategy(self, implementation_plan: Dict) -> ValidationStrategy:
        """Determine optimal validation strategy for implementation"""
        risk_analysis = await self.analyze_failure_risk(implementation_plan)
        
        payload = {
            "implementation_plan": implementation_plan,
            "risk_analysis": risk_analysis.to_dict(),
            "available_validation_methods": await self.get_validation_methods(),
            "resource_constraints": await self.get_resource_constraints(),
            "time_constraints": implementation_plan.get("deadline")
        }
        
        response = await self.post("/api/v1/reasoning/validation-strategy", payload)
        return ValidationStrategy.from_dict(response)
    
    async def assess_change_impact(self, modification_scope: Dict) -> ImpactAssessment:
        """Assess impact of proposed modifications"""
        payload = {
            "modification_scope": modification_scope,
            "system_architecture": await self.get_system_architecture(),
            "dependency_graph": await self.get_dependency_graph(),
            "user_workflows": await self.get_user_workflows(),
            "performance_baselines": await self.get_performance_baselines()
        }
        
        response = await self.post("/api/v1/reasoning/assess-impact", payload)
        return ImpactAssessment.from_dict(response)
```

**Predictive Validation Implementation**:
```python
async def implement_predictive_validation(implementation_plan: Dict) -> ValidationResults:
    """Implement predictive validation to reduce false positives"""
    
    # Analyze failure risk
    risk_analysis = await reasoning_service.analyze_failure_risk(implementation_plan)
    
    # Determine optimal validation strategy
    validation_strategy = await reasoning_service.determine_optimal_validation_strategy(implementation_plan)
    
    # Execute validation based on strategy
    if validation_strategy.requires_pre_validation:
        pre_validation_results = await execute_pre_validation(implementation_plan)
        if not pre_validation_results.passed:
            return ValidationResults(
                status="failed_pre_validation",
                risk_level=risk_analysis.risk_level,
                recommendations=pre_validation_results.recommendations
            )
    
    # Execute main validation
    main_validation_results = await execute_main_validation(
        implementation_plan, 
        validation_strategy
    )
    
    # Evaluate success probability
    success_evaluation = await reasoning_service.evaluate_success_probability({
        "validation_results": main_validation_results.to_dict(),
        "implementation_quality": main_validation_results.quality_score,
        "test_coverage": main_validation_results.test_coverage,
        "performance_impact": main_validation_results.performance_impact
    })
    
    return ValidationResults(
        status="completed",
        success_probability=success_evaluation.probability,
        risk_analysis=risk_analysis,
        validation_evidence=main_validation_results.evidence,
        recommendations=success_evaluation.recommendations
    )
```

### 5. Perception Service Integration

#### Purpose
Real-time system monitoring, anomaly detection, and performance optimization.

#### Technical Implementation

**Service Interface**:
```python
class PerceptionServiceClient:
    def __init__(self, service_url: str, api_key: str):
        self.base_url = service_url
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    async def monitor_system_health(self, components: List[str]) -> SystemHealth:
        """Monitor system health across specified components"""
        payload = {
            "components": components,
            "health_metrics": ["cpu", "memory", "disk", "network", "response_time"],
            "anomaly_detection": True,
            "trend_analysis": True,
            "alert_thresholds": await self.get_alert_thresholds()
        }
        
        response = await self.post("/api/v1/perception/monitor-health", payload)
        return SystemHealth.from_dict(response)
    
    async def detect_anomalies(self, execution_metrics: Dict) -> AnomalyDetection:
        """Detect anomalies in execution metrics"""
        payload = {
            "execution_metrics": execution_metrics,
            "baseline_metrics": await self.get_baseline_metrics(),
            "anomaly_sensitivity": "medium",
            "include_predictive_analysis": True,
            "context_window": "24_hours"
        }
        
        response = await self.post("/api/v1/perception/detect-anomalies", payload)
        return AnomalyDetection.from_dict(response)
    
    async def identify_performance_bottlenecks(self, system_state: Dict) -> BottleneckAnalysis:
        """Identify performance bottlenecks in system"""
        payload = {
            "system_state": system_state,
            "performance_metrics": await self.get_performance_metrics(),
            "resource_utilization": await self.get_resource_utilization(),
            "user_experience_metrics": await self.get_ux_metrics(),
            "analysis_depth": "comprehensive"
        }
        
        response = await self.post("/api/v1/perception/analyze-bottlenecks", payload)
        return BottleneckAnalysis.from_dict(response)
    
    async def assess_quality_degradation(self, current_metrics: Dict, baseline: Dict) -> QualityAssessment:
        """Assess quality degradation compared to baseline"""
        payload = {
            "current_metrics": current_metrics,
            "baseline_metrics": baseline,
            "quality_dimensions": ["performance", "reliability", "usability", "security"],
            "degradation_thresholds": await self.get_quality_thresholds(),
            "trend_analysis_window": "7_days"
        }
        
        response = await self.post("/api/v1/perception/assess-quality", payload)
        return QualityAssessment.from_dict(response)
```

**Real-Time Monitoring Integration**:
```python
class RealTimeMonitor:
    def __init__(self):
        self.perception_service = PerceptionServiceClient(
            service_url=os.getenv("PERCEPTION_SERVICE_URL"),
            api_key=os.getenv("PERCEPTION_SERVICE_API_KEY")
        )
        self.monitoring_active = False
    
    async def start_orchestration_monitoring(self, workflow_id: str):
        """Start real-time monitoring for orchestration workflow"""
        self.monitoring_active = True
        
        while self.monitoring_active:
            # Monitor system health
            system_health = await self.perception_service.monitor_system_health([
                "orchestration_engine", "agent_cluster", "ml_services", "communication_layer"
            ])
            
            # Check for anomalies
            current_metrics = await self.get_current_execution_metrics(workflow_id)
            anomaly_detection = await self.perception_service.detect_anomalies(current_metrics)
            
            # Identify bottlenecks
            system_state = await self.get_system_state()
            bottleneck_analysis = await self.perception_service.identify_performance_bottlenecks(system_state)
            
            # Take action if issues detected
            if system_health.status == "degraded" or anomaly_detection.anomalies_detected:
                await self.handle_system_issues(system_health, anomaly_detection, bottleneck_analysis)
            
            await asyncio.sleep(10)  # Monitor every 10 seconds
    
    async def handle_system_issues(self, health: SystemHealth, anomalies: AnomalyDetection, bottlenecks: BottleneckAnalysis):
        """Handle detected system issues"""
        issues = []
        
        if health.status == "degraded":
            issues.extend(health.issues)
        
        if anomalies.anomalies_detected:
            issues.extend(anomalies.detected_anomalies)
        
        if bottlenecks.bottlenecks_found:
            issues.extend(bottlenecks.bottlenecks)
        
        # Notify coordination service for resource reallocation
        await coordination_service.handle_system_issues(issues)
        
        # Suggest workflow adjustments through reasoning service
        adjustments = await reasoning_service.suggest_workflow_adjustments(issues)
        
        # Apply safe adjustments automatically
        for adjustment in adjustments.safe_adjustments:
            await self.apply_workflow_adjustment(adjustment)
```

## Service Integration Patterns

### 1. Cross-Service Decision Making

```python
async def make_ml_enhanced_decision(decision_context: Dict) -> EnhancedDecision:
    """Make decision using multiple ML services"""
    
    # Get historical patterns from learning service
    historical_patterns = await learning_service.get_patterns(decision_context["type"])
    
    # Get relevant context from memory service
    relevant_context = await memory_service.get_relevant_context(
        agent_id=decision_context["agent_id"],
        task_description=decision_context["task"]
    )
    
    # Analyze with reasoning service
    reasoning_analysis = await reasoning_service.analyze_decision(
        context=relevant_context.content,
        patterns=historical_patterns,
        constraints=decision_context["constraints"]
    )
    
    # Monitor current state with perception service
    current_state = await perception_service.get_system_state()
    
    # Coordinate final decision
    final_decision = await coordination_service.make_coordinated_decision({
        "reasoning_analysis": reasoning_analysis.to_dict(),
        "historical_patterns": [p.to_dict() for p in historical_patterns],
        "current_state": current_state.to_dict(),
        "decision_context": decision_context
    })
    
    return EnhancedDecision(
        decision=final_decision.decision,
        confidence=final_decision.confidence,
        reasoning=reasoning_analysis.explanation,
        supporting_evidence=final_decision.evidence,
        risk_assessment=reasoning_analysis.risks,
        success_probability=final_decision.success_probability
    )
```

### 2. Service Health and Failover

```python
class MLServiceManager:
    def __init__(self):
        self.services = {
            "coordination": CoordinationServiceClient(COORDINATION_URL, COORDINATION_KEY),
            "learning": LearningServiceClient(LEARNING_URL, LEARNING_KEY),
            "memory": MemoryServiceClient(MEMORY_URL, MEMORY_KEY),
            "reasoning": ReasoningServiceClient(REASONING_URL, REASONING_KEY),
            "perception": PerceptionServiceClient(PERCEPTION_URL, PERCEPTION_KEY)
        }
        self.health_status = {}
    
    async def check_service_health(self):
        """Check health of all ML services"""
        for service_name, service_client in self.services.items():
            try:
                health = await service_client.health_check()
                self.health_status[service_name] = {
                    "status": "healthy",
                    "response_time": health.response_time,
                    "last_check": datetime.now()
                }
            except Exception as e:
                self.health_status[service_name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "last_check": datetime.now()
                }
    
    async def get_available_services(self) -> List[str]:
        """Get list of currently available services"""
        await self.check_service_health()
        return [
            service for service, status in self.health_status.items()
            if status["status"] == "healthy"
        ]
    
    async def fallback_decision_making(self, decision_context: Dict, available_services: List[str]) -> Dict:
        """Make decisions with subset of available services"""
        if "reasoning" not in available_services:
            # Use simple rule-based fallback
            return await self.rule_based_decision(decision_context)
        
        if "memory" not in available_services:
            # Use limited context from cache
            decision_context["context"] = await self.get_cached_context(decision_context)
        
        if "learning" not in available_services:
            # Use default patterns
            decision_context["patterns"] = await self.get_default_patterns(decision_context["type"])
        
        # Proceed with available services
        return await self.make_partial_ml_decision(decision_context, available_services)
```

## Performance Optimization

### 1. Service Response Caching

```python
class MLServiceCache:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.cache_ttl = {
            "coordination": 300,  # 5 minutes
            "learning": 3600,     # 1 hour
            "memory": 1800,       # 30 minutes
            "reasoning": 600,     # 10 minutes
            "perception": 60      # 1 minute
        }
    
    async def get_cached_response(self, service: str, method: str, params: Dict) -> Optional[Dict]:
        """Get cached response if available"""
        cache_key = self.generate_cache_key(service, method, params)
        cached_data = await self.redis.get(cache_key)
        
        if cached_data:
            return json.loads(cached_data)
        return None
    
    async def cache_response(self, service: str, method: str, params: Dict, response: Dict):
        """Cache service response"""
        cache_key = self.generate_cache_key(service, method, params)
        ttl = self.cache_ttl.get(service, 300)
        
        await self.redis.setex(
            cache_key,
            ttl,
            json.dumps(response, default=str)
        )
    
    def generate_cache_key(self, service: str, method: str, params: Dict) -> str:
        """Generate cache key for service call"""
        param_hash = hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()
        return f"ml_service_cache:{service}:{method}:{param_hash}"
```

### 2. Async Service Orchestration

```python
async def orchestrate_ml_services_async(decision_context: Dict) -> EnhancedDecision:
    """Orchestrate ML services asynchronously for better performance"""
    
    # Start all service calls concurrently
    tasks = {
        "learning_patterns": learning_service.get_patterns(decision_context["type"]),
        "memory_context": memory_service.get_relevant_context(
            decision_context["agent_id"],
            decision_context["task"]
        ),
        "system_state": perception_service.get_system_state(),
        "baseline_metrics": perception_service.get_baseline_metrics()
    }
    
    # Wait for all services to respond
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    
    # Handle any service failures
    service_results = {}
    for task_name, result in zip(tasks.keys(), results):
        if isinstance(result, Exception):
            logger.warning(f"Service call failed: {task_name} - {result}")
            service_results[task_name] = await get_fallback_result(task_name, decision_context)
        else:
            service_results[task_name] = result
    
    # Use reasoning service to synthesize results
    reasoning_analysis = await reasoning_service.synthesize_ml_results(service_results)
    
    # Final coordination decision
    final_decision = await coordination_service.make_final_decision(
        reasoning_analysis, service_results
    )
    
    return EnhancedDecision.from_ml_results(final_decision, service_results)
```

This comprehensive ML service integration specification provides the technical foundation for implementing the next-generation agentic workflow system with full ML service integration at every decision point.