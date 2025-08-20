# services/router_modules/router_core.py
"""
Core router module containing the main graph orchestration logic.
This is a simplified version focused on DIRECT vs PLANNING routing only.
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any, Union, Tuple
from datetime import datetime

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableLambda

# Conditional import for ChatOllama - fallback if langchain_ollama not available
try:
    from langchain_ollama.chat_models import ChatOllama
    HAS_LANGCHAIN_OLLAMA = True
except ImportError:
    # When langchain_ollama is not available, create a placeholder
    ChatOllama = None
    HAS_LANGCHAIN_OLLAMA = False
    logging.warning("langchain_ollama not available, router core will use basic responses")

from worker.graph_types import GraphState
from worker.tool_handlers import get_tool_handler
from shared.utils.config import get_settings
from worker.services.progress_manager import progress_manager
from worker.services.ollama_service import invoke_llm_with_tokens

logger = logging.getLogger(__name__)
settings = get_settings()


def get_node_specific_model(state: GraphState, node_type: str) -> str:
    """
    Simplified model selection for streamlined router.
    Removes wave function models and complex fallback chains.
    """
    model_mappings = {
        "executive_assessment": state.chat_model or "llama3.2:3b",
        "tool_routing": state.tool_routing_model or "llama3.2:3b", 
        "simple_planning": state.simple_planning_model or "llama3.2:3b",
        "reflection": state.reflection_model or "llama3.2:3b",
        "final_response": state.final_response_model or "llama3.2:3b"
    }
    
    return model_mappings.get(node_type, state.chat_model or "llama3.2:3b")


async def run_router_graph(
    user_input: str,
    messages: List[BaseMessage],
    user_id: int,
    session_id: str,
    chat_model: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Enhanced main entry point for the router graph with dynamic node support.
    Automatically enables dynamic processing for complex tool use.
    """
    try:
        # Import enhanced router
        from .enhanced_router_core import run_enhanced_router_graph
        
        # Use enhanced router with dynamic nodes enabled by default
        return await run_enhanced_router_graph(
            user_input=user_input,
            messages=messages,
            user_id=user_id,
            session_id=session_id,
            chat_model=chat_model,
            enable_dynamic_nodes=True,  # Force dynamic processing for all complex operations
            **kwargs
        )
        
    except Exception as e:
        logger.error(f"Error in enhanced router graph: {e}", exc_info=True)
        
        # Fallback to simplified router if enhanced fails
        logger.warning("Falling back to simplified router due to enhanced router error")
        return await run_simplified_router_graph(
            user_input=user_input,
            messages=messages,
            user_id=user_id,
            session_id=session_id,
            chat_model=chat_model,
            **kwargs
        )

async def run_simplified_router_graph(
    user_input: str,
    messages: List[BaseMessage],
    user_id: int,
    session_id: str,
    chat_model: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Simplified fallback router without dynamic node support.
    """
    try:
        # Initialize simplified state
        initial_state = GraphState(
            messages=messages,
            user_input=user_input,
            user_id=str(user_id),  # Convert int to string for GraphState compatibility
            session_id=session_id,
            chat_model=chat_model or "llama3.2:3b",
            final_response="",
            conversation_summary="",
            routing_decision="DIRECT",  # Default to direct routing
            confidence_score=0.8,
            **kwargs
        )
        
        # Create simplified workflow
        workflow = create_simplified_workflow()
        
        # Compile and run
        app = workflow.compile()
        result = await app.ainvoke(initial_state)
        
        # Ensure final_response is always a string
        final_response = result.get("final_response", "")
        if isinstance(final_response, dict):
            # Extract response from dictionary if it's in dict format
            final_response = final_response.get("response", str(final_response))
        elif not isinstance(final_response, str):
            final_response = str(final_response)
        
        return {
            "response": final_response,
            "routing_decision": result.get("routing_decision", "DIRECT"),
            "confidence_score": result.get("confidence_score", 0.8),
            "metadata": {
                "user_id": user_id,
                "model_used": result.get("chat_model", chat_model),
                "timestamp": datetime.now().isoformat(),
                "router_type": "simplified_fallback"
            }
        }
        
    except Exception as e:
        logger.error(f"Error in simplified router graph: {e}", exc_info=True)
        return {
            "response": f"I encountered an error processing your request: {str(e)}",
            "routing_decision": "ERROR",
            "confidence_score": 0.0,
            "metadata": {"error": str(e)}
        }


def create_simplified_workflow() -> StateGraph:
    """
    Create simplified workflow with only essential nodes.
    Removes wave function, multi-agent debate, and complex assessment.
    """
    workflow = StateGraph(GraphState)
    
    # Add simplified nodes - import from other modules
    from .assessment_nodes import simple_executive_assessment_node
    from .execution_nodes import execute_tool_node, tool_explanation_node
    from .planning_nodes import simple_planner_node
    
    # Core routing nodes (async functions don't need RunnableLambda wrapper)
    workflow.add_node("executive_assessment", simple_executive_assessment_node)
    workflow.add_node("execute_tool", execute_tool_node)
    workflow.add_node("simple_planning", simple_planner_node)
    workflow.add_node("tool_explanation", tool_explanation_node)
    
    # Set entry point
    workflow.set_entry_point("executive_assessment")
    
    # Simple routing logic
    workflow.add_conditional_edges(
        "executive_assessment",
        lambda state: state.routing_decision,
        {
            "DIRECT": "execute_tool",
            "PLANNING": "simple_planning", 
            "END": END
        }
    )
    
    workflow.add_edge("execute_tool", "tool_explanation")
    workflow.add_edge("simple_planning", "execute_tool")
    workflow.add_edge("tool_explanation", END)
    
    return workflow