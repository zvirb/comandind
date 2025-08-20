"""Ollama service for LLM-powered memory processing.

Provides text extraction, reconciliation, and vector generation capabilities
using Ollama's llama3.2:3b model with optimized prompting and error handling.
"""

import asyncio
import json
import time
from typing import List, Dict, Any, Optional, Tuple

import httpx
import structlog

logger = structlog.get_logger(__name__)


class OllamaService:
    """Ollama LLM service for memory operations.
    
    Handles text processing, memory extraction, reconciliation,
    and vector generation with the llama3.2:3b model.
    """
    
    def __init__(
        self,
        url: str,
        model: str = "llama3.2:3b", 
        timeout: int = 120,
        max_retries: int = 3
    ):
        """Initialize Ollama service.
        
        Args:
            url: Ollama server URL
            model: Model name to use
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.url = url.rstrip('/')
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        
        # HTTP client with custom timeout
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10
            )
        )
        
        logger.info("Initializing Ollama service", 
                   url=url, 
                   model=model,
                   timeout=timeout)
    
    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()
        logger.info("Ollama client connection closed")
    
    async def health_check(self) -> bool:
        """Check if Ollama service is healthy and model is available."""
        try:
            # Check service health
            response = await self.client.get(f"{self.url}/api/tags")
            if response.status_code != 200:
                logger.warning("Ollama service unhealthy", status_code=response.status_code)
                return False
            
            # Check if our model is available
            models_data = response.json()
            available_models = [model["name"] for model in models_data.get("models", [])]
            
            if self.model not in available_models:
                logger.warning("Model not available", 
                             model=self.model,
                             available=available_models)
                return False
            
            logger.debug("Ollama health check passed", model=self.model)
            return True
            
        except Exception as e:
            logger.error("Ollama health check failed", error=str(e))
            return False
    
    async def ensure_model_ready(self) -> None:
        """Ensure the model is available, pull if necessary."""
        try:
            # First check if model exists
            if await self.health_check():
                logger.info("Model already available", model=self.model)
                return
            
            logger.info("Pulling model", model=self.model)
            
            # Pull the model
            response = await self.client.post(
                f"{self.url}/api/pull",
                json={"name": self.model},
                timeout=300  # Extended timeout for model pulling
            )
            
            if response.status_code == 200:
                logger.info("Model pull completed", model=self.model)
            else:
                logger.error("Failed to pull model", 
                           model=self.model,
                           status_code=response.status_code,
                           response=response.text)
                raise RuntimeError(f"Failed to pull model {self.model}")
                
        except Exception as e:
            logger.error("Failed to ensure model ready", model=self.model, error=str(e))
            raise
    
    async def _make_request_with_retry(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic."""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                response = await self.client.post(
                    f"{self.url}{endpoint}",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    logger.warning("Ollama request failed", 
                                 attempt=attempt + 1,
                                 error=error_msg,
                                 request_id=request_id)
                    last_error = error_msg
                    
            except httpx.TimeoutException as e:
                error_msg = f"Request timeout: {str(e)}"
                logger.warning("Ollama request timeout", 
                             attempt=attempt + 1,
                             error=error_msg,
                             request_id=request_id)
                last_error = error_msg
                
            except Exception as e:
                error_msg = f"Request error: {str(e)}"
                logger.warning("Ollama request error", 
                             attempt=attempt + 1,
                             error=error_msg,
                             request_id=request_id)
                last_error = error_msg
            
            # Wait before retry (exponential backoff)
            if attempt < self.max_retries - 1:
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
        
        # All retries failed
        error_msg = f"All {self.max_retries} attempts failed. Last error: {last_error}"
        logger.error("Ollama request failed after retries", 
                    error=error_msg,
                    request_id=request_id)
        raise RuntimeError(error_msg)
    
    async def extract_memory(
        self,
        content: str,
        extraction_prompt: str,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract and process memory content using LLM.
        
        Args:
            content: Raw memory content
            extraction_prompt: Prompt for extraction
            request_id: Optional request identifier
            
        Returns:
            Dict with processed_content, summary, and confidence
        """
        start_time = time.time()
        
        try:
            # Build the full prompt
            full_prompt = f"""
{extraction_prompt}

CONTENT TO PROCESS:
{content}

Please provide a JSON response with the following structure:
{{
    "processed_content": "refined and structured content",
    "summary": "brief summary of key points",
    "key_concepts": ["concept1", "concept2", ...],
    "confidence": 0.95
}}
"""
            
            payload = {
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.3,  # Lower temperature for more consistent extraction
                    "top_p": 0.9,
                    "top_k": 40,
                    "num_predict": 1000  # Limit response length
                }
            }
            
            response = await self._make_request_with_retry(
                "/api/generate",
                payload,
                request_id
            )
            
            # Parse the JSON response
            response_text = response.get("response", "").strip()
            
            try:
                result = json.loads(response_text)
                
                # Validate required fields
                if not all(key in result for key in ["processed_content", "summary"]):
                    raise ValueError("Missing required fields in LLM response")
                
                # Ensure confidence is a float
                result["confidence"] = float(result.get("confidence", 0.8))
                
                processing_time = time.time() - start_time
                
                logger.info("Memory extraction completed",
                          request_id=request_id,
                          processing_time_ms=round(processing_time * 1000, 2),
                          confidence=result["confidence"],
                          content_length=len(content))
                
                return result
                
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                logger.warning("Failed to parse LLM JSON response, using fallback", 
                             response_text=response_text,
                             error=str(e))
                
                # Fallback: use raw response
                return {
                    "processed_content": response_text or content,
                    "summary": content[:200] + "..." if len(content) > 200 else content,
                    "key_concepts": [],
                    "confidence": 0.5
                }
                
        except Exception as e:
            logger.error("Memory extraction failed", 
                        request_id=request_id,
                        content_length=len(content),
                        error=str(e))
            
            # Return minimal fallback
            return {
                "processed_content": content,
                "summary": content[:200] + "..." if len(content) > 200 else content,
                "key_concepts": [],
                "confidence": 0.3
            }
    
    async def reconcile_memories(
        self,
        new_memory: str,
        related_memories: List[Dict[str, Any]],
        reconciliation_prompt: str,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Reconcile new memory with existing related memories.
        
        Args:
            new_memory: New memory content
            related_memories: List of related memory records
            reconciliation_prompt: Prompt for reconciliation
            request_id: Optional request identifier
            
        Returns:
            Dict with reconciled content and relationships
        """
        start_time = time.time()
        
        try:
            # Build context from related memories
            related_context = "\n".join([
                f"Memory {i+1}: {mem.get('processed_content', '')[:300]}..."
                for i, mem in enumerate(related_memories[:3])  # Limit to top 3 for context
            ])
            
            full_prompt = f"""
{reconciliation_prompt}

NEW MEMORY TO RECONCILE:
{new_memory}

RELATED EXISTING MEMORIES:
{related_context}

Please provide a JSON response with:
{{
    "reconciled_content": "refined content that integrates with existing memories",
    "relationships": ["relationship1", "relationship2"],
    "conflicts_detected": ["conflict1", "conflict2"],
    "confidence": 0.90
}}
"""
            
            payload = {
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.2,  # Even lower temperature for consistency
                    "top_p": 0.8,
                    "top_k": 30,
                    "num_predict": 800
                }
            }
            
            response = await self._make_request_with_retry(
                "/api/generate",
                payload,
                request_id
            )
            
            response_text = response.get("response", "").strip()
            
            try:
                result = json.loads(response_text)
                
                # Validate and clean result
                result.setdefault("reconciled_content", new_memory)
                result.setdefault("relationships", [])
                result.setdefault("conflicts_detected", [])
                result["confidence"] = float(result.get("confidence", 0.7))
                
                processing_time = time.time() - start_time
                
                logger.info("Memory reconciliation completed",
                          request_id=request_id,
                          processing_time_ms=round(processing_time * 1000, 2),
                          related_count=len(related_memories),
                          confidence=result["confidence"])
                
                return result
                
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                logger.warning("Failed to parse reconciliation response", 
                             response_text=response_text,
                             error=str(e))
                
                return {
                    "reconciled_content": new_memory,
                    "relationships": [],
                    "conflicts_detected": [],
                    "confidence": 0.5
                }
                
        except Exception as e:
            logger.error("Memory reconciliation failed", 
                        request_id=request_id,
                        error=str(e))
            
            return {
                "reconciled_content": new_memory,
                "relationships": [],
                "conflicts_detected": [],
                "confidence": 0.3
            }
    
    async def generate_embeddings(
        self,
        text: str,
        request_id: Optional[str] = None
    ) -> Optional[List[float]]:
        """Generate vector embeddings for text content.
        
        Args:
            text: Input text to embed
            request_id: Optional request identifier
            
        Returns:
            Vector embedding or None if failed
        """
        try:
            # Use embeddings endpoint if available, otherwise generate
            payload = {
                "model": self.model,
                "prompt": text
            }
            
            # Try embeddings endpoint first
            try:
                response = await self._make_request_with_retry(
                    "/api/embeddings",
                    payload,
                    request_id
                )
                
                embeddings = response.get("embedding")
                if embeddings and isinstance(embeddings, list):
                    logger.debug("Generated embeddings via embeddings API", 
                               text_length=len(text),
                               vector_dim=len(embeddings),
                               request_id=request_id)
                    return embeddings
                    
            except Exception:
                # Fall back to generate endpoint with embedding prompt
                pass
            
            # Fallback: use generate endpoint with embedding-focused prompt
            embed_prompt = f"""Generate a semantic embedding representation for this text by analyzing its key concepts, themes, and meaning. Focus on extracting the core semantic features that would be useful for similarity matching and retrieval.

Text: {text}

Provide a normalized vector representation as a list of 1536 float values between -1 and 1."""
            
            payload = {
                "model": self.model,
                "prompt": embed_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.7,
                    "num_predict": 500
                }
            }
            
            response = await self._make_request_with_retry(
                "/api/generate",
                payload,
                request_id
            )
            
            # This is a simplified fallback - in production, you'd want
            # a proper embedding model or use a hash-based approach
            response_text = response.get("response", "")
            
            # Create a simple hash-based embedding as fallback
            import hashlib
            hash_obj = hashlib.sha256(text.encode())
            hash_hex = hash_obj.hexdigest()
            
            # Convert hash to vector (simplified approach)
            vector = []
            for i in range(0, len(hash_hex), 2):
                byte_val = int(hash_hex[i:i+2], 16)
                normalized_val = (byte_val - 127.5) / 127.5  # Normalize to [-1, 1]
                vector.append(normalized_val)
            
            # Pad or truncate to desired dimension
            while len(vector) < 1536:
                vector.extend(vector[:min(len(vector), 1536 - len(vector))])
            vector = vector[:1536]
            
            logger.debug("Generated fallback hash-based embeddings", 
                       text_length=len(text),
                       vector_dim=len(vector),
                       request_id=request_id)
            
            return vector
            
        except Exception as e:
            logger.error("Failed to generate embeddings", 
                        text_length=len(text),
                        request_id=request_id,
                        error=str(e))
            return None