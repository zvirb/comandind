#!/usr/bin/env python3
"""
LLM-Powered Calendar Event Parser

This service uses LLM intelligence to parse complex calendar requests
that contain structured lists, assignments, due dates, etc.
It serves as a robust fallback when rule-based parsing fails.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from worker.services.ollama_service import invoke_llm_with_tokens
from worker.graph_types import GraphState

logger = logging.getLogger(__name__)

@dataclass
class CalendarEventData:
    """Represents a parsed calendar event"""
    title: str
    date: str
    time: str = "09:00"  # Default time
    subject: str = ""
    description: str = ""
    location: str = ""
    priority: str = "normal"
    is_all_day: bool = False

class LLMCalendarParser:
    """Uses LLM intelligence to parse calendar events from text"""
    
    def __init__(self):
        self.default_time = "09:00"
        self.default_duration = "1 hour"
    
    async def parse_calendar_events(self, state: GraphState, raw_text: str) -> Tuple[List[CalendarEventData], str]:
        """
        Parse calendar events from raw text using LLM intelligence
        Returns (events_list, summary_message)
        """
        logger.info("🎯 Starting LLM-powered calendar event parsing")
        logger.info(f"📝 Input text length: {len(raw_text)} characters")
        logger.info(f"📝 First 200 chars: {raw_text[:200]}...")
        
        try:
            # Use LLM to extract structured calendar events
            logger.info("🤖 Calling LLM for event extraction...")
            events_data = await self._llm_extract_events(state, raw_text)
            logger.info(f"🤖 LLM returned {len(events_data)} raw event entries")
            
            # Convert to CalendarEventData objects
            events = []
            invalid_events = []
            
            for i, event_dict in enumerate(events_data):
                logger.debug(f"📋 Processing event {i+1}: {event_dict}")
                
                event = CalendarEventData(
                    title=event_dict.get("title", ""),
                    date=event_dict.get("date", ""),
                    time=event_dict.get("time", self.default_time),
                    subject=event_dict.get("subject", ""),
                    description=event_dict.get("description", ""),
                    location=event_dict.get("location", ""),
                    priority=event_dict.get("priority", "normal"),
                    is_all_day=event_dict.get("is_all_day", False)
                )
                
                # Only add events with valid title and date
                if event.title and event.date:
                    events.append(event)
                    logger.debug(f"✅ Valid event: '{event.title}' on {event.date}")
                else:
                    invalid_events.append(event_dict)
                    logger.warning(f"❌ Skipping invalid event - title: '{event.title}', date: '{event.date}': {event_dict}")
            
            # Log validation results
            logger.info(f"✅ Successfully validated {len(events)} calendar events")
            if invalid_events:
                logger.warning(f"❌ Rejected {len(invalid_events)} invalid events")
                for inv_event in invalid_events:
                    logger.warning(f"   - Invalid: {inv_event}")
            
            # Generate summary
            summary = self._generate_summary(events, raw_text)
            
            logger.info(f"🎉 LLM parser completed: {len(events)} valid events extracted")
            return events, summary
            
        except Exception as e:
            logger.error(f"💥 Error in LLM calendar parsing: {e}", exc_info=True)
            logger.error(f"💥 Failed on input: {raw_text[:500]}...")
            return [], f"Failed to parse calendar events: {str(e)}"
    
    async def _llm_extract_events(self, state: GraphState, raw_text: str) -> List[Dict[str, Any]]:
        """Use LLM to extract calendar events from text"""
        
        logger.info("🧠 Preparing LLM extraction prompt...")
        
        # Create a focused prompt for assignment/due date extraction
        parsing_prompt = f"""Extract calendar events from this assignment list. Find all items with due dates.

Text: {raw_text[:2000]}{"..." if len(raw_text) > 2000 else ""}

Look for:
- Subject sections (like "Web Development Assignments:")
- Assignment codes (like "2.1P", "3.2D")
- Assignment titles
- Due dates (like "Due Monday, 4 August 2025")

Return JSON: {{"calendar_events": [{{"title": "2.1P Assignment Title", "date": "Monday, 4 August 2025", "subject": "Web Development", "time": "09:00"}}]}}

