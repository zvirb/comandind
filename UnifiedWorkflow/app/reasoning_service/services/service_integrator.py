"""Service integration layer for cognitive architecture communication.

Handles event-driven communication with other cognitive services including
memory retrieval, perception analysis, and learning feedback.
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional
import aiohttp
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)


class ServiceIntegrator:
    """Integration layer for cognitive service communication."""
    
    def __init__(
        self,
        redis_service,
        hybrid_memory_url: str,
        perception_service_url: str,
        coordination_service_url: str,
        learning_service_url: str,
        enable_event_routing: bool = True,
        timeout: int = 30
    ):
        self.redis_service = redis_service
        self.hybrid_memory_url = hybrid_memory_url.rstrip("/")
        self.perception_service_url = perception_service_url.rstrip("/")
        self.coordination_service_url = coordination_service_url.rstrip("/")
        self.learning_service_url = learning_service_url.rstrip("/")
        self.enable_event_routing = enable_event_routing
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={"Content-Type": "application/json"}
            )
        return self._session
    
    # Memory Integration
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8)
    )
    async def retrieve_context_memory(
        self,
        workflow_id: str,
        query: str,
        limit: int = 5
    ) -> Optional[Dict[str, Any]]:
        """Retrieve relevant context from hybrid memory service."""
        try:
            session = await self._get_session()
            
            # Search for relevant memories
            search_url = f"{self.hybrid_memory_url}/memory/search"
            params = {
                "query": query,
                "limit": limit,
                "include_summary_only": True
            }
            
            async with session.get(search_url, params=params) as response:
                if response.status == 200:
                    memory_data = await response.json()
                    
                    logger.info(
                        "Retrieved context memory",
                        workflow_id=workflow_id,
                        results_count=memory_data.get("total_count", 0),
                        query_length=len(query)
                    )
                    
                    return {
                        "results": memory_data.get("results", []),
                        "total_count": memory_data.get("total_count", 0),
                        "context_summary": self._summarize_memory_context(memory_data.get("results", []))
                    }
                else:
                    logger.warning(
                        "Memory retrieval failed",
                        workflow_id=workflow_id,
                        status=response.status,
                        url=search_url
                    )
                    return None
                    
        except Exception as e:
            logger.error(
                "Error retrieving context memory",
                workflow_id=workflow_id,
                error=str(e)
            )
            return None
    
    async def store_reasoning_memory(
        self,
        workflow_id: str,
        reasoning_summary: str,
        confidence_score: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Store reasoning results in memory for future reference."""
        try:
            session = await self._get_session()
            
            memory_content = f"Reasoning Analysis: {reasoning_summary}"
            
            memory_data = {
                "content": memory_content,
                "content_type": "reasoning_result",
                "source": "reasoning_service",
                "tags": ["reasoning", "cognitive", f"confidence_{confidence_score:.1f}"],
                "metadata": {
                    "workflow_id": workflow_id,
                    "confidence_score": confidence_score,
                    "timestamp": time.time(),
                    **(metadata or {})
                }
            }
            
            async with session.post(f"{self.hybrid_memory_url}/memory/add", json=memory_data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(
                        "Stored reasoning memory",
                        workflow_id=workflow_id,
                        memory_id=result.get("memory_id"),
                        confidence_score=confidence_score
                    )
                    return True
                else:
                    logger.warning(
                        "Failed to store reasoning memory",
                        workflow_id=workflow_id,
                        status=response.status
                    )
                    return False
                    
        except Exception as e:
            logger.error(
                "Error storing reasoning memory",
                workflow_id=workflow_id,
                error=str(e)
            )
            return False
    
    def _summarize_memory_context(self, memory_results: List[Dict[str, Any]]) -> str:
        """Summarize memory context for reasoning use."""
        if not memory_results:
            return "No relevant context found"
        
        summaries = []
        for result in memory_results[:3]:  # Top 3 most relevant
            content = result.get("content", "")
            summary = result.get("summary", content[:100] + "..." if len(content) > 100 else content)
            summaries.append(summary)
        
        return " | ".join(summaries)
    
    # Perception Integration
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=4)
    )
    async def request_multimodal_analysis(
        self,
        workflow_id: str,
        image_data: str,
        image_format: str,
        analysis_prompt: str
    ) -> Optional[Dict[str, Any]]:
        """Request multimodal analysis from perception service."""
        try:
            session = await self._get_session()
            
            analysis_data = {
                "image_data": image_data,
                "format": image_format,
                "prompt": analysis_prompt
            }
            
            async with session.post(
                f"{self.perception_service_url}/analyze/multimodal", 
                json=analysis_data
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    logger.info(
                        "Multimodal analysis completed",
                        workflow_id=workflow_id,
                        processing_time_ms=result.get("processing_time_ms", 0)
                    )
                    
                    return result
                else:
                    logger.warning(
                        "Multimodal analysis failed",
                        workflow_id=workflow_id,
                        status=response.status
                    )
                    return None
                    
        except Exception as e:
            logger.error(
                "Error requesting multimodal analysis",
                workflow_id=workflow_id,
                error=str(e)
            )
            return None
    
    # Event Communication
    
    async def publish_reasoning_complete_event(
        self,
        workflow_id: str,
        reasoning_type: str,
        confidence_score: float,
        result_summary: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Publish reasoning completion event to coordination service."""
        if not self.enable_event_routing:
            return True
        
        try:
            event_data = {
                "workflow_id": workflow_id,
                "reasoning_type": reasoning_type,
                "confidence_score": confidence_score,
                "result_summary": result_summary,
                "processing_timestamp": time.time(),
                "service_version": "1.0.0",
                **(metadata or {})
            }
            
            # Publish via Redis
            published = await self.redis_service.publish_cognitive_event(
                event_type="reasoning_complete",
                event_data=event_data,
                channel="cognitive_events"
            )
            
            if published:
                logger.info(
                    "Published reasoning complete event",
                    workflow_id=workflow_id,
                    reasoning_type=reasoning_type,
                    confidence_score=confidence_score
                )
            
            return published
            
        except Exception as e:
            logger.error(
                "Error publishing reasoning complete event",
                workflow_id=workflow_id,
                error=str(e)
            )
            return False
    
    async def publish_validation_event(
        self,
        workflow_id: str,
        validation_type: str,
        validity_score: float,
        meets_threshold: bool,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Publish validation event to coordination service."""
        if not self.enable_event_routing:
            return True
        
        try:
            event_data = {
                "workflow_id": workflow_id,
                "validation_type": validation_type,
                "validity_score": validity_score,
                "meets_threshold": meets_threshold,
                "processing_timestamp": time.time(),
                **(metadata or {})
            }
            
            published = await self.redis_service.publish_cognitive_event(
                event_type="validation_complete",
                event_data=event_data,
                channel="cognitive_events"
            )
            
            if published:
                logger.info(
                    "Published validation event",
                    workflow_id=workflow_id,
                    validation_type=validation_type,
                    validity_score=validity_score,
                    meets_threshold=meets_threshold
                )
            
            return published
            
        except Exception as e:
            logger.error(
                "Error publishing validation event",
                workflow_id=workflow_id,
                error=str(e)
            )
            return False
    
    # Learning Integration
    
    async def send_learning_feedback(
        self,
        workflow_id: str,
        pattern_type: str,
        outcome_data: Dict[str, Any],
        success_indicators: Dict[str, Any]
    ) -> bool:
        """Send learning feedback to learning service."""
        try:
            session = await self._get_session()
            
            feedback_data = {
                "workflow_id": workflow_id,
                "pattern_type": pattern_type,
                "outcome_data": outcome_data,
                "success_indicators": success_indicators,
                "source_service": "reasoning_service",
                "feedback_timestamp": time.time()
            }
            
            async with session.post(
                f"{self.learning_service_url}/patterns/reasoning-outcome",
                json=feedback_data
            ) as response:
                if response.status in [200, 201, 202]:  # Accept various success codes
                    logger.info(
                        "Learning feedback sent successfully",
                        workflow_id=workflow_id,
                        pattern_type=pattern_type
                    )
                    return True
                else:
                    logger.warning(
                        "Learning feedback failed",
                        workflow_id=workflow_id,
                        status=response.status
                    )
                    return False
                    
        except Exception as e:
            logger.error(
                "Error sending learning feedback",
                workflow_id=workflow_id,
                error=str(e)
            )
            return False
    
    # Service Health Integration
    
    async def check_service_availability(
        self,
        service_name: str,
        service_url: str
    ) -> Dict[str, Any]:
        """Check availability of integrated service."""
        try:
            session = await self._get_session()
            start_time = time.time()
            
            async with session.get(f"{service_url}/health") as response:
                latency = time.time() - start_time
                
                if response.status == 200:
                    health_data = await response.json()
                    
                    return {
                        "service": service_name,
                        "available": True,
                        "status": health_data.get("status", "unknown"),
                        "latency_ms": round(latency * 1000, 2),
                        "version": health_data.get("version", "unknown")
                    }
                else:
                    return {
                        "service": service_name,
                        "available": False,
                        "status": f"HTTP {response.status}",
                        "latency_ms": round(latency * 1000, 2)
                    }
                    
        except Exception as e:
            return {
                "service": service_name,
                "available": False,
                "status": f"Error: {str(e)}",
                "latency_ms": -1
            }
    
    async def get_integration_health(self) -> Dict[str, Any]:
        """Get health status of all integrated services."""
        services_to_check = [
            ("hybrid_memory", self.hybrid_memory_url),
            ("perception_service", self.perception_service_url),
            ("coordination_service", self.coordination_service_url),
            ("learning_service", self.learning_service_url)
        ]
        
        # Check services concurrently
        health_tasks = [
            self.check_service_availability(name, url)
            for name, url in services_to_check
        ]
        
        health_results = await asyncio.gather(*health_tasks, return_exceptions=True)
        
        # Process results
        integration_health = {}
        all_available = True
        
        for i, result in enumerate(health_results):
            service_name = services_to_check[i][0]
            
            if isinstance(result, Exception):
                integration_health[service_name] = {
                    "available": False,
                    "status": f"Check failed: {str(result)}",
                    "latency_ms": -1
                }
                all_available = False
            else:
                integration_health[service_name] = result
                if not result.get("available", False):
                    all_available = False
        
        return {
            "overall_status": "healthy" if all_available else "degraded",
            "services": integration_health,
            "event_routing_enabled": self.enable_event_routing,
            "check_timestamp": time.time()
        }
    
    # Utility Methods
    
    async def batch_service_requests(
        self,
        requests: List[Dict[str, Any]],
        max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """Execute multiple service requests with concurrency control."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_request(request_config: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                method = request_config.get("method", "GET").upper()
                url = request_config.get("url")
                data = request_config.get("data")
                request_id = request_config.get("id", f"request_{id(request_config)}")
                
                try:
                    session = await self._get_session()
                    
                    if method == "GET":
                        async with session.get(url, params=data) as response:
                            result_data = await response.json() if response.status == 200 else {}
                    elif method == "POST":
                        async with session.post(url, json=data) as response:
                            result_data = await response.json() if response.status in [200, 201] else {}
                    else:
                        result_data = {"error": f"Unsupported method: {method}"}
                    
                    return {
                        "id": request_id,
                        "success": True,
                        "data": result_data
                    }
                    
                except Exception as e:
                    return {
                        "id": request_id,
                        "success": False,
                        "error": str(e)
                    }
        
        # Execute all requests concurrently
        results = await asyncio.gather(
            *[execute_request(req) for req in requests],
            return_exceptions=True
        )
        
        # Process results
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                processed_results.append({
                    "success": False,
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def close(self):
        """Close HTTP session and cleanup resources."""
        try:
            if self._session and not self._session.closed:
                await self._session.close()
                logger.info("Service integrator HTTP session closed")
        except Exception as e:
            logger.error("Error closing service integrator session", error=str(e))