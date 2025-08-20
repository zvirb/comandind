#!/usr/bin/env python3
"""
Individual calendar tools for Google Calendar integration.
Each tool handles a specific calendar operation with focused functionality.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from worker.services.google_calendar_service import (
    get_calendar_service,
    list_calendar_events,
    create_calendar_event as gcal_create_event,
    update_calendar_event as gcal_update_event,
)
from worker.services.progress_manager import progress_manager
from worker.graph_types import GraphState
from worker.calendar_categorization import (
    categorize_event,
    create_event_description_with_category,
    extract_category_from_description,
)

logger = logging.getLogger(__name__)


async def _handle_natural_language_calendar_request(state: GraphState, query: str) -> Dict[str, Any]:
    """
    Parse natural language calendar request and generate expert questions if needed.
    
    For complex requests with multiple events or missing details, this will:
    1. Parse the request to identify events and dates
    2. Identify missing information needed
    3. Generate expert questions for the user
    4. Send questions back via progress manager for fast chat response
    """
    logger.info(f"Parsing natural language calendar request: {query[:100]}...")
    
    try:
        from worker.services.ollama_service import invoke_llm_with_tokens
        
        # Use LLM to parse the request and identify what's needed
        parsing_prompt = f"""You are a calendar assistant. Analyze this user request and determine what information is needed to create calendar events.

User Request: {query}

Analyze the request and respond with JSON in this exact format:
{{
  "analysis": {{
    "events_identified": [
      {{
        "title": "Assignment title",
        "due_date": "2025-07-24",  
        "has_specific_time": false,
        "time_specified": null
      }}
    ],
    "missing_information": [
      "What time of day should these be due?",
      "Would you like reminders set? How far in advance?",
      "Any specific time zone preferences?"
    ],
    "can_proceed": false,
    "needs_clarification": true
  }}
}}

Guidelines:
- Look for assignment names, due dates, times
- If multiple assignments are listed, identify each one
- Check if specific times are mentioned (like "2pm", "morning", "end of day")
- If times are missing for due dates, set "has_specific_time": false
- Generate questions for missing critical information
- Set "can_proceed": true only if you have enough info to create events immediately
- Set "needs_clarification": true if you need to ask the user questions

