#!/usr/bin/env python3
"""
Enhanced Router Core with Dynamic Node Support

This module extends the existing router core to support dynamic node creation
and smart multi-step processing using LangGraph's dynamic capabilities.
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any, Union, Tuple
from datetime import datetime

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableLambda

# Conditional import for ChatOllama
try:
    from langchain_ollama.chat_models import ChatOllama
    HAS_LANGCHAIN_OLLAMA = True
except ImportError:
    ChatOllama = None
    HAS_LANGCHAIN_OLLAMA = False
    logging.warning("langchain_ollama not available, using basic responses")

from worker.graph_types import GraphState
from worker.tool_handlers import get_tool_handler
from shared.utils.config import get_settings
from worker.services.progress_manager import progress_manager
from worker.services.ollama_service import invoke_llm_with_tokens
from worker.services.router_modules.dynamic_node_manager import dynamic_node_manager

logger = logging.getLogger(__name__)
settings = get_settings()

def get_node_specific_model(state: GraphState, node_type: str) -> str:
    """
    Model selection for enhanced router with dynamic node support.
    """
    model_mappings = {
        "executive_assessment": state.chat_model or "llama3.2:3b",
        "tool_routing": state.tool_routing_model or "llama3.2:3b", 
        "simple_planning": state.simple_planning_model or "llama3.2:3b",
        "reflection": state.reflection_model or "llama3.2:3b",
        "final_response": state.final_response_model or "llama3.2:3b",
        "dynamic_analysis": state.tool_selection_model or "llama3.2:3b",
        "complexity_assessment": state.initial_assessment_model or "llama3.2:3b"
    }
    
    return model_mappings.get(node_type, state.chat_model or "llama3.2:3b")

async def run_enhanced_router_graph(
    user_input: str,
    messages: List[BaseMessage],
    user_id: int,
    session_id: str,
    chat_model: Optional[str] = None,
    enable_dynamic_nodes: bool = True,
    **kwargs
) -> Dict[str, Any]:
    """
    Enhanced main entry point for the router graph with dynamic node support.
    
    Args:
        user_input: The user's input message
        messages: Previous conversation messages
        user_id: User identifier
        session_id: Session identifier
        chat_model: Optional model override
        enable_dynamic_nodes: Whether to enable dynamic node creation
        **kwargs: Additional state parameters
    """
    try:
        # Initialize enhanced state
        initial_state = GraphState(
            messages=messages,
            user_input=user_input,
            user_id=str(user_id),
            session_id=session_id,
            chat_model=chat_model or "llama3.2:3b",
            final_response="",
            conversation_summary="",
            routing_decision="DIRECT",
            confidence_score=0.8,
            enable_dynamic_processing=enable_dynamic_nodes,
            use_dynamic_processing=False,  # Will be set by analysis
            memory_context=kwargs.get('memory_context', {}),  # Include memory context
            **{k: v for k, v in kwargs.items() if k != 'memory_context'}  # Exclude memory_context from kwargs to avoid duplication
        )
        
        # Analyze if dynamic processing is needed
        if enable_dynamic_nodes:
            needs_dynamic, processing_plan = await dynamic_node_manager.analyze_and_create_plan(initial_state)
            
            if needs_dynamic and processing_plan:
                logger.info(f"Using dynamic processing with plan: {processing_plan.plan_id}")
                initial_state.use_dynamic_processing = True
                initial_state.processing_plan = processing_plan
                
                # Create dynamic workflow
                base_workflow = create_enhanced_workflow()
                workflow = await dynamic_node_manager.create_dynamic_workflow(base_workflow, processing_plan)
            else:
                logger.info("Using standard workflow")
                workflow = create_enhanced_workflow()
        else:
            logger.info("Dynamic processing disabled, using standard workflow")
            workflow = create_enhanced_workflow()
        
        # Compile and run
        app = workflow.compile()
        result = await app.ainvoke(initial_state)
        
        # Ensure final_response is always a string
        final_response = result.get("final_response", "")
        if isinstance(final_response, dict):
            final_response = final_response.get("response", str(final_response))
        elif not isinstance(final_response, str):
            final_response = str(final_response)
        
        # Collect dynamic processing metadata
        dynamic_metadata = {}
        if hasattr(result, 'dynamic_plan_id'):
            dynamic_metadata = {
                "dynamic_processing_used": True,
                "plan_id": result.dynamic_plan_id,
                "dynamic_steps": len(getattr(result, 'dynamic_results', [])),
                "processing_type": "dynamic_multi_step"
            }
        
        return {
            "response": final_response,
            "routing_decision": result.get("routing_decision", "DIRECT"),
            "confidence_score": result.get("confidence_score", 0.8),
            "metadata": {
                "user_id": user_id,
                "model_used": result.get("chat_model", chat_model),
                "timestamp": datetime.now().isoformat(),
                **dynamic_metadata
            }
        }
        
    except Exception as e:
        logger.error(f"Error in enhanced router graph: {e}", exc_info=True)
        return {
            "response": f"I encountered an error processing your request: {str(e)}",
            "routing_decision": "ERROR",
            "confidence_score": 0.0,
            "metadata": {"error": str(e)}
        }

def create_enhanced_workflow() -> StateGraph:
    """
    Create enhanced workflow that supports dynamic node routing.
    """
    workflow = StateGraph(GraphState)
    
    # Import existing nodes
    from .assessment_nodes import enhanced_executive_assessment_node
    from .execution_nodes import execute_tool_node, tool_explanation_node
    from .planning_nodes import simple_planner_node
    
    # Add enhanced assessment that can detect dynamic needs
    workflow.add_node("executive_assessment", enhanced_executive_assessment_node)
    workflow.add_node("execute_tool", execute_tool_node)
    workflow.add_node("simple_planning", simple_planner_node)
    workflow.add_node("tool_explanation", tool_explanation_node)
    
    # Add complexity analysis node
    workflow.add_node("complexity_analysis", complexity_analysis_node)
    
    # Set entry point
    workflow.set_entry_point("executive_assessment")
    
    # Enhanced routing logic that supports dynamic processing
    workflow.add_conditional_edges(
        "executive_assessment",
        enhanced_routing_logic,
        {
            "DIRECT": "execute_tool",
            "PLANNING": "simple_planning",
            "COMPLEXITY_ANALYSIS": "complexity_analysis",
            "END": END
        }
    )
    
    # Add complexity analysis routing
    workflow.add_conditional_edges(
        "complexity_analysis",
        lambda state: "DIRECT" if not getattr(state, 'use_dynamic_processing', False) else "DYNAMIC",
        {
            "DIRECT": "execute_tool",
            "DYNAMIC": "execute_tool",  # Will be overridden in dynamic workflow
            "END": END
        }
    )
    
    workflow.add_edge("execute_tool", "tool_explanation")
    workflow.add_edge("simple_planning", "execute_tool")
    workflow.add_edge("tool_explanation", END)
    
    return workflow

def enhanced_routing_logic(state: GraphState) -> str:
    """
    Enhanced routing logic that can direct to complexity analysis or dynamic processing.
    """
    # Check if we should analyze complexity first
    if getattr(state, 'enable_dynamic_processing', False) and not hasattr(state, 'complexity_analyzed'):
        return "COMPLEXITY_ANALYSIS"
    
    # Check if dynamic processing was requested
    if getattr(state, 'use_dynamic_processing', False):
        return "DYNAMIC"
    
    # Use standard routing
    routing_decision = getattr(state, 'routing_decision', 'DIRECT')
    return routing_decision

async def complexity_analysis_node(state: GraphState) -> GraphState:
    """
    Node that analyzes request complexity and determines if dynamic processing is needed.
    """
    logger.info("Running complexity analysis node")
    
    try:
        # Mark as analyzed to prevent loops
        state.complexity_analyzed = True
        
        # Analyze complexity using dynamic node manager
        needs_dynamic, processing_plan = await dynamic_node_manager.analyze_and_create_plan(state)
        
        if needs_dynamic and processing_plan:
            logger.info(f"Complexity analysis suggests dynamic processing: {processing_plan.plan_id}")
            state.use_dynamic_processing = True
            state.processing_plan = processing_plan
            
            # Update routing decision for dynamic processing
            state.routing_decision = "DYNAMIC"
            
            # Notify user about smart processing
            if state.session_id:
                await progress_manager.broadcast_to_session_sync(state.session_id, {
                    "type": "smart_processing_detected",
                    "complexity_score": processing_plan.complexity_score,
                    "estimated_steps": processing_plan.estimated_steps,
                    "processing_type": processing_plan.context.get("analysis", {}).get("processing_type", "multi_step")
                })
        else:
            logger.info("Complexity analysis suggests standard processing")
            state.use_dynamic_processing = False
            # Keep existing routing decision
        
        return state
        
    except Exception as e:
        logger.error(f"Error in complexity analysis: {e}", exc_info=True)
        # Fall back to standard processing
        state.use_dynamic_processing = False
        state.complexity_analyzed = True
        return state

# Enhanced Assessment Node
async def enhanced_executive_assessment_node(state: GraphState) -> GraphState:
    """
    Enhanced executive assessment that can work with dynamic processing.
    """
    logger.info("Running enhanced executive assessment")
    
    try:
        user_input = state.user_input
        model_name = get_node_specific_model(state, "executive_assessment")
        
        # Enhanced assessment prompt that considers complexity
        assessment_prompt = f"""You are an AI executive assistant router. Analyze this user request and determine the best routing approach.

