"""
Specialized methods for expert group tool integration.
These methods provide real tool usage for Research Specialist and Personal Assistant.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

from worker.services.ollama_service import invoke_llm_with_tokens
from worker.tool_handlers import _search_with_tavily
from shared.database.models import User, UserOAuthToken, GoogleService
from shared.utils.database_setup import get_db

logger = logging.getLogger(__name__)

async def collect_expert_input_with_tools(state: Dict[str, Any], agent_id_to_role: Dict) -> Dict[str, Any]:
    """Phase 2: Collect input from experts with real tool usage for specialized agents."""
    
    selected_agents = state["selected_agents"]
    pm_questions = state["pm_questions"]
    user_request = state["user_request"]
    user_id = state.get("user_id")
    
    expert_inputs = {}
    tool_calls_made = state.get("tool_calls_made", [])
    search_results = state.get("search_results", {})
    calendar_data = state.get("calendar_data", {})
    
    # Process each expert individually with tool specialization
    for agent_id in selected_agents:
        if agent_id not in agent_id_to_role:
            continue
            
        agent_role = agent_id_to_role[agent_id]
        expert_name = agent_role.value
        question = pm_questions.get(expert_name, f"What are your key considerations for: {user_request}")
        
        logger.info(f"Processing specialized expert: {expert_name}")
        
        # Specialized tool usage based on agent type
        if expert_name == "Research Specialist":
            expert_input = await research_specialist_with_tools(user_request, question, user_id, tool_calls_made, search_results)
        elif expert_name == "Personal Assistant":
            expert_input = await personal_assistant_with_tools(user_request, question, user_id, tool_calls_made, calendar_data)
        else:
            # Standard expert without special tools
            expert_input = await standard_expert_response(expert_name, user_request, question)
        
        expert_inputs[expert_name] = expert_input
        
        # Add to discussion context
        discussion_entry = {
            "expert": expert_name,
            "response": expert_input["input"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phase": "expert_input",
            "confidence": expert_input.get("confidence", 0.85),
            "tools_used": expert_input.get("tools_used", []),
            "metadata": expert_input.get("metadata", {})
        }
        state["discussion_context"].append(discussion_entry)
    
    # Update state with tool usage data
    state["expert_inputs"] = expert_inputs
    state["tool_calls_made"] = tool_calls_made
    state["search_results"] = search_results
    state["calendar_data"] = calendar_data
    state["current_phase"] = "planning"
    
    return state

async def research_specialist_with_tools(user_request: str, question: str, user_id: str, tool_calls_made: List, search_results: Dict) -> Dict[str, Any]:
    """Research Specialist with actual Tavily web search integration."""
    
    # Extract research topics from the user request
    research_analysis_prompt = f"""
    As a Research Specialist, analyze this request and identify specific research topics to investigate: {user_request}
    
    Question for you: {question}
    
    First, identify 2-3 specific search queries that would provide the most valuable research insights.
    Format your response as:
    
    SEARCH_QUERIES:
    1. [specific search query]
    2. [specific search query] 
    3. [specific search query]
    
    RESEARCH_FOCUS:
    [Brief explanation of what you plan to research and why]
    """
    
    research_plan, _ = await invoke_llm_with_tokens(
        messages=[{"role": "user", "content": research_analysis_prompt}],
        model_name="llama3.1:8b"
    )
    
    # Parse search queries from the response
    search_queries = []
    lines = research_plan.split('\n')
    in_queries_section = False
    
    for line in lines:
        line = line.strip()
        if line.startswith("SEARCH_QUERIES:"):
            in_queries_section = True
            continue
        elif line.startswith("RESEARCH_FOCUS:"):
            in_queries_section = False
            continue
        elif in_queries_section and line and (line.startswith(("1.", "2.", "3.", "-"))):
            query = line.split(".", 1)[1].strip() if "." in line else line.lstrip("- ").strip()
            if query:
                search_queries.append(query)
    
    # If no queries parsed, create fallback queries
    if not search_queries:
        search_queries = [
            f"{user_request} best practices",
            f"{user_request} latest research",
            f"{user_request} expert recommendations"
        ]
    
    # Perform actual web searches
    all_search_results = []
    for query in search_queries[:3]:  # Limit to 3 searches
        try:
            # Get user's API key if available
            if user_id:
                async with get_db() as db:
                    user = await db.get(User, int(user_id))
                    if user and user.web_search_api_key and user.web_search_provider == "tavily":
                        # Record tool call
                        tool_call = {
                            "tool": "tavily_search",
                            "query": query,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "expert": "Research Specialist"
                        }
                        tool_calls_made.append(tool_call)
                        
                        # Perform search
                        search_result = await _search_with_tavily(query, user.web_search_api_key)
                        if "response" in search_result:
                            search_info = {
                                "query": query,
                                "result": search_result["response"],
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
                            all_search_results.append(search_info)
                            logger.info(f"Research Specialist executed search: {query}")
                        else:
                            logger.warning(f"Search failed for query: {query}")
                    else:
                        logger.warning(f"No Tavily API key configured for user {user_id}")
                        # Add note about missing API key
                        all_search_results.append({
                            "query": query,
                            "result": "[Search not performed - Tavily API key not configured]",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
        except Exception as e:
            logger.error(f"Search error for query '{query}': {e}")
            all_search_results.append({
                "query": query,
                "result": f"[Search failed: {str(e)}]",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
    
    # Store search results
    search_results["Research Specialist"] = all_search_results
    
    # Generate expert response incorporating search results
    search_context = "\n\n".join([
        f"**Search: {sr['query']}**\n{sr['result']}"
        for sr in all_search_results
    ])
    
    final_response_prompt = f"""
    As a Research Specialist, you have conducted web research on: {user_request}
    
    Question: {question}
    
    Search results from your research:
    {search_context}
    
    Based on your research findings, provide a comprehensive response that:
    1. Synthesizes the key insights from your web research
    2. Identifies trends, best practices, and expert recommendations
    3. Addresses potential challenges and opportunities you discovered
    4. Provides specific, research-backed recommendations
    5. Cites the search results where relevant
    
    Focus on providing valuable insights that only proper research could uncover.
    """
    
    final_response, _ = await invoke_llm_with_tokens(
        messages=[{"role": "user", "content": final_response_prompt}],
        model_name="llama3.1:8b"
    )
    
    return {
        "input": final_response,
        "question_asked": question,
        "agent_id": "research_specialist",
        "tools_used": ["Tavily Web Search"],
        "confidence": 0.95 if successful_searches > 0 else 0.70,
        "metadata": {
            "searches_performed": len(all_search_results),
            "search_queries": search_queries,
            "research_based": successful_searches > 0,
            "successful_searches": successful_searches,
            "failed_searches": len(search_errors),
            "search_errors": search_errors if search_errors else None,
            "error_recovery": "Provided analysis based on available results" if search_errors else None
        }
    }

async def personal_assistant_with_tools(user_request: str, question: str, user_id: str, tool_calls_made: List, calendar_data: Dict) -> Dict[str, Any]:
    """Personal Assistant with actual Google Calendar integration."""
    
    # Analyze if calendar information would be helpful
    calendar_analysis_prompt = f"""
    As a Personal Assistant, analyze this request: {user_request}
    
    Question: {question}
    
    Determine if checking the user's calendar would be helpful for providing scheduling advice or time management recommendations.
    
    Respond with ONLY:
    - "CALENDAR_NEEDED" if calendar information would be valuable for your response
    - "CALENDAR_NOT_NEEDED" if calendar information is not necessary
    
    Then briefly explain why.
    """
    
    calendar_need_response, _ = await invoke_llm_with_tokens(
        messages=[{"role": "user", "content": calendar_analysis_prompt}],
        model_name="llama3.1:8b"
    )
    
    calendar_info = {}
    tools_used = []
    
    if "CALENDAR_NEEDED" in calendar_need_response.upper() and user_id:
        try:
            # Get Google Calendar service for the user
            from worker.services.google_calendar_service import GoogleCalendarService
            
            async with get_db() as db:
                # Get user's Google Calendar OAuth token
                oauth_token = await db.query(UserOAuthToken).filter(
                    UserOAuthToken.user_id == int(user_id),
                    UserOAuthToken.service == GoogleService.CALENDAR
                ).first()
                
                if oauth_token:
                    # Record tool call attempt
                    tool_call = {
                        "tool": "google_calendar",
                        "action": "check_availability",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "expert": "Personal Assistant",
                        "status": "attempting"
                    }
                    tool_calls_made.append(tool_call)
                    
                    try:
                        # Get calendar service and fetch recent/upcoming events with timeout
                        cal_service = GoogleCalendarService(oauth_token, db)
                        
                        # Get events for next 7 days
                        now = datetime.now(timezone.utc)
                        time_min = now.isoformat()
                        time_max = (now + timedelta(days=7)).isoformat()
                        
                        # Wrap calendar API call with timeout
                        try:
                            service = cal_service._get_google_service()
                            events_result = await asyncio.wait_for(
                                asyncio.create_task(
                                    asyncio.to_thread(
                                        lambda: service.events().list(
                                            calendarId='primary',
                                            timeMin=time_min,
                                            timeMax=time_max,
                                            singleEvents=True,
                                            orderBy='startTime',
                                            maxResults=20
                                        ).execute()
                                    )
                                ),
                                timeout=15.0  # 15 second timeout
                            )
                            
                            events = events_result.get('items', [])
                            
                            # Process calendar data
                            calendar_summary = []
                            for event in events:
                                try:
                                    start = event['start'].get('dateTime', event['start'].get('date'))
                                    end = event['end'].get('dateTime', event['end'].get('date'))
                                    summary = event.get('summary', 'Busy')
                                    
                                    calendar_summary.append({
                                        "title": summary,
                                        "start": start,
                                        "end": end
                                    })
                                except Exception as event_error:
                                    logger.warning(f"Error processing calendar event: {event_error}")
                                    continue
                            
                            calendar_info = {
                                "events_found": len(events),
                                "upcoming_events": calendar_summary[:10],  # Limit to 10 most recent
                                "period_checked": "next 7 days",
                                "status": "success"
                            }
                            tools_used.append("Google Calendar API")
                            tool_call["status"] = "success"
                            
                            logger.info(f"Personal Assistant checked calendar - found {len(events)} events")
                            
                        except asyncio.TimeoutError:
                            error_msg = "Calendar request timed out after 15 seconds"
                            logger.error(f"Calendar timeout for user {user_id}")
                            calendar_info = {
                                "error": error_msg,
                                "note": "Calendar information unavailable due to timeout",
                                "status": "timeout"
                            }
                            tool_call["status"] = "timeout"
                            tool_call["error"] = error_msg
                            
                        except Exception as api_error:
                            error_msg = f"Calendar API error: {str(api_error)}"
                            logger.error(f"Calendar API error for user {user_id}: {api_error}")
                            calendar_info = {
                                "error": error_msg,
                                "note": "Calendar information unavailable due to API error",
                                "status": "api_error"
                            }
                            tool_call["status"] = "api_error"
                            tool_call["error"] = error_msg
                            
                    except Exception as service_error:
                        error_msg = f"Calendar service error: {str(service_error)}"
                        logger.error(f"Calendar service error for user {user_id}: {service_error}")
                        calendar_info = {
                            "error": error_msg,
                            "note": "Calendar information unavailable due to service error",
                            "status": "service_error"
                        }
                        tool_call["status"] = "service_error"
                        tool_call["error"] = error_msg
                else:
                    error_msg = "Google Calendar not connected"
                    logger.warning(f"No Google Calendar access for user {user_id}")
                    calendar_info = {
                        "error": error_msg,
                        "note": "User needs to connect Google Calendar for scheduling assistance",
                        "status": "not_connected"
                    }
                    # Record failed tool call
                    tool_call = {
                        "tool": "google_calendar",
                        "action": "check_availability",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "expert": "Personal Assistant",
                        "status": "not_connected",
                        "error": error_msg
                    }
                    tool_calls_made.append(tool_call)
        except Exception as e:
            error_msg = f"Unexpected calendar error: {str(e)}"
            logger.error(f"Unexpected calendar access error: {e}", exc_info=True)
            calendar_info = {
                "error": error_msg,
                "note": "Calendar information unavailable due to unexpected error",
                "status": "unexpected_error"
            }
            # Record failed tool call
            tool_call = {
                "tool": "google_calendar",
                "action": "check_availability",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "expert": "Personal Assistant",
                "status": "unexpected_error",
                "error": error_msg
            }
            tool_calls_made.append(tool_call)
    
    # Store calendar data
    calendar_data["Personal Assistant"] = calendar_info
    
    # Generate response incorporating calendar information
    if calendar_info and "events_found" in calendar_info:
        calendar_context = f"""
        Calendar Information (checked {calendar_info['period_checked']}):
        - Found {calendar_info['events_found']} upcoming events
        
        Recent upcoming events:
        {chr(10).join([f"- {evt['title']}: {evt['start']}" for evt in calendar_info['upcoming_events'][:5]])}
        """
    else:
        calendar_context = "Calendar information not available or not needed for this request."
    
    final_response_prompt = f"""
    As a Personal Assistant, provide helpful scheduling and time management advice for: {user_request}
    
    Question: {question}
    
    {calendar_context}
    
    Based on your role as a Personal Assistant and any available calendar information, provide:
    1. Practical scheduling advice and time management recommendations
    2. Specific time slots or scheduling suggestions (if calendar data available)
    3. Productivity tips relevant to the request
    4. Action items for better organization
    5. Any calendar-based insights (if applicable)
    
    Be specific and actionable in your recommendations.
    """
    
    final_response, _ = await invoke_llm_with_tokens(
        messages=[{"role": "user", "content": final_response_prompt}],
        model_name="llama3.1:8b"
    )
    
    return {
        "input": final_response,
        "question_asked": question,
        "agent_id": "personal_assistant",
        "tools_used": tools_used or ["Time Management Analysis"],
        "confidence": 0.90,
        "metadata": {
            "calendar_checked": bool(calendar_info and "events_found" in calendar_info),
            "calendar_events_found": calendar_info.get("events_found", 0),
            "scheduling_focused": True
        }
    }

async def standard_expert_response(expert_name: str, user_request: str, question: str) -> Dict[str, Any]:
    """Standard expert response without specialized tools."""
    
    expert_prompt = f"""
    You are the {expert_name} in a professional consultation about: {user_request}
    
    Question: {question}
    
    Provide your expert perspective addressing:
    1. Key considerations from your domain expertise
    2. Potential challenges or opportunities you foresee
    3. Resources or methodologies that might be needed
    4. Your recommended approach
    5. Specific actionable advice
    
    Keep your response focused, professional, and actionable (2-3 paragraphs).
    """
    
    response, _ = await invoke_llm_with_tokens(
        messages=[{"role": "user", "content": expert_prompt}],
        model_name="llama3.1:8b"
    )
    
    return {
        "input": response,
        "question_asked": question,
        "agent_id": "standard_expert",
        "tools_used": ["Expert Knowledge"],
        "confidence": 0.85,
        "metadata": {
            "expert_domain": expert_name,
            "standard_response": True
        }
    }

def enhance_summary_with_tool_usage(final_summary: str, state: Dict[str, Any]) -> str:
    """Enhance the final summary with tool usage transparency."""
    
    tool_calls_made = state.get("tool_calls_made", [])
    search_results = state.get("search_results", {})
    calendar_data = state.get("calendar_data", {})
    
    # Enhance summary with tool usage transparency
    tool_usage_summary = ""
    if tool_calls_made:
        tool_usage_summary += "\n\n**Tools Used During Consultation:**\n"
        for tool_call in tool_calls_made:
            tool_usage_summary += f"- {tool_call['expert']}: Used {tool_call['tool']}"
            if 'query' in tool_call:
                tool_usage_summary += f" (Query: {tool_call['query']})"
            tool_usage_summary += "\n"
    
    if search_results:
        tool_usage_summary += "\n**Research Conducted:**\n"
        for expert, results in search_results.items():
            tool_usage_summary += f"- {expert}: {len(results)} web searches performed\n"
    
    if calendar_data:
        tool_usage_summary += "\n**Calendar Analysis:**\n"
        for expert, data in calendar_data.items():
            if "events_found" in data:
                tool_usage_summary += f"- {expert}: Checked calendar, found {data['events_found']} upcoming events\n"
            elif "error" in data:
                tool_usage_summary += f"- {expert}: Calendar check failed - {data['error']}\n"
    
    return final_summary + tool_usage_summary