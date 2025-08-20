# /app/worker/services/progress_manager.py

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from redis.asyncio import Redis
import redis
from shared.utils.config import get_settings
from worker.smart_ai_models import (
    TokenMetrics, PauseReason, TaskStatus, ConfidenceLevel, HumanContextModel
)

logger = logging.getLogger(__name__)

# Named agent constants for consistent agent identification
class AgentNames:
    MISSION_ANALYZER = "Mission Analyzer"
    REFLECTION_CRITIC = "Reflection Critic"  
    DEBATE_FACILITATOR = "Debate Facilitator"
    CORRECTION_MEMORY = "Correction Memory"
    STEP_VALIDATOR = "Step Validator"
    WAVE_FUNCTION = "Wave Function Planner"
    MULTI_AGENT_DEBATE = "Multi-Agent Debate"
    ROUTER_INTELLIGENCE = "Router Intelligence"
    DOCUMENT_ANALYZER = "Document Analyzer"
    CALENDAR_ASSISTANT = "Calendar Assistant"
    TASK_MANAGER = "Task Manager"
    EMAIL_ASSISTANT = "Email Assistant"
    SOCRATIC_GUIDE = "Socratic Guide"

class WorkerProgressManager:
    """
    Enhanced progress manager for smart AI capabilities.
    Handles sending progress updates from the worker to the API via Redis Pub/Sub.
    Supports token tracking, interactive pauses, and human context integration.
    """

    def __init__(self):
        self.redis_client = None
        self.sync_redis_client = None
        self.pubsub_channel = "chat_progress"
        self.context_channel = "human_context"  # New channel for human context

    async def initialize(self):
        """Initializes the Redis client."""
        if not self.redis_client:
            settings = get_settings()
            try:
                self.redis_client = Redis.from_url(str(settings.REDIS_URL), decode_responses=True)
                await self.redis_client.ping() # type: ignore
                logger.info("WorkerProgressManager initialized and connected to Redis.")
            except Exception as e:
                logger.error(f"Failed to initialize WorkerProgressManager Redis client: {e}", exc_info=True)
                self.redis_client = None
    
    def initialize_sync(self):
        """Initialize synchronous Redis client for Celery workers."""
        if not self.sync_redis_client:
            settings = get_settings()
            try:
                self.sync_redis_client = redis.from_url(str(settings.REDIS_URL), decode_responses=True)
                self.sync_redis_client.ping()
                logger.info("Synchronous Redis client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize synchronous Redis client: {e}")
                self.sync_redis_client = None

    async def broadcast_to_session_sync(self, session_id: str, message: dict):
        """
        Publishes a message to the Redis Pub/Sub channel, which will be picked up by the API.
        """
        if not self.redis_client:
            await self.initialize()
        
        if self.redis_client:
            try:
                payload = {
                    "session_id": session_id,
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                }
                await self.redis_client.publish(self.pubsub_channel, json.dumps(payload)) # type: ignore
            except Exception as e:
                logger.error(f"Failed to publish message to Redis for session {session_id}: {e}", exc_info=True)
    
    def broadcast_to_session_sync_sync(self, session_id: str, message: dict):
        """
        Synchronous version for Celery workers.
        Publishes a message to the Redis Pub/Sub channel.
        """
        if not self.sync_redis_client:
            self.initialize_sync()
        
        if self.sync_redis_client:
            try:
                payload = {
                    "session_id": session_id,
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                }
                self.sync_redis_client.publish(self.pubsub_channel, json.dumps(payload))
            except Exception as e:
                logger.error(f"Failed to publish message to Redis for session {session_id}: {e}", exc_info=True)

    # --- Enhanced Progress Update Methods ---

    async def broadcast_token_update(self, session_id: str, token_metrics: TokenMetrics, category: str = "general"):
        """Broadcast token usage updates."""
        message = {
            "type": "token_update",
            "category": category,
            "token_metrics": {
                "input_tokens": token_metrics.input_tokens,
                "output_tokens": token_metrics.output_tokens,
                "total_tokens": token_metrics.total_tokens,
                "tool_selection_tokens": token_metrics.tool_selection_tokens,
                "reflection_tokens": token_metrics.reflection_tokens,
                "confidence_tokens": token_metrics.confidence_tokens,
                "memory_retrieval_tokens": token_metrics.memory_retrieval_tokens,
                "human_context_tokens": token_metrics.human_context_tokens
            }
        }
        await self.broadcast_to_session_sync(session_id, message)

    async def broadcast_confidence_update(self, session_id: str, confidence_score: float, 
                                         confidence_level: ConfidenceLevel, reasoning: str = ""):
        """Broadcast confidence score updates."""
        message = {
            "type": "confidence_update",
            "confidence_score": confidence_score,
            "confidence_level": confidence_level.value,
            "reasoning": reasoning
        }
        await self.broadcast_to_session_sync(session_id, message)

    async def broadcast_pause_request(self, session_id: str, pause_reason: PauseReason, 
                                     pause_message: str, context_prompt: str = "", 
                                     timeout: int = 30):
        """Broadcast a pause request for human input."""
        message = {
            "type": "pause_request",
            "pause_reason": pause_reason.value,
            "pause_message": pause_message,
            "context_prompt": context_prompt,
            "timeout": timeout,
            "awaiting_input": True
        }
        await self.broadcast_to_session_sync(session_id, message)

    async def broadcast_pause_resolved(self, session_id: str, resolution: str, 
                                      human_context: Optional[HumanContextModel] = None):
        """Broadcast that a pause has been resolved."""
        message = {
            "type": "pause_resolved",
            "resolution": resolution,
            "human_context": human_context.model_dump() if human_context else None
        }
        await self.broadcast_to_session_sync(session_id, message)

    async def broadcast_task_status(self, session_id: str, task_status: TaskStatus, 
                                   details: str = "", progress: float = 0.0):
        """Broadcast task status updates."""
        message = {
            "type": "task_status",
            "task_status": task_status.value,
            "details": details,
            "progress": progress
        }
        await self.broadcast_to_session_sync(session_id, message)

    async def broadcast_plan_update(self, session_id: str, plan_step: int, total_steps: int, 
                                   current_step_desc: str, confidence: float = 0.0):
        """Broadcast plan execution updates."""
        message = {
            "type": "plan_update",
            "current_step": plan_step,
            "total_steps": total_steps,
            "step_description": current_step_desc,
            "confidence": confidence,
            "progress": (plan_step / total_steps) * 100 if total_steps > 0 else 0
        }
        await self.broadcast_to_session_sync(session_id, message)

    async def broadcast_reflection_start(self, session_id: str, reflection_type: str, 
                                        target_output: str = ""):
        """Broadcast start of reflection process."""
        message = {
            "type": "reflection_start",
            "reflection_type": reflection_type,
            "target_output": target_output
        }
        await self.broadcast_to_session_sync(session_id, message)

    async def broadcast_reflection_complete(self, session_id: str, critique: str, 
                                          retry_needed: bool, confidence_change: float = 0.0):
        """Broadcast completion of reflection process."""
        message = {
            "type": "reflection_complete",
            "critique": critique,
            "retry_needed": retry_needed,
            "confidence_change": confidence_change
        }
        await self.broadcast_to_session_sync(session_id, message)

    async def broadcast_memory_retrieval(self, session_id: str, memory_type: str, 
                                        results_count: int, relevance_score: float = 0.0):
        """Broadcast memory retrieval activities."""
        message = {
            "type": "memory_retrieval",
            "memory_type": memory_type,
            "results_count": results_count,
            "relevance_score": relevance_score
        }
        await self.broadcast_to_session_sync(session_id, message)

    async def broadcast_error_recovery(self, session_id: str, error_type: str, 
                                      recovery_action: str, success: bool = False):
        """Broadcast error recovery attempts."""
        message = {
            "type": "error_recovery",
            "error_type": error_type,
            "recovery_action": recovery_action,
            "success": success
        }
        await self.broadcast_to_session_sync(session_id, message)

    async def broadcast_human_context_received(self, session_id: str, context: HumanContextModel):
        """Broadcast that human context has been received."""
        message = {
            "type": "human_context_received",
            "context": context.model_dump()
        }
        await self.broadcast_to_session_sync(session_id, message)

    async def broadcast_adaptive_thinking(self, session_id: str, thinking_level: str, 
                                         reason: str, token_impact: int = 0):
        """Broadcast adaptive thinking level changes."""
        message = {
            "type": "adaptive_thinking",
            "thinking_level": thinking_level,
            "reason": reason,
            "token_impact": token_impact
        }
        await self.broadcast_to_session_sync(session_id, message)

    async def broadcast_agent_message(self, session_id: str, agent_name: str, content: str,
                                    agent_type: str = "background", metadata: Dict[str, Any] = None,
                                    formatted: bool = False):
        """Broadcast a direct message from an agent to the chat UI."""
        message = {
            "type": "agent_message",
            "id": f"agent_{datetime.utcnow().timestamp()}",
            "agent_name": agent_name,
            "agent_type": agent_type,
            "content": content,
            "text": content,  # Fallback for compatibility
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
            "formatted": formatted
        }
        await self.broadcast_to_session_sync(session_id, message)
        logger.info(f"Agent message broadcast from {agent_name} ({agent_type}): {content[:100]}...")

    def broadcast_agent_message_sync(self, session_id: str, agent_name: str, content: str,
                                   agent_type: str = "background", metadata: Dict[str, Any] = None,
                                   formatted: bool = False):
        """Sync version of broadcast_agent_message for use in Celery tasks."""
        message = {
            "type": "agent_message",
            "id": f"agent_{datetime.utcnow().timestamp()}",
            "agent_name": agent_name,
            "agent_type": agent_type,
            "content": content,
            "text": content,  # Fallback for compatibility
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
            "formatted": formatted
        }
        self.broadcast_to_session_sync_sync(session_id, message)
        logger.info(f"Agent message broadcast (sync) from {agent_name} ({agent_type}): {content[:100]}...")

    # Convenience methods for common agent messages
    async def post_mission_analysis(self, session_id: str, suggestions: list):
        """Post mission analysis results directly to chat."""
        if not suggestions:
            content = "🎯 Mission analysis complete. No specific suggestions available at this time."
        else:
            content = f"🎯 **Mission Analysis Complete**\n\nGenerated {len(suggestions)} personalized suggestions based on your mission and goals."
        
        await self.broadcast_agent_message(
            session_id, AgentNames.MISSION_ANALYZER, content, 
            "mission analysis", {"suggestions_count": len(suggestions)}
        )

    async def post_debate_results(self, session_id: str, decision: str, consensus: bool, agents: list):
        """Post multi-agent debate results directly to chat."""
        emoji = "🤝" if consensus else "🤔"
        status = "Consensus Reached" if consensus else "Analysis Complete"
        content = f"{emoji} **{status}**\n\n🎯 **Decision**: {decision}\n👥 **Agents**: {', '.join(agents)}"
        
        await self.broadcast_agent_message(
            session_id, AgentNames.MULTI_AGENT_DEBATE, content,
            "collaborative reasoning", {"consensus": consensus, "agents": agents}
        )

    async def post_test_agent_message(self, session_id: str):
        """Test method to demonstrate direct agent posting."""
        content = """🧪 **Test Agent Message**

This is a test of the new direct agent posting system! 

✅ **Features:**
• Named agents post directly to chat
• No Fast LLM bottleneck  
• Rich formatted content
• Real-time delivery via WebSocket

🚀 **Benefits:**
• Faster results
• Better user experience
• More detailed information
• Scalable architecture"""
        
        await self.broadcast_agent_message(
            session_id, "Test Agent", content,
            "system test", {"test": True}, formatted=True
        )

    async def broadcast_method_selected(self, session_id: str, method_name: str, 
                                       confidence_score: float, reasoning: str = "", 
                                       estimated_time: str = ""):
        """Broadcast which processing method was selected for transparency."""
        message = {
            "type": "method_selected",
            "method_name": method_name,
            "confidence_score": confidence_score,
            "reasoning": reasoning,
            "estimated_time": estimated_time,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_session_sync(session_id, message)

    async def broadcast_node_transition(self, session_id: str, node_name: str, 
                                       node_state: dict, execution_time: float = 0.0):
        """Broadcast LangGraph node transitions for automatic progress monitoring."""
        
        # Map node names to human-readable descriptions
        node_descriptions = {
            "concurrent_assessment": "Analyzing request and confidence",
            "executive_assessment": "Executive decision making",
            "confidence_assessment": "Assessing confidence levels",
            "force_planning": "Creating execution plan", 
            "route_to_tool": "Selecting appropriate tool",
            "tool_explanation": "Explaining selected approach",
            "execute_tool": "Executing tool",
            "after_tool_execution": "Processing results",
            "reflection_node": "Reflecting on output quality",
            "multi_agent_debate": "Collaborative analysis in progress",
            "wave_function_planning": "Advanced specialist analysis",
            "planner_node": "Finalizing execution plan",
            
            # Multi-Agent Debate Service nodes
            "debate_select_agents": "Selecting expert debate agents",
            "debate_gather_positions": "Gathering initial expert positions",
            "debate_conduct_round": "Conducting expert argumentation",
            "debate_synthesize_debate": "Synthesizing expert consensus",
            
            # Mission Suggestions Service nodes
            "suggestions_get_user_context": "Analyzing user mission and goals",
            "suggestions_get_opportunities": "Identifying current opportunities",
            "suggestions_get_calendar_analysis": "Analyzing calendar patterns",
            "suggestions_analyze_opportunities": "Generating mission-aligned suggestions",
            "suggestions_store_suggestions": "Storing suggestions in database",
            
            # Reflection Service nodes
            "reflection_gather_grounding": "Gathering external grounding data",
            "reflection_generate_structured_critique": "Generating persona-based critique",
            "reflection_generate_verification_questions": "Creating verification questions",
            "reflection_evaluate_criteria": "Evaluating against quality criteria",
            "reflection_create_critique_model": "Creating comprehensive critique model",
            
            # Correction Memory Service nodes
            "correction_analyze_patterns": "Analyzing failure patterns for learning",
            "correction_retrieve_warnings": "Retrieving relevant correction warnings",
            "correction_store_pattern": "Storing failure pattern in memory",
            
            # Step Oversight Service nodes
            "oversight_analyze_step_success": "Analyzing step execution success",
            "oversight_generate_improvements": "Generating improvement suggestions",
            "oversight_store_failure_memory": "Storing failure in correction memory",
            "oversight_compile_result": "Compiling validation results"
        }
        
        # Determine node status and progress
        node_description = node_descriptions.get(node_name, f"Processing {node_name}")
        
        # Extract useful state information
        confidence_score = node_state.get("confidence_score", 0.0)
        selected_tool = node_state.get("selected_tool")
        plan_step = node_state.get("plan_step", 0)
        total_steps = len(node_state.get("plan", [])) if node_state.get("plan") else 0
        
        # Calculate overall progress if we're in plan execution
        progress_percentage = 0.0
        if total_steps > 0 and plan_step is not None:
            progress_percentage = (plan_step / total_steps) * 100
        
        message = {
            "type": "node_transition",
            "node_name": node_name,
            "node_description": node_description,
            "execution_time": execution_time,
            "confidence_score": confidence_score,
            "selected_tool": selected_tool,
            "plan_progress": {
                "current_step": plan_step,
                "total_steps": total_steps,
                "percentage": progress_percentage
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add specific information based on node type
        if node_name == "multi_agent_debate":
            message["status"] = "Engaging collaborative reasoning for complex decision"
        elif node_name == "wave_function_planning":
            message["status"] = "Running advanced specialist analysis"
        elif node_name == "force_planning":
            planning_method = node_state.get("planning_method", "unknown")
            message["planning_method"] = planning_method
            message["status"] = f"Using {planning_method} planning approach"
        elif node_name == "execute_tool":
            message["status"] = f"Executing {selected_tool}" if selected_tool else "Executing tool"
        
        await self.broadcast_to_session_sync(session_id, message)

    async def broadcast_workflow_start(self, session_id: str, user_input: str):
        """Broadcast the start of a workflow execution."""
        message = {
            "type": "workflow_start",
            "user_input": user_input,
            "status": "Starting workflow execution",
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_session_sync(session_id, message)

    async def broadcast_workflow_complete(self, session_id: str, final_response: str, 
                                         total_execution_time: float = 0.0,
                                         nodes_executed: int = 0):
        """Broadcast the completion of a workflow execution."""
        message = {
            "type": "workflow_complete", 
            "final_response": final_response,
            "total_execution_time": total_execution_time,
            "nodes_executed": nodes_executed,
            "status": "Workflow execution complete",
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_session_sync(session_id, message)

    # --- Human Context Management ---

    async def listen_for_human_context(self, session_id: str, timeout: int = 30) -> Optional[HumanContextModel]:
        """Listen for human context input on the context channel."""
        if not self.redis_client:
            await self.initialize()
            
        if not self.redis_client:
            return None
            
        try:
            # Subscribe to the human context channel
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe(f"{self.context_channel}:{session_id}")
            
            # Wait for message or timeout
            try:
                message = await asyncio.wait_for(pubsub.get_message(), timeout=timeout)
                if message and message["type"] == "message":
                    context_data = json.loads(message["data"])
                    return HumanContextModel(**context_data)
            except asyncio.TimeoutError:
                logger.info(f"Timeout waiting for human context for session {session_id}")
                return None
            finally:
                await pubsub.unsubscribe(f"{self.context_channel}:{session_id}")
                
        except Exception as e:
            logger.error(f"Error listening for human context: {e}", exc_info=True)
            return None

    async def send_human_context(self, session_id: str, context: HumanContextModel):
        """Send human context to the worker via Redis."""
        if not self.redis_client:
            await self.initialize()
            
        if self.redis_client:
            try:
                await self.redis_client.publish(
                    f"{self.context_channel}:{session_id}", 
                    json.dumps(context.model_dump())
                )
            except Exception as e:
                logger.error(f"Failed to send human context for session {session_id}: {e}", exc_info=True)

    # --- Legacy compatibility methods ---

    async def broadcast_tool_selection(self, session_id: str, tool_id: str, confidence: float = 0.0):
        """Legacy method for tool selection updates."""
        message = {
            "type": "tool_selection",
            "content": f"Selected tool: {tool_id}",
            "tool_id": tool_id,
            "confidence": confidence
        }
        await self.broadcast_to_session_sync(session_id, message)

    async def broadcast_plan_generated(self, session_id: str, plan: list, confidence: float = 0.0):
        """Legacy method for plan generation updates."""
        message = {
            "type": "plan_generated",
            "content": "Plan generated.",
            "plan": plan,
            "confidence": confidence
        }
        await self.broadcast_to_session_sync(session_id, message)

# Singleton instance
progress_manager = WorkerProgressManager()

# It's good practice to initialize it when the worker starts.
# This can be done in the worker's startup logic.
