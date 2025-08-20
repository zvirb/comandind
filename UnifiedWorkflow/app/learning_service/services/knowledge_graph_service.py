"""
Knowledge Graph Service
======================

Neo4j integration for pattern relationship storage, graph traversal,
and complex pattern queries within the learning system.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import json

from neo4j import AsyncGraphDatabase, AsyncDriver
import numpy as np

from models.patterns import (
    LearningPattern, PatternType, PatternScope, PatternRelationship
)
from models.knowledge_graph import (
    KnowledgeGraphNode, KnowledgeGraphEdge, NodeType, EdgeType,
    GraphTraversalQuery, GraphTraversalResult, KnowledgeGraphQuery,
    GraphAnalytics, GraphUpdateOperation
)
from config import config


logger = logging.getLogger(__name__)


class KnowledgeGraphService:
    """
    Service for managing pattern relationships and knowledge graph operations using Neo4j.
    
    Provides:
    - Pattern storage with relationship tracking
    - Graph traversal for pattern discovery
    - Complex pattern queries
    - Graph analytics and insights
    - Pattern evolution tracking
    """
    
    def __init__(self):
        self.driver: Optional[AsyncDriver] = None
        self.connected = False
        
        # Graph statistics
        self.total_nodes = 0
        self.total_edges = 0
        self.last_analytics_update = datetime.utcnow()
        
        logger.info("Knowledge Graph Service initialized")
    
    async def initialize(self) -> None:
        """Initialize connection to Neo4j database."""
        try:
            # Create Neo4j driver
            self.driver = AsyncGraphDatabase.driver(
                config.neo4j_url,
                auth=(config.neo4j_username, config.neo4j_password)
            )
            
            # Test connection
            async with self.driver.session(database=config.neo4j_database) as session:
                result = await session.run("RETURN 1 AS test")
                await result.single()
            
            self.connected = True
            
            # Initialize graph schema
            await self._initialize_graph_schema()
            
            # Load graph statistics
            await self._update_graph_statistics()
            
            logger.info("Successfully connected to Neo4j knowledge graph")
            
        except Exception as e:
            logger.error(f"Failed to initialize Knowledge Graph Service: {e}")
            self.connected = False
            raise
    
    async def close(self) -> None:
        """Close Neo4j connection."""
        if self.driver:
            await self.driver.close()
            self.connected = False
            logger.info("Neo4j connection closed")
    
    async def store_pattern(
        self, 
        pattern: LearningPattern,
        relationships: List[PatternRelationship]
    ) -> bool:
        """
        Store a learning pattern and its relationships in the knowledge graph.
        
        Args:
            pattern: Pattern to store
            relationships: Pattern relationships
            
        Returns:
            Success status
        """
        if not self.connected:
            logger.warning("Knowledge graph not connected")
            return False
        
        try:
            async with self.driver.session(database=config.neo4j_database) as session:
                # Create pattern node
                pattern_created = await self._create_pattern_node(session, pattern)
                
                if pattern_created:
                    # Create relationships
                    for relationship in relationships:
                        await self._create_relationship(session, relationship)
                    
                    # Update graph statistics
                    await self._update_graph_statistics()
                    
                    logger.info(f"Stored pattern {pattern.pattern_id} with {len(relationships)} relationships")
                    return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error storing pattern in knowledge graph: {e}")
            return False
    
    async def load_pattern(self, pattern_id: str) -> Optional[LearningPattern]:
        """Load a pattern from the knowledge graph."""
        if not self.connected:
            return None
        
        try:
            async with self.driver.session(database=config.neo4j_database) as session:
                query = """
                MATCH (p:Pattern {pattern_id: $pattern_id})
                RETURN p
                """
                result = await session.run(query, pattern_id=pattern_id)
                record = await result.single()
                
                if record:
                    return self._record_to_pattern(record['p'])
                
        except Exception as e:
            logger.error(f"Error loading pattern from knowledge graph: {e}")
        
        return None
    
    async def load_all_patterns(self) -> Dict[str, LearningPattern]:
        """Load all patterns from the knowledge graph."""
        if not self.connected:
            return {}
        
        patterns = {}
        try:
            async with self.driver.session(database=config.neo4j_database) as session:
                query = "MATCH (p:Pattern) RETURN p"
                result = await session.run(query)
                
                async for record in result:
                    pattern = self._record_to_pattern(record['p'])
                    if pattern:
                        patterns[pattern.pattern_id] = pattern
                        
            logger.info(f"Loaded {len(patterns)} patterns from knowledge graph")
            
        except Exception as e:
            logger.error(f"Error loading all patterns from knowledge graph: {e}")
        
        return patterns
    
    async def get_pattern_relationships(
        self,
        pattern_id: str,
        relationship_types: Optional[List[str]] = None,
        max_depth: int = 2
    ) -> Dict[str, List[PatternRelationship]]:
        """Get relationships for a specific pattern."""
        if not self.connected:
            return {}
        
        try:
            async with self.driver.session(database=config.neo4j_database) as session:
                # Build query with optional relationship type filter
                type_filter = ""
                if relationship_types:
                    types_str = "'" + "', '".join(relationship_types) + "'"
                    type_filter = f"WHERE TYPE(r) IN [{types_str}]"
                
                query = f"""
                MATCH (p1:Pattern {{pattern_id: $pattern_id}})-[r*1..{max_depth}]-(p2:Pattern)
                {type_filter}
                RETURN p1, r, p2
                """
                
                result = await session.run(query, pattern_id=pattern_id)
                
                relationships_by_type = {}
                async for record in result:
                    # Process relationship records
                    path_relationships = record['r']
                    for rel in path_relationships:
                        rel_type = rel.type
                        if rel_type not in relationships_by_type:
                            relationships_by_type[rel_type] = []
                        
                        relationship = PatternRelationship(
                            from_pattern_id=rel.start_node['pattern_id'],
                            to_pattern_id=rel.end_node['pattern_id'],
                            relationship_type=rel_type,
                            strength=rel.get('strength', 1.0),
                            confidence=rel.get('confidence', 1.0),
                            evidence=rel.get('evidence', [])
                        )
                        relationships_by_type[rel_type].append(relationship)
                
                return relationships_by_type
                
        except Exception as e:
            logger.error(f"Error getting pattern relationships: {e}")
            return {}
    
    async def traverse_graph(self, query: GraphTraversalQuery) -> GraphTraversalResult:
        """Perform graph traversal operation."""
        if not self.connected:
            return GraphTraversalResult(
                nodes=[], edges=[], paths=[], path_weights=[]
            )
        
        try:
            async with self.driver.session(database=config.neo4j_database) as session:
                start_time = datetime.utcnow()
                
                # Build traversal query
                cypher_query, parameters = self._build_traversal_query(query)
                
                result = await session.run(cypher_query, parameters)
                
                nodes = []
                edges = []
                paths = []
                path_weights = []
                
                async for record in result:
                    # Process traversal results
                    if 'path' in record:
                        path_data = record['path']
                        path_nodes = [node['id'] for node in path_data.nodes]
                        path_weight = sum(rel.get('weight', 1.0) for rel in path_data.relationships)
                        
                        paths.append(path_nodes)
                        path_weights.append(path_weight)
                        
                        # Collect unique nodes and edges
                        for node in path_data.nodes:
                            node_obj = self._neo4j_node_to_kg_node(node)
                            if node_obj not in nodes:
                                nodes.append(node_obj)
                        
                        for rel in path_data.relationships:
                            edge_obj = self._neo4j_rel_to_kg_edge(rel)
                            if edge_obj not in edges:
                                edges.append(edge_obj)
                
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                
                return GraphTraversalResult(
                    nodes=nodes,
                    edges=edges,
                    paths=paths,
                    path_weights=path_weights,
                    total_nodes_visited=len(nodes),
                    total_edges_traversed=len(edges),
                    max_depth_reached=query.max_depth,
                    execution_time=execution_time
                )
                
        except Exception as e:
            logger.error(f"Error performing graph traversal: {e}")
            return GraphTraversalResult(
                nodes=[], edges=[], paths=[], path_weights=[]
            )
    
    async def query_graph(self, query: KnowledgeGraphQuery) -> Dict[str, Any]:
        """Execute a general knowledge graph query."""
        if not self.connected:
            return {}
        
        try:
            if query.query_type == "pattern":
                return await self._execute_pattern_query(query)
            elif query.query_type == "similarity":
                return await self._execute_similarity_query(query)
            elif query.query_type == "path":
                return await self._execute_path_query(query)
            elif query.query_type == "subgraph":
                return await self._execute_subgraph_query(query)
            else:
                logger.warning(f"Unsupported query type: {query.query_type}")
                return {}
                
        except Exception as e:
            logger.error(f"Error executing graph query: {e}")
            return {}
    
    async def get_graph_analytics(self) -> GraphAnalytics:
        """Get comprehensive graph analytics."""
        if not self.connected:
            return GraphAnalytics()
        
        try:
            async with self.driver.session(database=config.neo4j_database) as session:
                analytics = GraphAnalytics()
                
                # Basic statistics
                stats_query = """
                MATCH (n) WITH count(n) as nodeCount
                MATCH ()-[r]-() WITH nodeCount, count(r) as edgeCount
                RETURN nodeCount, edgeCount
                """
                stats_result = await session.run(stats_query)
                stats_record = await stats_result.single()
                
                if stats_record:
                    analytics.total_nodes = stats_record['nodeCount']
                    analytics.total_edges = stats_record['edgeCount']
                
                # Calculate graph density
                if analytics.total_nodes > 1:
                    max_edges = analytics.total_nodes * (analytics.total_nodes - 1) / 2
                    analytics.graph_density = analytics.total_edges / max_edges
                
                # Get most central nodes
                centrality_query = """
                MATCH (n)-[r]-()
                WITH n, count(r) as degree
                RETURN n.pattern_id as pattern_id, n.name as name, degree
                ORDER BY degree DESC
                LIMIT 10
                """
                centrality_result = await session.run(centrality_query)
                
                analytics.most_central_nodes = []
                async for record in centrality_result:
                    analytics.most_central_nodes.append({
                        'pattern_id': record['pattern_id'],
                        'name': record['name'],
                        'degree': record['degree']
                    })
                
                # Get common patterns
                pattern_query = """
                MATCH (p:Pattern)
                WITH p.pattern_type as type, count(p) as count
                RETURN type, count
                ORDER BY count DESC
                """
                pattern_result = await session.run(pattern_query)
                
                analytics.common_patterns = []
                async for record in pattern_result:
                    analytics.common_patterns.append({
                        'type': record['type'],
                        'count': record['count']
                    })
                
                analytics.analysis_timestamp = datetime.utcnow()
                return analytics
                
        except Exception as e:
            logger.error(f"Error getting graph analytics: {e}")
            return GraphAnalytics()
    
    async def update_pattern_metrics(
        self, 
        pattern_id: str, 
        metrics_update: Dict[str, Any]
    ) -> bool:
        """Update pattern performance metrics."""
        if not self.connected:
            return False
        
        try:
            async with self.driver.session(database=config.neo4j_database) as session:
                query = """
                MATCH (p:Pattern {pattern_id: $pattern_id})
                SET p += $metrics
                RETURN p
                """
                result = await session.run(
                    query, 
                    pattern_id=pattern_id, 
                    metrics=metrics_update
                )
                
                return await result.single() is not None
                
        except Exception as e:
            logger.error(f"Error updating pattern metrics: {e}")
            return False
    
    # Private methods
    
    async def _initialize_graph_schema(self) -> None:
        """Initialize Neo4j graph schema with constraints and indexes."""
        try:
            async with self.driver.session(database=config.neo4j_database) as session:
                # Create constraints
                constraints = [
                    "CREATE CONSTRAINT pattern_id_unique IF NOT EXISTS FOR (p:Pattern) REQUIRE p.pattern_id IS UNIQUE",
                    "CREATE CONSTRAINT context_id_unique IF NOT EXISTS FOR (c:Context) REQUIRE c.context_id IS UNIQUE",
                    "CREATE CONSTRAINT service_name_unique IF NOT EXISTS FOR (s:Service) REQUIRE s.name IS UNIQUE"
                ]
                
                for constraint in constraints:
                    try:
                        await session.run(constraint)
                    except Exception as e:
                        # Constraint might already exist
                        logger.debug(f"Constraint creation result: {e}")
                
                # Create indexes
                indexes = [
                    "CREATE INDEX pattern_type_index IF NOT EXISTS FOR (p:Pattern) ON (p.pattern_type)",
                    "CREATE INDEX pattern_scope_index IF NOT EXISTS FOR (p:Pattern) ON (p.pattern_scope)",
                    "CREATE INDEX pattern_confidence_index IF NOT EXISTS FOR (p:Pattern) ON (p.confidence_score)",
                    "CREATE INDEX pattern_created_index IF NOT EXISTS FOR (p:Pattern) ON (p.created_at)"
                ]
                
                for index in indexes:
                    try:
                        await session.run(index)
                    except Exception as e:
                        # Index might already exist
                        logger.debug(f"Index creation result: {e}")
                
                logger.info("Graph schema initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing graph schema: {e}")
            raise
    
    async def _create_pattern_node(
        self, 
        session, 
        pattern: LearningPattern
    ) -> bool:
        """Create a pattern node in the graph."""
        try:
            query = """
            MERGE (p:Pattern {pattern_id: $pattern_id})
            SET p += $properties
            RETURN p
            """
            
            properties = {
                'name': pattern.name,
                'description': pattern.description,
                'pattern_type': pattern.pattern_type.value,
                'pattern_scope': pattern.pattern_scope.value,
                'source_service': pattern.source_service,
                'confidence_score': pattern.confidence_score,
                'created_at': pattern.created_at.isoformat(),
                'updated_at': pattern.updated_at.isoformat(),
                'status': pattern.status.value,
                'trigger_conditions': json.dumps(pattern.trigger_conditions),
                'context_requirements': json.dumps(pattern.context_requirements),
                'action_sequence': json.dumps(pattern.action_sequence),
                'expected_outcomes': json.dumps(pattern.expected_outcomes)
            }
            
            result = await session.run(
                query,
                pattern_id=pattern.pattern_id,
                properties=properties
            )
            
            return await result.single() is not None
            
        except Exception as e:
            logger.error(f"Error creating pattern node: {e}")
            return False
    
    async def _create_relationship(
        self, 
        session, 
        relationship: PatternRelationship
    ) -> bool:
        """Create a relationship between patterns."""
        try:
            query = f"""
            MATCH (p1:Pattern {{pattern_id: $from_id}})
            MATCH (p2:Pattern {{pattern_id: $to_id}})
            MERGE (p1)-[r:{relationship.relationship_type.upper()}]->(p2)
            SET r.strength = $strength,
                r.confidence = $confidence,
                r.evidence = $evidence,
                r.created_at = $created_at
            RETURN r
            """
            
            result = await session.run(
                query,
                from_id=relationship.from_pattern_id,
                to_id=relationship.to_pattern_id,
                strength=relationship.strength,
                confidence=relationship.confidence,
                evidence=relationship.evidence,
                created_at=relationship.created_at.isoformat()
            )
            
            return await result.single() is not None
            
        except Exception as e:
            logger.error(f"Error creating relationship: {e}")
            return False
    
    async def _update_graph_statistics(self) -> None:
        """Update cached graph statistics."""
        try:
            async with self.driver.session(database=config.neo4j_database) as session:
                # Count nodes
                node_result = await session.run("MATCH (n) RETURN count(n) as count")
                node_record = await node_result.single()
                self.total_nodes = node_record['count'] if node_record else 0
                
                # Count edges
                edge_result = await session.run("MATCH ()-[r]-() RETURN count(r) as count")
                edge_record = await edge_result.single()
                self.total_edges = edge_record['count'] if edge_record else 0
                
                self.last_analytics_update = datetime.utcnow()
                
        except Exception as e:
            logger.error(f"Error updating graph statistics: {e}")
    
    def _record_to_pattern(self, record) -> Optional[LearningPattern]:
        """Convert Neo4j record to LearningPattern."""
        try:
            return LearningPattern(
                pattern_id=record['pattern_id'],
                pattern_type=PatternType(record['pattern_type']),
                pattern_scope=PatternScope(record['pattern_scope']),
                name=record['name'],
                description=record['description'],
                trigger_conditions=json.loads(record.get('trigger_conditions', '{}')),
                context_requirements=json.loads(record.get('context_requirements', '{}')),
                action_sequence=json.loads(record.get('action_sequence', '[]')),
                expected_outcomes=json.loads(record.get('expected_outcomes', '{}')),
                source_service=record['source_service'],
                confidence_score=record.get('confidence_score', 0.0),
                created_at=datetime.fromisoformat(record['created_at']),
                updated_at=datetime.fromisoformat(record['updated_at'])
            )
        except Exception as e:
            logger.error(f"Error converting record to pattern: {e}")
            return None
    
    def _build_traversal_query(self, query: GraphTraversalQuery) -> Tuple[str, Dict[str, Any]]:
        """Build Cypher query for graph traversal."""
        # Simplified traversal query builder
        start_nodes_str = "'" + "', '".join(query.start_nodes) + "'"
        
        cypher_query = f"""
        MATCH path = (start:Pattern)-[*1..{query.max_depth}]-(end:Pattern)
        WHERE start.pattern_id IN [{start_nodes_str}]
        RETURN path
        LIMIT {query.max_results}
        """
        
        return cypher_query, {}
    
    def _neo4j_node_to_kg_node(self, node) -> KnowledgeGraphNode:
        """Convert Neo4j node to KnowledgeGraphNode."""
        return KnowledgeGraphNode(
            node_id=node.get('pattern_id', str(node.id)),
            node_type=NodeType.PATTERN,
            name=node.get('name', 'Unknown'),
            description=node.get('description'),
            properties=dict(node)
        )
    
    def _neo4j_rel_to_kg_edge(self, rel) -> KnowledgeGraphEdge:
        """Convert Neo4j relationship to KnowledgeGraphEdge."""
        return KnowledgeGraphEdge(
            source_node_id=str(rel.start_node.id),
            target_node_id=str(rel.end_node.id),
            edge_type=EdgeType.DERIVES_FROM,  # Default type
            strength=rel.get('strength', 1.0),
            confidence=rel.get('confidence', 1.0),
            properties=dict(rel)
        )
    
    async def _execute_pattern_query(self, query: KnowledgeGraphQuery) -> Dict[str, Any]:
        """Execute a pattern-based query."""
        # Implementation for pattern queries
        return {}
    
    async def _execute_similarity_query(self, query: KnowledgeGraphQuery) -> Dict[str, Any]:
        """Execute a similarity-based query.""" 
        # Implementation for similarity queries
        return {}
    
    async def _execute_path_query(self, query: KnowledgeGraphQuery) -> Dict[str, Any]:
        """Execute a path-based query."""
        # Implementation for path queries
        return {}
    
    async def _execute_subgraph_query(self, query: KnowledgeGraphQuery) -> Dict[str, Any]:
        """Execute a subgraph query."""
        # Implementation for subgraph queries
        return {}