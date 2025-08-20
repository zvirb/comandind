"""
This service provides a function to perform Google searches using the SerpApi.
It includes retry logic for network reliability.
"""
import logging
from typing import List, Dict, Any, Optional

import requests
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryCallState

# Absolute import from the backend root
from shared.utils.config import get_settings, Settings

load_dotenv()
SEARCH_URL = "https://serpapi.com/search.json"
DEFAULT_SEARCH_TIMEOUT = 10  # seconds

# Setup logging
logger = logging.getLogger(__name__)


def _log_and_return_search_error(retry_state: RetryCallState) -> Dict[str, str]:
    """Callback to log the final error and return a user-friendly dictionary."""
    exception = retry_state.outcome.exception() if retry_state.outcome else "Unknown error"
    logger.error(
        "SerpApi search failed after %d attempts. Last exception: %s",
        retry_state.attempt_number, exception,
        exc_info=exception if isinstance(exception, BaseException) else None
    )
    return {"error": f"Error performing search after multiple retries: {str(exception)}"}


def _filter_organic_results(organic_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filters each result to keep only specified keys."""
    if not organic_results:
        return []
    filtered_results: List[Dict[str, Any]] = []
    keys_to_keep = ["title", "snippet", "snippet_highlighted_words"]
    for result in organic_results:
        filtered_result = {key: result.get(key) for key in keys_to_keep if result.get(key) is not None}
        if filtered_result:
            filtered_results.append(filtered_result)
    return filtered_results


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
    retry_error_callback=_log_and_return_search_error
)
def run_google_search(query: str, settings: Optional[Settings] = None) -> Dict[str, Any]:
    """
    Performs a Google search using SerpApi and returns the result.
    Includes robust retry logic for transient network errors.
    """
    active_settings = settings if settings is not None else get_settings()

    if not active_settings.SERPAPI_KEY or active_settings.SERPAPI_KEY == "YOUR_SERPAPI_API_KEY_HERE":
        logger.warning("SerpApi API key is not configured. Skipping search.")
        return {"error": "SerpApi API key not configured."}

    logger.info("Performing Google search for: %s", query)
    params: Dict[str, Any] = {
        "api_key": active_settings.SERPAPI_KEY,
        "q": query,
        "engine": "google",
    }
    response = requests.get(SEARCH_URL, params=params, timeout=DEFAULT_SEARCH_TIMEOUT)
    response.raise_for_status()
    result_json = response.json()

    if "organic_results" in result_json:
        result_json["organic_results"] = _filter_organic_results(result_json["organic_results"])

    return result_json