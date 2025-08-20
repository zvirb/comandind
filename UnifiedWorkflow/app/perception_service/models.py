"""Pydantic models for request/response validation.

Comprehensive data models with validation for the Perception Service API.
"""

import base64
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class ImageFormat(str, Enum):
    """Supported image formats."""
    JPEG = "jpeg"
    JPG = "jpg"  
    PNG = "png"
    WEBP = "webp"
    GIF = "gif"


class ConceptualizeRequest(BaseModel):
    """Request model for image conceptualization."""
    
    image_data: str = Field(
        ...,
        description="Base64-encoded image data",
        example="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    )
    
    format: ImageFormat = Field(
        default=ImageFormat.JPEG,
        description="Image format (jpeg, png, webp, gif)"
    )
    
    prompt: Optional[str] = Field(
        default=None,
        description="Optional custom prompt for image analysis",
        max_length=1000
    )
    
    max_tokens: Optional[int] = Field(
        default=512,
        description="Maximum tokens for LLaVA response",
        ge=1,
        le=2048
    )
    
    temperature: Optional[float] = Field(
        default=0.1,
        description="Temperature for LLaVA generation (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    
    @validator('image_data')
    def validate_image_data(cls, v):
        """Validate base64 image data."""
        if not v:
            raise ValueError("Image data cannot be empty")
        
        try:
            # Validate base64 encoding
            decoded = base64.b64decode(v)
            
            # Check minimum size (100 bytes)
            if len(decoded) < 100:
                raise ValueError("Image data too small")
            
            # Check maximum size (10MB default)
            max_size = 10 * 1024 * 1024  # 10MB
            if len(decoded) > max_size:
                raise ValueError(f"Image data too large (max {max_size} bytes)")
            
            # Basic format validation by checking headers
            if decoded.startswith(b'\xFF\xD8\xFF'):
                # JPEG
                pass
            elif decoded.startswith(b'\x89PNG\r\n\x1a\n'):
                # PNG
                pass
            elif decoded.startswith(b'RIFF') and b'WEBP' in decoded[:20]:
                # WebP
                pass
            elif decoded.startswith(b'GIF87a') or decoded.startswith(b'GIF89a'):
                # GIF
                pass
            else:
                raise ValueError("Unsupported image format or corrupted data")
            
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError("Invalid base64 image data")
        
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "image_data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
                "format": "png",
                "prompt": "Describe this image focusing on objects and visual elements",
                "max_tokens": 256,
                "temperature": 0.1
            }
        }


class ConceptualizeResponse(BaseModel):
    """Response model for image conceptualization."""
    
    vector: List[float] = Field(
        ...,
        description="1536-dimension concept vector",
        min_items=1536,
        max_items=1536
    )
    
    dimensions: int = Field(
        ...,
        description="Vector dimensions (should be 1536)",
        example=1536
    )
    
    processing_time_ms: float = Field(
        ...,
        description="Processing time in milliseconds",
        ge=0
    )
    
    request_id: str = Field(
        ...,
        description="Unique request identifier"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata about the processing"
    )
    
    @validator('vector')
    def validate_vector_dimensions(cls, v):
        """Ensure vector has exactly 1536 dimensions."""
        if len(v) != 1536:
            raise ValueError(f"Vector must have exactly 1536 dimensions, got {len(v)}")
        
        # Validate all values are finite numbers
        for i, val in enumerate(v):
            if not isinstance(val, (int, float)) or not (-1e10 < val < 1e10):
                raise ValueError(f"Invalid vector value at index {i}: {val}")
        
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "vector": [0.1] * 1536,  # Simplified example
                "dimensions": 1536,
                "processing_time_ms": 1250.5,
                "request_id": "12345",
                "metadata": {
                    "model": "llava",
                    "prompt_tokens": 15,
                    "completion_tokens": 128
                }
            }
        }


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str = Field(
        ...,
        description="Overall service status",
        pattern="^(healthy|unhealthy|degraded)$"
    )
    
    timestamp: float = Field(
        ...,
        description="Health check timestamp (Unix time)",
        example=1641024000.0
    )
    
    checks: Dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed component health checks"
    )
    
    version: Optional[str] = Field(
        default="1.0.0",
        description="Service version"
    )
    
    uptime_seconds: Optional[float] = Field(
        default=None,
        description="Service uptime in seconds",
        ge=0
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": 1641024000.0,
                "checks": {
                    "ollama_service": {
                        "healthy": True,
                        "latency_ms": 45.2
                    },
                    "llava_model": {
                        "ready": True
                    }
                },
                "version": "1.0.0",
                "uptime_seconds": 3600.0
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    detail: str = Field(
        ...,
        description="Error description"
    )
    
    error_code: Optional[str] = Field(
        default=None,
        description="Specific error code"
    )
    
    timestamp: float = Field(
        ...,
        description="Error timestamp"
    )
    
    request_id: Optional[str] = Field(
        default=None,
        description="Request identifier"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Invalid image format",
                "error_code": "INVALID_FORMAT",
                "timestamp": 1641024000.0,
                "request_id": "12345"
            }
        }


# Utility models for internal processing

class OllamaRequest(BaseModel):
    """Internal model for Ollama API requests."""
    
    model: str = Field(default="llava")
    prompt: str = Field(...)
    images: List[str] = Field(default_factory=list)
    stream: bool = Field(default=False)
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)


class OllamaResponse(BaseModel):
    """Internal model for Ollama API responses."""
    
    response: str = Field(...)
    model: str = Field(...)
    created_at: str = Field(...)
    done: bool = Field(...)
    context: Optional[List[int]] = Field(default=None)
    total_duration: Optional[int] = Field(default=None)
    load_duration: Optional[int] = Field(default=None)
    prompt_eval_count: Optional[int] = Field(default=None)
    prompt_eval_duration: Optional[int] = Field(default=None)
    eval_count: Optional[int] = Field(default=None)
    eval_duration: Optional[int] = Field(default=None)