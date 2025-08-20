"""
Model Provider Factory - API client management for heterogeneous LLM providers
Supports OpenAI, Anthropic, Google Gemini, and Ollama with unified interface normalization.
"""

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, AsyncGenerator, Union
from dataclasses import dataclass
from enum import Enum

import httpx
import json
from shared.database.models import LLMProvider
from shared.utils.config import get_settings
from worker.smart_ai_models import TokenMetrics

logger = logging.getLogger(__name__)


@dataclass
class ModelProviderMessage:
    """Standardized message format across all providers."""
    role: str  # "system", "user", "assistant"
    content: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ModelProviderResponse:
    """Standardized response format across all providers."""
    content: str
    token_metrics: TokenMetrics
    model_used: str
    provider: LLMProvider
    success: bool
    error_message: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None


@dataclass
class ModelProviderRequest:
    """Standardized request format for all providers."""
    messages: List[ModelProviderMessage]
    model_name: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    tools: Optional[List[Dict[str, Any]]] = None
    stop_sequences: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseModelProvider(ABC):
    """Abstract base class for all model providers."""
    
    def __init__(self, provider_type: LLMProvider):
        self.provider_type = provider_type
        self.settings = get_settings()
        self._client: Optional[httpx.AsyncClient] = None
    
    @abstractmethod
    async def invoke(self, request: ModelProviderRequest) -> ModelProviderResponse:
        """Invoke the model with a request and return response."""
        pass
    
    @abstractmethod
    async def stream(self, request: ModelProviderRequest) -> AsyncGenerator[str, None]:
        """Stream model response."""
        pass
    
    @abstractmethod
    async def validate_config(self) -> bool:
        """Validate provider configuration."""
        pass
    
    async def get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=300.0)
        return self._client
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def _convert_messages(self, messages: List[ModelProviderMessage]) -> List[Dict[str, str]]:
        """Convert standard messages to provider format."""
        return [{"role": msg.role, "content": msg.content} for msg in messages]
    
    def _estimate_tokens(self, text: str) -> int:
        """Simple token estimation (1.3 tokens per word)."""
        return int(len(text.split()) * 1.3)


class OllamaProvider(BaseModelProvider):
    """Ollama provider for local model inference."""
    
    def __init__(self):
        super().__init__(LLMProvider.OLLAMA)
        self.base_url = getattr(self.settings, 'OLLAMA_API_BASE_URL', 'http://ollama:11434')
    
    async def validate_config(self) -> bool:
        """Validate Ollama configuration."""
        try:
            client = await self.get_client()
            response = await client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama validation failed: {e}")
            return False
    
    async def invoke(self, request: ModelProviderRequest) -> ModelProviderResponse:
        """Invoke Ollama model."""
        start_time = datetime.now()
        
        try:
            client = await self.get_client()
            
            payload = {
                "model": request.model_name,
                "messages": self._convert_messages(request.messages),
                "stream": False,
                "options": {
                    "temperature": request.temperature,
                }
            }
            
            if request.max_tokens:
                payload["options"]["num_predict"] = request.max_tokens
            
            if request.tools:
                payload["tools"] = request.tools
            
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            
            response_data = response.json()
            content = response_data.get("message", {}).get("content", "")
            
            # Calculate token metrics
            input_tokens = sum(self._estimate_tokens(msg.content) for msg in request.messages)
            output_tokens = self._estimate_tokens(content)
            
            token_metrics = TokenMetrics()
            token_metrics.add_tokens(input_tokens, output_tokens, "ollama")
            
            return ModelProviderResponse(
                content=content,
                token_metrics=token_metrics,
                model_used=request.model_name,
                provider=self.provider_type,
                success=True,
                raw_response=response_data
            )
            
        except Exception as e:
            logger.error(f"Ollama invocation failed: {e}")
            return ModelProviderResponse(
                content="",
                token_metrics=TokenMetrics(),
                model_used=request.model_name,
                provider=self.provider_type,
                success=False,
                error_message=str(e)
            )
    
    async def stream(self, request: ModelProviderRequest) -> AsyncGenerator[str, None]:
        """Stream Ollama model response."""
        try:
            client = await self.get_client()
            
            payload = {
                "model": request.model_name,
                "messages": self._convert_messages(request.messages),
                "stream": True,
                "options": {
                    "temperature": request.temperature,
                }
            }
            
            if request.max_tokens:
                payload["options"]["num_predict"] = request.max_tokens
            
            if request.tools:
                payload["tools"] = request.tools
            
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    try:
                        json_data = json.loads(chunk)
                        if "message" in json_data and "content" in json_data["message"]:
                            yield json_data["message"]["content"]
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            logger.error(f"Ollama streaming failed: {e}")
            yield f"Error: {str(e)}"


