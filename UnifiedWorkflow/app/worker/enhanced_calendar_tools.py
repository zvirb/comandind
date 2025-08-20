#!/usr/bin/env python3
"""
Enhanced Calendar Tools with Smart Multi-Event Processing

This module provides enhanced calendar functionality that can:
1. Parse complex multi-event requests
2. Create multiple events iteratively 
3. Handle bulk operations intelligently
4. Provide detailed progress feedback
5. Recover from partial failures
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from worker.services.ollama_service import invoke_llm_with_tokens
from worker.services.progress_manager import progress_manager
from worker.graph_types import GraphState
from worker.calendar_tools import (
    create_calendar_event_tool,
    check_calendar_events,
    edit_calendar_event_tool,
    delete_calendar_event_tool,
    move_calendar_event_tool
)

logger = logging.getLogger(__name__)

@dataclass
class ParsedCalendarEvent:
    """Represents a parsed calendar event from natural language"""
    title: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    description: str = ""
    location: str = ""
    due_date: Optional[str] = None
    has_specific_time: bool = False
    is_all_day: bool = False
    priority: str = "normal"
    category: str = ""
    reminders: List[str] = None
    confidence_score: float = 0.0

    def __post_init__(self):
        if self.reminders is None:
            self.reminders = []

@dataclass
class MultiEventProcessingResult:
    """Result of processing multiple calendar events"""
    total_events: int
    successful_events: int
    failed_events: int
    created_event_ids: List[str]
    failed_event_details: List[Dict[str, Any]]
    processing_summary: str
    individual_results: List[Dict[str, Any]]

class EnhancedCalendarProcessor:
    """Enhanced calendar processing with multi-event support"""
    
    def __init__(self):
        self.default_event_duration = 60  # minutes
        self.default_start_time = "09:00"  # 9 AM
        
    async def parse_multi_event_request(self, state: GraphState, request: str) -> Tuple[List[ParsedCalendarEvent], Dict[str, Any]]:
        """
        Parse a complex calendar request that may contain multiple events
        """
        parsing_prompt = f"""You are an expert calendar assistant. Parse this request to identify ALL calendar events that need to be created.

User Request: {request}

Analyze the request and respond with JSON in this exact format:
{{
  "parsing_result": {{
    "events_found": [
      {{
        "title": "Event title (extract the key activity)",
        "start_time": "2025-07-24T14:00:00" (ISO format if time specified, null if not),
        "end_time": "2025-07-24T15:00:00" (ISO format if time specified, null if not),
        "due_date": "2025-07-24" (for assignments/deadlines),
        "description": "Additional details if provided",
        "location": "Location if mentioned",
        "has_specific_time": true/false,
        "is_all_day": true/false,
        "priority": "low/normal/high",
        "category": "work/personal/academic/health/etc",
        "reminders": ["1 day before", "1 hour before"],
        "confidence_score": 0.0-1.0
      }}
    ],
    "missing_info": {{
      "needs_times": true/false,
      "needs_dates": true/false,
      "needs_locations": true/false,
      "needs_durations": true/false,
      "specific_questions": [
        "What time should the Math assignment be due?",
        "How long should the meeting last?"
      ]
    }},
    "can_proceed_immediately": true/false,
    "suggested_defaults": {{
      "default_duration": 60,
      "default_start_time": "09:00",
      "default_reminder": "1 hour before"
    }},
    "processing_strategy": "immediate/ask_clarification/batch_create"
  }}
}}

Guidelines:
- Look for multiple assignments, meetings, deadlines, appointments
- Extract specific dates and times when mentioned
- Identify recurring patterns (daily, weekly, etc.)
- For assignments: treat due dates as end times, suggest start times for work sessions
- For meetings: extract duration if mentioned
- Categorize events (work, personal, academic, health, etc.)
- Set confidence score based on how clear the information is
- If information is missing but events are clear, suggest reasonable defaults
- Use "immediate" strategy only if all events have complete information
- Use "ask_clarification" if critical information is missing
- Use "batch_create" if events are clear but some details can use defaults

