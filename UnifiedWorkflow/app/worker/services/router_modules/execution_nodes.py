# services/router_modules/execution_nodes.py
"""
Tool execution nodes for the simplified router.
Handles direct tool calls and response formatting.
"""

import logging
from typing import Dict, Any, Optional, Callable, Awaitable
from worker.graph_types import GraphState
from worker.tool_handlers import get_tool_handler
from worker.services.ollama_service import invoke_llm_with_tokens
from .router_core import get_node_specific_model

logger = logging.getLogger(__name__)


async def execute_tool_node(state: GraphState) -> Dict[str, Any]:
    """
    Execute the selected tool and return results.
    Simplified version with better error handling.
    """
    try:
        tool_id = state.selected_tool
        if not tool_id:
            # If no tool selected, try to infer from user input
            tool_id = await infer_tool_from_input(state.user_input)
            if not tool_id:
                return {
                    "final_response": "I couldn't determine which tool to use for your request. Could you be more specific?",
                    "execution_status": "failed"
                }
        
        # Get tool handler
        handler: Optional[Callable[..., Awaitable[Any]]] = get_tool_handler(tool_id)
        if not handler:
            logger.error(f"No handler found for tool ID: {tool_id}")
            return {
                "final_response": f"The tool '{tool_id}' is not available right now.",
                "execution_status": "failed"
            }
        
        logger.info(f"Executing tool: {tool_id} for user {state.user_id}")
        
        # Execute the tool
        result = await handler(state)
        
        # Debug logging to trace the issue
        logger.info(f"Tool {tool_id} returned result type: {type(result)}")
        if isinstance(result, dict):
            logger.info(f"Tool result keys: {list(result.keys())}")
            logger.info(f"Tool result 'response' type: {type(result.get('response'))}")
        
        # Extract the response string from the tool result
        if isinstance(result, dict):
            response_text = result.get("response", str(result))
        else:
            response_text = str(result)
        
        # Additional safety check
        if isinstance(response_text, dict):
            logger.warning(f"Response text is still a dict: {response_text}")
            response_text = response_text.get("response", str(response_text))
        
        return {
            "final_response": response_text,
            "execution_status": "success",
            "tool_used": tool_id,
            "tool_output": result
        }
        
    except Exception as e:
        logger.error(f"Error executing tool: {e}", exc_info=True)
        return {
            "final_response": f"I encountered an error while processing your request: {str(e)}",
            "execution_status": "error",
            "error_details": str(e)
        }


async def infer_tool_from_input(user_input: str) -> Optional[str]:
    """
    Enhanced tool inference that can detect hierarchical lists and complex data structures.
    """
    from worker.shared_constants import (
        CALENDAR_TOOL_ID, EMAIL_TOOL_ID, DRIVE_TOOL_ID, WEB_SEARCH_TOOL_ID,
        TASK_MANAGEMENT_TOOL_ID, FILE_SYSTEM_TOOL_ID, DOCUMENT_QA_TOOL_ID
    )
    
    user_input_lower = user_input.lower()
    
    # Check for hierarchical list patterns first (higher priority)
    if _is_hierarchical_list_request(user_input):
        # If it's specifically calendar-related with many due dates, use LLM parser
        if any(word in user_input_lower for word in ["calendar", "schedule", "due dates"]) and \
           len([line for line in user_input.split('\n') if 'due:' in line.lower()]) >= 5:
            logger.info("Detected complex calendar list - using LLM calendar parser tool")
            return "llm_calendar_parser_tool"
        else:
            logger.info("Detected hierarchical list structure - using list parser tool")
            return "list_parser_tool"
    
    # Calendar keywords
    if any(word in user_input_lower for word in ["calendar", "schedule", "meeting", "appointment", "event"]):
        return CALENDAR_TOOL_ID
    
    # Email keywords  
    if any(word in user_input_lower for word in ["email", "mail", "send", "compose", "inbox"]):
        return EMAIL_TOOL_ID
    
    # Drive keywords
    if any(word in user_input_lower for word in ["drive", "upload", "download", "file", "document", "folder"]):
        return DRIVE_TOOL_ID
    
    # Search keywords
    if any(word in user_input_lower for word in ["search", "find", "look up", "google", "web"]):
        return WEB_SEARCH_TOOL_ID
    
    # Task management keywords
    if any(word in user_input_lower for word in ["task", "todo", "reminder", "project", "deadline"]):
        return TASK_MANAGEMENT_TOOL_ID
    
    # File system keywords
    if any(word in user_input_lower for word in ["file", "directory", "folder", "path", "local"]):
        return FILE_SYSTEM_TOOL_ID
    
    # Document Q&A keywords
    if any(word in user_input_lower for word in ["document", "pdf", "analyze", "summarize", "extract"]):
        return DOCUMENT_QA_TOOL_ID
    
    return None


