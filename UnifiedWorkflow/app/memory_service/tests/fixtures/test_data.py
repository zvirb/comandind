"""Comprehensive test data fixtures and validation utilities for hybrid memory service testing."""

import json
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

import pytest
import numpy as np
from faker import Faker

fake = Faker()


@dataclass
class MemoryTestRecord:
    """Represents a complete memory record for testing."""
    memory_id: str
    content: str
    content_type: str
    source: str
    processed_content: str
    summary: str
    confidence_score: float
    vector_embedding: List[float]
    tags: List[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    access_count: int
    consolidation_count: int


class MemoryTestDataGenerator:
    """Generates realistic test data for memory service testing."""
    
    def __init__(self, vector_size: int = 384):
        self.vector_size = vector_size
        self.fake = Faker()
        
        # Content templates for different types
        self.content_templates = {
            "text": [
                "Meeting notes: {topic}. Key points: {points}",
                "Article summary: {title}. Main insights: {insights}",
                "Project update: {project_name}. Status: {status}. Next steps: {next_steps}",
                "Research findings on {research_topic}: {findings}",
                "Customer feedback: {product} - {feedback_type}: {details}",
                "Code review notes: {file_name} - {review_comments}",
                "Design document: {feature_name} - {design_details}",
                "Bug report: {issue_title} - Steps: {steps} - Impact: {impact}",
            ],
            "document": [
                "Technical specification for {system_name}. Requirements: {requirements}",
                "User manual for {product_name}. Instructions: {instructions}",
                "API documentation: {endpoint} - Parameters: {params} - Response: {response}",
                "Architecture design: {component} - Overview: {overview}",
            ],
            "image": [
                "Screenshot of {screen_name} showing {elements}",
                "Diagram illustrating {concept} with components {components}",
                "Photo from {event_name} featuring {subjects}",
                "Chart displaying {data_type} with trends {trends}",
            ],
            "code": [
                "Function implementation: {function_name} in {language}. Purpose: {purpose}",
                "Class definition: {class_name} with methods {methods}",
                "Database schema: {table_name} with fields {fields}",
                "Configuration file: {config_name} with settings {settings}",
            ]
        }
        
        # Metadata templates
        self.metadata_templates = {
            "meeting": {"participants": [], "duration": 0, "location": ""},
            "article": {"author": "", "publication": "", "word_count": 0},
            "project": {"team": "", "deadline": "", "priority": ""},
            "research": {"methodology": "", "sample_size": 0, "confidence": 0.0},
            "feedback": {"rating": 0, "category": "", "user_segment": ""},
            "code": {"language": "", "complexity": "", "test_coverage": 0.0},
            "document": {"format": "", "version": "", "last_reviewed": ""},
            "image": {"format": "", "dimensions": "", "file_size": 0}
        }
    
    def generate_random_vector(self) -> List[float]:
        """Generate a random vector embedding."""
        vector = np.random.randn(self.vector_size)
        # Normalize to unit length
        vector = vector / np.linalg.norm(vector)
        return vector.tolist()
    
    def generate_similar_vector(self, base_vector: List[float], similarity: float = 0.8) -> List[float]:
        """Generate a vector similar to the base vector with specified similarity."""
        base_np = np.array(base_vector)
        
        # Generate a random vector
        random_vector = np.random.randn(self.vector_size)
        random_vector = random_vector / np.linalg.norm(random_vector)
        
        # Combine vectors to achieve desired similarity
        similar_vector = similarity * base_np + (1 - similarity) * random_vector
        similar_vector = similar_vector / np.linalg.norm(similar_vector)
        
        return similar_vector.tolist()
    
    def generate_memory_content(self, content_type: str) -> Dict[str, Any]:
        """Generate realistic memory content based on type."""
        templates = self.content_templates.get(content_type, self.content_templates["text"])
        template = random.choice(templates)
        
        # Fill template with realistic data
        if content_type == "text":
            content = template.format(
                topic=fake.catch_phrase(),
                points="; ".join([fake.sentence() for _ in range(3)]),
                title=fake.sentence(nb_words=6),
                insights="; ".join([fake.sentence() for _ in range(2)]),
                project_name=fake.company(),
                status=random.choice(["On track", "Behind schedule", "Ahead of schedule"]),
                next_steps="; ".join([fake.sentence() for _ in range(2)]),
                research_topic=fake.catch_phrase(),
                findings=fake.paragraph(),
                product=fake.word(),
                feedback_type=random.choice(["Positive", "Negative", "Neutral"]),
                details=fake.sentence(),
                file_name=fake.file_name(extension="py"),
                review_comments=fake.paragraph(),
                feature_name=fake.word(),
                design_details=fake.paragraph(),
                issue_title=fake.sentence(),
                steps="; ".join([f"Step {i+1}: {fake.sentence()}" for i in range(3)]),
                impact=random.choice(["Low", "Medium", "High", "Critical"])
            )
        elif content_type == "document":
            content = template.format(
                system_name=fake.word(),
                requirements="; ".join([fake.sentence() for _ in range(3)]),
                product_name=fake.word(),
                instructions="; ".join([fake.sentence() for _ in range(4)]),
                endpoint=f"/api/{fake.word()}",
                params=", ".join([fake.word() for _ in range(3)]),
                response=fake.sentence(),
                component=fake.word(),
                overview=fake.paragraph()
            )
        elif content_type == "image":
            content = template.format(
                screen_name=fake.word(),
                elements=", ".join([fake.word() for _ in range(3)]),
                concept=fake.catch_phrase(),
                components=", ".join([fake.word() for _ in range(4)]),
                event_name=fake.sentence(nb_words=3),
                subjects=", ".join([fake.name() for _ in range(2)]),
                data_type=fake.word(),
                trends=", ".join([fake.word() for _ in range(3)])
            )
        elif content_type == "code":
            content = template.format(
                function_name=fake.word(),
                language=random.choice(["Python", "JavaScript", "Java", "Go", "Rust"]),
                purpose=fake.sentence(),
                class_name=fake.word(),
                methods=", ".join([fake.word() for _ in range(3)]),
                table_name=fake.word(),
                fields=", ".join([fake.word() for _ in range(5)]),
                config_name=fake.file_name(extension="json"),
                settings="; ".join([f"{fake.word()}={fake.word()}" for _ in range(3)])
            )
        else:
            content = fake.paragraph()
        
        return {"content": content, "processed_content": f"Processed: {content[:100]}..."}
    
    def generate_metadata(self, content_type: str) -> Dict[str, Any]:
        """Generate realistic metadata based on content type."""
        base_metadata = {
            "source_ip": fake.ipv4(),
            "user_agent": fake.user_agent(),
            "timestamp": fake.iso8601(),
            "session_id": str(uuid.uuid4())
        }
        
        if content_type == "text":
            base_metadata.update({
                "word_count": random.randint(50, 500),
                "language": "en",
                "sentiment": random.choice(["positive", "neutral", "negative"])
            })
        elif content_type == "document":
            base_metadata.update({
                "format": random.choice(["pdf", "docx", "txt", "md"]),
                "version": f"{random.randint(1, 5)}.{random.randint(0, 9)}",
                "page_count": random.randint(1, 50)
            })
        elif content_type == "image":
            base_metadata.update({
                "format": random.choice(["png", "jpg", "gif", "svg"]),
                "dimensions": f"{random.randint(100, 2000)}x{random.randint(100, 2000)}",
                "file_size": random.randint(1024, 5*1024*1024)
            })
        elif content_type == "code":
            base_metadata.update({
                "language": random.choice(["python", "javascript", "java", "go"]),
                "lines_of_code": random.randint(10, 1000),
                "complexity": random.choice(["low", "medium", "high"])
            })
        
        return base_metadata
    
    def generate_memory_record(
        self, 
        content_type: Optional[str] = None,
        source: Optional[str] = None,
        similarity_to: Optional[List[float]] = None
    ) -> MemoryTestRecord:
        """Generate a complete memory record for testing."""
        
        content_type = content_type or random.choice(["text", "document", "image", "code"])
        source = source or random.choice(["api", "web", "upload", "sync", "import"])
        
        content_data = self.generate_memory_content(content_type)
        
        # Generate vector embedding
        if similarity_to:
            vector_embedding = self.generate_similar_vector(similarity_to)
        else:
            vector_embedding = self.generate_random_vector()
        
        # Generate tags
        tags = [fake.word() for _ in range(random.randint(1, 5))]
        
        # Generate metadata
        metadata = self.generate_metadata(content_type)
        
        # Generate timestamps
        created_at = fake.date_time_between(start_date='-30d', end_date='now')
        updated_at = fake.date_time_between(start_date=created_at, end_date='now')
        
        return MemoryTestRecord(
            memory_id=str(uuid.uuid4()),
            content=content_data["content"],
            content_type=content_type,
            source=source,
            processed_content=content_data["processed_content"],
            summary=fake.sentence(nb_words=20),
            confidence_score=round(random.uniform(0.7, 0.99), 2),
            vector_embedding=vector_embedding,
            tags=tags,
            metadata=metadata,
            created_at=created_at,
            updated_at=updated_at,
            access_count=random.randint(0, 100),
            consolidation_count=random.randint(0, 10)
        )
    
    def generate_related_memories(self, base_memory: MemoryTestRecord, count: int = 3) -> List[MemoryTestRecord]:
        """Generate memories related to a base memory."""
        related_memories = []
        
        for _ in range(count):
            # Create similar memory with high similarity
            similar_memory = self.generate_memory_record(
                content_type=base_memory.content_type,
                source=base_memory.source,
                similarity_to=base_memory.vector_embedding
            )
            # Share some tags
            similar_memory.tags = base_memory.tags[:2] + similar_memory.tags[:2]
            related_memories.append(similar_memory)
        
        return related_memories
    
    def generate_search_test_data(self, query: str, result_count: int = 10) -> List[MemoryTestRecord]:
        """Generate test data for search scenarios."""
        memories = []
        
        # Generate highly relevant results (top 3)
        for i in range(min(3, result_count)):
            memory = self.generate_memory_record()
            # Make content somewhat related to query
            memory.content = f"{query} related content: {memory.content}"
            memory.confidence_score = round(random.uniform(0.9, 0.99), 2)
            memories.append(memory)
        
        # Generate moderately relevant results
        for i in range(min(4, result_count - 3)):
            memory = self.generate_memory_record()
            # Include query term in content
            words = memory.content.split()
            words.insert(random.randint(0, len(words)), query.split()[0] if query.split() else "test")
            memory.content = " ".join(words)
            memory.confidence_score = round(random.uniform(0.75, 0.89), 2)
            memories.append(memory)
        
        # Generate less relevant results
        remaining = result_count - len(memories)
        for i in range(remaining):
            memory = self.generate_memory_record()
            memory.confidence_score = round(random.uniform(0.5, 0.74), 2)
            memories.append(memory)
        
        return memories
    
    def generate_performance_test_data(self, count: int = 100) -> List[MemoryTestRecord]:
        """Generate large dataset for performance testing."""
        memories = []
        
        # Generate diverse content types
        content_types = ["text", "document", "image", "code"]
        
        for i in range(count):
            content_type = content_types[i % len(content_types)]
            memory = self.generate_memory_record(content_type=content_type)
            memories.append(memory)
        
        return memories


class ValidationHelpers:
    """Helper functions for validating test results."""
    
    @staticmethod
    def validate_memory_response(response_data: Dict[str, Any]) -> bool:
        """Validate memory add/search response structure."""
        required_fields = ['memory_id', 'processed_content', 'status']
        return all(field in response_data for field in required_fields)
    
    @staticmethod
    def validate_search_response(response_data: Dict[str, Any]) -> bool:
        """Validate search response structure."""
        required_fields = ['results', 'total_count', 'query', 'processing_time_ms']
        return all(field in response_data for field in required_fields)
    
    @staticmethod
    def validate_memory_record(record: MemoryTestRecord) -> bool:
        """Validate memory record completeness."""
        required_attrs = [
            'memory_id', 'content', 'content_type', 'processed_content',
            'confidence_score', 'vector_embedding', 'created_at'
        ]
        return all(hasattr(record, attr) and getattr(record, attr) is not None 
                  for attr in required_attrs)
    
    @staticmethod
    def calculate_vector_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        vec1_np = np.array(vec1)
        vec2_np = np.array(vec2)
        
        dot_product = np.dot(vec1_np, vec2_np)
        norm1 = np.linalg.norm(vec1_np)
        norm2 = np.linalg.norm(vec2_np)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    @staticmethod
    def validate_performance_metrics(metrics: Dict[str, Any], targets: Dict[str, float]) -> bool:
        """Validate performance metrics against targets."""
        for metric_name, target_value in targets.items():
            if metric_name not in metrics:
                return False
            
            actual_value = metrics[metric_name]
            
            # Handle different comparison types
            if metric_name.endswith('_p95_ms'):
                # P95 latency should be below target
                if actual_value > target_value:
                    return False
            elif metric_name.startswith('mrr'):
                # MRR should be above target
                if actual_value < target_value:
                    return False
            elif metric_name.endswith('_score'):
                # Scores should be above target
                if actual_value < target_value:
                    return False
        
        return True
    
    @staticmethod
    def generate_mrr_test_data(queries_and_relevance: List[tuple]) -> float:
        """Calculate MRR (Mean Reciprocal Rank) from test data."""
        reciprocal_ranks = []
        
        for query, relevant_docs in queries_and_relevance:
            # Find the rank of the first relevant document
            rank = None
            for i, doc_id in enumerate(query):
                if doc_id in relevant_docs:
                    rank = i + 1  # Rank is 1-indexed
                    break
            
            if rank:
                reciprocal_ranks.append(1.0 / rank)
            else:
                reciprocal_ranks.append(0.0)
        
        return sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0


# Pytest fixtures
@pytest.fixture
def memory_test_generator():
    """Fixture providing memory test data generator."""
    return MemoryTestDataGenerator()


@pytest.fixture
def validation_helpers():
    """Fixture providing validation helper functions."""
    return ValidationHelpers()


@pytest.fixture
def sample_memory_records(memory_test_generator):
    """Fixture providing sample memory records."""
    return [memory_test_generator.generate_memory_record() for _ in range(10)]


@pytest.fixture
def related_memory_cluster(memory_test_generator):
    """Fixture providing a cluster of related memories."""
    base_memory = memory_test_generator.generate_memory_record()
    related_memories = memory_test_generator.generate_related_memories(base_memory, count=5)
    return [base_memory] + related_memories


@pytest.fixture
def search_test_scenarios():
    """Fixture providing various search test scenarios."""
    return [
        {
            "query": "machine learning algorithms",
            "expected_results": 8,
            "min_confidence": 0.7
        },
        {
            "query": "database optimization",
            "expected_results": 5,
            "min_confidence": 0.8
        },
        {
            "query": "API documentation",
            "expected_results": 12,
            "min_confidence": 0.75
        },
        {
            "query": "user interface design",
            "expected_results": 6,
            "min_confidence": 0.85
        }
    ]


@pytest.fixture
def performance_test_data(memory_test_generator):
    """Fixture providing large dataset for performance testing."""
    return memory_test_generator.generate_performance_test_data(count=1000)


@pytest.fixture
def mock_api_responses():
    """Fixture providing mock API response templates."""
    return {
        "memory_add_success": {
            "memory_id": "123e4567-e89b-12d3-a456-426614174000",
            "processed_content": "Processed test content with extracted concepts and structured information",
            "summary": "Test content about machine learning concepts and applications",
            "confidence_score": 0.92,
            "related_memories": [
                {
                    "memory_id": "456e7890-e89b-12d3-a456-426614174111",
                    "similarity_score": 0.85,
                    "content": "Related ML content"
                }
            ],
            "processing_time_ms": 1250,
            "status": "success"
        },
        "search_success": {
            "results": [
                {
                    "memory_id": "123e4567-e89b-12d3-a456-426614174000",
                    "content": "Machine learning algorithms for data processing",
                    "summary": "Overview of ML algorithms",
                    "similarity_score": 0.95,
                    "content_type": "text",
                    "created_at": "2025-01-11T12:00:00Z",
                    "access_count": 5
                }
            ],
            "total_count": 1,
            "query": "machine learning",
            "processing_time_ms": 850,
            "similarity_threshold_used": 0.75,
            "hybrid_fusion_applied": True
        },
        "health_check": {
            "status": "healthy",
            "timestamp": 1641906000.123,
            "checks": {
                "database": {"healthy": True, "memory_count": 1542},
                "qdrant": {"healthy": True, "collection_info": {"vectors_count": 1542}},
                "ollama": {"healthy": True, "model": "llama3.1:8b"}
            },
            "version": "1.0.0"
        }
    }