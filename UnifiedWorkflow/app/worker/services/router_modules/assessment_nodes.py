# services/router_modules/assessment_nodes.py
"""
Simplified assessment nodes that remove concurrent processing bottlenecks.
Replaces complex wave function assessment with fast heuristic-based routing.
"""

import logging
from typing import Dict, Any
from worker.graph_types import GraphState
from worker.services.ollama_service import invoke_llm_with_tokens
from .router_core import get_node_specific_model

logger = logging.getLogger(__name__)


async def simple_executive_assessment_node(state: GraphState) -> Dict[str, Any]:
    """
    Simplified executive assessment that uses fast heuristics instead of concurrent LLM calls.
    Removes major bottleneck from original implementation.
    """
    try:
        user_input = state.user_input.lower()
        
        # Fast heuristic-based routing (no LLM calls)
        routing_decision = determine_routing_heuristically(user_input)
        confidence_score = calculate_simple_confidence(user_input, routing_decision)
        
        logger.info(f"Fast routing decision: {routing_decision} (confidence: {confidence_score})")
        
        # For DIRECT routing, set a default tool
        selected_tool = None
        if routing_decision == "DIRECT":
            # Default to unstructured interaction for direct routing
            selected_tool = "handle_unstructured_interaction"
        
        return {
            "routing_decision": routing_decision,
            "confidence_score": confidence_score,
            "selected_tool": selected_tool,
            "assessment_method": "heuristic"  # Track that we used fast method
        }
        
    except Exception as e:
        logger.error(f"Error in simplified executive assessment: {e}")
        return {
            "routing_decision": "DIRECT",
            "confidence_score": 0.5,
            "selected_tool": "handle_unstructured_interaction",  # Safe fallback
            "assessment_method": "fallback"
        }


def determine_routing_heuristically(user_input: str) -> str:
    """
    Fast heuristic routing based on keywords and patterns.
    Replaces expensive LLM-based assessment.
    """
    # Keywords that suggest planning is needed
    planning_keywords = [
        "plan", "strategy", "steps", "process", "workflow", "organize",
        "schedule", "timeline", "roadmap", "approach", "methodology",
        "complex", "multiple", "several", "various", "different",
        "first", "then", "next", "finally", "sequence", "order"
    ]
    
    # Keywords that suggest direct action
    direct_keywords = [
        "search", "find", "get", "show", "tell", "what", "when", "where",
        "how", "quick", "simple", "just", "only", "immediately", "now"
    ]
    
    # Count keyword matches
    planning_score = sum(1 for keyword in planning_keywords if keyword in user_input)
    direct_score = sum(1 for keyword in direct_keywords if keyword in user_input)
    
    # Length-based heuristic (longer requests often need planning)
    word_count = len(user_input.split())
    if word_count > 30:
        planning_score += 1
    
    # Question-based heuristic
    question_words = ["what", "how", "when", "where", "why", "which", "who"]
    if any(word in user_input for word in question_words):
        direct_score += 1
    
    # Decision logic
    if planning_score > direct_score:
        return "PLANNING"
    else:
        return "DIRECT"


def calculate_simple_confidence(user_input: str, routing_decision: str) -> float:
    """
    Calculate confidence based on simple heuristics.
    """
    base_confidence = 0.7
    
    # Adjust based on input clarity
    word_count = len(user_input.split())
    if word_count < 5:
        base_confidence -= 0.2  # Very short inputs are uncertain
    elif word_count > 50:
        base_confidence -= 0.1  # Very long inputs may be complex
    
    # Adjust based on question words
    question_words = ["what", "how", "when", "where", "why"]
    if any(word in user_input.lower() for word in question_words):
        if routing_decision == "DIRECT":
            base_confidence += 0.1  # Questions usually direct
    
    # Clamp between 0.3 and 0.9
    return max(0.3, min(0.9, base_confidence))


async def confidence_assessment_node(state: GraphState) -> Dict[str, Any]:
    """
    Simplified confidence assessment - mostly uses heuristic score.
    Only calls LLM for edge cases where heuristic confidence is very low.
    """
    if state.confidence_score >= 0.6:
        # Trust the heuristic assessment
        return {"confidence_verified": True}
    
    # Only for very uncertain cases, use LLM
    try:
        model = get_node_specific_model(state, "executive_assessment")
        
        prompt = f"""
        Analyze this user request and provide a confidence score (0.0-1.0):
        
        Request: {state.user_input}
        Initial routing: {state.routing_decision}
        
        Consider:
        1. Is the request clear and actionable?
        2. Does the routing decision seem appropriate?
        
        Respond with just a number between 0.0 and 1.0.
        """
        
        response, _ = await invoke_llm_with_tokens(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        
        # Parse confidence from response
        try:
            confidence = float(response.strip())
            confidence = max(0.0, min(1.0, confidence))
        except:
            confidence = state.confidence_score  # Fall back to heuristic
            
        return {
            "confidence_score": confidence,
            "confidence_verified": True
        }
        
    except Exception as e:
        logger.error(f"Error in confidence assessment: {e}")
        return {
            "confidence_score": state.confidence_score,
            "confidence_verified": False
        }