"""
AI Event Analysis Service for intelligent event creation and management.
"""

import logging
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from shared.utils.config import get_settings
try:
    from worker.services.ollama_service import invoke_llm_stream
except ImportError:
    # Fallback for when tiktoken is not available (e.g., in API container)
    async def invoke_llm_stream(messages, model_name, **kwargs):
        # Simple fallback implementation
        import httpx
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://ollama:11434/api/chat",
                json={
                    "model": model_name,
                    "messages": messages,
                    "stream": True
                }
            )
            
            if response.status_code == 200:
                async for line in response.aiter_lines():
                    if line.strip():
                        import json
                        try:
                            data = json.loads(line)
                            if "message" in data:
                                yield data["message"].get("content", "")
                        except json.JSONDecodeError:
                            continue
            else:
                yield "Error: Unable to process request"

logger = logging.getLogger(__name__)


class AIEventAnalysisService:
    """Service for analyzing event conversations with AI."""
    
    def __init__(self):
        self.settings = get_settings()
        
    async def analyze_conversation(
        self,
        conversation: List[Dict[str, Any]],
        time_slot: Dict[str, str],
        user_categories: List[Dict[str, Any]],
        user_id: int
    ) -> Dict[str, Any]:
        """
        Analyze conversation to extract event details or ask follow-up questions.
        
        Args:
            conversation: List of conversation messages
            time_slot: Dictionary with start and end times
            user_categories: List of user's available categories
            user_id: User ID for context
            
        Returns:
            Dict with analysis results including whether more info is needed
        """
        try:
            # Extract user messages from conversation
            user_messages = [msg for msg in conversation if msg["role"] == "user"]
            
            if not user_messages:
                return {
                    "needs_more_info": True,
                    "question": "What kind of event would you like to create?"
                }
            
            # Get the latest user message
            latest_message = user_messages[-1]["content"]
            
            # Build context for AI analysis
            context = self._build_analysis_context(
                conversation=conversation,
                time_slot=time_slot,
                categories=user_categories
            )
            
            # Create analysis prompt
            analysis_prompt = self._create_analysis_prompt(
                context=context,
                latest_message=latest_message,
                conversation_length=len(user_messages)
            )
            
            # Get AI response
            ai_response = await self._invoke_llm(
                prompt=analysis_prompt,
                model=self.settings.chat_model
            )
            
            # Parse AI response
            analysis_result = self._parse_ai_response(ai_response)
            
            # If we have enough information, generate event details
            if not analysis_result.get("needs_more_info", True):
                event_details = await self._generate_event_details(
                    conversation=conversation,
                    time_slot=time_slot,
                    categories=user_categories,
                    analysis_result=analysis_result
                )
                
                return {
                    "needs_more_info": False,
                    "event_details": event_details
                }
            else:
                return {
                    "needs_more_info": True,
                    "question": analysis_result.get("question", "Could you tell me more about your event?")
                }
                
        except Exception as e:
            logger.error(f"Error in AI event analysis: {e}")
            return {
                "needs_more_info": True,
                "question": "I encountered an error analyzing your request. Could you please describe your event in more detail?"
            }
    
    def _build_analysis_context(
        self,
        conversation: List[Dict[str, Any]],
        time_slot: Dict[str, str],
        categories: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build context for AI analysis."""
        
        # Format time slot
        start_time = datetime.fromisoformat(time_slot["start"].replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(time_slot["end"].replace('Z', '+00:00'))
        
        # Extract category names and descriptions
        category_info = []
        for cat in categories:
            category_info.append({
                "name": cat["name"],
                "description": cat.get("description", ""),
                "emoji": cat.get("emoji", ""),
                "type": cat.get("type", "both")
            })
        
        return {
            "time_slot": {
                "start": start_time.strftime("%Y-%m-%d %H:%M"),
                "end": end_time.strftime("%Y-%m-%d %H:%M"),
                "duration_minutes": int((end_time - start_time).total_seconds() / 60)
            },
            "categories": category_info,
            "conversation_history": conversation
        }
    
    def _create_analysis_prompt(
        self,
        context: Dict[str, Any],
        latest_message: str,
        conversation_length: int
    ) -> str:
        """Create prompt for AI analysis."""
        
        categories_text = "\n".join([
            f"- {cat['name']} ({cat['emoji']}): {cat['description']}"
            for cat in context["categories"]
        ])
        
        prompt = f"""
You are an AI assistant helping to create a calendar event. A user wants to create an event from {context['time_slot']['start']} to {context['time_slot']['end']} (duration: {context['time_slot']['duration_minutes']} minutes).

Available categories:
{categories_text}

Latest user message: "{latest_message}"

Conversation so far has {conversation_length} user messages.

Your task is to determine if you have enough information to create the event, or if you need to ask a follow-up question.

You have ENOUGH information if you can determine:
1. A clear event title/name
2. The general nature of the event (meeting, appointment, etc.)
3. A reasonable category match

You need MORE information if:
1. The user's message is too vague or unclear
2. You can't determine what type of event this is
3. You need specific details like attendees, location, or agenda

Respond in JSON format:
{{
    "needs_more_info": true/false,
    "question": "Your follow-up question if more info needed",
    "preliminary_category": "suggested category name if enough info",
    "confidence": "high/medium/low"
}}

Be conversational and helpful in your questions. Ask for one specific piece of information at a time.
"""
        
        return prompt
    
    def _parse_ai_response(self, ai_response: str) -> Dict[str, Any]:
        """Parse AI response and extract structured data."""
        
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
        
        # Fallback parsing
        if "enough" in ai_response.lower() or "sufficient" in ai_response.lower():
            return {
                "needs_more_info": False,
                "confidence": "medium"
            }
        else:
            return {
                "needs_more_info": True,
                "question": "Could you provide more details about your event?"
            }
    
    async def _generate_event_details(
        self,
        conversation: List[Dict[str, Any]],
        time_slot: Dict[str, str],
        categories: List[Dict[str, Any]],
        analysis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate detailed event information."""
        
        # Extract all user messages
        user_messages = [msg["content"] for msg in conversation if msg["role"] == "user"]
        combined_input = " ".join(user_messages)
        
        # Build categories context
        categories_context = {}
        for cat in categories:
            categories_context[cat["name"]] = cat["id"]
        
        # Create event generation prompt
        generation_prompt = f"""
Based on the conversation, create detailed event information.

User input: {combined_input}
Time slot: {time_slot['start']} to {time_slot['end']}
Available categories: {list(categories_context.keys())}

Generate event details in JSON format:
{{
    "title": "Clear, concise event title",
    "description": "Detailed description based on conversation",
    "category": "Most appropriate category from available list",
    "location": "Event location if mentioned or can be inferred",
    "attendees": ["List of attendees if mentioned"],
    "priority": 1-5 (1=low, 5=critical),
    "aiReasoning": {{
        "title": "Why this title was chosen",
        "description": "How description was generated",
        "category": "Why this category was selected",
        "location": "How location was determined",
        "attendees": "How attendees were identified"
    }}
}}

Make reasonable inferences but don't make up specific details that weren't mentioned.
"""
        
        try:
            ai_response = await self._invoke_llm(
                prompt=generation_prompt,
                model=self.settings.chat_model
            )
            
            # Parse response
            event_details = self._parse_event_details(ai_response)
            
            # Map category name to ID
            if event_details.get("category") in categories_context:
                event_details["category"] = categories_context[event_details["category"]]
            
            return event_details
            
        except Exception as e:
            logger.error(f"Error generating event details: {e}")
            
            # Return fallback event details
            return {
                "title": self._extract_basic_title(combined_input),
                "description": combined_input,
                "category": categories[0]["id"] if categories else None,
                "location": "",
                "attendees": [],
                "priority": 3,
                "aiReasoning": {
                    "title": "Extracted from user input",
                    "description": "Used full user description",
                    "category": "Selected first available category",
                    "location": "Not specified",
                    "attendees": "Not specified"
                }
            }
    
    def _parse_event_details(self, ai_response: str) -> Dict[str, Any]:
        """Parse AI response to extract event details."""
        
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                
                # Validate required fields
                if "title" not in parsed:
                    parsed["title"] = "New Event"
                if "priority" not in parsed:
                    parsed["priority"] = 3
                    
                return parsed
        except json.JSONDecodeError:
            pass
        
        # Fallback parsing
        return {
            "title": "New Event",
            "description": ai_response,
            "category": None,
            "location": "",
            "attendees": [],
            "priority": 3,
            "aiReasoning": {
                "title": "Fallback title",
                "description": "Used AI response as description",
                "category": "No category selected",
                "location": "Not specified",
                "attendees": "Not specified"
            }
        }
    
    def _extract_basic_title(self, text: str) -> str:
        """Extract a basic title from text."""
        
        # Simple title extraction
        words = text.split()
        if len(words) <= 5:
            return text.title()
        else:
            return " ".join(words[:5]).title() + "..."
    
    async def _invoke_llm(self, prompt: str, model: str) -> str:
        """Invoke the LLM and return the complete response."""
        try:
            # Format messages for Ollama
            messages = [{"role": "user", "content": prompt}]
            
            # Stream the response and collect it
            response_parts = []
            async for chunk in invoke_llm_stream(messages, model):
                response_parts.append(chunk)
            
            return "".join(response_parts)
            
        except Exception as e:
            logger.error(f"Error invoking LLM: {e}")
            return f"Error: {str(e)}"