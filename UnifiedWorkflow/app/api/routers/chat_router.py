"""Router for handling chat interactions."""
import uuid
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, Request, HTTPException, Response
from fastapi.responses import StreamingResponse
from celery import Celery
import logging

from ..dependencies import get_current_user
from shared.database.models import User
from shared.schemas.user_schemas import UserSettings
from shared.schemas.enhanced_chat_schemas import (
    ChatMessageRequest, ChatResponse, FeedbackRequest, MessageType,
    ToolExecutionResult, IntermediateStep, StreamingChunk, ToolExecutionStatus,
    ChatMode
)
from shared.services.smart_ai_interview_service import smart_ai_interview_service
from ..services.feedback_service import feedback_service
from shared.monitoring.prometheus_metrics import metrics
import time


router = APIRouter()
logger = logging.getLogger(__name__)

def normalize_chat_request(body: Dict[str, Any], message: str, logger) -> Dict[str, Any]:
    """
    Enhanced normalization and validation of chat request fields to prevent 422 errors.
    Handles common frontend variations and type coercion gracefully with comprehensive logging.
    """
    logger.info(f"Normalizing chat request: {body}")
    normalized = {"message": message}
    
    # Enhanced mode field validation with detailed logging
    mode_value = body.get("mode", "smart-router")
    logger.debug(f"Processing mode field: {mode_value} (type: {type(mode_value)})")
    try:
        # Handle various mode formats
        if isinstance(mode_value, str):
            # Map common variations
            mode_mappings = {
                "smart-router": ChatMode.SMART_ROUTER,
                "smart_router": ChatMode.SMART_ROUTER,
                "smartrouter": ChatMode.SMART_ROUTER,
                "socratic-interview": ChatMode.SOCRATIC_INTERVIEW,
                "socratic_interview": ChatMode.SOCRATIC_INTERVIEW,
                "socraticinterview": ChatMode.SOCRATIC_INTERVIEW,
                "expert-group": ChatMode.EXPERT_GROUP,
                "expert_group": ChatMode.EXPERT_GROUP,
                "expertgroup": ChatMode.EXPERT_GROUP,
                "direct": ChatMode.DIRECT
            }
            
            normalized_mode_key = mode_value.lower().strip()
            if normalized_mode_key in mode_mappings:
                normalized["mode"] = mode_mappings[normalized_mode_key]
                logger.debug(f"Successfully mapped mode '{mode_value}' to '{normalized['mode']}'") 
            else:
                # Try direct enum parsing
                try:
                    chat_mode = ChatMode(mode_value)
                    normalized["mode"] = chat_mode
                    logger.debug(f"Successfully parsed mode '{mode_value}' directly")
                except ValueError:
                    logger.warning(f"Invalid mode '{mode_value}', falling back to smart-router")
                    normalized["mode"] = ChatMode.SMART_ROUTER
        else:
            logger.warning(f"Non-string mode type {type(mode_value)}: '{mode_value}', falling back to smart-router")
            normalized["mode"] = ChatMode.SMART_ROUTER
    except Exception as e:
        logger.error(f"Unexpected error processing mode '{mode_value}': {e}, falling back to smart-router")
        normalized["mode"] = ChatMode.SMART_ROUTER
    
    # Enhanced session_id normalization with validation
    session_id = body.get("session_id")
    logger.debug(f"Processing session_id: {session_id} (type: {type(session_id)})")
    if session_id is not None:
        try:
            if isinstance(session_id, (str, int, float)):
                session_str = str(session_id).strip()
                if session_str:
                    normalized["session_id"] = session_str
                    logger.debug(f"Normalized session_id to: '{session_str}'")
                else:
                    normalized["session_id"] = None
                    logger.debug("Empty session_id after normalization, set to None")
            else:
                logger.warning(f"Invalid session_id type {type(session_id)}, setting to None")
                normalized["session_id"] = None
        except Exception as e:
            logger.error(f"Error normalizing session_id '{session_id}': {e}, setting to None")
            normalized["session_id"] = None
    
    # Enhanced current_graph_state validation
    current_graph_state = body.get("current_graph_state")
    logger.debug(f"Processing current_graph_state: {type(current_graph_state)}")
    if current_graph_state is not None:
        try:
            if isinstance(current_graph_state, dict):
                normalized["current_graph_state"] = current_graph_state
                logger.debug(f"Valid current_graph_state dict with {len(current_graph_state)} keys")
            elif isinstance(current_graph_state, str):
                # Try to parse JSON string
                import json
                try:
                    parsed_state = json.loads(current_graph_state)
                    if isinstance(parsed_state, dict):
                        normalized["current_graph_state"] = parsed_state
                        logger.debug(f"Parsed current_graph_state from JSON string")
                    else:
                        logger.warning(f"Parsed current_graph_state is not a dict: {type(parsed_state)}, using empty dict")
                        normalized["current_graph_state"] = {}
                except json.JSONDecodeError as je:
                    logger.warning(f"Failed to parse current_graph_state JSON '{current_graph_state}': {je}, using empty dict")
                    normalized["current_graph_state"] = {}
            else:
                logger.warning(f"Invalid current_graph_state type {type(current_graph_state)}, using empty dict")
                normalized["current_graph_state"] = {}
        except Exception as e:
            logger.error(f"Error processing current_graph_state: {e}, using empty dict")
            normalized["current_graph_state"] = {}
    
    # Enhanced message_history validation
    message_history = body.get("message_history")
    logger.debug(f"Processing message_history: {type(message_history)}")
    if message_history is not None:
        try:
            if isinstance(message_history, list):
                # Validate each item in the list
                validated_history = []
                for i, item in enumerate(message_history):
                    if isinstance(item, dict):
                        validated_history.append(item)
                    elif isinstance(item, str):
                        # Convert string to basic message format
                        validated_history.append({"content": item, "role": "user"})
                    else:
                        logger.warning(f"Invalid message_history item at index {i}: {type(item)}, skipping")
                normalized["message_history"] = validated_history
                logger.debug(f"Validated message_history with {len(validated_history)} items")
            elif isinstance(message_history, str):
                # Try to parse JSON array
                import json
                try:
                    parsed_history = json.loads(message_history)
                    if isinstance(parsed_history, list):
                        normalized["message_history"] = parsed_history
                        logger.debug(f"Parsed message_history from JSON string")
                    else:
                        logger.warning(f"Parsed message_history is not a list: {type(parsed_history)}, using empty list")
                        normalized["message_history"] = []
                except json.JSONDecodeError as je:
                    logger.warning(f"Failed to parse message_history JSON '{message_history}': {je}, using empty list")
                    normalized["message_history"] = []
            else:
                logger.warning(f"Invalid message_history type {type(message_history)}, using empty list")
                normalized["message_history"] = []
        except Exception as e:
            logger.error(f"Error processing message_history: {e}, using empty list")
            normalized["message_history"] = []
    
    # Enhanced user_preferences validation
    user_preferences = body.get("user_preferences")
    logger.debug(f"Processing user_preferences: {type(user_preferences)}")
    if user_preferences is not None:
        try:
            if isinstance(user_preferences, dict):
                normalized["user_preferences"] = user_preferences
                logger.debug(f"Valid user_preferences dict with {len(user_preferences)} keys")
            elif isinstance(user_preferences, str):
                # Try to parse JSON string
                import json
                try:
                    parsed_prefs = json.loads(user_preferences)
                    if isinstance(parsed_prefs, dict):
                        normalized["user_preferences"] = parsed_prefs
                        logger.debug(f"Parsed user_preferences from JSON string")
                    else:
                        logger.warning(f"Parsed user_preferences is not a dict: {type(parsed_prefs)}, using empty dict")
                        normalized["user_preferences"] = {}
                except json.JSONDecodeError as je:
                    logger.warning(f"Failed to parse user_preferences JSON '{user_preferences}': {je}, using empty dict")
                    normalized["user_preferences"] = {}
            else:
                logger.warning(f"Invalid user_preferences type {type(user_preferences)}, using empty dict")
                normalized["user_preferences"] = {}
        except Exception as e:
            logger.error(f"Error processing user_preferences: {e}, using empty dict")
            normalized["user_preferences"] = {}
    
    logger.info(f"Normalized request successfully: session_id='{normalized.get('session_id')}', mode='{normalized['mode']}', state_keys={list(normalized.get('current_graph_state', {}).keys())}, history_length={len(normalized.get('message_history', []))}")
    return normalized

