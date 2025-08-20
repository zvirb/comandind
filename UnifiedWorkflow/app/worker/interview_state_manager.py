"""
Manages the state of a Socratic interview session.
"""
from typing import Dict, Any, Optional

class InterviewStateManager:
    """Manages the state of a single user's interview session."""

    def __init__(self, user_id: int, interview_type: str):
        self.user_id = user_id
        self.interview_type = interview_type
        self.state: Dict[str, Any] = {
            "phase": "initialization",
            "history": [],
            "current_question": None,
            "user_responses": [],
        }

    def get_current_phase(self) -> str:
        """Returns the current phase of the interview."""
        return self.state["phase"]

    def transition_to_phase(self, new_phase: str):
        """Transitions the interview to a new phase."""
        self.state["phase"] = new_phase
        # In a real implementation, this would trigger loading new prompts, etc.

    def add_interaction(self, question: str, response: str):
        """Adds a question-response pair to the history."""
        self.state["history"].append({"question": question, "response": response})
        self.state["user_responses"].append(response)

    def get_full_history(self) -> list:
        """Returns the full conversation history."""
        return self.state["history"]

    def get_user_responses(self) -> list:
        """Returns a list of all user responses."""
        return self.state["user_responses"]
