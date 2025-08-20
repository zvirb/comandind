#!/usr/bin/env python3
"""
Dynamic User Input Tool

This tool can be dynamically added to LangGraph nodes when the LLM determines
that more information is required from the user to complete a task. It creates
interactive input nodes that pause workflow execution and wait for user response.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum

from langgraph.graph import StateGraph, END
from worker.graph_types import GraphState
from worker.services.progress_manager import progress_manager
from worker.services.ollama_service import invoke_llm_with_tokens

logger = logging.getLogger(__name__)

class InputType(Enum):
    """Types of input that can be requested"""
    TEXT = "text"
    CHOICE = "choice"
    DATE = "date"
    TIME = "time"
    NUMBER = "number"
    BOOLEAN = "boolean"
    LIST = "list"
    STRUCTURED = "structured"

@dataclass
class UserInputRequest:
    """Represents a request for user input"""
    request_id: str
    question: str
    input_type: InputType
    required: bool = True
    options: List[str] = field(default_factory=list)  # For choice type
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    help_text: str = ""
    placeholder: str = ""
    default_value: Optional[str] = None
    timeout_seconds: int = 300  # 5 minutes default
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class UserInputResponse:
    """Represents a user's response to an input request"""
    request_id: str
    value: Any
    input_type: InputType
    timestamp: datetime
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)

@dataclass
class InputSession:
    """Manages a session of user input requests"""
    session_id: str
    user_id: str
    graph_session_id: str
    requests: List[UserInputRequest] = field(default_factory=list)
    responses: Dict[str, UserInputResponse] = field(default_factory=dict)
    status: str = "active"  # active, completed, timeout, cancelled
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    context: Dict[str, Any] = field(default_factory=dict)

