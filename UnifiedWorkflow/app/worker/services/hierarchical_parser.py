"""
Hierarchical Parser with Robust Fallback Chain

This service implements a hierarchical parsing strategy, attempting to process
input with a series of increasingly general parsers. This ensures that even
if a highly specialized parser fails, the system can fall back to a more
general one, maximizing the chances of a successful parse.

Parser Hierarchy (most specific to most general):
1. Intelligent List Parser - handles complex structured lists with inheritance
2. LLM Calendar Parser - specialized for calendar/scheduling content
3. Opportunity Subtask Parser - generates contextual subtasks for opportunities
4. Generic LLM Parser - fallback for any text processing needs
"""

import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple, TypedDict, Annotated
from dataclasses import dataclass, field
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from worker.services.intelligent_list_parser import intelligent_list_parser, handle_list_parsing_request
from worker.services.llm_calendar_parser import llm_calendar_parser, handle_llm_calendar_parsing
from worker.services.opportunity_subtask_service import generate_contextual_subtasks
from worker.services.ollama_service import invoke_llm_with_tokens
from worker.services.parser_performance_monitor import (
    parser_performance_monitor, ParseOutcome, start_monitoring_session, 
    record_parser_performance, end_monitoring_session
)
from worker.graph_types import GraphState
from shared.database.models import User

logger = logging.getLogger(__name__)

class ParserState(TypedDict):
    text: str
    user_context: str
    target_parsers: List[str]
    attempted_parsers: List[str]
    result: Dict[str, Any]
    error: str
    next_parser: str

class HierarchicalParser:
    def __init__(self):
        self.graph = self._build_graph()
        self.parser_configs = {
            "intelligent_list": {
                "handler": self._handle_intelligent_list,
                "priority": 100,
                "description": "Complex structured lists with inheritance patterns",
                "triggers": ["due:", "assignments", "sections", "\n-", "\n*", "\n1."],
                "confidence_threshold": 0.8
            },
            "llm_calendar": {
                "handler": self._handle_llm_calendar,
                "priority": 90,
                "description": "LLM-powered calendar event extraction",
                "triggers": ["calendar", "schedule", "due", "deadline", "event", "appointment"],
                "confidence_threshold": 0.7
            },
            "opportunity_subtask": {
                "handler": self._handle_opportunity_subtask,
                "priority": 80,
                "description": "Contextual subtask generation for opportunities",
                "triggers": ["subtask", "opportunity", "break down", "steps", "plan"],
                "confidence_threshold": 0.6
            },
            "generic_llm": {
                "handler": self._handle_generic_llm,
                "priority": 10,
                "description": "Generic LLM processing for any text",
                "triggers": [],
                "confidence_threshold": 0.5
            }
        }

    def _build_graph(self):
        workflow = StateGraph(ParserState)

        workflow.add_node("router", self._router_node)
        workflow.add_node("intelligent_list", self._intelligent_list_node)
        workflow.add_node("llm_calendar", self._llm_calendar_node)
        workflow.add_node("opportunity_subtask", self._opportunity_subtask_node)
        workflow.add_node("generic_llm", self._generic_llm_node)
        workflow.add_node("fallback", self._fallback_node)

        workflow.set_entry_point("router")

        workflow.add_conditional_edges(
            "router",
            lambda state: state["next_parser"],
            {
                "intelligent_list": "intelligent_list",
                "llm_calendar": "llm_calendar",
                "opportunity_subtask": "opportunity_subtask",
                "generic_llm": "generic_llm",
                "fallback": "fallback",
                "end": END
            }
        )
        
        for parser_name in self.parser_configs.keys():
            workflow.add_conditional_edges(
                parser_name,
                lambda state: "router" if state.get("error") else "end",
                {"router": "router", "end": END}
            )
        
        workflow.add_edge("fallback", END)

        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)

    async def _router_node(self, state: ParserState) -> Dict[str, Any]:
        attempted_parsers = state.get("attempted_parsers", [])
        parser_order = self._auto_detect_parsers(state["text"], state["user_context"])
        
        for parser in parser_order:
            if parser not in attempted_parsers:
                return {"next_parser": parser, "attempted_parsers": attempted_parsers + [parser]}
        
        return {"next_parser": "fallback"}

    async def _intelligent_list_node(self, state: ParserState) -> Dict[str, Any]:
        result = await self._handle_intelligent_list(state, state["text"], state["user_context"])
        if result.get("success"):
            return {"result": result, "error": None}
        return {"error": result.get("error", "Failed"), "result": result}

    async def _llm_calendar_node(self, state: ParserState) -> Dict[str, Any]:
        result = await self._handle_llm_calendar(state, state["text"], state["user_context"])
        if result.get("success"):
            return {"result": result, "error": None}
        return {"error": result.get("error", "Failed"), "result": result}

    async def _opportunity_subtask_node(self, state: ParserState) -> Dict[str, Any]:
        result = await self._handle_opportunity_subtask(state, state["text"], state["user_context"])
        if result.get("success"):
            return {"result": result, "error": None}
        return {"error": result.get("error", "Failed"), "result": result}

    async def _generic_llm_node(self, state: ParserState) -> Dict[str, Any]:
        result = await self._handle_generic_llm(state, state["text"], state["user_context"])
        if result.get("success"):
            return {"result": result, "error": None}
        return {"error": result.get("error", "Failed"), "result": result}

    async def _fallback_node(self, state: ParserState) -> Dict[str, Any]:
        result = await self._generic_fallback(state, state["text"], state["user_context"])
        return {"result": result.result_data}

    async def parse_with_fallback(self, state: GraphState, text: str, user_context: str = "", target_parsers: List[str] = None) -> Dict[str, Any]:
        config = {"configurable": {"thread_id": "1"}}
        initial_state = {
            "text": text,
            "user_context": user_context,
            "target_parsers": target_parsers or [],
            "attempted_parsers": [],
            "result": {},
            "error": None,
            "next_parser": ""
        }
        final_state = await self.graph.ainvoke(initial_state, config)
        return final_state["result"]

    # ... keep the helper methods like _auto_detect_parsers, _handle_*, etc.

hierarchical_parser = HierarchicalParser()