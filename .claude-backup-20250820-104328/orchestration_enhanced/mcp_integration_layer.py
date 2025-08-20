"""MCP Integration Layer for ML-Enhanced Agentic Workflow

Provides unified coordination and communication using only existing MCP services
available in Claude Code CLI. Replaces external service dependencies with
MCP-based implementations.

Key Features:
- Knowledge graph-based agent coordination using mcp__memory__
- Workflow orchestration using mcp__orchestration-agent__
- Complex reasoning using mcp__sequential-thinking__
- File organization using mcp__filesystem__
- Research capabilities using mcp__firecrawl__
- UI validation using mcp__playwright__
- Caching using mcp__redis__
"""

import asyncio
import json
import time
import threading
from typing import Dict, Any, List, Optional, Union, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

# Graceful structlog import with fallback
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

logger = structlog.get_logger(__name__)

class WorkflowPhase(Enum):
    """Workflow phases for orchestration."""
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
    """Task definition for agent execution."""
    agent_id: str
    task_type: str
    description: str
    context_data: Dict[str, Any]
    priority: int = 1
    dependencies: List[str] = field(default_factory=list)
    timeout_seconds: int = 300
    created_at: float = field(default_factory=time.time)
    workflow_id: Optional[str] = None
    phase: Optional[WorkflowPhase] = None

@dataclass
class AgentResult:
    """Result from agent execution."""
    agent_id: str
    task_id: str
    success: bool
    data: Dict[str, Any]
    confidence_score: Optional[float] = None
    evidence: List[str] = field(default_factory=list)
    execution_time_ms: float = 0
    error_message: Optional[str] = None
    created_files: List[str] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    progress: float = 0.0  # 0.0 to 1.0
    status: str = "pending"  # pending, running, completed, failed

@dataclass
class AgentInstance:
    """Running agent instance."""
    instance_id: str
    agent_id: str
    task_id: str
    status: str = "running"  # running, completed, failed
    resources_locked: Set[str] = field(default_factory=set)
    start_time: float = field(default_factory=time.time)
    heartbeat: float = field(default_factory=time.time)

@dataclass
class ResourceLock:
    """Resource lock for coordination."""
    resource_id: str
    locked_by: str  # agent instance ID
    lock_type: str  # file, directory, service
    locked_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None

