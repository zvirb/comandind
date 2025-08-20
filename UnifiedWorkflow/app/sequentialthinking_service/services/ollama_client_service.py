"""
Ollama client service for LLM interaction with fallback and optimization
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
import aiohttp
import time

from ..config import get_settings
from ..models import ErrorType, ErrorContext

logger = logging.getLogger(__name__)
settings = get_settings()


class OllamaClientService:
    """
    Service for interacting with Ollama models with fallback and optimization
    """
    
    def __init__(self):
        self.base_url = settings.OLLAMA_URL
        self.primary_model = settings.OLLAMA_PRIMARY_MODEL
        self.backup_model = settings.OLLAMA_BACKUP_MODEL
        self.timeout = settings.OLLAMA_REASONING_TIMEOUT
        self._session: Optional[aiohttp.ClientSession] = None
        self._model_availability: Dict[str, bool] = {}
        
    async def initialize(self) -> None:
        """Initialize HTTP session and check model availability"""
        try:
            # Create HTTP session with mTLS if enabled
            connector_kwargs = {}
            
            if settings.MTLS_ENABLED and settings.MTLS_CERT_FILE:
                import ssl
                ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
                ssl_context.load_cert_chain(settings.MTLS_CERT_FILE, settings.MTLS_KEY_FILE)
                if settings.MTLS_CA_CERT_FILE:
                    ssl_context.load_verify_locations(settings.MTLS_CA_CERT_FILE)
                connector_kwargs['ssl_context'] = ssl_context
            
            connector = aiohttp.TCPConnector(**connector_kwargs)
            
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={"Content-Type": "application/json"}
            )
            
            # Check model availability
            await self._check_model_availability()
            
            logger.info("Ollama client service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Ollama client: {e}")
            raise
    
    async def _check_model_availability(self) -> None:
        """Check which models are available"""
        try:
            async with self._session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    available_models = {model['name'] for model in data.get('models', [])}
                    
                    self._model_availability[self.primary_model] = self.primary_model in available_models
                    self._model_availability[self.backup_model] = self.backup_model in available_models
                    
                    logger.info(f"Model availability: {self._model_availability}")
                else:
                    logger.warning(f"Could not check model availability: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error checking model availability: {e}")
            # Assume models are available if we can't check
            self._model_availability[self.primary_model] = True
            self._model_availability[self.backup_model] = True
    
    async def generate_chat_response_stream(
        self,
        message: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        preferred_model: Optional[str] = None
    ):
        """
        Generate streaming chat response for WebSocket integration
        
        Args:
            message: User message
            chat_history: Previous chat messages [{"role": "user|assistant", "content": "..."}]
            preferred_model: Model to use (falls back if not available)
            
        Yields:
            Dict with 'chunk', 'is_complete', 'model_used', 'metadata'
        """
        if not self._session:
            raise RuntimeError("Ollama client not initialized")
        
        # Determine model to use
        model_to_use = preferred_model or self.primary_model
        if not self._model_availability.get(model_to_use, False):
            logger.warning(f"Model {model_to_use} not available, falling back to {self.backup_model}")
            model_to_use = self.backup_model
        
        if not self._model_availability.get(model_to_use, False):
            raise RuntimeError(f"No available models for chat")
        
        # Build chat prompt
        full_prompt = self._build_chat_prompt(message, chat_history)
        
        try:
            payload = {
                "model": model_to_use,
                "prompt": full_prompt,
                "stream": True,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "num_predict": 2048,
                    "stop": ["Human:", "User:"]
                }
            }
            
            start_time = time.time()
            accumulated_content = ""
            
            async with self._session.post(
                f"{self.base_url}/api/generate", 
                json=payload
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"Ollama request failed: {response.status} - {error_text}")
                
                async for line in response.content:
                    if line:
                        try:
                            chunk_data = json.loads(line.decode('utf-8').strip())
                            chunk_content = chunk_data.get('response', '')
                            is_done = chunk_data.get('done', False)
                            
                            if chunk_content:
                                accumulated_content += chunk_content
                                
                                yield {
                                    "chunk": chunk_content,
                                    "is_complete": False,
                                    "model_used": model_to_use,
                                    "accumulated_content": accumulated_content,
                                    "metadata": {
                                        "processing_time_ms": int((time.time() - start_time) * 1000)
                                    }
                                }
                            
                            if is_done:
                                processing_time_ms = int((time.time() - start_time) * 1000)
                                yield {
                                    "chunk": "",
                                    "is_complete": True,
                                    "model_used": model_to_use,
                                    "accumulated_content": accumulated_content,
                                    "metadata": {
                                        "processing_time_ms": processing_time_ms,
                                        "confidence": self._estimate_confidence(accumulated_content, chunk_data),
                                        "total_tokens": chunk_data.get('eval_count', 0)
                                    }
                                }
                                break
                                
                        except json.JSONDecodeError:
                            # Skip malformed chunks
                            continue
                            
        except asyncio.TimeoutError:
            raise RuntimeError(f"Ollama request timed out after {self.timeout}s")
        except Exception as e:
            logger.error(f"Error generating chat stream: {e}")
            raise
    
    def _build_chat_prompt(self, message: str, chat_history: Optional[List[Dict[str, str]]] = None) -> str:
        """Build a chat prompt with history context"""
        
        system_prompt = """You are a helpful AI assistant. Provide clear, accurate, and helpful responses to user questions. 
