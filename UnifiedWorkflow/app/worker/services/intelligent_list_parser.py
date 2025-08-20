#!/usr/bin/env python3
"""
Intelligent List Parser Tool

This tool can parse complex hierarchical lists and understand how to combine
parent and child information to create complete data structures ready for
calendar events, tasks, or any other tool consumption.

Examples it handles:
1. Subject sections with assignment topics and dates
2. Project phases with multiple tasks
3. Event categories with specific items
4. Hierarchical data with inheritance patterns
"""

import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field

from worker.services.ollama_service import invoke_llm_with_tokens
from worker.graph_types import GraphState

logger = logging.getLogger(__name__)

@dataclass
class ParsedListItem:
    """Represents a parsed list item with inherited information"""
    title: str
    description: str = ""
    parent_context: Dict[str, Any] = field(default_factory=dict)
    inherited_data: Dict[str, Any] = field(default_factory=dict)
    level: int = 0
    item_type: str = "item"  # item, section, subsection, etc.
    raw_text: str = ""
    confidence_score: float = 0.8
    ready_for_tool: bool = False
    target_tool: str = ""
    complete_data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ListParsingResult:
    """Result of parsing a hierarchical list"""
    parsed_items: List[ParsedListItem]
    inheritance_patterns: Dict[str, Any]
    ready_for_tools: Dict[str, List[ParsedListItem]]  # tool_name -> items
    parsing_summary: str
    requires_user_input: bool = False
    missing_information: List[str] = field(default_factory=list)