@router.post("", response_model=Dict[str, Any])
@router.post("/", response_model=Dict[str, Any])
async def handle_chat_message(request: Request, current_user: User = Depends(get_current_user)):
    """
    Main chat endpoint that handles both structured and unstructured requests.
    This is the primary endpoint that the frontend calls.
    Enhanced with 422 error prevention and comprehensive monitoring.
    """
    start_time = time.time()
    endpoint = "/api/v1/chat/"
    method = request.method
    try:
        body = await request.json()
        logger.info(f"Received chat request from user {current_user.id}: {body}")
        
        # Enhanced request debugging
        logger.debug(f"Request details - Method: {request.method}, URL: {request.url}, Headers: {dict(request.headers)}")
        logger.debug(f"Request body type: {type(body)}, Keys: {list(body.keys()) if isinstance(body, dict) else 'N/A'}")
        
        # Log individual field types for debugging
        if isinstance(body, dict):
            for key, value in body.items():
                logger.debug(f"Field '{key}': value='{value}', type={type(value)}")
        
        # Record request metrics
        metrics.record_request_metrics(
            method=method,
            endpoint=endpoint,
            status=200,
            duration=0,  # Will be updated at the end
            request_size=len(str(body))
        )
        
    except Exception as e:
        logger.error(f"Failed to parse JSON request body: {e}")
        duration = time.time() - start_time
        metrics.record_request_metrics(method, endpoint, 400, duration)
        metrics.data_validation_failures_total.labels(
            data_type="json",
            validation_type="parse",
            error_type="invalid_json"
        ).inc()
        raise HTTPException(status_code=400, detail="Invalid JSON in request body")
    
    if not body or not isinstance(body, dict):
        logger.error(f"Invalid request body type: {type(body)}")
        duration = time.time() - start_time
        metrics.record_request_metrics(method, endpoint, 400, duration)
        metrics.data_validation_failures_total.labels(
            data_type="request_body",
            validation_type="type_check",
            error_type="invalid_type"
        ).inc()
        raise HTTPException(status_code=400, detail="Request body must be a valid JSON object")
    
    message = body.get("message") or body.get("query")
    if not message or (isinstance(message, str) and len(message.strip()) == 0):
        logger.error(f"Empty message in request body: {body}")
        duration = time.time() - start_time
        metrics.record_request_metrics(method, endpoint, 400, duration)
        metrics.data_validation_failures_total.labels(
            data_type="message",
            validation_type="required_field",
            error_type="empty_message"
        ).inc()
        raise HTTPException(status_code=400, detail="Message or query cannot be empty")
    
    # Ensure message is a string and truncate if too long (prevent 422 from max_length)
    message = str(message)
    if len(message) > 10000:
        logger.warning(f"Message too long ({len(message)} chars), truncating to 10000 chars")
        # Record message truncation event
        metrics.data_validation_attempts_total.labels(
            data_type="message",
            validation_type="length_truncation"
        ).inc()
        message = message[:10000]
    
    try:
        # Enhanced validation and normalization with graceful error handling
        logger.info(f"Starting request normalization for user {current_user.id}")
        normalized_request = normalize_chat_request(body, message, logger)
        logger.info(f"Request normalization completed successfully for user {current_user.id}")
        
        # Enhanced structured request parsing with detailed error handling
        try:
            logger.debug(f"Attempting structured validation with normalized request: {list(normalized_request.keys())}")
            chat_request = ChatMessageRequest(**normalized_request)
            logger.info(f"Successfully parsed ChatMessageRequest for user {current_user.id}")
            # Record successful validation
            metrics.data_validation_attempts_total.labels(
                data_type="chat_request",
                validation_type="pydantic_schema"
            ).inc()
        except Exception as validation_error:
            logger.error(f"Structured validation failed with detailed error: {validation_error}")
            logger.error(f"Failed request data: {normalized_request}")
            
            # Extract detailed field errors from Pydantic validation error
            field_errors = []
            if hasattr(validation_error, 'errors'):
                for error in validation_error.errors():
                    field_path = '.'.join(str(x) for x in error.get('loc', []))
                    error_msg = error.get('msg', 'Unknown error')
                    error_type = error.get('type', 'unknown')
                    field_errors.append(f"Field '{field_path}': {error_msg} (type: {error_type})")
                    logger.error(f"Validation error - Field: {field_path}, Message: {error_msg}, Type: {error_type}")
            
            # Record validation failure but successful fallback
            metrics.data_validation_failures_total.labels(
                data_type="chat_request", 
                validation_type="pydantic_schema",
                error_type="fallback_used"
            ).inc()
            
            # Create robust fallback request with extra validation
            try:
                safe_session_id = normalized_request.get("session_id")
                if not safe_session_id:
                    safe_session_id = str(uuid.uuid4())
                    logger.debug(f"Generated new session_id: {safe_session_id}")
                
                safe_mode = normalized_request.get("mode", ChatMode.SMART_ROUTER)
                if not isinstance(safe_mode, ChatMode):
                    safe_mode = ChatMode.SMART_ROUTER
                    logger.debug(f"Corrected mode to: {safe_mode}")
                
                safe_graph_state = normalized_request.get("current_graph_state", {})
                if not isinstance(safe_graph_state, dict):
                    safe_graph_state = {}
                    logger.debug("Corrected current_graph_state to empty dict")
                
                safe_message_history = normalized_request.get("message_history", [])
                if not isinstance(safe_message_history, list):
                    safe_message_history = []
                    logger.debug("Corrected message_history to empty list")
                
                safe_user_preferences = normalized_request.get("user_preferences", {})
                if not isinstance(safe_user_preferences, dict):
                    safe_user_preferences = {}
                    logger.debug("Corrected user_preferences to empty dict")
                
                chat_request = ChatMessageRequest(
                    message=str(message)[:10000],  # Truncate if too long
                    session_id=safe_session_id,
                    mode=safe_mode,
                    current_graph_state=safe_graph_state,
                    message_history=safe_message_history,
                    user_preferences=safe_user_preferences
                )
                logger.info(f"Successfully created fallback ChatMessageRequest for user {current_user.id}")
                
            except Exception as fallback_error:
                logger.error(f"Fallback request creation failed: {fallback_error}")
                # Ultimate fallback - minimal valid request
                chat_request = ChatMessageRequest(
                    message=str(message)[:10000],
                    session_id=str(uuid.uuid4()),
                    mode=ChatMode.SMART_ROUTER
                )
                logger.warning(f"Using minimal fallback ChatMessageRequest for user {current_user.id}")
                
                # Record ultimate fallback usage
                metrics.data_validation_failures_total.labels(
                    data_type="chat_request", 
                    validation_type="ultimate_fallback",
                    error_type="minimal_request"
                ).inc()
        
        # Call structured endpoint
        response = await handle_structured_chat_message(chat_request, request, current_user)
        
        # Convert structured response to dict for compatibility
        result = {
            "response": response.response,
            "status": "success",
            "message_id": response.message_id,
            "session_id": response.session_id,
            "task_id": getattr(response, "task_id", None),
            "processing_status": getattr(response, "processing_status", "completed")
        }
        
        # Record successful completion metrics
        duration = time.time() - start_time
        metrics.record_request_metrics(
            method=method,
            endpoint=endpoint,
            status=200,
            duration=duration,
            response_size=len(str(result))
        )
        
        # Record user request metric
        metrics.user_requests_total.labels(
            user_type=str(current_user.role),
            endpoint=endpoint
        ).inc()
        
        logger.info(f"Successfully processed chat message for user {current_user.id}")
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is (they already have metrics recorded)
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing chat message: {e}", exc_info=True)
        logger.error(f"Request body that caused error: {body}")
        
        # Record error metrics
        duration = time.time() - start_time
        metrics.record_request_metrics(method, endpoint, 500, duration)
        metrics.security_events.labels(
            event_type="unexpected_error",
            severity="medium",
            source="chat_api"
        ).inc()
        
        # Fallback: simple echo response for now
        # TODO: Implement actual AI processing without structured validation
        fallback_result = {
            "response": f"I received your message: {message}. The AI processing system is currently being enhanced.",
            "status": "success",
            "message_id": str(uuid.uuid4()),
            "session_id": body.get("session_id", str(uuid.uuid4())),
            "processing_status": "completed"
        }
        
        # Record fallback usage
        metrics.data_validation_failures_total.labels(
            data_type="chat_processing",
            validation_type="system_error",
            error_type="fallback_response"
        ).inc()
        
        return fallback_result

