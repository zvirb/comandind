"""
A simple tool that takes unstructured text and a user prompt to perform
a direct data extraction or Q&A task.
"""
import logging
from ..services.ollama_service import invoke_llm

logger = logging.getLogger(__name__)

async def run_unstructured_data_tool(user_input: str, context: str) -> str:
    """
    A simple tool that takes unstructured text and a user prompt to perform
    a direct data extraction or Q&A task.
    @param user_input The user's original prompt (e.g., "get the due dates").
    @param context The block of text to be analyzed.
    @returns The extracted information.
    """
    logger.info("--- EXECUTING UNSTRUCTURED DATA TOOL ---")

    extraction_prompt = f"""
        Based on the following text, please respond to the user's request.

        User Request: "{user_input}"

        Text to Analyze:
        {context}
    """

    messages = [{"role": "user", "content": extraction_prompt}]
    
    # TODO: Make the model name configurable
    result = await invoke_llm(messages, "mistral")
    return result.strip()
