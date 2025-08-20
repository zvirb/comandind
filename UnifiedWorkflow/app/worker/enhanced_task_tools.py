#!/usr/bin/env python3
"""
Enhanced Task Management Tools with Smart Multi-Task Processing

This module provides enhanced task management functionality that can:
1. Parse complex multi-task requests
2. Create task hierarchies and dependencies
3. Handle bulk task operations
4. Provide project management capabilities
5. Integrate with calendar for deadlines
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from worker.services.ollama_service import invoke_llm_with_tokens
from worker.services.progress_manager import progress_manager
from worker.graph_types import GraphState
from worker.task_management_tools import (
    create_task,
    update_task_status,
    get_task_list,
    prioritize_tasks,
    get_task_analytics,
    create_task_template,
    estimate_task_completion
)

logger = logging.getLogger(__name__)

@dataclass
class ParsedTask:
    """Represents a parsed task from natural language"""
    title: str
    description: str = ""
    priority: str = "medium"  # low, medium, high
    due_date: Optional[str] = None
    estimated_hours: Optional[float] = None
    category: str = ""
    tags: List[str] = None
    dependencies: List[str] = None
    subtasks: List[str] = None
    status: str = "pending"
    project: str = ""
    confidence_score: float = 0.0

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.dependencies is None:
            self.dependencies = []
        if self.subtasks is None:
            self.subtasks = []

@dataclass
class TaskHierarchy:
    """Represents a hierarchical task structure"""
    main_task: ParsedTask
    subtasks: List[ParsedTask]
    dependencies: Dict[str, List[str]]  # task_id -> list of dependency task_ids

@dataclass
class MultiTaskProcessingResult:
    """Result of processing multiple tasks"""
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    created_task_ids: List[str]
    failed_task_details: List[Dict[str, Any]]
    processing_summary: str
    task_hierarchy: Optional[TaskHierarchy] = None

class EnhancedTaskProcessor:
    """Enhanced task processing with multi-task and project support"""
    
    def __init__(self):
        self.default_task_duration = 2.0  # hours
        self.priority_keywords = {
            "urgent": "high",
            "asap": "high", 
            "critical": "high",
            "important": "high",
            "low priority": "low",
            "when possible": "low",
            "sometime": "low"
        }
        
    async def parse_multi_task_request(self, state: GraphState, request: str) -> Tuple[List[ParsedTask], Dict[str, Any]]:
        """
        Parse a complex task request that may contain multiple tasks, projects, or hierarchies
        """
        parsing_prompt = f"""You are an expert task management assistant. Parse this request to identify ALL tasks that need to be created, including any project structure or task hierarchies.

User Request: {request}

Analyze the request and respond with JSON in this exact format:
{{
  "parsing_result": {{
    "tasks_found": [
      {{
        "title": "Task title (clear, actionable)",
        "description": "Detailed description if provided",
        "priority": "low/medium/high",
        "due_date": "2025-07-25" (YYYY-MM-DD format if date mentioned),
        "estimated_hours": 2.0 (estimate based on task complexity),
        "category": "work/personal/academic/health/project/etc",
        "tags": ["tag1", "tag2"],
        "dependencies": ["depends on task title"],
        "subtasks": ["subtask 1", "subtask 2"],
        "project": "Project name if this is part of a larger project",
        "confidence_score": 0.0-1.0
      }}
    ],
    "project_structure": {{
      "is_project": true/false,
      "project_name": "Project name if identified",
      "has_dependencies": true/false,
      "has_subtasks": true/false,
      "complexity_level": "simple/moderate/complex"
    }},
    "missing_info": {{
      "needs_deadlines": true/false,
      "needs_priorities": true/false,
      "needs_details": true/false,
      "specific_questions": [
        "When should the project be completed?",
        "What's the priority of each task?"
      ]
    }},
    "can_proceed_immediately": true/false,
    "processing_strategy": "immediate/ask_clarification/create_project/create_hierarchy"
  }}
}}

Guidelines:
- Look for multiple tasks, projects, phases, or steps
- Identify task dependencies (e.g., "after completing X, do Y")
- Extract priorities from language (urgent, important, low priority, etc.)
- Identify project-like requests (building something, multi-phase work)
- Break down complex requests into manageable tasks
- Estimate time based on task complexity (simple: 1-2 hours, moderate: 3-6 hours, complex: 6+ hours)  
- Set confidence score based on how clear the information is
- Use "immediate" only if all tasks are clear and complete
- Use "ask_clarification" if critical information is missing
- Use "create_project" if this is clearly a multi-phase project
- Use "create_hierarchy" if tasks have clear dependencies