Analyze the request:"""

        # Get the appropriate model for calendar analysis
        model_name = getattr(state, 'tool_selection_model', 'llama3.2:3b')
        
        messages = [
            {"role": "system", "content": "You are a calendar parsing expert. Always respond with valid JSON only."},
            {"role": "user", "content": parsing_prompt}
        ]
        
        response, _ = await invoke_llm_with_tokens(
            messages,
            model_name,
            category="calendar_parsing"
        )
        
        # Parse the JSON response
        import json
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        
        if json_start != -1 and json_end != -1:
            json_str = response[json_start:json_end]
            analysis = json.loads(json_str)
            
            # Check if we need clarification
            if analysis.get("analysis", {}).get("needs_clarification", True):
                missing_info = analysis.get("analysis", {}).get("missing_information", [])
                events_found = analysis.get("analysis", {}).get("events_identified", [])
                
                # Generate expert question response
                question_text = f"I found {len(events_found)} assignments that need to be added to your calendar:\n\n"
                
                for i, event in enumerate(events_found, 1):
                    question_text += f"{i}. {event.get('title', 'Assignment')} - Due: {event.get('due_date', 'Date unclear')}\n"
                
                question_text += f"\nTo create these calendar events, I need some additional information:\n\n"
                
                for i, question in enumerate(missing_info, 1):
                    question_text += f"{i}. {question}\n"
                
                question_text += "\nPlease provide these details so I can set up your calendar events properly."
                
                # Send expert question back to user via progress manager
                if state.session_id:
                    progress_manager.broadcast_to_session_sync_sync(state.session_id, {
                        "type": "expert_question",
                        "content": question_text,
                        "question_type": "calendar_clarification",
                        "context": {
                            "events_identified": events_found,
                            "missing_info": missing_info,
                            "original_query": query
                        }
                    })
                
                return {
                    "response": question_text,
                    "requires_user_input": True,
                    "expert_question": True,
                    "analysis": analysis
                }
            
            else:
                # Proceed with event creation if we have enough info
                return {"response": "Proceeding with event creation based on provided information..."}
        
        else:
            # Fallback if JSON parsing fails
            return {"response": "I'd be happy to help you add these assignments to your calendar. Could you please specify what time of day these should be due, and whether you'd like any reminders set?"}
    
    except Exception as e:
        logger.error(f"Error parsing natural language calendar request: {e}", exc_info=True)
        return {"response": "I can help you add these assignments to your calendar. Could you please provide specific times and any additional preferences for these events?"}


async def check_calendar_events(state: GraphState) -> Dict[str, Any]:
    """
    Check for calendar events in a specific time period.
    
    Expected tool_output parameters:
    - start_date: ISO format date/datetime (optional, defaults to today)
    - end_date: ISO format date/datetime (optional, defaults to start_date + 7 days)
    - calendar_id: Calendar ID (optional, defaults to 'primary')
    """
    tool_output = state.tool_output or {}
    user_id = state.user_id
    
    logger.info("--- Checking calendar events ---")
    
    if not user_id:
        return {"response": "Error: User ID is missing, cannot access calendar."}
    
    try:
        # Parse parameters
        start_date = tool_output.get("start_date")
        end_date = tool_output.get("end_date")
        calendar_id = tool_output.get("calendar_id", "primary")
        
        # Default to checking the next 7 days if no dates provided
        if not start_date:
            start_date = datetime.now().isoformat()
        if not end_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end_dt = start_dt + timedelta(days=7)
            end_date = end_dt.isoformat()
        
        # Get calendar service
        service = await get_calendar_service(int(user_id))
        if not service:
            return {"response": "Error: Could not connect to your calendar service."}
        
        # Get events
        events = await list_calendar_events(service, calendar_id, start_date, end_date)
        
        if not events:
            return {"response": f"No events found between {start_date[:10]} and {end_date[:10]}."}
        
        # Format events for response
        event_list = []
        for event in events:
            start_time = event.get('start', {})
            start_str = start_time.get('dateTime', start_time.get('date', 'No time'))
            
            end_time = event.get('end', {})
            end_str = end_time.get('dateTime', end_time.get('date', 'No time'))
            
            summary = event.get('summary', 'No Title')
            description = event.get('description', '')
            location = event.get('location', '')
            
            # Extract category from description if available
            category = extract_category_from_description(description)
            
            event_info = f"**{summary}**"
            if category:
                event_info += f" ({category})"
            event_info += "\n"
            event_info += f"- Start: {start_str[:16] if 'T' in start_str else start_str}\n"
            event_info += f"- End: {end_str[:16] if 'T' in end_str else end_str}\n"
            if location:
                event_info += f"- Location: {location}\n"
            if description and not description.startswith('[Category:'):
                # Only show description if it's not just a category tag
                clean_description = description.split('[Category:')[0].strip()
                if clean_description:
                    event_info += f"- Description: {clean_description[:100]}{'...' if len(clean_description) > 100 else ''}\n"
            event_info += f"- Event ID: {event.get('id')}"
            
            event_list.append(event_info)
        
        response = f"Found {len(events)} events between {start_date[:10]} and {end_date[:10]}:\n\n"
        response += "\n\n---\n\n".join(event_list)
        
        return {"response": response}
        
    except Exception as e:
        logger.error(f"Error checking calendar events: {e}", exc_info=True)
        return {"response": "An error occurred while checking your calendar events."}


async def create_calendar_event_tool(state: GraphState) -> Dict[str, Any]:
    """
    Create calendar events from structured data or natural language.
    
    Expected tool_output parameters:
    Option 1 - Structured event:
    - summary: Event title (required)
    - start_time: ISO format datetime (required) 
    - end_time: ISO format datetime (required)
    - description: Event description (optional)
    - location: Event location (optional)
    - calendar_id: Calendar ID (optional, defaults to 'primary')
    
    Option 2 - Natural language:
    - natural_language_query: Full user request to parse and create events
    """
    tool_output = state.tool_output or {}
    user_id = state.user_id
    
    logger.info("--- Creating calendar event ---")
    
    if not user_id:
        return {"response": "Error: User ID is missing, cannot access calendar."}
    
    # Check if this is a natural language request that needs parsing
    natural_language_query = tool_output.get("natural_language_query")
    if natural_language_query:
        return await _handle_natural_language_calendar_request(state, natural_language_query)
    
    try:
        # Handle structured event creation
        summary = tool_output.get("summary")
        start_time = tool_output.get("start_time")
        end_time = tool_output.get("end_time")
        
        if not summary or not start_time or not end_time:
            return {"response": "Error: Event title (summary), start_time, and end_time are required."}
        
        # Optional parameters
        description = tool_output.get("description", "")
        location = tool_output.get("location", "")
        calendar_id = tool_output.get("calendar_id", "primary")
        
        # Get calendar service
        service = await get_calendar_service(int(user_id))
        if not service:
            return {
                "response": "❌ **Calendar connection failed.** Your Google Calendar access token may have expired. Please reconnect your Google Calendar in Settings → Integrations.",
                "success": False,
                "error": "calendar_auth_expired"
            }
        
        # Categorize the event and get appropriate color
        category, color_id = await categorize_event(summary, description, int(user_id))
        
        # Add category tag to description
        tagged_description = create_event_description_with_category(description, category)
        
        # Prepare event data with color
        event_data = {
            "summary": summary,
            "description": tagged_description,
            "start": {"dateTime": start_time, "timeZone": "UTC"},
            "end": {"dateTime": end_time, "timeZone": "UTC"},
            "colorId": color_id,  # Set Google Calendar color
        }
        
        if location:
            event_data["location"] = location
        
        # Create event
        result = await gcal_create_event(service, calendar_id, event_data)
        
        if result and result.get("htmlLink"):
            # Broadcast success
            if state.session_id:
                progress_manager.broadcast_to_session_sync_sync(state.session_id, {
                    "type": "calendar_event_created",
                    "content": f"Created calendar event: {summary}",
                    "event_name": summary,
                    "event_link": result.get('htmlLink')
                })
            
            return {
                "response": f"✅ Event '{summary}' created successfully (Category: {category}).\nView it here: {result.get('htmlLink')}",
                "success": True,
                "event_id": result.get('id'),
                "event_link": result.get('htmlLink')
            }
        else:
            return {
                "response": "Failed to create the calendar event.",
                "success": False,
                "error": "calendar_creation_failed"
            }
            
    except Exception as e:
        logger.error(f"Error creating calendar event: {e}", exc_info=True)
        return {
            "response": "An error occurred while creating the calendar event.",
            "success": False,
            "error": str(e)
        }


async def edit_calendar_event_tool(state: GraphState) -> Dict[str, Any]:
    """
    Edit an existing Google Calendar event.
    
    Expected tool_output parameters:
    - event_id: Google Calendar event ID (required)
    - summary: New event title (optional)
    - start_time: New start time in ISO format (optional)
    - end_time: New end time in ISO format (optional)
    - description: New description (optional)
    - location: New location (optional)
    - calendar_id: Calendar ID (optional, defaults to 'primary')
    """
    tool_output = state.tool_output or {}
    user_id = state.user_id
    
    logger.info("--- Editing calendar event ---")
    
    if not user_id:
        return {"response": "Error: User ID is missing, cannot access calendar."}
    
    try:
        # Validate required parameters
        event_id = tool_output.get("event_id")
        if not event_id:
            return {"response": "Error: Event ID is required to edit an event."}
        
        calendar_id = tool_output.get("calendar_id", "primary")
        
        # Get calendar service
        service = await get_calendar_service(int(user_id))
        if not service:
            return {"response": "Error: Could not connect to your calendar service."}
        
        # First, get the existing event
        try:
            existing_event = await asyncio.to_thread(
                service.events().get(calendarId=calendar_id, eventId=event_id).execute
            )
        except Exception as e:
            logger.error(f"Error getting existing event: {e}")
            return {"response": f"Error: Could not find event with ID '{event_id}'."}
        
        # Update only the fields provided
        event_data = existing_event.copy()
        
        # Track if we need to recategorize
        needs_recategorization = False
        new_summary = None
        new_description = None
        
        if "summary" in tool_output and tool_output["summary"]:
            new_summary = tool_output["summary"]
            event_data["summary"] = new_summary
            needs_recategorization = True
        
        if "description" in tool_output:
            # Extract original description without category tag
            original_description = tool_output["description"]
            new_description = original_description
            needs_recategorization = True
            
        if "location" in tool_output:
            event_data["location"] = tool_output["location"]
        
        if "start_time" in tool_output and tool_output["start_time"]:
            event_data["start"] = {"dateTime": tool_output["start_time"], "timeZone": "UTC"}
            
        if "end_time" in tool_output and tool_output["end_time"]:
            event_data["end"] = {"dateTime": tool_output["end_time"], "timeZone": "UTC"}
        
        # Recategorize if summary or description changed
        if needs_recategorization:
            final_summary = new_summary or existing_event.get("summary", "")
            final_description = new_description if new_description is not None else ""
            
            # Get existing category if description wasn't changed
            if new_description is None:
                existing_category = extract_category_from_description(existing_event.get("description", ""))
                if existing_category:
                    # Keep existing category and color if description wasn't changed
                    final_description = create_event_description_with_category("", existing_category)
                    event_data["description"] = final_description
                    # Keep existing color if it has one
                    if not existing_event.get("colorId"):
                        from worker.calendar_categorization import get_color_for_category
                        event_data["colorId"] = get_color_for_category(existing_category, int(user_id))
                else:
                    # Categorize with new summary
                    category, color_id = await categorize_event(final_summary, final_description, int(user_id))
                    tagged_description = create_event_description_with_category(final_description, category)
                    event_data["description"] = tagged_description
                    event_data["colorId"] = color_id
            else:
                # Recategorize with new description
                category, color_id = await categorize_event(final_summary, final_description, int(user_id))
                tagged_description = create_event_description_with_category(final_description, category)
                event_data["description"] = tagged_description
                event_data["colorId"] = color_id
        
        # Update event
        result = await gcal_update_event(service, calendar_id, event_id, event_data)
        
        if result and result.get("htmlLink"):
            return {"response": f"✅ Event '{result.get('summary')}' updated successfully.\nView it here: {result.get('htmlLink')}"}
        else:
            return {"response": "Failed to update the calendar event."}
            
    except Exception as e:
        logger.error(f"Error editing calendar event: {e}", exc_info=True)
        return {"response": "An error occurred while editing the calendar event."}


async def delete_calendar_event_tool(state: GraphState) -> Dict[str, Any]:
    """
    Delete a Google Calendar event.
    
    Expected tool_output parameters:
    - event_id: Google Calendar event ID (required)
    - calendar_id: Calendar ID (optional, defaults to 'primary')
    """
    tool_output = state.tool_output or {}
    user_id = state.user_id
    
    logger.info("--- Deleting calendar event ---")
    
    if not user_id:
        return {"response": "Error: User ID is missing, cannot access calendar."}
    
    try:
        # Validate required parameters
        event_id = tool_output.get("event_id")
        if not event_id:
            return {"response": "Error: Event ID is required to delete an event."}
        
        calendar_id = tool_output.get("calendar_id", "primary")
        
        # Get calendar service
        service = await get_calendar_service(int(user_id))
        if not service:
            return {"response": "Error: Could not connect to your calendar service."}
        
        # Get event title before deletion
        event_title = "Unknown Event"
        try:
            existing_event = await asyncio.to_thread(
                service.events().get(calendarId=calendar_id, eventId=event_id).execute
            )
            event_title = existing_event.get("summary", "Unknown Event")
        except Exception as e:
            logger.warning(f"Could not get event title before deletion: {e}")
        
        # Delete event
        await asyncio.to_thread(
            service.events().delete(calendarId=calendar_id, eventId=event_id).execute
        )
        
        return {"response": f"✅ Event '{event_title}' deleted successfully."}
        
    except Exception as e:
        logger.error(f"Error deleting calendar event: {e}", exc_info=True)
        return {"response": "An error occurred while deleting the calendar event."}


async def move_calendar_event_tool(state: GraphState) -> Dict[str, Any]:
    """
    Move an existing Google Calendar event to a new date and time.
    
    Expected tool_output parameters:
    - event_id: Google Calendar event ID (required)
    - new_start_time: New start time in ISO format (required)
    - new_end_time: New end time in ISO format (optional, will maintain duration if not provided)
    - calendar_id: Calendar ID (optional, defaults to 'primary')
    """
    tool_output = state.tool_output or {}
    user_id = state.user_id
    
    logger.info("--- Moving calendar event ---")
    
    if not user_id:
        return {"response": "Error: User ID is missing, cannot access calendar."}
    
    try:
        # Validate required parameters
        event_id = tool_output.get("event_id")
        new_start_time = tool_output.get("new_start_time")
        
        if not event_id or not new_start_time:
            return {"response": "Error: Event ID and new start time are required to move an event."}
        
        calendar_id = tool_output.get("calendar_id", "primary")
        new_end_time = tool_output.get("new_end_time")
        
        # Get calendar service
        service = await get_calendar_service(int(user_id))
        if not service:
            return {"response": "Error: Could not connect to your calendar service."}
        
        # Get the existing event
        try:
            existing_event = await asyncio.to_thread(
                service.events().get(calendarId=calendar_id, eventId=event_id).execute
            )
        except Exception as e:
            logger.error(f"Error getting existing event: {e}")
            return {"response": f"Error: Could not find event with ID '{event_id}'."}
        
        # Calculate duration if new_end_time not provided
        if not new_end_time:
            old_start = existing_event.get("start", {})
            old_end = existing_event.get("end", {})
            
            old_start_str = old_start.get("dateTime") or old_start.get("date")
            old_end_str = old_end.get("dateTime") or old_end.get("date")
            
            if old_start_str and old_end_str:
                try:
                    old_start_dt = datetime.fromisoformat(old_start_str.replace('Z', '+00:00'))
                    old_end_dt = datetime.fromisoformat(old_end_str.replace('Z', '+00:00'))
                    duration = old_end_dt - old_start_dt
                    
                    new_start_dt = datetime.fromisoformat(new_start_time.replace('Z', '+00:00'))
                    new_end_dt = new_start_dt + duration
                    new_end_time = new_end_dt.isoformat()
                except Exception as e:
                    logger.error(f"Error calculating duration: {e}")
                    return {"response": "Error: Could not calculate event duration. Please provide both start and end times."}
        
        # Update the event with new times while preserving categorization
        event_data = existing_event.copy()
        event_data["start"] = {"dateTime": new_start_time, "timeZone": "UTC"}
        event_data["end"] = {"dateTime": new_end_time, "timeZone": "UTC"}
        
        # Ensure category tag and color are preserved
        existing_description = existing_event.get("description", "")
        existing_category = extract_category_from_description(existing_description)
        
        if existing_category:
            # Preserve existing category and ensure color is set
            if not existing_event.get("colorId"):
                from worker.calendar_categorization import get_color_for_category
                event_data["colorId"] = get_color_for_category(existing_category, int(user_id))
        else:
            # Recategorize if no existing category (shouldn't happen with our new system)
            summary = existing_event.get("summary", "")
            category, color_id = await categorize_event(summary, "", int(user_id))
            tagged_description = create_event_description_with_category(existing_description, category)
            event_data["description"] = tagged_description
            event_data["colorId"] = color_id
        
        # Update event
        result = await gcal_update_event(service, calendar_id, event_id, event_data)
        
        if result and result.get("htmlLink"):
            event_name = result.get("summary", "Event")
            return {"response": f"✅ Event '{event_name}' moved successfully to {new_start_time[:16]}.\nView it here: {result.get('htmlLink')}"}
        else:
            return {"response": "Failed to move the calendar event."}
            
    except Exception as e:
        logger.error(f"Error moving calendar event: {e}", exc_info=True)
        return {"response": "An error occurred while moving the calendar event."}