"""
Smart AI Service for Enhanced Router Graph Functionality
Implements confidence-based routing, interactive pauses, and adaptive thinking patterns.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from worker.smart_ai_models import (
    TokenMetrics, HumanContextModel, PauseStateModel, PauseReason, TaskStatus,
    ConfidenceLevel, CritiqueModel, ToolCallRecord, ErrorModel
)
from worker.graph_types import GraphState
from worker.services.progress_manager import progress_manager
from worker.services.ollama_service import invoke_llm_with_tokens, count_message_tokens
from worker.services.mission_contradiction_service import mission_contradiction_service
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)

class SmartAIState(TypedDict):
    user_input: str
    context: str
    confidence_score: float
    confidence_level: ConfidenceLevel
    reasoning: str
    has_contradiction: bool
    contradiction_score: float
    analysis_text: str
    confirmation_prompt: str
    should_pause: bool
    pause_reason: PauseReason
    pause_message: str
    thinking_level: str

class SmartAIService:
    def __init__(self):
        self.settings = get_settings()
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(SmartAIState)

        workflow.add_node("assess_confidence", self._assess_confidence_node)
        workflow.add_node("check_mission_contradiction", self._check_mission_contradiction_node)
        workflow.add_node("should_pause", self._should_pause_node)
        workflow.add_node("determine_thinking_level", self._determine_thinking_level_node)

        workflow.set_entry_point("assess_confidence")
        workflow.add_edge("assess_confidence", "check_mission_contradiction")
        workflow.add_edge("check_mission_contradiction", "should_pause")
        
        workflow.add_conditional_edges(
            "should_pause",
            lambda state: "determine_thinking_level" if not state["should_pause"] else END,
            {"determine_thinking_level": "determine_thinking_level", "end": END}
        )
        workflow.add_edge("determine_thinking_level", END)

        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)

    async def _assess_confidence_node(self, state: SmartAIState) -> Dict[str, Any]:
        score, level, reasoning = await self.assess_confidence(state)
        return {"confidence_score": score, "confidence_level": level, "reasoning": reasoning}

    async def _check_mission_contradiction_node(self, state: SmartAIState) -> Dict[str, Any]:
        has_contradiction, contradiction_score, analysis_text, confirmation_prompt = await self.check_mission_contradiction(state)
        return {
            "has_contradiction": has_contradiction,
            "contradiction_score": contradiction_score,
            "analysis_text": analysis_text,
            "confirmation_prompt": confirmation_prompt
        }

    async def _should_pause_node(self, state: SmartAIState) -> Dict[str, Any]:
        should_pause, reason, message = await self.should_pause_for_human_input(state)
        return {"should_pause": should_pause, "pause_reason": reason, "pause_message": message}

    async def _determine_thinking_level_node(self, state: SmartAIState) -> Dict[str, Any]:
        thinking_level = await self.determine_adaptive_thinking_level(state)
        return {"thinking_level": thinking_level}

    async def process_request(self, user_input: str, context: str = "") -> Dict[str, Any]:
        config = {"configurable": {"thread_id": "1"}}
        initial_state = {"user_input": user_input, "context": context}
        final_state = await self.graph.ainvoke(initial_state, config)
        return final_state

    # ... keep the helper methods like assess_confidence, check_mission_contradiction, etc.

smart_ai_service = SmartAIService()