Current date/time context: {datetime.now().strftime('%Y-%m-%d %H:%M')}"""

        try:
            model_name = getattr(state, 'tool_selection_model', 'llama3.2:3b')
            
            response, _ = await invoke_llm_with_tokens(
                messages=[
                    {"role": "system", "content": "You are a task analysis expert. Always respond with valid JSON only."},
                    {"role": "user", "content": parsing_prompt}
                ],
                model_name=model_name,
                category="task_parsing"
            )
            
            # Parse JSON response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                parsed_data = json.loads(json_str)
                parsing_result = parsed_data.get("parsing_result", {})
                
                # Convert to ParsedTask objects
                tasks = []
                for task_data in parsing_result.get("tasks_found", []):
                    task = ParsedTask(
                        title=task_data.get("title", "Task"),
                        description=task_data.get("description", ""),
                        priority=task_data.get("priority", "medium"),
                        due_date=task_data.get("due_date"),
                        estimated_hours=task_data.get("estimated_hours", self.default_task_duration),
                        category=task_data.get("category", ""),
                        tags=task_data.get("tags", []),
                        dependencies=task_data.get("dependencies", []),
                        subtasks=task_data.get("subtasks", []),
                        project=task_data.get("project", ""),
                        confidence_score=task_data.get("confidence_score", 0.8)
                    )
                    tasks.append(task)
                
                return tasks, parsing_result
            else:
                raise ValueError("Could not parse JSON response from LLM")
                
        except Exception as e:
            logger.error(f"Error parsing multi-task request: {e}", exc_info=True)
            # Fallback: create a single generic task
            fallback_task = ParsedTask(
                title="Task from request",
                description=request,
                confidence_score=0.3
            )
            fallback_result = {
                "can_proceed_immediately": False,
                "processing_strategy": "ask_clarification",
                "missing_info": {
                    "needs_details": True,
                    "specific_questions": ["Could you provide more specific details about the tasks you'd like to create?"]
                }
            }
            return [fallback_task], fallback_result
    
    async def create_task_hierarchy(self, tasks: List[ParsedTask], parsing_result: Dict[str, Any]) -> TaskHierarchy:
        """
        Create a task hierarchy with dependencies
        """
        project_structure = parsing_result.get("project_structure", {})
        
        # Identify main task (usually the first or most comprehensive one)
        main_task = tasks[0] if tasks else ParsedTask(title="Project")
        
        # If this is a project, create a main project task
        if project_structure.get("is_project", False):
            project_name = project_structure.get("project_name", main_task.title)
            main_task = ParsedTask(
                title=f"Complete {project_name}",
                description=f"Main project task for: {project_name}",
                priority="high",
                category="project",
                project=project_name,
                confidence_score=0.9
            )
            
            # Make all other tasks subtasks of the main project
            for task in tasks:
                task.project = project_name
        
        # Build dependency map
        dependencies = {}
        for task in tasks:
            if task.dependencies:
                dependencies[task.title] = task.dependencies
        
        hierarchy = TaskHierarchy(
            main_task=main_task,
            subtasks=tasks[1:] if project_structure.get("is_project", False) else tasks,
            dependencies=dependencies
        )
        
        return hierarchy
    
    async def create_tasks_iteratively(self, state: GraphState, tasks: List[ParsedTask], hierarchy: Optional[TaskHierarchy] = None) -> MultiTaskProcessingResult:
        """
        Create multiple tasks with dependency handling and progress tracking
        """
        logger.info(f"Creating {len(tasks)} tasks iteratively")
        
        results = MultiTaskProcessingResult(
            total_tasks=len(tasks),
            successful_tasks=0,
            failed_tasks=0,
            created_task_ids=[],
            failed_task_details=[],
            processing_summary="",
            task_hierarchy=hierarchy
        )
        
        # Notify user of batch operation start
        if state.session_id:
            await progress_manager.broadcast_to_session_sync(state.session_id, {
                "type": "batch_task_operation_started",
                "total_tasks": len(tasks),
                "task_titles": [task.title for task in tasks],
                "is_project": hierarchy is not None
            })
        
        # Create tasks in dependency order if hierarchy exists
        if hierarchy:
            ordered_tasks = self._order_tasks_by_dependencies(tasks, hierarchy.dependencies)
        else:
            ordered_tasks = tasks
        
        for i, task in enumerate(ordered_tasks):
            try:
                logger.info(f"Creating task {i+1}/{len(ordered_tasks)}: {task.title}")
                
                # Update progress
                if state.session_id:
                    await progress_manager.broadcast_to_session_sync(state.session_id, {
                        "type": "batch_task_progress",
                        "current_task": i + 1,
                        "total_tasks": len(ordered_tasks),
                        "task_title": task.title,
                        "progress_percentage": ((i) / len(ordered_tasks)) * 100
                    })
                
                # Create the task using existing tool
                result = create_task(
                    title=task.title,
                    description=task.description,
                    priority=task.priority,
                    due_date=task.due_date,
                    tags=task.tags
                )
                
                if result.get("success", False):
                    results.successful_tasks += 1
                    task_id = result.get("task_id", f"task_{i+1}")
                    results.created_task_ids.append(task_id)
                    
                    logger.info(f"Successfully created task: {task.title}")
                    
                    # Create subtasks if they exist
                    if task.subtasks:
                        await self._create_subtasks(task, task_id, state)
                else:
                    results.failed_tasks += 1
                    error_details = {
                        "task_title": task.title,
                        "error": result.get("message", "Unknown error"),
                        "task_data": {
                            "priority": task.priority,
                            "due_date": task.due_date,
                            "description": task.description
                        }
                    }
                    results.failed_task_details.append(error_details)
                    logger.error(f"Failed to create task {task.title}: {error_details['error']}")
                
                # Small delay between tasks
                if i < len(ordered_tasks) - 1:
                    await asyncio.sleep(0.3)
                    
            except Exception as e:
                logger.error(f"Exception creating task {task.title}: {e}", exc_info=True)
                results.failed_tasks += 1
                results.failed_task_details.append({
                    "task_title": task.title,
                    "error": str(e),
                    "exception": True
                })
        
        # Generate summary
        results.processing_summary = self._generate_task_processing_summary(results)
        
        # Notify completion
        if state.session_id:
            await progress_manager.broadcast_to_session_sync(state.session_id, {
                "type": "batch_task_operation_completed",
                "total_tasks": results.total_tasks,
                "successful_tasks": results.successful_tasks,
                "failed_tasks": results.failed_tasks,
                "summary": results.processing_summary
            })
        
        return results
    
    def _order_tasks_by_dependencies(self, tasks: List[ParsedTask], dependencies: Dict[str, List[str]]) -> List[ParsedTask]:
        """
        Order tasks based on their dependencies using topological sort
        """
        # Simple implementation - can be enhanced with proper topological sort
        ordered = []
        remaining = tasks.copy()
        
        while remaining:
            # Find tasks with no unmet dependencies
            ready_tasks = []
            for task in remaining:
                if not task.dependencies or all(dep in [t.title for t in ordered] for dep in task.dependencies):
                    ready_tasks.append(task)
            
            if ready_tasks:
                # Add ready tasks to ordered list
                ordered.extend(ready_tasks)
                for task in ready_tasks:
                    remaining.remove(task)
            else:
                # If no ready tasks, add remaining (circular dependencies or missing deps)
                ordered.extend(remaining)
                break
        
        return ordered
    
    async def _create_subtasks(self, parent_task: ParsedTask, parent_id: str, state: GraphState):
        """
        Create subtasks for a parent task
        """
        for subtask_title in parent_task.subtasks:
            try:
                subtask_result = create_task(
                    title=subtask_title,
                    description=f"Subtask of: {parent_task.title}",
                    priority=parent_task.priority,
                    due_date=parent_task.due_date,
                    tags=parent_task.tags + ["subtask"]
                )
                
                if subtask_result.get("success"):
                    logger.info(f"Created subtask: {subtask_title}")
                else:
                    logger.warning(f"Failed to create subtask: {subtask_title}")
                    
            except Exception as e:
                logger.error(f"Error creating subtask {subtask_title}: {e}")
    
    def _generate_task_processing_summary(self, results: MultiTaskProcessingResult) -> str:
        """Generate a human-readable summary of the task processing results"""
        
        summary_parts = []
        
        if results.successful_tasks == results.total_tasks:
            summary_parts.append(f"✅ Successfully created all {results.total_tasks} tasks!")
        elif results.successful_tasks > 0:
            summary_parts.append(f"✅ Created {results.successful_tasks} of {results.total_tasks} tasks.")
            summary_parts.append(f"❌ {results.failed_tasks} tasks failed to create.")
        else:
            summary_parts.append(f"❌ Failed to create any of the {results.total_tasks} tasks.")
        
        # Add project information
        if results.task_hierarchy:
            summary_parts.append(f"\n**Project Structure:**")
            summary_parts.append(f"• Main task: {results.task_hierarchy.main_task.title}")
            if results.task_hierarchy.subtasks:
                summary_parts.append(f"• Subtasks: {len(results.task_hierarchy.subtasks)}")
            if results.task_hierarchy.dependencies:
                summary_parts.append(f"• Dependencies: {len(results.task_hierarchy.dependencies)} relationships")
        
        # Add task details
        if results.successful_tasks > 0:
            summary_parts.append(f"\n**Successfully created tasks:**")
            # Note: We'd need to track task titles in results to show them here
            summary_parts.append(f"• {results.successful_tasks} tasks ready to work on")
        
        # Add failure details
        if results.failed_tasks > 0:
            summary_parts.append(f"\n**Failed tasks:**")
            for failure in results.failed_task_details[:3]:  # Show first 3 failures
                summary_parts.append(f"• {failure['task_title']}: {failure['error']}")
            
            if len(results.failed_task_details) > 3:
                summary_parts.append(f"... and {len(results.failed_task_details) - 3} more")
        
        return "\n".join(summary_parts)

# Global processor instance
enhanced_task_processor = EnhancedTaskProcessor()

async def handle_smart_task_request(state: GraphState) -> Dict[str, Any]:
    """
    Enhanced task handler that can process complex multi-task requests
    """
    request = state.user_input
    logger.info(f"Processing smart task request: {request[:100]}...")
    
    try:
        # Parse the request to identify multiple tasks
        tasks, parsing_result = await enhanced_task_processor.parse_multi_task_request(state, request)
        
        logger.info(f"Parsed {len(tasks)} tasks from request")
        
        # Check processing strategy
        processing_strategy = parsing_result.get("processing_strategy", "ask_clarification")
        
        if processing_strategy == "ask_clarification":
            # Generate clarification questions
            missing_info = parsing_result.get("missing_info", {})
            questions = missing_info.get("specific_questions", [])
            
            if questions:
                question_text = f"I found {len(tasks)} potential tasks in your request:\n\n"
                for i, task in enumerate(tasks, 1):
                    question_text += f"{i}. {task.title}\n"
                
                question_text += f"\nTo create these tasks properly, I need some additional information:\n\n"
                for i, question in enumerate(questions, 1):
                    question_text += f"{i}. {question}\n"
                
                question_text += "\nPlease provide these details so I can create your tasks."
                
                return {
                    "response": question_text,
                    "requires_user_input": True,
                    "tasks_identified": len(tasks),
                    "parsing_result": parsing_result
                }
        
        elif processing_strategy in ["create_project", "create_hierarchy"]:
            # Create task hierarchy and process
            hierarchy = await enhanced_task_processor.create_task_hierarchy(tasks, parsing_result)
            all_tasks = [hierarchy.main_task] + hierarchy.subtasks
            
            batch_result = await enhanced_task_processor.create_tasks_iteratively(state, all_tasks, hierarchy)
            
            return {
                "response": batch_result.processing_summary,
                "batch_processing": True,
                "is_project": True,
                "total_tasks": batch_result.total_tasks,
                "successful_tasks": batch_result.successful_tasks,
                "failed_tasks": batch_result.failed_tasks
            }
        
        elif processing_strategy == "immediate":
            # Create tasks immediately
            if len(tasks) == 1:
                # Single task - use standard creation
                task = tasks[0]
                result = create_task(
                    title=task.title,
                    description=task.description,
                    priority=task.priority,
                    due_date=task.due_date,
                    tags=task.tags
                )
                
                if result.get("success"):
                    return {"response": result.get("message", "Task created successfully")}
                else:
                    return {"response": result.get("message", "Failed to create task")}
            else:
                # Multiple tasks - use batch processing
                batch_result = await enhanced_task_processor.create_tasks_iteratively(state, tasks)
                
                return {
                    "response": batch_result.processing_summary,
                    "batch_processing": True,
                    "total_tasks": batch_result.total_tasks,
                    "successful_tasks": batch_result.successful_tasks,
                    "failed_tasks": batch_result.failed_tasks
                }
        
        else:
            # Fallback
            return {
                "response": "I'll help you create tasks. Could you provide more specific details about the tasks you'd like to create?",
                "requires_clarification": True
            }
            
    except Exception as e:
        logger.error(f"Error in smart task request handling: {e}", exc_info=True)
        return {
            "response": "I encountered an error while processing your task request. Please try again with more specific details.",
            "error": str(e)
        }