class DynamicUserInputManager:
    """Manages dynamic user input requests in LangGraph workflows"""
    
    def __init__(self):
        self.active_sessions: Dict[str, InputSession] = {}
        self.response_waiters: Dict[str, asyncio.Event] = {}
        self.input_history: List[InputSession] = []
    
    async def analyze_input_needs(self, state: GraphState, context: str = "") -> Dict[str, Any]:
        """
        Analyze if user input is needed and what type of input to request
        """
        user_input = state.user_input
        current_context = context or getattr(state, 'current_context', '')
        
        analysis_prompt = f"""You are an expert workflow analyzer. Determine if user input is needed to complete this task and what specific information to request.

Current Task Context: {current_context}
User's Original Request: {user_input}
Current State: Processing in progress, may need additional information

Analyze and respond with JSON:
{{
  "input_analysis": {{
    "needs_user_input": true/false,
    "urgency": "critical/high/medium/low",
    "input_requests": [
      {{
        "question": "Clear, specific question to ask the user",
        "input_type": "text/choice/date/time/number/boolean/list/structured",
        "required": true/false,
        "options": ["option1", "option2"] (only for choice type),
        "validation_rules": {{
          "min_length": 1,
          "max_length": 100,
          "pattern": "regex pattern if needed",
          "custom_validation": "description of validation needed"
        }},
        "help_text": "Additional context or instructions",
        "placeholder": "Example of expected input",
        "default_value": "default if any",
        "context": {{
          "relates_to": "what part of the task this input helps with",
          "impact": "how this input affects the workflow"
        }}
      }}
    ],
    "input_strategy": {{
      "collection_method": "sequential/parallel/conditional",
      "timeout_per_question": 300,
      "allow_skip": true/false,
      "provide_suggestions": true/false
    }},
    "workflow_impact": {{
      "can_continue_without": true/false,
      "blocks_other_operations": true/false,
      "affects_parallel_processing": true/false
    }}
  }}
}}

Guidelines:
- Only request input if genuinely needed to complete the task
- Ask specific, clear questions that help move the task forward
- Consider what the user has already provided
- For complex tasks, break down into multiple specific questions
- Use appropriate input types:
  * text: for descriptions, names, general info
  * choice: when there are specific options to choose from
  * date: for dates (calendar events, deadlines)
  * time: for specific times
  * number: for quantities, durations, etc.
  * boolean: for yes/no questions
  * list: when multiple items are expected
  * structured: for complex data (addresses, contact info, etc.)
- Provide helpful context and examples
- Consider validation needs (required fields, format requirements)"""

        try:
            model_name = getattr(state, 'tool_selection_model', 'llama3.2:3b')
            
            response, _ = await invoke_llm_with_tokens(
                messages=[
                    {"role": "system", "content": "You are a user input analysis expert. Always respond with valid JSON only."},
                    {"role": "user", "content": analysis_prompt}
                ],
                model_name=model_name,
                category="input_needs_analysis"
            )
            
            # Parse JSON response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                analysis_data = json.loads(json_str)
                return analysis_data.get("input_analysis", {})
            else:
                raise ValueError("Could not parse input analysis response")
                
        except Exception as e:
            logger.error(f"Error analyzing input needs: {e}", exc_info=True)
            # Conservative fallback - assume input might be needed
            return {
                "needs_user_input": True,
                "urgency": "medium",
                "input_requests": [{
                    "question": "I need additional information to complete this task. Could you provide more details?",
                    "input_type": "text",
                    "required": True,
                    "help_text": "Please provide any additional information that would help complete your request.",
                    "placeholder": "Additional details..."
                }]
            }
    
    async def create_input_session(self, state: GraphState, input_analysis: Dict[str, Any]) -> InputSession:
        """Create a new input session based on analysis"""
        
        session_id = f"input_{uuid.uuid4().hex[:8]}"
        
        # Create input requests
        requests = []
        for i, request_data in enumerate(input_analysis.get("input_requests", [])):
            request = UserInputRequest(
                request_id=f"{session_id}_req_{i+1}",
                question=request_data.get("question", "Please provide information"),
                input_type=InputType(request_data.get("input_type", "text")),
                required=request_data.get("required", True),
                options=request_data.get("options", []),
                validation_rules=request_data.get("validation_rules", {}),
                help_text=request_data.get("help_text", ""),
                placeholder=request_data.get("placeholder", ""),
                default_value=request_data.get("default_value"),
                timeout_seconds=input_analysis.get("input_strategy", {}).get("timeout_per_question", 300),
                context=request_data.get("context", {})
            )
            requests.append(request)
        
        # Create session
        session = InputSession(
            session_id=session_id,
            user_id=state.user_id,
            graph_session_id=state.session_id,
            requests=requests,
            context={
                "original_request": state.user_input,
                "analysis": input_analysis,
                "workflow_context": getattr(state, 'current_context', '')
            }
        )
        
        self.active_sessions[session_id] = session
        logger.info(f"Created input session: {session_id} with {len(requests)} requests")
        
        return session
    
    async def request_user_input(self, session: InputSession, collection_method: str = "sequential") -> Dict[str, UserInputResponse]:
        """Request user input for a session"""
        
        if collection_method == "sequential":
            return await self._request_sequential_input(session)
        elif collection_method == "parallel":
            return await self._request_parallel_input(session)
        else:
            return await self._request_conditional_input(session)
    
    async def _request_sequential_input(self, session: InputSession) -> Dict[str, UserInputResponse]:
        """Request input sequentially, one question at a time"""
        
        responses = {}
        
        for request in session.requests:
            logger.info(f"Requesting sequential input: {request.request_id}")
            
            # Send input request to user
            if session.graph_session_id:
                await progress_manager.broadcast_to_session_sync(session.graph_session_id, {
                    "type": "user_input_request",
                    "input_session_id": session.session_id,
                    "request_id": request.request_id,
                    "question": request.question,
                    "input_type": request.input_type.value,
                    "required": request.required,
                    "options": request.options,
                    "help_text": request.help_text,
                    "placeholder": request.placeholder,
                    "default_value": request.default_value,
                    "validation_rules": request.validation_rules,
                    "timeout_seconds": request.timeout_seconds
                })
            
            # Wait for response
            response = await self._wait_for_input_response(request)
            
            if response:
                responses[request.request_id] = response
                session.responses[request.request_id] = response
                
                # If this was a required input and user didn't provide it, stop
                if request.required and not response.value:
                    break
            else:
                # Timeout or cancellation
                break
        
        return responses
    
    async def _request_parallel_input(self, session: InputSession) -> Dict[str, UserInputResponse]:
        """Request all inputs at once (parallel form)"""
        
        logger.info(f"Requesting parallel input for session: {session.session_id}")
        
        # Send all input requests at once
        if session.graph_session_id:
            input_form = {
                "type": "user_input_form",
                "input_session_id": session.session_id,
                "form_title": "Additional Information Required",
                "requests": []
            }
            
            for request in session.requests:
                input_form["requests"].append({
                    "request_id": request.request_id,
                    "question": request.question,
                    "input_type": request.input_type.value,
                    "required": request.required,
                    "options": request.options,
                    "help_text": request.help_text,
                    "placeholder": request.placeholder,
                    "default_value": request.default_value,
                    "validation_rules": request.validation_rules
                })
            
            await progress_manager.broadcast_to_session_sync(session.graph_session_id, input_form)
        
        # Wait for all responses (with timeout)
        timeout = max([req.timeout_seconds for req in session.requests])
        try:
            # Create waiter for this session
            session_waiter = asyncio.Event()
            self.response_waiters[session.session_id] = session_waiter
            
            # Wait for completion or timeout
            await asyncio.wait_for(session_waiter.wait(), timeout=timeout)
            
            return session.responses
            
        except asyncio.TimeoutError:
            logger.warning(f"Input session {session.session_id} timed out")
            session.status = "timeout"
            return session.responses
        finally:
            # Clean up waiter
            if session.session_id in self.response_waiters:
                del self.response_waiters[session.session_id]
    
    async def _request_conditional_input(self, session: InputSession) -> Dict[str, UserInputResponse]:
        """Request input conditionally based on previous responses"""
        # For now, fall back to sequential
        return await self._request_sequential_input(session)
    
    async def _wait_for_input_response(self, request: UserInputRequest) -> Optional[UserInputResponse]:
        """Wait for a response to a specific input request"""
        
        try:
            # Create waiter for this request
            request_waiter = asyncio.Event()
            self.response_waiters[request.request_id] = request_waiter
            
            # Wait for response or timeout
            await asyncio.wait_for(request_waiter.wait(), timeout=request.timeout_seconds)
            
            # Find the session and get the response
            for session in self.active_sessions.values():
                if request.request_id in session.responses:
                    return session.responses[request.request_id]
            
            return None
            
        except asyncio.TimeoutError:
            logger.warning(f"Input request {request.request_id} timed out")
            return None
        finally:
            # Clean up waiter
            if request.request_id in self.response_waiters:
                del self.response_waiters[request.request_id]
    
    async def submit_user_response(self, session_id: str, request_id: str, value: Any) -> bool:
        """Submit a user response to an input request"""
        
        if session_id not in self.active_sessions:
            logger.error(f"Input session not found: {session_id}")
            return False
        
        session = self.active_sessions[session_id]
        
        # Find the request
        request = next((req for req in session.requests if req.request_id == request_id), None)
        if not request:
            logger.error(f"Input request not found: {request_id}")
            return False
        
        # Validate the response
        is_valid, validation_errors = self._validate_input(value, request)
        
        # Create response
        response = UserInputResponse(
            request_id=request_id,
            value=value,
            input_type=request.input_type,
            timestamp=datetime.now(),
            is_valid=is_valid,
            validation_errors=validation_errors
        )
        
        # Store response
        session.responses[request_id] = response
        
        # Notify waiters
        if request_id in self.response_waiters:
            self.response_waiters[request_id].set()
        
        # Check if session is complete
        if len(session.responses) >= len([req for req in session.requests if req.required]):
            session.status = "completed"
            session.completed_at = datetime.now()
            
            # Notify session waiter
            if session_id in self.response_waiters:
                self.response_waiters[session_id].set()
        
        logger.info(f"Submitted response for {request_id}: {value} (valid: {is_valid})")
        return True
    
    def _validate_input(self, value: Any, request: UserInputRequest) -> tuple[bool, List[str]]:
        """Validate user input against request requirements"""
        
        errors = []
        
        # Check if required
        if request.required and (value is None or value == ""):
            errors.append("This field is required")
            return False, errors
        
        # Skip validation for empty optional fields
        if not request.required and (value is None or value == ""):
            return True, []
        
        # Type-specific validation
        if request.input_type == InputType.CHOICE:
            if value not in request.options:
                errors.append(f"Value must be one of: {', '.join(request.options)}")
        
        elif request.input_type == InputType.NUMBER:
            try:
                float(value)
            except (ValueError, TypeError):
                errors.append("Value must be a number")
        
        elif request.input_type == InputType.DATE:
            # Basic date validation (could be enhanced)
            if not self._is_valid_date_string(str(value)):
                errors.append("Please provide a valid date")
        
        elif request.input_type == InputType.TIME:
            # Basic time validation (could be enhanced)
            if not self._is_valid_time_string(str(value)):
                errors.append("Please provide a valid time")
        
        # Custom validation rules
        validation_rules = request.validation_rules
        
        if validation_rules.get("min_length") and len(str(value)) < validation_rules["min_length"]:
            errors.append(f"Minimum length is {validation_rules['min_length']} characters")
        
        if validation_rules.get("max_length") and len(str(value)) > validation_rules["max_length"]:
            errors.append(f"Maximum length is {validation_rules['max_length']} characters")
        
        if validation_rules.get("pattern"):
            import re
            if not re.match(validation_rules["pattern"], str(value)):
                errors.append("Format is not valid")
        
        return len(errors) == 0, errors
    
    def _is_valid_date_string(self, date_str: str) -> bool:
        """Basic date string validation"""
        common_formats = [
            "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y",
            "%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y"
        ]
        
        for fmt in common_formats:
            try:
                datetime.strptime(date_str, fmt)
                return True
            except ValueError:
                continue
        return False
    
    def _is_valid_time_string(self, time_str: str) -> bool:
        """Basic time string validation"""
        common_formats = [
            "%H:%M", "%I:%M %p", "%H:%M:%S", "%I:%M:%S %p"
        ]
        
        for fmt in common_formats:
            try:
                datetime.strptime(time_str, fmt)
                return True
            except ValueError:
                continue
        return False
    
    def get_session_responses(self, session_id: str) -> Dict[str, Any]:
        """Get all responses for a session in a structured format"""
        
        if session_id not in self.active_sessions:
            return {}
        
        session = self.active_sessions[session_id]
        structured_responses = {}
        
        for request_id, response in session.responses.items():
            # Find the original request
            request = next((req for req in session.requests if req.request_id == request_id), None)
            if request:
                structured_responses[request.question] = {
                    "value": response.value,
                    "type": response.input_type.value,
                    "is_valid": response.is_valid,
                    "context": request.context
                }
        
        return structured_responses
    
    def cleanup_session(self, session_id: str):
        """Clean up a completed input session"""
        
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            self.input_history.append(session)
            del self.active_sessions[session_id]
            
            # Clean up any remaining waiters
            for request in session.requests:
                if request.request_id in self.response_waiters:
                    del self.response_waiters[request.request_id]
            
            if session_id in self.response_waiters:
                del self.response_waiters[session_id]
            
            logger.info(f"Cleaned up input session: {session_id}")