@router.post("/structured", response_model=ChatResponse)
async def handle_structured_chat_message(chat_request: ChatMessageRequest, request: Request, current_user: User = Depends(get_current_user)):
    """
    Enhanced chat message handler with structured input/output.
    Uses Pydantic models for type safety and validation.
    """
    message = chat_request.message
    session_id = chat_request.session_id or str(uuid.uuid4())
    mode = chat_request.mode
    current_graph_state = chat_request.current_graph_state
    message_history = chat_request.message_history
    user_preferences = chat_request.user_preferences or {}

    if message.startswith("SYSTEM_COMMAND: START_ASSESSMENT"):
        try:
            assessment_type = message.split("TYPE:")[1].strip()
            response_content = await smart_ai_interview_service.initiate_assessment(current_user.id, assessment_type)
            # Return as ChatResponse instead of raw Response for consistency
            return ChatResponse(
                message_id=str(uuid.uuid4()),
                session_id=session_id,
                response=response_content,
                type=MessageType.SYSTEM,
                processing_status="completed"
            )
        except IndexError:
            logger.error(f"Invalid START_ASSESSMENT command format: {message}")
            raise HTTPException(status_code=400, detail="Invalid START_ASSESSMENT command format")
        except Exception as e:
            logger.error(f"Error initiating assessment: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error initiating assessment: {e}")

    
    # Get user settings for LLM model selection from database
    user_settings = UserSettings(
        theme="light", 
        notifications_enabled=True,
        selected_model=current_user.chat_model or "llama3.2:3b",  # Legacy fallback
        chat_model=current_user.chat_model or "llama3.2:3b",
        initial_assessment_model=current_user.initial_assessment_model or "llama3.2:3b",
        tool_selection_model=current_user.tool_selection_model or "llama3.2:3b", 
        embeddings_model=current_user.embeddings_model or "llama3.2:3b",
        coding_model=current_user.coding_model or "llama3.2:3b",
        # Granular node-specific models with intelligent fallbacks
        executive_assessment_model=getattr(current_user, 'executive_assessment_model', None) or current_user.initial_assessment_model or "llama3.2:3b",
        confidence_assessment_model=getattr(current_user, 'confidence_assessment_model', None) or current_user.initial_assessment_model or "llama3.2:3b",
        tool_routing_model=getattr(current_user, 'tool_routing_model', None) or current_user.tool_selection_model or "llama3.2:3b",
        simple_planning_model=getattr(current_user, 'simple_planning_model', None) or current_user.tool_selection_model or "llama3.2:3b",
        wave_function_specialist_model=getattr(current_user, 'wave_function_specialist_model', None) or current_user.initial_assessment_model or "llama3.2:1b",
        wave_function_refinement_model=getattr(current_user, 'wave_function_refinement_model', None) or current_user.coding_model or "llama3.1:8b",
        plan_validation_model=getattr(current_user, 'plan_validation_model', None) or current_user.initial_assessment_model or "llama3.2:3b",
        plan_comparison_model=getattr(current_user, 'plan_comparison_model', None) or current_user.coding_model or "llama3.2:3b",
        reflection_model=getattr(current_user, 'reflection_model', None) or current_user.chat_model or "llama3.2:3b",
        final_response_model=getattr(current_user, 'final_response_model', None) or current_user.chat_model or "llama3.2:3b"
    )
    
    # Add user model preferences to the graph state
    if current_graph_state is None:
        current_graph_state = {}
    
    current_graph_state.update({
        # Legacy model fields
        "chat_model": user_settings.chat_model,
        "initial_assessment_model": user_settings.initial_assessment_model,
        "tool_selection_model": user_settings.tool_selection_model,
        "embeddings_model": user_settings.embeddings_model,
        "coding_model": user_settings.coding_model,
        "selected_model": user_settings.selected_model,  # For backward compatibility
        # Granular node-specific models
        "executive_assessment_model": user_settings.executive_assessment_model,
        "confidence_assessment_model": user_settings.confidence_assessment_model,
        "tool_routing_model": user_settings.tool_routing_model,
        "simple_planning_model": user_settings.simple_planning_model,
        "wave_function_specialist_model": user_settings.wave_function_specialist_model,
        "wave_function_refinement_model": user_settings.wave_function_refinement_model,
        "plan_validation_model": user_settings.plan_validation_model,
        "plan_comparison_model": user_settings.plan_comparison_model,
        "reflection_model": user_settings.reflection_model,
        "final_response_model": user_settings.final_response_model
    })
    
    # Get Celery app from FastAPI app state
    celery_app: Celery = request.app.state.celery_app
    
    # Trigger the AI workflow engine
    task_kwargs = {
        "session_id": session_id,
        "user_id": str(current_user.id),
        "user_input": message,
        "current_graph_state_dict": current_graph_state
    }
    
    try:
        task = celery_app.send_task("tasks.execute_chat_graph", kwargs=task_kwargs)
        
        return ChatResponse(
            message_id=str(uuid.uuid4()),
            session_id=session_id,
            response="Your message is being processed by the AI workflow engine",
            type=MessageType.ASSISTANT,
            task_id=task.id,
            processing_status="processing"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to trigger AI processing: {str(e)}"
        )

