#!/usr/bin/env python3
"""
LangGraph Nodes for Parsing Assessment Workflow

These nodes implement an intelligent parsing assessment and improvement
workflow using LangGraph's state management and routing capabilities.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from langgraph.graph import StateGraph, END
from worker.graph_types import GraphState
from worker.services.parsing_assessment_service import (
    parsing_assessment_service, 
    ParseAction, 
    ParseAssessment
)

logger = logging.getLogger(__name__)

async def parsing_assessment_node(state: GraphState) -> GraphState:
    """
    LangGraph node that assesses the quality of parsing results
    and decides what action to take next.
    """
    logger.info("🎯 Executing parsing assessment node")
    
    try:
        # Get the original parsing results from state
        original_text = getattr(state, 'original_parsing_text', '') or state.user_input
        parsing_results = getattr(state, 'parsing_results', {})
        target_intent = getattr(state, 'target_intent', 'calendar')
        
        logger.info(f"📝 Original text length: {len(original_text)} characters")
        logger.info(f"📊 Parsing results keys: {list(parsing_results.keys())}")
        logger.info(f"🎯 Target intent: {target_intent}")
        
        if not parsing_results:
            logger.warning("❌ No parsing results found in state")
            state.assessment_action = "error"
            state.assessment_reason = "No parsing results to assess"
            return state
        
        # Log current parsing state
        ready_items = parsing_results.get("ready_for_tools", {})
        logger.info(f"📋 Items ready for tools: {[(tool, len(items)) for tool, items in ready_items.items()]}")
        
        # Perform LLM assessment
        logger.info("🧠 Calling parsing assessment service...")
        assessment = await parsing_assessment_service.assess_parsing_results(
            state, original_text, parsing_results, target_intent
        )
        
        # Store assessment in state
        state.parsing_assessment = assessment
        state.assessment_action = assessment.action.value
        state.assessment_quality_score = assessment.quality_score
        state.assessment_confidence = assessment.confidence
        state.assessment_issues = assessment.issues_found
        state.assessment_reason = assessment.reason
        state.supplement_data = assessment.supplement_data
        
        logger.info(f"✅ Assessment complete: {assessment.action.value} (quality: {assessment.quality_score:.2f}, confidence: {assessment.confidence:.2f})")
        logger.info(f"📋 Assessment reason: {assessment.reason}")
        if assessment.issues_found:
            logger.info(f"⚠️ Issues found: {assessment.issues_found}")
        
        # Add to dynamic results
        dynamic_results = getattr(state, 'dynamic_results', [])
        dynamic_results.append({
            "node_type": "parsing_assessment",
            "action": assessment.action.value,
            "quality_score": assessment.quality_score,
            "confidence": assessment.confidence,
            "issues_found": assessment.issues_found,
            "timestamp": datetime.now().isoformat()
        })
        state.dynamic_results = dynamic_results
        
        return state
        
    except Exception as e:
        logger.error(f"💥 Error in parsing assessment node: {e}", exc_info=True)
        state.assessment_action = "error"
        state.assessment_reason = f"Assessment failed: {str(e)}"
        return state

async def parsing_supplement_node(state: GraphState) -> GraphState:
    """
    LangGraph node that supplements missing data in parsing results
    using LLM intelligence.
    """
    logger.info("Executing parsing supplement node")
    
    try:
        original_text = getattr(state, 'original_parsing_text', '') or state.user_input
        parsing_results = getattr(state, 'parsing_results', {})
        supplement_data = getattr(state, 'supplement_data', {})
        
        # Supplement the parsing data
        supplemented = await parsing_assessment_service.supplement_parsing_data(
            state, original_text, parsing_results, supplement_data
        )
        
        # Merge supplemented data with existing results
        from worker.services.parsing_assessment_service import _merge_supplemented_data
        enhanced_results = _merge_supplemented_data(parsing_results, supplemented)
        
        # Update state with enhanced results
        state.parsing_results = enhanced_results
        state.parsing_action_taken = "supplemented"
        state.supplement_summary = supplemented.get("extraction_summary", "")
        
        logger.info(f"Supplementation complete: {supplemented.get('extraction_summary', '')}")
        
        # Add to dynamic results
        dynamic_results = getattr(state, 'dynamic_results', [])
        dynamic_results.append({
            "node_type": "parsing_supplement",
            "success": True,
            "additional_items": len(supplemented.get("additional_items", [])),
            "enhanced_items": len(supplemented.get("enhanced_existing", [])),
            "summary": supplemented.get("extraction_summary", ""),
            "timestamp": datetime.now().isoformat()
        })
        state.dynamic_results = dynamic_results
        
        return state
        
    except Exception as e:
        logger.error(f"Error in parsing supplement node: {e}", exc_info=True)
        state.parsing_action_taken = "supplement_failed"
        state.supplement_error = str(e)
        return state

async def parsing_reparse_node(state: GraphState) -> GraphState:
    """
    LangGraph node that re-parses the original text using LLM
    when the initial parsing was insufficient.
    """
    logger.info("🔄 Executing parsing reparse node")
    
    try:
        original_text = getattr(state, 'original_parsing_text', '') or state.user_input
        target_intent = getattr(state, 'target_intent', 'calendar')
        
        logger.info(f"🔄 Reparse triggered for target: {target_intent}")
        logger.info(f"📝 Text to reparse length: {len(original_text)} characters")
        logger.info(f"📝 Text preview: {original_text[:300]}...")
        
        # Use LLM to reparse from scratch
        if target_intent == "calendar":
            logger.info("📅 Using LLM calendar parser for reparse...")
            from worker.services.llm_calendar_parser import parse_calendar_events_with_llm
            
            logger.info("🚀 Calling LLM calendar parser...")
            llm_results = await parse_calendar_events_with_llm(state, original_text)
            
            logger.info(f"🤖 LLM reparse results: success={llm_results.get('success')}")
            logger.info(f"🤖 LLM parsing method: {llm_results.get('parsing_method', 'unknown')}")
            
        else:
            # For other intents, could add more specialized parsers
            logger.warning(f"❌ No LLM parser available for intent: {target_intent}")
            llm_results = {"success": False, "response": "No LLM parser available for this intent"}
        
        if llm_results.get("success"):
            # Replace parsing results with LLM results
            logger.info("✅ Reparse successful - updating state with new results")
            
            state.parsing_results = llm_results
            state.parsing_action_taken = "reparsed"
            state.reparse_success = True
            
            event_count = llm_results.get('event_count', len(llm_results.get('events', [])))
            logger.info(f"🎉 Reparsing successful: {event_count} items found")
            
            # Log the events found
            events = llm_results.get('events', [])
            for i, event in enumerate(events[:5]):  # Log first 5 events
                title = event.get('title', 'NO_TITLE') if isinstance(event, dict) else getattr(event, 'title', 'NO_TITLE')
                date = event.get('date', 'NO_DATE') if isinstance(event, dict) else getattr(event, 'date', 'NO_DATE')
                logger.debug(f"📅 Reparsed event {i+1}: {title} - {date}")
            
        else:
            # Keep original results as fallback
            logger.warning("❌ Reparse failed - keeping original results")
            
            state.parsing_action_taken = "reparse_failed"
            state.reparse_success = False
            state.reparse_error = llm_results.get("response", "Unknown error")
            
            logger.warning(f"🔄 Reparsing failed: {llm_results.get('response', '')}")
            logger.warning(f"🔄 Error details: {llm_results.get('error', 'No error details')}")
        
        # Add to dynamic results
        dynamic_results = getattr(state, 'dynamic_results', [])
        dynamic_results.append({
            "node_type": "parsing_reparse",
            "success": llm_results.get("success", False),
            "items_found": llm_results.get("event_count", len(llm_results.get('events', []))) if llm_results.get("success") else 0,
            "method": "llm_reparse",
            "parsing_method": llm_results.get("parsing_method", "unknown"),
            "timestamp": datetime.now().isoformat()
        })
        state.dynamic_results = dynamic_results
        
        logger.info(f"🔄 Reparse node completed: action={state.parsing_action_taken}")
        return state
        
    except Exception as e:
        logger.error(f"💥 Error in parsing reparse node: {e}", exc_info=True)
        state.parsing_action_taken = "reparse_error"
        state.reparse_error = str(e)
        return state

async def parsing_finalization_node(state: GraphState) -> GraphState:
    """
    LangGraph node that finalizes the parsing workflow and
    prepares results for the next stage (e.g., calendar creation).
    """
    logger.info("Executing parsing finalization node")
    
    try:
        parsing_results = getattr(state, 'parsing_results', {})
        action_taken = getattr(state, 'parsing_action_taken', 'unknown')
        target_intent = getattr(state, 'target_intent', 'calendar')
        
        # Prepare final response based on action taken
        if action_taken == "accepted":
            final_response = "✅ **Initial parsing was sufficient**\n\n" + parsing_results.get("response", "")
        elif action_taken == "supplemented":
            supplement_summary = getattr(state, 'supplement_summary', '')
            final_response = f"🔍 **Parsing enhanced with LLM assistance**\n\n{parsing_results.get('response', '')}\n\n**Enhancement**: {supplement_summary}"
        elif action_taken == "reparsed":
            final_response = f"🧠 **Re-parsed using LLM intelligence**\n\n{parsing_results.get('response', '')}"
        else:
            final_response = parsing_results.get("response", "Parsing completed")
        
        # Store final results
        state.final_parsing_response = final_response
        state.parsing_workflow_complete = True
        
        # If this was for calendar creation, prepare for next stage
        if target_intent == "calendar" and parsing_results.get("events"):
            state.ready_for_calendar_creation = True
            state.calendar_events_data = parsing_results.get("events", [])
        
        logger.info(f"Parsing workflow finalized: {action_taken}")
        
        # Add to dynamic results
        dynamic_results = getattr(state, 'dynamic_results', [])
        dynamic_results.append({
            "node_type": "parsing_finalization",
            "action_taken": action_taken,
            "ready_for_next_stage": target_intent == "calendar" and parsing_results.get("events", []),
            "final_item_count": len(parsing_results.get("events", [])),
            "timestamp": datetime.now().isoformat()
        })
        state.dynamic_results = dynamic_results
        
        return state
        
    except Exception as e:
        logger.error(f"Error in parsing finalization node: {e}", exc_info=True)
        state.final_parsing_response = f"Parsing finalization failed: {str(e)}"
        return state

def parsing_assessment_routing(state: GraphState) -> str:
    """
    LangGraph routing function that determines the next node
    based on assessment results.
    """
    assessment_action = getattr(state, 'assessment_action', 'error')
    
    logger.info(f"🔀 Routing assessment action: '{assessment_action}'")
    
    if assessment_action == "accept":
        logger.info("🔀 Routing to finalize (accept)")
        return "finalize"
    elif assessment_action == "supplement":
        logger.info("🔀 Routing to supplement")
        return "supplement"
    elif assessment_action in ["reparse", "enhance"]:
        logger.info(f"🔀 Routing to reparse (action: {assessment_action})")
        return "reparse"
    else:
        # Error case or unknown action
        logger.warning(f"🔀 Unknown assessment action '{assessment_action}', routing to finalize")
        return "finalize"

def create_parsing_assessment_workflow() -> StateGraph:
    """
    Create a LangGraph workflow for intelligent parsing assessment
    and improvement.
    """
    workflow = StateGraph(GraphState)
    
    # Add nodes
    workflow.add_node("assess", parsing_assessment_node)
    workflow.add_node("supplement", parsing_supplement_node)
    workflow.add_node("reparse", parsing_reparse_node)
    workflow.add_node("finalize", parsing_finalization_node)
    
    # Set entry point
    workflow.set_entry_point("assess")
    
    # Add conditional routing based on assessment
    workflow.add_conditional_edges(
        "assess",
        parsing_assessment_routing,
        {
            "finalize": "finalize",
            "supplement": "supplement",
            "reparse": "reparse"
        }
    )
    
    # After supplement or reparse, go to finalize
    workflow.add_edge("supplement", "finalize")
    workflow.add_edge("reparse", "finalize")
    
    # End after finalization
    workflow.add_edge("finalize", END)
    
    return workflow

# Global workflow instance
parsing_assessment_workflow = create_parsing_assessment_workflow()

# Convenience function to run the assessment workflow
async def run_parsing_assessment_workflow(
    state: GraphState,
    original_text: str,
    parsing_results: Dict[str, Any],
    target_intent: str = "calendar"
) -> GraphState:
    """
    Run the complete parsing assessment workflow using LangGraph
    """
    # Prepare state for workflow
    state.original_parsing_text = original_text
    state.parsing_results = parsing_results
    state.target_intent = target_intent
    
    # Compile and run workflow
    app = parsing_assessment_workflow.compile()
    result_state = await app.ainvoke(state)
    
    return result_state