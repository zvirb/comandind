# /app/tool_handlers.py

# --- Standard Library Imports ---
import asyncio
import datetime
import logging
import os
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, List, Optional

# --- Third-Party Imports ---
from tavily import TavilyClient #type: ignore

# --- Local Application Imports ---
# NOTE: If 'utils' is part of your app, its import might also need a full path
# e.g., from worker.utils.text_utils import ...
from worker.utils.text_utils import extract_json_with_self_correction

from shared.utils.config import get_settings
from worker import shared_constants as constants
from worker.services.google_calendar_service import (
    create_calendar_event as gcal_create_event,
    get_calendar_service,
)
from worker.services.gmail_service import (
    get_gmail_service,
    get_recent_emails,
    search_emails,
)
from worker.services.google_drive_service import (
    get_drive_service,
    list_drive_files,
    download_file_content,
    search_files_by_content,
    get_file_metadata,
)
from worker.services.home_assistant_service import (
    call_home_assistant_service,
)
from worker.services.ollama_service import invoke_llm, invoke_llm_stream
from worker.services.progress_manager import progress_manager
from worker.services.qdrant_service import QdrantService
from worker.utils.embeddings import get_embeddings
from worker.tools.socratic_guidance_tool import socratic_guidance_tool
from worker.email_tools import (
    compose_email,
    get_email_templates,
    schedule_email,
    get_email_analytics,
    prioritize_emails,
    generate_email_summary
)
from worker.task_management_tools import (
    create_task,
    update_task_status,
    get_task_list,
    prioritize_tasks,
    get_task_analytics,
    create_task_template,
    estimate_task_completion
)
from worker.calendar_tools import (
    check_calendar_events,
    create_calendar_event_tool,
    edit_calendar_event_tool,
    delete_calendar_event_tool,
    move_calendar_event_tool,
)
# from worker.reflective_coach_tools (
#     initiate_socratic_dialogue,
#     ask_clarifying_questions,
#     summarize_and_reflect,
#     identify_themes_and_patterns,
#     guide_goal_setting,
#     measure_progress,
#     conclude_session,
# )

from worker.graph_types import GraphState
from worker.services.smart_tool_wrapper import smart_task_tool, smart_email_tool, smart_file_tool
from worker.services.intelligent_list_parser import handle_list_parsing_request
from worker.services.dynamic_user_input import handle_user_input_request
from worker.services.llm_calendar_parser import handle_llm_calendar_parsing

logger = logging.getLogger(__name__)
settings = get_settings()

def get_model_for_task(state: GraphState, task_type: str) -> str:
    """
    Returns the appropriate model name for a specific task type.
    Falls back to default model if specialized model not configured.
    """
    default_model = settings.OLLAMA_GENERATION_MODEL_NAME
    
    if task_type == "chat":
        return state.chat_model or state.selected_model or default_model
    elif task_type == "initial_assessment":
        return state.initial_assessment_model or state.selected_model or default_model
    elif task_type == "tool_selection":
        return state.tool_selection_model or state.selected_model or default_model
    elif task_type == "embeddings":
        return state.embeddings_model or state.selected_model or default_model
    elif task_type == "coding":
        return state.coding_model or state.selected_model or default_model
    else:
        return state.selected_model or default_model

# Define a secure workspace for the agent based on the Docker volume mount
AGENT_WORKSPACE = "/app/documents"

# --- System Prompts ---
SYSTEM_PROMPT_EXTRACT_HA_SERVICE_CALL = """
You are an expert assistant that translates natural language commands into structured Home Assistant service calls.
Your goal is to identify the domain, service, and entity data from the user's request.
You MUST return the details in a single, valid JSON object. Do not add any explanatory text before or after the JSON.

The JSON object should have the following structure:
{
  "domain": "e.g., light, switch, climate",
  "service": "e.g., turn_on, turn_off, set_temperature",
  "entity_data": {
    "entity_id": "e.g., light.living_room_lights, switch.office_fan",
    "temperature": "e.g., 22 (only for climate services)",
    "brightness_pct": "e.g., 50 (only for light.turn_on)"
  }
}

Examples:
- User: "turn on the living room lights" -> {"domain": "light", "service": "turn_on", "entity_data": {"entity_id": "light.living_room_lights"}}
- User: "set the thermostat to 22 degrees" -> {"domain": "climate", "service": "set_temperature", "entity_data": {"entity_id": "climate.thermostat", "temperature": 22}}
- User: "turn off the office fan" -> {"domain": "switch", "service": "turn_off", "entity_data": {"entity_id": "switch.office_fan"}}
"""

SYSTEM_PROMPT_EXTRACT_EVENT_DETAILS = """
You are an expert assistant that extracts structured event details from a user's natural language request.
Your goal is to identify the event summary (title), start time, and end time.
The current time is {current_time}.
If the user does not specify a duration, assume a default duration of 60 minutes.
If the user provides a vague time like "tomorrow morning", interpret it as 9 AM tomorrow.
You MUST return the event details in a single, valid JSON object. Do not add any explanatory text before or after the JSON.

For the event title (summary), extract the key activity or subject, not the entire request. For example:
- "book study time" → "Study"
- "schedule a meeting with John" → "Meeting with John"
- "book time to work on project" → "Work on project"
- "reserve conference room" → "Conference room reservation"

The JSON object should have the following structure:
{{
  "summary": "The title of the event (extract the key activity, not the entire request)",
  "start_time": "The start time in ISO 8601 format (e.g., YYYY-MM-DDTHH:MM:SS)",
  "end_time": "The end time in ISO 8601 format (e.g., YYYY-MM-DDTHH:MM:SS)",
  "description": "A brief description of the event, if provided by the user."
}}
"""

# --- Main Tool Handling Functions ---

# Old calendar handler removed - now using individual calendar tools
async def _retrieve_relevant_documents(question: str, user_id: int, search_limit: int) -> List[str]:
    """Generates embedding for a question and retrieves relevant documents from Qdrant."""
    question_embedding = await get_embeddings([question])
    if not question_embedding:
        raise ValueError("Failed to generate embedding for the user's question.")

    qdrant_service = QdrantService()
    search_results = await qdrant_service.search(
        vector=question_embedding[0],
        user_id=user_id,
        limit=search_limit
    )

    # The search result is a list of ScoredPoint objects. The payload is a dict.
    # We need to extract the 'content' from the payload.
    return [hit.payload['content'] for hit in search_results if hit.payload and 'content' in hit.payload]