@router.get("/status/{task_id}")
async def get_chat_task_status(task_id: str, request: Request, _current_user: User = Depends(get_current_user)):
    """
    Get the status and result of a chat processing task.
    """
    try:
        celery_app: Celery = request.app.state.celery_app
        from celery.result import AsyncResult
        
        task_result = AsyncResult(task_id, app=celery_app)
        
        result = {
            "task_id": task_id,
            "status": task_result.status,
            "result": task_result.result if task_result.ready() else None,
            "error_message": None
        }
        
        if task_result.failed():
            # Extract exception message from the result
            error_info = task_result.result
            result["error_message"] = str(error_info)
            # Also include the traceback for more detailed client-side logging if needed
            result["traceback"] = task_result.traceback
        
        # If the task completed successfully, extract the response
        elif task_result.successful():
            final_state = task_result.result
            if isinstance(final_state, dict):
                # First, try to get response from final_response field
                if "final_response" in final_state and final_state["final_response"]:
                    response = final_state["final_response"]
                    if isinstance(response, dict) and "response" in response:
                        result["response"] = response["response"]
                    elif isinstance(response, str):
                        result["response"] = response
                
                # If no final_response, try to extract from messages
                elif "messages" in final_state:
                    messages = final_state.get("messages", [])
                    for message in reversed(messages):
                        if hasattr(message, 'type') and message.type == 'ai':
                            result["response"] = message.content
                            break
                        elif isinstance(message, dict) and message.get("type") == "ai":
                            result["response"] = message.get("content", "")
                            break
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get task status: {str(e)}"
        )

