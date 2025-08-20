"""
This service handles interactions with the Ollama API for language model invocations.
Enhanced with token tracking and metrics for smart AI capabilities.
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

import httpx
import tiktoken

# --- Local Imports ---
from shared.utils.config import get_settings
from worker.tool_registry import AVAILABLE_TOOLS
from worker.smart_ai_models import TokenMetrics

# --- Logging Setup ---
logger = logging.getLogger(__name__)


class OllamaService:
    """Service class for interacting with Ollama LLM API."""
    
    def __init__(self):
        self.settings = get_settings()
    
    async def invoke_llm(self, prompt: str, model_name: str = None) -> str:
        """
        Invoke LLM with a simple prompt string.
        
        Args:
            prompt: The prompt string to send to the LLM
            model_name: Optional model name, uses default if not provided
            
        Returns:
            The response content from the language model
        """
        if model_name is None:
            model_name = getattr(self.settings, 'DEFAULT_LLM_MODEL', 'llama3.2:1b')
        
        messages = [{"role": "user", "content": prompt}]
        return await invoke_llm(messages, model_name)


def convert_tools_to_ollama_format() -> List[Dict[str, Any]]:
    """
    Convert the tool registry to Ollama tool format.
    
    Returns:
        List of tool definitions in Ollama format
    """
    ollama_tools = []
    
    for tool in AVAILABLE_TOOLS:
        ollama_tool = {
            "type": "function",
            "function": {
                "name": tool["id"],
                "description": tool["description"],
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The user's query or request"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
        ollama_tools.append(ollama_tool)
    
    return ollama_tools


def estimate_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """
    Estimate token count for a given text using tiktoken.
    Falls back to word-based estimation if tiktoken fails.
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception:
        # Fallback to word-based estimation (rough approximation)
        return len(text.split()) * 1.3  # Approximate token-to-word ratio
    

def count_message_tokens(messages: List[Dict[str, str]], model: str = "gpt-3.5-turbo") -> int:
    """
    Count tokens in a list of messages.
    """
    total_tokens = 0
    for message in messages:
        # Count tokens in message content
        if isinstance(message.get("content"), str):
            total_tokens += estimate_tokens(message["content"], model)
        # Add overhead for message structure
        total_tokens += 4  # Overhead per message
    return int(total_tokens)


def extract_token_usage(response_data: Dict[str, Any]) -> Tuple[int, int]:
    """
    Extract token usage from Ollama response.
    Returns (input_tokens, output_tokens) or estimates if not available.
    """
    # Check if Ollama provides token usage information
    if "usage" in response_data:
        usage = response_data["usage"]
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        return input_tokens, output_tokens
    
    # Fallback to estimation
    input_tokens = 0
    output_tokens = 0
    
    # Estimate output tokens from message content
    if "message" in response_data and "content" in response_data["message"]:
        content = response_data["message"]["content"]
        output_tokens = estimate_tokens(content)
    
    return input_tokens, output_tokens


async def invoke_llm_stream(
    messages: List[Dict[str, str]], model_name: str, tools: List[Dict[str, Any]] = None
) -> AsyncGenerator[str, None]:
    """
    Invokes the specified Ollama language model with a list of messages and streams the response.

    Args:
        messages: A list of message dictionaries.
        model_name: The name of the Ollama model to use.
        tools: Optional list of tools for the model.

    Yields:
        The content of the response from the language model, token by token.
    """
    settings = get_settings()
    ollama_url = f"{settings.OLLAMA_API_BASE_URL}/api/chat"
    logger.info(
        "Streaming LLM '%s' at %s with %d messages...",
        model_name,
        settings.OLLAMA_API_BASE_URL,
        len(messages),
    )

    json_payload: Dict[str, Any] = {
        "model": model_name,
        "messages": messages,
        "stream": True,
    }
    
    # Add tools if provided
    if tools:
        json_payload["tools"] = tools
        logger.info(f"Including {len(tools)} tools in Ollama request")

    try:
        async with httpx.AsyncClient(timeout=3600.0) as client:
            async with client.stream("POST", ollama_url, json=json_payload) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    try:
                        # Ollama streams JSON objects separated by newlines
                        json_data = json.loads(chunk)
                        if (
                            "message" in json_data
                            and "content" in json_data["message"]
                        ):
                            yield json_data["message"]["content"]
                    except json.JSONDecodeError:
                        logger.warning("Could not decode JSON chunk: %s", chunk)
                        continue  # Ignore chunks that are not valid JSON
    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP error occurred while streaming LLM: %s - %s",
            e.response.status_code,
            e.response.text,
        )
        raise
    except Exception as e:
        logger.error(
            "An unexpected error occurred during LLM stream: %s", e, exc_info=True
        )
        raise


