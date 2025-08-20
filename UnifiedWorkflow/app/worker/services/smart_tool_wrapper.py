#!/usr/bin/env python3
"""
Smart Tool Wrapper

A generic wrapper that can enhance any tool with:
1. Complexity analysis
2. Multi-step processing
3. Progress tracking
4. Error recovery
5. Context preservation
"""

import asyncio
import logging
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from worker.graph_types import GraphState
from worker.services.smart_tool_orchestrator import smart_orchestrator
from worker.services.progress_manager import progress_manager

logger = logging.getLogger(__name__)

def smart_tool_enhancement(
    enable_multi_step: bool = True,
    enable_progress_tracking: bool = True,
    enable_error_recovery: bool = True,
    complexity_threshold: int = 4,
    max_iterations: int = 10
):
    """
    Decorator to enhance any tool with smart capabilities
    
    Args:
        enable_multi_step: Enable multi-step processing for complex requests
        enable_progress_tracking: Send progress updates to user
        enable_error_recovery: Attempt to recover from errors
        complexity_threshold: Complexity score threshold for smart processing
        max_iterations: Maximum number of iterations for multi-step tasks
    """
    def decorator(original_handler: Callable[[GraphState], Dict[str, Any]]):
        @wraps(original_handler)
        async def enhanced_handler(state: GraphState) -> Dict[str, Any]:
            logger.info(f"Smart tool enhancement wrapper for: {original_handler.__name__}")
            
            try:
                # Analyze request complexity if multi-step is enabled
                if enable_multi_step:
                    analysis = await smart_orchestrator.analyze_request_complexity(state, state.user_input)
                    complexity_score = analysis.get("complexity_score", 1)
                    requires_multi_step = analysis.get("requires_multi_step", False)
                    
                    logger.info(f"Complexity analysis - Score: {complexity_score}, Multi-step: {requires_multi_step}")
                    
                    # Use smart orchestration for complex requests
                    if complexity_score >= complexity_threshold and requires_multi_step:
                        logger.info("Using smart orchestration for complex request")
                        
                        # Notify user about smart processing
                        if enable_progress_tracking and state.session_id:
                            await progress_manager.broadcast_to_session_sync(state.session_id, {
                                "type": "smart_processing_started",
                                "tool_name": original_handler.__name__,
                                "complexity_score": complexity_score,
                                "estimated_steps": analysis.get("estimated_steps", 1)
                            })
                        
                        # Create and execute smart plan
                        execution = await smart_orchestrator.create_smart_execution_plan(state, state.user_input, analysis)
                        result = await smart_orchestrator.execute_smart_task(execution, state)
                        
                        return result
                
                # For simple requests or if smart processing is disabled, use original handler
                logger.info("Using original tool handler")
                
                # Add progress tracking for original handler if enabled
                if enable_progress_tracking and state.session_id:
                    await progress_manager.broadcast_to_session_sync(state.session_id, {
                        "type": "tool_processing_started",
                        "tool_name": original_handler.__name__
                    })
                
                # Execute original handler with error recovery
                if enable_error_recovery:
                    result = await execute_with_retry(original_handler, state, max_retries=2)
                else:
                    result = await original_handler(state)
                
                # Notify completion
                if enable_progress_tracking and state.session_id:
                    await progress_manager.broadcast_to_session_sync(state.session_id, {
                        "type": "tool_processing_completed",
                        "tool_name": original_handler.__name__,
                        "success": not result.get("error")
                    })
                
                return result
                
            except Exception as e:
                logger.error(f"Error in smart tool wrapper for {original_handler.__name__}: {e}", exc_info=True)
                
                # Notify error
                if enable_progress_tracking and state.session_id:
                    await progress_manager.broadcast_to_session_sync(state.session_id, {
                        "type": "tool_processing_error",
                        "tool_name": original_handler.__name__,
                        "error": str(e)
                    })
                
                return {
                    "response": f"An error occurred while processing your request with {original_handler.__name__}. Please try again.",
                    "error": str(e),
                    "tool_name": original_handler.__name__
                }
        
        return enhanced_handler
    return decorator

async def execute_with_retry(
    handler: Callable[[GraphState], Dict[str, Any]], 
    state: GraphState, 
    max_retries: int = 2
) -> Dict[str, Any]:
    """
    Execute a handler with retry logic for error recovery
    """
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            result = await handler(state)
            
            # Check if result indicates an error that should be retried
            if result.get("error") and attempt < max_retries:
                error_msg = result["error"]
                
                # Determine if error is retryable
                retryable_errors = [
                    "timeout",
                    "connection",
                    "temporarily unavailable",
                    "rate limit",
                    "service unavailable"
                ]
                
                is_retryable = any(err in error_msg.lower() for err in retryable_errors)
                
                if is_retryable:
                    logger.warning(f"Retryable error on attempt {attempt + 1}: {error_msg}")
                    await asyncio.sleep(min(2 ** attempt, 10))  # Exponential backoff
                    continue
            
            return result
            
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                logger.warning(f"Exception on attempt {attempt + 1}: {e}")
                await asyncio.sleep(min(2 ** attempt, 10))
                continue
            else:
                raise
    
    # This shouldn't be reached, but just in case
    raise last_error if last_error else Exception("Unknown error in retry logic")

# Convenience decorators for common tool types
def smart_calendar_tool(original_handler):
    """Smart enhancement specifically for calendar tools"""
    return smart_tool_enhancement(
        enable_multi_step=True,
        enable_progress_tracking=True,
        enable_error_recovery=True,
        complexity_threshold=3,  # Lower threshold for calendar complexity
        max_iterations=15  # More iterations for multi-event handling
    )(original_handler)

def smart_email_tool(original_handler):
    """Smart enhancement specifically for email tools"""
    return smart_tool_enhancement(
        enable_multi_step=True,
        enable_progress_tracking=True,
        enable_error_recovery=True,
        complexity_threshold=4,
        max_iterations=10
    )(original_handler)

def smart_task_tool(original_handler):
    """Smart enhancement specifically for task management tools"""
    return smart_tool_enhancement(
        enable_multi_step=True,
        enable_progress_tracking=True,
        enable_error_recovery=True,
        complexity_threshold=4,
        max_iterations=12
    )(original_handler)

def smart_file_tool(original_handler):
    """Smart enhancement specifically for file system tools"""
    return smart_tool_enhancement(
        enable_multi_step=True,
        enable_progress_tracking=False,  # File operations might be too fast for progress tracking
        enable_error_recovery=True,
        complexity_threshold=5,
        max_iterations=8
    )(original_handler)

# Generic smart tool wrapper for any tool
def make_tool_smart(original_handler, **kwargs):
    """
    Make any tool smart with custom settings
    
    Usage:
        enhanced_handler = make_tool_smart(my_handler, complexity_threshold=3)
    """
    return smart_tool_enhancement(**kwargs)(original_handler)