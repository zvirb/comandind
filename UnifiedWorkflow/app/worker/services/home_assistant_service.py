"""
This service provides a function to interact with the Home Assistant API.
"""
import logging
from typing import Dict, Any
import httpx
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)

async def call_home_assistant_service(domain: str, service: str, entity_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calls a specific service in Home Assistant (e.g., 'light.turn_on').

    Args:
        domain: The service domain (e.g., 'light', 'switch').
        service: The service to call (e.g., 'turn_on', 'set_temperature').
        entity_data: The data for the service call, including 'entity_id'.

    Returns:
        A dictionary with the result of the API call.
    """
    settings = get_settings()
    ha_url = settings.HOME_ASSISTANT_URL
    ha_token = settings.HOME_ASSISTANT_TOKEN.get_secret_value() if settings.HOME_ASSISTANT_TOKEN else None

    if not ha_url or not ha_token:
        logger.error("Home Assistant URL or Token is not configured.")
        return {"error": "Home Assistant integration is not configured in the settings."}

    api_url = f"{ha_url.rstrip('/')}/api/services/{domain}/{service}"
    headers = {"Authorization": f"Bearer {ha_token}", "Content-Type": "application/json"}

    logger.info(f"Calling Home Assistant service: {api_url} with data: {entity_data}")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(api_url, json=entity_data, headers=headers, timeout=10.0)
            response.raise_for_status()
            return {"status": "success", "response_data": response.json()}
        except httpx.HTTPStatusError as e:
            error_details = e.response.text
            logger.error(f"Error calling Home Assistant API: {e.response.status_code} - {error_details}")
            return {"error": f"Failed to call Home Assistant: {error_details}"}
        except Exception as e:
            logger.error(f"An unexpected error occurred when calling Home Assistant: {e}", exc_info=True)
            return {"error": "An unexpected error occurred while contacting Home Assistant."}
