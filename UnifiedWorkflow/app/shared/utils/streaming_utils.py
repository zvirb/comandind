"""
Streaming utilities for Server-Sent Events (SSE) responses.
Ensures all streaming JSON responses are properly formatted and SSE compliant.
"""

import json
import logging
import re
from typing import Any, Dict, Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)


def sanitize_content(content: str) -> str:
    """
    Sanitize content to prevent JSON encoding issues.
    
    Args:
        content: Raw content that may contain problematic characters
        
    Returns:
        Sanitized content safe for JSON encoding
    """
    if not isinstance(content, str):
        content = str(content)
    
    # Remove null bytes and other control characters that break JSON
    content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
    
    # Replace problematic Unicode characters
    content = content.encode('utf-8', errors='replace').decode('utf-8')
    
    # Ensure no unescaped quotes or backslashes
    content = content.replace('\\', '\\\\').replace('"', '\\"')
    
    return content


def validate_json_serializable(data: Any) -> bool:
    """
    Validate that data can be safely JSON serialized.
    
    Args:
        data: Data to validate
        
    Returns:
        True if data can be JSON serialized, False otherwise
    """
    try:
        json.dumps(data)
        return True
    except (TypeError, ValueError, OverflowError) as e:
        logger.warning(f"Data not JSON serializable: {e}")
        return False


def safe_json_dumps(data: Any, default_value: str = "null") -> str:
    """
    Safely serialize data to JSON with fallback.
    
    Args:
        data: Data to serialize
        default_value: Fallback value if serialization fails
        
    Returns:
        JSON string or default_value if serialization fails
    """
    try:
        # Handle special cases
        if hasattr(data, 'dict'):
            # Pydantic model - convert to dict first
            data = data.dict()
        elif hasattr(data, '__dict__'):
            # Other objects with __dict__ - convert to dict
            data = {k: v for k, v in data.__dict__.items() if not k.startswith('_')}
        
        # Recursively sanitize string content
        if isinstance(data, dict):
            sanitized_data = {}
            for key, value in data.items():
                if isinstance(value, str):
                    sanitized_data[key] = sanitize_content(value)
                elif isinstance(value, (list, dict)):
                    sanitized_data[key] = _recursive_sanitize(value)
                else:
                    sanitized_data[key] = value
            data = sanitized_data
        elif isinstance(data, str):
            data = sanitize_content(data)
        elif isinstance(data, list):
            data = _recursive_sanitize(data)
        
        return json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    except Exception as e:
        logger.error(f"JSON serialization failed: {e}")
        return default_value


def _recursive_sanitize(data: Union[list, dict]) -> Union[list, dict]:
    """Recursively sanitize nested data structures."""
    if isinstance(data, dict):
        return {
            key: sanitize_content(value) if isinstance(value, str) 
            else _recursive_sanitize(value) if isinstance(value, (list, dict))
            else value
            for key, value in data.items()
        }
    elif isinstance(data, list):
        return [
            sanitize_content(item) if isinstance(item, str)
            else _recursive_sanitize(item) if isinstance(item, (list, dict))
            else item
            for item in data
        ]
    return data


