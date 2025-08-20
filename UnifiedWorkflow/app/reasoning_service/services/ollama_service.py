"""Ollama integration service for LLM-powered reasoning capabilities.

Provides async interface to Ollama for cognitive reasoning tasks with
performance optimization and error handling.
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional, List
import aiohttp
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)


class OllamaService:
    """Async Ollama service client for reasoning tasks."""
    
    def __init__(
        self,
        url: str,
        model: str,
        timeout: int = 120,
        max_retries: int = 3,
        max_concurrent_requests: int = 5
    ):
        self.url = url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self._session: Optional[aiohttp.ClientSession] = None
        self._semaphore = asyncio.Semaphore(max_concurrent_requests)
        self._model_ready = False
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session with proper timeout."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={"Content-Type": "application/json"}
            )
        return self._session
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def health_check(self) -> bool:
        """Check if Ollama service is accessible."""
        try:
            session = await self._get_session()
            async with session.get(f"{self.url}/api/tags") as response:
                if response.status == 200:
                    logger.info("Ollama service health check passed")
                    return True
                else:
                    logger.warning("Ollama health check failed", status=response.status)
                    return False
                    
        except Exception as e:
            logger.error("Ollama health check error", error=str(e))
            return False
    
    async def ensure_model_ready(self) -> bool:
        """Ensure the reasoning model is ready for inference."""
        try:
            session = await self._get_session()
            
            # Check if model is already loaded
            async with session.get(f"{self.url}/api/ps") as response:
                if response.status == 200:
                    data = await response.json()
                    loaded_models = [model.get("name", "") for model in data.get("models", [])]
                    
                    if any(self.model in model_name for model_name in loaded_models):
                        self._model_ready = True
                        logger.info("Reasoning model already loaded", model=self.model)
                        return True
            
            # Pull model if not available
            logger.info("Loading reasoning model", model=self.model)
            pull_data = {"name": self.model}
            
            async with session.post(
                f"{self.url}/api/pull",
                json=pull_data
            ) as response:
                if response.status == 200:
                    # Stream response to handle progress
                    async for line in response.content:
                        if line:
                            try:
                                progress_data = json.loads(line.decode().strip())
                                if progress_data.get("status") == "success":
                                    self._model_ready = True
                                    logger.info("Reasoning model loaded successfully")
                                    return True
                            except json.JSONDecodeError:
                                continue
                                
        except Exception as e:
            logger.error("Failed to ensure model readiness", error=str(e), model=self.model)
            
        return False
    
    async def is_model_ready(self) -> bool:
        """Check if model is ready without attempting to load it."""
        return self._model_ready
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8)
    )
    async def generate_reasoning(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate reasoning response using Ollama."""
        
        async with self._semaphore:
            start_time = time.time()
            
            try:
                session = await self._get_session()
                
                # Prepare request data
                request_data = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "top_p": 0.9,
                        "repeat_penalty": 1.1
                    }
                }
                
                if system_prompt:
                    request_data["system"] = system_prompt
                    
                if max_tokens:
                    request_data["options"]["num_predict"] = max_tokens
                
                logger.info(
                    "Generating reasoning response",
                    request_id=request_id,
                    model=self.model,
                    prompt_length=len(prompt),
                    temperature=temperature
                )
                
                async with session.post(
                    f"{self.url}/api/generate",
                    json=request_data
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(
                            "Ollama generation failed",
                            status=response.status,
                            error=error_text,
                            request_id=request_id
                        )
                        raise aiohttp.ClientError(f"Ollama request failed: {error_text}")
                    
                    result = await response.json()
                    processing_time = time.time() - start_time
                    
                    # Extract response text
                    response_text = result.get("response", "")
                    
                    if not response_text:
                        raise ValueError("Empty response from Ollama")
                    
                    logger.info(
                        "Reasoning generation completed",
                        request_id=request_id,
                        processing_time_ms=round(processing_time * 1000, 2),
                        response_length=len(response_text),
                        tokens_evaluated=result.get("eval_count", 0),
                        tokens_generated=result.get("eval_count", 0)
                    )
                    
                    return {
                        "response": response_text,
                        "processing_time_ms": round(processing_time * 1000, 2),
                        "model": self.model,
                        "tokens_evaluated": result.get("eval_count", 0),
                        "tokens_generated": result.get("eval_count", 0),
                        "eval_duration_ms": result.get("eval_duration", 0) // 1_000_000,
                        "load_duration_ms": result.get("load_duration", 0) // 1_000_000
                    }
                    
            except Exception as e:
                processing_time = time.time() - start_time
                logger.error(
                    "Reasoning generation error",
                    error=str(e),
                    request_id=request_id,
                    processing_time_ms=round(processing_time * 1000, 2)
                )
                raise
    
    async def generate_structured_reasoning(
        self,
        prompt: str,
        response_format: Dict[str, Any],
        system_prompt: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate structured reasoning response with JSON format."""
        
        # Enhance prompt with format instructions
        format_instruction = f"""
        
Please provide your response in the following JSON format:
{json.dumps(response_format, indent=2)}

Ensure your response is valid JSON and follows the exact structure provided.
"""
        
        enhanced_prompt = prompt + format_instruction
        
        response = await self.generate_reasoning(
            prompt=enhanced_prompt,
            system_prompt=system_prompt,
            temperature=0.05,  # Lower temperature for structured output
            request_id=request_id
        )
        
        try:
            # Try to parse JSON response
            response_text = response["response"]
            
            # Extract JSON from response (handle potential extra text)
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            
            if json_start >= 0 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                parsed_response = json.loads(json_text)
                response["structured_response"] = parsed_response
                response["parsing_success"] = True
            else:
                response["parsing_success"] = False
                response["parsing_error"] = "No valid JSON found in response"
                
        except json.JSONDecodeError as e:
            response["parsing_success"] = False
            response["parsing_error"] = str(e)
            logger.warning(
                "Failed to parse structured response",
                request_id=request_id,
                error=str(e)
            )
        
        return response
    
    async def batch_generate(
        self,
        prompts: List[str],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        request_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Generate responses for multiple prompts concurrently."""
        
        logger.info(
            "Starting batch reasoning generation",
            request_id=request_id,
            prompt_count=len(prompts)
        )
        
        # Create tasks for concurrent execution
        tasks = [
            self.generate_reasoning(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                request_id=f"{request_id}_batch_{i}" if request_id else f"batch_{i}"
            )
            for i, prompt in enumerate(prompts)
        ]
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "Batch generation error for prompt",
                    prompt_index=i,
                    error=str(result),
                    request_id=request_id
                )
                processed_results.append({
                    "error": str(result),
                    "prompt_index": i,
                    "success": False
                })
            else:
                result["prompt_index"] = i
                result["success"] = True
                processed_results.append(result)
        
        return processed_results
    
    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info("Ollama service session closed")