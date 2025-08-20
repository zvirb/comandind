"""Memory pipeline mock for hybrid memory service testing."""

import asyncio
from typing import Dict, Any, List, Optional
from uuid import uuid4
import numpy as np
from faker import Faker

fake = Faker()


class MemoryPipelineMock:
    """Mock memory pipeline for comprehensive testing."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.response_delay = self.config.get("response_delay", 0.0)
        self.error_rate = self.config.get("error_rate", 0.0)
        self.quality_mode = self.config.get("quality_mode", "high")  # high, medium, low
        self.enable_reconciliation = self.config.get("enable_reconciliation", True)
        
        # Mock services (injected or created)
        self.ollama_service = self.config.get("ollama_service")
        self.database_service = self.config.get("database_service")
        self.qdrant_service = self.config.get("qdrant_service")
        
        # Pipeline state
        self.processed_memories = []
        self.call_count = 0
    
    async def process_memory(
        self,
        content: str,
        content_type: str = "text",
        source: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Mock memory processing pipeline."""
        await self._simulate_delay()
        self.call_count += 1
        
        if self._should_error():
            return {
                "status": "error",
                "error": "Pipeline processing failed",
                "processing_time_ms": np.random.randint(100, 500)
            }
        
        # Generate realistic processing result
        memory_id = uuid4()
        
        # Mock phase 1 - extraction
        phase1_time = np.random.randint(800, 1500)
        processed_content = self._generate_processed_content(content, self.quality_mode)
        summary = self._generate_summary(content)
        confidence = self._generate_confidence(content, self.quality_mode)
        
        # Mock phase 2 - reconciliation (if enabled and similar memories found)
        phase2_time = 0
        related_memories = []
        reconciliation_applied = False
        
        if self.enable_reconciliation and self._should_reconcile(content):
            phase2_time = np.random.randint(600, 1200)
            related_memories = self._generate_related_memories()
            reconciliation_applied = True
            
            # Enhance processed content with reconciliation
            processed_content = f"[Reconciled] {processed_content}"
            confidence = min(confidence + 0.05, 0.98)  # Boost confidence slightly
        
        total_time = phase1_time + phase2_time
        
        # Store in mock processed memories
        memory_record = {
            "memory_id": memory_id,
            "original_content": content,
            "processed_content": processed_content,
            "content_type": content_type,
            "source": source,
            "tags": tags or [],
            "metadata": metadata or {},
            "confidence_score": confidence,
            "created_at": fake.date_time_this_year()
        }
        self.processed_memories.append(memory_record)
        
        return {
            "memory_id": memory_id,
            "processed_content": processed_content,
            "summary": summary,
            "confidence_score": confidence,
            "related_memories": [str(m) for m in related_memories],
            "processing_time_ms": total_time,
            "status": "success",
            "pipeline_metrics": {
                "phase1_time_ms": phase1_time,
                "phase2_time_ms": phase2_time,
                "total_time_ms": total_time,
                "related_memories_found": len(related_memories),
                "reconciliation_applied": reconciliation_applied,
                "qdrant_storage_success": True
            }
        }
    
    async def search_memories(
        self,
        query: str,
        limit: int = 10,
        similarity_threshold: Optional[float] = None,
        content_type_filter: Optional[str] = None,
        source_filter: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        include_summary_only: bool = False,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Mock memory search functionality."""
        await self._simulate_delay()
        self.call_count += 1
        
        if self._should_error():
            return {
                "results": [],
                "total_count": 0,
                "query": query,
                "processing_time_ms": np.random.randint(50, 200),
                "error": "Search pipeline failed"
            }
        
        # Mock search results based on query and stored memories
        results = self._generate_search_results(
            query, limit, similarity_threshold, content_type_filter,
            source_filter, include_summary_only
        )
        
        processing_time = np.random.randint(300, 1000)
        
        return {
            "results": results,
            "total_count": len(results),
            "query": query,
            "processing_time_ms": processing_time,
            "similarity_threshold_used": similarity_threshold or 0.7,
            "postgres_results": max(0, len(results) - 2),
            "qdrant_results": min(len(results), 3),
            "hybrid_fusion_applied": len(results) > 1
        }
    
    # Helper methods
    
    async def _simulate_delay(self):
        """Simulate processing delay."""
        if self.response_delay > 0:
            await asyncio.sleep(self.response_delay)
    
    def _should_error(self) -> bool:
        """Determine if operation should error."""
        return np.random.random() < self.error_rate
    
    def _should_reconcile(self, content: str) -> bool:
        """Determine if reconciliation should be triggered."""
        # Mock logic - reconcile for longer content or specific keywords
        return len(content) > 500 or any(
            keyword in content.lower() 
            for keyword in ["machine learning", "neural network", "api design", "data analysis"]
        )
    
    def _generate_processed_content(self, content: str, quality_mode: str) -> str:
        """Generate processed content based on quality mode."""
        content_length = len(content)
        
        if quality_mode == "high":
            # High quality: structured, comprehensive processing
            if content_length > 1000:
                return f"Comprehensive analysis: {content[:200]}... [Detailed extraction with key concepts, relationships, and structured information]"
            else:
                return f"Structured extraction: {content[:150]}... [Organized with key points and context]"
        
        elif quality_mode == "medium":
            # Medium quality: good but less detailed
            return f"Processed content: {content[:100]}... [Key information extracted]"
        
        else:  # low quality
            # Low quality: basic processing
            return f"Basic extraction: {content[:80]}..."
    
    def _generate_summary(self, content: str) -> str:
        """Generate summary from content."""
        words = content.split()
        
        if len(words) <= 15:
            return content
        else:
            key_words = words[:12]
            return " ".join(key_words) + "..."
    
    def _generate_confidence(self, content: str, quality_mode: str) -> float:
        """Generate confidence score based on content and quality mode."""
        base_confidence = {
            "high": 0.88,
            "medium": 0.82,
            "low": 0.75
        }.get(quality_mode, 0.80)
        
        # Adjust based on content characteristics
        content_lower = content.lower()
        
        # Boost confidence for well-structured content
        if any(keyword in content_lower for keyword in [
            "definition", "explanation", "example", "steps", "process"
        ]):
            base_confidence += 0.05
        
        # Reduce confidence for unclear content
        if len(content) < 50 or content.count("?") > 3:
            base_confidence -= 0.1
        
        # Add realistic variation
        variation = np.random.uniform(-0.03, 0.03)
        final_confidence = base_confidence + variation
        
        return max(min(final_confidence, 0.98), 0.60)
    
    def _generate_related_memories(self) -> List[str]:
        """Generate mock related memory IDs."""
        num_related = np.random.randint(1, 4)
        return [str(uuid4()) for _ in range(num_related)]
    
    def _generate_search_results(
        self,
        query: str,
        limit: int,
        similarity_threshold: Optional[float],
        content_type_filter: Optional[str],
        source_filter: Optional[str],
        include_summary_only: bool
    ) -> List[Dict[str, Any]]:
        """Generate mock search results."""
        query_lower = query.lower()
        results = []
        
        # Generate results based on processed memories and query relevance
        for i, memory in enumerate(self.processed_memories):
            if len(results) >= limit:
                break
            
            # Apply filters
            if content_type_filter and memory["content_type"] != content_type_filter:
                continue
            if source_filter and memory["source"] != source_filter:
                continue
            
            # Calculate mock relevance
            content_lower = memory["processed_content"].lower()
            relevance = self._calculate_mock_relevance(query_lower, content_lower)
            
            if similarity_threshold and relevance < similarity_threshold:
                continue
            
            # Format result
            content_field = memory["processed_content"]
            if include_summary_only:
                content_field = memory["processed_content"][:100] + "..."
            
            result = {
                "memory_id": str(memory["memory_id"]),
                "content": content_field,
                "summary": self._generate_summary(memory["processed_content"]),
                "content_type": memory["content_type"],
                "source": memory.get("source", ""),
                "tags": memory.get("tags", []),
                "similarity_score": relevance,
                "relevance_score": relevance * 0.9,  # Slightly lower relevance score
                "created_at": memory["created_at"].isoformat(),
                "updated_at": memory["created_at"].isoformat(),
                "access_count": np.random.randint(1, 20),
                "consolidation_count": np.random.randint(0, 3)
            }
            
            results.append(result)
        
        # If no stored memories match, generate some mock results
        if not results and not self.processed_memories:
            results = self._generate_default_search_results(query, limit, similarity_threshold)
        
        # Sort by similarity score
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        return results[:limit]
    
    def _calculate_mock_relevance(self, query: str, content: str) -> float:
        """Calculate mock relevance score between query and content."""
        query_terms = query.split()
        content_words = content.split()
        
        if not query_terms:
            return 0.5
        
        # Count matching terms
        matches = 0
        for term in query_terms:
            for word in content_words:
                if term in word.lower() or word.lower() in term:
                    matches += 1
                    break
        
        # Base relevance on term matches
        base_relevance = min(matches / len(query_terms), 1.0) * 0.8
        
        # Add some randomness for realism
        relevance = base_relevance + np.random.uniform(0, 0.2)
        
        return min(max(relevance, 0.0), 1.0)
    
    def _generate_default_search_results(
        self,
        query: str,
        limit: int,
        similarity_threshold: Optional[float]
    ) -> List[Dict[str, Any]]:
        """Generate default mock search results when no stored memories exist."""
        results = []
        base_relevance = 0.85
        
        for i in range(min(limit, 5)):  # Generate up to 5 default results
            relevance = base_relevance - (i * 0.1)
            
            if similarity_threshold and relevance < similarity_threshold:
                break
            
            result = {
                "memory_id": str(uuid4()),
                "content": f"Mock search result {i+1} for query: {query}",
                "summary": f"Summary of result {i+1}",
                "content_type": "text",
                "source": "mock_source",
                "tags": ["mock", "search", "result"],
                "similarity_score": relevance,
                "relevance_score": relevance * 0.95,
                "created_at": fake.date_time_this_year().isoformat(),
                "updated_at": fake.date_time_this_year().isoformat(),
                "access_count": np.random.randint(1, 15),
                "consolidation_count": np.random.randint(0, 2)
            }
            
            results.append(result)
        
        return results


# Predefined pipeline configurations

PIPELINE_CONFIGS = {
    "high_quality": {
        "response_delay": 0.1,
        "error_rate": 0.0,
        "quality_mode": "high",
        "enable_reconciliation": True
    },
    
    "medium_quality": {
        "response_delay": 0.05,
        "error_rate": 0.0,
        "quality_mode": "medium",
        "enable_reconciliation": True
    },
    
    "fast_processing": {
        "response_delay": 0.02,
        "error_rate": 0.0,
        "quality_mode": "medium",
        "enable_reconciliation": False
    },
    
    "unreliable": {
        "response_delay": 0.2,
        "error_rate": 0.08,
        "quality_mode": "medium",
        "enable_reconciliation": True
    },
    
    "high_error": {
        "response_delay": 0.1,
        "error_rate": 0.3,
        "quality_mode": "low",
        "enable_reconciliation": False
    }
}


def create_pipeline_mock(config_name: str = "high_quality") -> MemoryPipelineMock:
    """Create memory pipeline mock with predefined configuration."""
    config = PIPELINE_CONFIGS.get(config_name, PIPELINE_CONFIGS["high_quality"])
    return MemoryPipelineMock(config)