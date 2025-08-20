"""
Enhanced Parallel Execution Service with LCEL (LangChain 0.3+ features).
Provides parallel processing capabilities for tool execution and LLM calls.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union, Callable, Awaitable
from concurrent.futures import ThreadPoolExecutor, as_completed
from uuid import uuid4

from langchain_core.runnables import RunnableParallel, RunnableLambda, RunnablePassthrough
from langchain_core.runnables.config import RunnableConfig
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

from worker.graph_types import GraphState
from worker.services.enhanced_tool_service import enhanced_tool_service
from shared.schemas.enhanced_chat_schemas import ToolExecutionResult, IntermediateStep, ToolExecutionStatus
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class ParallelTaskResult(BaseModel):
    """Result of a parallel task execution."""
    task_id: str = Field(..., description="Unique task identifier")
    task_name: str = Field(..., description="Task name")
    status: str = Field(..., description="Task status: success, error, timeout")
    result: Optional[Any] = Field(None, description="Task result")
    error: Optional[str] = Field(None, description="Error message if failed")
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")
    started_at: datetime = Field(..., description="Task start time")
    completed_at: datetime = Field(..., description="Task completion time")

class ParallelExecutionPlan(BaseModel):
    """Plan for parallel execution of multiple tasks."""
    plan_id: str = Field(default_factory=lambda: str(uuid4()), description="Execution plan ID")
    tasks: List[Dict[str, Any]] = Field(..., description="List of tasks to execute")
    max_concurrency: int = Field(3, description="Maximum concurrent tasks")
    timeout_seconds: int = Field(30, description="Timeout per task")
    execution_strategy: str = Field("concurrent", description="Execution strategy: concurrent, batch, sequential")

class ParallelExecutionService:
    """Service for parallel execution of tools and LLM calls using LCEL."""
    
    def __init__(self):
        self.ollama_base_url = settings.OLLAMA_API_BASE_URL
        self.max_concurrent_tasks = 5
        self.default_timeout = 30
        
    async def create_parallel_runnable(
        self, 
        tasks: Dict[str, Callable[[GraphState], Awaitable[Any]]]
    ) -> RunnableParallel:
        """Create a parallel runnable from a dict of tasks."""
        try:
            # Convert functions to RunnableLambda instances
            runnable_tasks = {}
            for task_name, task_func in tasks.items():
                runnable_tasks[task_name] = RunnableLambda(task_func)
            
            # Create parallel runnable
            parallel_runnable = RunnableParallel(runnable_tasks)
            
            logger.info(f"Created parallel runnable with {len(tasks)} tasks")
            return parallel_runnable
            
        except Exception as e:
            logger.error(f"Error creating parallel runnable: {e}")
            raise
    
    async def execute_tools_in_parallel(
        self, 
        tool_requests: List[Dict[str, Any]], 
        state: GraphState,
        max_concurrency: Optional[int] = None
    ) -> List[ToolExecutionResult]:
        """Execute multiple tools in parallel with LCEL."""
        if not tool_requests:
            return []
        
        concurrency = max_concurrency or min(len(tool_requests), self.max_concurrent_tasks)
        
        try:
            # Create semaphore for concurrency control
            semaphore = asyncio.Semaphore(concurrency)
            
            async def execute_single_tool(tool_request: Dict[str, Any]) -> ToolExecutionResult:
                async with semaphore:
                    tool_name = tool_request.get("tool_name")
                    tool_input = tool_request.get("input", {})
                    
                    if not tool_name:
                        return ToolExecutionResult(
                            tool_name="unknown",
                            status=ToolExecutionStatus.ERROR,
                            error="Tool name not provided",
                            execution_time_ms=0
                        )
                    
                    return await enhanced_tool_service.execute_tool_with_validation(
                        tool_name, tool_input, state
                    )
            
            # Execute all tools concurrently
            tasks = [execute_single_tool(req) for req in tool_requests]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle exceptions in results
            tool_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    tool_name = tool_requests[i].get("tool_name", "unknown")
                    tool_results.append(ToolExecutionResult(
                        tool_name=tool_name,
                        status=ToolExecutionStatus.ERROR,
                        error=str(result),
                        execution_time_ms=0
                    ))
                else:
                    tool_results.append(result)
            
            logger.info(f"Executed {len(tool_results)} tools in parallel")
            return tool_results
            
        except Exception as e:
            logger.error(f"Error in parallel tool execution: {e}")
            return [ToolExecutionResult(
                tool_name="parallel_execution",
                status=ToolExecutionStatus.ERROR,
                error=str(e),
                execution_time_ms=0
            )]
    
    async def execute_llm_calls_in_parallel(
        self, 
        llm_requests: List[Dict[str, Any]], 
        models: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Execute multiple LLM calls in parallel using LCEL."""
        if not llm_requests:
            return []
        
        try:
            # Create parallel LLM tasks
            parallel_tasks = {}
            
            for i, request in enumerate(llm_requests):
                task_name = f"llm_task_{i}"
                
                # Determine model to use
                model = models[i] if models and i < len(models) else "llama3.2:3b"
                
                # Create LLM instance
                llm = ChatOllama(
                    model=model,
                    base_url=self.ollama_base_url,
                    temperature=request.get("temperature", 0.1)
                )
                
                # Create prompt from request
                from langchain_core.prompts import ChatPromptTemplate
                
                messages = request.get("messages", [])
                if isinstance(messages, list) and messages:
                    prompt = ChatPromptTemplate.from_messages(messages)
                    chain = prompt | llm
                else:
                    # Direct text input
                    chain = llm
                
                # Add to parallel tasks
                parallel_tasks[task_name] = chain
            
            # Create and execute parallel runnable
            if parallel_tasks:
                parallel_runnable = RunnableParallel(parallel_tasks)
                
                # Prepare input data
                input_data = {}
                for i, request in enumerate(llm_requests):
                    task_name = f"llm_task_{i}"
                    input_data[task_name] = request.get("input", {})
                
                # Execute in parallel
                start_time = datetime.now()
                results = await parallel_runnable.ainvoke(input_data)
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                
                # Format results
                formatted_results = []
                for i, (task_name, result) in enumerate(results.items()):
                    formatted_results.append({
                        "task_id": task_name,
                        "model": models[i] if models and i < len(models) else "llama3.2:3b",
                        "result": result.content if hasattr(result, 'content') else str(result),
                        "execution_time_ms": execution_time / len(results),  # Approximate per task
                        "status": "success"
                    })
                
                logger.info(f"Executed {len(formatted_results)} LLM calls in parallel")
                return formatted_results
            
            return []
            
        except Exception as e:
            logger.error(f"Error in parallel LLM execution: {e}")
            return [{
                "task_id": "error",
                "error": str(e),
                "status": "error",
                "execution_time_ms": 0
            }]
    
    async def execute_mixed_parallel_tasks(
        self, 
        execution_plan: ParallelExecutionPlan, 
        state: GraphState
    ) -> List[ParallelTaskResult]:
        """Execute a mix of tools and LLM calls in parallel."""
        try:
            # Separate tool and LLM tasks
            tool_tasks = []
            llm_tasks = []
            other_tasks = []
            
            for task in execution_plan.tasks:
                task_type = task.get("type", "unknown")
                if task_type == "tool":
                    tool_tasks.append(task)
                elif task_type == "llm":
                    llm_tasks.append(task)
                else:
                    other_tasks.append(task)
            
            # Execute different task types in parallel
            results = []
            
            # Create coroutines for different task types
            coroutines = []
            
            if tool_tasks:
                tool_requests = [{
                    "tool_name": task.get("tool_name"),
                    "input": task.get("input", {})
                } for task in tool_tasks]
                coroutines.append(self._execute_tool_batch(tool_requests, state))
            
            if llm_tasks:
                llm_requests = [{
                    "messages": task.get("messages", []),
                    "input": task.get("input", {}),
                    "temperature": task.get("temperature", 0.1)
                } for task in llm_tasks]
                models = [task.get("model", "llama3.2:3b") for task in llm_tasks]
                coroutines.append(self._execute_llm_batch(llm_requests, models))
            
            # Execute all batches concurrently
            if coroutines:
                start_time = datetime.now()
                batch_results = await asyncio.gather(*coroutines, return_exceptions=True)
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                
                # Combine results
                task_index = 0
                for batch_result in batch_results:
                    if isinstance(batch_result, Exception):
                        results.append(ParallelTaskResult(
                            task_id=f"batch_error_{task_index}",
                            task_name="batch_execution",
                            status="error",
                            error=str(batch_result),
                            execution_time_ms=execution_time,
                            started_at=start_time,
                            completed_at=datetime.now()
                        ))
                    elif isinstance(batch_result, list):
                        for result in batch_result:
                            results.append(self._convert_to_parallel_result(result, task_index))
                            task_index += 1
            
            logger.info(f"Executed {len(results)} mixed parallel tasks")
            return results
            
        except Exception as e:
            logger.error(f"Error in mixed parallel execution: {e}")
            return [ParallelTaskResult(
                task_id="execution_error",
                task_name="parallel_execution",
                status="error",
                error=str(e),
                execution_time_ms=0,
                started_at=datetime.now(),
                completed_at=datetime.now()
            )]
    
    async def _execute_tool_batch(
        self, 
        tool_requests: List[Dict[str, Any]], 
        state: GraphState
    ) -> List[ToolExecutionResult]:
        """Execute a batch of tool requests."""
        return await self.execute_tools_in_parallel(tool_requests, state)
    
    async def _execute_llm_batch(
        self, 
        llm_requests: List[Dict[str, Any]], 
        models: List[str]
    ) -> List[Dict[str, Any]]:
        """Execute a batch of LLM requests."""
        return await self.execute_llm_calls_in_parallel(llm_requests, models)
    
    def _convert_to_parallel_result(
        self, 
        result: Union[ToolExecutionResult, Dict[str, Any]], 
        task_index: int
    ) -> ParallelTaskResult:
        """Convert tool or LLM result to ParallelTaskResult."""
        now = datetime.now()
        
        if isinstance(result, ToolExecutionResult):
            return ParallelTaskResult(
                task_id=f"tool_{task_index}",
                task_name=result.tool_name,
                status=result.status.value,
                result=result.result,
                error=result.error,
                execution_time_ms=result.execution_time_ms or 0,
                started_at=now,
                completed_at=now
            )
        elif isinstance(result, dict):
            return ParallelTaskResult(
                task_id=result.get("task_id", f"task_{task_index}"),
                task_name=result.get("model", "llm_task"),
                status=result.get("status", "unknown"),
                result=result.get("result"),
                error=result.get("error"),
                execution_time_ms=result.get("execution_time_ms", 0),
                started_at=now,
                completed_at=now
            )
        else:
            return ParallelTaskResult(
                task_id=f"unknown_{task_index}",
                task_name="unknown_task",
                status="error",
                error="Unknown result type",
                execution_time_ms=0,
                started_at=now,
                completed_at=now
            )
    
    async def create_conditional_parallel_chain(
        self, 
        condition_func: Callable[[GraphState], bool],
        parallel_tasks_true: Dict[str, Callable[[GraphState], Awaitable[Any]]],
        parallel_tasks_false: Dict[str, Callable[[GraphState], Awaitable[Any]]]
    ) -> RunnableLambda:
        """Create a conditional parallel execution chain."""
        async def conditional_execution(state: GraphState) -> Dict[str, Any]:
            try:
                # Evaluate condition
                condition_result = condition_func(state)
                
                # Select appropriate task set
                tasks_to_execute = parallel_tasks_true if condition_result else parallel_tasks_false
                
                # Create and execute parallel runnable
                if tasks_to_execute:
                    parallel_runnable = await self.create_parallel_runnable(tasks_to_execute)
                    results = await parallel_runnable.ainvoke(state)
                    
                    return {
                        "condition_result": condition_result,
                        "parallel_results": results,
                        "execution_path": "true" if condition_result else "false"
                    }
                else:
                    return {
                        "condition_result": condition_result,
                        "parallel_results": {},
                        "execution_path": "true" if condition_result else "false",
                        "message": "No tasks to execute"
                    }
                    
            except Exception as e:
                logger.error(f"Error in conditional parallel execution: {e}")
                return {
                    "condition_result": False,
                    "parallel_results": {},
                    "execution_path": "error",
                    "error": str(e)
                }
        
        return RunnableLambda(conditional_execution)

# Global instance
parallel_execution_service = ParallelExecutionService()