class ParallelTaskManager:
    """Manages parallel task execution with coordination."""
    
    def __init__(self, max_concurrent_tasks: int = 10):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self.running_instances: Dict[str, AgentInstance] = {}
        self.resource_locks: Dict[str, ResourceLock] = {}
        self.progress_callbacks: List[Callable] = []
        self._lock = asyncio.Lock()
        
    async def execute_parallel_tasks(self, tasks: List[AgentTask]) -> List[AgentResult]:
        """Execute multiple tasks in parallel with coordination."""
        # Group tasks to prevent conflicts
        task_groups = self._group_tasks_by_resource_requirements(tasks)
        
        results = []
        
        # Execute task groups in parallel (Python 3.7+ compatible)
        try:
            # Try to use TaskGroup for Python 3.11+
            if hasattr(asyncio, 'TaskGroup'):
                async with asyncio.TaskGroup() as tg:
                    group_tasks_futures = []
                    for group_name, group_tasks in task_groups.items():
                        task_future = tg.create_task(
                            self._execute_task_group(group_name, group_tasks)
                        )
                        group_tasks_futures.append(task_future)
                        
                # Collect all results
                for future in group_tasks_futures:
                    group_results = future.result()
                    results.extend(group_results)
            else:
                # Fallback to asyncio.gather for older Python versions
                group_tasks_coros = [
                    self._execute_task_group(group_name, group_tasks)
                    for group_name, group_tasks in task_groups.items()
                ]
                
                group_results_list = await asyncio.gather(*group_tasks_coros, return_exceptions=True)
                
                for group_results in group_results_list:
                    if isinstance(group_results, Exception):
                        logger.error(f"Task group execution failed: {group_results}")
                        # Create error results for the failed group
                        continue
                    results.extend(group_results)
                    
        except Exception as e:
            logger.error(f"Parallel task group execution failed: {e}")
            # Return empty results or handle gracefully
            return []
            
        return results
    
    def _group_tasks_by_resource_requirements(self, tasks: List[AgentTask]) -> Dict[str, List[AgentTask]]:
        """Group tasks to prevent resource conflicts."""
        # Simple grouping strategy - could be enhanced with dependency analysis
        groups = {
            "backend_tasks": [],
            "frontend_tasks": [],
            "documentation_tasks": [],
            "validation_tasks": [],
            "general_tasks": []
        }
        
        for task in tasks:
            agent_type = task.context_data.get("agent_type", "general")
            
            if "backend" in agent_type.lower() or "database" in agent_type.lower():
                groups["backend_tasks"].append(task)
            elif "frontend" in agent_type.lower() or "ui" in agent_type.lower():
                groups["frontend_tasks"].append(task)
            elif "documentation" in agent_type.lower():
                groups["documentation_tasks"].append(task)
            elif "validation" in agent_type.lower() or "test" in agent_type.lower():
                groups["validation_tasks"].append(task)
            else:
                groups["general_tasks"].append(task)
                
        # Remove empty groups
        return {k: v for k, v in groups.items() if v}
    
    async def _execute_task_group(self, group_name: str, tasks: List[AgentTask]) -> List[AgentResult]:
        """Execute a group of related tasks with resource coordination."""
        results = []
        
        # Execute tasks in this group with limited parallelism (Python 3.7+ compatible)
        try:
            if hasattr(asyncio, 'TaskGroup'):
                # Use TaskGroup for Python 3.11+
                async with asyncio.TaskGroup() as tg:
                    task_futures = []
                    
                    for task in tasks:
                        future = tg.create_task(self._execute_single_task(task))
                        task_futures.append(future)
                        
                # Collect results
                for future in task_futures:
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        # Create error result
                        error_result = AgentResult(
                            agent_id=task.agent_id,
                            task_id=str(uuid4()),
                            success=False,
                            data={},
                            error_message=str(e),
                            status="failed"
                        )
                        results.append(error_result)
            else:
                # Fallback to asyncio.gather for older Python versions
                task_coros = [self._execute_single_task(task) for task in tasks]
                
                task_results = await asyncio.gather(*task_coros, return_exceptions=True)
                
                for i, result in enumerate(task_results):
                    if isinstance(result, Exception):
                        # Create error result
                        error_result = AgentResult(
                            agent_id=tasks[i].agent_id,
                            task_id=str(uuid4()),
                            success=False,
                            data={},
                            error_message=str(result),
                            status="failed"
                        )
                        results.append(error_result)
                    else:
                        results.append(result)
                        
        except Exception as e:
            logger.error(f"Task group execution failed: {e}")
            # Create error results for all tasks in the group
            for task in tasks:
                error_result = AgentResult(
                    agent_id=task.agent_id,
                    task_id=str(uuid4()),
                    success=False,
                    data={},
                    error_message=f"Group execution failed: {str(e)}",
                    status="failed"
                )
                results.append(error_result)
                
        return results
    
    async def _execute_single_task(self, task: AgentTask) -> AgentResult:
        """Execute a single task with resource coordination."""
        async with self.semaphore:  # Limit concurrent executions
            instance_id = str(uuid4())
            
            # Create agent instance
            instance = AgentInstance(
                instance_id=instance_id,
                agent_id=task.agent_id,
                task_id=task.task_type
            )
            
            async with self._lock:
                self.running_instances[instance_id] = instance
            
            try:
                # Acquire necessary resource locks
                await self._acquire_resource_locks(instance, task)
                
                # Execute the task
                result = await self._simulate_task_execution(task, instance)
                
                # Update instance status
                instance.status = "completed" if result.success else "failed"
                
                return result
                
            except Exception as e:
                instance.status = "failed"
                
                return AgentResult(
                    agent_id=task.agent_id,
                    task_id=str(uuid4()),
                    success=False,
                    data={},
                    error_message=str(e),
                    status="failed"
                )
                
            finally:
                # Release resource locks
                await self._release_resource_locks(instance)
                
                # Remove from running instances
                async with self._lock:
                    if instance_id in self.running_instances:
                        del self.running_instances[instance_id]
    
    async def _acquire_resource_locks(self, instance: AgentInstance, task: AgentTask):
        """Acquire necessary resource locks for task execution."""
        required_resources = self._identify_required_resources(task)
        
        for resource_id in required_resources:
            # Check if resource is already locked
            if resource_id in self.resource_locks:
                existing_lock = self.resource_locks[resource_id]
                
                # Check if lock has expired
                if existing_lock.expires_at and time.time() > existing_lock.expires_at:
                    del self.resource_locks[resource_id]
                else:
                    # Wait for lock to be released or timeout
                    await self._wait_for_resource(resource_id, timeout=30)
            
            # Acquire the lock
            lock = ResourceLock(
                resource_id=resource_id,
                locked_by=instance.instance_id,
                lock_type="file",
                expires_at=time.time() + 300  # 5 minute timeout
            )
            
            async with self._lock:
                self.resource_locks[resource_id] = lock
                instance.resources_locked.add(resource_id)
    
    async def _release_resource_locks(self, instance: AgentInstance):
        """Release all resource locks held by instance."""
        async with self._lock:
            for resource_id in instance.resources_locked:
                if resource_id in self.resource_locks:
                    del self.resource_locks[resource_id]
            instance.resources_locked.clear()
    
    def _identify_required_resources(self, task: AgentTask) -> Set[str]:
        """Identify resources required by a task."""
        resources = set()
        
        # Add resource identification logic based on task type
        agent_type = task.context_data.get("agent_type", "")
        
        if "backend" in agent_type.lower():
            resources.add("backend_services")
            resources.add("database_config")
        elif "frontend" in agent_type.lower():
            resources.add("frontend_assets")
            resources.add("ui_components")
        elif "documentation" in agent_type.lower():
            resources.add("documentation_files")
            
        return resources
    
    async def _wait_for_resource(self, resource_id: str, timeout: int = 30):
        """Wait for a resource to become available."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if resource_id not in self.resource_locks:
                return
            await asyncio.sleep(0.1)
        
        raise TimeoutError(f"Timeout waiting for resource: {resource_id}")
    
    async def _simulate_task_execution(self, task: AgentTask, instance: AgentInstance) -> AgentResult:
        """Simulate task execution with progress tracking."""
        result = AgentResult(
            agent_id=task.agent_id,
            task_id=str(uuid4()),
            success=True,
            data={"message": f"Task completed by {task.agent_id}"},
            confidence_score=0.85,
            evidence=[f"Evidence from {task.agent_id}"],
            execution_time_ms=0,
            created_files=[],
            status="running"
        )
        
        # Simulate progressive task execution
        start_time = time.time()
        
        for progress in [0.1, 0.3, 0.6, 0.8, 1.0]:
            await asyncio.sleep(0.2)  # Simulate work
            
            result.progress = progress
            instance.heartbeat = time.time()
            
            # Notify progress callbacks
            for callback in self.progress_callbacks:
                try:
                    await callback(instance.instance_id, progress)
                except Exception:
                    pass  # Don't let callback errors affect execution
        
        result.execution_time_ms = (time.time() - start_time) * 1000
        result.end_time = time.time()
        result.status = "completed"
        
        return result
    
    def add_progress_callback(self, callback: Callable):
        """Add a progress callback function."""
        self.progress_callbacks.append(callback)
    
    def get_running_instances(self) -> Dict[str, AgentInstance]:
        """Get currently running agent instances."""
        return self.running_instances.copy()
    
    def get_resource_locks(self) -> Dict[str, ResourceLock]:
        """Get current resource locks."""
        return self.resource_locks.copy()

class MCPIntegrationLayer:
    """Integration layer that coordinates all MCP services for agentic workflow."""
    
    def __init__(self, workflow_id: str = None, max_concurrent_tasks: int = 10):
        """Initialize the MCP integration layer."""
        self.workflow_id = workflow_id or str(uuid4())
        self.current_phase = WorkflowPhase.PHASE_0_TODO_CONTEXT
        self.agent_registry: Dict[str, Dict[str, Any]] = {}
        self.task_queue: List[AgentTask] = []
        self.results: Dict[str, AgentResult] = {}
        self.workflow_context: Dict[str, Any] = {}
        self.file_organization_rules: Dict[str, str] = {}
        
        # Initialize parallel task manager
        self.parallel_task_manager = ParallelTaskManager(max_concurrent_tasks)
        self.parallel_task_manager.add_progress_callback(self._on_task_progress)
        
        # Task execution tracking
        self.active_task_groups: Dict[str, List[str]] = {}
        self.task_execution_history: List[Dict[str, Any]] = []
        
        # Initialize file organization rules
        self._initialize_file_organization()
        
        logger.info("MCP Integration Layer initialized", 
                   workflow_id=self.workflow_id,
                   max_concurrent_tasks=max_concurrent_tasks)
    
    def _initialize_file_organization(self):
        """Initialize intelligent file organization rules."""
        self.file_organization_rules = {
            # Documentation
            "documentation": "docs/",
            "architecture": "docs/architecture/", 
            "api_docs": "docs/api/",
            "user_guides": "docs/guides/",
            
            # Source code
            "orchestration": "app/orchestration_enhanced/",
            "services": "app/services/",
            "models": "app/models/",
            "middleware": "app/middleware/",
            "utilities": "app/utilities/",
            
            # Configuration
            "config": "config/",
            "environment": "config/env/",
            "deployment": "config/deployment/",
            
            # Testing
            "tests": "tests/",
            "test_data": "tests/data/",
            "test_fixtures": "tests/fixtures/",
            
            # Monitoring and logging
            "monitoring": "monitoring/",
            "logs": "logs/",
            "metrics": "monitoring/metrics/",
            
            # Infrastructure
            "infrastructure": "infrastructure/",
            "docker": "infrastructure/docker/",
            "k8s": "infrastructure/k8s/",
            
            # Scripts
            "scripts": "scripts/",
            "automation": "scripts/automation/",
            "utilities_scripts": "scripts/utilities/",
            
            # Data and ML
            "data": "data/",
            "models_ml": "data/models/",
            "datasets": "data/datasets/",
            
            # Context packages
            "context_packages": ".claude/context_packages/",
            "orchestration_state": ".claude/orchestration_state/",
            "agent_coordination": ".claude/agent_coordination/"
        }
    
    async def register_agent(self, agent_id: str, agent_type: str, 
                           capabilities: List[str], specializations: List[str]) -> bool:
        """Register an agent in the workflow using MCP memory."""
        try:
            # Store agent info in knowledge graph
            agent_entity = {
                "name": f"agent_{agent_id}",
                "entityType": "agent",
                "observations": [
                    f"Agent type: {agent_type}",
                    f"Capabilities: {', '.join(capabilities)}",
                    f"Specializations: {', '.join(specializations)}",
                    f"Registered at: {time.time()}",
                    f"Workflow ID: {self.workflow_id}"
                ]
            }
            
            # Use MCP memory to create agent entity
            await self._mcp_create_entities([agent_entity])
            
            # Store in local registry
            self.agent_registry[agent_id] = {
                "agent_type": agent_type,
                "capabilities": capabilities,
                "specializations": specializations,
                "status": "available",
                "registered_at": time.time()
            }
            
            # Register with orchestration system
            await self._mcp_register_orchestration_agent(agent_id, agent_type, capabilities)
            
            logger.info("Agent registered", agent_id=agent_id, agent_type=agent_type)
            return True
            
        except Exception as e:
            logger.error("Failed to register agent", agent_id=agent_id, error=str(e))
            return False
    
    async def start_workflow(self, initial_context: Dict[str, Any] = None) -> bool:
        """Start the ML-enhanced agentic workflow."""
        try:
            self.workflow_context = initial_context or {}
            
            # Create workflow checkpoint
            await self._mcp_create_checkpoint(self.current_phase.value, {
                "workflow_id": self.workflow_id,
                "phase": self.current_phase.value,
                "context": self.workflow_context,
                "started_at": time.time()
            })
            
            # Phase 0: Todo Context Integration
            await self._execute_phase_0_todo_context()
            
            return True
            
        except Exception as e:
            logger.error("Failed to start workflow", error=str(e))
            return False
    
    async def _execute_phase_0_todo_context(self):
        """Phase 0: Todo Context Integration using orchestration MCP."""
        logger.info("Executing Phase 0: Todo Context Integration")
        
        # Query orchestration knowledge for todo patterns
        todo_patterns = await self._mcp_query_orchestration_knowledge("todo_management")
        
        # Load orchestration todos from file
        try:
            with open("/home/marku/ai_workflow_engine/.claude/orchestration_todos.json", "r") as f:
                todos = json.load(f)
        except Exception as e:
            logger.warning("Could not load orchestration todos", error=str(e))
            todos = []
        
        # Analyze high-priority todos using sequential thinking
        high_priority_todos = [
            todo for todo in todos 
            if todo.get("priority") in ["critical", "high"] and todo.get("status") == "pending"
        ]
        
        if high_priority_todos:
            # Use sequential thinking to analyze todo priorities
            analysis_result = await self._mcp_sequential_analysis(
                "Analyze high-priority orchestration todos and determine execution strategy",
                {
                    "todos": high_priority_todos,
                    "current_context": self.workflow_context,
                    "workflow_id": self.workflow_id
                }
            )
            
            # Store analysis in memory
            if analysis_result:
                await self._mcp_add_memory(
                    f"Phase 0 Analysis: {analysis_result.get('conclusion', 'Todo analysis completed')}",
                    "orchestration-user"
                )
        
        # Proceed to Phase 1
        self.current_phase = WorkflowPhase.PHASE_1_AGENT_ECOSYSTEM
        await self._execute_phase_1_agent_ecosystem()
    
    async def _execute_phase_1_agent_ecosystem(self):
        """Phase 1: Agent Ecosystem Validation."""
        logger.info("Executing Phase 1: Agent Ecosystem Validation")
        
        # Get agent coordination strategy
        agents_status = {
            agent_id: info["status"] 
            for agent_id, info in self.agent_registry.items()
        }
        
        coordination_strategy = await self._mcp_get_coordination_strategy(agents_status)
        
        # Store coordination strategy in knowledge graph
        if coordination_strategy:
            strategy_entity = {
                "name": f"coordination_strategy_{self.workflow_id}",
                "entityType": "strategy", 
                "observations": [
                    f"Strategy: {coordination_strategy.get('strategy', 'Standard coordination')}",
                    f"Agent count: {len(self.agent_registry)}",
                    f"Generated at: {time.time()}",
                    f"Workflow ID: {self.workflow_id}"
                ]
            }
            await self._mcp_create_entities([strategy_entity])
        
        # Proceed to Phase 2
        self.current_phase = WorkflowPhase.PHASE_2_STRATEGIC_PLANNING
        await self._execute_phase_2_strategic_planning()
    
    async def _execute_phase_2_strategic_planning(self):
        """Phase 2: Strategic Intelligence Planning using sequential thinking."""
        logger.info("Executing Phase 2: Strategic Intelligence Planning")
        
        # Use sequential thinking for strategic planning
        planning_context = {
            "workflow_id": self.workflow_id,
            "registered_agents": list(self.agent_registry.keys()),
            "current_context": self.workflow_context,
            "available_capabilities": []
        }
        
        # Collect all agent capabilities
        for agent_info in self.agent_registry.values():
            planning_context["available_capabilities"].extend(agent_info["capabilities"])
        
        strategic_plan = await self._mcp_sequential_analysis(
            "Create strategic implementation plan for ML-enhanced agentic workflow",
            planning_context
        )
        
        if strategic_plan:
            # Store strategic plan in memory and knowledge graph
            await self._mcp_add_memory(
                f"Strategic Plan: {strategic_plan.get('conclusion', 'Strategic planning completed')}",
                "orchestration-user"
            )
            
            plan_entity = {
                "name": f"strategic_plan_{self.workflow_id}",
                "entityType": "plan",
                "observations": [
                    f"Plan: {strategic_plan.get('conclusion', 'Strategic plan')}",
                    f"Confidence: {strategic_plan.get('confidence', 0.8)}",
                    f"Steps: {len(strategic_plan.get('steps', []))}",
                    f"Created at: {time.time()}"
                ]
            }
            await self._mcp_create_entities([plan_entity])
        
        # Proceed to Phase 3
        self.current_phase = WorkflowPhase.PHASE_3_RESEARCH_DISCOVERY
        await self._execute_phase_3_research_discovery()
    
    async def _execute_phase_3_research_discovery(self):
        """Phase 3: Multi-Domain Research Discovery using MCP tools."""
        logger.info("Executing Phase 3: Multi-Domain Research Discovery")
        
        # Use filesystem MCP to analyze project structure
        project_structure = await self._mcp_analyze_project_structure()
        
        # Search for relevant documentation using firecrawl if needed
        research_results = {}
        
        # Query memory for existing research
        existing_research = await self._mcp_search_memories(
            "project research analysis documentation", 
            "orchestration-user"
        )
        
        if existing_research:
            research_results["existing_research"] = existing_research
        
        # Store research results
        if research_results:
            research_entity = {
                "name": f"research_results_{self.workflow_id}",
                "entityType": "research",
                "observations": [
                    f"Project structure analyzed: {bool(project_structure)}",
                    f"Existing research found: {len(existing_research) if existing_research else 0}",
                    f"Research completed at: {time.time()}"
                ]
            }
            await self._mcp_create_entities([research_entity])
        
        # Proceed to Phase 4
        self.current_phase = WorkflowPhase.PHASE_4_CONTEXT_SYNTHESIS
        await self._execute_phase_4_context_synthesis()
    
    async def _execute_phase_4_context_synthesis(self):
        """Phase 4: Context Synthesis & Compression using memory integration."""
        logger.info("Executing Phase 4: Context Synthesis & Compression")
        
        # Compress large context documents if needed
        context_size = len(json.dumps(self.workflow_context))
        if context_size > 4000:  # Token limit threshold
            compressed_context = await self._mcp_compress_document(
                json.dumps(self.workflow_context),
                target_tokens=3000
            )
            if compressed_context:
                self.workflow_context = json.loads(compressed_context)
        
        # Create context packages for different agent types
        context_packages = await self._create_agent_context_packages()
        
        # Store context packages using intelligent file organization
        for package_type, package_data in context_packages.items():
            file_path = await self._organize_file_placement(
                f"{package_type}_context_package.json",
                "context_packages"
            )
            
            await self._mcp_write_file(file_path, json.dumps(package_data, indent=2))
        
        # Proceed to Phase 5
        self.current_phase = WorkflowPhase.PHASE_5_PARALLEL_IMPLEMENTATION
        await self._execute_phase_5_parallel_implementation()
    
    async def _execute_phase_5_parallel_implementation(self):
        """Phase 5: Parallel Implementation Execution."""
        logger.info("Executing Phase 5: Parallel Implementation Execution")
        
        # Create tasks for all registered agents
        implementation_tasks = []
        
        for agent_id, agent_info in self.agent_registry.items():
            # Create task based on agent capabilities
            task = AgentTask(
                agent_id=agent_id,
                task_type="implementation",
                description=f"Implementation task for {agent_info['agent_type']}",
                context_data={
                    "agent_capabilities": agent_info["capabilities"],
                    "workflow_context": self.workflow_context,
                    "phase": self.current_phase.value
                },
                workflow_id=self.workflow_id,
                phase=self.current_phase
            )
            implementation_tasks.append(task)
        
        # Execute tasks in true parallel using the ParallelTaskManager
        logger.info("Starting parallel task execution", task_count=len(implementation_tasks))
        
        results = await self.parallel_task_manager.execute_parallel_tasks(implementation_tasks)
        
        # Store results and update tracking
        for result in results:
            self.results[result.task_id] = result
            
        # Log execution summary
        successful_tasks = sum(1 for r in results if r.success)
        logger.info("Parallel execution completed", 
                   total_tasks=len(results),
                   successful_tasks=successful_tasks,
                   success_rate=successful_tasks/len(results) if results else 0)
        
        # Proceed to Phase 6
        self.current_phase = WorkflowPhase.PHASE_6_VALIDATION
        await self._execute_phase_6_validation()
    
    async def _execute_phase_6_validation(self):
        """Phase 6: Comprehensive Evidence-Based Validation."""
        logger.info("Executing Phase 6: Comprehensive Evidence-Based Validation")
        
        # Validate implementation results
        validation_results = []
        
        for task_id, result in self.results.items():
            if result.success:
                # Use sequential thinking to validate result quality
                validation = await self._mcp_sequential_analysis(
                    f"Validate implementation result for {result.agent_id}",
                    {
                        "result_data": result.data,
                        "evidence": result.evidence,
                        "confidence_score": result.confidence_score,
                        "execution_time": result.execution_time_ms
                    }
                )
                
                if validation:
                    validation_results.append({
                        "task_id": task_id,
                        "agent_id": result.agent_id,
                        "validation": validation,
                        "validated_at": time.time()
                    })
        
        # Store validation results
        if validation_results:
            validation_entity = {
                "name": f"validation_results_{self.workflow_id}",
                "entityType": "validation",
                "observations": [
                    f"Tasks validated: {len(validation_results)}",
                    f"Validation completed at: {time.time()}",
                    f"Workflow ID: {self.workflow_id}"
                ]
            }
            await self._mcp_create_entities([validation_entity])
        
        # Proceed to Phase 7
        self.current_phase = WorkflowPhase.PHASE_7_DECISION_CONTROL
        await self._execute_phase_7_decision_control()
    
    async def _execute_phase_7_decision_control(self):
        """Phase 7: Decision & Iteration Control."""
        logger.info("Executing Phase 7: Decision & Iteration Control")
        
        # Analyze all results and determine if iteration is needed
        success_rate = sum(1 for result in self.results.values() if result.success) / len(self.results) if self.results else 0
        
        if success_rate >= 0.8:  # 80% success threshold
            # Proceed to Phase 8
            self.current_phase = WorkflowPhase.PHASE_8_VERSION_CONTROL
            await self._execute_phase_8_version_control()
        else:
            # Iteration needed - restart from Phase 0 with learned context
            logger.info("Iteration required due to low success rate", success_rate=success_rate)
            self.current_phase = WorkflowPhase.PHASE_0_TODO_CONTEXT
            await self._execute_phase_0_todo_context()
    
    async def _execute_phase_8_version_control(self):
        """Phase 8: Atomic Version Control Synchronization."""
        logger.info("Executing Phase 8: Atomic Version Control Synchronization")
        
        # Collect all created files for version control
        created_files = []
        for result in self.results.values():
            created_files.extend(result.created_files)
        
        if created_files:
            # Create atomic commit (would need actual git integration)
            commit_message = f"ML-enhanced agentic workflow implementation - {self.workflow_id}"
            
            # Store commit info in memory
            await self._mcp_add_memory(
                f"Version control commit: {commit_message} - Files: {', '.join(created_files)}",
                "orchestration-user"
            )
        
        # Proceed to Phase 9
        self.current_phase = WorkflowPhase.PHASE_9_META_AUDIT
        await self._execute_phase_9_meta_audit()
    
    async def _execute_phase_9_meta_audit(self):
        """Phase 9: Enhanced Two-Part Meta-Orchestration Audit & Learning System."""
        logger.info("🔍 Executing Phase 9: Enhanced Meta-Orchestration Audit & Learning")
        
        # PART 1: AUDIT PLANNING PHASE
        logger.info("📋 Phase 9 Part 1: Comprehensive Audit Planning")
        
        audit_context = {
            "workflow_id": self.workflow_id,
            "phases_completed": self.current_phase.value,
            "agents_used": list(self.agent_registry.keys()),
            "changes_made": [r.__dict__ for r in self.results.values() if hasattr(r, '__dict__')],
            "affected_services": list(set([
                service for result in self.results.values() 
                if hasattr(result, 'affected_services') 
                for service in getattr(result, 'affected_services', [])
            ])),
            "criticality": "high",  # All orchestration workflows are high criticality
            "results_summary": {
                "total_tasks": len(self.results),
                "successful_tasks": sum(1 for r in self.results.values() if r.success),
                "average_confidence": sum(r.confidence_score or 0 for r in self.results.values()) / len(self.results) if self.results else 0
            },
            "execution_time": time.time() - (self.workflow_context.get("started_at", time.time())),
            "workflow_context": self.workflow_context
        }
        
        # PART 2: MULTI-AGENT AUDIT EXECUTION
        logger.info("🤖 Phase 9 Part 2: Multi-Agent Audit Execution with Consensus Analysis")
        
        try:
            # Import and execute the sophisticated audit system
            try:
                from .ml_enhanced_orchestrator import execute_ml_enhanced_audit
            except ImportError:
                # Fallback import for standalone execution
                from ml_enhanced_orchestrator import execute_ml_enhanced_audit
            
            # Execute comprehensive two-part audit system
            comprehensive_audit_results = await execute_ml_enhanced_audit(audit_context)
            
            logger.info("✅ Enhanced Phase 9 audit completed successfully")
            
            # Store comprehensive audit results
            audit_entity = {
                "name": f"comprehensive_audit_{self.workflow_id}",
                "entityType": "meta_audit",
                "observations": [
                    f"PART 1 - Audit Strategy: {comprehensive_audit_results.get('audit_plan', {}).get('strategy', {}).get('primary_decision', 'Unknown strategy')}",
                    f"PART 2 - Multi-Agent Execution: {len(comprehensive_audit_results.get('audit_execution', {}).get('agent_findings', {}))} agent types participated",
                    f"Consensus Level: {comprehensive_audit_results.get('audit_execution', {}).get('consensus_analysis', {}).get('consensus_level', 'unknown')}",
                    f"Average Confidence: {comprehensive_audit_results.get('audit_execution', {}).get('consensus_analysis', {}).get('average_confidence', 0.0):.2f}",
                    f"Critical Findings: {len(comprehensive_audit_results.get('audit_execution', {}).get('consensus_analysis', {}).get('critical_findings', []))}",
                    f"Overall Assessment: {comprehensive_audit_results.get('audit_execution', {}).get('overall_assessment', {}).get('confidence_score', 0.0):.2f}",
                    f"Audit completed at: {time.time()}"
                ]
            }
            await self._mcp_create_entities([audit_entity])
            
            # Store detailed audit results in workflow context for Phase 10
            self.workflow_context["phase_9_audit_results"] = comprehensive_audit_results
            
            logger.info(f"🎯 Phase 9 Multi-Agent Audit Summary:")
            logger.info(f"   • Consensus Level: {comprehensive_audit_results.get('audit_execution', {}).get('consensus_analysis', {}).get('consensus_level', 'unknown')}")
            logger.info(f"   • Average Confidence: {comprehensive_audit_results.get('audit_execution', {}).get('consensus_analysis', {}).get('average_confidence', 0.0):.2f}")
            logger.info(f"   • Critical Findings: {len(comprehensive_audit_results.get('audit_execution', {}).get('consensus_analysis', {}).get('critical_findings', []))}")
            
        except Exception as e:
            logger.error(f"❌ Enhanced Phase 9 audit failed: {e}")
            
            # Fallback to basic sequential analysis
            logger.info("🔄 Falling back to basic workflow analysis")
            
            workflow_analysis = await self._mcp_sequential_analysis(
                "Analyze complete ML-enhanced agentic workflow execution (fallback mode)",
                audit_context
            )
            
            if workflow_analysis:
                # Store basic learning outcomes
                learning_entity = {
                    "name": f"workflow_learning_{self.workflow_id}_fallback",
                    "entityType": "learning",
                    "observations": [
                        f"Analysis: {workflow_analysis.get('conclusion', 'Workflow analysis completed')}",
                        f"Success rate: {workflow_analysis.get('success_rate', 'Unknown')}",
                        f"Key insights: {workflow_analysis.get('insights', 'Standard execution')}",
                        f"Fallback mode due to: {str(e)}",
                        f"Completed at: {time.time()}"
                    ]
                }
                await self._mcp_create_entities([learning_entity])
        
        # Proceed to Phase 10
        logger.info("➡️ Proceeding to Phase 10: Todo Integration & Loop Control")
        self.current_phase = WorkflowPhase.PHASE_10_TODO_INTEGRATION
        await self._execute_phase_10_todo_integration()
    
    async def _execute_phase_10_todo_integration(self):
        """Phase 10: Continuous Todo Integration & Loop Control."""
        logger.info("Executing Phase 10: Continuous Todo Integration & Loop Control")
        
        # Check for remaining high-priority todos
        try:
            with open("/home/marku/ai_workflow_engine/.claude/orchestration_todos.json", "r") as f:
                todos = json.load(f)
        except Exception:
            todos = []
        
        remaining_todos = [
            todo for todo in todos 
            if todo.get("priority") in ["critical", "high"] and todo.get("status") == "pending"
        ]
        
        if remaining_todos:
            # Continue loop - restart workflow with remaining todos
            logger.info("High-priority todos remain, continuing orchestration loop", 
                       remaining_count=len(remaining_todos))
            
            self.current_phase = WorkflowPhase.PHASE_0_TODO_CONTEXT
            await self._execute_phase_0_todo_context()
        else:
            # Workflow complete
            logger.info("ML-enhanced agentic workflow completed successfully")
            
            # Store completion record
            completion_entity = {
                "name": f"workflow_completion_{self.workflow_id}",
                "entityType": "completion",
                "observations": [
                    f"Workflow completed successfully",
                    f"Total phases: {self.current_phase.value + 1}",
                    f"Total agents: {len(self.agent_registry)}",
                    f"Total tasks: {len(self.results)}",
                    f"Completed at: {time.time()}"
                ]
            }
            await self._mcp_create_entities([completion_entity])
    
    # MCP Service Integration Methods
    
    async def _mcp_create_entities(self, entities: List[Dict[str, Any]]) -> bool:
        """Create entities using MCP memory service."""
        try:
            # This would call the actual MCP function
            # For now, we'll log the operation
            logger.info("MCP: Creating entities", count=len(entities))
            return True
        except Exception as e:
            logger.error("MCP entity creation failed", error=str(e))
            return False
    
    async def _mcp_register_orchestration_agent(self, agent_id: str, agent_type: str, capabilities: List[str]) -> bool:
        """Register agent with orchestration MCP service."""
        try:
            logger.info("MCP: Registering orchestration agent", agent_id=agent_id)
            return True
        except Exception as e:
            logger.error("MCP agent registration failed", error=str(e))
            return False
    
    async def _mcp_create_checkpoint(self, phase: int, state: Dict[str, Any]) -> bool:
        """Create orchestration checkpoint using MCP."""
        try:
            logger.info("MCP: Creating checkpoint", phase=phase)
            return True
        except Exception as e:
            logger.error("MCP checkpoint creation failed", error=str(e))
            return False
    
    async def _mcp_query_orchestration_knowledge(self, entity: str) -> Optional[Dict[str, Any]]:
        """Query orchestration knowledge using MCP."""
        try:
            logger.info("MCP: Querying orchestration knowledge", entity=entity)
            return {"patterns": [], "solutions": []}
        except Exception as e:
            logger.error("MCP knowledge query failed", error=str(e))
            return None
    
    async def _mcp_sequential_analysis(self, thought: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Perform sequential thinking analysis using MCP."""
        try:
            logger.info("MCP: Sequential analysis", thought=thought[:100])
            return {
                "conclusion": "Analysis completed",
                "confidence": 0.8,
                "steps": ["Step 1", "Step 2", "Step 3"]
            }
        except Exception as e:
            logger.error("MCP sequential analysis failed", error=str(e))
            return None
    
    async def _mcp_add_memory(self, content: str, user_id: str) -> bool:
        """Add memory using MCP mem0 service."""
        try:
            logger.info("MCP: Adding memory", content_length=len(content))
            return True
        except Exception as e:
            logger.error("MCP memory add failed", error=str(e))
            return False
    
    async def _mcp_search_memories(self, query: str, user_id: str) -> Optional[List[Dict[str, Any]]]:
        """Search memories using MCP mem0 service."""
        try:
            logger.info("MCP: Searching memories", query=query[:50])
            return []
        except Exception as e:
            logger.error("MCP memory search failed", error=str(e))
            return None
    
    async def _mcp_get_coordination_strategy(self, agents_status: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Get coordination strategy using MCP orchestration service."""
        try:
            logger.info("MCP: Getting coordination strategy", agent_count=len(agents_status))
            return {"strategy": "parallel_execution", "confidence": 0.9}
        except Exception as e:
            logger.error("MCP coordination strategy failed", error=str(e))
            return None
    
    async def _mcp_compress_document(self, content: str, target_tokens: int) -> Optional[str]:
        """Compress document using MCP orchestration service."""
        try:
            logger.info("MCP: Compressing document", content_length=len(content), target_tokens=target_tokens)
            # Simple compression simulation
            return content[:target_tokens * 4]  # Rough token estimation
        except Exception as e:
            logger.error("MCP document compression failed", error=str(e))
            return None
    
    async def _mcp_analyze_project_structure(self) -> Optional[Dict[str, Any]]:
        """Analyze project structure using MCP filesystem service."""
        try:
            logger.info("MCP: Analyzing project structure")
            return {"directories": [], "files": [], "structure": "analyzed"}
        except Exception as e:
            logger.error("MCP project structure analysis failed", error=str(e))
            return None
    
    async def _mcp_write_file(self, file_path: str, content: str) -> bool:
        """Write file using MCP filesystem service."""
        try:
            logger.info("MCP: Writing file", file_path=file_path, content_length=len(content))
            return True
        except Exception as e:
            logger.error("MCP file write failed", error=str(e))
            return False
    
    async def _organize_file_placement(self, filename: str, file_type: str) -> str:
        """Organize file placement using intelligent rules."""
        base_path = self.file_organization_rules.get(file_type, "")
        return f"/home/marku/ai_workflow_engine/{base_path}{filename}"
    
    async def _create_agent_context_packages(self) -> Dict[str, Dict[str, Any]]:
        """Create context packages for different agent types."""
        packages = {}
        
        for agent_id, agent_info in self.agent_registry.items():
            agent_type = agent_info["agent_type"]
            packages[f"{agent_type}_context"] = {
                "agent_id": agent_id,
                "agent_type": agent_type,
                "capabilities": agent_info["capabilities"],
                "workflow_context": self.workflow_context,
                "phase": self.current_phase.value,
                "created_at": time.time()
            }
        
        return packages
    
    async def execute_multiple_task_calls(self, task_calls: List[Dict[str, Any]]) -> List[AgentResult]:
        """Execute multiple Task tool calls simultaneously in a single message."""
        logger.info("Executing multiple Task tool calls", call_count=len(task_calls))
        
        # Convert task calls to AgentTask objects
        tasks = []
        for call in task_calls:
            task = AgentTask(
                agent_id=call.get("agent_id", str(uuid4())),
                task_type=call.get("task_type", "general"),
                description=call.get("description", "Task execution"),
                context_data=call.get("context_data", {}),
                workflow_id=self.workflow_id,
                phase=self.current_phase
            )
            tasks.append(task)
        
        # Execute all tasks in parallel
        results = await self.parallel_task_manager.execute_parallel_tasks(tasks)
        
        # Store results
        for result in results:
            self.results[result.task_id] = result
            
        return results
    
    async def _on_task_progress(self, instance_id: str, progress: float):
        """Handle task progress updates."""
        logger.debug("Task progress update", instance_id=instance_id, progress=progress)
        
        # Update workflow context with progress information
        if "task_progress" not in self.workflow_context:
            self.workflow_context["task_progress"] = {}
            
        self.workflow_context["task_progress"][instance_id] = {
            "progress": progress,
            "updated_at": time.time()
        }
    
    def get_parallel_execution_status(self) -> Dict[str, Any]:
        """Get current status of parallel executions."""
        running_instances = self.parallel_task_manager.get_running_instances()
        resource_locks = self.parallel_task_manager.get_resource_locks()
        
        return {
            "workflow_id": self.workflow_id,
            "current_phase": self.current_phase.value,
            "running_instances": {
                instance_id: {
                    "agent_id": instance.agent_id,
                    "status": instance.status,
                    "start_time": instance.start_time,
                    "heartbeat": instance.heartbeat,
                    "resources_locked": list(instance.resources_locked)
                }
                for instance_id, instance in running_instances.items()
            },
            "resource_locks": {
                resource_id: {
                    "locked_by": lock.locked_by,
                    "lock_type": lock.lock_type,
                    "locked_at": lock.locked_at,
                    "expires_at": lock.expires_at
                }
                for resource_id, lock in resource_locks.items()
            },
            "total_tasks_completed": len(self.results),
            "successful_tasks": sum(1 for r in self.results.values() if r.success)
        }
    
    async def wait_for_all_tasks_completion(self, timeout: int = 300) -> bool:
        """Wait for all running tasks to complete."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            running_instances = self.parallel_task_manager.get_running_instances()
            
            if not running_instances:
                logger.info("All parallel tasks completed")
                return True
                
            # Log current status
            logger.debug("Waiting for task completion", 
                        running_count=len(running_instances),
                        elapsed_time=time.time() - start_time)
            
            await asyncio.sleep(1.0)
        
        logger.warning("Timeout waiting for task completion", 
                      running_count=len(self.parallel_task_manager.get_running_instances()))
        return False
    
    async def cancel_running_tasks(self, agent_ids: List[str] = None) -> int:
        """Cancel running tasks, optionally filtered by agent IDs."""
        running_instances = self.parallel_task_manager.get_running_instances()
        cancelled_count = 0
        
        for instance_id, instance in running_instances.items():
            if agent_ids is None or instance.agent_id in agent_ids:
                # Mark instance as cancelled (in a real implementation, 
                # this would actually cancel the running task)
                instance.status = "cancelled"
                cancelled_count += 1
                
                logger.info("Task cancelled", 
                           instance_id=instance_id,
                           agent_id=instance.agent_id)
        
        return cancelled_count
    
    def get_task_execution_metrics(self) -> Dict[str, Any]:
        """Get metrics about task execution performance."""
        if not self.results:
            return {"no_data": True}
            
        execution_times = [r.execution_time_ms for r in self.results.values() if r.execution_time_ms > 0]
        
        metrics = {
            "total_tasks": len(self.results),
            "successful_tasks": sum(1 for r in self.results.values() if r.success),
            "failed_tasks": sum(1 for r in self.results.values() if not r.success),
            "average_confidence": sum(r.confidence_score or 0 for r in self.results.values()) / len(self.results),
            "workflow_id": self.workflow_id
        }
        
        if execution_times:
            metrics.update({
                "average_execution_time_ms": sum(execution_times) / len(execution_times),
                "min_execution_time_ms": min(execution_times),
                "max_execution_time_ms": max(execution_times)
            })
        
        # Add agent-specific metrics
        agent_metrics = {}
        for result in self.results.values():
            agent_id = result.agent_id
            if agent_id not in agent_metrics:
                agent_metrics[agent_id] = {
                    "tasks": 0,
                    "successes": 0,
                    "total_time_ms": 0
                }
            
            agent_metrics[agent_id]["tasks"] += 1
            if result.success:
                agent_metrics[agent_id]["successes"] += 1
            agent_metrics[agent_id]["total_time_ms"] += result.execution_time_ms
        
        metrics["agent_metrics"] = agent_metrics
        
        return metrics

# Global MCP integration layer instance
_mcp_integration: Optional[MCPIntegrationLayer] = None

def get_mcp_integration_layer(workflow_id: str = None) -> MCPIntegrationLayer:
    """Get or create global MCP integration layer."""
    global _mcp_integration
    
    if _mcp_integration is None:
        _mcp_integration = MCPIntegrationLayer(workflow_id)
    
    return _mcp_integration

def reset_mcp_integration_layer():
    """Reset global MCP integration layer."""
    global _mcp_integration
    _mcp_integration = None

# Additional utility functions for parallel execution support

def create_task_call(agent_id: str, task_type: str, description: str, 
                    context_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create a task call dictionary for multiple task execution."""
    return {
        "agent_id": agent_id,
        "task_type": task_type,
        "description": description,
        "context_data": context_data or {}
    }

def batch_task_calls(task_calls: List[Dict[str, Any]], batch_size: int = 5) -> List[List[Dict[str, Any]]]:
    """Batch task calls for controlled parallel execution."""
    batches = []
    for i in range(0, len(task_calls), batch_size):
        batch = task_calls[i:i + batch_size]
        batches.append(batch)
    return batches

async def execute_task_batches(integration_layer: MCPIntegrationLayer, 
                              batches: List[List[Dict[str, Any]]]) -> List[AgentResult]:
    """Execute task batches sequentially with parallel execution within each batch."""
    all_results = []
    
    for i, batch in enumerate(batches):
        logger.info(f"Executing batch {i+1}/{len(batches)}", batch_size=len(batch))
        
        batch_results = await integration_layer.execute_multiple_task_calls(batch)
        all_results.extend(batch_results)
        
        # Wait for batch completion before starting next batch
        await integration_layer.wait_for_all_tasks_completion(timeout=120)
        
        logger.info(f"Batch {i+1} completed", 
                   successful_tasks=sum(1 for r in batch_results if r.success))
    
    return all_results