async def invoke_llm_stream_with_tokens(
    messages: List[Dict[str, str]], 
    model_name: str, 
    tools: List[Dict[str, Any]] = None,
    category: str = "general"
) -> AsyncGenerator[Tuple[str, Optional[TokenMetrics]], None]:
    """
    Invokes the specified Ollama language model with streaming and token tracking.

    Args:
        messages: A list of message dictionaries.
        model_name: The name of the Ollama model to use.
        tools: Optional list of tools for the model.
        category: Category for token tracking (general/tool_selection/reflection/etc.)

    Yields:
        Tuple of (content, token_metrics) where token_metrics is provided on completion.
    """
    settings = get_settings()
    ollama_url = f"{settings.OLLAMA_API_BASE_URL}/api/chat"
    
    # Estimate input tokens
    input_tokens = count_message_tokens(messages, model_name)
    logger.info(
        "Streaming LLM '%s' with estimated %d input tokens...",
        model_name,
        input_tokens,
    )

    json_payload: Dict[str, Any] = {
        "model": model_name,
        "messages": messages,
        "stream": True,
    }
    
    if tools:
        json_payload["tools"] = tools
        logger.info(f"Including {len(tools)} tools in Ollama request")

    output_content = ""
    
    try:
        async with httpx.AsyncClient(timeout=3600.0) as client:
            async with client.stream("POST", ollama_url, json=json_payload) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    try:
                        json_data = json.loads(chunk)
                        if (
                            "message" in json_data
                            and "content" in json_data["message"]
                        ):
                            content = json_data["message"]["content"]
                            output_content += content
                            yield content, None
                        
                        # Check for completion and token usage
                        if json_data.get("done", False):
                            # Estimate output tokens
                            output_tokens = estimate_tokens(output_content, model_name)
                            
                            # Create token metrics
                            token_metrics = TokenMetrics()
                            token_metrics.add_tokens(input_tokens, output_tokens, category)
                            
                            logger.info(
                                "LLM stream completed. Tokens: %d input, %d output, %d total",
                                input_tokens, output_tokens, input_tokens + output_tokens
                            )
                            
                            yield "", token_metrics
                            
                    except json.JSONDecodeError:
                        logger.warning("Could not decode JSON chunk: %s", chunk)
                        continue
                        
    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP error occurred while streaming LLM: %s - %s",
            e.response.status_code,
            e.response.text,
        )
        raise
    except Exception as e:
        logger.error(
            "An unexpected error occurred during LLM stream: %s", e, exc_info=True
        )
        raise


