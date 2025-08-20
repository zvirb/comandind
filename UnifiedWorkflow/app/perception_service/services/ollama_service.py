"""Ollama service integration for LLaVA model inference.

High-performance async client for image analysis and concept vector generation
with comprehensive error handling and performance optimization.
"""

import asyncio
import base64
import hashlib
import time
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin

import httpx
import numpy as np
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

try:
    from ..models import OllamaRequest, OllamaResponse
    from ..config import get_settings
except ImportError:
    # Fallback for direct module execution
    from models import OllamaRequest, OllamaResponse
    from config import get_settings

logger = structlog.get_logger(__name__)


class OllamaError(Exception):
    """Base exception for Ollama-related errors."""
    pass


class OllamaConnectionError(OllamaError):
    """Ollama connection/network errors."""
    pass


class OllamaModelError(OllamaError):
    """Ollama model-related errors."""
    pass


class OllamaService:
    """
    High-performance Ollama service client for LLaVA model integration.
    
    Features:
    - Async HTTP client with connection pooling
    - Automatic retry logic with exponential backoff
    - Vector generation from text descriptions
    - Performance monitoring and caching
    - Comprehensive error handling
    """
    
    def __init__(self, ollama_url: str):
        """Initialize Ollama service client."""
        self.settings = get_settings()
        self.ollama_url = ollama_url
        self.model_name = self.settings.ollama_model
        
        # HTTP client with optimized settings
        timeout = httpx.Timeout(self.settings.ollama_timeout)
        
        limits = httpx.Limits(
            max_connections=20,
            max_keepalive_connections=10
        )
        
        self.client = httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            follow_redirects=True
        )
        
        # Model readiness cache
        self._model_ready = False
        self._model_check_time = 0
        self._model_check_interval = 300  # 5 minutes
        
        logger.info("Ollama service initialized", 
                   url=ollama_url, 
                   model=self.model_name)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
        logger.info("Ollama service client closed")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(httpx.RequestError)
    )
    async def health_check(self) -> bool:
        """Check if Ollama service is healthy and responsive."""
        try:
            url = urljoin(self.ollama_url, "/api/tags")
            response = await self.client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                logger.debug("Ollama health check successful", 
                           models_available=len(data.get('models', [])))
                return True
            else:
                logger.warning("Ollama health check failed", 
                             status_code=response.status_code,
                             response=response.text[:200])
                return False
                
        except httpx.RequestError as e:
            logger.error("Ollama health check connection error", error=str(e))
            raise OllamaConnectionError(f"Failed to connect to Ollama: {e}")
        except Exception as e:
            logger.error("Ollama health check unexpected error", error=str(e))
            return False
    
    async def is_model_ready(self) -> bool:
        """Check if the LLaVA model is ready for inference."""
        current_time = time.time()
        
        # Use cached result if recent
        if (self._model_ready and 
            current_time - self._model_check_time < self._model_check_interval):
            return self._model_ready
        
        try:
            url = urljoin(self.ollama_url, "/api/tags")
            response = await self.client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                models = data.get('models', [])
                
                # Check if our model is available
                model_available = any(
                    model.get('name', '').startswith(self.model_name) 
                    for model in models
                )
                
                self._model_ready = model_available
                self._model_check_time = current_time
                
                if not model_available:
                    available_models = [m.get('name') for m in models]
                    logger.warning("LLaVA model not found", 
                                 required_model=self.model_name,
                                 available_models=available_models)
                
                return model_available
            else:
                logger.error("Failed to check model availability", 
                           status_code=response.status_code)
                return False
                
        except Exception as e:
            logger.error("Error checking model readiness", error=str(e))
            return False
    
    async def ensure_model_ready(self) -> None:
        """Ensure the LLaVA model is available, pull if necessary."""
        if await self.is_model_ready():
            return
        
        logger.info("Pulling LLaVA model", model=self.model_name)
        
        try:
            url = urljoin(self.ollama_url, "/api/pull")
            data = {"name": self.model_name}
            
            timeout = httpx.Timeout(600.0)
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=data)
                
                if response.status_code == 200:
                    logger.info("LLaVA model pull completed", model=self.model_name)
                    self._model_ready = True
                    self._model_check_time = time.time()
                else:
                    raise OllamaModelError(f"Failed to pull model: {response.text}")
                    
        except Exception as e:
            logger.error("Failed to ensure model ready", error=str(e))
            raise OllamaModelError(f"Model preparation failed: {e}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException))
    )
    async def generate_description(
        self, 
        image_data: str, 
        prompt: Optional[str] = None,
        request_id: Optional[int] = None
    ) -> str:
        """Generate text description of image using LLaVA model."""
        
        if not await self.is_model_ready():
            await self.ensure_model_ready()
        
        # Use custom prompt or default
        analysis_prompt = prompt or self.settings.default_prompt
        
        request_data = OllamaRequest(
            model=self.model_name,
            prompt=analysis_prompt,
            images=[image_data],
            stream=False,
            options={
                "temperature": 0.1,
                "top_p": 0.9,
                "max_tokens": 512,
                "stop": ["Human:", "Assistant:", "\n\n\n"]
            }
        )
        
        start_time = time.time()
        
        try:
            url = urljoin(self.ollama_url, "/api/generate")
            
            response = await self.client.post(
                url,
                json=request_data.dict(),
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                error_detail = response.text[:500]
                logger.error("Ollama generation failed", 
                           status_code=response.status_code,
                           error=error_detail,
                           request_id=request_id)
                raise OllamaModelError(f"Generation failed: {error_detail}")
            
            response_data = OllamaResponse(**response.json())
            generation_time = time.time() - start_time
            
            logger.info("Image description generated",
                       request_id=request_id,
                       generation_time_ms=round(generation_time * 1000, 2),
                       response_length=len(response_data.response),
                       total_duration_ms=response_data.total_duration // 1_000_000 if response_data.total_duration else None)
            
            return response_data.response.strip()
            
        except httpx.TimeoutException:
            logger.error("Ollama request timeout", 
                        request_id=request_id,
                        timeout=self.settings.ollama_timeout)
            raise OllamaError("Image analysis timed out")
            
        except httpx.RequestError as e:
            logger.error("Ollama request error", error=str(e), request_id=request_id)
            raise OllamaConnectionError(f"Request failed: {e}")
            
        except Exception as e:
            logger.error("Unexpected error in generation", 
                        error=str(e), request_id=request_id)
            raise OllamaError(f"Generation error: {e}")
    
    def _text_to_vector(self, text: str) -> List[float]:
        """
        Convert text description to 1536-dimension vector.
        
        Uses a combination of techniques:
        1. Character-level encoding
        2. Word-level hashing
        3. Semantic features extraction
        4. Normalization and padding to 1536 dimensions
        """
        
        # Initialize vector
        vector = np.zeros(1536, dtype=np.float32)
        
        if not text:
            return vector.tolist()
        
        # Clean and normalize text
        text = text.lower().strip()
        words = text.split()
        
        # 1. Character-level features (first 256 dims)
        char_counts = np.zeros(256, dtype=np.float32)
        for char in text[:1000]:  # Limit length
            char_counts[ord(char) % 256] += 1
        
        # Normalize character counts
        if char_counts.sum() > 0:
            char_counts = char_counts / char_counts.sum()
        
        vector[:256] = char_counts
        
        # 2. Word-level hash features (dims 256-768)
        word_features = np.zeros(512, dtype=np.float32)
        for word in words[:100]:  # Limit words
            # Use multiple hash functions for better distribution
            for i, seed in enumerate([42, 123, 456, 789]):
                hash_val = int(hashlib.md5(f"{word}_{seed}".encode()).hexdigest(), 16)
                idx = (hash_val % 128) + (i * 128)
                word_features[idx] += 1.0
        
        # Normalize word features
        if word_features.sum() > 0:
            word_features = word_features / np.sqrt(word_features.sum())
        
        vector[256:768] = word_features
        
        # 3. Semantic features (dims 768-1280)
        semantic_features = np.zeros(512, dtype=np.float32)
        
        # Length features
        semantic_features[0] = min(len(text) / 1000.0, 1.0)
        semantic_features[1] = min(len(words) / 100.0, 1.0)
        
        # Common visual concept indicators
        visual_concepts = [
            'person', 'people', 'man', 'woman', 'child', 'face', 'hand', 'eye',
            'car', 'vehicle', 'building', 'house', 'tree', 'sky', 'water', 'road',
            'animal', 'dog', 'cat', 'bird', 'flower', 'food', 'table', 'chair',
            'red', 'blue', 'green', 'black', 'white', 'yellow', 'color', 'bright',
            'large', 'small', 'standing', 'sitting', 'walking', 'running', 'outdoor',
            'indoor', 'background', 'foreground', 'center', 'left', 'right'
        ]
        
        for i, concept in enumerate(visual_concepts[:100]):
            if concept in text:
                semantic_features[i + 2] = 1.0
        
        # N-gram features
        bigrams = [text[i:i+2] for i in range(len(text)-1)]
        for bigram in bigrams[:200]:
            hash_val = int(hashlib.md5(bigram.encode()).hexdigest(), 16)
            idx = hash_val % 300
            semantic_features[idx + 102] = 1.0
        
        vector[768:1280] = semantic_features
        
        # 4. Statistical features (dims 1280-1536)
        stat_features = np.zeros(256, dtype=np.float32)
        
        # Text statistics
        if len(text) > 0:
            stat_features[0] = len(set(text)) / len(text)  # Character diversity
            stat_features[1] = text.count(' ') / len(text)  # Space ratio
            stat_features[2] = sum(c.isupper() for c in text) / len(text)  # Uppercase ratio
            stat_features[3] = sum(c.isdigit() for c in text) / len(text)  # Digit ratio
        
        if len(words) > 0:
            stat_features[4] = len(set(words)) / len(words)  # Word diversity
            stat_features[5] = sum(len(word) for word in words) / len(words)  # Avg word length
        
        # Position-based encoding for remaining dimensions
        for i in range(6, 256):
            hash_val = int(hashlib.md5(f"{text}_{i}".encode()).hexdigest(), 16)
            stat_features[i] = (hash_val % 1000) / 1000.0
        
        vector[1280:1536] = stat_features
        
        # Final normalization
        vector_norm = np.linalg.norm(vector)
        if vector_norm > 0:
            vector = vector / vector_norm
        
        return vector.tolist()
    
    async def generate_concept_vector(
        self,
        image_data: str,
        image_format: str,
        prompt: Optional[str] = None,
        request_id: Optional[int] = None
    ) -> List[float]:
        """
        Generate concept vector from image data.
        
        Process:
        1. Analyze image with LLaVA to get description
        2. Convert description to 1536-dimension vector
        3. Return normalized vector for similarity search
        """
        
        start_time = time.time()
        
        try:
            # Generate image description
            description = await self.generate_description(
                image_data=image_data,
                prompt=prompt,
                request_id=request_id
            )
            
            # Convert description to vector
            vector = self._text_to_vector(description)
            
            # Validate vector
            if len(vector) != 1536:
                raise ValueError(f"Vector dimension mismatch: {len(vector)} != 1536")
            
            # Check for NaN/inf values
            if any(not np.isfinite(v) for v in vector):
                logger.warning("Vector contains non-finite values, using fallback",
                             request_id=request_id)
                vector = [0.0] * 1536
            
            total_time = time.time() - start_time
            
            logger.info("Concept vector generated successfully",
                       request_id=request_id,
                       description_length=len(description),
                       vector_norm=np.linalg.norm(vector),
                       total_time_ms=round(total_time * 1000, 2))
            
            return vector
            
        except Exception as e:
            logger.error("Failed to generate concept vector",
                        error=str(e),
                        request_id=request_id,
                        exc_info=True)
            raise
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()