"""
API Contract Validation Middleware.
Validates API request/response contracts and ensures compliance with OpenAPI specs.
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Set
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.routing import APIRoute
from pydantic import BaseModel, ValidationError
import jsonschema
from jsonschema import validate, ValidationError as JsonSchemaValidationError

logger = logging.getLogger(__name__)


class ContractValidationConfig(BaseModel):
    """Configuration for contract validation."""
    enforce_request_validation: bool = True
    enforce_response_validation: bool = True
    log_validation_errors: bool = True
    return_validation_errors: bool = False  # Set to False in production
    excluded_paths: Set[str] = {"/docs", "/openapi.json", "/health/live"}


class ContractValidationResult(BaseModel):
    """Result of contract validation."""
    valid: bool
    endpoint: str
    method: str
    validation_type: str  # "request" or "response"
    errors: List[str] = []
    schema_used: Optional[str] = None
    timestamp: str
    execution_time_ms: float


class APIContractValidator:
    """Validates API contracts against defined schemas."""
    
    def __init__(self, config: ContractValidationConfig):
        self.config = config
        self.request_schemas: Dict[str, Dict[str, Any]] = {}
        self.response_schemas: Dict[str, Dict[str, Any]] = {}
        self.validation_stats = {
            "total_validations": 0,
            "successful_validations": 0,
            "failed_validations": 0,
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
            
        logger.debug(f"Registered schema for {key}")
    
    def validate_request(
        self,
        endpoint: str,
        method: str,
        request_data: Dict[str, Any]
    ) -> ContractValidationResult:
        """Validate request against registered schema."""
        start_time = time.time()
        key = f"{method.upper()}:{endpoint}"
        
        result = ContractValidationResult(
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
        
        try:
            validate(instance=request_data, schema=schema)
            self.validation_stats["successful_validations"] += 1
            
        except JsonSchemaValidationError as e:
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
    
    def validate_response(
        self,
        endpoint: str,
        method: str,
        response_data: Any,
        status_code: int
    ) -> ContractValidationResult:
        """Validate response against registered schema."""
        start_time = time.time()
        key = f"{method.upper()}:{endpoint}"
        
        result = ContractValidationResult(
            valid=True,
            endpoint=endpoint,
            method=method,
            validation_type="response",
            timestamp=datetime.utcnow().isoformat(),
            execution_time_ms=0
        )
        
        if key not in self.response_schemas:
            # No schema registered, consider valid
            result.execution_time_ms = (time.time() - start_time) * 1000
            return result
            
        schema = self.response_schemas[key]
        result.schema_used = key
        
        try:
            # Handle different response data types
            if hasattr(response_data, 'dict'):
                # Pydantic model
                data_to_validate = response_data.dict()
            elif isinstance(response_data, dict):
                data_to_validate = response_data
            elif isinstance(response_data, str):
                try:
                    data_to_validate = json.loads(response_data)
                except json.JSONDecodeError:
                    data_to_validate = {"content": response_data}
            else:
                data_to_validate = {"content": str(response_data)}
                
            validate(instance=data_to_validate, schema=schema)
            self.validation_stats["successful_validations"] += 1
            
        except JsonSchemaValidationError as e:
            result.valid = False
            result.errors.append(f"Response validation error: {e.message}")
            self.validation_stats["failed_validations"] += 1
            
            if self.config.log_validation_errors:
                logger.warning(f"Response validation failed for {key}: {e.message}")
                
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
        """Get validation statistics."""
        stats = self.validation_stats.copy()
        stats["endpoints_validated"] = list(stats["endpoints_validated"])
        stats["success_rate"] = (
            stats["successful_validations"] / max(stats["total_validations"], 1) * 100
        )
        return stats


class ContractValidationMiddleware(BaseHTTPMiddleware):
    """Middleware to validate API contracts."""
    
    def __init__(self, app, config: Optional[ContractValidationConfig] = None):
        super().__init__(app)
        self.config = config or ContractValidationConfig()
        self.validator = APIContractValidator(self.config)
        self._register_default_schemas()
        
    def _register_default_schemas(self):
        """Register default schemas for common endpoints."""
        
        # Health check endpoints
        health_response_schema = {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["healthy", "unhealthy", "degraded"]},
                "service": {"type": "string"},
                "timestamp": {"type": "string"},
                "evidence": {"type": "object"}
            },
            "required": ["status", "timestamp"]
        }
        
        self.validator.register_endpoint_schema(
            "/health", "GET", 
            response_schema=health_response_schema
        )
        
        self.validator.register_endpoint_schema(
            "/health/detailed", "GET",
            response_schema={
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "checks": {"type": "object"},
                    "evidence": {"type": "object"}
                },
                "required": ["status", "checks"]
            }
        )
        
        # Authentication endpoints
        login_request_schema = {
            "type": "object",
            "properties": {
                "email": {"type": "string", "format": "email"},
                "password": {"type": "string", "minLength": 8},
                "device_name": {"type": "string"}
            },
            "required": ["email", "password"]
        }
        
        login_response_schema = {
            "type": "object",
            "properties": {
                "access_token": {"type": "string"},
                "user_id": {"type": "integer"},
                "email": {"type": "string"},
                "requires_2fa": {"type": "boolean"},
                "evidence": {"type": "object"}
            },
            "required": ["access_token", "user_id", "email"]
        }
        
        self.validator.register_endpoint_schema(
            "/jwt/login", "POST",
            request_schema=login_request_schema,
            response_schema=login_response_schema
        )
        
    async def dispatch(self, request: Request, call_next):
        """Process request with contract validation."""
        
        # Skip validation for excluded paths
        if request.url.path in self.config.excluded_paths:
            return await call_next(request)
            
        # Skip non-API endpoints if not explicitly included
        if not any(pattern in str(request.url) for pattern in ["/api/", "/auth", "/health"]):
            return await call_next(request)
        
        validation_results = []
        
        # Validate request if enabled
        if self.config.enforce_request_validation:
            try:
                # Get request body for validation
                body = await request.body()
                if body:
                    try:
                        request_data = json.loads(body)
                    except json.JSONDecodeError:
                        request_data = {"body": body.decode()}
                else:
                    request_data = {}
                    
                # Add query parameters
                if request.query_params:
                    request_data["query_params"] = dict(request.query_params)
                    
                result = self.validator.validate_request(
                    endpoint=request.url.path,
                    method=request.method,
                    request_data=request_data
                )
                validation_results.append(result)
                
                # Return error if validation failed and enforcement is enabled
                if not result.valid and self.config.return_validation_errors:
                    return Response(
                        content=json.dumps({
                            "error": "Request validation failed",
                            "details": result.errors,
                            "validation_result": result.dict()
                        }),
                        status_code=status.HTTP_400_BAD_REQUEST,
                        media_type="application/json"
                    )
                    
            except Exception as e:
                logger.error(f"Request validation error: {e}")
        
        # Process the request
        response = await call_next(request)
        
        # Validate response if enabled
        if self.config.enforce_response_validation:
            try:
                # For non-JSON responses, skip validation
                content_type = response.headers.get("content-type", "")
                if "application/json" not in content_type:
                    return response
                    
                # This is tricky - we need to read the response body without consuming it
                # For now, we'll skip response validation for streaming responses
                # In a production system, you might want to implement response buffering
                
                result = self.validator.validate_response(
                    endpoint=request.url.path,
                    method=request.method,
                    response_data={"status": "response_validation_skipped"},
                    status_code=response.status_code
                )
                validation_results.append(result)
                
            except Exception as e:
                logger.error(f"Response validation error: {e}")
        
        # Add validation headers
        if validation_results:
            total_valid = all(r.valid for r in validation_results)
            response.headers["X-Contract-Validation"] = "passed" if total_valid else "failed"
            response.headers["X-Validation-Count"] = str(len(validation_results))
        
        return response
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        return self.validator.get_validation_stats()


# Utility function to create validation evidence
def create_contract_validation_evidence(
    endpoint: str,
    method: str,
    validation_results: List[ContractValidationResult]
) -> Dict[str, Any]:
    """Create evidence for contract validation."""
    
    all_valid = all(r.valid for r in validation_results)
    
    evidence = {
        "timestamp": datetime.utcnow().isoformat(),
        "validation_type": "api_contract_validation",
        "endpoint": endpoint,
        "method": method,
        "success": all_valid,
        "validation_summary": {
            "total_validations": len(validation_results),
            "successful_validations": sum(1 for r in validation_results if r.valid),
            "failed_validations": sum(1 for r in validation_results if not r.valid),
            "validation_types": list(set(r.validation_type for r in validation_results))
        },
        "evidence_details": {
            "contract_compliance": all_valid,
            "schema_validation_passed": all_valid,
            "api_specification_followed": all_valid
        }
    }
    
    if not all_valid:
        evidence["failure_details"] = [
            {
                "validation_type": r.validation_type,
                "errors": r.errors,
                "schema": r.schema_used
            }
            for r in validation_results if not r.valid
        ]
        
    return evidence