Be conversational but informative. If you're uncertain about something, acknowledge it clearly."""
        
        # Build conversation context
        conversation = [system_prompt]
        
        if chat_history:
            for msg in chat_history[-10:]:  # Keep last 10 messages for context
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                if role == 'user':
                    conversation.append(f"Human: {content}")
                elif role == 'assistant':
                    conversation.append(f"Assistant: {content}")
        
        # Add current message
        conversation.append(f"Human: {message}")
        conversation.append("Assistant:")
        
        return "\n\n".join(conversation)

    async def generate_reasoning_step(
        self, 
        prompt: str, 
        context: Optional[Dict[str, Any]] = None,
        preferred_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a single reasoning step using Ollama
        
        Args:
            prompt: The reasoning prompt
            context: Additional context information
            preferred_model: Model to use (falls back if not available)
            
        Returns:
            Dict with 'content', 'model_used', 'processing_time_ms', 'confidence'
        """
        if not self._session:
            raise RuntimeError("Ollama client not initialized")
        
        start_time = time.time()
        
        # Determine model to use
        model_to_use = preferred_model or self.primary_model
        if not self._model_availability.get(model_to_use, False):
            logger.warning(f"Model {model_to_use} not available, falling back to {self.backup_model}")
            model_to_use = self.backup_model
        
        if not self._model_availability.get(model_to_use, False):
            raise RuntimeError(f"No available models for reasoning")
        
        # Prepare the prompt
        full_prompt = self._build_reasoning_prompt(prompt, context)
        
        try:
            # Make request to Ollama
            payload = {
                "model": model_to_use,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "num_predict": 2048,
                    "stop": ["<|end_thinking|>", "Human:", "Assistant:"]
                }
            }
            
            async with self._session.post(
                f"{self.base_url}/api/generate", 
                json=payload
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"Ollama request failed: {response.status} - {error_text}")
                
                data = await response.json()
                content = data.get('response', '').strip()
                
                if not content:
                    raise ValueError("Empty response from model")
                
                processing_time_ms = int((time.time() - start_time) * 1000)
                
                return {
                    "content": content,
                    "model_used": model_to_use,
                    "processing_time_ms": processing_time_ms,
                    "confidence": self._estimate_confidence(content, data),
                    "raw_response": data
                }
                
        except asyncio.TimeoutError:
            raise RuntimeError(f"Ollama request timed out after {self.timeout}s")
        except Exception as e:
            logger.error(f"Error generating reasoning step: {e}")
            raise
    
    def _build_reasoning_prompt(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Build a structured prompt for reasoning"""
        
        system_prompt = """You are an advanced reasoning assistant. Your task is to provide clear, logical thinking about the given problem.

Instructions:
- Think step by step through the problem
- Be explicit about your reasoning process  
- If you're uncertain, acknowledge it
- If you need to revise previous thinking, clearly explain why
- Focus on accuracy and logical consistency
- Provide your reasoning between <thinking> tags

Format your response as:
<thinking>
[Your detailed reasoning here]
</thinking>

[Your conclusion or next step]"""

        context_section = ""
        if context:
            context_section = f"\n\nContext:\n{json.dumps(context, indent=2)}\n"
        
        return f"{system_prompt}{context_section}\n\nProblem to reason about:\n{prompt}\n\nPlease provide your reasoning:"
    
    def _estimate_confidence(self, content: str, raw_response: Dict[str, Any]) -> float:
        """Estimate confidence in the response"""
        
        # Basic heuristics for confidence estimation
        confidence = 0.5  # Base confidence
        
        # Length-based confidence (longer, more detailed responses often more confident)
        if len(content) > 200:
            confidence += 0.1
        if len(content) > 500:
            confidence += 0.1
            
        # Check for uncertainty markers
        uncertainty_markers = [
            "i'm not sure", "uncertain", "might be", "could be", 
            "possibly", "perhaps", "maybe", "i think", "unclear"
        ]
        
        content_lower = content.lower()
        uncertainty_count = sum(1 for marker in uncertainty_markers if marker in content_lower)
        confidence -= uncertainty_count * 0.1
        
        # Check for confidence markers
        confidence_markers = [
            "clearly", "obviously", "definitely", "certainly", 
            "undoubtedly", "without doubt", "conclusively"
        ]
        
        confidence_count = sum(1 for marker in confidence_markers if marker in content_lower)
        confidence += confidence_count * 0.05
        
        # Check for structured thinking (indicates more thoughtful response)
        if "<thinking>" in content and "</thinking>" in content:
            confidence += 0.1
            
        # Ensure confidence stays in valid range
        return max(0.1, min(0.95, confidence))
    
    async def validate_reasoning(
        self, 
        original_query: str, 
        reasoning_steps: List[str], 
        final_answer: str
    ) -> Dict[str, Any]:
        """
        Validate reasoning coherence and correctness
        
        Returns:
            Dict with 'is_valid', 'issues', 'confidence', 'suggestions'
        """
        if not self._session:
            raise RuntimeError("Ollama client not initialized")
        
        validation_prompt = f"""Please evaluate the following reasoning chain for logical consistency and correctness.

Original Query: {original_query}

Reasoning Steps:
{chr(10).join(f"{i+1}. {step}" for i, step in enumerate(reasoning_steps))}

Final Answer: {final_answer}

Please assess:
1. Is each step logically sound?
2. Do the steps flow logically from one to the next?
3. Does the final answer follow from the reasoning?
4. Are there any logical fallacies or errors?
5. What is the overall quality of this reasoning?

Respond with:
- VALID/INVALID
- List of specific issues (if any)
- Confidence score (0-1)
- Suggestions for improvement (if any)"""

        try:
            result = await self.generate_reasoning_step(
                validation_prompt, 
                {"task": "validation", "type": "reasoning_assessment"}
            )
            
            content = result["content"].lower()
            
            # Parse validation result
            is_valid = "valid" in content and "invalid" not in content.replace("valid", "")
            
            # Extract issues and suggestions (simplified parsing)
            issues = []
            suggestions = []
            
            if "issues:" in content:
                issues_section = content.split("issues:")[1].split("confidence")[0] if "confidence" in content else content.split("issues:")[1]
                issues = [line.strip() for line in issues_section.split("\n") if line.strip() and not line.strip().startswith("-")]
            
            return {
                "is_valid": is_valid,
                "issues": issues,
                "confidence": result["confidence"],
                "suggestions": suggestions,
                "validation_reasoning": result["content"]
            }
            
        except Exception as e:
            logger.error(f"Error validating reasoning: {e}")
            return {
                "is_valid": False,
                "issues": [f"Validation error: {str(e)}"],
                "confidence": 0.0,
                "suggestions": ["Unable to validate reasoning due to technical error"]
            }
    
    async def generate_recovery_plan(
        self, 
        error_context: ErrorContext, 
        failed_reasoning: List[str]
    ) -> Dict[str, Any]:
        """
        Generate a recovery plan after reasoning failure
        
        Returns:
            Dict with recovery strategy and specific actions
        """
        if not self._session:
            raise RuntimeError("Ollama client not initialized")
        
        recovery_prompt = f"""A reasoning process has encountered an error and needs a recovery plan.

Error Details:
- Type: {error_context.error_type}
- Message: {error_context.error_message}
- Failed at step: {error_context.failed_step}
- Retry count: {error_context.retry_count}

Previous Reasoning Attempts:
{chr(10).join(f"Step {i+1}: {step}" for i, step in enumerate(failed_reasoning))}

Please provide a recovery strategy that includes:
1. What went wrong in the reasoning
2. How to adjust the approach
3. Whether to rollback to an earlier step
4. Alternative reasoning strategies to try
5. Estimated success probability

Format your response clearly with specific, actionable recommendations."""

        try:
            result = await self.generate_reasoning_step(
                recovery_prompt,
                {
                    "task": "recovery_planning", 
                    "error_type": error_context.error_type,
                    "retry_count": error_context.retry_count
                }
            )
            
            return {
                "strategy": "llm_guided_recovery",
                "plan_content": result["content"],
                "confidence": result["confidence"],
                "processing_time_ms": result["processing_time_ms"],
                "model_used": result["model_used"]
            }
            
        except Exception as e:
            logger.error(f"Error generating recovery plan: {e}")
            return {
                "strategy": "fallback_recovery",
                "plan_content": "Unable to generate detailed recovery plan. Attempting simple retry with reduced complexity.",
                "confidence": 0.3,
                "processing_time_ms": 0,
                "model_used": "fallback"
            }
    
    async def close(self) -> None:
        """Close the HTTP session"""
        if self._session:
            await self._session.close()
            logger.info("Ollama client service closed")