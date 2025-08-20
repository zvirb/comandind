#!/usr/bin/env python3
"""
Memory Service Integration Module

Replaces markdown file creation with structured memory MCP service usage.
Provides comprehensive orchestration knowledge storage and retrieval.

Key Features:
- Entity-based knowledge storage instead of markdown files
- Structured schemas for orchestration data
- Intelligent search and retrieval
- Legacy migration capabilities
- Size management and token optimization
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from uuid import uuid4

logger = logging.getLogger(__name__)

class MemoryEntityType:
    """Standardized entity types for orchestration knowledge."""
    
    # Core orchestration entities
    ORCHESTRATION_WORKFLOW = "orchestration_workflow"
    AGENT_FINDINGS = "agent_findings"
    SYSTEM_CONFIGURATION = "system_configuration"
    ERROR_PATTERNS = "error_patterns"
    PERFORMANCE_METRICS = "performance_metrics"
    
    # Analysis entities
    INFRASTRUCTURE_ANALYSIS = "infrastructure_analysis"
    SECURITY_VALIDATION = "security_validation"
    DATABASE_SCHEMA = "database_schema"
    API_DOCUMENTATION = "api_documentation"
    DEPLOYMENT_EVIDENCE = "deployment_evidence"
    
    # Learning entities
    PATTERN_LIBRARY = "pattern_library"
    DECISION_RECORD = "decision_record"
    VALIDATION_PROTOCOL = "validation_protocol"
    INTEGRATION_GUIDE = "integration_guide"
    TROUBLESHOOTING_GUIDE = "troubleshooting_guide"
    
    # Context entities
    CONTEXT_PACKAGE = "context_package"
    SYNTHESIS_RESULT = "synthesis_result"
    AUDIT_REPORT = "audit_report"
    
    @classmethod
    def get_all_types(cls) -> List[str]:
        """Get all available entity types."""
        return [
            value for name, value in cls.__dict__.items()
            if not name.startswith('_') and isinstance(value, str) and not callable(value)
        ]


class MemoryServiceIntegration:
    """
    Memory service integration for orchestration knowledge management.
    
    Replaces markdown file creation with structured memory MCP operations.
    """
    
    def __init__(self, mcp_functions: Dict[str, Any]):
        """
        Initialize with MCP function references.
        
        Args:
            mcp_functions: Dictionary of MCP function references
        """
        self.mcp = mcp_functions
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    async def store_orchestration_knowledge(
        self,
        entity_name: str,
        entity_type: str,
        content: Union[str, Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Store orchestration knowledge as memory entity.
        
        Args:
            entity_name: Unique name for the entity
            entity_type: Type from MemoryEntityType class
            content: Knowledge content (string or structured data)
            metadata: Additional metadata
            tags: Classification tags
            
        Returns:
            Entity ID for future reference
        """
        try:
            # Validate entity type
            if entity_type not in MemoryEntityType.get_all_types():
                raise ValueError(f"Invalid entity type: {entity_type}")
            
            # Prepare content
            if isinstance(content, dict):
                content_str = json.dumps(content, indent=2)
            else:
                content_str = str(content)
            
            # Prepare observations
            observations = [content_str]
            
            # Add metadata as observations if provided
            if metadata:
                metadata_str = f"Metadata: {json.dumps(metadata, indent=2)}"
                observations.append(metadata_str)
            
            # Add tags as observations if provided
            if tags:
                tags_str = f"Tags: {', '.join(tags)}"
                observations.append(tags_str)
            
            # Add timestamp
            timestamp_str = f"Created: {datetime.utcnow().isoformat()}Z"
            observations.append(timestamp_str)
            
            # Create entity
            result = await self.mcp["mcp__memory__create_entities"](
                entities=[{
                    "name": entity_name,
                    "entityType": entity_type,
                    "observations": observations
                }]
            )
            
            self.logger.info(f"Stored orchestration knowledge: {entity_name} ({entity_type})")
            return entity_name
            
        except Exception as e:
            self.logger.error(f"Failed to store orchestration knowledge: {e}")
            raise
    
    async def search_orchestration_knowledge(
        self,
        query: str,
        entity_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search orchestration knowledge.
        
        Args:
            query: Search query
            entity_type: Optional entity type filter
            limit: Maximum results to return
            
        Returns:
            List of matching entities with metadata
        """
        try:
            # Build search query
            search_query = query
            if entity_type:
                search_query = f"{query} entityType:{entity_type}"
            
            # Search entities
            result = await self.mcp["mcp__memory__search_nodes"](query=search_query)
            
            # Process results
            entities = result.get("entities", [])
            
            # Limit results
            if len(entities) > limit:
                entities = entities[:limit]
            
            # Parse and enrich results
            processed_results = []
            for entity in entities:
                processed_entity = {
                    "name": entity.get("name"),
                    "entity_type": entity.get("entityType"),
                    "observations": entity.get("observations", []),
                    "content": self._extract_content_from_observations(entity.get("observations", [])),
                    "metadata": self._extract_metadata_from_observations(entity.get("observations", [])),
                    "tags": self._extract_tags_from_observations(entity.get("observations", [])),
                    "timestamp": self._extract_timestamp_from_observations(entity.get("observations", []))
                }
                processed_results.append(processed_entity)
            
            self.logger.info(f"Found {len(processed_results)} knowledge entities for query: {query}")
            return processed_results
            
        except Exception as e:
            self.logger.error(f"Failed to search orchestration knowledge: {e}")
            raise
    
    async def update_orchestration_knowledge(
        self,
        entity_name: str,
        additional_content: Union[str, Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update existing orchestration knowledge entity.
        
        Args:
            entity_name: Name of existing entity
            additional_content: Content to add
            metadata: Additional metadata
            
        Returns:
            True if successful
        """
        try:
            # Prepare content
            if isinstance(additional_content, dict):
                content_str = json.dumps(additional_content, indent=2)
            else:
                content_str = str(additional_content)
            
            # Prepare observations
            observations = [content_str]
            
            # Add metadata if provided
            if metadata:
                metadata_str = f"Update Metadata: {json.dumps(metadata, indent=2)}"
                observations.append(metadata_str)
            
            # Add update timestamp
            timestamp_str = f"Updated: {datetime.utcnow().isoformat()}Z"
            observations.append(timestamp_str)
            
            # Add observations to existing entity
            await self.mcp["mcp__memory__add_observations"](
                observations=[{
                    "entityName": entity_name,
                    "contents": observations
                }]
            )
            
            self.logger.info(f"Updated orchestration knowledge: {entity_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update orchestration knowledge: {e}")
            raise
    
    async def get_orchestration_knowledge(
        self,
        entity_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get specific orchestration knowledge entity.
        
        Args:
            entity_name: Name of entity to retrieve
            
        Returns:
            Entity data if found, None otherwise
        """
        try:
            # Open specific entity by name
            result = await self.mcp["mcp__memory__open_nodes"](names=[entity_name])
            
            entities = result.get("entities", [])
            if not entities:
                return None
            
            entity = entities[0]
            
            # Process and return entity data
            return {
                "name": entity.get("name"),
                "entity_type": entity.get("entityType"),
                "observations": entity.get("observations", []),
                "content": self._extract_content_from_observations(entity.get("observations", [])),
                "metadata": self._extract_metadata_from_observations(entity.get("observations", [])),
                "tags": self._extract_tags_from_observations(entity.get("observations", [])),
                "timestamp": self._extract_timestamp_from_observations(entity.get("observations", []))
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get orchestration knowledge: {e}")
            return None
    
    async def store_agent_findings(
        self,
        agent_name: str,
        findings: Dict[str, Any],
        context: Optional[str] = None
    ) -> str:
        """
        Store agent research findings in memory.
        
        Args:
            agent_name: Name of the agent
            findings: Research findings and analysis
            context: Optional context information
            
        Returns:
            Entity name for reference
        """
        entity_name = f"{agent_name}_findings_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Prepare structured findings content
        content = {
            "agent": agent_name,
            "findings": findings,
            "context": context,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        # Store in memory
        await self.store_orchestration_knowledge(
            entity_name=entity_name,
            entity_type=MemoryEntityType.AGENT_FINDINGS,
            content=content,
            metadata={"agent": agent_name, "type": "research_findings"},
            tags=[agent_name, "findings", "research"]
        )
        
        return entity_name
    
    async def store_context_package(
        self,
        package_name: str,
        specialist_type: str,
        context_data: Dict[str, Any],
        token_count: int
    ) -> str:
        """
        Store context package for specialist agents.
        
        Args:
            package_name: Unique package name
            specialist_type: Type of specialist this package is for
            context_data: Context data and instructions
            token_count: Estimated token count
            
        Returns:
            Entity name for reference
        """
        # Validate token count
        if token_count > 4000:
            self.logger.warning(f"Context package exceeds 4000 tokens: {token_count}")
        
        # Prepare package content
        content = {
            "specialist_type": specialist_type,
            "context_data": context_data,
            "token_count": token_count,
            "created": datetime.utcnow().isoformat() + "Z"
        }
        
        # Store in memory
        await self.store_orchestration_knowledge(
            entity_name=package_name,
            entity_type=MemoryEntityType.CONTEXT_PACKAGE,
            content=content,
            metadata={"specialist": specialist_type, "tokens": token_count},
            tags=[specialist_type, "context", "package"]
        )
        
        return package_name
    
    async def store_validation_evidence(
        self,
        validation_name: str,
        evidence_data: Dict[str, Any],
        success: bool
    ) -> str:
        """
        Store validation evidence and results.
        
        Args:
            validation_name: Name of validation performed
            evidence_data: Evidence and proof data
            success: Whether validation succeeded
            
        Returns:
            Entity name for reference
        """
        entity_name = f"validation_{validation_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Prepare evidence content
        content = {
            "validation_type": validation_name,
            "evidence": evidence_data,
            "success": success,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        # Store in memory
        await self.store_orchestration_knowledge(
            entity_name=entity_name,
            entity_type=MemoryEntityType.DEPLOYMENT_EVIDENCE,
            content=content,
            metadata={"validation": validation_name, "success": success},
            tags=["validation", "evidence", validation_name]
        )
        
        return entity_name
    
    async def migrate_markdown_to_memory(
        self,
        markdown_file_path: str,
        entity_type: str,
        entity_name: Optional[str] = None
    ) -> str:
        """
        Migrate existing markdown file to memory entity.
        
        Args:
            markdown_file_path: Path to markdown file
            entity_type: Entity type for the memory
            entity_name: Optional custom entity name
            
        Returns:
            Entity name created
        """
        try:
            # Read markdown file
            file_path = Path(markdown_file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"Markdown file not found: {markdown_file_path}")
            
            content = file_path.read_text(encoding='utf-8')
            
            # Generate entity name if not provided
            if not entity_name:
                entity_name = file_path.stem.replace('-', '_').replace(' ', '_')
            
            # Extract metadata from content
            metadata = {
                "source_file": str(file_path),
                "migrated_at": datetime.utcnow().isoformat() + "Z",
                "file_size": len(content)
            }
            
            # Store in memory
            await self.store_orchestration_knowledge(
                entity_name=entity_name,
                entity_type=entity_type,
                content=content,
                metadata=metadata,
                tags=["migrated", "markdown", entity_type]
            )
            
            self.logger.info(f"Migrated markdown file to memory: {markdown_file_path} -> {entity_name}")
            return entity_name
            
        except Exception as e:
            self.logger.error(f"Failed to migrate markdown file: {e}")
            raise
    
    def _extract_content_from_observations(self, observations: List[str]) -> str:
        """Extract main content from observations list."""
        if not observations:
            return ""
        
        # First observation is typically the main content
        main_content = observations[0]
        
        # Filter out metadata and tags observations
        for obs in observations:
            if not any(obs.startswith(prefix) for prefix in ["Metadata:", "Tags:", "Created:", "Updated:", "Update Metadata:"]):
                return obs
        
        return main_content
    
    def _extract_metadata_from_observations(self, observations: List[str]) -> Dict[str, Any]:
        """Extract metadata from observations list."""
        metadata = {}
        
        for obs in observations:
            if obs.startswith("Metadata:") or obs.startswith("Update Metadata:"):
                try:
                    # Remove prefix and parse JSON
                    json_str = obs.split(":", 1)[1].strip()
                    obs_metadata = json.loads(json_str)
                    metadata.update(obs_metadata)
                except (json.JSONDecodeError, IndexError):
                    continue
        
        return metadata
    
    def _extract_tags_from_observations(self, observations: List[str]) -> List[str]:
        """Extract tags from observations list."""
        tags = []
        
        for obs in observations:
            if obs.startswith("Tags:"):
                try:
                    # Remove prefix and split tags
                    tags_str = obs.split(":", 1)[1].strip()
                    obs_tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()]
                    tags.extend(obs_tags)
                except IndexError:
                    continue
        
        return list(set(tags))  # Remove duplicates
    
    def _extract_timestamp_from_observations(self, observations: List[str]) -> Optional[str]:
        """Extract creation/update timestamp from observations list."""
        for obs in observations:
            if obs.startswith("Created:") or obs.startswith("Updated:"):
                try:
                    # Remove prefix and get timestamp
                    timestamp = obs.split(":", 1)[1].strip()
                    return timestamp
                except IndexError:
                    continue
        
        return None


class MemoryAntiPattern:
    """
    Anti-pattern detection and prevention for markdown file creation.
    
    Prevents agents from creating markdown files and redirects to memory service.
    """
    
    def __init__(self, memory_integration: MemoryServiceIntegration):
        self.memory = memory_integration
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def detect_markdown_creation_attempt(self, file_path: str) -> bool:
        """
        Detect attempt to create markdown file.
        
        Args:
            file_path: Path being written to
            
        Returns:
            True if this is a markdown file creation attempt
        """
        return file_path.lower().endswith('.md')
    
    async def redirect_to_memory_service(
        self,
        intended_file_path: str,
        content: str,
        suggested_entity_type: Optional[str] = None
    ) -> str:
        """
        Redirect markdown file creation to memory service.
        
        Args:
            intended_file_path: Path where markdown would have been created
            content: Content intended for markdown file
            suggested_entity_type: Suggested entity type
            
        Returns:
            Entity name created in memory service
        """
        # Determine entity type from file name/path
        if not suggested_entity_type:
            suggested_entity_type = self._determine_entity_type_from_path(intended_file_path)
        
        # Generate entity name from file path
        file_path = Path(intended_file_path)
        entity_name = file_path.stem.replace('-', '_').replace(' ', '_')
        
        # Add timestamp to avoid conflicts
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        entity_name = f"{entity_name}_{timestamp}"
        
        # Store in memory instead
        await self.memory.store_orchestration_knowledge(
            entity_name=entity_name,
            entity_type=suggested_entity_type,
            content=content,
            metadata={
                "intended_file": intended_file_path,
                "redirected_at": datetime.utcnow().isoformat() + "Z",
                "anti_pattern_prevention": True
            },
            tags=["redirected", "anti_pattern", suggested_entity_type]
        )
        
        self.logger.info(f"Redirected markdown creation to memory: {intended_file_path} -> {entity_name}")
        return entity_name
    
    def _determine_entity_type_from_path(self, file_path: str) -> str:
        """Determine appropriate entity type from file path."""
        path_lower = file_path.lower()
        
        # Map file patterns to entity types
        type_mappings = {
            "orchestration": MemoryEntityType.ORCHESTRATION_WORKFLOW,
            "audit": MemoryEntityType.AUDIT_REPORT,
            "analysis": MemoryEntityType.AGENT_FINDINGS,
            "evidence": MemoryEntityType.DEPLOYMENT_EVIDENCE,
            "validation": MemoryEntityType.VALIDATION_PROTOCOL,
            "security": MemoryEntityType.SECURITY_VALIDATION,
            "performance": MemoryEntityType.PERFORMANCE_METRICS,
            "config": MemoryEntityType.SYSTEM_CONFIGURATION,
            "error": MemoryEntityType.ERROR_PATTERNS,
            "guide": MemoryEntityType.INTEGRATION_GUIDE,
            "troubleshoot": MemoryEntityType.TROUBLESHOOTING_GUIDE,
            "api": MemoryEntityType.API_DOCUMENTATION,
            "database": MemoryEntityType.DATABASE_SCHEMA,
            "infrastructure": MemoryEntityType.INFRASTRUCTURE_ANALYSIS,
            "pattern": MemoryEntityType.PATTERN_LIBRARY,
            "decision": MemoryEntityType.DECISION_RECORD,
            "context": MemoryEntityType.CONTEXT_PACKAGE,
            "synthesis": MemoryEntityType.SYNTHESIS_RESULT
        }
        
        # Check for pattern matches
        for pattern, entity_type in type_mappings.items():
            if pattern in path_lower:
                return entity_type
        
        # Default to agent findings
        return MemoryEntityType.AGENT_FINDINGS


async def create_memory_integration_instance(mcp_functions: Dict[str, Any]) -> MemoryServiceIntegration:
    """
    Factory function to create memory service integration instance.
    
    Args:
        mcp_functions: Dictionary of MCP function references
        
    Returns:
        Configured MemoryServiceIntegration instance
    """
    integration = MemoryServiceIntegration(mcp_functions)
    
    # Validate MCP functions are available
    required_functions = [
        "mcp__memory__create_entities",
        "mcp__memory__search_nodes",
        "mcp__memory__add_observations",
        "mcp__memory__open_nodes"
    ]
    
    missing_functions = [func for func in required_functions if func not in mcp_functions]
    if missing_functions:
        raise ValueError(f"Missing required MCP functions: {missing_functions}")
    
    return integration


# Convenience functions for common operations
async def store_orchestration_report(
    memory: MemoryServiceIntegration,
    report_name: str,
    report_content: str,
    agent_name: Optional[str] = None
) -> str:
    """Store orchestration report in memory."""
    metadata = {}
    tags = ["report", "orchestration"]
    
    if agent_name:
        metadata["agent"] = agent_name
        tags.append(agent_name)
    
    return await memory.store_orchestration_knowledge(
        entity_name=report_name,
        entity_type=MemoryEntityType.AUDIT_REPORT,
        content=report_content,
        metadata=metadata,
        tags=tags
    )


async def store_validation_results(
    memory: MemoryServiceIntegration,
    validation_name: str,
    results: Dict[str, Any]
) -> str:
    """Store validation results in memory."""
    return await memory.store_validation_evidence(
        validation_name=validation_name,
        evidence_data=results,
        success=results.get("success", False)
    )


async def search_orchestration_patterns(
    memory: MemoryServiceIntegration,
    pattern_name: str
) -> List[Dict[str, Any]]:
    """Search for orchestration patterns and solutions."""
    return await memory.search_orchestration_knowledge(
        query=pattern_name,
        entity_type=MemoryEntityType.PATTERN_LIBRARY
    )