async def _generate_rag_answer(question: str, context_documents: List[str], selected_model: str) -> str:
    """Constructs a RAG prompt and invokes the LLM to get an answer."""
    context_str = "\n\n".join(context_documents)
    rag_prompt = f"Based on the following documents, answer the question:\n\nDocuments:\n{context_str}\n\nQuestion: {question}\n\nAnswer:"
    return await invoke_llm(messages=[{"role": "user", "content": rag_prompt}], model_name=selected_model)

async def handle_document_qa(state: GraphState) -> Dict[str, Any]:
    """
    Handles questions about uploaded documents using RAG (Retrieval-Augmented Generation).
    It retrieves relevant documents from Qdrant and uses an LLM to answer the question.
    """
    tool_output = state.tool_output or {}
    user_question = tool_output.get("question", "")
    user_id_str: str | None = state.user_id
    settings = get_settings()
    selected_model = get_model_for_task(state, "embeddings")  # Use embeddings model for document QA
    logger.info(f"--- Handling Document Q&A for question: '{user_question}' ---")

    if not user_question or not user_id_str:
        return {"response": "No question or user ID provided for document Q&A."}

    try:
        settings = get_settings()
        search_limit = settings.DEFAULT_DOCUMENT_SEARCH_LIMIT

        # 1. Retrieve relevant documents
        context_documents = await _retrieve_relevant_documents(user_question, int(user_id_str), search_limit)
        if not context_documents:
            return {"response": "I couldn't find any relevant documents to answer your question."}

        # 2. Generate answer based on context
        answer = await _generate_rag_answer(user_question, context_documents, selected_model)
        return {"response": answer}
    except Exception as e:
        logger.error(f"Error during document Q&A for user {user_id_str}: {e}", exc_info=True)
        return {"response": "An error occurred while trying to answer your question from the documents."}

async def handle_calendar_interaction(state: GraphState) -> Dict[str, Any]:
    """
    Enhanced calendar interaction handler with smart multi-event processing.
    Analyzes the user's request and uses intelligent routing and batch processing.
    """
    user_input = state.user_input.lower()
    
    try:
        # Simple routing logic based on keywords in the user input
        if any(word in user_input for word in ["check", "show", "list", "what's", "what is", "see", "view"]):
            # Route to check calendar events
            return await check_calendar_events(state)
        
        elif any(word in user_input for word in ["edit", "update", "change", "modify", "alter"]):
            # Route to edit calendar event
            return await edit_calendar_event_tool(state)
        
        elif any(word in user_input for word in ["delete", "remove", "cancel", "drop"]):
            # Route to delete calendar event
            return await delete_calendar_event_tool(state)
        
        elif any(word in user_input for word in ["move", "reschedule", "shift"]):
            # Route to move calendar event
            return await move_calendar_event_tool(state)
        
        else:
            # For create/add requests and general calendar requests, use smart processing
            from worker.enhanced_calendar_tools import handle_smart_calendar_request
            return await handle_smart_calendar_request(state)
    
    except Exception as e:
        logger.error(f"Error in calendar interaction handler: {e}", exc_info=True)
        return {
            "response": "I encountered an error while trying to help with your calendar request. Please try again or be more specific about what you'd like me to do.",
            "error": str(e)
        }

async def handle_unstructured_interaction(state: GraphState) -> Dict[str, Any]:
    """Handles direct queries to the LLM for general conversation, streaming the response."""
    user_query = state.user_input
    session_id = state.session_id
    settings = get_settings()
    selected_model = get_model_for_task(state, "chat")
    logger.info(f"--- Handling Unstructured Interaction for query: '{user_query}' ---")

    # Get memory context from state for enhanced responses
    memory_context = getattr(state, 'memory_context', {})
    
    # Build enhanced system prompt with memory context
    system_prompt = "You are a helpful AI assistant."
    
    # Add user patterns and preferences if available
    user_patterns = memory_context.get('user_patterns', {})
    if user_patterns:
        system_prompt += f"\n\nUser Context:"
        if user_patterns.get('communication_style'):
            system_prompt += f"\n- Communication style: {user_patterns['communication_style']}"
        if user_patterns.get('interests'):
            system_prompt += f"\n- Interests: {', '.join(user_patterns['interests'])}"
        if user_patterns.get('preferences'):
            system_prompt += f"\n- Preferences: {user_patterns['preferences']}"
    
    # Build conversation messages with memory context
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add relevant semantic context if available
    semantic_context = memory_context.get('semantic_context', [])
    if semantic_context:
        context_summary = "Based on our previous conversations:"
        for context in semantic_context[:3]:  # Use top 3 most relevant
            context_summary += f"\n- {context.get('content', '')[:100]}..."
        messages.append({"role": "system", "content": f"Relevant context: {context_summary}"})
    
    # Add recent conversation history
    conversation_history = memory_context.get('conversation_history', [])
    for msg in conversation_history[-8:]:  # Use last 8 messages to leave room for context
        if msg.get('role') and msg.get('content'):
            messages.append({"role": msg['role'], "content": msg['content']})
    
    # Add current user query
    messages.append({"role": "user", "content": user_query})
    
    logger.info(f"Enhanced prompt with {len(messages)} messages including memory context")
    
    # This is now a streaming handler with memory
    # We will collect the full response to store in history, but stream it to the user
    full_response = ""
    try:
        async for token in invoke_llm_stream(
            messages=messages,
            model_name=selected_model,
        ):
            full_response += token
            if session_id:
                # Send progressive agent message with accumulated content
                await progress_manager.broadcast_agent_message(
                    session_id=session_id,
                    agent_name="AI Assistant",
                    content=full_response,  # Send accumulated content, not just token
                    agent_type="streaming",
                    metadata={"is_partial": True, "token_count": len(full_response.split())}
                )

        # After streaming is complete, send final complete message
        if session_id:
            await progress_manager.broadcast_agent_message(
                session_id=session_id,
                agent_name="AI Assistant", 
                content=full_response,
                agent_type="streaming",
                metadata={"is_partial": False, "final": True}
            )

    except Exception as e:
        logger.error(f"Error during streaming LLM response: {e}", exc_info=True)
        error_message = "Sorry, I encountered an error while generating a response."
        if session_id:
            await progress_manager.broadcast_to_session_sync(
                session_id, {"type": "error", "content": error_message}
            )
        return {"response": error_message}

    # The final, complete response is returned to be stored in the graph state
    return {"response": full_response}