# Global instance
dynamic_user_input_manager = DynamicUserInputManager()

# Node creation functions for LangGraph integration

def create_user_input_node(input_analysis: Dict[str, Any]) -> Callable:
    """Create a LangGraph node that requests user input"""
    
    async def user_input_node(state: GraphState) -> GraphState:
        """Node that pauses workflow to request user input"""
        
        logger.info("Executing user input node")
        
        try:
            # Create input session
            session = await dynamic_user_input_manager.create_input_session(state, input_analysis)
            
            # Determine collection method
            input_strategy = input_analysis.get("input_strategy", {})
            collection_method = input_strategy.get("collection_method", "sequential")
            
            # Request input from user
            responses = await dynamic_user_input_manager.request_user_input(session, collection_method)
            
            # Process responses and update state
            if responses:
                # Get structured responses
                structured_responses = dynamic_user_input_manager.get_session_responses(session.session_id)
                
                # Add responses to state
                state.user_input_responses = structured_responses
                state.additional_user_info = structured_responses
                
                # Update context with new information
                current_context = getattr(state, 'current_context', '')
                new_context = current_context + f"\n\nAdditional user information: {json.dumps(structured_responses, indent=2)}"
                state.current_context = new_context
                
                # Mark as having received input
                state.received_user_input = True
                
                logger.info(f"Received {len(responses)} user responses")
            else:
                # Handle timeout or no responses
                state.user_input_timeout = True
                state.received_user_input = False
                
                logger.warning("User input timed out or was cancelled")
            
            # Clean up session
            dynamic_user_input_manager.cleanup_session(session.session_id)
            
            return state
            
        except Exception as e:
            logger.error(f"Error in user input node: {e}", exc_info=True)
            state.user_input_error = str(e)
            state.received_user_input = False
            return state
    
    return user_input_node