def _is_hierarchical_list_request(user_input: str) -> bool:
    """
    Detect if the user input contains hierarchical list structures that need parsing.
    """
    # Look for common hierarchical list indicators
    lines = user_input.strip().split('\n')
    
    # Must have at least 3 lines to be considered hierarchical
    if len(lines) < 3:
        return False
    
    # Count lines that look like structured data
    structured_lines = 0
    section_headers = 0
    due_dates = 0
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
            
        # Look for section headers (lines that end with colon or are standalone categories)
        if (line_stripped.endswith(':') and not any(keyword in line_stripped.lower() 
            for keyword in ['due', 'time', 'date', 'at'])) or \
           (len(line_stripped.split()) <= 4 and line_stripped[0].isupper()):
            section_headers += 1
            
        # Look for due dates or time indicators
        if any(keyword in line_stripped.lower() for keyword in ['due:', 'due ', 'deadline:', 'deadline ']):
            due_dates += 1
            
        # Look for structured list items (start with number, letter, dash, or bullet)
        if line_stripped and (line_stripped[0].isdigit() or line_stripped.startswith(('-', '•', '*', '→'))):
            structured_lines += 1
    
    # Hierarchical list criteria:
    # 1. Has section headers AND structured content
    # 2. Has multiple due dates (suggests assignment/task lists)
    # 3. Has mixed structure (headers + items)
    
    is_hierarchical = (
        (section_headers >= 1 and structured_lines >= 2) or  # Clear hierarchy
        (due_dates >= 3) or  # Multiple assignments/tasks
        (section_headers >= 2 and len(lines) >= 5)  # Multiple sections
    )
    
    if is_hierarchical:
        logger.info(f"Hierarchical list detected: {section_headers} headers, {structured_lines} structured lines, {due_dates} due dates")
    
    return is_hierarchical


async def tool_explanation_node(state: GraphState) -> Dict[str, Any]:
    """
    Provide a brief explanation of what was accomplished.
    Simplified version that doesn't over-explain.
    """
    try:
        # For now, just pass through the final_response from execution node
        # This preserves the actual tool output without over-explaining
        current_response = state.final_response or "Task completed."
        
        # Ensure we return a string
        if isinstance(current_response, dict):
            current_response = current_response.get("response", str(current_response))
        elif not isinstance(current_response, str):
            current_response = str(current_response)
        
        return {
            "final_response": current_response,
            "explanation_generated": True
        }
        
    except Exception as e:
        logger.error(f"Error in tool explanation: {e}")
        # Return the original response if explanation fails
        fallback_response = state.final_response or "Task completed."
        if isinstance(fallback_response, dict):
            fallback_response = fallback_response.get("response", str(fallback_response))
        elif not isinstance(fallback_response, str):
            fallback_response = str(fallback_response)
            
        return {
            "final_response": fallback_response,
            "explanation_generated": False
        }


async def generate_success_explanation(state: GraphState) -> str:
    """
    Generate a brief success message without over-explaining.
    """
    tool_used = state.tool_used or "the requested tool"
    
    # Simple success templates based on tool type
    success_templates = {
        "calendar_tool": "I've updated your calendar as requested.",
        "email_tool": "I've handled your email request.",
        "drive_tool": "I've processed your Google Drive request.",
        "web_search_tool": "Here's what I found from your search.",
        "task_management_tool": "I've updated your tasks.",
        "file_system_tool": "I've completed the file operation.",
        "document_qa_tool": "I've analyzed the document for you."
    }
    
    # Use template or generic message
    template = success_templates.get(tool_used, f"I've completed the {tool_used} operation.")
    
    # Combine with actual response if it's informative
    if isinstance(state.final_response, str) and len(state.final_response) < 500:
        return f"{template}\n\n{state.final_response}"
    elif isinstance(state.final_response, dict) and "result" in state.final_response:
        return f"{template}\n\n{state.final_response['result']}"
    else:
        return template


async def generate_failure_explanation(state: GraphState) -> str:
    """
    Generate helpful guidance for failed executions.
    """
    error_details = state.error_details or "unknown error"
    
    # Provide user-friendly error messages
    if "permission" in error_details.lower():
        return "I don't have the necessary permissions to complete this task. You may need to check your account settings or re-authorize the service."
    elif "not found" in error_details.lower():
        return "I couldn't find the requested item. Please check the details and try again."
    elif "network" in error_details.lower() or "connection" in error_details.lower():
        return "I'm having trouble connecting to the service right now. Please try again in a moment."
    elif "rate limit" in error_details.lower():
        return "I've hit a usage limit for this service. Please wait a moment and try again."
    else:
        return f"I encountered an issue while processing your request. You might want to try rephrasing your request or checking if the service is available."