@smart_email_tool
async def handle_email_interaction(state: GraphState) -> Dict[str, Any]:
    """
    Handles email interactions including reading recent emails, searching, and summarizing.
    """
    tool_output = state.tool_output or {}
    action = tool_output.get("action", "")
    details = tool_output.get("details", {})
    user_id_str: str | None = state.user_id
    settings = get_settings()
    selected_model = get_model_for_task(state, "chat")

    if not user_id_str:
        return {"response": "User ID is required for email operations."}

    user_id = int(user_id_str)
    
    logger.info(f"--- Handling Email Interaction: action='{action}' ---")

    try:
        # Get Gmail service for the user
        service = get_gmail_service(user_id)
        if not service:
            return {"response": "Error: Could not connect to your Gmail account. Please ensure you have connected Gmail in your settings."}

        if action.lower() in ["read", "read emails", "read unread emails", "check emails", "recent emails"]:
            # Get recent emails
            max_results = int(details.get("count", 10))
            emails = await get_recent_emails(service, max_results=max_results)
            
            if not emails:
                return {"response": "No recent emails found in your inbox."}
            
            # Format the email summary
            email_summaries = []
            for email in emails:
                summary = f"**From:** {email['sender']}\n**Subject:** {email['subject']}\n**Date:** {email['date']}\n**Preview:** {email['snippet'][:100]}..."
                email_summaries.append(summary)
            
            response = f"Here are your {len(emails)} most recent emails:\n\n" + "\n\n---\n\n".join(email_summaries)
            return {"response": response}

        elif action.lower() in ["search", "search emails", "find emails"]:
            # Search emails
            query = details.get("query", "")
            if not query:
                return {"response": "Please provide a search query to find emails."}
            
            max_results = int(details.get("count", 10))
            emails = await search_emails(service, query, max_results=max_results)
            
            if not emails:
                return {"response": f"No emails found matching the search query: '{query}'"}
            
            # Format the search results
            email_summaries = []
            for email in emails:
                summary = f"**From:** {email['sender']}\n**Subject:** {email['subject']}\n**Date:** {email['date']}\n**Preview:** {email['snippet'][:100]}..."
                email_summaries.append(summary)
            
            response = f"Found {len(emails)} emails matching '{query}':\n\n" + "\n\n---\n\n".join(email_summaries)
            return {"response": response}

        elif action.lower() in ["summarize", "summarize emails", "email summary"]:
            # Get recent emails and create an AI summary
            max_results = int(details.get("count", 5))
            emails = await get_recent_emails(service, max_results=max_results)
            
            if not emails:
                return {"response": "No recent emails found to summarize."}
            
            # Create email context for LLM
            email_context = []
            for email in emails:
                context = f"From: {email['sender']}\nSubject: {email['subject']}\nDate: {email['date']}\nContent: {email['snippet']}"
                email_context.append(context)
            
            # Use LLM to create summary
            emails_text = "\n\n---\n\n".join(email_context)
            summary_prompt = f"Please provide a concise summary of these recent emails, highlighting any important information, urgent matters, or action items:\n\n{emails_text}"
            
            summary = await invoke_llm(messages=[
                {"role": "system", "content": "You are a helpful email assistant. Provide clear, concise summaries of email content."},
                {"role": "user", "content": summary_prompt}
            ], model_name=selected_model)
            
            return {"response": f"**Email Summary:**\n\n{summary}"}

        elif action.lower() in ["compose", "compose email", "write email", "create email"]:
            # Compose a new email
            recipient = details.get("recipient", "")
            subject = details.get("subject", "")
            body = details.get("body", "")
            priority = details.get("priority", "normal")
            
            if not recipient or not subject:
                return {"response": "Both recipient and subject are required to compose an email."}
            
            result = compose_email(recipient, subject, body, priority)
            return {"response": result["message"]}

        elif action.lower() in ["templates", "email templates", "get templates"]:
            # Get email templates
            result = get_email_templates()
            if result["success"]:
                template_list = []
                for name, template in result["templates"].items():
                    template_list.append(f"**{name}:**\n  Subject: {template['subject']}\n  Body: {template['body'][:100]}...")
                
                response = "Available email templates:\n\n" + "\n\n".join(template_list)
                return {"response": response}
            else:
                return {"response": "Failed to retrieve email templates."}

        elif action.lower() in ["analytics", "email analytics", "email stats"]:
            # Get email analytics
            result = get_email_analytics()
            if result["success"]:
                analytics = result["analytics"]
                response = f"""**Email Analytics:**

**Today:**
- Sent: {analytics['today']['sent']}
- Received: {analytics['today']['received']}  
- Unread: {analytics['today']['unread']}

**This Week:**
- Sent: {analytics['this_week']['sent']}
- Received: {analytics['this_week']['received']}
- Unread: {analytics['this_week']['unread']}

**Average Response Time:** {analytics['response_time_avg']}

**Top Contacts:**
{chr(10).join([f"- {contact['email']} ({contact['count']} emails)" for contact in analytics['top_contacts']])}"""
                return {"response": response}
            else:
                return {"response": "Failed to retrieve email analytics."}

        elif action.lower() in ["prioritize", "prioritize emails", "sort emails"]:
            # Prioritize emails (using existing Gmail integration)
            max_results = int(details.get("count", 10))
            emails = await get_recent_emails(service, max_results=max_results)
            
            if not emails:
                return {"response": "No emails found to prioritize."}
            
            # Convert to format expected by prioritize_emails
            email_list = []
            for email in emails:
                email_data = {
                    "subject": email["subject"],
                    "sender": email["sender"],
                    "received_hours_ago": 1,  # Default value, would calculate in real implementation
                }
                email_list.append(email_data)
            
            result = prioritize_emails(email_list)
            if result["success"]:
                prioritized = result["prioritized_emails"][:5]  # Show top 5
                response_list = []
                for i, email in enumerate(prioritized, 1):
                    response_list.append(f"{i}. **{email['subject']}** (Score: {email['priority_score']})\n   From: {email['sender']}")
                
                response = "**Top Priority Emails:**\n\n" + "\n\n".join(response_list)
                return {"response": response}
            else:
                return {"response": result["message"]}

        else:
            return {"response": f"I don't understand the email action '{action}'. Available actions are: read emails, search emails, summarize emails, compose email, email templates, email analytics, prioritize emails."}

    except Exception as e:
        logger.error(f"An unexpected error occurred in handle_email_interaction: {e}", exc_info=True)
        return {"response": "An unexpected error occurred while handling your email request."}

