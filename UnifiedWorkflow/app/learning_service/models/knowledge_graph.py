"""
Knowledge Graph Models
=====================

Models for knowledge graph nodes, edges, and traversal operations
supporting pattern relationship storage and complex pattern queries.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum
import uuid


class NodeType(str, Enum):
    """Types of knowledge graph nodes."""
    PATTERN = "pattern"
    CONTEXT = "context"
    OUTCOME = "outcome"
    SERVICE = "service"
    AGENT = "agent"
    WORKFLOW = "workflow"
    CONCEPT = "concept"
    METRIC = "metric"


class EdgeType(str, Enum):
    """Types of knowledge graph edges."""
    DERIVES_FROM = "derives_from"        # Pattern derivation
    PRECEDES = "precedes"                # Temporal relationships
    ENABLES = "enables"                  # Enabling relationships
    CONFLICTS = "conflicts"              # Conflicting patterns
    SIMILAR_TO = "similar_to"            # Similarity relationships
    PART_OF = "part_of"                 # Composition relationships
    CAUSES = "causes"                   # Causal relationships
    CORRELATES_WITH = "correlates_with"  # Correlation relationships
    DEPENDS_ON = "depends_on"           # Dependency relationships


class KnowledgeGraphNode(BaseModel):
    """Node in the knowledge graph."""
    
    node_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique node identifier")
    node_type: NodeType = Field(..., description="Type of the node")
    
    # Node Identity
    name: str = Field(..., description="Human-readable node name")
    description: Optional[str] = Field(None, description="Node description")
    
    # Node Properties
    properties: Dict[str, Any] = Field(default_factory=dict, description="Node properties")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Node metadata")
    
    # Node State
    active: bool = Field(default=True, description="Whether the node is active")
    confidence: float = Field(default=1.0, description="Confidence in node validity")
    importance: float = Field(default=0.5, description="Importance score for the node")
    
    # Temporal Information
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Node creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    last_accessed: Optional[datetime] = Field(None, description="Last access timestamp")
    
    # Graph Statistics
    incoming_edges: int = Field(default=0, description="Number of incoming edges")
    outgoing_edges: int = Field(default=0, description="Number of outgoing edges")
    centrality_score: float = Field(default=0.0, description="Node centrality score")
    
    # Node Embeddings for Similarity
    embedding: Optional[List[float]] = Field(None, description="Vector embedding for similarity calculations")
    
    @validator('confidence', 'importance', 'centrality_score')
    def validate_scores(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("Scores must be between 0 and 1")
        return v


class KnowledgeGraphEdge(BaseModel):
    """Edge in the knowledge graph."""
    
    edge_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique edge identifier")
    edge_type: EdgeType = Field(..., description="Type of the edge")
    
    # Edge Endpoints
    source_node_id: str = Field(..., description="Source node ID")
    target_node_id: str = Field(..., description="Target node ID")
    
    # Edge Properties
    properties: Dict[str, Any] = Field(default_factory=dict, description="Edge properties")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Edge metadata")
    
    # Edge Strength and Confidence
    strength: float = Field(..., description="Strength of the relationship (0-1)")
    confidence: float = Field(..., description="Confidence in the relationship")
    weight: float = Field(default=1.0, description="Edge weight for graph algorithms")
    
    # Edge State
    active: bool = Field(default=True, description="Whether the edge is active")
    bidirectional: bool = Field(default=False, description="Whether the edge is bidirectional")
    
    # Temporal Information
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Edge creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    last_traversed: Optional[datetime] = Field(None, description="Last traversal timestamp")
    
    # Evidence and Support
    evidence: List[str] = Field(default_factory=list, description="Evidence supporting the relationship")
    support_count: int = Field(default=1, description="Number of observations supporting this edge")
    
    # Edge Statistics
    traversal_count: int = Field(default=0, description="Number of times edge has been traversed")
    success_count: int = Field(default=0, description="Number of successful traversals")
    
    @validator('strength', 'confidence', 'weight')
    def validate_edge_metrics(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("Edge metrics must be between 0 and 1")
        return v
    
    @property
    def success_rate(self) -> float:
        """Calculate traversal success rate."""
        if self.traversal_count == 0:
            return 0.0
        return self.success_count / self.traversal_count


class GraphTraversalQuery(BaseModel):
    """Query for graph traversal operations."""
    
    start_nodes: List[str] = Field(..., description="Starting node IDs")
    target_nodes: Optional[List[str]] = Field(None, description="Target node IDs (if any)")
    
    # Traversal Parameters
    max_depth: int = Field(default=3, description="Maximum traversal depth")
    edge_types: Optional[List[EdgeType]] = Field(None, description="Edge types to follow")
    node_types: Optional[List[NodeType]] = Field(None, description="Node types to include")
    
    # Filtering
    min_confidence: float = Field(default=0.0, description="Minimum edge confidence")
    min_strength: float = Field(default=0.0, description="Minimum edge strength")
    active_only: bool = Field(default=True, description="Include only active nodes/edges")
    
    # Traversal Strategy
    strategy: str = Field(default="breadth_first", description="Traversal strategy")
    weighted: bool = Field(default=True, description="Use edge weights in traversal")
    
    # Result Limits
    max_results: int = Field(default=100, description="Maximum number of results")
    include_paths: bool = Field(default=True, description="Include traversal paths in results")
    
    @validator('max_depth')
    def validate_depth(cls, v):
        if v <= 0 or v > 10:
            raise ValueError("Max depth must be between 1 and 10")
        return v
    
    @validator('strategy')
    def validate_strategy(cls, v):
        valid_strategies = ['breadth_first', 'depth_first', 'shortest_path', 'weighted']
        if v not in valid_strategies:
            raise ValueError(f"Strategy must be one of: {valid_strategies}")
        return v


class GraphTraversalResult(BaseModel):
    """Result of graph traversal operation."""
    
    query_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique query identifier")
    
    # Result Nodes and Edges
    nodes: List[KnowledgeGraphNode] = Field(default_factory=list, description="Nodes in the result")
    edges: List[KnowledgeGraphEdge] = Field(default_factory=list, description="Edges in the result")
    
    # Traversal Paths
    paths: List[List[str]] = Field(default_factory=list, description="Traversal paths (node ID sequences)")
    path_weights: List[float] = Field(default_factory=list, description="Weights for each path")
    
    # Result Statistics
    total_nodes_visited: int = Field(default=0, description="Total nodes visited during traversal")
    total_edges_traversed: int = Field(default=0, description="Total edges traversed")
    max_depth_reached: int = Field(default=0, description="Maximum depth reached")
    
    # Query Performance
    execution_time: float = Field(default=0.0, description="Query execution time")
    query_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Query execution timestamp")
    
    # Result Quality
    completeness_score: float = Field(default=0.0, description="Completeness of the result")
    relevance_score: float = Field(default=0.0, description="Relevance of the result")
    
    @validator('completeness_score', 'relevance_score')
    def validate_quality_scores(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("Quality scores must be between 0 and 1")
        return v


class KnowledgeGraphQuery(BaseModel):
    """General knowledge graph query."""
    
    query_type: str = Field(..., description="Type of query (pattern, similarity, path, subgraph)")
    parameters: Dict[str, Any] = Field(..., description="Query parameters")
    
    # Query Constraints
    filters: Dict[str, Any] = Field(default_factory=dict, description="Query filters")
    sorting: Optional[Dict[str, str]] = Field(None, description="Result sorting criteria")
    pagination: Optional[Dict[str, int]] = Field(None, description="Pagination parameters")
    
    # Query Options
    include_metadata: bool = Field(default=True, description="Include node/edge metadata")
    include_statistics: bool = Field(default=False, description="Include graph statistics")
    cache_results: bool = Field(default=True, description="Cache query results")
    
    @validator('query_type')
    def validate_query_type(cls, v):
        valid_types = ['pattern', 'similarity', 'path', 'subgraph', 'centrality', 'clustering']
        if v not in valid_types:
            raise ValueError(f"Query type must be one of: {valid_types}")
        return v


class GraphAnalytics(BaseModel):
    """Analytics and insights derived from the knowledge graph."""
    
    # Graph Structure Metrics
    total_nodes: int = Field(default=0, description="Total number of nodes")
    total_edges: int = Field(default=0, description="Total number of edges")
    graph_density: float = Field(default=0.0, description="Graph density")
    average_degree: float = Field(default=0.0, description="Average node degree")
    
    # Centrality Metrics
    most_central_nodes: List[Dict[str, Any]] = Field(default_factory=list, description="Most central nodes")
    hub_nodes: List[str] = Field(default_factory=list, description="Hub node IDs")
    bridge_edges: List[str] = Field(default_factory=list, description="Bridge edge IDs")
    
    # Pattern Insights
    common_patterns: List[Dict[str, Any]] = Field(default_factory=list, description="Most common patterns")
    emerging_patterns: List[Dict[str, Any]] = Field(default_factory=list, description="Emerging patterns")
    
    # Clustering and Communities
    communities: List[List[str]] = Field(default_factory=list, description="Detected communities")
    modularity_score: float = Field(default=0.0, description="Graph modularity score")
    
    # Temporal Insights
    growth_rate: float = Field(default=0.0, description="Graph growth rate")
    activity_hotspots: List[Dict[str, Any]] = Field(default_factory=list, description="Activity hotspots")
    
    # Quality Metrics
    consistency_score: float = Field(default=0.0, description="Graph consistency score")
    completeness_score: float = Field(default=0.0, description="Graph completeness score")
    
    # Analysis Metadata
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Analysis timestamp")
    analysis_version: str = Field(default="1.0", description="Analysis version")


class GraphUpdateOperation(BaseModel):
    """Operation for updating the knowledge graph."""
    
    operation_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique operation identifier")
    operation_type: str = Field(..., description="Type of operation (create, update, delete, merge)")
    
    # Target Elements
    target_nodes: List[str] = Field(default_factory=list, description="Target node IDs")
    target_edges: List[str] = Field(default_factory=list, description="Target edge IDs")
    
    # Operation Data
    node_data: Optional[KnowledgeGraphNode] = Field(None, description="Node data for create/update operations")
    edge_data: Optional[KnowledgeGraphEdge] = Field(None, description="Edge data for create/update operations")
    
    # Operation Parameters
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Operation parameters")
    batch_operation: bool = Field(default=False, description="Whether this is part of a batch operation")
    
    # Operation Validation
    validate_before: bool = Field(default=True, description="Validate operation before execution")
    rollback_on_error: bool = Field(default=True, description="Rollback on error")
    
    # Operation Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Operation creation timestamp")
    priority: int = Field(default=5, description="Operation priority (1-10)")
    
    @validator('operation_type')
    def validate_operation_type(cls, v):
        valid_types = ['create', 'update', 'delete', 'merge', 'batch']
        if v not in valid_types:
            raise ValueError(f"Operation type must be one of: {valid_types}")
        return v
    
    @validator('priority')
    def validate_priority(cls, v):
        if not 1 <= v <= 10:
            raise ValueError("Priority must be between 1 and 10")
        return v