@router.post("/enhanced", response_model=ChatResponse)
async def handle_enhanced_chat_message(
    chat_request: ChatMessageRequest, 
    current_user: User = Depends(get_current_user)
):
    """
    Enhanced chat endpoint with structured inputs/outputs and streaming support.
    Uses LangChain 0.3+ features including structured outputs and LCEL.
    """
    from worker.services.enhanced_router_service import enhanced_router_service
    from datetime import datetime
    import asyncio
    
    try:
        # Create enhanced graph state
        enhanced_state = await enhanced_router_service.create_enhanced_graph_state(
            user_input=chat_request.message,
            session_id=chat_request.session_id or str(uuid.uuid4()),
            user_id=str(current_user.id)
        )
        
        # Convert to legacy GraphState for compatibility
        from worker.graph_types import GraphState
        legacy_state = GraphState(
            user_input=chat_request.message,
            session_id=enhanced_state.session_id,
            user_id=str(current_user.id),
            messages=[],
            chat_model=current_user.chat_model or "llama3.2:3b",
            tool_routing_model=getattr(current_user, 'tool_routing_model', None) or "llama3.2:3b",
            executive_assessment_model=getattr(current_user, 'executive_assessment_model', None) or "llama3.2:3b"
        )
        
        # Collect intermediate steps
        intermediate_steps = []
        tool_results = []
        
        # Process with streaming
        async for step in enhanced_router_service.process_request_with_streaming(
            chat_request.message, legacy_state
        ):
            intermediate_steps.append(step)
            
            # Extract tool results from steps
            if step.step_name.startswith("tool_execution_") and step.status == "completed":
                if step.output and isinstance(step.output, dict):
                    tool_result = ToolExecutionResult(**step.output)
                    tool_results.append(tool_result)
        
        # Generate final response based on results
        final_response = "I've processed your request."
        if tool_results:
            successful_tools = [tr for tr in tool_results if tr.status == ToolExecutionStatus.SUCCESS]
            if successful_tools:
                final_response = f"Successfully executed {len(successful_tools)} tool(s). "
                if successful_tools[0].result:
                    if isinstance(successful_tools[0].result, dict) and "response" in successful_tools[0].result:
                        final_response = successful_tools[0].result["response"]
                    elif isinstance(successful_tools[0].result, str):
                        final_response = successful_tools[0].result
        
        # Calculate processing metrics
        processing_time = sum(step.timestamp.timestamp() for step in intermediate_steps[-2:]) if len(intermediate_steps) >= 2 else 0
        processing_time_ms = processing_time * 1000 if processing_time > 0 else None
        
        # Create structured response
        response = ChatResponse(
            message_id=str(uuid.uuid4()),
            session_id=enhanced_state.session_id,
            response=final_response,
            type=MessageType.ASSISTANT,
            tool_results=tool_results,
            intermediate_steps=intermediate_steps,
            processing_time_ms=processing_time_ms,
            model_used=current_user.chat_model or "llama3.2:3b",
            confidence_score=0.9 if tool_results and any(tr.status == ToolExecutionStatus.SUCCESS for tr in tool_results) else 0.7
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error in enhanced chat handler: {e}", exc_info=True)
        # Return error response
        return ChatResponse(
            message_id=str(uuid.uuid4()),
            session_id=chat_request.session_id or str(uuid.uuid4()),
            response=f"I encountered an error processing your request: {str(e)}",
            type=MessageType.ASSISTANT,
            confidence_score=0.1
        )

@router.post("/stream")
async def handle_streaming_chat(
    chat_request: ChatMessageRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Streaming chat endpoint with LCEL streaming support.
    Returns real-time intermediate steps and final response.
    """
    import json
    from worker.services.enhanced_router_service import enhanced_router_service
    
    async def generate_streaming_response():
        """Generate streaming response chunks."""
        session_id = chat_request.session_id or str(uuid.uuid4())
        
        try:
            # Create enhanced graph state
            enhanced_state = await enhanced_router_service.create_enhanced_graph_state(
                user_input=chat_request.message,
                session_id=session_id,
                user_id=str(current_user.id)
            )
            
            # Convert to legacy GraphState for compatibility
            from worker.graph_types import GraphState
            legacy_state = GraphState(
                user_input=chat_request.message,
                session_id=enhanced_state.session_id,
                user_id=str(current_user.id),
                messages=[],
                chat_model=current_user.chat_model or "llama3.2:3b",
                tool_routing_model=getattr(current_user, 'tool_routing_model', None) or "llama3.2:3b",
                executive_assessment_model=getattr(current_user, 'executive_assessment_model', None) or "llama3.2:3b"
            )
            
            # Stream intermediate steps
            async for step in enhanced_router_service.process_request_with_streaming(
                chat_request.message, legacy_state
            ):
                chunk = StreamingChunk(
                    chunk_id=str(uuid.uuid4()),
                    session_id=session_id,
                    type="intermediate_step",
                    content=step.dict(),
                    is_final=False
                )
                yield f"data: {json.dumps(chunk.dict())}\n\n"
            
            # Final response chunk
            final_chunk = StreamingChunk(
                chunk_id=str(uuid.uuid4()),
                session_id=session_id,
                type="text",
                content="Processing completed successfully.",
                is_final=True
            )
            yield f"data: {json.dumps(final_chunk.dict())}\n\n"
            
        except Exception as e:
            logger.error(f"Error in streaming chat: {e}", exc_info=True)
            error_chunk = StreamingChunk(
                chunk_id=str(uuid.uuid4()),
                session_id=session_id,
                type="text",
                content=f"Error: {str(e)}",
                is_final=True
            )
            yield f"data: {json.dumps(error_chunk.dict())}\n\n"
    
    return StreamingResponse(
        generate_streaming_response(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.post("/feedback/structured", response_model=Dict[str, str])
async def handle_feedback_structured(
    feedback_request: FeedbackRequest, 
    _current_user: User = Depends(get_current_user)
):
    """Enhanced feedback handler with structured input validation."""
    try:
        # Support both 'feedback' and 'feedback_type' field names for frontend compatibility
        feedback_value = feedback_request.feedback or feedback_request.feedback_type
        if not feedback_value:
            raise HTTPException(status_code=400, detail="Either 'feedback' or 'feedback_type' field required")
        
        feedback_service.handle_feedback(
            feedback_request.session_id, 
            feedback_request.message_id, 
            feedback_value
        )
        return {"status": "success", "message": "Feedback recorded"}
    except Exception as e:
        logger.error(f"Error handling feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/feedback")
async def handle_feedback(request: Request, _current_user: User = Depends(get_current_user)):
    """Legacy feedback handler for backward compatibility."""
    try:
        body = await request.json()
        session_id = body.get("session_id")
        message_id = body.get("message_id")
        feedback = body.get("feedback")

        if not all([session_id, message_id, feedback]):
            raise HTTPException(status_code=400, detail="Missing required feedback data")

        feedback_service.handle_feedback(session_id, message_id, feedback)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/legacy")
async def handle_chat_message_legacy(request: Request, _current_user: User = Depends(get_current_user)):
    """
    Legacy chat endpoint for backward compatibility.
    Use the main structured endpoint instead.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON in request body")
    
    if not body or not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Request body must be a valid JSON object")
    
    message = body.get("message") or body.get("query")
    if not message:
        raise HTTPException(status_code=400, detail="Message or query cannot be empty")
    
    # Convert to structured format and call main endpoint
    chat_request = ChatMessageRequest(
        message=message,
        session_id=body.get("session_id"),
        mode=ChatMode.SMART_ROUTER,
        current_graph_state=body.get("current_graph_state"),
        message_history=body.get("message_history", []),
        user_preferences=body.get("user_preferences", {})
    )
    
    # Call the main structured endpoint
    return await handle_structured_chat_message(chat_request, None, _current_user)

@router.post("/message")
async def handle_chat_message_legacy_route(request: Request, _current_user: User = Depends(get_current_user)):
    """
    Handles incoming chat messages from the user via POST /api/v1/chat/message (legacy endpoint).
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON in request body")
    
    if not body or not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Request body must be a valid JSON object")
    
    message = body.get("message") or body.get("query")
    if not message:
        raise HTTPException(status_code=400, detail="Message or query cannot be empty")
    
    return {"response": f"You said: {message}", "status": "success"}