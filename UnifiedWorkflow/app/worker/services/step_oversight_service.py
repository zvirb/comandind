"""
Step Oversight Service (Simplified)

Provides a more direct and efficient approach to monitoring and validating step execution.
This version removes the complexity of LangGraph and focuses on core validation logic.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

from worker.services.ollama_service import invoke_llm_with_tokens
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)


class StepStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    RETRY_NEEDED = "retry_needed"


class StepOversightService:
    """
    A simplified oversight system for step execution validation and improvement.
    This version is more direct and efficient, removing LangGraph overhead.
    """

    def __init__(self):
        self.settings = get_settings()
        self.max_retries = 2  # Reduced max retries for simplicity

    async def validate_step_execution(
        self, 
        step_description: str, 
        tool_used: str, 
        tool_output: Dict[str, Any],
        user_context: str = "",
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validates if a step was executed successfully and provides a direct assessment.

        Returns a dictionary with validation results, including status, success, issues,
        and a confidence score.
        """
        try:
            logger.info(f"Validating step: {step_description[:70]}...")

            # Use a single LLM call for a combined analysis and validation
            analysis_result = await self._analyze_step_outcome(
                step_description, tool_used, tool_output, user_context
            )

            # Determine success based on the analysis
            is_success = analysis_result.get("status") == StepStatus.SUCCESS
            analysis_result["success"] = is_success

            if not is_success:
                logger.warning(
                    f"Step validation failed for '{step_description[:50]}...' with status: {analysis_result.get('status')}"
                )
                # Optionally, you could still store failure patterns here if needed

            return analysis_result

        except Exception as e:
            logger.error(f"Error during step validation: {e}", exc_info=True)
            return {
                "status": StepStatus.FAILURE,
                "success": False,
                "issues": [f"Validation process failed: {e}"],
                "confidence": 0.0,
            }

    async def _analyze_step_outcome(
        self, 
        step_description: str, 
        tool_used: str, 
        tool_output: Dict[str, Any],
        user_context: str
    ) -> Dict[str, Any]:
        """
        Analyzes the outcome of a step using a single, efficient LLM call.
        """
        analysis_prompt = f"""
        You are an expert execution validator. Analyze the success of this step.

        **Step Description:** "{step_description}"
        **Tool Used:** {tool_used}
        **Tool Output:**
        ```json
        {json.dumps(tool_output, indent=2)}
        ```
        **User Context:** {user_context}

        **Instructions:**
        1.  **Assess Status:** Determine if the step was a 'success', 'failure', or 'partial' success.
        2.  **Identify Issues:** List any specific problems or errors encountered.
        3.  **Score Confidence:** Provide a confidence score (0.0 to 1.0) in your assessment.

        **Respond with JSON only in this format:**
        {{
          "status": "success|failure|partial",
          "confidence": 0.0,
          "issues": ["A list of specific issues found, if any."]
        }}
        """
        try:
            # Use a reliable model for this critical analysis
            analysis_model = self.settings.OLLAMA_GENERATION_MODEL_NAME
            messages = [
                {"role": "system", "content": "You are an expert execution validator. Always respond with valid JSON."},
                {"role": "user", "content": analysis_prompt}
            ]

            response, _ = await invoke_llm_with_tokens(
                messages, analysis_model, category="step_validation"
            )

            # Parse the JSON response
            analysis = json.loads(response)
            logger.info(f"Step validation complete. Status: {analysis.get('status')}, Confidence: {analysis.get('confidence')}")
            return analysis

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse validation JSON from LLM: {e}. Using fallback.")
            return self._fallback_validation(tool_output)
        except Exception as e:
            logger.error(f"Error in LLM-based step analysis: {e}", exc_info=True)
            return self._fallback_validation(tool_output)

    def _fallback_validation(self, tool_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Provides a basic, non-LLM validation as a fallback.
        """
        output_str = str(tool_output).lower()
        has_error = any(key in output_str for key in ["error", "failed", "exception"])
        has_success_indicator = any(key in output_str for key in ["success", "completed", "created"])

        if has_error:
            status = StepStatus.FAILURE
            issues = ["An error was detected in the tool output."]
        elif has_success_indicator:
            status = StepStatus.SUCCESS
            issues = []
        else:
            status = StepStatus.PARTIAL
            issues = ["Output did not contain clear success or failure indicators."]

        return {
            "status": status,
            "confidence": 0.6,  # Lower confidence for fallback
            "issues": issues,
        }

    def should_retry_step(
        self, 
        validation_result: Dict[str, Any], 
        retry_count: int
    ) -> bool:
        """
        Determines if a step should be retried based on the simplified validation.
        """
        status = validation_result.get("status")
        confidence = validation_result.get("confidence", 0)

        if retry_count >= self.max_retries:
            logger.info(f"Max retries ({self.max_retries}) reached. No more retries.")
            return False

        # Retry failures and partial successes if confidence in the assessment is high
        if status in [StepStatus.FAILURE, StepStatus.PARTIAL] and confidence > 0.7:
            logger.info(f"Retrying step. Status: {status}, Confidence: {confidence:.2f}")
            return True

        return False


# Global instance
step_oversight_service = StepOversightService()
