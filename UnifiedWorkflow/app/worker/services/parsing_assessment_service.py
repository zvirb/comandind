
import json
import logging
from typing import Any, Dict, List, Optional, Tuple, TypedDict, Annotated
from dataclasses import dataclass
from enum import Enum
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from worker.services.ollama_service import invoke_llm_with_tokens
from worker.graph_types import GraphState

logger = logging.getLogger(__name__)

class ParseAction(Enum):
    ACCEPT = "accept"
    SUPPLEMENT = "supplement"
    REPARSE = "reparse"
    ENHANCE = "enhance"

class AssessmentState(TypedDict):
    original_text: str
    parsing_results: Dict[str, Any]
    target_intent: str
    assessment: Dict[str, Any]
    final_results: Dict[str, Any]
    error: str

class ParsingAssessmentService:
    def __init__(self):
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AssessmentState)

        workflow.add_node("assess_quality", self._assess_quality_node)
        workflow.add_node("supplement_data", self._supplement_data_node)
        workflow.add_node("reparse_text", self._reparse_text_node)
        workflow.add_node("finalize_results", self._finalize_results_node)

        workflow.set_entry_point("assess_quality")

        workflow.add_conditional_edges(
            "assess_quality",
            lambda state: state["assessment"].get("action", "accept"),
            {
                "accept": "finalize_results",
                "supplement": "supplement_data",
                "reparse": "reparse_text",
                "enhance": "reparse_text" # For now, enhance will also trigger reparse
            }
        )
        
        workflow.add_edge("supplement_data", "finalize_results")
        workflow.add_edge("reparse_text", "finalize_results")
        workflow.add_edge("finalize_results", END)

        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)

    async def _assess_quality_node(self, state: AssessmentState) -> Dict[str, Any]:
        assessment = await self.assess_parsing_results(
            state, state["original_text"], state["parsing_results"], state["target_intent"]
        )
        return {"assessment": assessment.__dict__}

    async def _supplement_data_node(self, state: AssessmentState) -> Dict[str, Any]:
        supplemented = await self.supplement_parsing_data(
            state, state["original_text"], state["parsing_results"], state["assessment"].get("supplement_data", {})
        )
        final_results = self._merge_supplemented_data(state["parsing_results"], supplemented)
        return {"final_results": final_results}

    async def _reparse_text_node(self, state: AssessmentState) -> Dict[str, Any]:
        from worker.services.hierarchical_parser import hierarchical_parser
        parser_results = await hierarchical_parser.parse_with_fallback(state, state["original_text"], state.get("user_context", ""))
        return {"final_results": parser_results}

    async def _finalize_results_node(self, state: AssessmentState) -> Dict[str, Any]:
        if not state.get("final_results"):
            return {"final_results": state["parsing_results"]}
        return {}

    async def assess_and_improve_parsing(self, state: GraphState, original_text: str, parsing_results: Dict[str, Any], target_intent: str = "calendar") -> Tuple[Dict[str, Any], str]:
        config = {"configurable": {"thread_id": "1"}}
        initial_state = {
            "original_text": original_text,
            "parsing_results": parsing_results,
            "target_intent": target_intent,
            "assessment": {},
            "final_results": {},
            "error": None
        }
        final_state = await self.graph.ainvoke(initial_state, config)
        action_taken = final_state["assessment"].get("action", "accept")
        return final_state["final_results"], action_taken

    # ... keep the helper methods like assess_parsing_results, _llm_assess_results, etc.

parsing_assessment_service = ParsingAssessmentService()
