#!/usr/bin/env python3
"""
Orchestration State Management for Agent Coordination
Provides shared state tracking across agent execution phases
"""
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import threading

@dataclass
class AgentTask:
    """Represents a task assigned to an agent"""
    agent_name: str
    task_description: str
    dependencies: List[str]
    context: Dict[str, Any]
    priority: str = "normal"  # high, normal, low
    estimated_duration: int = 300  # seconds
    
@dataclass
class AgentResult:
    """Represents the result of an agent execution"""
    agent_name: str
    task_id: str
    success: bool
    output: Dict[str, Any]
    execution_time: float
    tools_used: List[str]
    errors: List[str]
    context_used: Dict[str, Any]
    timestamp: str

class OrchestrationPhase:
    """Defines execution phases with parallel/sequential constraints"""
    def __init__(self, name: str, execution_mode: str = "parallel"):
        self.name = name
        self.execution_mode = execution_mode  # "parallel" or "sequential"
        self.tasks: List[AgentTask] = []
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        self.start_time: Optional[str] = None
        self.end_time: Optional[str] = None
        
    def add_task(self, task: AgentTask):
        """Add a task to this phase"""
        self.tasks.append(task)
        
    def is_complete(self) -> bool:
        """Check if all tasks in this phase are complete"""
        total_tasks = len(self.tasks)
        completed_count = len(self.completed_tasks)
        failed_count = len(self.failed_tasks)
        return (completed_count + failed_count) == total_tasks
        
    def can_proceed_to_next_phase(self) -> bool:
        """Check if we can proceed to next phase (no critical failures)"""
        # For now, allow proceeding if at least 70% of tasks succeed
        total_tasks = len(self.tasks)
        if total_tasks == 0:
            return True
        success_rate = len(self.completed_tasks) / total_tasks
        return success_rate >= 0.7

