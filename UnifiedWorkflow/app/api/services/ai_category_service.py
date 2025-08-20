"""
AI Category Service for generating intelligent category suggestions with colors and emojis.
"""

import logging
import json
import re
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


class AICategoryService:
    """Service for generating AI-powered category suggestions with colors and emojis."""
    
    def __init__(self):
        self.settings = get_settings()
        
    async def generate_category_suggestions(
        self,
        user_profile: Dict[str, Any],
        existing_categories: List[Dict[str, Any]],
        user_id: int
    ) -> List[Dict[str, Any]]:
        """
        Generate AI-powered category suggestions based on user profile.
        
        Args:
            user_profile: User's profile data (mission, work style, etc.)
            existing_categories: Current user categories
            user_id: User ID for context
            
        Returns:
            List of category suggestions with AI-generated colors and emojis
        """
        try:
            # Build context for AI analysis
            context = self._build_user_context(user_profile, existing_categories)
            
            # Create suggestion prompt
            suggestion_prompt = self._create_suggestion_prompt(context)
            
            # Get AI response
            ai_response = await self._invoke_llm(
                prompt=suggestion_prompt,
                model=self.settings.chat_model
            )
            
            # Parse AI response
            suggestions = self._parse_ai_suggestions(ai_response)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error generating category suggestions: {e}")
            return self._get_fallback_suggestions(existing_categories)
    
    async def assign_color_and_emoji(
        self,
        category_name: str,
        category_type: str,
        description: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Generate appropriate color and emoji for a category.
        
        Args:
            category_name: Name of the category
            category_type: Type of category (event, opportunity, both)
            description: Description of the category
            user_context: Additional user context
            
        Returns:
            Dict with color and emoji assignments
        """
        try:
            # Create color/emoji assignment prompt
            assignment_prompt = self._create_color_emoji_prompt(
                category_name, category_type, description, user_context
            )
            
            # Get AI response
            ai_response = await self._invoke_llm(
                prompt=assignment_prompt,
                model=self.settings.chat_model
            )
            
            # Parse AI response
            assignment = self._parse_color_emoji_response(ai_response)
            
            return assignment
            
        except Exception as e:
            logger.error(f"Error assigning color and emoji: {e}")
            return self._get_fallback_color_emoji(category_name, category_type)
    
    def _build_user_context(
        self,
        user_profile: Dict[str, Any],
        existing_categories: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build context for AI analysis."""
        
        # Extract mission statement components
        mission_statement = user_profile.get("missionStatement", {})
        work_style = user_profile.get("workStyle", {})
        productivity_patterns = user_profile.get("productivityPatterns", {})
        
        # Extract existing category names
        existing_names = [cat.get("name", "") for cat in existing_categories]
        
        return {
            "mission": mission_statement,
            "work_style": work_style,
            "productivity": productivity_patterns,
            "existing_categories": existing_names,
            "category_count": len(existing_categories)
        }
    
    def _create_suggestion_prompt(self, context: Dict[str, Any]) -> str:
        """Create prompt for generating category suggestions."""
        
        existing_categories_text = ", ".join(context["existing_categories"])
        
        prompt = f"""
You are an AI assistant helping to create personalized category suggestions for a user's task and event management system.

User Context:
- Mission Statement: {context.get('mission', 'Not provided')}
- Work Style: {context.get('work_style', 'Not provided')}
- Productivity Patterns: {context.get('productivity', 'Not provided')}
- Existing Categories: {existing_categories_text}

Based on this user profile, suggest 2-3 new categories that would be valuable for their productivity system. Each category should:
1. Align with their mission and work style
2. Not duplicate existing categories
3. Be actionable and meaningful
4. Have an appropriate color (hex code) and emoji

For colors, use this psychology:
- Blue (#3b82f6, #0ea5e9): Professional, trustworthy, productive
- Green (#10b981, #84cc16): Growth, health, nature, success
- Purple (#8b5cf6, #a855f7): Creative, innovative, strategic
- Red (#ef4444, #dc2626): Urgent, important, energy
- Orange (#f97316, #fb923c): Enthusiasm, creativity, social
- Yellow (#fbbf24, #eab308): Optimism, learning, attention
- Pink (#ec4899, #f472b6): Personal, emotional, relationships
- Cyan (#06b6d4, #0891b2): Communication, clarity, technology

For emojis, choose ones that are:
- Relevant to the category purpose
- Visually distinctive
- Universally recognizable
- Professional appropriate

Respond in JSON format:
{{
  "suggestions": [
    {{
      "id": "ai-suggestion-1",
      "action": "create",
      "category": {{
        "name": "Category Name",
        "type": "both|event|opportunity",
        "color": "#hexcode",
        "emoji": "🌟",
        "priority": 1-5,
        "description": "Clear description of what this category is for",
        "weights": {{
          "importance": 0.0-1.0,
          "urgency": 0.0-1.0,
          "complexity": 0.0-1.0
        }}
      }},
      "reasoning": "Explain why this category would be valuable for this user"
    }}
  ]
}}

Focus on categories that would genuinely improve their productivity and align with their personal goals.
"""
        
        return prompt
    
    def _create_color_emoji_prompt(
        self,
        category_name: str,
        category_type: str,
        description: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create prompt for color and emoji assignment."""
        
        context_text = ""
        if user_context:
            context_text = f"User Context: {user_context}"
        
        prompt = f"""
You are an AI assistant helping to assign appropriate colors and emojis to a category.

Category Details:
- Name: {category_name}
- Type: {category_type}
- Description: {description}
{context_text}

Choose an appropriate color (hex code) and emoji based on:

Color Psychology:
- Blue: Professional, productive, trustworthy
- Green: Growth, health, success, nature
- Purple: Creative, strategic, innovative
- Red: Urgent, important, high energy
- Orange: Enthusiasm, social, creative
- Yellow: Learning, optimism, attention
- Pink: Personal, emotional, relationships
- Cyan: Communication, technology, clarity

Emoji Guidelines:
- Should be relevant to the category purpose
- Visually distinctive and recognizable
- Professional appropriate
- Single emoji only

Respond in JSON format:
{{
  "color": "#hexcode",
  "emoji": "🌟",
  "reasoning": "Brief explanation of why this color and emoji fit the category"
}}
"""
        
        return prompt
    
    def _parse_ai_suggestions(self, ai_response: str) -> List[Dict[str, Any]]:
        """Parse AI response to extract category suggestions."""
        
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                return parsed.get("suggestions", [])
        except json.JSONDecodeError:
            pass
        
        # Fallback parsing - extract key information
        return self._extract_fallback_suggestions(ai_response)
    
    def _parse_color_emoji_response(self, ai_response: str) -> Dict[str, str]:
        """Parse AI response to extract color and emoji assignment."""
        
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                return {
                    "color": parsed.get("color", "#6b7280"),
                    "emoji": parsed.get("emoji", "📋"),
                    "reasoning": parsed.get("reasoning", "AI-generated assignment")
                }
        except json.JSONDecodeError:
            pass
        
        # Fallback parsing
        color_match = re.search(r'#[0-9a-fA-F]{6}', ai_response)
        emoji_match = re.search(r'[🌟🎯💼🏠🏥📚👥⚡🚀💡🔥🎨🌱⭐🏆🎪🌊🔧🎭🌙☀️🌈]', ai_response)
        
        return {
            "color": color_match.group() if color_match else "#6b7280",
            "emoji": emoji_match.group() if emoji_match else "📋",
            "reasoning": "Extracted from AI response"
        }
    
    def _extract_fallback_suggestions(self, ai_response: str) -> List[Dict[str, Any]]:
        """Extract suggestions from unstructured AI response."""
        
        # This would implement more sophisticated parsing
        # For now, return empty list
        return []
    
    def _get_fallback_suggestions(self, existing_categories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get fallback suggestions when AI fails."""
        
        existing_names = [cat.get("name", "").lower() for cat in existing_categories]
        
        fallback_suggestions = []
        
        # Common productive categories
        common_categories = [
            {
                "name": "Deep Work",
                "type": "both",
                "color": "#8b5cf6",
                "emoji": "🧠",
                "priority": 5,
                "description": "Focused, high-concentration work sessions",
                "weights": {"importance": 0.9, "urgency": 0.6, "complexity": 0.8}
            },
            {
                "name": "Quick Wins",
                "type": "both",
                "color": "#10b981",
                "emoji": "⚡",
                "priority": 4,
                "description": "Small tasks that provide immediate value",
                "weights": {"importance": 0.6, "urgency": 0.9, "complexity": 0.3}
            },
            {
                "name": "Creative Projects",
                "type": "both",
                "color": "#f97316",
                "emoji": "🎨",
                "priority": 3,
                "description": "Creative and innovative work",
                "weights": {"importance": 0.7, "urgency": 0.4, "complexity": 0.9}
            }
        ]
        
        for cat in common_categories:
            if cat["name"].lower() not in existing_names:
                fallback_suggestions.append({
                    "id": f"fallback-{len(fallback_suggestions) + 1}",
                    "action": "create",
                    "category": cat,
                    "reasoning": "Commonly useful category for productivity"
                })
        
        return fallback_suggestions[:2]  # Return max 2 suggestions
    
    def _get_fallback_color_emoji(self, category_name: str, category_type: str) -> Dict[str, str]:
        """Get fallback color and emoji assignments."""
        
        # Simple keyword-based assignment
        name_lower = category_name.lower()
        
        if any(word in name_lower for word in ["work", "business", "professional"]):
            return {"color": "#3b82f6", "emoji": "💼", "reasoning": "Work-related category"}
        elif any(word in name_lower for word in ["health", "fitness", "wellness"]):
            return {"color": "#ef4444", "emoji": "🏥", "reasoning": "Health-related category"}
        elif any(word in name_lower for word in ["learning", "study", "education"]):
            return {"color": "#8b5cf6", "emoji": "📚", "reasoning": "Learning-related category"}
        elif any(word in name_lower for word in ["social", "family", "friends"]):
            return {"color": "#f59e0b", "emoji": "👥", "reasoning": "Social-related category"}
        elif any(word in name_lower for word in ["creative", "art", "design"]):
            return {"color": "#f97316", "emoji": "🎨", "reasoning": "Creative-related category"}
        elif any(word in name_lower for word in ["urgent", "emergency", "critical"]):
            return {"color": "#dc2626", "emoji": "🚨", "reasoning": "Urgent-related category"}
        else:
            return {"color": "#6b7280", "emoji": "📋", "reasoning": "Default assignment"}
    
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