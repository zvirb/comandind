# worker/services/smart_router_service.py
"""
Smart Router Service - Simplified routing system based on smart_ai.txt principles.
Replaces the complex wave function system with streamlined decision making.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from worker.graph_types import GraphState
from worker.services.router_modules.router_core import run_router_graph
from worker.services.ollama_service import invoke_llm_with_tokens
from worker.tool_registry import AVAILABLE_TOOLS
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SmartRouterService:
    """
    Simplified smart routing service that replaces the wave function approach.
    Uses fast heuristics and targeted LLM calls for optimal performance.
    """
    
    def __init__(self):
        self.routing_stats = {
            "total_requests": 0,
            "direct_routes": 0,
            "planning_routes": 0,
            "average_response_time": 0.0
        }
    
    async def process_request(
        self, 
        user_input: str, 
        user_id: int, 
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process user request using simplified smart routing.
        """
        start_time = datetime.now()
        
        try:
            # Get tools from internal registry
            tools = AVAILABLE_TOOLS
            logger.info(f"Got {len(tools)} tools from internal registry.")

            # Convert user input to message format
            messages = [HumanMessage(content=user_input)]
            
            # Add any context messages if provided
            if context and context.get("conversation_history"):
                for msg in context["conversation_history"]:
                    if msg.get("role") == "user":
                        messages.insert(-1, HumanMessage(content=msg["content"]))
                    elif msg.get("role") == "assistant":
                        messages.insert(-1, AIMessage(content=msg["content"]))
            
            # Use the simplified router graph
            result = await run_router_graph(
                user_input=user_input,
                messages=messages,
                user_id=user_id,
                session_id=session_id or f"session_{datetime.now().timestamp()}",
                chat_model="llama3.2:3b"
            )
            
            # Update routing stats
            self._update_stats(result, start_time)
            
            return {
                "response": result["response"],
                "routing_decision": result.get("routing_decision", "DIRECT"),
                "confidence_score": result.get("confidence_score", 0.8),
                "processing_time": (datetime.now() - start_time).total_seconds(),
                "metadata": {
                    **result.get("metadata", {}),
                    "service": "smart_router",
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error in smart router service: {e}", exc_info=True)
            
            # Fallback to simple LLM response
            fallback_response = await self._fallback_response(user_input)
            
            return {
                "response": fallback_response,
                "routing_decision": "FALLBACK",
                "confidence_score": 0.3,
                "processing_time": (datetime.now() - start_time).total_seconds(),
                "metadata": {
                    "service": "smart_router",
                    "error": str(e),
                    "fallback": True,
                    "timestamp": datetime.now().isoformat()
                }
            }
    
    async def _fallback_response(self, user_input: str) -> str:
        """
        Provide a simple fallback response when routing fails.
        """
        try:
            response, _ = await invoke_llm_with_tokens(
                model="llama3.2:3b",
                messages=[{"role": "user", "content": user_input}],
                temperature=0.7
            )
            return response
        except Exception as e:
            logger.error(f"Fallback response failed: {e}")
            return "I'm having trouble processing your request right now. Could you try rephrasing it?"
    
    def _update_stats(self, result: Dict[str, Any], start_time: datetime):
        """
        Update routing statistics for monitoring and optimization.
        """
        self.routing_stats["total_requests"] += 1
        
        routing_decision = result.get("routing_decision", "DIRECT")
        if routing_decision == "DIRECT":
            self.routing_stats["direct_routes"] += 1
        elif routing_decision == "PLANNING":
            self.routing_stats["planning_routes"] += 1
        
        # Update average response time
        processing_time = (datetime.now() - start_time).total_seconds()
        total = self.routing_stats["total_requests"]
        current_avg = self.routing_stats["average_response_time"]
        self.routing_stats["average_response_time"] = (
            (current_avg * (total - 1) + processing_time) / total
        )
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """
        Get current routing statistics for monitoring.
        """
        return {
            **self.routing_stats,
            "direct_percentage": (
                self.routing_stats["direct_routes"] / 
                max(1, self.routing_stats["total_requests"]) * 100
            ),
            "planning_percentage": (
                self.routing_stats["planning_routes"] / 
                max(1, self.routing_stats["total_requests"]) * 100
            )
        }
    
    async def analyze_conversation_context(
        self, 
        messages: List[Dict[str, Any]], 
        max_context_length: int = 15
    ) -> Dict[str, Any]:
        """
        Analyze conversation context for better routing decisions.
        Simplified version that doesn't require heavy computation.
        """
        if not messages:
            return {"context_summary": "", "user_intent": "unknown", "complexity": "low"}
        
        # Take recent messages for context
        recent_messages = messages[-max_context_length:]
        
        # Simple pattern matching for intent
        latest_message = messages[-1].get("content", "").lower()
        
        intent_patterns = {
            "question": ["what", "how", "when", "where", "why", "who", "?"],
            "request": ["please", "can you", "could you", "help", "do"],
            "command": ["create", "make", "build", "generate", "write"],
            "search": ["find", "search", "look for", "locate"]
        }
        
        detected_intent = "general"
        for intent, patterns in intent_patterns.items():
            if any(pattern in latest_message for pattern in patterns):
                detected_intent = intent
                break
        
        # Simple complexity assessment
        word_count = len(latest_message.split())
        complexity = "high" if word_count > 30 else "medium" if word_count > 10 else "low"
        
        return {
            "context_summary": f"Conversation with {len(recent_messages)} recent messages",
            "user_intent": detected_intent,
            "complexity": complexity,
            "message_count": len(messages),
            "latest_message_length": word_count
        }


# Global instance for reuse
smart_router_service = SmartRouterService()