"""
Enhanced Smart Router Service with User Approval Workflow
Implements plan-first approach with user approval and real-time streaming
"""

import logging
import asyncio
import json
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone
from enum import Enum

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from worker.graph_types import GraphState
from worker.services.ollama_service import invoke_llm_with_tokens
from worker.tool_registry import AVAILABLE_TOOLS
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PlanStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionStep:
    def __init__(self, step_id: str, description: str, tool: str, parameters: Dict[str, Any]):
        self.step_id = step_id
        self.description = description
        self.tool = tool
        self.parameters = parameters
        self.status = "pending"
        self.result = None
        self.error = None
        self.started_at = None
        self.completed_at = None


class ExecutionPlan:
    def __init__(self, plan_id: str, user_input: str, steps: List[ExecutionStep]):
        self.plan_id = plan_id
        self.user_input = user_input
        self.steps = steps
        self.status = PlanStatus.PENDING
        self.created_at = datetime.now(timezone.utc)
        self.approved_at = None
        self.completed_at = None
        self.user_feedback = None


class EnhancedSmartRouterService:
    """Enhanced smart router with user approval workflow and streaming updates."""
    
    def __init__(self):
        self.active_plans: Dict[str, ExecutionPlan] = {}
        self.progress_callbacks: Dict[str, List[Callable]] = {}
    
    async def process_user_request(
        self,
        user_input: str,
        user_id: int,
        session_id: str,
        stream_callback: Optional[Callable] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process user request with plan-first approach.
        """
        try:
            await self._stream_update(stream_callback, {
                "type": "status",
                "message": "Analyzing your request...",
                "progress": 10
            })
            
            # Analyze request complexity
            complexity_analysis = await self._analyze_request_complexity(user_input, user_id)
            
            await self._stream_update(stream_callback, {
                "type": "analysis",
                "complexity": complexity_analysis,
                "message": f"Request complexity: {complexity_analysis['level']}",
                "progress": 30
            })
            
            # Decide if planning is needed
            if complexity_analysis["requires_planning"]:
                return await self._handle_planning_workflow(
                    user_input, user_id, session_id, stream_callback, context
                )
            else:
                return await self._handle_direct_execution(
                    user_input, user_id, session_id, stream_callback, context
                )
            
        except Exception as e:
            logger.error(f"Error in enhanced smart router: {e}", exc_info=True)
            await self._stream_update(stream_callback, {
                "type": "error",
                "message": f"Error processing request: {str(e)}",
                "progress": 100
            })
            return {
                "response": "I encountered an error processing your request. Please try again.",
                "status": "error",
                "error": str(e)
            }
    
    async def _analyze_request_complexity(self, user_input: str, user_id: int) -> Dict[str, Any]:
        """Analyze if request requires planning or can be handled directly."""
        
        analysis_prompt = f"""Analyze this user request to determine if it requires multi-step planning or can be handled directly.

User Request: "{user_input}"

Consider:
1. Does it involve multiple tools or steps?
2. Are there dependencies between actions?
3. Does it require data from one step to inform the next?
4. Is it a complex workflow or simple single action?

Respond with JSON:
{{
  "requires_planning": true/false,
  "level": "simple|moderate|complex",
  "reasoning": "Brief explanation",
  "estimated_steps": number,
  "suggested_tools": ["tool1", "tool2"],
  "confidence": 0.0-1.0
}}"""
        
        try:
            messages = [
                {"role": "system", "content": "You are an expert request analyzer. Analyze user requests and determine complexity level. Always respond with valid JSON."},
                {"role": "user", "content": analysis_prompt}
            ]
            
            response, _ = await invoke_llm_with_tokens(
                messages,
                "llama3.2:3b",
                category="complexity_analysis"
            )
            
            # Parse JSON response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                analysis = json.loads(json_str)
                return analysis
            
        except Exception as e:
            logger.error(f"Error in complexity analysis: {e}")
        
        # Fallback analysis
        return {
            "requires_planning": len(user_input.split()) > 20 or "and" in user_input.lower(),
            "level": "moderate",
            "reasoning": "Fallback analysis due to parsing error",
            "estimated_steps": 2,
            "suggested_tools": [],
            "confidence": 0.5
        }
    
    async def _handle_planning_workflow(
        self,
        user_input: str,
        user_id: int,
        session_id: str,
        stream_callback: Optional[Callable],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Handle requests that require planning and user approval."""
        
        await self._stream_update(stream_callback, {
            "type": "status",
            "message": "Creating execution plan...",
            "progress": 50
        })
        
        # Generate execution plan
        plan = await self._generate_execution_plan(user_input, user_id, context)
        
        if not plan:
            return {
                "response": "I couldn't create a plan for your request. Please try rephrasing it.",
                "status": "planning_failed"
            }
        
        # Store plan for approval
        self.active_plans[plan.plan_id] = plan
        
        await self._stream_update(stream_callback, {
            "type": "plan_created",
            "plan": self._serialize_plan(plan),
            "message": "Plan created. Please review and approve.",
            "progress": 70
        })
        
        return {
            "response": "I've created a plan for your request. Please review the steps and let me know if you'd like me to proceed or make any changes.",
            "status": "awaiting_approval",
            "plan_id": plan.plan_id,
            "plan": self._serialize_plan(plan),
            "requires_approval": True
        }
    
    async def _generate_execution_plan(
        self,
        user_input: str,
        user_id: int,
        context: Optional[Dict[str, Any]]
    ) -> Optional[ExecutionPlan]:
        """Generate detailed execution plan with steps."""
        
        # Build context about available tools
        available_tools_desc = []
        for tool_id, tool_info in AVAILABLE_TOOLS.items():
            available_tools_desc.append(f"- {tool_id}: {tool_info.get('description', 'No description')}")
        
        tools_context = "\n".join(available_tools_desc[:10])  # Limit to prevent prompt overflow
        
        planning_prompt = f"""Create a detailed execution plan for this user request.

User Request: "{user_input}"

Available Tools:
{tools_context}

Create a step-by-step plan with specific tools and parameters. Respond with JSON:

{{
  "plan_summary": "Brief description of what will be accomplished",
  "steps": [
    {{
      "step_id": "step_1",
      "description": "Clear description of what this step does",
      "tool": "tool_name",
      "parameters": {{"param1": "value1"}},
      "depends_on": ["step_0"] or null,
      "estimated_duration": "30 seconds"
    }}
  ],
  "expected_outcome": "What the user can expect as the final result",
  "risks": ["potential issue 1", "potential issue 2"],
  "requires_confirmation": true/false
}}

Guidelines:
- Be specific about tool parameters
- Include dependency information
- Estimate realistic durations
- Identify potential risks or issues
- Only use tools that are actually available"""
        
        try:
            messages = [
                {"role": "system", "content": "You are an expert task planner. Create detailed, executable plans with specific steps and tool usage. Always respond with valid JSON."},
                {"role": "user", "content": planning_prompt}
            ]
            
            response, _ = await invoke_llm_with_tokens(
                messages,
                "llama3.2:3b",
                category="execution_planning"
            )
            
            # Parse JSON response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                plan_data = json.loads(json_str)
                
                # Convert to ExecutionPlan object
                steps = []
                for step_data in plan_data.get("steps", []):
                    step = ExecutionStep(
                        step_id=step_data["step_id"],
                        description=step_data["description"],
                        tool=step_data["tool"],
                        parameters=step_data.get("parameters", {})
                    )
                    steps.append(step)
                
                plan_id = f"plan_{user_id}_{int(datetime.now(timezone.utc).timestamp())}"
                return ExecutionPlan(plan_id, user_input, steps)
            
        except Exception as e:
            logger.error(f"Error generating execution plan: {e}", exc_info=True)
        
        return None
    
    async def _handle_direct_execution(
        self,
        user_input: str,
        user_id: int,
        session_id: str,
        stream_callback: Optional[Callable],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Handle simple requests that don't require planning."""
        
        await self._stream_update(stream_callback, {
            "type": "status",
            "message": "Processing your request...",
            "progress": 60
        })
        
        # Use existing router for direct execution
        from worker.services.router_modules.router_core import run_router_graph
        
        messages = [HumanMessage(content=user_input)]
        if context and context.get("conversation_history"):
            for msg in context["conversation_history"]:
                if msg.get("role") == "user":
                    messages.insert(-1, HumanMessage(content=msg["content"]))
                elif msg.get("role") == "assistant":
                    messages.insert(-1, AIMessage(content=msg["content"]))
        
        result = await run_router_graph(
            user_input=user_input,
            messages=messages,
            user_id=user_id,
            session_id=session_id,
            chat_model="llama3.2:3b"
        )
        
        await self._stream_update(stream_callback, {
            "type": "completed",
            "message": "Request completed successfully",
            "progress": 100
        })
        
        return {
            **result,
            "status": "completed",
            "requires_approval": False
        }
    
    async def approve_plan(
        self,
        plan_id: str,
        user_id: int,
        modifications: Optional[Dict[str, Any]] = None,
        stream_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Approve and execute a plan."""
        
        if plan_id not in self.active_plans:
            return {
                "error": "Plan not found or expired",
                "status": "plan_not_found"
            }
        
        plan = self.active_plans[plan_id]
        
        # Apply modifications if provided
        if modifications:
            plan = await self._apply_plan_modifications(plan, modifications)
        
        plan.status = PlanStatus.APPROVED
        plan.approved_at = datetime.now(timezone.utc)
        
        await self._stream_update(stream_callback, {
            "type": "plan_approved",
            "message": "Plan approved. Starting execution...",
            "progress": 0
        })
        
        # Execute the plan
        return await self._execute_plan(plan, stream_callback)
    
    async def reject_plan(
        self,
        plan_id: str,
        user_id: int,
        feedback: Optional[str] = None
    ) -> Dict[str, Any]:
        """Reject a plan and optionally provide feedback."""
        
        if plan_id not in self.active_plans:
            return {
                "error": "Plan not found or expired",
                "status": "plan_not_found"
            }
        
        plan = self.active_plans[plan_id]
        plan.status = PlanStatus.REJECTED
        plan.user_feedback = feedback
        
        # Remove from active plans
        del self.active_plans[plan_id]
        
        return {
            "message": "Plan rejected. Please provide a new request or feedback for improvement.",
            "status": "plan_rejected",
            "feedback_received": feedback is not None
        }
    
    async def _execute_plan(
        self,
        plan: ExecutionPlan,
        stream_callback: Optional[Callable]
    ) -> Dict[str, Any]:
        """Execute approved plan with streaming updates."""
        
        plan.status = PlanStatus.EXECUTING
        results = []
        
        try:
            total_steps = len(plan.steps)
            
            for i, step in enumerate(plan.steps):
                progress = int((i / total_steps) * 100)
                
                await self._stream_update(stream_callback, {
                    "type": "step_started",
                    "step": step.step_id,
                    "description": step.description,
                    "progress": progress,
                    "message": f"Executing: {step.description}"
                })
                
                step.status = "executing"
                step.started_at = datetime.now(timezone.utc)
                
                # Execute step
                try:
                    step_result = await self._execute_step(step)
                    step.result = step_result
                    step.status = "completed"
                    results.append(step_result)
                    
                    await self._stream_update(stream_callback, {
                        "type": "step_completed",
                        "step": step.step_id,
                        "result": step_result,
                        "message": f"Completed: {step.description}"
                    })
                    
                except Exception as e:
                    step.error = str(e)
                    step.status = "failed"
                    logger.error(f"Step {step.step_id} failed: {e}")
                    
                    await self._stream_update(stream_callback, {
                        "type": "step_failed",
                        "step": step.step_id,
                        "error": str(e),
                        "message": f"Failed: {step.description}"
                    })
                
                step.completed_at = datetime.now(timezone.utc)
            
            plan.status = PlanStatus.COMPLETED
            plan.completed_at = datetime.now(timezone.utc)
            
            await self._stream_update(stream_callback, {
                "type": "plan_completed",
                "message": "Plan execution completed successfully",
                "progress": 100
            })
            
            # Generate final response
            final_response = await self._generate_final_response(plan, results)
            
            # Clean up
            if plan.plan_id in self.active_plans:
                del self.active_plans[plan.plan_id]
            
            return {
                "response": final_response,
                "status": "completed",
                "plan_id": plan.plan_id,
                "execution_summary": {
                    "total_steps": total_steps,
                    "completed_steps": len([s for s in plan.steps if s.status == "completed"]),
                    "failed_steps": len([s for s in plan.steps if s.status == "failed"]),
                    "execution_time": (plan.completed_at - plan.approved_at).total_seconds()
                }
            }
            
        except Exception as e:
            plan.status = PlanStatus.FAILED
            logger.error(f"Plan execution failed: {e}", exc_info=True)
            
            await self._stream_update(stream_callback, {
                "type": "plan_failed",
                "error": str(e),
                "message": "Plan execution failed"
            })
            
            return {
                "response": f"Plan execution failed: {str(e)}",
                "status": "failed",
                "error": str(e)
            }
    
    async def _execute_step(self, step: ExecutionStep) -> Any:
        """Execute individual step using appropriate tool."""
        
        # Import tool handler
        from worker.tool_handlers import get_tool_handler
        
        tool_handler = get_tool_handler(step.tool)
        if not tool_handler:
            raise Exception(f"Tool handler not found: {step.tool}")
        
        # Execute tool with parameters
        return await tool_handler(step.parameters)
    
    async def _generate_final_response(self, plan: ExecutionPlan, results: List[Any]) -> str:
        """Generate final response based on plan execution results."""
        
        success_count = len([s for s in plan.steps if s.status == "completed"])
        total_count = len(plan.steps)
        
        if success_count == total_count:
            status_msg = "I successfully completed all the requested tasks."
        else:
            failed_count = total_count - success_count
            status_msg = f"I completed {success_count} out of {total_count} tasks. {failed_count} tasks encountered issues."
        
        # Summarize results
        results_summary = []
        for step in plan.steps:
            if step.status == "completed" and step.result:
                results_summary.append(f"✅ {step.description}: Success")
            elif step.status == "failed":
                results_summary.append(f"❌ {step.description}: {step.error}")
        
        summary = "\n".join(results_summary)
        
        return f"{status_msg}\n\nExecution Summary:\n{summary}"
    
    def _serialize_plan(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """Serialize plan for API response."""
        return {
            "plan_id": plan.plan_id,
            "user_input": plan.user_input,
            "status": plan.status.value,
            "created_at": plan.created_at.isoformat(),
            "steps": [
                {
                    "step_id": step.step_id,
                    "description": step.description,
                    "tool": step.tool,
                    "parameters": step.parameters,
                    "status": step.status
                }
                for step in plan.steps
            ]
        }
    
    async def _apply_plan_modifications(
        self,
        plan: ExecutionPlan,
        modifications: Dict[str, Any]
    ) -> ExecutionPlan:
        """Apply user modifications to the plan."""
        # This would implement plan modification logic
        # For now, return the original plan
        return plan
    
    async def _stream_update(
        self,
        callback: Optional[Callable],
        update: Dict[str, Any]
    ):
        """Send streaming update to callback if provided."""
        if callback:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(update)
                else:
                    callback(update)
            except Exception as e:
                logger.error(f"Error in stream callback: {e}")


# Global instance
enhanced_smart_router = EnhancedSmartRouterService()