async def handle_drive_interaction(state: GraphState) -> Dict[str, Any]:
    """
    Handles Google Drive interactions including searching files, downloading documents, and importing content.
    """
    tool_output = state.tool_output or {}
    action = tool_output.get("action", "")
    details = tool_output.get("details", {})
    user_id_str: str | None = state.user_id
    settings = get_settings()
    selected_model = get_model_for_task(state, "chat")

    if not user_id_str:
        return {"response": "User ID is required for Google Drive operations."}

    user_id = int(user_id_str)
    
    logger.info(f"--- Handling Google Drive Interaction: action='{action}' ---")

    try:
        # Get Google Drive service for the user
        service = get_drive_service(user_id)
        if not service:
            return {"response": "Error: Could not connect to your Google Drive account. Please ensure you have connected Google Drive in your settings."}

        if action.lower() in ["search", "search files", "find files", "list files"]:
            # Search or list files
            query = details.get("query", "")
            max_results = int(details.get("count", 20))
            
            files = await list_drive_files(service, query=query, max_results=max_results)
            
            if not files:
                search_term = f" matching '{query}'" if query else ""
                return {"response": f"No files found{search_term} in your Google Drive."}
            
            # Format the file list
            file_summaries = []
            for file in files:
                size_mb = ""
                if file.get('size'):
                    size_bytes = int(file['size'])
                    size_mb = f" ({size_bytes / (1024*1024):.1f} MB)"
                
                summary = f"**{file['name']}**\n- Type: {file['mimeType']}\n- Modified: {file.get('modifiedTime', 'Unknown')}{size_mb}\n- Link: {file.get('webViewLink', 'N/A')}"
                file_summaries.append(summary)
            
            search_term = f" matching '{query}'" if query else ""
            response = f"Found {len(files)} files{search_term} in your Google Drive:\n\n" + "\n\n---\n\n".join(file_summaries)
            return {"response": response}

        elif action.lower() in ["download", "download file", "get content", "read file"]:
            # Download file content
            file_id = details.get("file_id", "")
            file_name = details.get("file_name", "")
            
            if not file_id and not file_name:
                return {"response": "Please provide either a file ID or file name to download."}
            
            # If we have a file name but no ID, search for it first
            if not file_id and file_name:
                files = await list_drive_files(service, query=file_name, max_results=5)
                matching_files = [f for f in files if file_name.lower() in f['name'].lower()]
                
                if not matching_files:
                    return {"response": f"No files found with name containing '{file_name}'."}
                elif len(matching_files) > 1:
                    # Multiple matches, show options
                    file_options = []
                    for i, file in enumerate(matching_files[:3], 1):
                        file_options.append(f"{i}. {file['name']} (Modified: {file.get('modifiedTime', 'Unknown')})")
                    
                    return {"response": f"Multiple files found with that name:\n\n" + "\n".join(file_options) + "\n\nPlease be more specific with the file name."}
                else:
                    file_id = matching_files[0]['id']
                    file_metadata = matching_files[0]
            else:
                # Get file metadata
                file_metadata = await get_file_metadata(service, file_id)
                if not file_metadata:
                    return {"response": f"File with ID '{file_id}' not found or not accessible."}
            
            # Download the content
            content = await download_file_content(service, file_id, file_metadata['mimeType'])
            
            if content is None:
                return {"response": f"Could not extract content from file '{file_metadata['name']}'. The file type may not be supported for content extraction."}
            
            # Limit content display
            if len(content) > 2000:
                content = content[:2000] + "...\n\n[Content truncated - showing first 2000 characters]"
            
            return {"response": f"**Content of '{file_metadata['name']}':**\n\n{content}"}

        elif action.lower() in ["import", "import document", "import for analysis"]:
            # Import document content for analysis/processing
            file_name = details.get("file_name", "")
            file_id = details.get("file_id", "")
            
            if not file_id and not file_name:
                return {"response": "Please provide either a file ID or file name to import."}
            
            # Find the file if we only have a name
            if not file_id and file_name:
                files = await list_drive_files(service, query=file_name, max_results=5)
                matching_files = [f for f in files if file_name.lower() in f['name'].lower()]
                
                if not matching_files:
                    return {"response": f"No files found with name containing '{file_name}'."}
                elif len(matching_files) > 1:
                    file_options = []
                    for i, file in enumerate(matching_files[:3], 1):
                        file_options.append(f"{i}. {file['name']}")
                    
                    return {"response": f"Multiple files found:\n\n" + "\n".join(file_options) + "\n\nPlease be more specific."}
                else:
                    file_id = matching_files[0]['id']
                    file_metadata = matching_files[0]
            else:
                file_metadata = await get_file_metadata(service, file_id)
            
            # Download and process content
            content = await download_file_content(service, file_id, file_metadata['mimeType'])
            
            if content is None:
                return {"response": f"Could not import '{file_metadata['name']}'. File type not supported for content extraction."}
            
            # Use LLM to summarize or analyze the content
            analysis_prompt = f"Please provide a brief summary and analysis of this document:\n\nDocument: {file_metadata['name']}\nContent:\n{content[:1500]}"
            
            analysis = await invoke_llm(messages=[
                {"role": "system", "content": "You are a helpful document analysis assistant. Provide clear, concise summaries and insights."},
                {"role": "user", "content": analysis_prompt}
            ], model_name=selected_model)
            
            return {"response": f"**Imported and analyzed '{file_metadata['name']}':**\n\n{analysis}"}

        elif action.lower() in ["search content", "search by content", "find in content"]:
            # Search files by content
            search_term = details.get("query", "")
            if not search_term:
                return {"response": "Please provide a search term to look for within file content."}
            
            max_results = int(details.get("count", 10))
            files = await search_files_by_content(service, search_term, max_results=max_results)
            
            if not files:
                return {"response": f"No files found containing '{search_term}' in their content."}
            
            # Format the results
            file_summaries = []
            for file in files:
                summary = f"**{file['name']}**\n- Type: {file['mimeType']}\n- Modified: {file.get('modifiedTime', 'Unknown')}\n- Link: {file.get('webViewLink', 'N/A')}"
                file_summaries.append(summary)
            
            response = f"Found {len(files)} files containing '{search_term}':\n\n" + "\n\n---\n\n".join(file_summaries)
            return {"response": response}

        else:
            return {"response": f"I don't understand the Google Drive action '{action}'. Available actions are: search files, download file, import document, search content."}

    except Exception as e:
        logger.error(f"An unexpected error occurred in handle_drive_interaction: {e}", exc_info=True)
        return {"response": "An unexpected error occurred while handling your Google Drive request."}

# --- Placeholder Functions ---