class OrchestrationState:
    """Central state management for agent orchestration"""
    
    def __init__(self):
        self.execution_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.state_file = Path(".claude/logs") / f"orchestration_state_{self.execution_id}.json"
        self.lock = threading.Lock()
        
        # Phase management
        self.phases: List[OrchestrationPhase] = []
        self.current_phase_index = 0
        self.execution_complete = False
        
        # Agent tracking
        self.agent_outputs: Dict[str, AgentResult] = {}
        self.active_agents: Set[str] = set()
        self.failed_agents: Set[str] = set()
        
        # Synthesis tracking
        self.synthesis_complete = False
        self.synthesis_context: Dict[str, Any] = {}
        self.documentation_updates: Dict[str, List[Dict]] = {}
        
        # Performance metrics
        self.start_time = datetime.now().isoformat()
        self.phase_times: Dict[str, Dict[str, str]] = {}
        
        # Create logs directory
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
    def add_phase(self, phase: OrchestrationPhase):
        """Add an execution phase"""
        with self.lock:
            self.phases.append(phase)
            
    def get_current_phase(self) -> Optional[OrchestrationPhase]:
        """Get the currently executing phase"""
        if self.current_phase_index < len(self.phases):
            return self.phases[self.current_phase_index]
        return None
        
    def mark_agent_complete(self, agent_name: str, result: AgentResult):
        """Mark an agent as completed with its result"""
        with self.lock:
            self.agent_outputs[agent_name] = result
            self.active_agents.discard(agent_name)
            
            # Update current phase
            current_phase = self.get_current_phase()
            if current_phase:
                if result.success:
                    current_phase.completed_tasks.add(agent_name)
                else:
                    current_phase.failed_tasks.add(agent_name)
                    self.failed_agents.add(agent_name)
                    
            self._save_state()
            
    def mark_agent_active(self, agent_name: str):
        """Mark an agent as currently active"""
        with self.lock:
            self.active_agents.add(agent_name)
            
    def is_ready_for_synthesis(self) -> bool:
        """Check if research phase is complete and ready for synthesis"""
        research_agents = {'codebase-research-analyst', 'schema-database-expert', 
                          'fullstack-communication-auditor'}
        completed_research = set(self.agent_outputs.keys()) & research_agents
        return len(completed_research) >= 2  # At least 2 of 3 research agents complete
        
    def set_synthesis_complete(self, context: Dict[str, Any], doc_updates: Dict[str, List[Dict]]):
        """Mark synthesis phase as complete with context"""
        with self.lock:
            self.synthesis_complete = True
            self.synthesis_context = context
            self.documentation_updates = doc_updates
            self._save_state()
            
    def get_context_for_agent(self, agent_name: str) -> Dict[str, Any]:
        """Get synthesized context for a specific agent"""
        if self.synthesis_complete and agent_name in self.synthesis_context:
            return self.synthesis_context[agent_name]
        return {}
        
    def can_proceed_to_next_phase(self) -> bool:
        """Check if current phase is complete and we can proceed"""
        current_phase = self.get_current_phase()
        if not current_phase:
            return False
        return current_phase.can_proceed_to_next_phase()
        
    def advance_to_next_phase(self) -> bool:
        """Move to the next execution phase"""
        with self.lock:
            current_phase = self.get_current_phase()
            if current_phase:
                current_phase.end_time = datetime.now().isoformat()
                self.phase_times[current_phase.name] = {
                    'start': current_phase.start_time,
                    'end': current_phase.end_time
                }
                
            self.current_phase_index += 1
            
            next_phase = self.get_current_phase()
            if next_phase:
                next_phase.start_time = datetime.now().isoformat()
                self._save_state()
                return True
            else:
                self.execution_complete = True
                self._save_state()
                return False
                
    def get_execution_summary(self) -> Dict[str, Any]:
        """Generate comprehensive execution summary"""
        with self.lock:
            total_agents = len(self.agent_outputs)
            successful_agents = sum(1 for result in self.agent_outputs.values() if result.success)
            
            return {
                "execution_id": self.execution_id,
                "start_time": self.start_time,
                "current_phase": self.current_phase_index,
                "total_phases": len(self.phases),
                "execution_complete": self.execution_complete,
                "total_agents": total_agents,
                "successful_agents": successful_agents,
                "failed_agents": len(self.failed_agents),
                "success_rate": successful_agents / total_agents if total_agents > 0 else 0,
                "synthesis_complete": self.synthesis_complete,
                "active_agents": list(self.active_agents),
                "phase_times": self.phase_times,
                "documentation_updates": {k: len(v) for k, v in self.documentation_updates.items()}
            }
            
    def _save_state(self):
        """Persist current state to disk"""
        try:
            state_data = {
                "execution_id": self.execution_id,
                "current_phase_index": self.current_phase_index,
                "execution_complete": self.execution_complete,
                "synthesis_complete": self.synthesis_complete,
                "active_agents": list(self.active_agents),
                "failed_agents": list(self.failed_agents),
                "agent_results": {k: asdict(v) for k, v in self.agent_outputs.items()},
                "synthesis_context": self.synthesis_context,
                "documentation_updates": self.documentation_updates,
                "phase_times": self.phase_times,
                "timestamp": datetime.now().isoformat()
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state_data, f, indent=2)
                
        except Exception as e:
            print(f"Warning: Could not save orchestration state: {e}")


