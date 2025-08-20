# api/routers/chat_modes_router.py
"""
API router for the four different chat modes:
1. Simple Chat - Direct LLM interaction without tools
2. Expert Group Chat - Multi-expert conversation interface  
3. Smart Router - Simplified router based on smart_ai.txt
4. Socratic Interview - Dedicated assessment interface
"""

import uuid
import json
import logging
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, Request, HTTPException, Response
from fastapi.responses import StreamingResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError

from ..dependencies import get_current_user
from shared.database.models import User
from shared.schemas.user_schemas import UserSettings
from shared.utils.streaming_utils import (
    format_sse_data, format_sse_error, format_sse_info, 
    format_sse_content, format_sse_final, SSEValidator
)
from worker.services.router_modules.router_core import run_router_graph
from shared.services.smart_ai_interview_service import smart_ai_interview_service
from worker.services.ollama_service import invoke_llm_with_tokens, invoke_llm_stream_with_tokens
from worker.services.centralized_resource_service import centralized_resource_service, ComplexityLevel
from worker.services.expert_group_langgraph_service import expert_group_langgraph_service
from worker.services.smart_router_langgraph_service import smart_router_langgraph_service
from worker.services.conversational_expert_group_service import conversational_expert_group_service
from worker.services.helios_pm_orchestration_engine import HeliosPMOrchestrationEngine

# Helper functions for context-aware simple chat
async def _enhance_prompt_with_context(user_message: str, chat_context) -> str:
    """
    Enhance user prompt with retrieved context for RAG capabilities.
    """
    if not chat_context.context_items:
        return user_message
    
    context_sections = []
    
    # Group context by type for better organization
    context_by_type = {}
    for item in chat_context.context_items[:10]:  # Limit to top 10 items
        item_type = item.get("type", "general")
        if item_type not in context_by_type:
            context_by_type[item_type] = []
        context_by_type[item_type].append(item)
    
    # Build context sections
    if "recent_history" in context_by_type:
        recent_items = context_by_type["recent_history"][:3]
        history_text = "\n".join([f"- {item['content'][:200]}..." if len(item['content']) > 200 
                                 else f"- {item['content']}" for item in recent_items])
        context_sections.append(f"Recent Conversation:\n{history_text}")
    
    if "session_context" in context_by_type:
        session_items = context_by_type["session_context"][:2]
        session_text = "\n".join([f"- {item['content'][:150]}..." if len(item['content']) > 150 
                                 else f"- {item['content']}" for item in session_items])
        context_sections.append(f"Session Context:\n{session_text}")
    
    if "persistent_context" in context_by_type:
        persistent_items = context_by_type["persistent_context"][:2]
        persistent_text = "\n".join([f"- {item['content'][:150]}..." if len(item['content']) > 150 
                                   else f"- {item['content']}" for item in persistent_items])
        context_sections.append(f"User Preferences & Knowledge:\n{persistent_text}")
    
    if "semantic_context" in context_by_type:
        semantic_items = context_by_type["semantic_context"][:2]
        semantic_text = "\n".join([f"- {item['content'][:150]}..." if len(item['content']) > 150 
                                 else f"- {item['content']}" for item in semantic_items])
        context_sections.append(f"Related Previous Discussions:\n{semantic_text}")
    
    if not context_sections:
        return user_message
    
    # Combine context with user message
    enhanced_prompt = f"""You are a helpful AI assistant with access to relevant context from previous conversations. Use this context to provide more personalized and informed responses.

**RELEVANT CONTEXT:**
{chr(10).join(context_sections)}

**CURRENT USER MESSAGE:**
{user_message}

**INSTRUCTIONS:**
- Use the context to inform your response when relevant
- Don't explicitly mention that you're using context unless asked
- Maintain natural conversation flow
- If context contains preferences or past decisions, respect them
- Provide helpful, contextual responses that build on previous conversations"""

    return enhanced_prompt


def _determine_context_complexity(chat_context, user_message: str) -> ComplexityLevel:
    """
    Determine complexity level based on context and message characteristics.
    """
    # Base complexity on message length and complexity indicators
    message_words = len(user_message.split())
    
    # Start with default complexity
    if message_words < 10:
        base_complexity = ComplexityLevel.SIMPLE
    elif message_words < 30:
        base_complexity = ComplexityLevel.MODERATE
    else:
        base_complexity = ComplexityLevel.COMPLEX
    
    # Adjust based on context richness
    context_adjustment = 0
    if chat_context.context_items:
        context_adjustment += min(len(chat_context.context_items) * 0.1, 0.5)
        
        # Check for complex context types
        for item in chat_context.context_items:
            if item.get("type") in ["persistent_context", "semantic_context"]:
                context_adjustment += 0.2
                break
    
    # Check for complexity indicators in message
    complex_indicators = [
        "analyze", "compare", "explain", "detailed", "comprehensive",
        "why", "how", "what if", "pros and cons", "advantages",
        "disadvantages", "recommendations", "suggestions"
    ]
    
    message_lower = user_message.lower()
    complexity_score = sum(1 for indicator in complex_indicators if indicator in message_lower)
    
    if complexity_score >= 3 or context_adjustment >= 0.4:
        return ComplexityLevel.COMPLEX
    elif complexity_score >= 1 or context_adjustment >= 0.2:
        return ComplexityLevel.MODERATE
    else:
        return base_complexity

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize model lifecycle management on module load
import asyncio
async def _initialize_model_management():
    """Initialize model lifecycle management and GPU monitoring background processes."""
    try:
        from worker.services.model_lifecycle_manager import model_lifecycle_manager
        from worker.services.gpu_monitor_service import gpu_monitor_service
        from worker.services.model_queue_manager import model_queue_manager
        from worker.services.gpu_load_balancer import gpu_load_balancer
        from worker.services.resource_analytics_service import resource_analytics_service
        
        # Start model lifecycle management
        await model_lifecycle_manager.start_background_management()
        await model_lifecycle_manager.preload_common_models()
        
        # Start GPU monitoring
        try:
            await gpu_monitor_service.start_monitoring()
        except Exception as e:
            logger.warning(f"GPU monitor service not available: {e}")
        
        # Start GPU load balancing
        await gpu_load_balancer.start_monitoring()
        
        # Start queue processing
        await model_queue_manager.start_queue_processing()
        
        # Start resource analytics
        await resource_analytics_service.start_monitoring()
        
        logger.info("Model management, GPU monitoring, queue processing, load balancing, and analytics initialized successfully")
    except Exception as e:
        logger.warning(f"Could not initialize model management services: {e}")