async def handle_home_assistant_interaction(state: GraphState) -> Dict[str, Any]:
    """
    Handles interactions with Home Assistant by translating natural language
    into service calls.
    """
    tool_output = state.tool_output or {}
    command = tool_output.get("command")
    settings = get_settings()
    selected_model = get_model_for_task(state, "initial_assessment")  # Use assessment model for parsing commands

    if not command:
        logger.warning("Home Assistant tool called without a command.")
        return {"response": "No command was provided for Home Assistant."}

    logger.info(f"--- Handling Home Assistant Interaction for command: '{command}' ---")

    try:
        # 1. Use LLM to extract structured service call details
        llm_response_str = await invoke_llm(messages=[
            {"role": "system", "content": SYSTEM_PROMPT_EXTRACT_HA_SERVICE_CALL},
            {"role": "user", "content": command}
        ], model_name=selected_model)

        # 2. Parse the JSON from the LLM response
        service_call_details = await extract_json_with_self_correction(llm_response_str, selected_model)
        if not service_call_details or not all(k in service_call_details for k in ["domain", "service", "entity_data"]):
            logger.error(f"LLM did not return valid JSON for HA service call. Response: {llm_response_str}")
            return {"response": f"I had trouble understanding the command '{command}'. Could you be more specific?"}

        # 3. Call the Home Assistant service and format the response
        result = await call_home_assistant_service(**service_call_details)
        if result.get("error"):
            return {"response": f"I couldn't complete the action. Home Assistant reported an error: {result['error']}"}
        return {"response": f"Successfully executed the command: '{command}'."}
    except Exception as e:
        logger.error(f"An unexpected error occurred in handle_home_assistant_interaction: {e}", exc_info=True)
        return {"response": "An unexpected error occurred while handling your Home Assistant request."}

async def handle_web_search(state: GraphState) -> Dict[str, Any]:
    """Performs a web search using the user's configured search provider and API key."""
    query = (state.tool_output or {}).get("query")
    if not query:
        logger.warning("Web search called without a query.")
        return {"response": "No search query was provided."}
    
    logger.info(f"--- Handling Web Search for query: '{query}' ---")
    
    # Get user from state
    user_id = state.user_id
    if not user_id:
        logger.warning("Web search called without user context.")
        return {"response": "Web search requires user authentication."}
    
    try:
        # Get user's web search configuration
        from shared.database.models import User
        from shared.utils.database_setup import get_db
        
        async with get_db() as db:
            user = await db.get(User, user_id)
            if not user:
                return {"response": "User not found."}
            
            # Check if user has web search configured
            if not user.web_search_provider or user.web_search_provider == "disabled":
                return {"response": "Web search is not configured. Please configure your search API settings in your profile."}
            
            if not user.web_search_api_key:
                return {"response": f"No API key configured for {user.web_search_provider}. Please add your API key in your profile settings."}
            
            # Use the appropriate search service based on user's preference
            if user.web_search_provider == "tavily":
                return await _search_with_tavily(query, user.web_search_api_key)
            elif user.web_search_provider == "serpapi":
                return await _search_with_serpapi(query, user.web_search_api_key)
            else:
                return {"response": f"Unsupported search provider: {user.web_search_provider}"}
                
    except Exception as e:
        logger.error(f"Error during web search for query '{query}': {e}", exc_info=True)
        return {"response": "An error occurred while performing the web search."}


async def _search_with_tavily(query: str, api_key: str) -> Dict[str, Any]:
    """Search using Tavily API with user's API key."""
    try:
        # Create TavilyClient with user's API key
        import os
        original_key = os.environ.get('TAVILY_API_KEY')
        os.environ['TAVILY_API_KEY'] = api_key
        
        tavily_client = TavilyClient()
        search_result = tavily_client.search(query=query, search_depth="basic")
        
        # Restore original key if it existed
        if original_key:
            os.environ['TAVILY_API_KEY'] = original_key
        else:
            os.environ.pop('TAVILY_API_KEY', None)
            
        return {"response": search_result.get("answer", "No direct answer found.")}
    except Exception as e:
        logger.error(f"Tavily search error: {e}")
        return {"response": f"Tavily search failed: {str(e)}"}


async def _search_with_serpapi(query: str, api_key: str) -> Dict[str, Any]:
    """Search using SerpApi with user's API key."""
    try:
        from worker.google_search_service import run_google_search
        from shared.utils.config import Settings
        
        # Create temporary settings with user's API key
        temp_settings = Settings()
        temp_settings.SERPAPI_KEY = api_key
        
        search_result = run_google_search(query, temp_settings)
        
        if "error" in search_result:
            return {"response": f"Search failed: {search_result['error']}"}
        
        # Format the results for better readability
        formatted_response = f"Search results for '{query}':\n\n"
        
        if "organic_results" in search_result:
            for i, result in enumerate(search_result["organic_results"][:3], 1):
                title = result.get("title", "No title")
                snippet = result.get("snippet", "No description")
                formatted_response += f"{i}. **{title}**\n   {snippet}\n\n"
        
        return {"response": formatted_response.strip()}
    except Exception as e:
        logger.error(f"SerpApi search error: {e}")
        return {"response": f"SerpApi search failed: {str(e)}"}


@smart_file_tool
async def handle_file_system_interaction(state: GraphState) -> Dict[str, Any]:
    """Handles file system operations (read, write, list) within a secure workspace."""
    tool_output = state.tool_output or {}
    action = tool_output.get("action")
    filename = tool_output.get("filename")
    content = tool_output.get("content")

    logger.info(f"--- Handling File System Interaction: action='{action}', filename='{filename}' ---")

    # Ensure the workspace directory exists
    os.makedirs(AGENT_WORKSPACE, exist_ok=True)

    if action == "list":
        try:
            files = os.listdir(AGENT_WORKSPACE)
            return {"response": f"Files in workspace: {', '.join(files) if files else 'None'}"}
        except Exception as e:
            logger.error(f"Error listing files in workspace: {e}", exc_info=True)
            return {"response": "Error: Could not list files in the workspace."}

    # For read/write, a filename is required and must be validated
    if not filename:
        return {"response": "Error: 'filename' is required for 'read' or 'write' actions."}

    # --- Security Check ---
    # Disallow directory traversal and absolute paths
    if "/" in filename or "\\" in filename or ".." in filename:
        logger.warning(f"Attempted file access with invalid path characters: '{filename}'")
        return {"response": "Error: Invalid filename. Only simple filenames are allowed (no paths)."}

    # Construct the full path and verify it's within the workspace
    full_path = os.path.abspath(os.path.join(AGENT_WORKSPACE, filename))
    if not full_path.startswith(os.path.abspath(AGENT_WORKSPACE)):
        logger.error(f"Path traversal attempt detected! Filename: '{filename}', Resolved Path: '{full_path}'")
        return {"response": "Error: Access denied. Path is outside the designated workspace."}

    if action == "read":
        try:
            if not os.path.exists(full_path):
                return {"response": f"Error: File '{filename}' not found."}
            with open(full_path, "r", encoding="utf-8") as f:
                file_content = f.read()
            return {"response": f"Content of '{filename}':\n\n{file_content}"}
        except Exception as e:
            logger.error(f"Error reading file '{filename}': {e}", exc_info=True)
            return {"response": f"Error: Could not read file '{filename}'."}

    elif action == "write":
        if content is None:
            return {"response": "Error: 'content' is required for the 'write' action."}
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"response": f"Successfully wrote to file '{filename}'."}
        except Exception as e:
            logger.error(f"Error writing to file '{filename}': {e}", exc_info=True)
            return {"response": f"Error: Could not write to file '{filename}'."}

    else:
        return {"response": f"Error: Unknown file system action '{action}'. Valid actions are 'read', 'write', 'list'."}

