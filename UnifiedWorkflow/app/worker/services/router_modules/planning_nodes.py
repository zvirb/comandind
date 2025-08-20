# services/router_modules/planning_nodes.py
"""
Simplified planning nodes that replace the wave function system.
Focuses on simple, direct planning without specialist agents.
"""

import logging
from typing import Dict, Any, List
from worker.graph_types import GraphState
from worker.services.ollama_service import invoke_llm_with_tokens
from worker.shared_constants import PLANNER_TOOL_ID
from .router_core import get_node_specific_model

logger = logging.getLogger(__name__)


async def simple_planner_node(state: GraphState) -> Dict[str, Any]:
    """
    Simplified planning that replaces the wave function system.
    Creates straightforward step-by-step plans without specialist agents.
    """
    try:
        logger.info("Starting simple planning for complex request")
        
        # Generate a simple plan
        plan = await generate_simple_plan(state)
        
        if not plan:
            # Fall back to direct execution if planning fails
            return {
                "routing_decision": "DIRECT",
                "plan_steps": [],
                "planning_status": "failed_fallback_to_direct"
            }
        
        # Set up for plan execution
        return {
            "selected_tool": PLANNER_TOOL_ID,
            "plan_steps": plan,
            "planning_status": "success",
            "plan_complexity": "simple"
        }
        
    except Exception as e:
        logger.error(f"Error in simple planning: {e}", exc_info=True)
        return {
            "routing_decision": "DIRECT",
            "plan_steps": [],
            "planning_status": "error_fallback_to_direct"
        }


async def generate_simple_plan(state: GraphState) -> List[str]:
    """
    Generate a straightforward plan using a single LLM call.
    Replaces the complex wave function planning system.
    """
    try:
        model = get_node_specific_model(state, "simple_planning")
        
        planning_prompt = f"""
        Create a simple, step-by-step plan for this user request:
        
        Request: {state.user_input}
        
        Guidelines:
        1. Break the request into 3-7 clear, actionable steps
        2. Each step should be a concrete action, not advice
        3. Focus on what tools or actions are needed
        4. Keep steps simple and direct
        5. Avoid over-complicating the plan
        
        Format as a numbered list:
        1. [First step]
        2. [Second step]
        etc.
        
        Only return the numbered list, nothing else.
        """
        
        response, _ = await invoke_llm_with_tokens(
            model=model,
            messages=[{"role": "user", "content": planning_prompt}],
            temperature=0.3
        )
        
        # Parse the plan steps
        steps = parse_plan_steps(response)
        
        if len(steps) < 2:
            logger.warning("Generated plan too short, may not need planning")
            return []
        
        logger.info(f"Generated simple plan with {len(steps)} steps")
        return steps
        
    except Exception as e:
        logger.error(f"Error generating simple plan: {e}")
        return []


def parse_plan_steps(plan_text: str) -> List[str]:
    """
    Parse plan steps from LLM response.
    """
    steps = []
    lines = plan_text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Remove numbering (1., 2., etc.)
        if line[0].isdigit() and '.' in line:
            step = line.split('.', 1)[1].strip()
            if step:
                steps.append(step)
        elif line.startswith('- '):
            # Handle bullet points
            step = line[2:].strip()
            if step:
                steps.append(step)
        elif line and not any(char.isdigit() for char in line[:3]):
            # Handle lines without numbering
            steps.append(line)
    
    return steps[:7]  # Limit to 7 steps max


async def plan_validation_node(state: GraphState) -> Dict[str, Any]:
    """
    Simple plan validation - just checks if plan makes sense.
    Much lighter than the original validation.
    """
    try:
        plan_steps = state.plan_steps
        if not plan_steps or len(plan_steps) < 2:
            return {
                "plan_valid": False,
                "validation_reason": "Plan too short or missing"
            }
        
        # Simple validation checks
        validation_score = 0
        
        # Check if steps mention actual actions
        action_words = ["search", "find", "create", "update", "send", "get", "set", "call", "execute", "run"]
        for step in plan_steps:
            if any(word in step.lower() for word in action_words):
                validation_score += 1
        
        # Plan is valid if at least half the steps contain action words
        is_valid = validation_score >= len(plan_steps) / 2
        
        return {
            "plan_valid": is_valid,
            "validation_score": validation_score,
            "validation_reason": f"Action words found in {validation_score}/{len(plan_steps)} steps"
        }
        
    except Exception as e:
        logger.error(f"Error in plan validation: {e}")
        return {
            "plan_valid": True,  # Default to valid if validation fails
            "validation_reason": "Validation error - defaulting to valid"
        }


async def force_planning_node(state: GraphState) -> Dict[str, Any]:
    """
    Simple fallback planning for cases where user explicitly requests planning.
    """
    try:
        logger.info("Force planning requested")
        
        # Generate plan regardless of complexity assessment
        plan = await generate_simple_plan(state)
        
        if plan:
            return {
                "selected_tool": PLANNER_TOOL_ID,
                "plan_steps": plan,
                "planning_status": "forced_success",
                "routing_decision": "PLANNING"
            }
        else:
            return {
                "routing_decision": "DIRECT",
                "planning_status": "forced_failed",
                "plan_steps": []
            }
            
    except Exception as e:
        logger.error(f"Error in force planning: {e}")
        return {
            "routing_decision": "DIRECT",
            "planning_status": "forced_error"
        }