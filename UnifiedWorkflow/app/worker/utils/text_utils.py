"""Utility functions for text manipulation and JSON extraction."""

import asyncio  # Import asyncio for sleep
import json
import logging
import re
from typing import Any, Dict, Optional  # Keep Optional for return type

from worker.services.ollama_service import invoke_llm

logger = logging.getLogger(__name__)

SELF_CORRECTION_PROMPT = """
The previous attempt to generate JSON resulted in an error.
Provided below is the faulty text and the Python error that was raised.
Your task is to analyze the error and the text, and then output a corrected, valid JSON object.
Do NOT provide any commentary, explanation, or markdown formatting. Output only the raw, valid JSON.

Faulty Text:
---
{faulty_text}
---

Python Error:
---
{error_message}
---

Corrected JSON:
"""


def _strip_markdown(text: str) -> str:
    """Strips common markdown fences from a string."""
    stripped_text = text.strip()
    match = re.search(r"```(json)?\s*([\s\S]*?)\s*```", stripped_text)
    if match:
        return match.group(2).strip()
    return stripped_text


async def extract_json_with_self_correction(text: str, selected_model: str) -> Optional[Dict[str, Any]]:
    """A robust function to extract JSON from a string, using retries and self-correction."""
    current_text = _strip_markdown(text)
    last_error: Optional[json.JSONDecodeError] = None
    max_attempts = 3  # 1 initial attempt + 2 retries

    for attempt_num in range(1, max_attempts + 1):
        try:
            parsed_json = json.loads(current_text)
            logger.info("Successfully extracted JSON on attempt %d.", attempt_num)
            return parsed_json
        except json.JSONDecodeError as e:
            last_error = e
            logger.warning(
                "JSON parsing failed on attempt %d: %s", attempt_num, e
            )

            if attempt_num < max_attempts:
                logger.info(
                    "Attempting self-correction with LLM for attempt %d...", attempt_num + 1
                )
                correction_prompt = SELF_CORRECTION_PROMPT.format(
                    faulty_text=current_text, error_message=str(last_error)
                )
                # The invoke_llm function expects a list of message dictionaries for the chat endpoint.
                try:
                    corrected_text: str = await asyncio.wait_for(
                        invoke_llm(
                            messages=[{"role": "user", "content": correction_prompt}], 
                            model_name=selected_model
                        ),
                        timeout=30.0
                    )
                except asyncio.TimeoutError:
                    logger.error("LLM correction timed out after 30 seconds")
                    return None
                current_text = _strip_markdown(corrected_text)
                await asyncio.sleep(0.1)  # Small delay before next attempt
            else:
                logger.error(
                    "Could not extract valid JSON after %d attempts. Final error: %s",
                    max_attempts, last_error
                )
                return None
        except Exception as e:  # Catch any other unexpected errors during parsing
            logger.error(
                "An unexpected error occurred during JSON parsing on attempt %d: %s",
                attempt_num, e, exc_info=True
            )
            return None  # Fail immediately for unexpected errors

    return None  # Should not be reached, but for type safety