async def handle_reflective_coach_interaction(state: GraphState) -> Dict[str, Any]:
    """Handles interactions with the Reflective AI Coach tools."""
    tool_output = state.tool_output or {}
    sub_tool = tool_output.get("sub_tool")
    args = tool_output.get("args", {})
    
    logger.info(f"--- Handling Reflective Coach Interaction: sub_tool='{sub_tool}' ---")

    if sub_tool == "initiate_socratic_dialogue":
        return {"response": initiate_socratic_dialogue(**args)}
    elif sub_tool == "ask_clarifying_questions":
        return {"response": ask_clarifying_questions(**args)}
    elif sub_tool == "summarize_and_reflect":
        return {"response": summarize_and_reflect(**args)}
    elif sub_tool == "identify_themes_and_patterns":
        return {"response": identify_themes_and_patterns(**args)}
    elif sub_tool == "guide_goal_setting":
        return {"response": guide_goal_setting(**args)}
    elif sub_tool == "measure_progress":
        return {"response": measure_progress(**args)}
    elif sub_tool == "conclude_session":
        return {"response": conclude_session(**args)}
    else:
        return {"response": f"Error: Unknown reflective coach sub-tool '{sub_tool}'."}

@smart_task_tool
async def handle_task_management_interaction(state: GraphState) -> Dict[str, Any]:
    """Handles task management operations including creating, updating, and managing tasks."""
    tool_output = state.tool_output or {}
    action = tool_output.get("action", "")
    task_data = tool_output.get("task_data", {})
    user_id_str: str | None = state.user_id
    
    logger.info(f"--- Handling Task Management Interaction: action='{action}' ---")

    if not user_id_str:
        return {"response": "User ID is required for task management operations."}

    user_id = int(user_id_str)
    
    try:
        if action.lower() in ["create", "create task", "add task", "new task"]:
            # Create a new task using our tools
            title = task_data.get("title", "")
            description = task_data.get("description", "")
            priority = task_data.get("priority", "medium")
            due_date = task_data.get("due_date")
            tags = task_data.get("tags", [])
            
            if not title:
                return {"response": "Task title is required to create a new task."}
            
            result = create_task(title, description, priority, due_date, tags)
            return {"response": result["message"]}
                
        elif action.lower() in ["list", "list tasks", "show tasks", "get tasks"]:
            # List tasks using our tools
            status_filter = task_data.get("status")
            priority_filter = task_data.get("priority")
            tag_filter = task_data.get("tag")
            limit = int(task_data.get("limit", 10))
            
            result = get_task_list(status_filter, priority_filter, tag_filter, limit)
            
            if result["success"]:
                tasks = result["tasks"]
                if not tasks:
                    return {"response": "You have no tasks matching the specified criteria."}
                
                task_list = []
                for task in tasks:
                    task_summary = f"• **{task['title']}** (Status: {task['status']}, Priority: {task['priority']})"
                    if task.get('due_date'):
                        task_summary += f"\n  Due: {task['due_date']}"
                    if task.get('tags'):
                        task_summary += f"\n  Tags: {', '.join(task['tags'])}"
                    task_list.append(task_summary)
                
                response = f"Found {len(tasks)} tasks:\n\n" + "\n\n".join(task_list)
                return {"response": response}
            else:
                return {"response": result["message"]}

        elif action.lower() in ["update", "update status", "update task"]:
            # Update task status
            task_id = task_data.get("task_id", "")
            status = task_data.get("status", "")
            notes = task_data.get("notes", "")
            
            if not task_id or not status:
                return {"response": "Both task ID and new status are required to update a task."}
            
            result = update_task_status(task_id, status, notes)
            return {"response": result["message"]}

        elif action.lower() in ["prioritize", "prioritize tasks", "sort tasks"]:
            # Prioritize tasks
            result = get_task_list()
            
            if result["success"]:
                prioritized_result = prioritize_tasks(result["tasks"])
                
                if prioritized_result["success"]:
                    prioritized = prioritized_result["prioritized_tasks"][:10]  # Show top 10
                    task_list = []
                    for i, task in enumerate(prioritized, 1):
                        task_list.append(f"{i}. **{task['title']}** (Score: {task['priority_score']})\n   Status: {task['status']}, Priority: {task['priority']}")
                    
                    response = "**Prioritized Task List:**\n\n" + "\n\n".join(task_list)
                    return {"response": response}
                else:
                    return {"response": prioritized_result["message"]}
            else:
                return {"response": result["message"]}

        elif action.lower() in ["analytics", "task analytics", "task stats"]:
            # Get task analytics
            result = get_task_analytics()
            
            if result["success"]:
                analytics = result["analytics"]
                response = f"""**Task Analytics:**

**Overview:**
- Total tasks: {analytics['overview']['total_tasks']}
- Completed today: {analytics['overview']['completed_today']}
- In progress: {analytics['overview']['in_progress']}
- Overdue: {analytics['overview']['overdue']}
- Completion rate: {analytics['overview']['completion_rate']:.0%}

**By Priority:**
{chr(10).join([f"- {priority.title()}: {data['completed']}/{data['total']} completed" for priority, data in analytics['by_priority'].items()])}

**Productivity Insights:**
- Average completion time: {analytics['productivity_trends']['avg_completion_time']}
- Most productive day: {analytics['productivity_trends']['most_productive_day']}

**Upcoming Deadlines:**
{chr(10).join([f"- {item['title']} (Due: {item['due_date']}, Priority: {item['priority']})" for item in analytics['upcoming_deadlines']])}"""
                return {"response": response}
            else:
                return {"response": "Failed to retrieve task analytics."}

        elif action.lower() in ["template", "create template", "task template"]:
            # Create task template
            name = task_data.get("name", "")
            tasks = task_data.get("tasks", [])
            
            if not name or not tasks:
                return {"response": "Template name and task list are required to create a template."}
            
            result = create_task_template(name, tasks)
            return {"response": result["message"]}

        elif action.lower() in ["estimate", "estimate time", "time estimate"]:
            # Estimate task completion time
            task_id = task_data.get("task_id", "")
            similar_tasks = task_data.get("similar_tasks", [])
            
            if not task_id:
                return {"response": "Task ID is required for time estimation."}
            
            result = estimate_task_completion(task_id, similar_tasks)
            
            if result["success"]:
                response = f"**Time Estimate for Task {task_id}:**\n"
                if result["estimated_hours"]:
                    response += f"- Estimated time: {result['estimated_hours']} hours\n"
                    response += f"- Base estimate: {result['base_estimate']} hours\n"
                    response += f"- Confidence: {result['confidence']}\n"
                    response += f"- Based on {result['reference_tasks_count']} similar tasks"
                else:
                    response += result["estimation"]
                return {"response": response}
            else:
                return {"response": result["message"]}
                
        else:
            return {"response": f"I don't understand the task management action '{action}'. Available actions are: create task, list tasks, update status, prioritize tasks, task analytics, create template, estimate time."}
            
    except Exception as e:
        logger.error(f"An unexpected error occurred in handle_task_management_interaction: {e}", exc_info=True)
        return {"response": "An unexpected error occurred while handling your task management request."}