def _inject_datetime_context(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Inject current date/time context into the message list as a system message.
    
    Args:
        messages: Original list of messages
        
    Returns:
        Updated list of messages with datetime context
    """
    from datetime import datetime
    import pytz
    
    # Get current UTC time and format it nicely
    now_utc = datetime.now(pytz.UTC)
    current_time = now_utc.strftime("%A, %B %d, %Y at %I:%M %p UTC")
    
    # Create system message with current date/time context
    datetime_context = {
        "role": "system", 
        "content": f"Current date and time: {current_time}. Use this information when responding to time-sensitive questions or when current date/time is relevant to the conversation."
    }
    
    # Check if there's already a system message at the beginning
    if messages and messages[0].get("role") == "system":
        # Append datetime info to existing system message
        messages[0]["content"] = f"{messages[0]['content']}\n\n{datetime_context['content']}"
        return messages
    else:
        # Insert datetime context as first system message
        return [datetime_context] + messages


async def invoke_llm(messages: List[Dict[str, str]], model_name: str) -> str:
    """
    Invokes the specified Ollama language model with a list of messages (for chat).

    Args:
        messages: A list of message dictionaries, e.g., [{"role": "user", "content": "..."}].
        model_name: The name of the Ollama model to use for the invocation.

    Returns:
        The response content from the language model as a string.
    """
    # Add current date/time context to messages
    messages = _inject_datetime_context(messages)
    
    settings = get_settings()
    # Use the /api/chat endpoint for conversational interactions
    ollama_url = f"{settings.OLLAMA_API_BASE_URL}/api/chat"

    logger.info(
        "Invoking LLM '%s' at %s with %d messages...",
        model_name,
        settings.OLLAMA_API_BASE_URL,
        len(messages),
    )

    # The payload for /api/chat uses 'messages' instead of 'prompt'
    json_payload: Dict[str, Any] = {
        "model": model_name,
        "messages": messages,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=3600.0) as client:
            response = await client.post(ollama_url, json=json_payload)
            response.raise_for_status()  # Raise an exception for 4xx or 5xx status codes

            response_data = response.json()

            # The response from /api/chat is structured differently
            if "message" in response_data and "content" in response_data["message"]:
                logger.info("LLM invocation successful.")
                return response_data["message"]["content"]

            logger.error(
                "LLM response did not contain a 'message.content' field: %s",
                response_data,
            )
            raise ValueError("Invalid response format from Ollama chat API")

    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP error occurred while invoking LLM: %s - %s",
            e.response.status_code,
            e.response.text,
        )
        raise
    except Exception as e:
        logger.error(
            "An unexpected error occurred during LLM invocation: %s", e, exc_info=True
        )
        raise


async def invoke_llm_with_tokens(
    messages: List[Dict[str, str]], 
    model_name: str, 
    category: str = "general"
) -> Tuple[str, TokenMetrics]:
    """
    Invokes the specified Ollama language model with token tracking.

    Args:
        messages: A list of message dictionaries.
        model_name: The name of the Ollama model to use.
        category: Category for token tracking.

    Returns:
        Tuple of (response_content, token_metrics).
    """
    # Add current date/time context to messages
    messages = _inject_datetime_context(messages)
    
    settings = get_settings()
    ollama_url = f"{settings.OLLAMA_API_BASE_URL}/api/chat"
    
    # Estimate input tokens
    input_tokens = count_message_tokens(messages, model_name)
    logger.info(
        "Invoking LLM '%s' with estimated %d input tokens...",
        model_name,
        input_tokens,
    )

    json_payload: Dict[str, Any] = {
        "model": model_name,
        "messages": messages,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=3600.0) as client:
            response = await client.post(ollama_url, json=json_payload)
            response.raise_for_status()

            response_data = response.json()

            if "message" in response_data and "content" in response_data["message"]:
                content = response_data["message"]["content"]
                
                # Extract or estimate token usage
                input_tokens_actual, output_tokens = extract_token_usage(response_data)
                if input_tokens_actual == 0:
                    input_tokens_actual = input_tokens  # Use our estimate
                if output_tokens == 0:
                    output_tokens = estimate_tokens(content, model_name)
                
                # Create token metrics
                token_metrics = TokenMetrics()
                token_metrics.add_tokens(input_tokens_actual, output_tokens, category)
                
                logger.info(
                    "LLM invocation completed. Tokens: %d input, %d output, %d total",
                    input_tokens_actual, output_tokens, input_tokens_actual + output_tokens
                )
                
                return content, token_metrics

            logger.error(
                "LLM response did not contain a 'message.content' field: %s",
                response_data,
            )
            raise ValueError("Invalid response format from Ollama chat API")

    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP error occurred while invoking LLM: %s - %s",
            e.response.status_code,
            e.response.text,
        )
        raise
    except Exception as e:
        logger.error(
            "An unexpected error occurred during LLM invocation: %s", e, exc_info=True
        )
        raise

async def generate_embeddings(
    texts: List[str], model_name: str = "mxbai-embed-large"
) -> Optional[List[List[float]]]:
    """
    Generates embeddings for a list of texts using a specified Ollama model.
    This implementation sends requests concurrently for improved performance.

    Args:
        texts: A list of strings to be converted into embeddings.
        model_name: The name of the embedding model to use.

    Returns:
        A list of embeddings, where each embedding is a list of floats,
        in the same order as the input texts. Returns None if the operation fails.
    """
    settings = get_settings()
    ollama_url = f"{settings.OLLAMA_API_BASE_URL}/api/embeddings"
    logger.info(
        "Generating embeddings for %d texts with model '%s' (concurrently)...",
        len(texts),
        model_name,
    )

    async def _get_embedding(text: str, client: httpx.AsyncClient) -> Optional[List[float]]:
        """Helper function to get a single embedding."""
        try:
            json_payload = {"model": model_name, "prompt": text}
            response = await client.post(ollama_url, json=json_payload)
            response.raise_for_status()
            response_data = response.json()
            return response_data.get("embedding")
        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error for text '%s...': %s - %s",
                text[:50], e.response.status_code, e.response.text
            )
            return None
        except Exception as e:
            logger.error(
                "Error generating embedding for text '%s...': %s", text[:50], e
            )
            return None

    try:
        async with httpx.AsyncClient(timeout=3600.0) as client:
            tasks = [_get_embedding(text, client) for text in texts]
            results = await asyncio.gather(*tasks)

        # Filter out None results and check if all embeddings were generated
        final_embeddings = [emb for emb in results if emb is not None]
        if len(final_embeddings) != len(texts):
            logger.warning(
                "Failed to generate embeddings for %d out of %d texts.",
                len(texts) - len(final_embeddings),
                len(texts),
            )
            # Depending on requirements, you might want to raise an error here
            # or return partial results. For now, we return what we have.

        logger.info("Successfully generated %d embeddings.", len(final_embeddings))
        return final_embeddings if final_embeddings else None

    except Exception as e:
        logger.error(
            "An unexpected error occurred during concurrent embedding generation: %s",
            e,
            exc_info=True,
        )
        return None