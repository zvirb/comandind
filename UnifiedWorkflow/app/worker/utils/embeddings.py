"""
This utility provides a function to generate embeddings for text using Ollama.
"""
import logging
from typing import List

import httpx

from shared.utils.config import get_settings

logger = logging.getLogger(__name__)


async def get_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generates embeddings for a list of texts using the Ollama API.

    This implementation processes one text at a time. For higher throughput,
    consider batching if the underlying model/API supports it.

    Args:
        texts: A list of strings to be embedded.

    Returns:
        A list of embedding vectors, where each vector is a list of floats.
    """
    settings = get_settings()
    # NOTE: Ensure OLLAMA_EMBEDDING_MODEL_NAME is defined in your settings.
    # Common choices are 'nomic-embed-text' or 'mxbai-embed-large'.
    model_name = settings.OLLAMA_EMBEDDING_MODEL_NAME
    ollama_url = f"{settings.OLLAMA_API_BASE_URL}/api/embeddings"
    all_embeddings: List[List[float]] = []

    logger.info("Generating embeddings using model '%s' at %s", model_name, settings.OLLAMA_API_BASE_URL)

    async with httpx.AsyncClient(timeout=60.0) as client:
        for text in texts:
            json_payload = {"model": model_name, "prompt": text}
            try:
                response = await client.post(ollama_url, json=json_payload)
                response.raise_for_status()
                response_data = response.json()
                if 'embedding' in response_data:
                    all_embeddings.append(response_data['embedding'])
                else:
                    logger.error("Ollama API response missing 'embedding' field: %s", response_data)
                    raise ValueError("Invalid response format from Ollama embedding API")
            except httpx.HTTPStatusError as e:
                logger.error("HTTP error getting embeddings: %s - %s", e.response.status_code, e.response.text)
                raise
            except Exception as e:
                logger.error("Unexpected error during embedding generation: %s", e, exc_info=True)
                raise

    logger.info("Successfully generated %d embeddings.", len(all_embeddings))
    return all_embeddings