async def handle_user_profile_interaction(state: GraphState) -> Dict[str, Any]:
    """Handles interactions with the user profile tools."""
    tool_output = state.tool_output or {}
    sub_tool = tool_output.get("sub_tool")
    args = tool_output.get("args", {})
    
    logger.info(f"--- Handling User Profile Interaction: sub_tool='{sub_tool}' ---")

    try:
        if sub_tool == "update_calendar_weights_from_goals":
            # Get the user's goals and current weights from the provided arguments
            goals = args.get("goals", [])
            current_weights = args.get("current_weights", {})
            
            # Import the tool function
            from worker.user_profile_tools import update_calendar_weights_from_goals
            
            # Calculate updated weights based on goals
            updated_weights = update_calendar_weights_from_goals(goals, current_weights)
            
            # TODO: In a full implementation, save the updated_weights to the database
            # For now, return the calculated weights
            return {
                "response": f"Successfully updated calendar weights based on your goals. New weights: {updated_weights}",
                "updated_weights": updated_weights
            }
        
        elif sub_tool == "get_profile_summary":
            # Get profile data from arguments
            profile_data = args.get("profile_data", {})
            
            from worker.user_profile_tools import get_profile_summary
            
            summary = get_profile_summary(profile_data)
            
            return {
                "response": f"Here's your profile summary:\n\n{summary}",
                "profile_summary": summary
            }
        
        elif sub_tool == "extract_goals_from_profile":
            # Get profile data from arguments
            profile_data = args.get("profile_data", {})
            
            from worker.user_profile_tools import extract_goals_from_profile
            
            goals = extract_goals_from_profile(profile_data)
            
            return {
                "response": f"I've extracted the following goals from your profile: {', '.join(goals) if goals else 'No specific goals found'}",
                "extracted_goals": goals
            }
        
        elif sub_tool == "validate_profile_completeness":
            # Get profile data from arguments
            profile_data = args.get("profile_data", {})
            
            from worker.user_profile_tools import validate_profile_completeness
            
            validation_result = validate_profile_completeness(profile_data)
            
            response = f"Your profile is {validation_result['completeness_score']}% complete "
            response += f"({validation_result['completed_fields']}/{validation_result['total_fields']} fields)."
            
            if validation_result['suggestions']:
                response += "\n\nSuggestions for improvement:\n" + "\n".join(f"• {suggestion}" for suggestion in validation_result['suggestions'])
            
            return {
                "response": response,
                "validation_result": validation_result
            }
        
        else:
            return {"response": f"Error: Unknown user profile sub-tool '{sub_tool}'."}
    
    except Exception as e:
        logger.error(f"Error in handle_user_profile_interaction: {e}", exc_info=True)
        return {"response": f"An error occurred while processing your profile request: {str(e)}"}

async def handle_planner_interaction(state: GraphState) -> Dict[str, Any]:
    """
    Handles planning requests by breaking down complex tasks into steps.
    The actual plan is extracted by the planner_node in the graph service.
    """
    logger.info(f"--- Handling Planner Interaction for query: '{state.user_input}' ---")
    
    try:
        # Extract the plan from the tool_output (set by route_to_tool)
        tool_output = state.tool_output
        if not tool_output:
            return {"response": "No planning data available."}
        
        plan = tool_output.get("plan", [])
        
        if not plan:
            return {"response": "Unable to create a plan for your request."}
        
        plan_text = "I've created a plan for your request:\n\n"
        for i, step in enumerate(plan, 1):
            plan_text += f"{i}. {step}\n"
        
        return {"response": plan_text}
        
    except Exception as e:
        logger.error(f"An unexpected error occurred in handle_planner_interaction: {e}", exc_info=True)
        return {"response": "An error occurred while creating your plan. Please try again."}

async def handle_socratic_guidance(state: GraphState) -> Dict[str, Any]:
    """
    Handles Socratic guidance interactions to help users align with their mission statement.
    Uses gentle questioning to guide users toward mission-aligned decision-making.
    """
    tool_output = state.tool_output or {}
    user_request = tool_output.get("user_request") or state.user_input
    current_context = tool_output.get("current_context", "")
    
    logger.info(f"--- Handling Socratic Guidance for request: '{user_request}' ---")
    
    try:
        if not state.user_id:
            return {"response": "Error: User ID is missing for Socratic guidance."}
        
        # Use the Socratic guidance tool
        socratic_response, token_metrics = await socratic_guidance_tool.invoke(
            user_id=int(state.user_id),
            user_request=user_request,
            current_context=current_context,
            session_id=state.session_id
        )
        
        # Update state with token usage
        if hasattr(state, 'token_usage') and state.token_usage:
            state.token_usage.add_tokens(
                token_metrics.input_tokens,
                token_metrics.output_tokens,
                "socratic_guidance"
            )
        
        # Broadcast the interaction to the session
        await progress_manager.broadcast_to_session_sync(state.session_id, {
            "type": "socratic_guidance",
            "message": socratic_response,
            "context": current_context,
            "token_usage": {
                "input_tokens": token_metrics.input_tokens,
                "output_tokens": token_metrics.output_tokens,
                "total_tokens": token_metrics.total_tokens
            }
        })
        
        return {"response": socratic_response}
        
    except Exception as e:
        logger.error(f"An unexpected error occurred in handle_socratic_guidance: {e}", exc_info=True)
        return {"response": "I'd like to help you think through this decision. Can you tell me more about what's most important to you here?"}

