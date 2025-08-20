"""
Service for integrating with the Memory Service for enhanced context
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
import aiohttp
import json

from ..config import get_settings
from ..models import MemoryIntegrationRequest

logger = logging.getLogger(__name__)
settings = get_settings()


class MemoryIntegrationService:
    """
    Service for integrating with the hybrid memory & knowledge graph microservice
    """
    
    def __init__(self):
        self.memory_service_url = settings.MEMORY_SERVICE_URL
        self._session: Optional[aiohttp.ClientSession] = None
        self._auth_token: Optional[str] = None
        
    async def initialize(self, auth_token: Optional[str] = None) -> None:
        """Initialize HTTP session for memory service communication"""
        try:
            self._auth_token = auth_token
            
            # Create HTTP session
            headers = {"Content-Type": "application/json"}
            if self._auth_token:
                headers["Authorization"] = f"Bearer {self._auth_token}"
            
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            )
            
            # Test connection to memory service
            await self._test_connection()
            
            logger.info("Memory integration service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize memory integration service: {e}")
            raise
    
    async def _test_connection(self) -> None:
        """Test connection to memory service"""
        try:
            async with self._session.get(f"{self.memory_service_url}/health") as response:
                if response.status != 200:
                    raise RuntimeError(f"Memory service health check failed: {response.status}")
                
                data = await response.json()
                if data.get("status") != "healthy":
                    raise RuntimeError("Memory service is not healthy")
                    
        except Exception as e:
            logger.warning(f"Memory service connection test failed: {e}")
            # Don't raise here - service should work without memory integration
    
    async def get_relevant_context(
        self, 
        query: str, 
        user_id: Optional[str] = None,
        context_limit: int = 3,
        similarity_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        Get relevant context from memory service using hybrid search
        
        Args:
            query: The reasoning query to find context for
            user_id: User identifier for personalized context
            context_limit: Maximum number of context items to return
            similarity_threshold: Minimum similarity score for relevance
            
        Returns:
            Dict with context items from knowledge graph and semantic memory
        """
        if not self._session:
            raise RuntimeError("Memory integration service not initialized")
        
        try:
            # Prepare hybrid search request
            search_request = {
                "query": query,
                "search_type": "hybrid",  # Both structured and semantic search
                "limit": context_limit * 2,  # Get more to filter down
                "filters": {
                    "similarity_threshold": similarity_threshold
                }
            }
            
            if user_id:
                search_request["user_id"] = user_id
            
            async with self._session.post(
                f"{self.memory_service_url}/hybrid_search",
                json=search_request
            ) as response:
                
                if response.status != 200:
                    logger.warning(f"Memory service search failed: {response.status}")
                    return {"context_items": [], "sources": [], "error": f"Search failed: {response.status}"}
                
                data = await response.json()
                results = data.get("results", [])
                
                # Process and rank results
                context_items = self._process_context_results(results, context_limit)
                
                return {
                    "context_items": context_items,
                    "sources": self._extract_sources(results),
                    "total_found": len(results),
                    "query_used": query
                }
                
        except Exception as e:
            logger.error(f"Error getting relevant context: {e}")
            return {"context_items": [], "sources": [], "error": str(e)}
    
    def _process_context_results(self, results: List[Dict], limit: int) -> List[Dict[str, Any]]:
        """Process and rank context results"""
        
        processed_items = []
        
        for result in results[:limit]:
            context_item = {
                "content": result.get("content", ""),
                "source": result.get("source", "unknown"),
                "relevance_score": result.get("score", 0.0),
                "type": result.get("type", "semantic"),
                "metadata": result.get("metadata", {})
            }
            
            # Add structured data if available (from knowledge graph)
            if result.get("entities"):
                context_item["entities"] = result["entities"]
            if result.get("relationships"):
                context_item["relationships"] = result["relationships"]
            
            processed_items.append(context_item)
        
        # Sort by relevance score
        processed_items.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return processed_items
    
    def _extract_sources(self, results: List[Dict]) -> List[str]:
        """Extract unique sources from results"""
        sources = set()
        for result in results:
            source = result.get("source", "unknown")
            if source != "unknown":
                sources.add(source)
        return list(sources)
    
    async def get_knowledge_graph_context(
        self, 
        entities: List[str], 
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get specific context from knowledge graph based on entities
        
        Args:
            entities: List of entity names to search for
            user_id: User identifier for personalized results
            
        Returns:
            Dict with entity information and relationships
        """
        if not self._session:
            raise RuntimeError("Memory integration service not initialized")
        
        try:
            context = {"entities": [], "relationships": []}
            
            # Get entities
            for entity in entities:
                params = {"entity_type": entity, "limit": 5}
                if user_id:
                    params["user_id"] = user_id
                
                async with self._session.get(
                    f"{self.memory_service_url}/knowledge_graph/entities",
                    params=params
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        context["entities"].extend(data.get("entities", []))
            
            # Get relationships for found entities
            entity_names = [e.get("name", "") for e in context["entities"]]
            for entity_name in entity_names[:3]:  # Limit to avoid too many requests
                params = {"source_entity": entity_name, "limit": 3}
                
                async with self._session.get(
                    f"{self.memory_service_url}/knowledge_graph/relationships",
                    params=params
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        context["relationships"].extend(data.get("relationships", []))
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting knowledge graph context: {e}")
            return {"entities": [], "relationships": [], "error": str(e)}
    
    async def store_reasoning_outcome(
        self,
        query: str,
        reasoning_steps: List[str],
        final_answer: str,
        success: bool,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Store successful reasoning outcomes back to memory service for future learning
        
        Args:
            query: Original reasoning query
            reasoning_steps: List of reasoning steps taken
            final_answer: Final reasoning result
            success: Whether reasoning was successful
            user_id: User identifier
            
        Returns:
            Boolean indicating if storage was successful
        """
        if not self._session or not success:
            return False  # Only store successful reasoning
        
        try:
            # Prepare document for storage
            reasoning_document = {
                "content": f"Query: {query}\n\nReasoning Steps:\n" + 
                          "\n".join(f"{i+1}. {step}" for i, step in enumerate(reasoning_steps)) +
                          f"\n\nFinal Answer: {final_answer}",
                "document_metadata": {
                    "type": "reasoning_session",
                    "query": query,
                    "success": success,
                    "steps_count": len(reasoning_steps),
                    "user_id": user_id
                }
            }
            
            async with self._session.post(
                f"{self.memory_service_url}/process_document",
                json=reasoning_document
            ) as response:
                
                if response.status == 200:
                    logger.info(f"Successfully stored reasoning outcome for query: {query[:50]}...")
                    return True
                else:
                    logger.warning(f"Failed to store reasoning outcome: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error storing reasoning outcome: {e}")
            return False
    
    async def get_user_reasoning_patterns(
        self, 
        user_id: str, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get user's historical reasoning patterns for personalization
        
        Args:
            user_id: User identifier
            limit: Maximum number of patterns to return
            
        Returns:
            List of reasoning patterns and preferences
        """
        if not self._session:
            return []
        
        try:
            # Search for user's previous reasoning sessions
            search_request = {
                "query": "reasoning patterns successful approaches",
                "search_type": "structured",
                "limit": limit,
                "filters": {
                    "user_id": user_id,
                    "type": "reasoning_session",
                    "success": True
                }
            }
            
            async with self._session.post(
                f"{self.memory_service_url}/hybrid_search",
                json=search_request
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    results = data.get("results", [])
                    
                    # Extract patterns
                    patterns = []
                    for result in results:
                        metadata = result.get("metadata", {})
                        patterns.append({
                            "query_type": self._classify_query_type(metadata.get("query", "")),
                            "steps_count": metadata.get("steps_count", 0),
                            "approach": self._extract_approach(result.get("content", "")),
                            "success_factors": self._identify_success_factors(result.get("content", ""))
                        })
                    
                    return patterns
                    
        except Exception as e:
            logger.error(f"Error getting user reasoning patterns: {e}")
        
        return []
    
    def _classify_query_type(self, query: str) -> str:
        """Classify the type of reasoning query"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["analyze", "compare", "evaluate"]):
            return "analytical"
        elif any(word in query_lower for word in ["solve", "calculate", "compute"]):
            return "problem_solving"
        elif any(word in query_lower for word in ["explain", "describe", "define"]):
            return "explanatory"
        elif any(word in query_lower for word in ["predict", "forecast", "estimate"]):
            return "predictive"
        else:
            return "general"
    
    def _extract_approach(self, content: str) -> str:
        """Extract the reasoning approach from content"""
        if "step by step" in content.lower():
            return "sequential"
        elif "compare" in content.lower() or "contrast" in content.lower():
            return "comparative" 
        elif "break down" in content.lower() or "decompose" in content.lower():
            return "analytical"
        else:
            return "general"
    
    def _identify_success_factors(self, content: str) -> List[str]:
        """Identify factors that contributed to successful reasoning"""
        factors = []
        content_lower = content.lower()
        
        if "clear" in content_lower and "structure" in content_lower:
            factors.append("structured_approach")
        if "evidence" in content_lower or "data" in content_lower:
            factors.append("evidence_based")
        if "multiple" in content_lower and ("perspective" in content_lower or "angle" in content_lower):
            factors.append("multi_perspective")
        if "verify" in content_lower or "validate" in content_lower:
            factors.append("validation")
            
        return factors
    
    async def close(self) -> None:
        """Close the HTTP session"""
        if self._session:
            await self._session.close()
            logger.info("Memory integration service closed")