def create_input_analysis_node() -> Callable:
    """Create a node that analyzes if user input is needed"""
    
    async def input_analysis_node(state: GraphState) -> GraphState:
        """Node that determines if user input is required"""
        
        logger.info("Analyzing if user input is needed")
        
        try:
            # Analyze input needs
            current_context = getattr(state, 'current_context', '')
            input_analysis = await dynamic_user_input_manager.analyze_input_needs(state, current_context)
            
            # Store analysis in state
            state.input_needs_analysis = input_analysis
            state.needs_user_input = input_analysis.get("needs_user_input", False)
            
            # If input is needed, mark for input collection
            if state.needs_user_input:
                state.routing_decision = "USER_INPUT"
                logger.info("User input required - routing to input collection")
            else:
                logger.info("No user input needed - continuing with workflow")
            
            return state
            
        except Exception as e:
            logger.error(f"Error in input analysis: {e}", exc_info=True)
            state.input_analysis_error = str(e)
            state.needs_user_input = False
            return state
    
    return input_analysis_node

# Tool handler for direct integration
async def handle_user_input_request(state: GraphState) -> Dict[str, Any]:
    """
    Handle user input requests from tools or workflows
    """
    tool_output = state.tool_output or {}
    questions = tool_output.get("questions", [])
    input_type = tool_output.get("input_type", "text")
    timeout = tool_output.get("timeout", 300)
    
    logger.info(f"Handling user input request with {len(questions)} questions")
    
    try:
        # Create a simple input analysis for direct requests
        input_analysis = {
            "needs_user_input": True,
            "urgency": "high",
            "input_requests": [],
            "input_strategy": {
                "collection_method": "sequential",
                "timeout_per_question": timeout
            }
        }
        
        # Convert questions to input requests
        for i, question in enumerate(questions):
            if isinstance(question, dict):
                input_analysis["input_requests"].append(question)
            else:
                input_analysis["input_requests"].append({
                    "question": str(question),
                    "input_type": input_type,
                    "required": True
                })
        
        # Create and execute input session
        session = await dynamic_user_input_manager.create_input_session(state, input_analysis)
        responses = await dynamic_user_input_manager.request_user_input(session)
        
        # Process responses
        if responses:
            structured_responses = dynamic_user_input_manager.get_session_responses(session.session_id)
            dynamic_user_input_manager.cleanup_session(session.session_id)
            
            return {
                "response": "User input collected successfully",
                "user_responses": structured_responses,
                "success": True
            }
        else:
            return {
                "response": "User input request timed out or was cancelled",
                "success": False,
                "timeout": True
            }
            
    except Exception as e:
        logger.error(f"Error handling user input request: {e}", exc_info=True)
        return {
            "response": f"Failed to collect user input: {str(e)}",
            "success": False,
            "error": str(e)
        }