def format_sse_data(event_type: str, content: Any, **metadata) -> str:
    """
    Format data as a properly structured SSE event.
    
    Args:
        event_type: Type of the SSE event
        content: Main content for the event
        **metadata: Additional metadata to include
        
    Returns:
        Properly formatted SSE data string
    """
    # Build the event data
    event_data = {
        "type": event_type,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    # Add content
    if content is not None:
        if isinstance(content, str):
            event_data["content"] = sanitize_content(content)
        else:
            event_data["content"] = content
    
    # Add metadata
    if metadata:
        # Sanitize metadata values
        sanitized_metadata = {}
        for key, value in metadata.items():
            if isinstance(value, str):
                sanitized_metadata[key] = sanitize_content(value)
            else:
                sanitized_metadata[key] = value
        
        event_data["metadata"] = sanitized_metadata
    
    # Convert to JSON safely
    json_str = safe_json_dumps(event_data)
    
    # Format as SSE event
    return f"data: {json_str}\n\n"


def format_sse_error(error: Union[str, Exception], error_type: Optional[str] = None) -> str:
    """
    Format an error as a properly structured SSE event.
    
    Args:
        error: Error message or Exception
        error_type: Optional error type classification
        
    Returns:
        Properly formatted SSE error event
    """
    if isinstance(error, Exception):
        error_message = sanitize_content(str(error))
        error_type = error_type or type(error).__name__
    else:
        error_message = sanitize_content(str(error))
        error_type = error_type or "UnknownError"
    
    return format_sse_data(
        event_type="error",
        content=error_message,
        error_type=error_type
    )


def format_sse_info(message: str, **metadata) -> str:
    """
    Format an info message as SSE event.
    
    Args:
        message: Info message
        **metadata: Additional metadata
        
    Returns:
        Properly formatted SSE info event
    """
    return format_sse_data(
        event_type="info",
        content=sanitize_content(message),
        **metadata
    )


def format_sse_content(content: str, **metadata) -> str:
    """
    Format content as SSE event.
    
    Args:
        content: Content to stream
        **metadata: Additional metadata
        
    Returns:
        Properly formatted SSE content event
    """
    return format_sse_data(
        event_type="content",
        content=sanitize_content(content),
        **metadata
    )


def format_sse_final(session_id: str, mode: str, **metadata) -> str:
    """
    Format final completion event as SSE.
    
    Args:
        session_id: Session identifier
        mode: Chat mode
        **metadata: Additional metadata
        
    Returns:
        Properly formatted SSE final event
    """
    # Build the event data with session_id and mode at top level
    event_data = {
        "type": "final",
        "session_id": session_id,
        "mode": mode,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    # Add metadata
    if metadata:
        # Sanitize metadata values
        sanitized_metadata = {}
        for key, value in metadata.items():
            if isinstance(value, str):
                sanitized_metadata[key] = sanitize_content(value)
            else:
                sanitized_metadata[key] = value
        
        event_data["metadata"] = sanitized_metadata
    
    # Convert to JSON safely
    json_str = safe_json_dumps(event_data)
    
    # Format as SSE event
    return f"data: {json_str}\n\n"


class SSEValidator:
    """Validator for SSE event format compliance."""
    
    @staticmethod
    def validate_sse_format(sse_data: str) -> bool:
        """
        Validate that SSE data follows proper format.
        
        Args:
            sse_data: SSE formatted string
            
        Returns:
            True if valid SSE format, False otherwise
        """
        # SSE format should start with "data: " and end with "\n\n"
        if not sse_data.startswith("data: "):
            logger.warning("SSE data doesn't start with 'data: '")
            return False
        
        if not sse_data.endswith("\n\n"):
            logger.warning("SSE data doesn't end with '\\n\\n'")
            return False
        
        # Extract JSON part
        json_part = sse_data[6:-2]  # Remove "data: " and "\n\n"
        
        # Validate JSON
        try:
            json.loads(json_part)
            return True
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in SSE data: {e}")
            return False
    
    @staticmethod
    def validate_event_structure(event_data: dict) -> bool:
        """
        Validate that event data has required structure.
        
        Args:
            event_data: Parsed event data dictionary
            
        Returns:
            True if valid structure, False otherwise
        """
        required_fields = ["type", "timestamp"]
        
        for field in required_fields:
            if field not in event_data:
                logger.warning(f"Missing required field '{field}' in event data")
                return False
        
        # Validate event type
        valid_types = ["content", "info", "error", "final", "expert_response", 
                      "meeting_start", "phase_transition", "todo_update", 
                      "task_delegation", "meeting_summary", "meeting_end",
                      "workflow_info", "expert_question", "expert_content",
                      "expert_separator", "phase_header"]
        
        if event_data["type"] not in valid_types:
            logger.warning(f"Invalid event type: {event_data['type']}")
            return False
        
        return True