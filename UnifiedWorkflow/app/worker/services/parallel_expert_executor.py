"""
Parallel Expert Executor - Coordinates parallel execution of expert agents with resource management
Manages concurrent agent execution within GPU constraints and admin model settings.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, AsyncGenerator, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

from worker.services.model_resource_manager import model_resource_manager, ModelCategory
from worker.services.expert_group_specialized_methods import (
    research_specialist_with_tools,
    personal_assistant_with_tools,
    standard_expert_response
)
from shared.utils.streaming_utils import sanitize_content

logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    """Status of expert execution."""
    WAITING = "waiting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    QUEUED = "queued"


@dataclass
class ExpertExecutionTask:
    """Represents a single expert execution task."""
    expert_id: str
    expert_role: str
    model_name: str
    prompt_data: Dict[str, Any]
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    status: ExecutionStatus = ExecutionStatus.WAITING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    tools_used: List[str] = None
    
    def __post_init__(self):
        if self.tools_used is None:
            self.tools_used = []


class ParallelExpertExecutor:
    """
    Orchestrates parallel execution of expert agents with resource management.
    Integrates with model resource manager for GPU constraint enforcement.
    """
    
    def __init__(self):
        self.active_executions: Dict[str, ExpertExecutionTask] = {}
        self.execution_history: List[ExpertExecutionTask] = []
        self._execution_lock = asyncio.Lock()
        
        # Expert model mapping functions
        self.expert_model_fields = {
            "project_manager": "project_manager_model",
            "technical_expert": "technical_expert_model",
            "business_analyst": "business_analyst_model",
            "creative_director": "creative_director_model",
            "research_specialist": "research_specialist_model",
            "planning_expert": "planning_expert_model",
            "socratic_expert": "socratic_expert_model",
            "wellbeing_coach": "wellbeing_coach_model",
            "personal_assistant": "personal_assistant_model",
            "data_analyst": "data_analyst_model",
            "output_formatter": "output_formatter_model",
            "quality_assurance": "quality_assurance_model"
        }
    
    def get_expert_model(self, expert_id: str, user_settings: Dict[str, Any]) -> str:
        """
        Get the configured model for an expert from user settings.
        
        Args:
            expert_id: The expert identifier (e.g., "research_specialist")
            user_settings: User settings containing model configurations
            
        Returns:
            Model name to use for this expert
        """
        model_field = self.expert_model_fields.get(expert_id)
        if model_field and model_field in user_settings:
            model_name = user_settings[model_field]
            if model_name:
                logger.info(f"Using configured model {model_name} for {expert_id}")
                return model_name
        
        # Fallback to default models based on expert type
        default_models = {
            "project_manager": "llama3.2:3b",
            "technical_expert": "llama3.1:8b",
            "business_analyst": "llama3.2:3b",
            "creative_director": "llama3.2:3b",
            "research_specialist": "llama3.1:8b",
            "planning_expert": "llama3.2:3b",
            "socratic_expert": "llama3.2:3b",
            "wellbeing_coach": "llama3.2:3b",
            "personal_assistant": "mistral:7b",
            "data_analyst": "qwen2.5:7b",
            "output_formatter": "llama3.2:3b",
            "quality_assurance": "llama3.2:3b"
        }
        
        default_model = default_models.get(expert_id, "llama3.2:3b")
        logger.info(f"Using default model {default_model} for {expert_id}")
        return default_model
    
    async def execute_experts_in_parallel(
        self,
        expert_tasks: List[Dict[str, Any]],
        user_settings: Dict[str, Any],
        session_id: str,
        user_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute multiple experts in parallel within resource constraints.
        
        Args:
            expert_tasks: List of expert task definitions
            user_settings: User settings containing model configurations
            session_id: Session identifier
            user_id: User identifier for tool usage
            
        Yields:
            Execution status updates and results
        """
        logger.info(f"Starting parallel execution of {len(expert_tasks)} experts")
        
        # Create execution tasks with model assignments
        execution_tasks = []
        for task_data in expert_tasks:
            expert_id = task_data["expert_id"]
            expert_role = task_data["expert_role"]
            model_name = self.get_expert_model(expert_id, user_settings)
            
            task = ExpertExecutionTask(
                expert_id=expert_id,
                expert_role=expert_role,
                model_name=model_name,
                prompt_data=task_data.get("prompt_data", {}),
                user_id=user_id,
                session_id=session_id
            )
            execution_tasks.append(task)
        
        # Group tasks by resource compatibility
        parallel_groups = await self._group_by_resource_compatibility(execution_tasks)
        
        # Execute groups sequentially, tasks within groups in parallel
        for group_index, task_group in enumerate(parallel_groups):
            yield {
                "type": "parallel_group_start",
                "content": sanitize_content(f"🚀 **Parallel Group {group_index + 1}**: Starting {len(task_group)} experts simultaneously"),
                "metadata": {
                    "group_index": group_index,
                    "experts_in_group": [task.expert_id for task in task_group],
                    "models_used": [task.model_name for task in task_group]
                },
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
            }
            
            # Execute tasks in this group in parallel
            await asyncio.sleep(0.5)  # Brief pause for better UX
            async for result in self._execute_task_group_parallel(task_group):
                yield result
            
            yield {
                "type": "parallel_group_complete",
                "content": sanitize_content(f"✅ **Group {group_index + 1} Complete**: All experts finished"),
                "metadata": {
                    "group_index": group_index,
                    "completed_experts": len(task_group)
                },
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
            }
            
            # Brief pause between groups
            await asyncio.sleep(0.3)
        
        # Final summary
        total_experts = sum(len(group) for group in parallel_groups)
        completed_experts = len([task for group in parallel_groups for task in group if task.status == ExecutionStatus.COMPLETED])
        
        yield {
            "type": "parallel_execution_complete",
            "content": sanitize_content(f"🎯 **Parallel Execution Complete**: {completed_experts}/{total_experts} experts completed successfully"),
            "metadata": {
                "total_groups": len(parallel_groups),
                "total_experts": total_experts,
                "completed_experts": completed_experts,
                "execution_summary": self._generate_execution_summary(execution_tasks)
            },
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
        }
    
    async def _group_by_resource_compatibility(
        self, 
        tasks: List[ExpertExecutionTask]
    ) -> List[List[ExpertExecutionTask]]:
        """
        Group tasks into parallel execution groups based on resource constraints.
        
        Returns:
            List of task groups that can be executed in parallel
        """
        groups = []
        remaining_tasks = tasks.copy()
        
        while remaining_tasks:
            # Get agent/model pairs for remaining tasks
            agent_model_pairs = [(task.expert_id, task.model_name) for task in remaining_tasks]
            
            # Get compatible pairs for parallel execution
            compatible_pairs = model_resource_manager.get_compatible_agents_for_parallel_execution(
                agent_model_pairs
            )
            
            if not compatible_pairs:
                # If no tasks can run in parallel, take the first one
                compatible_pairs = [agent_model_pairs[0]]
            
            # Create group from compatible tasks
            group_tasks = []
            for expert_id, model_name in compatible_pairs:
                # Find and remove the task from remaining_tasks
                for task in remaining_tasks[:]:
                    if task.expert_id == expert_id and task.model_name == model_name:
                        group_tasks.append(task)
                        remaining_tasks.remove(task)
                        break
            
            if group_tasks:
                groups.append(group_tasks)
        
        logger.info(f"Grouped {len(tasks)} tasks into {len(groups)} parallel execution groups")
        for i, group in enumerate(groups):
            group_info = [(task.expert_id, task.model_name) for task in group]
            logger.info(f"Group {i + 1}: {group_info}")
        
        return groups
    
    async def _execute_task_group_parallel(
        self, 
        task_group: List[ExpertExecutionTask]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute a group of tasks in parallel."""
        
        # Reserve execution slots for all tasks in the group
        agent_model_pairs = [(task.expert_id, task.model_name) for task in task_group]
        reserved_pairs = await model_resource_manager.batch_reserve_slots(agent_model_pairs)
        
        # Create execution coroutines for reserved tasks
        execution_coroutines = []
        reserved_tasks = []
        
        for task in task_group:
            if (task.expert_id, task.model_name) in reserved_pairs:
                reserved_tasks.append(task)
                execution_coroutines.append(self._execute_single_expert(task))
            else:
                # Task couldn't get a slot, mark as queued
                task.status = ExecutionStatus.QUEUED
                yield {
                    "type": "expert_queued",
                    "expert": task.expert_role,
                    "expert_id": task.expert_id,
                    "content": sanitize_content(f"**{task.expert_role}** queued due to resource constraints (model: {task.model_name})"),
                    "metadata": {
                        "model_name": task.model_name,
                        "reason": "resource_constraints"
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
                }
        
        if not execution_coroutines:
            logger.warning("No tasks could be executed in this group")
            return
        
        # Execute tasks in parallel and stream results
        try:
            # Use asyncio.gather to run all expert executions concurrently
            results = await asyncio.gather(*execution_coroutines, return_exceptions=True)
            
            # Process results
            for task, result in zip(reserved_tasks, results):
                if isinstance(result, Exception):
                    task.status = ExecutionStatus.FAILED
                    task.error = str(result)
                    task.end_time = datetime.now(timezone.utc)
                    
                    yield {
                        "type": "expert_error",
                        "expert": task.expert_role,
                        "expert_id": task.expert_id,
                        "content": sanitize_content(f"**{task.expert_role}** encountered an error: {str(result)}"),
                        "metadata": {
                            "model_name": task.model_name,
                            "error": str(result)
                        },
                        "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
                    }
                else:
                    task.result = result
                    task.status = ExecutionStatus.COMPLETED
                    task.end_time = datetime.now(timezone.utc)
                    
                    # Stream the expert response
                    yield {
                        "type": "expert_response",
                        "expert": task.expert_role,
                        "expert_id": task.expert_id,
                        "content": sanitize_content(result.get("input", "")),
                        "metadata": {
                            "model_name": task.model_name,
                            "tools_used": result.get("tools_used", []),
                            "confidence": result.get("confidence", 0.85),
                            "parallel_execution": True,
                            "execution_time_seconds": (task.end_time - task.start_time).total_seconds() if task.start_time else None
                        },
                        "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
                    }
        
        finally:
            # Release execution slots for all reserved tasks
            for task in reserved_tasks:
                await model_resource_manager.release_execution_slot(task.model_name, task.expert_id)
    
    async def _execute_single_expert(self, task: ExpertExecutionTask) -> Dict[str, Any]:
        """Execute a single expert task."""
        task.status = ExecutionStatus.RUNNING
        task.start_time = datetime.now(timezone.utc)
        
        try:
            # Store in active executions
            async with self._execution_lock:
                self.active_executions[task.expert_id] = task
            
            # Execute based on expert type with specialized tool usage
            if task.expert_role == "Research Specialist":
                # Use specialized tool method for research
                result = await research_specialist_with_tools(
                    task.prompt_data.get("user_request", ""),
                    task.prompt_data.get("question", ""), 
                    task.user_id,
                    [],  # tool_calls_made
                    {}   # search_results
                )
            elif task.expert_role == "Personal Assistant":
                # Use specialized tool method for calendar
                result = await personal_assistant_with_tools(
                    task.prompt_data.get("user_request", ""),
                    task.prompt_data.get("question", ""),
                    task.user_id,
                    [],  # tool_calls_made  
                    {}   # calendar_data
                )
            else:
                # Standard expert response without tools
                result = await standard_expert_response(
                    task.expert_role,
                    task.prompt_data.get("user_request", ""),
                    task.prompt_data.get("question", "")
                )
            
            task.tools_used = result.get("tools_used", [])
            logger.info(f"Expert {task.expert_id} completed successfully with model {task.model_name}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing expert {task.expert_id}: {e}", exc_info=True)
            raise
        
        finally:
            # Remove from active executions
            async with self._execution_lock:
                self.active_executions.pop(task.expert_id, None)
                self.execution_history.append(task)
    
    def _generate_execution_summary(self, tasks: List[ExpertExecutionTask]) -> Dict[str, Any]:
        """Generate a summary of the parallel execution."""
        summary = {
            "total_tasks": len(tasks),
            "completed": len([t for t in tasks if t.status == ExecutionStatus.COMPLETED]),
            "failed": len([t for t in tasks if t.status == ExecutionStatus.FAILED]),
            "queued": len([t for t in tasks if t.status == ExecutionStatus.QUEUED]),
            "models_used": {},
            "tools_usage": {},
            "execution_times": []
        }
        
        for task in tasks:
            # Count model usage
            model = task.model_name
            if model not in summary["models_used"]:
                summary["models_used"][model] = 0
            summary["models_used"][model] += 1
            
            # Count tool usage
            for tool in task.tools_used:
                if tool not in summary["tools_usage"]:
                    summary["tools_usage"][tool] = 0
                summary["tools_usage"][tool] += 1
            
            # Execution times
            if task.start_time and task.end_time:
                execution_time = (task.end_time - task.start_time).total_seconds()
                summary["execution_times"].append({
                    "expert": task.expert_id,
                    "seconds": execution_time
                })
        
        return summary
    
    async def get_execution_status(self) -> Dict[str, Any]:
        """Get current execution status for monitoring."""
        async with self._execution_lock:
            return {
                "active_executions": len(self.active_executions),
                "active_experts": list(self.active_executions.keys()),
                "execution_history_count": len(self.execution_history),
                "resource_status": await model_resource_manager.get_resource_status()
            }


# Global instance
parallel_expert_executor = ParallelExpertExecutor()