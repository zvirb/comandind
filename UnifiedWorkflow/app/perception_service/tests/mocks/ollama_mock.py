"""Comprehensive Ollama service mocks for testing.

Provides realistic mock implementations of Ollama API responses
for consistent testing across different scenarios.
"""

import asyncio
import base64
import json
import time
from typing import Dict, Any, List, Optional, Union
from unittest.mock import AsyncMock
import numpy as np
from faker import Faker

fake = Faker()


class OllamaMockResponse:
    """Mock HTTP response for Ollama API calls."""
    
    def __init__(self, status_code: int, data: Dict[str, Any]):
        self.status_code = status_code
        self.data = data
    
    async def json(self):
        """Return JSON data."""
        return self.data
    
    @property
    def text(self):
        """Return text representation."""
        return json.dumps(self.data)


class OllamaMockService:
    """Comprehensive mock for Ollama service with realistic behaviors."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize mock with configuration options."""
        self.config = config or {}
        self.base_url = self.config.get("base_url", "http://localhost:11434")
        self.model = self.config.get("model", "llava")
        self.timeout = self.config.get("timeout", 30.0)
        
        # Mock state
        self.is_healthy = self.config.get("healthy", True)
        self.model_ready = self.config.get("model_ready", True)
        self.response_delay = self.config.get("response_delay", 0.0)
        self.error_rate = self.config.get("error_rate", 0.0)
        self.call_count = 0
        
        # Mock data
        self.mock_models = self.config.get("available_models", [
            {"name": "llava:latest", "size": 4000000000},
            {"name": "llava:13b", "size": 7300000000}
        ])
    
    async def health_check(self) -> bool:
        """Mock health check."""
        await self._simulate_delay()
        self.call_count += 1
        
        if self._should_error():
            raise RuntimeError("Health check failed")
        
        return self.is_healthy
    
    async def is_model_ready(self) -> bool:
        """Mock model readiness check."""
        await self._simulate_delay()
        self.call_count += 1
        
        if not self.is_healthy:
            return False
        
        return self.model_ready
    
    async def ensure_model_ready(self) -> None:
        """Mock model readiness ensuring."""
        await self._simulate_delay()
        self.call_count += 1
        
        if not self.is_healthy:
            raise RuntimeError("Service unhealthy")
        
        if not self.model_ready:
            # Simulate model pull
            await asyncio.sleep(0.1)  # Simulate pull delay
            self.model_ready = True
    
    async def generate_concept_vector(
        self,
        image_data: str,
        image_format: str,
        prompt: str = None,
        request_id: str = None
    ) -> List[float]:
        """Mock concept vector generation."""
        await self._simulate_delay()
        self.call_count += 1
        
        if self._should_error():
            raise RuntimeError("Vector generation failed")
        
        # Validate inputs
        if not image_data:
            raise ValueError("Invalid image data")
        
        if image_format not in ["jpeg", "png", "webp"]:
            raise ValueError(f"Unsupported image format: {image_format}")
        
        try:
            # Validate base64
            base64.b64decode(image_data)
        except Exception:
            raise ValueError("Invalid base64 image data")
        
        # Generate deterministic vector based on image data hash
        vector = self._generate_deterministic_vector(image_data, prompt)
        
        return vector
    
    async def generate_text(
        self,
        prompt: str,
        context: List[int] = None,
        request_id: str = None
    ) -> Dict[str, Any]:
        """Mock text generation."""
        await self._simulate_delay()
        self.call_count += 1
        
        if self._should_error():
            raise RuntimeError("Text generation failed")
        
        return {
            "response": self._generate_mock_text(prompt),
            "done": True,
            "context": context or list(range(100)),
            "created_at": fake.iso8601(),
            "model": self.model,
            "total_duration": fake.random_int(min=1000000000, max=5000000000),
            "load_duration": fake.random_int(min=100000000, max=1000000000),
            "prompt_eval_duration": fake.random_int(min=500000000, max=2000000000),
            "eval_duration": fake.random_int(min=1000000000, max=3000000000)
        }
    
    async def generate_embeddings(
        self,
        text: str,
        request_id: str = None
    ) -> List[float]:
        """Mock text embeddings generation."""
        await self._simulate_delay()
        self.call_count += 1
        
        if self._should_error():
            raise RuntimeError("Embeddings generation failed")
        
        # Generate deterministic embeddings based on text hash
        return self._generate_deterministic_vector(text)
    
    def get_mock_http_client(self):
        """Get HTTP client mock for direct API testing."""
        http_mock = AsyncMock()
        
        async def mock_get(*args, **kwargs):
            url = args[0] if args else kwargs.get("url", "")
            
            if "/api/tags" in url:
                return OllamaMockResponse(200, {"models": self.mock_models})
            
            return OllamaMockResponse(404, {"error": "Not found"})
        
        async def mock_post(*args, **kwargs):
            url = args[0] if args else kwargs.get("url", "")
            
            if "/api/generate" in url:
                return OllamaMockResponse(200, {
                    "response": fake.text(max_nb_chars=200),
                    "done": True
                })
            elif "/api/embeddings" in url:
                return OllamaMockResponse(200, {
                    "embedding": np.random.rand(1536).tolist()
                })
            elif "/api/pull" in url:
                return OllamaMockResponse(200, {"status": "success"})
            
            return OllamaMockResponse(400, {"error": "Bad request"})
        
        http_mock.get = mock_get
        http_mock.post = mock_post
        http_mock.__aenter__ = AsyncMock(return_value=http_mock)
        http_mock.__aexit__ = AsyncMock(return_value=None)
        
        return http_mock
    
    async def close(self):
        """Mock cleanup method."""
        pass
    
    # Helper methods
    
    async def _simulate_delay(self):
        """Simulate network delay."""
        if self.response_delay > 0:
            await asyncio.sleep(self.response_delay)
    
    def _should_error(self) -> bool:
        """Determine if this call should error based on error rate."""
        if self.error_rate <= 0:
            return False
        
        return np.random.random() < self.error_rate
    
    def _generate_deterministic_vector(
        self,
        input_data: str,
        prompt: str = None
    ) -> List[float]:
        """Generate deterministic vector based on input."""
        # Use hash of input for deterministic results
        import hashlib
        
        hash_input = f"{input_data}_{prompt or ''}"
        hash_obj = hashlib.sha256(hash_input.encode())
        
        # Use hash bytes to seed random generator for deterministic results
        seed = int(hash_obj.hexdigest()[:8], 16)
        rng = np.random.RandomState(seed)
        
        # Generate vector with specific characteristics
        vector = rng.normal(0, 0.1, 1536).tolist()
        
        # Normalize to reasonable range
        vector = [max(min(v, 1.0), -1.0) for v in vector]
        
        return vector
    
    def _generate_mock_text(self, prompt: str) -> str:
        """Generate mock text response based on prompt."""
        prompt_lower = prompt.lower()
        
        if "describe" in prompt_lower and "image" in prompt_lower:
            return fake.sentence(nb_words=15) + " The image contains various visual elements including shapes, colors, and patterns."
        elif "analyze" in prompt_lower:
            return fake.sentence(nb_words=20) + " This analysis reveals several key characteristics and features."
        elif "identify" in prompt_lower:
            return fake.sentence(nb_words=12) + " Several distinct elements can be identified in the content."
        else:
            return fake.text(max_nb_chars=200)


# Predefined mock configurations for common scenarios

MOCK_CONFIGS = {
    "healthy_fast": {
        "healthy": True,
        "model_ready": True,
        "response_delay": 0.1,
        "error_rate": 0.0
    },
    
    "healthy_slow": {
        "healthy": True,
        "model_ready": True,
        "response_delay": 2.0,
        "error_rate": 0.0
    },
    
    "unhealthy": {
        "healthy": False,
        "model_ready": False,
        "response_delay": 0.0,
        "error_rate": 0.0
    },
    
    "unreliable": {
        "healthy": True,
        "model_ready": True,
        "response_delay": 0.5,
        "error_rate": 0.1  # 10% error rate
    },
    
    "model_not_ready": {
        "healthy": True,
        "model_ready": False,
        "response_delay": 0.2,
        "error_rate": 0.0
    }
}


def create_ollama_mock(config_name: str = "healthy_fast") -> OllamaMockService:
    """Create Ollama mock with predefined configuration."""
    config = MOCK_CONFIGS.get(config_name, MOCK_CONFIGS["healthy_fast"])
    return OllamaMockService(config)


def create_custom_ollama_mock(**kwargs) -> OllamaMockService:
    """Create Ollama mock with custom configuration."""
    return OllamaMockService(kwargs)