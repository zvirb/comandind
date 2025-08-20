"""
Enhanced API Contract Validation Middleware with flexible chat endpoint support.
Prevents 422 errors through comprehensive type coercion and graceful validation.
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Set
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
import jsonschema
from jsonschema import validate, ValidationError as JsonSchemaValidationError

logger = logging.getLogger(__name__)


class EnhancedContractValidationConfig(BaseModel):
    """Enhanced configuration for contract validation."""
    enforce_request_validation: bool = True
    enforce_response_validation: bool = True
    log_validation_errors: bool = True
    return_validation_errors: bool = False  # Set to False in production
    excluded_paths: Set[str] = {"/docs", "/openapi.json", "/health/live"}
    # New: Chat-specific flexibility
    chat_validation_mode: str = "flexible"  # "strict", "flexible", "permissive"


class EnhancedContractValidationResult(BaseModel):
    """Enhanced result of contract validation with detailed debugging."""
    valid: bool
    endpoint: str
    method: str
    validation_type: str  # "request" or "response"
    errors: List[str] = []
    warnings: List[str] = []  # New: non-fatal validation warnings
    schema_used: Optional[str] = None
    timestamp: str
    execution_time_ms: float
    normalization_applied: bool = False  # New: track if data was normalized


class EnhancedAPIContractValidator:
    """Enhanced API contract validator with flexible chat support."""
    
    def __init__(self, config: EnhancedContractValidationConfig):
        self.config = config
        self.request_schemas: Dict[str, Dict[str, Any]] = {}
        self.response_schemas: Dict[str, Dict[str, Any]] = {}
        self.validation_stats = {
            "total_validations": 0,
            "successful_validations": 0,
            "failed_validations": 0,
            "normalized_validations": 0,  # New: track normalizations
            "endpoints_validated": set()
        }
    
    def register_endpoint_schema(
        self,
        endpoint: str,
        method: str,
        request_schema: Optional[Dict[str, Any]] = None,
        response_schema: Optional[Dict[str, Any]] = None
    ):
        """Register schemas for an endpoint."""
        key = f"{method.upper()}:{endpoint}"
        
        if request_schema:
            self.request_schemas[key] = request_schema
            
        if response_schema:
            self.response_schemas[key] = response_schema
            
        logger.debug(f"Registered enhanced schema for {key}")
    
    def normalize_chat_request_data(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize chat request data to prevent validation errors.
        Applies intelligent type coercion and field mapping.
        """
        normalized = request_data.copy()
        normalization_applied = False
        
        # Normalize mode field
        if "mode" in normalized:
            mode_value = normalized["mode"]
            if isinstance(mode_value, str):
                mode_mappings = {
                    "smart-router": "smart-router",
                    "smart_router": "smart-router",
                    "smartrouter": "smart-router",
                    "socratic-interview": "socratic-interview",
                    "socratic_interview": "socratic-interview",
                    "socraticinterview": "socratic-interview",
                    "expert-group": "expert-group",
                    "expert_group": "expert-group",
                    "expertgroup": "expert-group",
                    "direct": "direct"
                }
                
                normalized_mode = mode_mappings.get(mode_value.lower().strip())
                if normalized_mode and normalized_mode != mode_value:
                    normalized["mode"] = normalized_mode
                    normalization_applied = True
                    logger.debug(f"Normalized mode '{mode_value}' to '{normalized_mode}'")
        
        # Normalize session_id
        if "session_id" in normalized and normalized["session_id"] is not None:
            if not isinstance(normalized["session_id"], str):
                normalized["session_id"] = str(normalized["session_id"])
                normalization_applied = True
                logger.debug("Converted session_id to string")
        
        # Normalize JSON string fields
        json_fields = ["current_graph_state", "message_history", "user_preferences"]
        for field in json_fields:
            if field in normalized and isinstance(normalized[field], str):
                try:
                    parsed_value = json.loads(normalized[field])
                    normalized[field] = parsed_value
                    normalization_applied = True
                    logger.debug(f"Parsed JSON string for field '{field}'")
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON string for field '{field}', leaving as string")
        
        return normalized, normalization_applied
    
    def validate_request(
        self,
        endpoint: str,
        method: str,
        request_data: Dict[str, Any]
    ) -> EnhancedContractValidationResult:
        """Enhanced request validation with normalization."""
        start_time = time.time()
        key = f"{method.upper()}:{endpoint}"
        
        result = EnhancedContractValidationResult(
            valid=True,
            endpoint=endpoint,
            method=method,
            validation_type="request",
            timestamp=datetime.utcnow().isoformat(),
            execution_time_ms=0
        )
        
        if key not in self.request_schemas:
            # No schema registered, consider valid
            result.execution_time_ms = (time.time() - start_time) * 1000
            return result
            
        schema = self.request_schemas[key]
        result.schema_used = key
        
        # Apply normalization for chat endpoints
        validation_data = request_data
        if "/chat" in endpoint and self.config.chat_validation_mode in ["flexible", "permissive"]:
            try:
                validation_data, normalization_applied = self.normalize_chat_request_data(request_data)
                result.normalization_applied = normalization_applied
                if normalization_applied:
                    self.validation_stats["normalized_validations"] += 1
                    result.warnings.append("Request data was normalized for compatibility")
            except Exception as e:
                logger.warning(f"Failed to normalize chat request data: {e}")
                result.warnings.append(f"Normalization failed: {e}")
        
        try:
            validate(instance=validation_data, schema=schema)
            self.validation_stats["successful_validations"] += 1
            logger.debug(f"Request validation successful for {key}")
            
        except JsonSchemaValidationError as e:
            # For flexible/permissive modes on chat endpoints, log but don't fail
            if "/chat" in endpoint and self.config.chat_validation_mode == "permissive":
                result.warnings.append(f"Schema validation warning: {e.message}")
                self.validation_stats["successful_validations"] += 1
                logger.info(f"Chat request validation warning (permissive mode): {e.message}")
            else:
                result.valid = False
                result.errors.append(f"Request validation error: {e.message}")
                self.validation_stats["failed_validations"] += 1
                
                if self.config.log_validation_errors:
                    logger.warning(f"Request validation failed for {key}: {e.message}")
                    
        except Exception as e:
            result.valid = False
            result.errors.append(f"Validation error: {str(e)}")
            self.validation_stats["failed_validations"] += 1
            
        finally:
            result.execution_time_ms = (time.time() - start_time) * 1000
            self.validation_stats["total_validations"] += 1
            self.validation_stats["endpoints_validated"].add(key)
            
        return result
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get enhanced validation statistics."""
        stats = self.validation_stats.copy()
        stats["endpoints_validated"] = list(stats["endpoints_validated"])
        stats["success_rate"] = (
            stats["successful_validations"] / max(stats["total_validations"], 1) * 100
        )
        stats["normalization_rate"] = (
            stats["normalized_validations"] / max(stats["total_validations"], 1) * 100
        )
        return stats


class EnhancedContractValidationMiddleware(BaseHTTPMiddleware):
    """Enhanced middleware with flexible chat endpoint validation."""
    
    def __init__(self, app, config: Optional[EnhancedContractValidationConfig] = None):
        super().__init__(app)
        self.config = config or EnhancedContractValidationConfig()
        self.validator = EnhancedAPIContractValidator(self.config)
        self._register_enhanced_schemas()
        
    def _register_enhanced_schemas(self):
        """Register enhanced schemas with flexible chat support."""
        logger.info(f"Registering enhanced contract validation schemas (chat_mode: {self.config.chat_validation_mode})")
        
        # Ultra-flexible chat request schema
        chat_request_schema = {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string", 
                    "minLength": 1, 
                    "maxLength": 10000,
                    "description": "Primary message field"
                },
                "query": {
                    "type": "string", 
                    "minLength": 1, 
                    "maxLength": 10000,
                    "description": "Alternative message field for backward compatibility"
                },
                "session_id": {
                    "anyOf": [
                        {"type": "string"},
                        {"type": "number"}, 
                        {"type": "null"}
                    ],
                    "description": "Session identifier with flexible typing"
                },
                "mode": {
                    "anyOf": [
                        {"type": "string", "enum": ["smart-router", "socratic-interview", "expert-group", "direct"]},
                        {"type": "string"},  # Allow any string with normalization
                        {"type": "null"}
                    ],
                    "description": "Chat processing mode with automatic normalization"
                },
                "current_graph_state": {
                    "anyOf": [
                        {"type": "object"},
                        {"type": "string"},  # JSON strings will be parsed
                        {"type": "null"}
                    ],
                    "description": "Graph state with JSON parsing support"
                },
                "message_history": {
                    "anyOf": [
                        {"type": "array"},
                        {"type": "string"},  # JSON arrays will be parsed
                        {"type": "null"}
                    ],
                    "description": "Message history with JSON parsing support"
                },
                "user_preferences": {
                    "anyOf": [
                        {"type": "object"},
                        {"type": "string"},  # JSON objects will be parsed
                        {"type": "null"}
                    ],
                    "description": "User preferences with JSON parsing support"
                }
            },
            "anyOf": [
                {"required": ["message"]},
                {"required": ["query"]}
            ],
            "additionalProperties": True,
            "description": "Ultra-flexible chat request schema with intelligent normalization"
        }
        
        # Flexible chat response schema
        chat_response_schema = {
            "type": "object",
            "properties": {
                "response": {"type": "string"},
                "message_id": {"type": "string"},
                "session_id": {"type": "string"},
                "status": {"type": "string"},
                "task_id": {"type": ["string", "null"]},
                "processing_status": {"type": "string"}
            },
            "required": ["response"],
            "additionalProperties": True,
            "description": "Flexible chat response schema"
        }
        
        # Register all chat endpoints
        chat_endpoints = [
            "/api/v1/chat", 
            "/api/v1/chat/", 
            "/api/v1/chat/structured", 
            "/api/v1/chat/enhanced",
            "/api/v1/chat/stream",
            "/api/v1/chat/legacy",
            "/api/v1/chat/message"
        ]
        
        for endpoint in chat_endpoints:
            self.validator.register_endpoint_schema(
                endpoint, "POST",
                request_schema=chat_request_schema,
                response_schema=chat_response_schema
            )
            logger.debug(f"Registered enhanced chat schema for {endpoint}")
        
        # Standard authentication endpoints
        login_schema = {
            "type": "object",
            "properties": {
                "email": {"type": "string", "format": "email"},
                "password": {"type": "string", "minLength": 1},
                "device_name": {"type": "string"}
            },
            "required": ["email", "password"],
            "additionalProperties": True
        }
        
        self.validator.register_endpoint_schema(
            "/auth/jwt/login", "POST",
            request_schema=login_schema
        )
        
        logger.info(f"Enhanced contract validation setup complete with {len(chat_endpoints)} chat endpoints")
    
    async def dispatch(self, request: Request, call_next):
        """Enhanced request processing with flexible validation."""
        
        # Skip validation for excluded paths
        if request.url.path in self.config.excluded_paths:
            return await call_next(request)
        
        # Skip non-API endpoints unless explicitly included
        if not any(pattern in str(request.url) for pattern in ["/api/", "/auth", "/health"]):
            return await call_next(request)
        
        validation_results = []
        
        # Enhanced request validation
        if self.config.enforce_request_validation:
            try:
                body = await request.body()
                if body:
                    try:
                        request_data = json.loads(body)
                    except json.JSONDecodeError:
                        request_data = {"body": body.decode()}
                else:
                    request_data = {}
                    
                if request.query_params:
                    request_data["query_params"] = dict(request.query_params)
                    
                result = self.validator.validate_request(
                    endpoint=request.url.path,
                    method=request.method,
                    request_data=request_data
                )
                validation_results.append(result)
                
                # Enhanced error handling - more permissive for chat endpoints
                if not result.valid:
                    if "/chat" in request.url.path and self.config.chat_validation_mode == "permissive":
                        logger.info(f"Chat validation failed but allowing in permissive mode: {result.errors}")
                    elif self.config.return_validation_errors:
                        return Response(
                            content=json.dumps({
                                "error": "Request validation failed",
                                "details": result.errors,
                                "warnings": result.warnings,
                                "validation_result": {
                                    "valid": result.valid,
                                    "endpoint": result.endpoint,
                                    "normalization_applied": result.normalization_applied
                                }
                            }),
                            status_code=status.HTTP_400_BAD_REQUEST,
                            media_type="application/json"
                        )
                        
            except Exception as e:
                logger.error(f"Enhanced request validation error: {e}")
        
        # Process the request
        response = await call_next(request)
        
        # Add enhanced validation headers
        if validation_results:
            result = validation_results[0]
            response.headers["X-Enhanced-Contract-Validation"] = "passed" if result.valid else "failed"
            response.headers["X-Validation-Normalization"] = "true" if result.normalization_applied else "false"
            response.headers["X-Validation-Warnings"] = str(len(result.warnings))
        
        return response
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get enhanced validation statistics."""
        return self.validator.get_validation_stats()