Extract ALL assignments with due dates. Use section headers as subjects."""

        try:
            model_name = getattr(state, 'tool_selection_model', 'llama3.2:3b')
            logger.info(f"🤖 Using model: {model_name}")
            logger.info(f"📏 Prompt length: {len(parsing_prompt)} characters")
            
            logger.info("🚀 Invoking LLM for calendar event extraction...")
            response, token_info = await invoke_llm_with_tokens(
                messages=[
                    {"role": "system", "content": "You are a meticulous calendar event extraction expert. Always respond with valid JSON only."},
                    {"role": "user", "content": parsing_prompt}
                ],
                model_name=model_name,
                category="llm_calendar_parsing"
            )
            
            logger.info(f"🤖 LLM response received - length: {len(response)} characters")
            logger.debug(f"🤖 Full LLM response: {response}")
            
            # Parse JSON response
            logger.info("📊 Attempting to parse JSON from LLM response...")
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                logger.info(f"📊 Extracted JSON substring (first 200 chars): {json_str[:200]}...")
                
                try:
                    parsed_data = json.loads(json_str)
                    events_data = parsed_data.get("calendar_events", [])
                    logger.info(f"✅ Successfully parsed JSON - found {len(events_data)} calendar events")
                    
                    # Log each event found
                    for i, event in enumerate(events_data):
                        logger.debug(f"📅 Event {i+1}: {event.get('title', 'NO_TITLE')} - {event.get('date', 'NO_DATE')}")
                    
                    return events_data
                    
                except json.JSONDecodeError as json_error:
                    logger.error(f"❌ JSON parsing failed: {json_error}")
                    logger.error(f"❌ Problematic JSON: {json_str}")
                    raise ValueError(f"Could not parse LLM response as JSON: {json_error}")
            else:
                logger.error("❌ No JSON found in LLM response")
                logger.error(f"❌ Response preview: {response[:500]}...")
                raise ValueError("Could not extract JSON from LLM response")
                
        except Exception as e:
            logger.error(f"💥 Error in LLM event extraction: {e}", exc_info=True)
            logger.warning("🔄 Falling back to manual extraction...")
            # Fallback: try to extract manually
            fallback_events = self._fallback_extraction(raw_text)
            logger.info(f"🔄 Fallback extraction returned {len(fallback_events)} events")
            return fallback_events
    
    def _fallback_extraction(self, raw_text: str) -> List[Dict[str, Any]]:
        """Enhanced fallback extraction when LLM fails"""
        logger.info("🔄 Starting enhanced fallback extraction...")
        
        events = []
        lines = raw_text.split('\n')
        current_subject = "General"
        current_assignment = None
        pending_assignments = []
        last_due_date = None
        logger.info(f"📝 Processing {len(lines)} lines for fallback extraction")
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
                
            # Check for subject headers (ending with colon, not containing due dates)
            if line.endswith(':') and not any(word in line.lower() for word in ['due', 'deadline']):
                old_subject = current_subject
                current_subject = line.replace(':', '').strip()
                # Clean up subject names
                if 'assignments' in current_subject.lower():
                    current_subject = current_subject.replace(' Assignments', '').replace(' assignments', '')
                logger.debug(f"📚 Line {line_num}: Subject changed from '{old_subject}' to '{current_subject}'")
                pending_assignments = []
                current_assignment = None
                last_due_date = None
                continue
            
            # Check for grouped due dates (e.g., "Due Monday, 4 August 2025")
            if line.lower().startswith('due ') and len(line.split()) <= 8:
                due_date = line.replace('Due ', '').strip()
                last_due_date = due_date
                logger.debug(f"📅 Line {line_num}: Found group due date: {due_date}")
                # Apply this date to pending assignments
                for assignment in pending_assignments:
                    event = {
                        "title": assignment,
                        "date": due_date,
                        "time": "09:00",
                        "subject": current_subject,
                        "description": "",
                        "priority": "normal",
                        "is_all_day": False
                    }
                    events.append(event)
                    logger.debug(f"📅 Applied date to assignment: '{assignment}' - {due_date}")
                pending_assignments = []
                continue
            
            # Check for individual due dates on their own line (e.g., "Due: Thu, 24 July 2025")
            if line.lower().startswith('due:') and current_assignment:
                date_part = line.replace('Due:', '').strip()
                
                event = {
                    "title": current_assignment,
                    "date": date_part.split('(')[0].strip(),
                    "time": "09:00",
                    "subject": current_subject,
                    "description": "",
                    "priority": "normal",
                    "is_all_day": False
                }
                
                events.append(event)
                logger.debug(f"📅 Line {line_num}: Extracted event - '{current_assignment}' - {event['date']} ({current_subject})")
                current_assignment = None
                continue
            
            # Enhanced assignment detection for multiple formats
            import re
            
            # Format 1: "2.1P Add images, hyperlinks and tables into your web page"
            assignment_match = re.match(r'^(\d+\.\d+[A-Z])\s+(.+)', line)
            if assignment_match:
                assignment_code = assignment_match.group(1)
                title = assignment_match.group(2).strip()
                full_title = f"{assignment_code} {title}"
                current_assignment = full_title
                pending_assignments.append(full_title)
                logger.debug(f"📋 Line {line_num}: Found assignment: '{full_title}'")
                
                # If we have a recent due date, apply it immediately
                if last_due_date:
                    event = {
                        "title": full_title,
                        "date": last_due_date,
                        "time": "09:00",
                        "subject": current_subject,
                        "description": "",
                        "priority": "normal",
                        "is_all_day": False
                    }
                    events.append(event)
                    logger.debug(f"📅 Applied recent due date to assignment: '{full_title}' - {last_due_date}")
                continue
            
            # Format 2: Lines that look like tasks/assignments without codes
            if (line and not line.startswith('Due') and 
                not line.endswith(':') and 
                len(line.split()) > 2 and
                not re.match(r'^\d+\.', line)):  # Not a numbered list
                
                # This might be a task/assignment description
                current_assignment = line
                pending_assignments.append(line)
                logger.debug(f"📋 Line {line_num}: Found potential assignment: '{line}'")
                
                # If we have a recent due date, apply it immediately
                if last_due_date:
                    event = {
                        "title": line,
                        "date": last_due_date,
                        "time": "09:00",
                        "subject": current_subject,
                        "description": "",
                        "priority": "normal",
                        "is_all_day": False
                    }
                    events.append(event)
                    logger.debug(f"📅 Applied recent due date to assignment: '{line}' - {last_due_date}")
                continue
        
        # Handle any remaining pending assignments with the last known due date
        if pending_assignments and last_due_date:
            logger.debug(f"📅 Applying final due date to {len(pending_assignments)} pending assignments")
            for assignment in pending_assignments:
                event = {
                    "title": assignment,
                    "date": last_due_date,
                    "time": "09:00",
                    "subject": current_subject,
                    "description": "",
                    "priority": "normal",
                    "is_all_day": False
                }
                events.append(event)
                logger.debug(f"📅 Final assignment: '{assignment}' - {last_due_date}")
        
        logger.info(f"🔄 Enhanced fallback extraction completed: {len(events)} events found")
        return events
    
    def _generate_summary(self, events: List[CalendarEventData], original_text: str) -> str:
        """Generate a summary of parsed events"""
        if not events:
            return "❌ **No calendar events could be parsed from the provided text.**"
        
        # Group by subject
        by_subject = {}
        for event in events:
            subject = event.subject or "General"
            if subject not in by_subject:
                by_subject[subject] = []
            by_subject[subject].append(event)
        
        summary_parts = [f"📅 **Successfully parsed {len(events)} calendar events:**"]
        
        for subject, subject_events in by_subject.items():
            summary_parts.append(f"\n**{subject}** ({len(subject_events)} events)")
            
            # Show first few events as examples
            for event in subject_events[:3]:
                summary_parts.append(f"  • {event.title} - {event.date}")
            
            if len(subject_events) > 3:
                summary_parts.append(f"  ... and {len(subject_events) - 3} more")
        
        summary_parts.append(f"\n✅ All events ready for calendar creation!")
        
        return "\n".join(summary_parts)

# Global instance
llm_calendar_parser = LLMCalendarParser()

# Integration function for calendar tools
async def parse_calendar_events_with_llm(state: GraphState, raw_text: str = None) -> Dict[str, Any]:
    """
    Parse calendar events using LLM intelligence
    """
    logger.info("🎯 Starting parse_calendar_events_with_llm integration function")
    
    text_to_parse = raw_text or state.user_input
    logger.info(f"📝 Text to parse length: {len(text_to_parse)} characters")
    logger.info(f"📝 Using raw_text: {raw_text is not None}, user_input: {state.user_input is not None}")
    
    try:
        logger.info("🚀 Calling LLM calendar parser instance...")
        events, summary = await llm_calendar_parser.parse_calendar_events(state, text_to_parse)
        
        logger.info(f"📊 Parser returned {len(events)} events")
        
        if not events:
            logger.warning("❌ No events extracted by LLM parser")
            return {
                "success": False,
                "response": "Could not extract any calendar events from the provided text.",
                "events": [],
                "parsing_method": "llm_intelligent_failed"
            }
        
        logger.info(f"✅ Successfully extracted {len(events)} calendar events via LLM")
        
        # Log first few events for debugging
        for i, event in enumerate(events[:3]):
            logger.debug(f"📅 Event {i+1}: {event.title} - {event.date} ({event.subject})")
        
        return {
            "success": True,
            "response": summary,
            "events": [event.__dict__ for event in events],
            "event_count": len(events),
            "parsing_method": "llm_intelligent"
        }
        
    except Exception as e:
        logger.error(f"💥 Error in LLM calendar parsing integration: {e}", exc_info=True)
        logger.error(f"💥 Failed input preview: {text_to_parse[:200]}...")
        return {
            "success": False,
            "response": f"Failed to parse calendar events: {str(e)}",
            "events": [],
            "error": str(e),
            "parsing_method": "llm_intelligent_error"
        }


# Direct tool handler for LLM calendar parsing
async def handle_llm_calendar_parsing(state: GraphState) -> Dict[str, Any]:
    """
    Direct tool handler for LLM-powered calendar parsing
    Can be used as a standalone tool or as fallback
    """
    try:
        # Parse events using LLM
        parsing_result = await parse_calendar_events_with_llm(state)
        
        if not parsing_result.get("success"):
            return parsing_result
        
        events = parsing_result.get("events", [])
        if not events:
            return {
                "response": "No calendar events could be extracted from your request.",
                "success": False
            }
        
        # If user wants to create calendar events, do it
        user_intent = state.user_input.lower()
        if any(word in user_intent for word in ["calendar", "schedule", "create", "add"]):
            
            # Import calendar creation function
            from worker.services.intelligent_list_parser import _create_calendar_events_from_llm_data
            
            success_count, created_events, errors = await _create_calendar_events_from_llm_data(state, events)
            
            if success_count > 0:
                response = f"🎉 **Successfully created {success_count} calendar events using LLM parsing!**\n\n"
                response += parsing_result.get("response", "")
                
                if errors:
                    response += f"\n\n⚠️ **Issues encountered:**\n"
                    response += "\n".join([f"• {error}" for error in errors])
                
                return {
                    "response": response,
                    "success": True,
                    "calendar_events_created": success_count,
                    "events_details": created_events,
                    "parsing_method": "direct_llm"
                }
            else:
                return {
                    "response": f"Extracted {len(events)} events but failed to create calendar entries. Errors: {'; '.join(errors)}",
                    "success": False,
                    "events_extracted": len(events)
                }
        else:
            # Just return the parsed events without creating
            return {
                "response": parsing_result.get("response", ""),
                "success": True,
                "events_extracted": len(events),
                "events": events,
                "parsing_method": "direct_llm_preview"
            }
            
    except Exception as e:
        logger.error(f"Error in LLM calendar parsing handler: {e}", exc_info=True)
        return {
            "response": f"Failed to parse calendar events: {str(e)}",
            "success": False,
            "error": str(e)
        }