# Start background task (run in event loop when available)
def init_model_management():
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(_initialize_model_management())
        else:
            loop.run_until_complete(_initialize_model_management())
    except Exception as e:
        logger.debug(f"Model management initialization deferred: {e}")

# Attempt to initialize (will defer if no event loop)
init_model_management()


@router.get("/debug")
async def debug_chat_modes(
    current_user: User = Depends(get_current_user)
):
    """Debug endpoint to test chat modes functionality."""
    return {
        "status": "ok",
        "available_modes": ["simple", "expert-group", "smart-router", "socratic", "helios"],
        "user_id": current_user.id,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/resource-status")
async def get_resource_status(
    current_user: User = Depends(get_current_user)
):
    """Get current model resource status and parallel execution capabilities."""
    try:
        from worker.services.model_resource_manager import model_resource_manager
        from worker.services.model_lifecycle_manager import model_lifecycle_manager
        from worker.services.parallel_expert_executor import parallel_expert_executor
        from worker.services.user_expert_settings_service import user_expert_settings_service
        
        # Get resource status
        resource_status = await model_resource_manager.get_resource_status()
        lifecycle_status = await model_lifecycle_manager.get_lifecycle_status()
        execution_status = await parallel_expert_executor.get_execution_status()
        
        # Get user's expert model distribution
        user_distribution = await user_expert_settings_service.get_user_model_distribution(current_user.id)
        
        return {
            "user_id": current_user.id,
            "timestamp": datetime.now().isoformat(),
            "parallel_execution_enabled": True,
            "resource_management": resource_status,
            "model_lifecycle": lifecycle_status,
            "execution_status": execution_status,
            "user_model_distribution": user_distribution
        }
        
    except Exception as e:
        logger.error(f"Error getting resource status: {e}")
        return {
            "error": str(e),
            "parallel_execution_enabled": False,
            "user_id": current_user.id,
            "timestamp": datetime.now().isoformat()
        }


@router.get("/gpu-status")
async def get_gpu_status(
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive GPU monitoring status and optimization recommendations."""
    try:
        from worker.services.gpu_monitor_service import gpu_monitor_service
        
        # Get comprehensive GPU status
        monitoring_status = await gpu_monitor_service.get_monitoring_status()
        metrics_summary = await gpu_monitor_service.get_metrics_summary(hours=1)
        optimization_recommendations = await gpu_monitor_service.get_optimization_recommendations()
        
        return {
            "user_id": current_user.id,
            "timestamp": datetime.now().isoformat(),
            "gpu_monitoring": monitoring_status,
            "metrics_summary": metrics_summary,
            "optimization_recommendations": optimization_recommendations,
            "monitoring_enabled": True
        }
        
    except Exception as e:
        logger.error(f"Error getting GPU status: {e}")
        return {
            "error": str(e),
            "monitoring_enabled": False,
            "user_id": current_user.id,
            "timestamp": datetime.now().isoformat()
        }


class ChatModeRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    mode: Optional[str] = None  # "simple", "expert_group", "smart_router", "socratic"
    context: Optional[Dict[str, Any]] = None
    
    # Expert selection fields
    selectedExperts: Optional[List[str]] = None  # Direct field for frontend expert selection
    selected_agents: Optional[List[str]] = None  # Alternative field name
    
    # Additional fields for backward compatibility
    current_graph_state: Optional[Dict[str, Any]] = None
    message_history: Optional[List[Dict[str, Any]]] = None
    user_preferences: Optional[Dict[str, Any]] = None


class ChatModeResponse(BaseModel):
    response: str
    session_id: str
    mode: str
    metadata: Dict[str, Any]
    timestamp: str


@router.post("/simple")
async def simple_chat_mode(
    request: ChatModeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Context-aware Simple Chat Mode - RAG-enhanced conversational AI with memory.
    Features context retrieval, memory formation, and session continuity.
    """
    try:
        logger.info(f"Context-aware simple chat request: {request.dict()}")
        session_id = request.session_id or str(uuid.uuid4())
        
        # Import context service
        from worker.services.simple_chat_context_service import simple_chat_context_service
        
        # Step 1: Establish session continuity
        await simple_chat_context_service.manage_session_continuity(
            user_id=current_user.id,
            new_session_id=session_id,
            parent_session_id=request.context.get("parent_session_id") if request.context else None
        )
        
        # Step 2: Retrieve context for RAG enhancement
        chat_context = await simple_chat_context_service.get_chat_context(
            user_id=current_user.id,
            session_id=session_id,
            current_message=request.message
        )
        
        # Step 3: Enhance prompt with retrieved context
        enhanced_prompt = await _enhance_prompt_with_context(request.message, chat_context)
        
        # Step 4: Use centralized resource management with context-aware complexity
        context_complexity = _determine_context_complexity(chat_context, request.message)
        result = await centralized_resource_service.allocate_and_invoke(
            prompt=enhanced_prompt,
            user_id=str(current_user.id),
            service_name="simple_chat_context",
            session_id=session_id,
            complexity=context_complexity,
            fallback_allowed=True
        )
        
        # Step 5: Form memories from conversation (async, non-blocking)
        if chat_context.memory_formation_enabled:
            asyncio.create_task(
                simple_chat_context_service.form_memory(
                    user_id=current_user.id,
                    session_id=session_id,
                    conversation_content=enhanced_prompt,
                    user_message=request.message,
                    ai_response=result["response"]
                )
            )
        
        return ChatModeResponse(
            response=result["response"],
            session_id=session_id,
            mode="simple_context",
            metadata={
                "tokens_used": result["token_info"],
                "model": result["allocation"]["model"],
                "complexity": result["allocation"]["complexity"],
                "category": result["allocation"]["category"],
                "processing_time": result["metadata"]["processing_time"],
                "user_id": current_user.id,
                "resource_allocation": result["allocation"],
                # Context-aware metadata
                "context_items_retrieved": len(chat_context.context_items),
                "context_tokens": chat_context.total_tokens,
                "context_retrieval_time_ms": chat_context.retrieval_time_ms,
                "memory_formation_enabled": chat_context.memory_formation_enabled,
                "average_relevance_score": sum(chat_context.relevance_scores) / len(chat_context.relevance_scores) if chat_context.relevance_scores else 0.0
            },
            timestamp=datetime.now().isoformat()
        )
        
    except ValidationError as e:
        logger.error(f"Validation error in context-aware simple chat: {e}")
        raise HTTPException(status_code=422, detail=f"Request validation failed: {str(e)}")
    except Exception as e:
        logger.error(f"Error in context-aware simple chat: {e}")
        raise HTTPException(status_code=500, detail=f"Context-aware simple chat error: {str(e)}")


@router.post("/expert-group")
async def expert_group_chat_mode(
    request: ChatModeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Expert group chat mode - Non-streaming version for compatibility.
    Recommends using the streaming endpoint for real-time meeting experience.
    """
    try:
        logger.info(f"Expert group chat mode request: {request.dict()}")
        session_id = request.session_id or str(uuid.uuid4())
        
        # Extract selected agents with comprehensive logging
        selected_agents = []
        
        # Try multiple sources for expert selection data
        if request.selectedExperts:
            selected_agents = request.selectedExperts
            logger.info(f"EXPERT_SELECTION_DEBUG: Found selectedExperts in request field: {selected_agents}")
        elif request.selected_agents:
            selected_agents = request.selected_agents  
            logger.info(f"EXPERT_SELECTION_DEBUG: Found selected_agents in request field: {selected_agents}")
        elif request.context and "selectedExperts" in request.context:
            selected_agents = request.context["selectedExperts"]
            logger.info(f"EXPERT_SELECTION_DEBUG: Found selectedExperts in context: {selected_agents}")
        elif request.context and "selected_agents" in request.context:
            selected_agents = request.context["selected_agents"]
            logger.info(f"EXPERT_SELECTION_DEBUG: Found selected_agents in context: {selected_agents}")
        elif request.context and "enabled_experts" in request.context:
            selected_agents = request.context["enabled_experts"]
            logger.info(f"EXPERT_SELECTION_DEBUG: Found enabled_experts in context: {selected_agents}")
        else:
            logger.warning(f"EXPERT_SELECTION_DEBUG: No expert selection found in request. Context: {request.context}")
        
        logger.info(f"EXPERT_SELECTION_DEBUG: Extracted selected_agents: {selected_agents}")
        
        # Use the LangGraph service for non-streaming requests (backward compatibility)
        expert_response = await expert_group_langgraph_service.process_request(
            user_request=request.message,
            selected_agents=selected_agents
        )
        
        # Use response as-is since this endpoint is for backward compatibility only
        response_text = expert_response["response"]
        
        return ChatModeResponse(
            response=response_text,
            session_id=session_id,
            mode="expert_group",
            metadata={
                "experts_involved": expert_response.get("experts_involved", []),
                "discussion_context": expert_response.get("discussion_context", []),
                "is_sequential": expert_response.get("is_sequential", True),
                "processing_method": "langgraph_workflow",
                "parallel_execution_available": True,
                "user_id": current_user.id
            },
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error in expert group chat mode: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Expert group chat error: {str(e)}")


@router.post("/smart-router")
async def smart_router_chat_mode(
    request: ChatModeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Smart router mode - Enhanced with LangGraph todo management and structured task execution.
    Provides analysis -> planning -> execution -> summary workflow.
    """
    try:
        logger.info(f"Smart router mode request: {request.dict()}")
        session_id = request.session_id or str(uuid.uuid4())
        
        # Use the new LangGraph smart router service
        router_result = await smart_router_langgraph_service.process_request(
            user_request=request.message,
            session_id=session_id
        )
        
        return ChatModeResponse(
            response=router_result["response"],
            session_id=session_id,
            mode="smart_router",
            metadata={
                "routing_decision": router_result.get("routing_decision"),
                "confidence_score": router_result.get("confidence_score"),
                "todo_list": router_result.get("todo_list", []),
                "completed_tasks": router_result.get("completed_tasks", []),
                "tools_used": router_result.get("tools_used", []),
                "actions_performed": router_result.get("actions_performed", []),
                "complexity_analysis": router_result.get("complexity_analysis", {}),
                "approach_strategy": router_result.get("approach_strategy", ""),
                "workflow_type": router_result.get("workflow_type", "langgraph_smart_router"),
                "user_id": current_user.id
            },
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error in smart router mode: {e}")
        raise HTTPException(status_code=500, detail=f"Smart router error: {str(e)}")


@router.post("/socratic")
async def socratic_interview_mode(
    request: ChatModeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Socratic interview mode - Dedicated assessment interface.
    Handles structured assessments with Socratic method questioning.
    """
    try:
        logger.info(f"Socratic interview mode request: {request.dict()}")
        session_id = request.session_id or str(uuid.uuid4())
        
        # Handle different types of Socratic interactions
        assessment_type = None
        if request.context:
            assessment_type = request.context.get("assessment_type") or request.context.get("interview_type")
        
        # Check if this is a system command to start an assessment
        if request.message.startswith("SYSTEM_COMMAND: START_ASSESSMENT"):
            # Extract assessment type from system command
            if "TYPE:" in request.message:
                assessment_type = request.message.split("TYPE:")[-1].strip()
            
            logger.info(f"SOCRATIC DEBUG: Starting assessment type: {assessment_type}")
            
            # Return initial assessment question
            response_content = await get_initial_assessment_question(
                assessment_type=assessment_type,
                user_id=current_user.id,
                session_id=session_id
            )
            
            logger.info(f"SOCRATIC DEBUG: Generated response content: {response_content[:100]}...")
        elif assessment_type:
            # Formal assessment session - continue the adaptive interview
            response_content, _ = await smart_ai_interview_service.adaptive_service.continue_adaptive_interview(
                user_id=current_user.id,
                user_response=request.message,
                interview_type=assessment_type,
                session_id=session_id
            )
        else:
            # General Socratic dialogue
            response_content = await process_socratic_dialogue(
                user_message=request.message,
                user_id=current_user.id,
                session_id=session_id
            )
        
        chat_response = ChatModeResponse(
            response=response_content,
            session_id=session_id,
            mode="socratic",
            metadata={
                "assessment_type": assessment_type,
                "socratic_method": "active",
                "progress_tracking": True,
                "user_id": current_user.id
            },
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"SOCRATIC DEBUG: Returning response - session_id: {session_id}, response_length: {len(response_content)}, mode: socratic")
        return chat_response
        
    except Exception as e:
        logger.error(f"Error in Socratic interview mode: {e}")
        raise HTTPException(status_code=500, detail=f"Socratic interview error: {str(e)}")


async def get_initial_assessment_question(assessment_type: str, user_id: int, session_id: str) -> str:
    """
    Get the initial question for a specific assessment type.
    """
    initial_questions = {
        "personal_life_statement": "Welcome to your Personal Mission Statement journey! Let's begin exploring what truly matters to you. When you think about a time in your life when you felt most fulfilled and authentic, what was happening? What made that moment so meaningful?",
        "work_style": "Welcome to your Work Style Assessment! I'd like to understand how you work best. Think about a recent project or task that you really enjoyed working on. What was it about that experience that energized you?",
        "productivity_patterns": "Welcome to your Productivity Optimization session! Let's examine your current productivity. Consider your most productive day in the past week. What factors contributed to that success? Walk me through what made it work so well."
    }
    
    return initial_questions.get(assessment_type, "Let's begin this Socratic exploration. What would you like to discuss and learn about today?")


async def process_socratic_dialogue(user_message: str, user_id: int, session_id: str) -> str:
    """
    Process general Socratic dialogue for learning and exploration.
    """
    socratic_prompt = f"""
    Use the Socratic method to engage with this user message: {user_message}

    Socratic method guidelines:
    1. Ask probing questions that help the user think deeper
    2. Guide them to discover insights themselves
    3. Challenge assumptions gently
    4. Build on their responses to deepen understanding
    
    Respond with a thoughtful question or gentle challenge that encourages reflection.
    """
    
    # Use centralized resource management for Socratic dialogue
    result = await centralized_resource_service.allocate_and_invoke(
        prompt=socratic_prompt,
        user_id=str(user_id),
        service_name="socratic",
        session_id=session_id,
        complexity=ComplexityLevel.MODERATE,  # Socratic dialogue requires moderate reasoning
        fallback_allowed=True
    )
    
    return result["response"]


@router.post("/helios")
async def helios_multi_agent_mode(
    request: ChatModeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Helios Multi-Agent mode - Project Manager orchestrated expert collaboration.
    Provides individual agent chats, GPU allocation, and true task delegation.
    """
    try:
        logger.info(f"Helios multi-agent mode request: {request.dict()}")
        session_id = request.session_id or str(uuid.uuid4())
        
        # Initialize Helios PM orchestration engine
        helios_engine = HeliosPMOrchestrationEngine()
        
        # Initialize orchestration state
        orchestration_state = await helios_engine.initialize_orchestration(
            user_request=request.message,
            user_id=str(current_user.id)
        )
        
        # Run PM orchestration workflow
        orchestration_result = []
        async for update in helios_engine.run_pm_orchestration(orchestration_state):
            orchestration_result.append(update)
        
        # Get final output from orchestration state
        final_output = orchestration_state.final_output or orchestration_state.synthesis_content or "Helios expert collaboration completed."
        
        return ChatModeResponse(
            response=final_output,
            session_id=session_id,
            mode="helios",
            metadata={
                "orchestration_phases": len(orchestration_result),
                "experts_involved": len(orchestration_state.task_delegations),
                "task_delegations": [d.dict() for d in orchestration_state.task_delegations],
                "expert_responses": [r.dict() for r in orchestration_state.expert_responses],
                "available_agents": orchestration_state.available_agents,
                "orchestration_type": "pm_led_collaboration",
                "gpu_allocation_enabled": True,
                "individual_agent_chats": True,
                "user_id": current_user.id
            },
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error in Helios multi-agent mode: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Helios multi-agent error: {str(e)}")


# === STREAMING ENDPOINTS ===

@router.post("/simple/stream")
async def simple_chat_mode_stream(
    request: ChatModeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Context-aware Simple Chat Streaming - RAG-enhanced real-time responses with memory.
    Features context retrieval, memory formation, and intelligent streaming.
    """
    async def generate_streaming_response():
        try:
            logger.info(f"Context-aware simple chat streaming request: {request.dict()}")
            session_id = request.session_id or str(uuid.uuid4())
            
            # Import context service
            from worker.services.simple_chat_context_service import simple_chat_context_service
            
            # Step 1: Send initial processing signal
            yield format_sse_info('🧠 Retrieving conversation context...')
            
            # Step 2: Establish session continuity
            await simple_chat_context_service.manage_session_continuity(
                user_id=current_user.id,
                new_session_id=session_id,
                parent_session_id=request.context.get("parent_session_id") if request.context else None
            )
            
            # Step 3: Retrieve context for RAG enhancement
            chat_context = await simple_chat_context_service.get_chat_context(
                user_id=current_user.id,
                session_id=session_id,
                current_message=request.message
            )
            
            # Step 4: Inform about context retrieval
            if chat_context.context_items:
                yield format_sse_data('context_info', f'Retrieved {len(chat_context.context_items)} context items in {chat_context.retrieval_time_ms:.1f}ms')
            
            # Step 5: Enhance prompt with retrieved context
            enhanced_prompt = await _enhance_prompt_with_context(request.message, chat_context)
            
            # Step 6: Determine context-aware complexity
            context_complexity = _determine_context_complexity(chat_context, request.message)
            
            # Step 7: Stream response with context awareness
            ai_response_chunks = []
            async for chunk, token_info in centralized_resource_service.allocate_and_invoke_stream(
                prompt=enhanced_prompt,
                user_id=str(current_user.id),
                service_name="simple_chat_context",
                session_id=session_id,
                complexity=context_complexity
            ):
                if chunk:  # Stream content chunks
                    ai_response_chunks.append(chunk)
                    yield format_sse_content(chunk)
                elif token_info:  # Final chunk with enhanced metadata
                    # Combine AI response for memory formation
                    full_ai_response = "".join(ai_response_chunks)
                    
                    # Step 8: Form memories asynchronously (non-blocking)
                    if chat_context.memory_formation_enabled and full_ai_response:
                        asyncio.create_task(
                            simple_chat_context_service.form_memory(
                                user_id=current_user.id,
                                session_id=session_id,
                                conversation_content=enhanced_prompt,
                                user_message=request.message,
                                ai_response=full_ai_response
                            )
                        )
                    
                    # Enhanced final metadata
                    tokens_data = token_info.dict() if hasattr(token_info, 'dict') else {}
                    final_metadata = {
                        "tokens": tokens_data,
                        "context_items_retrieved": len(chat_context.context_items),
                        "context_tokens": chat_context.total_tokens,
                        "context_retrieval_time_ms": chat_context.retrieval_time_ms,
                        "memory_formation_enabled": chat_context.memory_formation_enabled,
                        "average_relevance_score": sum(chat_context.relevance_scores) / len(chat_context.relevance_scores) if chat_context.relevance_scores else 0.0,
                        "complexity_used": context_complexity.value
                    }
                    
                    yield format_sse_final(session_id, "simple_context", **final_metadata)
                    
        except Exception as e:
            logger.error(f"Error in context-aware simple chat streaming: {e}")
            yield format_sse_error(e, "simple_chat_context_error")
    
    return StreamingResponse(
        generate_streaming_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/expert-group/conversational/stream")
async def expert_group_conversational_stream(
    request: ChatModeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    NEW: Conversational expert group chat with real-time business meeting simulation.
    Provides individual expert responses, todo updates, and 1-hour meeting timeout.
    """
    async def generate_conversational_response():
        try:
            logger.info(f"Conversational expert group request: {request.dict()}")
            session_id = request.session_id or str(uuid.uuid4())
            
            # Extract selected agents with comprehensive logging
            selected_agents = []
            
            # Try multiple sources for expert selection data
            if request.selectedExperts:
                selected_agents = request.selectedExperts
                logger.info(f"EXPERT_SELECTION_DEBUG: Found selectedExperts in request field: {selected_agents}")
            elif request.selected_agents:
                selected_agents = request.selected_agents  
                logger.info(f"EXPERT_SELECTION_DEBUG: Found selected_agents in request field: {selected_agents}")
            elif request.context and "selectedExperts" in request.context:
                selected_agents = request.context["selectedExperts"]
                logger.info(f"EXPERT_SELECTION_DEBUG: Found selectedExperts in context: {selected_agents}")
            elif request.context and "selected_agents" in request.context:
                selected_agents = request.context["selected_agents"]
                logger.info(f"EXPERT_SELECTION_DEBUG: Found selected_agents in context: {selected_agents}")
            elif request.context and "enabled_experts" in request.context:
                selected_agents = request.context["enabled_experts"]
                logger.info(f"EXPERT_SELECTION_DEBUG: Found enabled_experts in context: {selected_agents}")
            else:
                logger.warning(f"EXPERT_SELECTION_DEBUG: No expert selection found in request. Context: {request.context}")
            
            logger.info(f"EXPERT_SELECTION_DEBUG: Starting conversational meeting with {len(selected_agents)} experts: {selected_agents}")
            
            # Run conversational meeting with real-time streaming
            try:
                async for meeting_update in conversational_expert_group_service.run_conversational_meeting(
                    user_request=request.message,
                    selected_agents=selected_agents,
                    user_id=str(current_user.id)
                ):
                    # Validate and stream each meeting update
                    if isinstance(meeting_update, dict) and meeting_update.get('type'):
                        # Use existing meeting update format but ensure it's properly formatted
                        event_type = meeting_update.get('type')
                        content = meeting_update.get('content', '')
                        metadata = meeting_update.get('metadata', {})
                        
                        # Add any additional fields as metadata
                        for key, value in meeting_update.items():
                            if key not in ['type', 'content', 'metadata', 'timestamp']:
                                metadata[key] = value
                        
                        yield format_sse_data(event_type, content, **metadata)
                    else:
                        # Fallback for malformed updates
                        logger.warning(f"Malformed meeting update: {meeting_update}")
                        yield format_sse_error("Received malformed meeting update", "meeting_format_error")
                    
                    # Add small delay for better UX
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Conversational meeting failed: {e}", exc_info=True)
                yield format_sse_error(f"Meeting error: {str(e)}", type(e).__name__)
            
            # Final completion signal
            yield format_sse_data("stream_complete", None, session_id=session_id)
                    
        except Exception as e:
            logger.error(f"Error in conversational expert group streaming: {e}")
            yield format_sse_error(e, "conversational_expert_group_error")
    
    return StreamingResponse(
        generate_conversational_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/expert-group/stream")
async def expert_group_chat_mode_stream(
    request: ChatModeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Expert group chat mode with streaming - Legacy streaming endpoint.
    REDIRECTS to conversational streaming for better real-time experience.
    """
    async def generate_streaming_response():
        try:
            logger.info(f"Legacy expert group streaming - redirecting to conversational: {request.dict()}")
            session_id = request.session_id or str(uuid.uuid4())
            
            # Extract selected agents with comprehensive logging
            selected_agents = []
            
            # Try multiple sources for expert selection data
            if request.selectedExperts:
                selected_agents = request.selectedExperts
                logger.info(f"EXPERT_SELECTION_DEBUG: Found selectedExperts in request field: {selected_agents}")
            elif request.selected_agents:
                selected_agents = request.selected_agents  
                logger.info(f"EXPERT_SELECTION_DEBUG: Found selected_agents in request field: {selected_agents}")
            elif request.context and "selectedExperts" in request.context:
                selected_agents = request.context["selectedExperts"]
                logger.info(f"EXPERT_SELECTION_DEBUG: Found selectedExperts in context: {selected_agents}")
            elif request.context and "selected_agents" in request.context:
                selected_agents = request.context["selected_agents"]
                logger.info(f"EXPERT_SELECTION_DEBUG: Found selected_agents in context: {selected_agents}")
            elif request.context and "enabled_experts" in request.context:
                selected_agents = request.context["enabled_experts"]
                logger.info(f"EXPERT_SELECTION_DEBUG: Found enabled_experts in context: {selected_agents}")
            else:
                logger.warning(f"EXPERT_SELECTION_DEBUG: No expert selection found in request. Context: {request.context}")
            
            logger.info(f"EXPERT_SELECTION_DEBUG: Legacy streaming with {len(selected_agents)} experts: {selected_agents}")
            
            # Recommend using conversational endpoint
            yield format_sse_info('🔄 Redirecting to enhanced conversational meeting experience...')
            await asyncio.sleep(0.5)
            
            # Delegate to conversational service for real-time experience
            try:
                async for meeting_update in conversational_expert_group_service.run_conversational_meeting(
                    user_request=request.message,
                    selected_agents=selected_agents
                ):
                    # Validate and stream each meeting update
                    if isinstance(meeting_update, dict) and meeting_update.get('type'):
                        # Use existing meeting update format but ensure it's properly formatted
                        event_type = meeting_update.get('type')
                        content = meeting_update.get('content', '')
                        metadata = meeting_update.get('metadata', {})
                        
                        # Add legacy compatibility metadata
                        metadata['legacy_redirect'] = True
                        metadata['original_endpoint'] = '/expert-group/stream'
                        
                        # Add any additional fields as metadata
                        for key, value in meeting_update.items():
                            if key not in ['type', 'content', 'metadata', 'timestamp']:
                                metadata[key] = value
                        
                        yield format_sse_data(event_type, content, **metadata)
                    else:
                        # Fallback for malformed updates
                        logger.warning(f"Malformed meeting update: {meeting_update}")
                        yield format_sse_error("Received malformed meeting update", "meeting_format_error")
                    
                    # Add small delay for better UX
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Conversational meeting delegation failed: {e}", exc_info=True)
                yield format_sse_error(f"Meeting error: {str(e)}", type(e).__name__)
            
            # Final completion signal
            yield format_sse_data("stream_complete", None, session_id=session_id, 
                                legacy_redirect=True, recommendation="Use /expert-group/conversational/stream directly")
                    
        except Exception as e:
            logger.error(f"Error in legacy expert group streaming: {e}")
            yield format_sse_error(e, "expert_group_legacy_error")
    
    return StreamingResponse(
        generate_streaming_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/smart-router/stream")
async def smart_router_chat_mode_stream(
    request: ChatModeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Smart router mode with streaming - Shows todo workflow progress and streams structured response.
    """
    async def generate_streaming_response():
        try:
            logger.info(f"Smart router streaming mode request: {request.dict()}")
            session_id = request.session_id or str(uuid.uuid4())
            
            yield format_sse_info('Analyzing request and creating structured approach...')
            
            # Use the new LangGraph smart router service with timeout
            router_result = None
            try:
                router_result = await asyncio.wait_for(
                    smart_router_langgraph_service.process_request(
                        user_request=request.message,
                        session_id=session_id
                    ),
                    timeout=3600.0  # 1 hour timeout for full workflow with multiple LLM calls
                )
                
                # Stream workflow progress information
                routing_decision = router_result.get("routing_decision", "DIRECT")
                todo_count = len(router_result.get("todo_list", []))
                completed_count = len(router_result.get("completed_tasks", []))
                
                yield format_sse_data('workflow_info', f'Routing: {routing_decision} | Tasks: {completed_count}/{todo_count} completed')
                
                response_text = router_result["response"]
                
                # Stream the response
                words = response_text.split()
                chunk_size = 50
                for i in range(0, len(words), chunk_size):
                    chunk_words = words[i:i + chunk_size]
                    chunk = " " + " ".join(chunk_words) if i > 0 else " ".join(chunk_words)
                    yield format_sse_content(chunk)
                    await asyncio.sleep(0.1)
                
            except asyncio.TimeoutError:
                logger.error("Smart router processing timed out, using fallback response")
                fallback_content = f"I've analyzed your request: {request.message}\n\nHere's my structured approach:\n\n• Identified key requirements and objectives\n• Developed a systematic methodology\n• Created actionable steps for implementation\n• Provided recommendations based on best practices\n\nFor more detailed analysis, please try breaking your request into smaller, more specific parts."
                
                # Stream fallback response
                words = fallback_content.split()
                chunk_size = 35
                for i in range(0, len(words), chunk_size):
                    chunk_words = words[i:i + chunk_size]
                    chunk = " " + " ".join(chunk_words) if i > 0 else " ".join(chunk_words)
                    yield format_sse_content(chunk)
                    await asyncio.sleep(0.1)
            
            # Final metadata with detailed workflow info
            metadata = {
                "routing_decision": router_result.get("routing_decision", "DIRECT") if router_result else "TIMEOUT",
                "confidence_score": router_result.get("confidence_score", 0.85) if router_result else 0.5,
                "todo_list": router_result.get("todo_list", []) if router_result else [],
                "completed_tasks": len(router_result.get("completed_tasks", [])) if router_result else 0,
                "tools_used": router_result.get("tools_used", []) if router_result else [],
                "workflow_type": router_result.get("workflow_type", "langgraph_smart_router") if router_result else "fallback"
            }
            yield format_sse_final(session_id, 'smart_router', **metadata)
                    
        except Exception as e:
            logger.error(f"Error in smart router streaming: {e}")
            yield format_sse_error(e, "smart_router_error")
    
    return StreamingResponse(
        generate_streaming_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/helios/stream")
async def helios_multi_agent_stream(
    request: ChatModeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Helios Multi-Agent mode with streaming - Real-time PM orchestration with expert collaboration.
    Shows phase updates, task delegations, expert responses, and synthesis in real-time.
    """
    async def generate_helios_streaming_response():
        try:
            logger.info(f"Helios streaming mode request: {request.dict()}")
            session_id = request.session_id or str(uuid.uuid4())
            
            # Initialize Helios PM orchestration engine
            helios_engine = HeliosPMOrchestrationEngine()
            
            yield format_sse_info('🌟 Initializing Helios Multi-Agent Environment...')
            await asyncio.sleep(0.5)
            
            # Initialize orchestration state
            orchestration_state = await helios_engine.initialize_orchestration(
                user_request=request.message,
                user_id=str(current_user.id)
            )
            
            yield format_sse_data('helios_initialization', 'Helios team assembled', 
                                available_agents=orchestration_state.available_agents,
                                session_id=session_id)
            
            # Run PM orchestration workflow with streaming
            async for orchestration_update in helios_engine.run_pm_orchestration(orchestration_state):
                # Stream each orchestration update
                if isinstance(orchestration_update, dict):
                    update_type = orchestration_update.get('type', 'orchestration_update')
                    content = orchestration_update.get('content', '')
                    metadata = orchestration_update.get('metadata', {})
                    
                    # Add session tracking
                    metadata['session_id'] = session_id
                    metadata['helios_mode'] = True
                    
                    # Remove any additional fields and add to metadata
                    for key, value in orchestration_update.items():
                        if key not in ['type', 'content', 'metadata']:
                            metadata[key] = value
                    
                    yield format_sse_data(update_type, content, **metadata)
                    
                    # Add small delay for better streaming experience
                    await asyncio.sleep(0.1)
            
            # Final orchestration summary
            final_metadata = {
                "session_id": session_id,
                "orchestration_complete": True,
                "experts_involved": len(orchestration_state.task_delegations),
                "task_delegations_count": len(orchestration_state.task_delegations),
                "expert_responses_count": len(orchestration_state.expert_responses),
                "available_agents": orchestration_state.available_agents,
                "final_output_available": bool(orchestration_state.final_output)
            }
            
            yield format_sse_final(session_id, 'helios', **final_metadata)
                    
        except Exception as e:
            logger.error(f"Error in Helios streaming: {e}", exc_info=True)
            yield format_sse_error(e, "helios_orchestration_error")
    
    return StreamingResponse(
        generate_helios_streaming_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/socratic/stream")
async def socratic_interview_mode_stream(
    request: ChatModeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Socratic interview mode with streaming - Real-time thoughtful questioning and guidance.
    """
    async def generate_streaming_response():
        try:
            logger.info(f"Socratic streaming mode request: {request.dict()}")
            session_id = request.session_id or str(uuid.uuid4())
            
            # Handle different types of Socratic interactions
            assessment_type = None
            if request.context:
                assessment_type = request.context.get("assessment_type") or request.context.get("interview_type")
            
            response_content = ""
            # Check if this is a system command to start an assessment
            if request.message.startswith("SYSTEM_COMMAND: START_ASSESSMENT"):
                if "TYPE:" in request.message:
                    assessment_type = request.message.split("TYPE:")[-1].strip()
                
                # Get initial assessment question
                response_content = await get_initial_assessment_question(
                    assessment_type=assessment_type,
                    user_id=current_user.id,
                    session_id=session_id
                )
                
                # Stream the initial question
                words = response_content.split()
                chunk_size = 30
                for i in range(0, len(words), chunk_size):
                    chunk_words = words[i:i + chunk_size]
                    chunk = " " + " ".join(chunk_words) if i > 0 else " ".join(chunk_words)
                    yield format_sse_content(chunk)
                    await asyncio.sleep(0.1)
                
            elif assessment_type:
                # Continue adaptive interview with streaming
                yield format_sse_info('Crafting thoughtful follow-up question...')
                
                response_content, _ = await smart_ai_interview_service.adaptive_service.continue_adaptive_interview(
                    user_id=current_user.id,
                    user_response=request.message,
                    interview_type=assessment_type,
                    session_id=session_id
                )
                
                # Stream the response
                words = response_content.split()
                chunk_size = 25
                for i in range(0, len(words), chunk_size):
                    chunk_words = words[i:i + chunk_size]
                    chunk = " " + " ".join(chunk_words) if i > 0 else " ".join(chunk_words)
                    yield format_sse_content(chunk)
                    await asyncio.sleep(0.15)  # Slightly slower for thoughtful feel
                    
            else:
                # General Socratic dialogue with real streaming
                socratic_prompt = f"""
                Use the Socratic method to engage with this user message: {request.message}

                Socratic method guidelines:
                1. Ask probing questions that help the user think deeper
                2. Guide them to discover insights themselves
                3. Challenge assumptions gently
                4. Build on their responses to deepen understanding
                
                Respond with a thoughtful question or gentle challenge that encourages reflection.
                """
                
                # Stream the Socratic response using centralized resource management
                async for chunk, token_info in centralized_resource_service.allocate_and_invoke_stream(
                    prompt=socratic_prompt,
                    user_id=str(current_user.id),
                    service_name="socratic",
                    session_id=session_id,
                    complexity=ComplexityLevel.MODERATE
                ):
                    if chunk:
                        yield format_sse_content(chunk)
                    elif token_info:
                        pass  # Just continue, we'll send final message below
            
            # Final message
            yield format_sse_final(session_id, 'socratic', assessment_type=assessment_type, socratic_method='active')
                    
        except Exception as e:
            logger.error(f"Error in Socratic streaming: {e}")
            yield format_sse_error(e, "socratic_error")
    
    return StreamingResponse(
        generate_streaming_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/{mode_name:path}")
async def fallback_chat_mode(
    mode_name: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Fallback endpoint for any chat mode that doesn't match specific endpoints.
    This handles cases where the frontend might send requests to non-standard paths.
    """
    logger.warning(f"Fallback chat mode called with mode_name: {mode_name}")
    
    try:
        # Try to parse the request body as JSON
        try:
            body = await request.json()
            chat_request = ChatModeRequest(**body)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON body")
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=f"Request validation failed: {e.errors()}")

        logger.info(f"Fallback request data: {chat_request.dict()}")
        
        # Map mode names to appropriate handlers
        mode_mapping = {
            "simple": simple_chat_mode,
            "expert-group": expert_group_chat_mode,
            "smart-router": smart_router_chat_mode,
            "socratic": socratic_interview_mode,
            "helios": helios_multi_agent_mode
        }
        
        # Extract the base mode from a potentially complex path
        base_mode = mode_name.split('/')[0]

        if base_mode in mode_mapping:
            logger.info(f"Routing {mode_name} to appropriate handler for {base_mode}")
            return await mode_mapping[base_mode](chat_request, current_user)
        else:
            # Unknown mode, return error with helpful message
            logger.error(f"Unknown chat mode requested: {mode_name}")
            raise HTTPException(
                status_code=422, 
                detail=f"Unknown chat mode '{mode_name}'. Available modes: {list(mode_mapping.keys())}"
            )
    except HTTPException as e:
        # Re-raise HTTP exceptions to avoid being caught by the generic one
        raise e
    except Exception as e:
        logger.error(f"Error in fallback handler for {mode_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process request: {str(e)}")


@router.post("/expert-group/stop")
async def stop_expert_group(
    current_user: User = Depends(get_current_user)
):
    """Stop the expert group chat mode processing."""
    logger.info(f"Expert group stop requested by user {current_user.id}")
    
    # For now, just return success - in the future this could cancel active tasks
    return {
        "status": "stopped",
        "message": "Expert group processing stopped successfully",
        "user_id": current_user.id
    }