class IntelligentListParser:
    """Intelligent parser for hierarchical lists with data inheritance"""
    
    def __init__(self):
        self.common_patterns = {
            "date_patterns": [
                r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',  # MM/DD/YYYY or MM-DD-YYYY
                r'\b(\w+day,?\s+\w+\s+\d{1,2})\b',  # Monday, January 15
                r'\b(due:?\s*\w+\s+\d{1,2})\b',  # due: January 15
                r'\b(\d{1,2}(?:st|nd|rd|th)?\s+\w+)\b',  # 15th January
            ],
            "time_patterns": [
                r'\b(\d{1,2}:\d{2}\s*(?:am|pm|AM|PM))\b',  # 2:30 PM
                r'\b(\d{1,2}\s*(?:am|pm|AM|PM))\b',  # 2 PM
                r'\b(at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?)\b',  # at 2:30 PM
            ],
            "priority_patterns": [
                r'\b(urgent|asap|high\s+priority|critical)\b',
                r'\b(low\s+priority|when\s+possible|optional)\b',
            ]
        }
    
    async def parse_hierarchical_list(self, state: GraphState, raw_list: str, target_tools: List[str] = None) -> ListParsingResult:
        """
        Parse a hierarchical list understanding inheritance patterns
        
        Args:
            state: Current graph state
            raw_list: The raw list text to parse
            target_tools: List of target tools (e.g., ['calendar', 'task_management'])
        """
        logger.info(f"🔍 Parsing hierarchical list for tools: {target_tools}")
        logger.info(f"📝 Input text length: {len(raw_list)} characters")
        
        try:
            # First, analyze the structure and inheritance patterns
            logger.info("📊 Analyzing list structure and inheritance patterns...")
            structure_analysis = await self._analyze_list_structure(state, raw_list, target_tools)
            logger.info(f"📊 Structure analysis completed: {structure_analysis.get('list_type', 'unknown')}")
            
            # Parse individual items with context
            logger.info("📋 Parsing individual items with context...")
            parsed_items = await self._parse_items_with_inheritance(state, raw_list, structure_analysis)
            logger.info(f"📋 Parsed {len(parsed_items)} individual items")
            
            # Apply inheritance rules
            logger.info("🔗 Applying inheritance patterns...")
            items_with_inheritance = self._apply_inheritance_patterns(parsed_items, structure_analysis)
            logger.info(f"🔗 Applied inheritance to {len(items_with_inheritance)} items")
            
            # Prepare items for specific tools
            logger.info("🛠️ Preparing items for target tools...")
            ready_for_tools = await self._prepare_for_tools(state, items_with_inheritance, target_tools)
            
            # Log tool readiness
            for tool, items in ready_for_tools.items():
                logger.info(f"🛠️ {tool}: {len(items)} items ready")
            
            # Check for missing information
            logger.info("⚠️ Checking for missing information...")
            missing_info, requires_input = self._identify_missing_information(items_with_inheritance, target_tools)
            
            if missing_info:
                logger.warning(f"⚠️ Missing information detected: {missing_info}")
            
            # Generate summary
            summary = self._generate_parsing_summary(items_with_inheritance, ready_for_tools, missing_info)
            
            result = ListParsingResult(
                parsed_items=items_with_inheritance,
                inheritance_patterns=structure_analysis.get("inheritance_patterns", {}),
                ready_for_tools=ready_for_tools,
                parsing_summary=summary,
                requires_user_input=requires_input,
                missing_information=missing_info
            )
            
            logger.info(f"✅ Hierarchical parsing completed successfully")
            logger.info(f"✅ Total items: {len(result.parsed_items)}, Ready for tools: {sum(len(items) for items in result.ready_for_tools.values())}")
            
            return result
            
        except Exception as e:
            logger.error(f"💥 Error parsing hierarchical list: {e}", exc_info=True)
            logger.error(f"💥 Failed input preview: {raw_list[:300]}...")
            
            # Enhanced fallback with basic regex patterns
            logger.warning("🔄 Attempting basic regex fallback parsing...")
            fallback_items = self._basic_regex_fallback(raw_list, target_tools)
            
            # Return fallback result
            fallback_result = ListParsingResult(
                parsed_items=fallback_items,
                inheritance_patterns={},
                ready_for_tools={"calendar": fallback_items} if "calendar" in (target_tools or []) else {},
                parsing_summary=f"⚠️ Used basic regex fallback parsing: found {len(fallback_items)} items. Original error: {str(e)}",
                requires_user_input=len(fallback_items) == 0,
                missing_information=["Advanced parsing failed, used basic patterns"] if fallback_items else ["Could not parse the provided list. Please provide a clearer format."]
            )
            
            logger.info(f"🔄 Fallback parsing found {len(fallback_items)} items")
            return fallback_result
    
    async def _analyze_list_structure(self, state: GraphState, raw_list: str, target_tools: List[str]) -> Dict[str, Any]:
        """Analyze the hierarchical structure and inheritance patterns"""
        
        analysis_prompt = f"""You are an expert list structure analyzer. Analyze this hierarchical list to understand its structure and data inheritance patterns.

List to analyze:
{raw_list}

Target tools: {target_tools or ['general']}

Respond with JSON in this exact format:
{{
  "structure_analysis": {{
    "list_type": "subject_assignments/project_phases/event_categories/mixed_hierarchy",
    "hierarchy_levels": {{
      "level_0": "description of top level (e.g., 'Subject sections')",
      "level_1": "description of first sublevel (e.g., 'Assignment topics')", 
      "level_2": "description of second sublevel (e.g., 'Due dates')"
    }},
    "inheritance_patterns": {{
      "parent_to_child": {{
        "subject": "inherits from section header",
        "date": "inherits from parent or uses default",
        "priority": "inherits from context",
        "location": "inherits from section"
      }},
      "data_flow": "top_down/bottom_up/mixed",
      "missing_data_strategy": "inherit/prompt/default"
    }},
    "detected_entities": {{
      "dates": ["list of detected dates"],
      "times": ["list of detected times"],
      "subjects": ["list of subjects/categories"],
      "priorities": ["list of priority indicators"],
      "locations": ["list of locations"]
    }},
    "parsing_strategy": {{
      "primary_approach": "hierarchical_inheritance/flat_combination/context_aware",
      "inheritance_rules": [
        "Rule 1: Assignment topics inherit subject from section header",
        "Rule 2: Due dates apply to all items in section unless specified"
      ],
      "completeness_check": {{
        "calendar_ready": "what's needed for calendar events",
        "task_ready": "what's needed for task creation"
      }}
    }}
  }}
}}

Guidelines:
- Identify hierarchical levels (sections, subsections, items)
- Determine what information flows from parent to child
- Look for patterns like:
  * Subject sections with assignment lists
  * Project phases with task breakdowns  
  * Event categories with specific items
  * Date/time information at different levels
- Understand inheritance: does subject come from header? Does date apply to all items?
- Consider target tools: calendar needs dates/times, tasks need priorities/due dates"""

        try:
            model_name = getattr(state, 'tool_selection_model', 'llama3.2:3b')
            
            response, _ = await invoke_llm_with_tokens(
                messages=[
                    {"role": "system", "content": "You are a list structure analysis expert. Always respond with valid JSON only."},
                    {"role": "user", "content": analysis_prompt}
                ],
                model_name=model_name,
                category="list_structure_analysis"
            )
            
            # Parse JSON response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                analysis_data = json.loads(json_str)
                return analysis_data.get("structure_analysis", {})
            else:
                raise ValueError("Could not parse structure analysis response")
                
        except Exception as e:
            logger.error(f"Error in structure analysis: {e}")
            # Return fallback analysis
            return {
                "list_type": "mixed_hierarchy",
                "hierarchy_levels": {"level_0": "sections", "level_1": "items"},
                "inheritance_patterns": {"parent_to_child": {"context": "inherits from parent"}},
                "parsing_strategy": {"primary_approach": "hierarchical_inheritance"}
            }
    
    async def _parse_items_with_inheritance(self, state: GraphState, raw_list: str, structure_analysis: Dict[str, Any]) -> List[ParsedListItem]:
        """Parse individual items while tracking hierarchical context"""
        
        parsing_prompt = f"""You are an expert list item parser. Parse each item in this hierarchical list, understanding the context and inheritance patterns.

List to parse:
{raw_list}

Structure analysis: {json.dumps(structure_analysis, indent=2)}

Parse each item and respond with JSON:
{{
  "parsed_items": [
    {{
      "title": "Clean, concise title for this item",
      "description": "Additional details if available",
      "level": 0,
      "item_type": "section/subsection/item/task",
      "raw_text": "Original text for this item",
      "parent_context": {{
        "subject": "Subject/category from parent section",
        "section_header": "The section this item belongs to",
        "inherited_date": "Date that applies from parent",
        "inherited_priority": "Priority from context"
      }},
      "extracted_data": {{
        "dates": ["any dates found in this item"],
        "times": ["any times found in this item"], 
        "priorities": ["any priority indicators"],
        "locations": ["any locations mentioned"],
        "subjects": ["subject/category indicators"]
      }},
      "confidence_score": 0.0-1.0
    }}
  ]
}}

Guidelines:
- Parse EVERY item, section header, and subsection
- Track hierarchy level (0 = main sections, 1 = subsections, 2 = items, etc.)
- Extract parent context (what section/category does this belong to?)
- Find all dates, times, priorities, locations in each item
- Use the structure analysis to understand inheritance patterns
- Be thorough - don't miss any items or context"""

        try:
            model_name = getattr(state, 'tool_selection_model', 'llama3.2:3b')
            
            response, _ = await invoke_llm_with_tokens(
                messages=[
                    {"role": "system", "content": "You are a hierarchical list parsing expert. Always respond with valid JSON only."},
                    {"role": "user", "content": parsing_prompt}
                ],
                model_name=model_name,
                category="list_item_parsing"
            )
            
            # Parse JSON response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                parsed_data = json.loads(json_str)
                
                # Convert to ParsedListItem objects
                items = []
                for item_data in parsed_data.get("parsed_items", []):
                    item = ParsedListItem(
                        title=item_data.get("title", ""),
                        description=item_data.get("description", ""),
                        level=item_data.get("level", 0),
                        item_type=item_data.get("item_type", "item"),
                        raw_text=item_data.get("raw_text", ""),
                        parent_context=item_data.get("parent_context", {}),
                        confidence_score=item_data.get("confidence_score", 0.8)
                    )
                    
                    # Store extracted data for later inheritance processing
                    item.inherited_data = item_data.get("extracted_data", {})
                    items.append(item)
                
                return items
            else:
                raise ValueError("Could not parse items response")
                
        except Exception as e:
            logger.error(f"Error parsing items: {e}")
            # Return basic parsing fallback
            lines = raw_list.strip().split('\n')
            items = []
            for i, line in enumerate(lines):
                if line.strip():
                    items.append(ParsedListItem(
                        title=line.strip(),
                        raw_text=line,
                        level=0,
                        confidence_score=0.5
                    ))
            return items
    
    def _apply_inheritance_patterns(self, items: List[ParsedListItem], structure_analysis: Dict[str, Any]) -> List[ParsedListItem]:
        """Apply inheritance patterns to combine parent and child data"""
        
        inheritance_patterns = structure_analysis.get("inheritance_patterns", {})
        parent_to_child = inheritance_patterns.get("parent_to_child", {})
        
        # Build hierarchy map
        hierarchy_map = {}
        for i, item in enumerate(items):
            level = item.level
            if level not in hierarchy_map:
                hierarchy_map[level] = []
            hierarchy_map[level].append((i, item))
        
        # Apply inheritance from top to bottom
        for level in sorted(hierarchy_map.keys()):
            for item_idx, item in hierarchy_map[level]:
                if level > 0:  # Has potential parents
                    # Find parent items (items at level-1 that come before this item)
                    parent_items = []
                    for parent_level in range(level-1, -1, -1):
                        if parent_level in hierarchy_map:
                            for parent_idx, parent_item in hierarchy_map[parent_level]:
                                if parent_idx < item_idx:
                                    parent_items.append(parent_item)
                                    break  # Take the most recent parent at each level
                    
                    # Apply inheritance rules
                    combined_data = {}
                    
                    # Inherit from parent context
                    for parent in parent_items:
                        # Inherit subject/category
                        if parent.item_type in ["section", "subsection"] and not combined_data.get("subject"):
                            combined_data["subject"] = parent.title
                        
                        # Inherit dates if not present in current item
                        parent_dates = parent.inherited_data.get("dates", [])
                        if parent_dates and not item.inherited_data.get("dates"):
                            combined_data["inherited_dates"] = parent_dates
                        
                        # Inherit other context
                        for key, value in parent.parent_context.items():
                            if value and not combined_data.get(key):
                                combined_data[key] = value
                    
                    # Combine with item's own data
                    item.complete_data = {
                        "title": item.title,
                        "description": item.description,
                        "subject": combined_data.get("subject", item.parent_context.get("subject", "")),
                        "dates": item.inherited_data.get("dates", combined_data.get("inherited_dates", [])),
                        "times": item.inherited_data.get("times", []),
                        "priorities": item.inherited_data.get("priorities", []),
                        "locations": item.inherited_data.get("locations", []),
                        "raw_text": item.raw_text,
                        "level": item.level,
                        "item_type": item.item_type
                    }
                else:
                    # Top level item - use its own data
                    item.complete_data = {
                        "title": item.title,
                        "description": item.description,
                        "dates": item.inherited_data.get("dates", []),
                        "times": item.inherited_data.get("times", []),
                        "priorities": item.inherited_data.get("priorities", []),
                        "locations": item.inherited_data.get("locations", []),
                        "raw_text": item.raw_text,
                        "level": item.level,
                        "item_type": item.item_type
                    }
        
        return items
    
    async def _prepare_for_tools(self, state: GraphState, items: List[ParsedListItem], target_tools: List[str]) -> Dict[str, List[ParsedListItem]]:
        """Prepare parsed items for specific tools (calendar, task management, etc.)"""
        
        ready_for_tools = {}
        
        if not target_tools:
            target_tools = ["general"]
        
        for tool in target_tools:
            ready_items = []
            
            for item in items:
                # Skip section headers unless they have actionable content
                if item.item_type in ["section", "subsection"] and not item.complete_data.get("dates"):
                    continue
                
                # Prepare for calendar tool
                if tool == "calendar" or tool == "calendar_tool":
                    if self._is_calendar_ready(item):
                        item.ready_for_tool = True
                        item.target_tool = "calendar"
                        ready_items.append(item)
                
                # Prepare for task management tool
                elif tool == "task" or tool == "task_management":
                    if self._is_task_ready(item):
                        item.ready_for_tool = True
                        item.target_tool = "task_management"
                        ready_items.append(item)
                
                # General preparation
                else:
                    if item.complete_data.get("title"):
                        item.ready_for_tool = True
                        item.target_tool = tool
                        ready_items.append(item)
            
            ready_for_tools[tool] = ready_items
        
        return ready_for_tools
    
    def _is_calendar_ready(self, item: ParsedListItem) -> bool:
        """Check if an item has enough information for calendar event creation"""
        complete_data = item.complete_data
        
        # Must have title
        if not complete_data.get("title"):
            return False
        
        # Must have some date/time information
        has_dates = bool(complete_data.get("dates"))
        has_times = bool(complete_data.get("times"))
        
        # Calendar events need at least a date
        return has_dates or has_times
    
    def _is_task_ready(self, item: ParsedListItem) -> bool:
        """Check if an item has enough information for task creation"""
        complete_data = item.complete_data
        
        # Must have title
        if not complete_data.get("title"):
            return False
        
        # Tasks are more flexible - just need a title and optionally other info
        return True
    
    def _identify_missing_information(self, items: List[ParsedListItem], target_tools: List[str]) -> Tuple[List[str], bool]:
        """Identify what information is missing for complete tool preparation"""
        
        missing_info = []
        requires_input = False
        
        if not target_tools:
            return missing_info, requires_input
        
        for tool in target_tools:
            if tool == "calendar" or tool == "calendar_tool":
                # Check for missing calendar information
                items_without_dates = [item for item in items 
                                     if item.item_type not in ["section", "subsection"] 
                                     and item.complete_data.get("title") 
                                     and not item.complete_data.get("dates")]
                
                if items_without_dates:
                    missing_info.append(f"Missing dates for {len(items_without_dates)} calendar items")
                    requires_input = True
                
                items_without_times = [item for item in items 
                                     if item.complete_data.get("dates") 
                                     and not item.complete_data.get("times")]
                
                if len(items_without_times) > len(items_without_dates):  # Some have dates but no times
                    missing_info.append("Missing specific times for calendar events (will use default times)")
            
            elif tool == "task" or tool == "task_management":
                # Check for missing task information
                items_without_priorities = [item for item in items 
                                          if item.complete_data.get("title") 
                                          and not item.complete_data.get("priorities")]
                
                if len(items_without_priorities) > len(items) * 0.5:  # More than half missing priorities
                    missing_info.append("Missing priority levels for tasks (will use default: medium)")
        
        return missing_info, requires_input
    
    def _generate_parsing_summary(self, items: List[ParsedListItem], ready_for_tools: Dict[str, List[ParsedListItem]], missing_info: List[str]) -> str:
        """Generate a human-readable summary of the parsing results"""
        
        summary_parts = []
        
        # Overall parsing results
        total_items = len([item for item in items if item.item_type not in ["section", "subsection"]])
        sections = len([item for item in items if item.item_type in ["section", "subsection"]])
        
        summary_parts.append(f"📋 **Parsed {total_items} items from {sections} sections**")
        
        # Tool readiness
        for tool, tool_items in ready_for_tools.items():
            if tool_items:
                summary_parts.append(f"✅ **{len(tool_items)} items ready for {tool}**")
                
                # Show examples
                examples = tool_items[:3]  # Show first 3
                for item in examples:
                    subject = item.complete_data.get("subject", "")
                    title = item.complete_data.get("title", "")
                    dates = item.complete_data.get("dates", [])
                    
                    example = f"  • {title}"
                    if subject:
                        example += f" ({subject})"
                    if dates:
                        example += f" - {dates[0]}"
                    
                    summary_parts.append(example)
                
                if len(tool_items) > 3:
                    summary_parts.append(f"  ... and {len(tool_items) - 3} more")
        
        # Missing information
        if missing_info:
            summary_parts.append(f"\n⚠️ **Missing Information:**")
            for info in missing_info:
                summary_parts.append(f"  • {info}")
        
        # Inheritance patterns detected
        inheritance_examples = []
        for item in items:
            if item.complete_data.get("subject") and item.level > 0:
                inheritance_examples.append(f"{item.complete_data['title']} → {item.complete_data['subject']}")
        
        if inheritance_examples:
            summary_parts.append(f"\n🔗 **Inheritance Patterns Detected:**")
            for example in inheritance_examples[:2]:  # Show first 2
                summary_parts.append(f"  • {example}")
        
        return "\n".join(summary_parts)