class ParallelExecutor:
    """Handles parallel execution of agent tasks"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        
    async def execute_parallel_agents(self, tasks: List[AgentTask], 
                                     call_agent_func) -> Dict[str, AgentResult]:
        """Execute multiple agent tasks in parallel"""
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Create futures for all tasks
            futures = {}
            for task in tasks:
                future = executor.submit(call_agent_func, task.agent_name, task.task_description, task.context)
                futures[task.agent_name] = future
                
            # Collect results as they complete
            for agent_name, future in futures.items():
                try:
                    start_time = datetime.now()
                    result = future.result(timeout=600)  # 10 minute timeout per agent
                    end_time = datetime.now()
                    
                    results[agent_name] = AgentResult(
                        agent_name=agent_name,
                        task_id=f"{agent_name}_{datetime.now().strftime('%H%M%S')}",
                        success=result.get('success', True),
                        output=result,
                        execution_time=(end_time - start_time).total_seconds(),
                        tools_used=result.get('tools_used', []),
                        errors=result.get('errors', []),
                        context_used=result.get('context_used', {}),
                        timestamp=end_time.isoformat()
                    )
                    
                except Exception as e:
                    results[agent_name] = AgentResult(
                        agent_name=agent_name,
                        task_id=f"{agent_name}_{datetime.now().strftime('%H%M%S')}",
                        success=False,
                        output={},
                        execution_time=0,
                        tools_used=[],
                        errors=[str(e)],
                        context_used={},
                        timestamp=datetime.now().isoformat()
                    )
                    
        return results
        
    def execute_sequential_agents(self, tasks: List[AgentTask], 
                                 call_agent_func) -> Dict[str, AgentResult]:
        """Execute agent tasks sequentially"""
        results = {}
        
        for task in tasks:
            try:
                start_time = datetime.now()
                result = call_agent_func(task.agent_name, task.task_description, task.context)
                end_time = datetime.now()
                
                results[task.agent_name] = AgentResult(
                    agent_name=task.agent_name,
                    task_id=f"{task.agent_name}_{datetime.now().strftime('%H%M%S')}",
                    success=result.get('success', True),
                    output=result,
                    execution_time=(end_time - start_time).total_seconds(),
                    tools_used=result.get('tools_used', []),
                    errors=result.get('errors', []),
                    context_used=result.get('context_used', {}),
                    timestamp=end_time.isoformat()
                )
                
                # Stop on critical failure in sequential execution
                if not results[task.agent_name].success and task.priority == "high":
                    print(f"🚨 Critical task failed: {task.agent_name}")
                    break
                    
            except Exception as e:
                results[task.agent_name] = AgentResult(
                    agent_name=task.agent_name,
                    task_id=f"{task.agent_name}_{datetime.now().strftime('%H%M%S')}",
                    success=False,
                    output={},
                    execution_time=0,
                    tools_used=[],
                    errors=[str(e)],
                    context_used={},
                    timestamp=datetime.now().isoformat()
                )
                
        return results


# Global orchestration state instance
orchestration_state = OrchestrationState()
parallel_executor = ParallelExecutor()

def create_orchestration_plan(request_analysis: Dict[str, Any]) -> List[OrchestrationPhase]:
    """Create a structured orchestration plan with phases"""
    phases = []
    
    # Phase 1: Research (Parallel)
    research_phase = OrchestrationPhase("research", "parallel")
    research_phase.add_task(AgentTask("codebase-research-analyst", 
                                    "Analyze codebase for relevant patterns", [], {}))
    research_phase.add_task(AgentTask("schema-database-expert", 
                                    "Analyze database schema and requirements", [], {}))
    research_phase.add_task(AgentTask("fullstack-communication-auditor", 
                                    "Audit communication patterns", [], {}))
    phases.append(research_phase)
    
    # Phase 2: Synthesis (Sequential)
    synthesis_phase = OrchestrationPhase("synthesis", "sequential")
    synthesis_phase.add_task(AgentTask("nexus-synthesis-agent", 
                                     "Synthesize research findings into implementation contexts", [], {}))
    phases.append(synthesis_phase)
    
    # Phase 3: Implementation (Parallel)
    implementation_phase = OrchestrationPhase("implementation", "parallel")
    implementation_phase.add_task(AgentTask("backend-gateway-expert", 
                                           "Implement backend changes", [], {}))
    implementation_phase.add_task(AgentTask("webui-architect", 
                                          "Implement frontend changes", [], {}))
    implementation_phase.add_task(AgentTask("test-automation-engineer", 
                                          "Create comprehensive tests", [], {}))
    phases.append(implementation_phase)
    
    # Phase 4: Validation (Sequential)
    validation_phase = OrchestrationPhase("validation", "sequential")
    validation_phase.add_task(AgentTask("ui-regression-debugger", 
                                      "Validate UI functionality with evidence", [], {}))
    phases.append(validation_phase)
    
    # Phase 5: Documentation (Sequential)
    documentation_phase = OrchestrationPhase("documentation", "sequential")
    documentation_phase.add_task(AgentTask("documentation-specialist", 
                                          "Update documentation with learnings", [], {}))
    phases.append(documentation_phase)
    
    return phases

if __name__ == "__main__":
    # Test the orchestration system
    print("Testing Orchestration State Management...")
    
    # Create test phases
    phases = create_orchestration_plan({"request": "test authentication system"})
    
    for phase in phases:
        orchestration_state.add_phase(phase)
    
    print(f"Created {len(phases)} execution phases")
    print(f"Current phase: {orchestration_state.get_current_phase().name}")
    print(f"Execution ID: {orchestration_state.execution_id}")
    
    # Test state persistence
    summary = orchestration_state.get_execution_summary()
    print(f"Execution summary: {json.dumps(summary, indent=2)}")