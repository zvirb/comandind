"""Dynamic Request Handler - Agent Information Gathering System.

This module implements the dynamic agent request framework that allows executing agents
to request additional specialist agents when they discover information gaps during execution.
"""

import asyncio
import time
import uuid
from typing import Dict, Any, List, Optional, Set, Tuple
from enum import Enum
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger(__name__)


class RequestType(str, Enum):
    """Types of dynamic agent requests."""
    RESEARCH = "research"
    VALIDATION = "validation"
    ANALYSIS = "analysis"
    EXPERTISE = "expertise"
    SUPPLEMENTAL_CONTEXT = "supplemental_context"
    DEPENDENCY_ANALYSIS = "dependency_analysis"
    SECURITY_AUDIT = "security_audit"
    PERFORMANCE_ASSESSMENT = "performance_assessment"


class RequestUrgency(str, Enum):
    """Request urgency levels for prioritization."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RequestStatus(str, Enum):
    """Request processing statuses."""
    PENDING = "pending"
    ANALYZING = "analyzing"
    AGENT_SELECTED = "agent_selected"
    CONTEXT_GENERATED = "context_generated"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


@dataclass
class InformationGap:
    """Represents a detected information gap."""
    gap_id: str
    gap_type: str
    description: str
    severity: str  # low, medium, high, critical
    detected_by: str  # agent name
    related_context: Dict[str, Any] = field(default_factory=dict)
    suggested_expertise: List[str] = field(default_factory=list)
    
    @property
    def priority_score(self) -> int:
        """Calculate priority score based on severity and context."""
        severity_scores = {"low": 1, "medium": 3, "high": 7, "critical": 10}
        base_score = severity_scores.get(self.severity, 1)
        
        # Boost score for certain gap types
        if self.gap_type in ["security_vulnerability", "data_corruption", "system_failure"]:
            base_score *= 2
        
        return base_score


@dataclass
class DynamicAgentRequest:
    """Represents a dynamic agent request from an executing agent."""
    request_id: str
    requesting_agent: str
    workflow_id: str
    request_type: RequestType
    urgency: RequestUrgency
    status: RequestStatus = RequestStatus.PENDING
    
    # Request details
    description: str = ""
    specific_expertise_needed: List[str] = field(default_factory=list)
    context_requirements: Dict[str, Any] = field(default_factory=dict)
    information_gaps: List[InformationGap] = field(default_factory=list)
    
    # Response requirements
    expected_output_format: str = "structured_analysis"
    max_response_tokens: int = 4000
    timeout_minutes: int = 30
    
    # Processing metadata
    created_at: float = field(default_factory=time.time)
    analyzed_at: Optional[float] = None
    assigned_agent: Optional[str] = None
    context_package_id: Optional[str] = None
    spawned_workflow_id: Optional[str] = None
    completed_at: Optional[float] = None
    
    # Results
    response_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    confidence_score: float = 0.0
    
    @property
    def is_complete(self) -> bool:
        """Check if request is complete."""
        return self.status in [RequestStatus.COMPLETED, RequestStatus.FAILED, RequestStatus.REJECTED]
    
    @property
    def duration(self) -> Optional[float]:
        """Get request processing duration."""
        if self.completed_at:
            return self.completed_at - self.created_at
        return None
    
    @property
    def priority_score(self) -> int:
        """Calculate request priority score."""
        urgency_scores = {"low": 1, "medium": 3, "high": 7, "critical": 10}
        base_score = urgency_scores.get(self.urgency, 1)
        
        # Factor in information gap priorities
        if self.information_gaps:
            gap_bonus = sum(gap.priority_score for gap in self.information_gaps)
            base_score += gap_bonus
        
        # Time sensitivity bonus
        age_minutes = (time.time() - self.created_at) / 60
        if age_minutes > self.timeout_minutes * 0.8:
            base_score *= 1.5  # Boost priority for time-sensitive requests
        
        return int(base_score)


class InformationGapDetector:
    """ML-enhanced detector for information gaps in agent execution."""
    
    def __init__(self, knowledge_graph_service=None, ml_service=None):
        self.knowledge_graph = knowledge_graph_service
        self.ml_service = ml_service
        
        # Gap detection patterns
        self.gap_patterns = {
            "missing_dependency": [
                "need information about",
                "requires analysis of",
                "depends on understanding",
                "missing context for"
            ],
            "insufficient_expertise": [
                "beyond my expertise",
                "need specialist knowledge",
                "requires domain expert",
                "unfamiliar with"
            ],
            "security_concern": [
                "potential security risk",
                "security validation needed",
                "audit required",
                "vulnerability assessment"
            ],
            "performance_impact": [
                "performance implications",
                "scalability concerns",
                "resource impact",
                "optimization needed"
            ]
        }
    
    async def detect_gaps(
        self,
        agent_name: str,
        task_context: Dict[str, Any],
        execution_log: List[str],
        current_findings: Dict[str, Any]
    ) -> List[InformationGap]:
        """Detect information gaps in agent execution."""
        gaps = []
        
        try:
            # Pattern-based gap detection
            pattern_gaps = await self._detect_pattern_gaps(agent_name, execution_log)
            gaps.extend(pattern_gaps)
            
            # Context-based gap detection
            context_gaps = await self._detect_context_gaps(task_context, current_findings)
            gaps.extend(context_gaps)
            
            # ML-enhanced gap detection
            if self.ml_service:
                ml_gaps = await self._detect_ml_gaps(agent_name, task_context, execution_log)
                gaps.extend(ml_gaps)
            
            # Knowledge graph gap detection
            if self.knowledge_graph:
                kg_gaps = await self._detect_knowledge_gaps(agent_name, current_findings)
                gaps.extend(kg_gaps)
            
            # Deduplicate and prioritize
            gaps = self._deduplicate_gaps(gaps)
            gaps.sort(key=lambda g: g.priority_score, reverse=True)
            
            logger.info(
                "Detected information gaps",
                agent_name=agent_name,
                gap_count=len(gaps),
                high_priority_gaps=sum(1 for g in gaps if g.severity in ["high", "critical"])
            )
            
            return gaps
            
        except Exception as e:
            logger.error("Gap detection failed", agent_name=agent_name, error=str(e))
            return []
    
    async def _detect_pattern_gaps(self, agent_name: str, execution_log: List[str]) -> List[InformationGap]:
        """Detect gaps using pattern matching."""
        gaps = []
        
        for log_entry in execution_log:
            log_lower = log_entry.lower()
            
            for gap_type, patterns in self.gap_patterns.items():
                for pattern in patterns:
                    if pattern in log_lower:
                        gap = InformationGap(
                            gap_id=str(uuid.uuid4()),
                            gap_type=gap_type,
                            description=f"Pattern detected: {pattern}",
                            severity="medium",
                            detected_by=agent_name,
                            related_context={"log_entry": log_entry}
                        )
                        gaps.append(gap)
                        break
        
        return gaps
    
    async def _detect_context_gaps(self, task_context: Dict[str, Any], current_findings: Dict[str, Any]) -> List[InformationGap]:
        """Detect gaps based on context analysis."""
        gaps = []
        
        # Check for missing required context
        required_contexts = ["system_architecture", "dependencies", "security_requirements", "performance_targets"]
        
        for context_type in required_contexts:
            if context_type not in task_context and context_type not in current_findings:
                gap = InformationGap(
                    gap_id=str(uuid.uuid4()),
                    gap_type="missing_context",
                    description=f"Missing {context_type} information",
                    severity="medium",
                    detected_by="context_analyzer",
                    suggested_expertise=self._get_expertise_for_context(context_type)
                )
                gaps.append(gap)
        
        return gaps
    
    async def _detect_ml_gaps(self, agent_name: str, task_context: Dict[str, Any], execution_log: List[str]) -> List[InformationGap]:
        """Use ML to detect subtle information gaps."""
        # Placeholder for ML-based gap detection
        # This would integrate with the ML service for sophisticated analysis
        return []
    
    async def _detect_knowledge_gaps(self, agent_name: str, current_findings: Dict[str, Any]) -> List[InformationGap]:
        """Detect gaps using knowledge graph analysis."""
        # Placeholder for knowledge graph integration
        # This would query the knowledge graph for related information and gaps
        return []
    
    def _deduplicate_gaps(self, gaps: List[InformationGap]) -> List[InformationGap]:
        """Remove duplicate gaps."""
        seen = set()
        unique_gaps = []
        
        for gap in gaps:
            gap_key = (gap.gap_type, gap.description[:50])  # Use truncated description as key
            if gap_key not in seen:
                seen.add(gap_key)
                unique_gaps.append(gap)
        
        return unique_gaps
    
    def _get_expertise_for_context(self, context_type: str) -> List[str]:
        """Get suggested expertise for missing context."""
        expertise_map = {
            "system_architecture": ["codebase-research-analyst", "backend-gateway-expert"],
            "dependencies": ["dependency-analyzer", "schema-database-expert"],
            "security_requirements": ["security-validator", "fullstack-communication-auditor"],
            "performance_targets": ["performance-profiler", "monitoring-analyst"]
        }
        return expertise_map.get(context_type, [])


class AgentSelector:
    """Intelligent agent selection for dynamic requests."""
    
    def __init__(self, agent_registry, performance_monitor=None):
        self.agent_registry = agent_registry
        self.performance_monitor = performance_monitor
        
        # Agent capability mapping
        self.capability_map = {
            RequestType.RESEARCH: [
                "codebase-research-analyst",
                "smart-search-agent",
                "dependency-analyzer"
            ],
            RequestType.VALIDATION: [
                "security-validator",
                "test-automation-engineer",
                "user-experience-auditor"
            ],
            RequestType.ANALYSIS: [
                "performance-profiler",
                "monitoring-analyst",
                "python-refactoring-architect"
            ],
            RequestType.EXPERTISE: [
                "backend-gateway-expert",
                "webui-architect",
                "schema-database-expert"
            ],
            RequestType.SECURITY_AUDIT: [
                "security-validator",
                "fullstack-communication-auditor"
            ],
            RequestType.PERFORMANCE_ASSESSMENT: [
                "performance-profiler",
                "monitoring-analyst"
            ]
        }
    
    async def select_agent(self, request: DynamicAgentRequest) -> Optional[str]:
        """Select optimal agent for dynamic request."""
        try:
            # Get candidate agents based on request type
            candidates = self.capability_map.get(request.request_type, [])
            
            # Filter by specific expertise if requested
            if request.specific_expertise_needed:
                filtered_candidates = []
                for agent in candidates:
                    agent_info = await self.agent_registry.get_agent_info(agent)
                    if agent_info and any(
                        expertise in agent_info.get("capabilities", [])
                        for expertise in request.specific_expertise_needed
                    ):
                        filtered_candidates.append(agent)
                candidates = filtered_candidates or candidates  # Fallback to original if no matches
            
            # Check agent availability
            available_agents = []
            for agent in candidates:
                if await self.agent_registry.is_agent_available(agent):
                    available_agents.append(agent)
            
            if not available_agents:
                logger.warning(
                    "No available agents for request",
                    request_type=request.request_type,
                    candidates=candidates
                )
                return None
            
            # Select best agent based on performance and workload
            best_agent = await self._select_best_agent(available_agents, request)
            
            logger.info(
                "Selected agent for dynamic request",
                request_id=request.request_id,
                selected_agent=best_agent,
                candidates_count=len(available_agents)
            )
            
            return best_agent
            
        except Exception as e:
            logger.error("Agent selection failed", request_id=request.request_id, error=str(e))
            return None
    
    async def _select_best_agent(self, candidates: List[str], request: DynamicAgentRequest) -> str:
        """Select the best agent from candidates."""
        if len(candidates) == 1:
            return candidates[0]
        
        # Score agents based on multiple factors
        agent_scores = {}
        
        for agent in candidates:
            score = 0
            
            # Base capability score
            score += 10
            
            # Workload penalty (prefer less busy agents)
            workload = await self._get_agent_workload(agent)
            score -= workload * 2
            
            # Performance bonus (prefer historically successful agents)
            if self.performance_monitor:
                performance = await self.performance_monitor.get_agent_performance(agent)
                score += performance.get("success_rate", 0.5) * 10
            
            # Urgency factor (prefer faster agents for urgent requests)
            if request.urgency in [RequestUrgency.HIGH, RequestUrgency.CRITICAL]:
                avg_time = await self._get_agent_avg_response_time(agent)
                if avg_time and avg_time < 300:  # Less than 5 minutes
                    score += 5
            
            agent_scores[agent] = score
        
        # Return agent with highest score
        best_agent = max(agent_scores, key=agent_scores.get)
        return best_agent
    
    async def _get_agent_workload(self, agent_name: str) -> int:
        """Get current workload for agent."""
        # This would integrate with the orchestrator's workload tracking
        return 0  # Placeholder
    
    async def _get_agent_avg_response_time(self, agent_name: str) -> Optional[float]:
        """Get average response time for agent."""
        # This would query performance metrics
        return None  # Placeholder


class DynamicRequestHandler:
    """Main handler for dynamic agent requests."""
    
    def __init__(
        self,
        agent_registry,
        context_generator,
        orchestrator,
        workflow_manager,
        redis_service=None
    ):
        self.agent_registry = agent_registry
        self.context_generator = context_generator
        self.orchestrator = orchestrator
        self.workflow_manager = workflow_manager
        self.redis_service = redis_service
        
        # Initialize components
        self.gap_detector = InformationGapDetector()
        self.agent_selector = AgentSelector(agent_registry)
        
        # Request tracking
        self.active_requests: Dict[str, DynamicAgentRequest] = {}
        self.request_queue: List[str] = []
        
        # Processing control
        self._processing = False
        self._processing_task: Optional[asyncio.Task] = None
        
        # Metrics
        self.metrics = {
            "total_requests": 0,
            "completed_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0.0,
            "agent_spawn_rate": 0.0
        }
    
    async def initialize(self) -> None:
        """Initialize the dynamic request handler."""
        logger.info("Initializing Dynamic Request Handler...")
        
        # Start processing loop
        await self.start_processing()
        
        logger.info("Dynamic Request Handler initialized")
    
    async def create_agent_request(
        self,
        requesting_agent: str,
        workflow_id: str,
        request_type: RequestType,
        description: str,
        urgency: RequestUrgency = RequestUrgency.MEDIUM,
        specific_expertise: List[str] = None,
        context_requirements: Dict[str, Any] = None
    ) -> str:
        """Create a new dynamic agent request."""
        try:
            request_id = str(uuid.uuid4())
            
            request = DynamicAgentRequest(
                request_id=request_id,
                requesting_agent=requesting_agent,
                workflow_id=workflow_id,
                request_type=request_type,
                urgency=urgency,
                description=description,
                specific_expertise_needed=specific_expertise or [],
                context_requirements=context_requirements or {}
            )
            
            # Store request
            self.active_requests[request_id] = request
            self.request_queue.append(request_id)
            
            # Update metrics
            self.metrics["total_requests"] += 1
            
            logger.info(
                "Created dynamic agent request",
                request_id=request_id,
                requesting_agent=requesting_agent,
                request_type=request_type,
                urgency=urgency
            )
            
            return request_id
            
        except Exception as e:
            logger.error("Failed to create agent request", error=str(e))
            raise
    
    async def detect_information_gaps(
        self,
        agent_name: str,
        task_context: Dict[str, Any],
        execution_log: List[str],
        current_findings: Dict[str, Any]
    ) -> List[InformationGap]:
        """Detect information gaps for an agent."""
        return await self.gap_detector.detect_gaps(
            agent_name, task_context, execution_log, current_findings
        )
    
    async def auto_create_requests_for_gaps(
        self,
        requesting_agent: str,
        workflow_id: str,
        information_gaps: List[InformationGap]
    ) -> List[str]:
        """Automatically create requests for detected information gaps."""
        request_ids = []
        
        for gap in information_gaps:
            # Determine request type from gap type
            request_type = self._gap_type_to_request_type(gap.gap_type)
            
            # Determine urgency from gap severity
            urgency = self._severity_to_urgency(gap.severity)
            
            # Create request
            request_id = await self.create_agent_request(
                requesting_agent=requesting_agent,
                workflow_id=workflow_id,
                request_type=request_type,
                description=f"Address information gap: {gap.description}",
                urgency=urgency,
                specific_expertise=gap.suggested_expertise,
                context_requirements=gap.related_context
            )
            
            # Add gap to request
            request = self.active_requests[request_id]
            request.information_gaps.append(gap)
            
            request_ids.append(request_id)
        
        return request_ids
    
    async def get_request_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a dynamic request."""
        request = self.active_requests.get(request_id)
        if not request:
            return None
        
        return {
            "request_id": request_id,
            "status": request.status,
            "assigned_agent": request.assigned_agent,
            "progress_percentage": self._calculate_progress(request),
            "estimated_completion": self._estimate_completion(request),
            "response_available": request.response_data is not None
        }
    
    async def get_request_response(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get response data for a completed request."""
        request = self.active_requests.get(request_id)
        if not request or not request.is_complete:
            return None
        
        return {
            "request_id": request_id,
            "status": request.status,
            "response_data": request.response_data,
            "confidence_score": request.confidence_score,
            "processing_duration": request.duration,
            "assigned_agent": request.assigned_agent
        }
    
    async def start_processing(self) -> None:
        """Start the request processing loop."""
        if self._processing:
            return
        
        self._processing = True
        self._processing_task = asyncio.create_task(self._process_requests_loop())
        logger.info("Started dynamic request processing")
    
    async def stop_processing(self) -> None:
        """Stop the request processing loop."""
        self._processing = False
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped dynamic request processing")
    
    async def _process_requests_loop(self) -> None:
        """Main request processing loop."""
        while self._processing:
            try:
                await self._process_pending_requests()
                await self._check_completed_requests()
                await self._handle_timeouts()
                await asyncio.sleep(2)  # Process every 2 seconds
                
            except Exception as e:
                logger.error("Error in request processing loop", error=str(e))
                await asyncio.sleep(5)
    
    async def _process_pending_requests(self) -> None:
        """Process pending requests in priority order."""
        if not self.request_queue:
            return
        
        # Sort queue by priority
        self.request_queue.sort(
            key=lambda rid: self.active_requests[rid].priority_score,
            reverse=True
        )
        
        # Process high-priority requests
        for request_id in list(self.request_queue):
            request = self.active_requests.get(request_id)
            if not request or request.status != RequestStatus.PENDING:
                if request_id in self.request_queue:
                    self.request_queue.remove(request_id)
                continue
            
            # Process request
            await self._process_request(request)
            
            # Remove from queue
            if request_id in self.request_queue:
                self.request_queue.remove(request_id)
    
    async def _process_request(self, request: DynamicAgentRequest) -> None:
        """Process a single dynamic request."""
        try:
            request.status = RequestStatus.ANALYZING
            request.analyzed_at = time.time()
            
            # Select appropriate agent
            selected_agent = await self.agent_selector.select_agent(request)
            if not selected_agent:
                request.status = RequestStatus.REJECTED
                request.error_message = "No suitable agent available"
                request.completed_at = time.time()
                return
            
            request.assigned_agent = selected_agent
            request.status = RequestStatus.AGENT_SELECTED
            
            # Generate context package
            context_package_id = await self._generate_request_context(request)
            request.context_package_id = context_package_id
            request.status = RequestStatus.CONTEXT_GENERATED
            
            # Spawn agent execution
            spawned_workflow_id = await self._spawn_agent_execution(request)
            request.spawned_workflow_id = spawned_workflow_id
            request.status = RequestStatus.EXECUTING
            
            logger.info(
                "Processing dynamic request",
                request_id=request.request_id,
                assigned_agent=selected_agent,
                spawned_workflow=spawned_workflow_id
            )
            
        except Exception as e:
            request.status = RequestStatus.FAILED
            request.error_message = str(e)
            request.completed_at = time.time()
            logger.error("Request processing failed", request_id=request.request_id, error=str(e))
    
    async def _generate_request_context(self, request: DynamicAgentRequest) -> str:
        """Generate context package for request."""
        try:
            # Gather context from requesting agent and workflow
            workflow_context = await self.workflow_manager.get_workflow_context(request.workflow_id)
            
            # Create specialized context for the request
            specialized_context = {
                "request_details": {
                    "description": request.description,
                    "urgency": request.urgency,
                    "information_gaps": [gap.__dict__ for gap in request.information_gaps],
                    "requesting_agent": request.requesting_agent
                },
                "workflow_context": workflow_context,
                "context_requirements": request.context_requirements,
                "expected_output": {
                    "format": request.expected_output_format,
                    "max_tokens": request.max_response_tokens
                }
            }
            
            # Generate context package
            context_package_id = await self.context_generator.generate_context_package(
                agent_name=request.assigned_agent,
                workflow_id=request.workflow_id,
                task_context=specialized_context,
                requirements={"max_tokens": request.max_response_tokens}
            )
            
            return context_package_id
            
        except Exception as e:
            logger.error("Context generation failed", request_id=request.request_id, error=str(e))
            raise
    
    async def _spawn_agent_execution(self, request: DynamicAgentRequest) -> str:
        """Spawn agent execution for the request."""
        try:
            # Create sub-workflow for agent execution
            workflow_config = {
                "workflow_type": "dynamic_agent_request",
                "name": f"Dynamic Request: {request.description[:50]}",
                "required_agents": [request.assigned_agent],
                "priority": "high" if request.urgency in [RequestUrgency.HIGH, RequestUrgency.CRITICAL] else "medium",
                "timeout_minutes": request.timeout_minutes,
                "parent_workflow_id": request.workflow_id,
                "request_id": request.request_id,
                "context": {
                    "dynamic_request": True,
                    "context_package_id": request.context_package_id,
                    "expected_output_format": request.expected_output_format
                }
            }
            
            # Create workflow through orchestrator
            spawned_workflow = await self.orchestrator.create_workflow(
                workflow_id=str(uuid.uuid4()),
                workflow_config=workflow_config,
                background_tasks=None  # Handle synchronously for dynamic requests
            )
            
            return spawned_workflow["workflow_id"]
            
        except Exception as e:
            logger.error("Agent spawning failed", request_id=request.request_id, error=str(e))
            raise
    
    async def _check_completed_requests(self) -> None:
        """Check for completed dynamic requests."""
        for request in list(self.active_requests.values()):
            if request.status == RequestStatus.EXECUTING and request.spawned_workflow_id:
                # Check spawned workflow status
                workflow_status = await self.workflow_manager.get_workflow_status(request.spawned_workflow_id)
                
                if workflow_status and workflow_status.get("status") == "completed":
                    # Extract results
                    await self._extract_request_results(request, workflow_status)
                    
                elif workflow_status and workflow_status.get("status") in ["failed", "cancelled"]:
                    request.status = RequestStatus.FAILED
                    request.error_message = "Spawned workflow failed"
                    request.completed_at = time.time()
    
    async def _extract_request_results(self, request: DynamicAgentRequest, workflow_status: Dict[str, Any]) -> None:
        """Extract results from completed spawned workflow."""
        try:
            # Get workflow results
            workflow_results = workflow_status.get("results", {})
            agent_results = workflow_results.get(request.assigned_agent, {})
            
            # Process and structure response
            response_data = {
                "analysis": agent_results.get("analysis", {}),
                "findings": agent_results.get("findings", {}),
                "recommendations": agent_results.get("recommendations", []),
                "confidence_metrics": agent_results.get("confidence", {}),
                "metadata": {
                    "agent_used": request.assigned_agent,
                    "processing_time": request.duration,
                    "workflow_id": request.spawned_workflow_id
                }
            }
            
            # Calculate confidence score
            confidence_score = agent_results.get("confidence", {}).get("overall", 0.8)
            
            # Update request
            request.response_data = response_data
            request.confidence_score = confidence_score
            request.status = RequestStatus.COMPLETED
            request.completed_at = time.time()
            
            # Update metrics
            self.metrics["completed_requests"] += 1
            if request.duration:
                total_time = self.metrics["avg_response_time"] * (self.metrics["completed_requests"] - 1)
                self.metrics["avg_response_time"] = (total_time + request.duration) / self.metrics["completed_requests"]
            
            logger.info(
                "Dynamic request completed",
                request_id=request.request_id,
                assigned_agent=request.assigned_agent,
                confidence_score=confidence_score,
                duration_minutes=request.duration / 60 if request.duration else 0
            )
            
        except Exception as e:
            request.status = RequestStatus.FAILED
            request.error_message = f"Result extraction failed: {str(e)}"
            request.completed_at = time.time()
            logger.error("Result extraction failed", request_id=request.request_id, error=str(e))
    
    async def _handle_timeouts(self) -> None:
        """Handle request timeouts."""
        current_time = time.time()
        
        for request in list(self.active_requests.values()):
            if not request.is_complete:
                timeout_threshold = request.created_at + (request.timeout_minutes * 60)
                
                if current_time > timeout_threshold:
                    request.status = RequestStatus.FAILED
                    request.error_message = "Request timed out"
                    request.completed_at = current_time
                    
                    # Cancel spawned workflow if exists
                    if request.spawned_workflow_id:
                        try:
                            await self.workflow_manager.cancel_workflow(request.spawned_workflow_id)
                        except Exception as e:
                            logger.warning("Failed to cancel timed out workflow", error=str(e))
                    
                    logger.warning(
                        "Dynamic request timed out",
                        request_id=request.request_id,
                        timeout_minutes=request.timeout_minutes
                    )
    
    def _gap_type_to_request_type(self, gap_type: str) -> RequestType:
        """Convert gap type to request type."""
        mapping = {
            "missing_dependency": RequestType.DEPENDENCY_ANALYSIS,
            "insufficient_expertise": RequestType.EXPERTISE,
            "security_concern": RequestType.SECURITY_AUDIT,
            "performance_impact": RequestType.PERFORMANCE_ASSESSMENT,
            "missing_context": RequestType.SUPPLEMENTAL_CONTEXT
        }
        return mapping.get(gap_type, RequestType.RESEARCH)
    
    def _severity_to_urgency(self, severity: str) -> RequestUrgency:
        """Convert gap severity to request urgency."""
        mapping = {
            "low": RequestUrgency.LOW,
            "medium": RequestUrgency.MEDIUM,
            "high": RequestUrgency.HIGH,
            "critical": RequestUrgency.CRITICAL
        }
        return mapping.get(severity, RequestUrgency.MEDIUM)
    
    def _calculate_progress(self, request: DynamicAgentRequest) -> float:
        """Calculate request progress percentage."""
        status_progress = {
            RequestStatus.PENDING: 0.0,
            RequestStatus.ANALYZING: 20.0,
            RequestStatus.AGENT_SELECTED: 40.0,
            RequestStatus.CONTEXT_GENERATED: 60.0,
            RequestStatus.EXECUTING: 80.0,
            RequestStatus.COMPLETED: 100.0,
            RequestStatus.FAILED: 100.0,
            RequestStatus.REJECTED: 100.0
        }
        return status_progress.get(request.status, 0.0)
    
    def _estimate_completion(self, request: DynamicAgentRequest) -> Optional[float]:
        """Estimate completion time for request."""
        if request.is_complete:
            return None
        
        # Base estimation on request type and urgency
        base_minutes = {
            RequestType.RESEARCH: 15,
            RequestType.VALIDATION: 10,
            RequestType.ANALYSIS: 20,
            RequestType.EXPERTISE: 25,
            RequestType.SECURITY_AUDIT: 30,
            RequestType.PERFORMANCE_ASSESSMENT: 20
        }.get(request.request_type, 15)
        
        # Adjust for urgency
        urgency_multiplier = {
            RequestUrgency.LOW: 1.5,
            RequestUrgency.MEDIUM: 1.0,
            RequestUrgency.HIGH: 0.7,
            RequestUrgency.CRITICAL: 0.5
        }.get(request.urgency, 1.0)
        
        estimated_minutes = base_minutes * urgency_multiplier
        return time.time() + (estimated_minutes * 60)
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get dynamic request handler metrics."""
        active_count = len([r for r in self.active_requests.values() if not r.is_complete])
        
        return {
            **self.metrics,
            "active_requests": active_count,
            "queued_requests": len(self.request_queue),
            "success_rate": (
                self.metrics["completed_requests"] / self.metrics["total_requests"]
                if self.metrics["total_requests"] > 0 else 0
            )
        }
    
    async def shutdown(self) -> None:
        """Shutdown the dynamic request handler."""
        logger.info("Shutting down Dynamic Request Handler...")
        await self.stop_processing()
        logger.info("Dynamic Request Handler shutdown complete")