# Global instance
intelligent_list_parser = IntelligentListParser()

# Tool handler function for integration
async def handle_list_parsing_request(state: GraphState) -> Dict[str, Any]:
    """
    Handle list parsing requests from the workflow
    """
    logger.info("🎯 Starting intelligent list parsing request handler")
    
    tool_output = state.tool_output or {}
    raw_list = tool_output.get("raw_list", "") or tool_output.get("list_text", "") or state.user_input
    
    logger.info(f"📝 Raw input length: {len(raw_list)} characters")
    logger.info(f"📝 Input preview: {raw_list[:200]}...")
    
    # Detect target tools from user intent
    user_intent = state.user_input.lower()
    if any(word in user_intent for word in ["calendar", "schedule", "due dates", "appointments", "events"]):
        target_tools = ["calendar"]
        logger.info("📅 Detected calendar intent from user input")
    elif any(word in user_intent for word in ["tasks", "todo", "assignments", "projects"]):
        target_tools = ["task_management"]
        logger.info("📋 Detected task management intent from user input")
    else:
        target_tools = tool_output.get("target_tools", ["calendar", "task_management"])
        logger.info(f"🎯 Using default/provided target tools: {target_tools}")
    
    logger.info(f"🛠️ Processing list parsing request for tools: {target_tools}")
    
    try:
        logger.info("🔍 Calling intelligent list parser...")
        # Parse the list
        result = await intelligent_list_parser.parse_hierarchical_list(state, raw_list, target_tools)
        logger.info(f"🔍 Intelligent parser returned {len(result.parsed_items)} items")
        
        # If calendar was the target, use LangGraph assessment workflow
        if "calendar" in target_tools and any(word in user_intent for word in ["calendar", "schedule", "add to calendar", "create events"]):
            
            logger.info("📊 Using LangGraph parsing assessment workflow for calendar events")
            logger.info(f"📊 Items ready for calendar: {len(result.ready_for_tools.get('calendar', []))}")
            
            # Run the intelligent assessment workflow
            from worker.services.parsing_assessment_nodes import run_parsing_assessment_workflow
            
            # Convert result to format expected by assessment
            assessment_input = {
                "parsed_items": [item.__dict__ for item in result.parsed_items],
                "ready_for_tools": {tool: [item.__dict__ for item in items] 
                                  for tool, items in result.ready_for_tools.items()},
                "requires_user_input": result.requires_user_input,
                "missing_information": result.missing_information,
                "response": result.parsing_summary
            }
            
            logger.info(f"📊 Assessment input prepared - {len(assessment_input['parsed_items'])} items")
            logger.info(f"📊 Ready for tools: {[(tool, len(items)) for tool, items in assessment_input['ready_for_tools'].items()]}")
            
            # Run assessment workflow
            logger.info("🚀 Launching parsing assessment workflow...")
            assessed_state = await run_parsing_assessment_workflow(
                state, raw_list, assessment_input, "calendar"
            )
            
            logger.info("📊 Assessment workflow completed")
            logger.info(f"📊 Assessment action: {getattr(assessed_state, 'parsing_action_taken', 'unknown')}")
            
            # Get final results from workflow
            final_results = getattr(assessed_state, 'parsing_results', assessment_input)
            action_taken = getattr(assessed_state, 'parsing_action_taken', 'unknown')
            final_response = getattr(assessed_state, 'final_parsing_response', result.parsing_summary)
            
            # If we have calendar events ready, create them
            if final_results.get("events") or final_results.get("ready_for_tools", {}).get("calendar"):
                
                # Determine which events to create
                events_to_create = []
                if final_results.get("events"):
                    # LLM-parsed events (from reparse action)
                    events_to_create = final_results["events"]
                    creation_function = _create_calendar_events_from_llm_data
                elif final_results.get("ready_for_tools", {}).get("calendar"):
                    # Enhanced structured events (from supplement action)
                    calendar_items = [item for item in result.parsed_items 
                                    if item.ready_for_tool and item.target_tool == "calendar"]
                    events_to_create = calendar_items
                    creation_function = _create_calendar_events_from_parsed_items
                
                if events_to_create:
                    success_count, created_events, errors = await creation_function(state, events_to_create)
                    
                    if success_count > 0:
                        response = f"🎉 **Successfully created {success_count} calendar events!**\n\n"
                        response += final_response
                        
                        if errors:
                            response += f"\n\n⚠️ **Issues encountered:**\n"
                            response += "\n".join([f"• {error}" for error in errors])
                        
                        return {
                            "response": response,
                            "calendar_events_created": success_count,
                            "events_details": created_events,
                            "success": True,
                            "parsing_method": f"langgraph_assessment_{action_taken}",
                            "assessment_workflow": getattr(assessed_state, 'dynamic_results', [])
                        }
            
            # If no events could be created, return assessment results
            return {
                "response": final_response,
                "success": len(final_results.get("events", [])) > 0,
                "parsing_method": f"langgraph_assessment_{action_taken}",
                "assessment_workflow": getattr(assessed_state, 'dynamic_results', [])
            }
        
        # Return comprehensive parsing result
        return {
            "response": result.parsing_summary,
            "parsed_items": [item.__dict__ for item in result.parsed_items],
            "ready_for_tools": {tool: [item.__dict__ for item in items] 
                              for tool, items in result.ready_for_tools.items()},
            "requires_user_input": result.requires_user_input,
            "missing_information": result.missing_information,
            "inheritance_patterns": result.inheritance_patterns,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Error in list parsing handler: {e}", exc_info=True)
        return {
            "response": f"Failed to parse list: {str(e)}",
            "success": False,
            "error": str(e)
        }


async def _create_calendar_events_from_parsed_items(state: GraphState, calendar_items: List[ParsedListItem]) -> Tuple[int, List[Dict], List[str]]:
    """
    Create calendar events from parsed list items
    """
    from worker.calendar_tools import create_calendar_event_tool
    
    success_count = 0
    created_events = []
    errors = []
    
    for item in calendar_items:
        try:
            # Convert parsed item to calendar event format
            complete_data = item.complete_data
            
            # Create event details
            event_title = complete_data.get("title", "")
            if not event_title:
                errors.append(f"Skipped item without title: {item.raw_text}")
                continue
            
            # Get dates - use first available date
            dates = complete_data.get("dates", [])
            if not dates:
                errors.append(f"Skipped '{event_title}' - no date found")
                continue
            
            event_date = dates[0]  # Use first date
            
            # Get times - use default if not specified
            times = complete_data.get("times", [])
            start_time = times[0] if times else "09:00"
            
            # Build event details
            description = f"Subject: {complete_data.get('subject', 'General')}"
            if complete_data.get("description"):
                description += f"\nDetails: {complete_data['description']}"
            
            # Create event through tool
            event_state = GraphState(
                user_input=f"Create event: {event_title}",
                user_id=state.user_id,
                session_id=state.session_id,
                tool_output={
                    "title": event_title,
                    "start_date": event_date,
                    "start_time": start_time,
                    "description": description,
                    "location": complete_data.get("locations", [""])[0] if complete_data.get("locations") else ""
                }
            )
            
            result = await create_calendar_event_tool(event_state)
            
            if result.get("success", False):
                success_count += 1
                created_events.append({
                    "title": event_title,
                    "date": event_date,
                    "time": start_time,
                    "subject": complete_data.get("subject", "")
                })
            else:
                errors.append(f"Failed to create '{event_title}': {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            errors.append(f"Error creating event for '{item.title}': {str(e)}")
    
    return success_count, created_events, errors


async def _create_calendar_events_from_llm_data(state: GraphState, llm_events: List[Dict]) -> Tuple[int, List[Dict], List[str]]:
    """
    Create calendar events from LLM-parsed event data
    """
    from worker.calendar_tools import create_calendar_event_tool
    
    success_count = 0
    created_events = []
    errors = []
    
    for event_data in llm_events:
        try:
            title = event_data.get("title", "")
            date = event_data.get("date", "")
            
            if not title or not date:
                errors.append(f"Skipping event with missing title or date: {event_data}")
                continue
            
            # Prepare datetime strings for calendar creation
            date_str = date  # e.g., "Thu, 24 July 2025"
            time_str = event_data.get("time", "09:00")  # e.g., "09:00"
            
            # Parse the date and create ISO datetime strings
            from datetime import datetime
            try:
                # Clean up date string (remove "Est." prefix if present)
                clean_date = date_str.replace("Est. ", "").strip()
                
                # Try to parse the date string
                if "," in clean_date:
                    # Format like "Thu, 24 July 2025"
                    date_part = clean_date.split(",")[1].strip()  # "24 July 2025"
                    date_obj = datetime.strptime(date_part, "%d %B %Y")
                else:
                    # Format like "Monday, 4 August 2025"
                    date_obj = datetime.strptime(clean_date, "%A, %d %B %Y")
                
                # Create start datetime
                time_parts = time_str.split(":")
                hour = int(time_parts[0])
                minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                
                start_datetime = date_obj.replace(hour=hour, minute=minute)
                end_datetime = start_datetime + timedelta(hours=1)  # Default 1 hour duration
                
                start_time_iso = start_datetime.isoformat()
                end_time_iso = end_datetime.isoformat()
                
            except Exception as parse_error:
                logger.error(f"Error parsing date '{date_str}': {parse_error}")
                errors.append(f"Failed to parse date for '{title}': {date_str}")
                continue
            
            # Create event through calendar tool
            event_state = GraphState(
                user_input=f"Create event: {title}",
                user_id=state.user_id,
                session_id=state.session_id,
                tool_output={
                    "summary": title,  # Fixed: use 'summary' instead of 'title'
                    "start_time": start_time_iso,  # Fixed: use ISO format datetime
                    "end_time": end_time_iso,  # Fixed: use ISO format datetime
                    "description": f"Subject: {event_data.get('subject', 'General')}\n{event_data.get('description', '')}".strip(),
                    "location": event_data.get("location", ""),
                    "calendar_id": "primary"
                }
            )
            
            result = await create_calendar_event_tool(event_state)
            
            if result.get("success", False):
                success_count += 1
                created_events.append({
                    "title": title,
                    "date": date,
                    "time": event_data.get("time", "09:00"),
                    "subject": event_data.get("subject", "")
                })
            else:
                error_type = result.get("error", "Unknown error")
                if error_type == "calendar_auth_expired":
                    errors.append(f"⚠️ Calendar connection expired - please reconnect Google Calendar in Settings")
                    # Stop processing more events since they'll all fail with the same error
                    errors.append(f"⏸️ Stopped processing remaining {len(llm_events) - llm_events.index(event_data) - 1} events due to authentication issue")
                    break
                else:
                    errors.append(f"Failed to create '{title}': {error_type}")
                
        except Exception as e:
            errors.append(f"Error creating event for '{event_data.get('title', 'Unknown')}': {str(e)}")
    
    return success_count, created_events, errors