"""Ollama service mock for hybrid memory service testing."""

import asyncio
import hashlib
from typing import Dict, Any, List, Optional
import numpy as np
from faker import Faker

fake = Faker()


class OllamaMockService:
    """Mock Ollama service for memory service testing."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.model = self.config.get("model", "llama2")
        self.is_healthy = self.config.get("healthy", True)
        self.response_delay = self.config.get("response_delay", 0.0)
        self.error_rate = self.config.get("error_rate", 0.0)
        self.call_count = 0
    
    async def health_check(self) -> bool:
        """Mock health check."""
        await self._simulate_delay()
        self.call_count += 1
        
        if self._should_error():
            raise RuntimeError("Ollama health check failed")
        
        return self.is_healthy
    
    async def extract_memory(
        self,
        content: str,
        extraction_prompt: str,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Mock memory extraction."""
        await self._simulate_delay()
        self.call_count += 1
        
        if self._should_error():
            raise RuntimeError("Memory extraction failed")
        
        # Generate realistic extraction result
        return {
            "processed_content": self._generate_processed_content(content),
            "summary": self._generate_summary(content),
            "confidence": np.random.uniform(0.7, 0.95),
            "key_concepts": self._extract_key_concepts(content),
            "category": self._classify_content(content),
            "processing_time_ms": np.random.randint(800, 2000)
        }
    
    async def reconcile_memories(
        self,
        new_content: str,
        related_memories: List[Dict[str, Any]],
        reconciliation_prompt: str,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Mock memory reconciliation."""
        await self._simulate_delay()
        self.call_count += 1
        
        if self._should_error():
            raise RuntimeError("Memory reconciliation failed")
        
        return {
            "reconciled_content": self._generate_reconciled_content(new_content, related_memories),
            "confidence": np.random.uniform(0.8, 0.96),
            "changes_made": self._generate_reconciliation_changes(),
            "integration_quality": np.random.uniform(0.85, 0.98),
            "processing_time_ms": np.random.randint(1200, 2800)
        }
    
    async def generate_embeddings(
        self,
        text: str,
        request_id: Optional[str] = None
    ) -> List[float]:
        """Mock embeddings generation."""
        await self._simulate_delay()
        self.call_count += 1
        
        if self._should_error():
            raise RuntimeError("Embeddings generation failed")
        
        return self._generate_deterministic_embeddings(text)
    
    async def close(self):
        """Mock cleanup."""
        pass
    
    # Helper methods
    
    async def _simulate_delay(self):
        """Simulate processing delay."""
        if self.response_delay > 0:
            await asyncio.sleep(self.response_delay)
    
    def _should_error(self) -> bool:
        """Determine if call should error."""
        return np.random.random() < self.error_rate
    
    def _generate_processed_content(self, content: str) -> str:
        """Generate processed content from raw content."""
        # Simulate structured extraction
        content_lower = content.lower()
        
        if "machine learning" in content_lower:
            return f"Structured information about machine learning: {content[:200]}..."
        elif "software" in content_lower:
            return f"Software development knowledge: {content[:200]}..."
        elif "data" in content_lower:
            return f"Data analysis insights: {content[:200]}..."
        else:
            return f"General knowledge extraction: {content[:200]}..."
    
    def _generate_summary(self, content: str) -> str:
        """Generate summary from content."""
        words = content.split()[:15]
        return " ".join(words) + ("..." if len(content.split()) > 15 else "")
    
    def _extract_key_concepts(self, content: str) -> List[str]:
        """Extract key concepts from content."""
        content_lower = content.lower()
        concepts = []
        
        concept_keywords = [
            "machine learning", "deep learning", "neural networks",
            "software development", "programming", "algorithms",
            "data science", "statistics", "analysis",
            "cloud computing", "infrastructure", "deployment"
        ]
        
        for keyword in concept_keywords:
            if keyword in content_lower:
                concepts.append(keyword.replace(" ", "-"))
        
        return concepts[:5]  # Limit to top 5
    
    def _classify_content(self, content: str) -> str:
        """Classify content into categories."""
        content_lower = content.lower()
        
        if any(term in content_lower for term in ["machine learning", "neural", "ai", "model"]):
            return "machine-learning"
        elif any(term in content_lower for term in ["software", "programming", "code", "development"]):
            return "software-development"
        elif any(term in content_lower for term in ["data", "statistics", "analysis", "visualization"]):
            return "data-science"
        elif any(term in content_lower for term in ["cloud", "server", "infrastructure", "deployment"]):
            return "cloud-computing"
        else:
            return "general"
    
    def _generate_reconciled_content(self, new_content: str, related_memories: List[Dict]) -> str:
        """Generate reconciled content."""
        base_content = self._generate_processed_content(new_content)
        
        if related_memories:
            return f"Integrated content: {base_content} [Reconciled with {len(related_memories)} related memories]"
        else:
            return base_content
    
    def _generate_reconciliation_changes(self) -> List[str]:
        """Generate reconciliation changes."""
        possible_changes = [
            "Merged duplicate concepts",
            "Resolved conflicting information",
            "Enhanced with related context",
            "Standardized terminology",
            "Updated temporal references",
            "Consolidated similar examples"
        ]
        
        num_changes = np.random.randint(1, 4)
        return np.random.choice(possible_changes, size=num_changes, replace=False).tolist()
    
    def _generate_deterministic_embeddings(self, text: str) -> List[float]:
        """Generate deterministic embeddings based on text."""
        # Use hash for deterministic results
        hash_obj = hashlib.sha256(text.encode())
        seed = int(hash_obj.hexdigest()[:8], 16)
        rng = np.random.RandomState(seed)
        
        # Generate normalized vector
        vector = rng.normal(0, 0.1, 1536)
        return vector.tolist()