class OpenAIProvider(BaseModelProvider):
    """OpenAI provider for GPT models."""
    
    def __init__(self):
        super().__init__(LLMProvider.OPENAI)
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.base_url = "https://api.openai.com/v1"
    
    async def validate_config(self) -> bool:
        """Validate OpenAI configuration."""
        if not self.api_key:
            logger.error("OpenAI API key not configured")
            return False
        
        try:
            client = await self.get_client()
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = await client.get(f"{self.base_url}/models", headers=headers)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"OpenAI validation failed: {e}")
            return False
    
    async def invoke(self, request: ModelProviderRequest) -> ModelProviderResponse:
        """Invoke OpenAI model."""
        if not await self.validate_config():
            return ModelProviderResponse(
                content="",
                token_metrics=TokenMetrics(),
                model_used=request.model_name,
                provider=self.provider_type,
                success=False,
                error_message="OpenAI configuration invalid"
            )
        
        try:
            client = await self.get_client()
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": request.model_name,
                "messages": self._convert_messages(request.messages),
                "temperature": request.temperature,
                "stream": False
            }
            
            if request.max_tokens:
                payload["max_tokens"] = request.max_tokens
            
            if request.tools:
                payload["tools"] = request.tools
            
            if request.stop_sequences:
                payload["stop"] = request.stop_sequences
            
            response = await client.post(f"{self.base_url}/chat/completions", 
                                       headers=headers, json=payload)
            response.raise_for_status()
            
            response_data = response.json()
            content = response_data["choices"][0]["message"]["content"]
            
            # Extract token usage
            usage = response_data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            
            token_metrics = TokenMetrics()
            token_metrics.add_tokens(input_tokens, output_tokens, "openai")
            
            return ModelProviderResponse(
                content=content,
                token_metrics=token_metrics,
                model_used=request.model_name,
                provider=self.provider_type,
                success=True,
                raw_response=response_data
            )
            
        except Exception as e:
            logger.error(f"OpenAI invocation failed: {e}")
            return ModelProviderResponse(
                content="",
                token_metrics=TokenMetrics(),
                model_used=request.model_name,
                provider=self.provider_type,
                success=False,
                error_message=str(e)
            )
    
    async def stream(self, request: ModelProviderRequest) -> AsyncGenerator[str, None]:
        """Stream OpenAI model response."""
        if not await self.validate_config():
            yield "Error: OpenAI configuration invalid"
            return
        
        try:
            client = await self.get_client()
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": request.model_name,
                "messages": self._convert_messages(request.messages),
                "temperature": request.temperature,
                "stream": True
            }
            
            if request.max_tokens:
                payload["max_tokens"] = request.max_tokens
            
            async with client.stream("POST", f"{self.base_url}/chat/completions", 
                                   headers=headers, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        if data == "[DONE]":
                            break
                        try:
                            json_data = json.loads(data)
                            delta = json_data["choices"][0]["delta"]
                            if "content" in delta:
                                yield delta["content"]
                        except (json.JSONDecodeError, KeyError):
                            continue
                            
        except Exception as e:
            logger.error(f"OpenAI streaming failed: {e}")
            yield f"Error: {str(e)}"


class AnthropicProvider(BaseModelProvider):
    """Anthropic provider for Claude models."""
    
    def __init__(self):
        super().__init__(LLMProvider.ANTHROPIC)
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        self.base_url = "https://api.anthropic.com/v1"
    
    async def validate_config(self) -> bool:
        """Validate Anthropic configuration."""
        if not self.api_key:
            logger.error("Anthropic API key not configured")
            return False
        return True  # Basic validation - could add API ping
    
    async def invoke(self, request: ModelProviderRequest) -> ModelProviderResponse:
        """Invoke Anthropic Claude model."""
        if not await self.validate_config():
            return ModelProviderResponse(
                content="",
                token_metrics=TokenMetrics(),
                model_used=request.model_name,
                provider=self.provider_type,
                success=False,
                error_message="Anthropic configuration invalid"
            )
        
        try:
            client = await self.get_client()
            headers = {
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            # Convert messages to Anthropic format
            messages = []
            system_message = None
            
            for msg in request.messages:
                if msg.role == "system":
                    system_message = msg.content
                else:
                    messages.append({"role": msg.role, "content": msg.content})
            
            payload = {
                "model": request.model_name,
                "messages": messages,
                "temperature": request.temperature,
                "stream": False
            }
            
            if system_message:
                payload["system"] = system_message
            
            if request.max_tokens:
                payload["max_tokens"] = request.max_tokens
            else:
                payload["max_tokens"] = 4096  # Required for Anthropic
            
            response = await client.post(f"{self.base_url}/messages", 
                                       headers=headers, json=payload)
            response.raise_for_status()
            
            response_data = response.json()
            content = response_data["content"][0]["text"]
            
            # Extract token usage
            usage = response_data.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            
            token_metrics = TokenMetrics()
            token_metrics.add_tokens(input_tokens, output_tokens, "anthropic")
            
            return ModelProviderResponse(
                content=content,
                token_metrics=token_metrics,
                model_used=request.model_name,
                provider=self.provider_type,
                success=True,
                raw_response=response_data
            )
            
        except Exception as e:
            logger.error(f"Anthropic invocation failed: {e}")
            return ModelProviderResponse(
                content="",
                token_metrics=TokenMetrics(),
                model_used=request.model_name,
                provider=self.provider_type,
                success=False,
                error_message=str(e)
            )
    
    async def stream(self, request: ModelProviderRequest) -> AsyncGenerator[str, None]:
        """Stream Anthropic Claude model response."""
        if not await self.validate_config():
            yield "Error: Anthropic configuration invalid"
            return
        
        try:
            client = await self.get_client()
            headers = {
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            # Convert messages to Anthropic format
            messages = []
            system_message = None
            
            for msg in request.messages:
                if msg.role == "system":
                    system_message = msg.content
                else:
                    messages.append({"role": msg.role, "content": msg.content})
            
            payload = {
                "model": request.model_name,
                "messages": messages,
                "temperature": request.temperature,
                "stream": True,
                "max_tokens": request.max_tokens or 4096
            }
            
            if system_message:
                payload["system"] = system_message
            
            async with client.stream("POST", f"{self.base_url}/messages", 
                                   headers=headers, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        try:
                            json_data = json.loads(data)
                            if json_data["type"] == "content_block_delta":
                                delta = json_data["delta"]
                                if delta["type"] == "text_delta":
                                    yield delta["text"]
                        except (json.JSONDecodeError, KeyError):
                            continue
                            
        except Exception as e:
            logger.error(f"Anthropic streaming failed: {e}")
            yield f"Error: {str(e)}"


class GoogleProvider(BaseModelProvider):
    """Google provider for Gemini models."""
    
    def __init__(self):
        super().__init__(LLMProvider.GOOGLE)
        self.api_key = os.getenv('GOOGLE_API_KEY')
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
    
    async def validate_config(self) -> bool:
        """Validate Google configuration."""
        if not self.api_key:
            logger.error("Google API key not configured")
            return False
        return True  # Basic validation
    
    async def invoke(self, request: ModelProviderRequest) -> ModelProviderResponse:
        """Invoke Google Gemini model."""
        if not await self.validate_config():
            return ModelProviderResponse(
                content="",
                token_metrics=TokenMetrics(),
                model_used=request.model_name,
                provider=self.provider_type,
                success=False,
                error_message="Google configuration invalid"
            )
        
        try:
            client = await self.get_client()
            
            # Convert messages to Gemini format
            contents = []
            for msg in request.messages:
                if msg.role == "user":
                    contents.append({"role": "user", "parts": [{"text": msg.content}]})
                elif msg.role == "assistant":
                    contents.append({"role": "model", "parts": [{"text": msg.content}]})
                # System messages are handled differently in Gemini
            
            payload = {
                "contents": contents,
                "generationConfig": {
                    "temperature": request.temperature,
                }
            }
            
            if request.max_tokens:
                payload["generationConfig"]["maxOutputTokens"] = request.max_tokens
            
            response = await client.post(
                f"{self.base_url}/models/{request.model_name}:generateContent?key={self.api_key}",
                json=payload
            )
            response.raise_for_status()
            
            response_data = response.json()
            content = response_data["candidates"][0]["content"]["parts"][0]["text"]
            
            # Estimate token usage (Google doesn't always provide exact counts)
            input_tokens = sum(self._estimate_tokens(msg.content) for msg in request.messages)
            output_tokens = self._estimate_tokens(content)
            
            token_metrics = TokenMetrics()
            token_metrics.add_tokens(input_tokens, output_tokens, "google")
            
            return ModelProviderResponse(
                content=content,
                token_metrics=token_metrics,
                model_used=request.model_name,
                provider=self.provider_type,
                success=True,
                raw_response=response_data
            )
            
        except Exception as e:
            logger.error(f"Google invocation failed: {e}")
            return ModelProviderResponse(
                content="",
                token_metrics=TokenMetrics(),
                model_used=request.model_name,
                provider=self.provider_type,
                success=False,
                error_message=str(e)
            )
    
    async def stream(self, request: ModelProviderRequest) -> AsyncGenerator[str, None]:
        """Stream Google Gemini model response."""
        # Google Gemini streaming implementation would go here
        # For now, yield a non-streaming response
        response = await self.invoke(request)
        if response.success:
            yield response.content
        else:
            yield f"Error: {response.error_message}"


class ModelProviderFactory:
    """
    Factory for creating and managing model providers.
    Provides unified interface for heterogeneous LLM access.
    """
    
    def __init__(self):
        self._providers: Dict[LLMProvider, BaseModelProvider] = {}
        self._initialized = False
    
    async def initialize(self):
        """Initialize all available providers."""
        if self._initialized:
            return
        
        logger.info("Initializing Model Provider Factory...")
        
        # Initialize providers
        self._providers[LLMProvider.OLLAMA] = OllamaProvider()
        self._providers[LLMProvider.OPENAI] = OpenAIProvider()
        self._providers[LLMProvider.ANTHROPIC] = AnthropicProvider()
        self._providers[LLMProvider.GOOGLE] = GoogleProvider()
        
        # Validate provider configurations
        for provider_type, provider in self._providers.items():
            try:
                is_valid = await provider.validate_config()
                if is_valid:
                    logger.info(f"✓ {provider_type.value} provider initialized successfully")
                else:
                    logger.warning(f"✗ {provider_type.value} provider configuration invalid")
            except Exception as e:
                logger.error(f"✗ {provider_type.value} provider initialization failed: {e}")
        
        self._initialized = True
        logger.info("Model Provider Factory initialization complete")
    
    async def get_provider(self, provider_type: LLMProvider) -> Optional[BaseModelProvider]:
        """Get provider instance for given type."""
        if not self._initialized:
            await self.initialize()
        
        return self._providers.get(provider_type)
    
    async def invoke_model(
        self, 
        provider_type: LLMProvider, 
        request: ModelProviderRequest
    ) -> ModelProviderResponse:
        """Invoke model through appropriate provider."""
        provider = await self.get_provider(provider_type)
        if not provider:
            return ModelProviderResponse(
                content="",
                token_metrics=TokenMetrics(),
                model_used=request.model_name,
                provider=provider_type,
                success=False,
                error_message=f"Provider {provider_type.value} not available"
            )
        
        return await provider.invoke(request)
    
    async def stream_model(
        self, 
        provider_type: LLMProvider, 
        request: ModelProviderRequest
    ) -> AsyncGenerator[str, None]:
        """Stream model response through appropriate provider."""
        provider = await self.get_provider(provider_type)
        if not provider:
            yield f"Error: Provider {provider_type.value} not available"
            return
        
        async for chunk in provider.stream(request):
            yield chunk
    
    async def get_available_providers(self) -> List[LLMProvider]:
        """Get list of available and configured providers."""
        if not self._initialized:
            await self.initialize()
        
        available = []
        for provider_type, provider in self._providers.items():
            try:
                if await provider.validate_config():
                    available.append(provider_type)
            except Exception:
                pass
        
        return available
    
    async def close_all(self):
        """Close all provider connections."""
        for provider in self._providers.values():
            try:
                await provider.close()
            except Exception as e:
                logger.debug(f"Error closing provider: {e}")


# Global instance
model_provider_factory = ModelProviderFactory()