User Request: {user_input}

Consider these routing options:
1. DIRECT - Simple request that can be handled by a single tool immediately
2. PLANNING - Complex request that needs planning and multiple steps
3. COMPLEXITY_ANALYSIS - Request that might benefit from smart multi-step processing

Respond with JSON:
{{
  "routing_decision": "DIRECT/PLANNING/COMPLEXITY_ANALYSIS",
  "confidence_score": 0.0-1.0,
  "reasoning": "Brief explanation of routing choice",
  "complexity_indicators": [
    "multiple events/tasks mentioned",
    "requires iteration", 
    "batch processing needed",
    "hierarchical structure detected"
  ],
  "estimated_difficulty": "simple/moderate/complex"
}}

Guidelines:
- Use DIRECT for simple, single-tool requests
- Use PLANNING for requests needing deliberate multi-step planning
- Use COMPLEXITY_ANALYSIS for requests with multiple items, iteration needs, or batch operations
- Consider indicators like "add 5 events", "create project with subtasks", "process all emails"
- Higher complexity suggests need for smart processing"""

        response, _ = await invoke_llm_with_tokens(
            messages=[
                {"role": "system", "content": "You are an expert request router. Always respond with valid JSON."},
                {"role": "user", "content": assessment_prompt}
            ],
            model_name=model_name,
            category="executive_assessment"
        )
        
        # Parse response
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                assessment_result = json.loads(json_str)
                
                state.routing_decision = assessment_result.get("routing_decision", "DIRECT")
                state.confidence_score = assessment_result.get("confidence_score", 0.8)
                state.assessment_reasoning = assessment_result.get("reasoning", "")
                state.complexity_indicators = assessment_result.get("complexity_indicators", [])
                
                logger.info(f"Enhanced assessment: {state.routing_decision} (confidence: {state.confidence_score})")
                
            else:
                # Fallback
                state.routing_decision = "DIRECT"
                state.confidence_score = 0.5
                
        except Exception as parse_error:
            logger.error(f"Error parsing assessment response: {parse_error}")
            state.routing_decision = "DIRECT"
            state.confidence_score = 0.5
        
        return state
        
    except Exception as e:
        logger.error(f"Error in enhanced executive assessment: {e}", exc_info=True)
        state.routing_decision = "DIRECT"
        state.confidence_score = 0.3
        return state

# Import this in the assessment_nodes.py or update the import
enhanced_executive_assessment_node = enhanced_executive_assessment_node

# Backwards compatibility wrapper for existing router
async def run_router_graph(
    user_input: str,
    messages: List[BaseMessage],
    user_id: int,
    session_id: str,
    chat_model: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Backwards compatible wrapper that enables dynamic processing by default.
    """
    return await run_enhanced_router_graph(
        user_input=user_input,
        messages=messages,
        user_id=user_id,
        session_id=session_id,
        chat_model=chat_model,
        enable_dynamic_nodes=True,
        **kwargs
    )