Current date/time context: {datetime.now().strftime('%Y-%m-%d %H:%M')}"""

        try:
            model_name = getattr(state, 'tool_selection_model', 'llama3.2:3b')
            
            response, _ = await invoke_llm_with_tokens(
                messages=[
                    {"role": "system", "content": "You are a calendar parsing expert. Always respond with valid JSON only."},
                    {"role": "user", "content": parsing_prompt}
                ],
                model_name=model_name,
                category="calendar_parsing"
            )
            
            # Parse JSON response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                parsed_data = json.loads(json_str)
                parsing_result = parsed_data.get("parsing_result", {})
                
                # Convert to ParsedCalendarEvent objects
                events = []
                for event_data in parsing_result.get("events_found", []):
                    event = ParsedCalendarEvent(
                        title=event_data.get("title", "Event"),
                        start_time=event_data.get("start_time"),
                        end_time=event_data.get("end_time"),
                        description=event_data.get("description", ""),
                        location=event_data.get("location", ""),
                        due_date=event_data.get("due_date"),
                        has_specific_time=event_data.get("has_specific_time", False),
                        is_all_day=event_data.get("is_all_day", False),
                        priority=event_data.get("priority", "normal"),
                        category=event_data.get("category", ""),
                        reminders=event_data.get("reminders", []),
                        confidence_score=event_data.get("confidence_score", 0.8)
                    )
                    events.append(event)
                
                return events, parsing_result
            else:
                raise ValueError("Could not parse JSON response from LLM")
                
        except Exception as e:
            logger.error(f"Error parsing multi-event request: {e}", exc_info=True)
            # Fallback: create a single generic event
            fallback_event = ParsedCalendarEvent(
                title="Event from request",
                description=request,
                confidence_score=0.3
            )
            fallback_result = {
                "can_proceed_immediately": False,
                "processing_strategy": "ask_clarification",
                "missing_info": {
                    "needs_times": True,
                    "needs_dates": True,
                    "specific_questions": ["Could you provide more specific details about the events you'd like to create?"]
                }
            }
            return [fallback_event], fallback_result
    
    async def process_events_with_defaults(self, events: List[ParsedCalendarEvent], parsing_result: Dict[str, Any]) -> List[ParsedCalendarEvent]:
        """
        Fill in missing information with intelligent defaults
        """
        suggested_defaults = parsing_result.get("suggested_defaults", {})
        default_duration = suggested_defaults.get("default_duration", self.default_event_duration)
        default_start_time = suggested_defaults.get("default_start_time", self.default_start_time)
        
        processed_events = []
        
        for event in events:
            processed_event = event
            
            # Handle due dates (convert to calendar events)
            if event.due_date and not event.start_time:
                # For assignments, create an end time at due date and suggest start time
                due_datetime = datetime.fromisoformat(event.due_date)
                if not event.has_specific_time:
                    # Default due time to end of day
                    due_datetime = due_datetime.replace(hour=23, minute=59)
                
                processed_event.end_time = due_datetime.isoformat()
                
                # Suggest start time (1-2 hours before due time for work session)
                work_duration = 2 * 60  # 2 hours for assignments
                start_datetime = due_datetime - timedelta(minutes=work_duration)
                processed_event.start_time = start_datetime.isoformat()
                processed_event.title = f"Work on {event.title}"
                processed_event.description = f"Work session for: {event.title}\nDue: {due_datetime.strftime('%Y-%m-%d %H:%M')}"
            
            # Handle events with no times
            elif not event.start_time and not event.due_date:
                # Use default start time tomorrow
                tomorrow = datetime.now() + timedelta(days=1)
                start_hour, start_minute = map(int, default_start_time.split(':'))
                start_datetime = tomorrow.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
                
                processed_event.start_time = start_datetime.isoformat()
                end_datetime = start_datetime + timedelta(minutes=default_duration)
                processed_event.end_time = end_datetime.isoformat()
            
            # Handle events with start time but no end time
            elif event.start_time and not event.end_time:
                start_datetime = datetime.fromisoformat(event.start_time)
                end_datetime = start_datetime + timedelta(minutes=default_duration)
                processed_event.end_time = end_datetime.isoformat()
            
            # Add default reminders if none specified
            if not processed_event.reminders:
                if processed_event.category == "academic" or "assignment" in processed_event.title.lower():
                    processed_event.reminders = ["1 day before", "3 hours before"]
                elif processed_event.category == "health" or "doctor" in processed_event.title.lower():
                    processed_event.reminders = ["1 day before", "2 hours before"]
                else:
                    processed_event.reminders = ["1 hour before"]
            
            processed_events.append(processed_event)
        
        return processed_events
    
    async def create_events_iteratively(self, state: GraphState, events: List[ParsedCalendarEvent]) -> MultiEventProcessingResult:
        """
        Create multiple calendar events with progress tracking and error handling
        """
        logger.info(f"Creating {len(events)} calendar events iteratively")
        
        results = MultiEventProcessingResult(
            total_events=len(events),
            successful_events=0,
            failed_events=0,
            created_event_ids=[],
            failed_event_details=[],
            processing_summary="",
            individual_results=[]
        )
        
        # Notify user of batch operation start
        if state.session_id:
            await progress_manager.broadcast_to_session_sync(state.session_id, {
                "type": "batch_calendar_operation_started",
                "total_events": len(events),
                "event_titles": [event.title for event in events]
            })
        
        for i, event in enumerate(events):
            try:
                logger.info(f"Creating event {i+1}/{len(events)}: {event.title}")
                
                # Update progress
                if state.session_id:
                    await progress_manager.broadcast_to_session_sync(state.session_id, {
                        "type": "batch_calendar_progress",
                        "current_event": i + 1,
                        "total_events": len(events),
                        "event_title": event.title,
                        "progress_percentage": ((i) / len(events)) * 100
                    })
                
                # Prepare state for individual event creation
                event_state = GraphState(
                    user_input=f"Create calendar event: {event.title}",
                    user_id=state.user_id,
                    session_id=state.session_id,
                    tool_output={
                        "summary": event.title,
                        "start_time": event.start_time,
                        "end_time": event.end_time,
                        "description": event.description,
                        "location": event.location
                    }
                )
                
                # Create the event
                result = await create_calendar_event_tool(event_state)
                
                if result and not result.get("error"):
                    results.successful_events += 1
                    results.individual_results.append({
                        "event_title": event.title,
                        "status": "success",
                        "result": result
                    })
                    
                    # Extract event ID if available (implementation specific)
                    event_link = result.get("response", "")
                    if "event" in event_link.lower():
                        results.created_event_ids.append(f"event_{i+1}")
                    
                    logger.info(f"Successfully created event: {event.title}")
                else:
                    results.failed_events += 1
                    error_details = {
                        "event_title": event.title,
                        "error": result.get("error", "Unknown error"),
                        "event_data": {
                            "start_time": event.start_time,
                            "end_time": event.end_time,
                            "description": event.description
                        }
                    }
                    results.failed_event_details.append(error_details)
                    results.individual_results.append({
                        "event_title": event.title,
                        "status": "failed",
                        "error": error_details["error"]
                    })
                    
                    logger.error(f"Failed to create event {event.title}: {error_details['error']}")
                
                # Small delay between events to avoid rate limiting
                if i < len(events) - 1:
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"Exception creating event {event.title}: {e}", exc_info=True)
                results.failed_events += 1
                results.failed_event_details.append({
                    "event_title": event.title,
                    "error": str(e),
                    "exception": True
                })
        
        # Generate summary
        results.processing_summary = self._generate_processing_summary(results)
        
        # Notify completion
        if state.session_id:
            await progress_manager.broadcast_to_session_sync(state.session_id, {
                "type": "batch_calendar_operation_completed",
                "total_events": results.total_events,
                "successful_events": results.successful_events,
                "failed_events": results.failed_events,
                "summary": results.processing_summary
            })
        
        return results
    
    def _generate_processing_summary(self, results: MultiEventProcessingResult) -> str:
        """Generate a human-readable summary of the batch processing results"""
        
        summary_parts = []
        
        if results.successful_events == results.total_events:
            summary_parts.append(f"✅ Successfully created all {results.total_events} calendar events!")
        elif results.successful_events > 0:
            summary_parts.append(f"✅ Created {results.successful_events} of {results.total_events} calendar events.")
            summary_parts.append(f"❌ {results.failed_events} events failed to create.")
        else:
            summary_parts.append(f"❌ Failed to create any of the {results.total_events} calendar events.")
        
        # Add details about successful events
        if results.successful_events > 0:
            successful_titles = [r["event_title"] for r in results.individual_results if r["status"] == "success"]
            if len(successful_titles) <= 5:
                summary_parts.append(f"\n**Successfully created:**\n" + "\n".join([f"• {title}" for title in successful_titles]))
            else:
                summary_parts.append(f"\n**Successfully created {len(successful_titles)} events** (showing first 5):\n" + 
                                   "\n".join([f"• {title}" for title in successful_titles[:5]]))
        
        # Add details about failed events
        if results.failed_events > 0:
            summary_parts.append(f"\n**Failed events:**")
            for failure in results.failed_event_details[:3]:  # Show first 3 failures
                summary_parts.append(f"• {failure['event_title']}: {failure['error']}")
            
            if len(results.failed_event_details) > 3:
                summary_parts.append(f"... and {len(results.failed_event_details) - 3} more")
        
        return "\n".join(summary_parts)

# Global processor instance
enhanced_calendar_processor = EnhancedCalendarProcessor()

async def handle_smart_calendar_request(state: GraphState) -> Dict[str, Any]:
    """
    Enhanced calendar handler that can process complex multi-event requests
    """
    request = state.user_input
    logger.info(f"Processing smart calendar request: {request[:100]}...")
    
    try:
        # Parse the request to identify multiple events
        events, parsing_result = await enhanced_calendar_processor.parse_multi_event_request(state, request)
        
        logger.info(f"Parsed {len(events)} events from request")
        
        # Check processing strategy
        processing_strategy = parsing_result.get("processing_strategy", "ask_clarification")
        
        if processing_strategy == "ask_clarification":
            # Generate clarification questions
            missing_info = parsing_result.get("missing_info", {})
            questions = missing_info.get("specific_questions", [])
            
            if questions:
                question_text = f"I found {len(events)} potential calendar events in your request:\n\n"
                for i, event in enumerate(events, 1):
                    question_text += f"{i}. {event.title}\n"
                
                question_text += f"\nTo create these events properly, I need some additional information:\n\n"
                for i, question in enumerate(questions, 1):
                    question_text += f"{i}. {question}\n"
                
                question_text += "\nPlease provide these details so I can create your calendar events."
                
                return {
                    "response": question_text,
                    "requires_user_input": True,
                    "events_identified": len(events),
                    "parsing_result": parsing_result
                }
        
        elif processing_strategy == "batch_create" or processing_strategy == "immediate":
            # Process events with defaults and create them
            processed_events = await enhanced_calendar_processor.process_events_with_defaults(events, parsing_result)
            
            if len(processed_events) == 1:
                # Single event - use standard creation
                event = processed_events[0]
                event_state = GraphState(
                    user_input=request,
                    user_id=state.user_id,
                    session_id=state.session_id,
                    tool_output={
                        "summary": event.title,
                        "start_time": event.start_time,
                        "end_time": event.end_time,
                        "description": event.description,
                        "location": event.location
                    }
                )
                return await create_calendar_event_tool(event_state)
            
            else:
                # Multiple events - use batch processing
                batch_result = await enhanced_calendar_processor.create_events_iteratively(state, processed_events)
                
                return {
                    "response": batch_result.processing_summary,
                    "batch_processing": True,
                    "total_events": batch_result.total_events,
                    "successful_events": batch_result.successful_events,
                    "failed_events": batch_result.failed_events,
                    "individual_results": batch_result.individual_results
                }
        
        else:
            # Fallback to standard processing
            return {
                "response": "I'll help you create calendar events. Could you provide more specific details about the events you'd like to create?",
                "requires_clarification": True
            }
            
    except Exception as e:
        logger.error(f"Error in smart calendar request handling: {e}", exc_info=True)
        return {
            "response": "I encountered an error while processing your calendar request. Please try again with more specific details.",
            "error": str(e)
        }