async def handle_general_analysis(user_input: str, user_id: int, session_id: str) -> AsyncGenerator[str, None]:
    """
    General-purpose analysis tool using AI reasoning.
    Handles complex analysis, decision-making, and problem-solving tasks.
    """
    try:
        analysis_prompt = f"""You are an AI analysis expert. Analyze the following request and provide comprehensive insights:

        Request: {user_input}

        Provide:
        1. Key aspects to consider
        2. Analysis of the situation/problem
        3. Insights and conclusions  
        4. Recommendations or next steps

        Be thorough but concise, and structure your response clearly."""

        messages = [{"role": "user", "content": analysis_prompt}]
        
        async for chunk in invoke_llm_stream(messages, "llama3.2:3b"):
            yield chunk
            
    except Exception as e:
        logger.error(f"Error in general analysis: {e}")
        yield f"I encountered an error while analyzing your request: {str(e)}"


async def handle_multi_step_planning(user_input: str, user_id: int, session_id: str) -> AsyncGenerator[str, None]:
    """Multi-step planning tool for complex workflows and projects."""
    try:
        planning_prompt = f"""You are an expert project planner. Create a detailed multi-step plan for: {user_input}

        Create a structured plan with:
        1. Overview of the goal
        2. Step-by-step breakdown
        3. Dependencies between steps
        4. Estimated timeframes
        5. Resources needed
        6. Potential challenges and mitigation strategies

        Make the plan actionable and specific."""

        messages = [{"role": "user", "content": planning_prompt}]
        
        async for chunk in invoke_llm_stream(messages, "llama3.2:3b"):
            yield chunk
            
    except Exception as e:
        logger.error(f"Error in multi-step planning: {e}")  
        yield f"I encountered an error while creating your plan: {str(e)}"


async def handle_research_synthesis(user_input: str, user_id: int, session_id: str) -> AsyncGenerator[str, None]:
    """Research and synthesis tool for comprehensive information gathering."""
    try:
        synthesis_prompt = f"""You are a research analyst. Provide a comprehensive analysis of: {user_input}

        Include:
        1. Key aspects and considerations
        2. Different perspectives or viewpoints
        3. Analysis of trends or patterns
        4. Important implications
        5. Conclusions and recommendations

        Structure your synthesis clearly and be thorough."""

        messages = [{"role": "user", "content": synthesis_prompt}]
        
        async for chunk in invoke_llm_stream(messages, "llama3.2:3b"):
            yield chunk
            
    except Exception as e:
        logger.error(f"Error in research synthesis: {e}")
        yield f"I encountered an error while researching this topic: {str(e)}"


async def handle_creative_assistance(user_input: str, user_id: int, session_id: str) -> AsyncGenerator[str, None]:
    """Creative assistance tool for writing, brainstorming, and content creation."""
    try:
        creative_prompt = f"""You are a creative writing and ideation assistant. Help with: {user_input}

        Provide creative assistance by:
        1. Understanding the creative goal
        2. Generating relevant ideas or content
        3. Offering multiple creative approaches
        4. Providing specific examples or drafts
        5. Suggesting refinements or improvements

        Be imaginative, original, and helpful while maintaining quality."""

        messages = [{"role": "user", "content": creative_prompt}]
        
        async for chunk in invoke_llm_stream(messages, "llama3.2:3b"):
            yield chunk
            
    except Exception as e:
        logger.error(f"Error in creative assistance: {e}")
        yield f"I encountered an error while helping with your creative request: {str(e)}"


async def handle_helios_delegation(user_input: str, user_id: int, session_id: str) -> AsyncGenerator[str, None]:
    """
    Delegate complex tasks to the 12-specialist Helios expert team.
    
    This handler creates a structured task assignment event for the Helios blackboard
    and initiates the multi-agent collaborative workflow.
    """
    try:
        from shared.services.helios_delegation_service import HeliosDelegationService
        
        delegation_service = HeliosDelegationService()
        
        yield "🚀 Delegating your request to the Helios expert team...\n"
        yield "📋 Analyzing task complexity and selecting appropriate specialists...\n"
        
        # Delegate to Helios team and get real-time updates
        async for update in delegation_service.delegate_task(
            user_request=user_input,
            user_id=user_id,
            session_id=session_id
        ):
            yield update
            
    except ImportError:
        logger.error("Helios delegation service not available")
        yield "⚠️ Helios expert team delegation is not currently available. The service may still be initializing or requires system updates."
    except Exception as e:
        logger.error(f"Error in Helios delegation: {e}")
        yield f"❌ Error occurred while delegating to Helios team: {str(e)}"


# --- Tool Handler Mapping ---
TOOL_HANDLER_MAP = {
    constants.CALENDAR_TOOL_ID: handle_calendar_interaction,  # Consolidated calendar handler
    constants.DOCUMENT_QA_TOOL_ID: handle_document_qa,
    constants.HOME_ASSISTANT_TOOL_ID: handle_home_assistant_interaction,
    constants.EMAIL_TOOL_ID: handle_email_interaction,
    constants.DRIVE_TOOL_ID: handle_drive_interaction,
    constants.WEB_SEARCH_TOOL_ID: handle_web_search,
    constants.UNSTRUCTURED_TOOL_ID: handle_unstructured_interaction,
    constants.FILE_SYSTEM_TOOL_ID: handle_file_system_interaction,
    constants.TASK_MANAGEMENT_TOOL_ID: handle_task_management_interaction,
    constants.SOCRATIC_GUIDANCE_TOOL_ID: handle_socratic_guidance,
    # "reflective_coach_tool": handle_reflective_coach_interaction,
    "user_profile_tool": handle_user_profile_interaction,
    constants.PLANNER_TOOL_ID: handle_planner_interaction,
    "list_parser_tool": handle_list_parsing_request,
    "user_input_tool": handle_user_input_request,
    "llm_calendar_parser_tool": handle_llm_calendar_parsing,
    "general_analysis_tool": handle_general_analysis,
    "multi_step_planner_tool": handle_multi_step_planning,
    "research_synthesis_tool": handle_research_synthesis,
    "creative_assistance_tool": handle_creative_assistance,
    "delegate_to_helios_team": handle_helios_delegation,
}

def get_tool_handler(tool_id: str) -> Optional[Callable[[GraphState], Awaitable[Dict[str, Any]]]]:
    """Retrieves a handler function from the map by its name."""
    # Use the 'tool_id' parameter that was passed into the function
    return TOOL_HANDLER_MAP.get(tool_id)
