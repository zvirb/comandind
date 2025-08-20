"""Context Package Generator with intelligent <4000 token limit enforcement.

This module generates optimized context packages for agents, ensuring they receive
relevant information within strict token limits while maintaining semantic coherence.
"""

import asyncio
import hashlib
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

import structlog
from config import AGENT_CAPABILITIES

logger = structlog.get_logger(__name__)


class CompressionLevel(str, Enum):
    """Context compression levels."""
    NONE = "none"
    LIGHT = "light"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class ContextSection(str, Enum):
    """Context package sections."""
    TASK_DESCRIPTION = "task_description"
    RELEVANT_CONTEXT = "relevant_context"
    SUCCESS_CRITERIA = "success_criteria"
    DEPENDENCIES = "dependencies"
    HISTORICAL_DATA = "historical_data"
    AGENT_SPECIFIC = "agent_specific"
    WORKFLOW_METADATA = "workflow_metadata"
    RELATED_TASKS = "related_tasks"
    CODE_CONTEXT = "code_context"
    PERFORMANCE_HINTS = "performance_hints"


@dataclass
class ContextPackage:
    """Represents a generated context package for an agent."""
    package_id: str
    agent_name: str
    workflow_id: str
    token_count: int
    sections: Dict[str, Any] = field(default_factory=dict)
    compression_level: CompressionLevel = CompressionLevel.MODERATE
    generated_at: float = field(default_factory=time.time)
    cache_key: Optional[str] = None
    priority_score: float = 1.0
    
    def to_prompt_string(self) -> str:
        """Convert context package to prompt string for agent."""
        prompt_parts = []
        
        # Header
        prompt_parts.append(f"# Agent Context Package")
        prompt_parts.append(f"Agent: {self.agent_name}")
        prompt_parts.append(f"Workflow: {self.workflow_id}")
        prompt_parts.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.generated_at))}")
        prompt_parts.append("")
        
        # Sections
        section_order = [
            ContextSection.TASK_DESCRIPTION,
            ContextSection.SUCCESS_CRITERIA,
            ContextSection.DEPENDENCIES,
            ContextSection.RELEVANT_CONTEXT,
            ContextSection.AGENT_SPECIFIC,
            ContextSection.CODE_CONTEXT,
            ContextSection.RELATED_TASKS,
            ContextSection.HISTORICAL_DATA,
            ContextSection.PERFORMANCE_HINTS,
            ContextSection.WORKFLOW_METADATA
        ]
        
        for section in section_order:
            if section in self.sections and self.sections[section]:
                prompt_parts.append(f"## {section.replace('_', ' ').title()}")
                
                section_data = self.sections[section]
                if isinstance(section_data, dict):
                    prompt_parts.append(json.dumps(section_data, indent=2))
                elif isinstance(section_data, list):
                    for item in section_data:
                        prompt_parts.append(f"- {item}")
                else:
                    prompt_parts.append(str(section_data))
                
                prompt_parts.append("")
        
        return "\n".join(prompt_parts)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get package summary information."""
        return {
            "package_id": self.package_id,
            "agent_name": self.agent_name,
            "workflow_id": self.workflow_id,
            "token_count": self.token_count,
            "section_count": len(self.sections),
            "compression_level": self.compression_level,
            "priority_score": self.priority_score,
            "cache_key": self.cache_key
        }


class ContextPackageGenerator:
    """Generates optimized context packages for agents with token limit enforcement."""
    
    def __init__(
        self,
        max_tokens: int = 4000,
        redis_service=None,
        cache_ttl_seconds: int = 1800  # 30 minutes
    ):
        self.max_tokens = max_tokens
        self.redis_service = redis_service
        self.cache_ttl_seconds = cache_ttl_seconds
        
        # Token estimation coefficients
        self.char_to_token_ratio = 4.0  # Rough estimate: 4 chars per token
        self.compression_ratios = {
            CompressionLevel.NONE: 1.0,
            CompressionLevel.LIGHT: 0.9,
            CompressionLevel.MODERATE: 0.8,
            CompressionLevel.AGGRESSIVE: 0.6
        }
        
        # Context prioritization weights
        self.section_weights = {
            ContextSection.TASK_DESCRIPTION: 1.0,
            ContextSection.SUCCESS_CRITERIA: 0.9,
            ContextSection.DEPENDENCIES: 0.8,
            ContextSection.RELEVANT_CONTEXT: 0.7,
            ContextSection.AGENT_SPECIFIC: 0.8,
            ContextSection.CODE_CONTEXT: 0.6,
            ContextSection.RELATED_TASKS: 0.5,
            ContextSection.HISTORICAL_DATA: 0.4,
            ContextSection.PERFORMANCE_HINTS: 0.3,
            ContextSection.WORKFLOW_METADATA: 0.2
        }
        
        # Performance metrics
        self.generation_metrics = {
            "total_packages": 0,
            "cache_hits": 0,
            "compression_applied": 0,
            "avg_generation_time": 0.0
        }
    
    async def generate_context_package(
        self,
        agent_name: str,
        workflow_id: str,
        task_context: Dict[str, Any],
        requirements: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate optimized context package for an agent."""
        start_time = time.time()
        
        try:
            logger.info(
                "Generating context package",
                agent_name=agent_name,
                workflow_id=workflow_id
            )
            
            # Parse requirements
            requirements = requirements or {}
            max_tokens = requirements.get("max_tokens", self.max_tokens)
            compression_level = CompressionLevel(requirements.get("compression_level", "moderate"))
            include_sections = requirements.get("include_sections", list(ContextSection))
            exclude_sections = requirements.get("exclude_sections", [])
            prioritize_recent = requirements.get("prioritize_recent", True)
            
            # Generate cache key
            cache_key = self._generate_cache_key(agent_name, workflow_id, task_context, requirements)
            
            # Check cache first
            if self.redis_service and cache_key:
                cached_package = await self._get_cached_package(cache_key)
                if cached_package:
                    self.generation_metrics["cache_hits"] += 1
                    logger.info("Using cached context package", cache_key=cache_key)
                    return cached_package.package_id
            
            # Create package ID
            package_id = f"ctx_{workflow_id}_{agent_name}_{int(time.time())}"
            
            # Gather context sections
            raw_sections = await self._gather_context_sections(
                agent_name=agent_name,
                workflow_id=workflow_id,
                task_context=task_context,
                include_sections=include_sections,
                exclude_sections=exclude_sections,
                prioritize_recent=prioritize_recent
            )
            
            # Optimize and compress sections to fit token limit
            optimized_sections = await self._optimize_sections_for_token_limit(
                raw_sections=raw_sections,
                max_tokens=max_tokens,
                compression_level=compression_level,
                agent_name=agent_name
            )
            
            # Calculate final token count
            final_token_count = self._estimate_token_count(optimized_sections)
            
            # Create context package
            package = ContextPackage(
                package_id=package_id,
                agent_name=agent_name,
                workflow_id=workflow_id,
                token_count=final_token_count,
                sections=optimized_sections,
                compression_level=compression_level,
                cache_key=cache_key
            )
            
            # Cache the package if Redis is available
            if self.redis_service:
                await self._cache_package(package)
            
            # Update metrics
            generation_time = time.time() - start_time
            self.generation_metrics["total_packages"] += 1
            self.generation_metrics["avg_generation_time"] = (
                (self.generation_metrics["avg_generation_time"] * (self.generation_metrics["total_packages"] - 1) + generation_time) /
                self.generation_metrics["total_packages"]
            )
            
            logger.info(
                "Context package generated",
                package_id=package_id,
                agent_name=agent_name,
                token_count=final_token_count,
                generation_time_ms=round(generation_time * 1000, 2)
            )
            
            return package_id
            
        except Exception as e:
            logger.error(
                "Context package generation failed",
                agent_name=agent_name,
                workflow_id=workflow_id,
                error=str(e)
            )
            raise
    
    async def get_context_package(self, package_id: str) -> Optional[ContextPackage]:
        """Retrieve a context package by ID."""
        if self.redis_service:
            package_data = await self.redis_service.get_json(f"context_package:{package_id}")
            if package_data:
                return ContextPackage(**package_data)
        return None
    
    async def get_package_prompt(self, package_id: str) -> Optional[str]:
        """Get the prompt string for a context package."""
        package = await self.get_context_package(package_id)
        if package:
            return package.to_prompt_string()
        return None
    
    async def invalidate_cache(self, cache_pattern: str = None) -> int:
        """Invalidate cached context packages."""
        if not self.redis_service:
            return 0
        
        if cache_pattern:
            keys = await self.redis_service.scan_keys(f"context_package_cache:{cache_pattern}*")
        else:
            keys = await self.redis_service.scan_keys("context_package_cache:*")
        
        deleted_count = 0
        for key in keys:
            await self.redis_service.delete(key)
            deleted_count += 1
        
        logger.info("Cache invalidated", deleted_keys=deleted_count, pattern=cache_pattern)
        return deleted_count
    
    async def get_generation_metrics(self) -> Dict[str, Any]:
        """Get context package generation metrics."""
        cache_hit_rate = (
            self.generation_metrics["cache_hits"] / self.generation_metrics["total_packages"]
            if self.generation_metrics["total_packages"] > 0 else 0
        )
        
        return {
            **self.generation_metrics,
            "cache_hit_rate": cache_hit_rate,
            "max_tokens": self.max_tokens,
            "cache_ttl_seconds": self.cache_ttl_seconds
        }
    
    # Private helper methods
    
    def _generate_cache_key(
        self,
        agent_name: str,
        workflow_id: str,
        task_context: Dict[str, Any],
        requirements: Dict[str, Any]
    ) -> str:
        """Generate cache key for context package."""
        cache_data = {
            "agent": agent_name,
            "workflow": workflow_id,
            "context": task_context,
            "requirements": requirements
        }
        
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    async def _get_cached_package(self, cache_key: str) -> Optional[ContextPackage]:
        """Retrieve cached context package."""
        if not self.redis_service:
            return None
        
        package_data = await self.redis_service.get_json(f"context_package_cache:{cache_key}")
        if package_data:
            return ContextPackage(**package_data)
        
        return None
    
    async def _cache_package(self, package: ContextPackage) -> None:
        """Cache context package."""
        if not self.redis_service or not package.cache_key:
            return
        
        # Cache the package data
        await self.redis_service.set_json(
            key=f"context_package_cache:{package.cache_key}",
            value=package.__dict__,
            expiry_seconds=self.cache_ttl_seconds
        )
        
        # Also store by package ID
        await self.redis_service.set_json(
            key=f"context_package:{package.package_id}",
            value=package.__dict__,
            expiry_seconds=self.cache_ttl_seconds
        )
    
    async def _gather_context_sections(
        self,
        agent_name: str,
        workflow_id: str,
        task_context: Dict[str, Any],
        include_sections: List[str],
        exclude_sections: List[str],
        prioritize_recent: bool
    ) -> Dict[str, Any]:
        """Gather all relevant context sections."""
        sections = {}
        
        # Task Description (always included)
        if ContextSection.TASK_DESCRIPTION in include_sections:
            sections[ContextSection.TASK_DESCRIPTION] = await self._build_task_description(
                agent_name, workflow_id, task_context
            )
        
        # Success Criteria
        if ContextSection.SUCCESS_CRITERIA in include_sections:
            sections[ContextSection.SUCCESS_CRITERIA] = await self._build_success_criteria(
                agent_name, workflow_id, task_context
            )
        
        # Dependencies
        if ContextSection.DEPENDENCIES in include_sections:
            sections[ContextSection.DEPENDENCIES] = await self._build_dependencies(
                agent_name, workflow_id, task_context
            )
        
        # Relevant Context
        if ContextSection.RELEVANT_CONTEXT in include_sections:
            sections[ContextSection.RELEVANT_CONTEXT] = await self._build_relevant_context(
                agent_name, workflow_id, task_context, prioritize_recent
            )
        
        # Agent-Specific Context
        if ContextSection.AGENT_SPECIFIC in include_sections:
            sections[ContextSection.AGENT_SPECIFIC] = await self._build_agent_specific_context(
                agent_name, workflow_id, task_context
            )
        
        # Code Context
        if ContextSection.CODE_CONTEXT in include_sections:
            sections[ContextSection.CODE_CONTEXT] = await self._build_code_context(
                agent_name, workflow_id, task_context
            )
        
        # Related Tasks
        if ContextSection.RELATED_TASKS in include_sections:
            sections[ContextSection.RELATED_TASKS] = await self._build_related_tasks(
                agent_name, workflow_id, task_context
            )
        
        # Historical Data
        if ContextSection.HISTORICAL_DATA in include_sections:
            sections[ContextSection.HISTORICAL_DATA] = await self._build_historical_data(
                agent_name, workflow_id, task_context, prioritize_recent
            )
        
        # Performance Hints
        if ContextSection.PERFORMANCE_HINTS in include_sections:
            sections[ContextSection.PERFORMANCE_HINTS] = await self._build_performance_hints(
                agent_name, workflow_id, task_context
            )
        
        # Workflow Metadata
        if ContextSection.WORKFLOW_METADATA in include_sections:
            sections[ContextSection.WORKFLOW_METADATA] = await self._build_workflow_metadata(
                agent_name, workflow_id, task_context
            )
        
        # Remove excluded sections
        for section in exclude_sections:
            sections.pop(section, None)
        
        return sections
    
    async def _optimize_sections_for_token_limit(
        self,
        raw_sections: Dict[str, Any],
        max_tokens: int,
        compression_level: CompressionLevel,
        agent_name: str
    ) -> Dict[str, Any]:
        """Optimize context sections to fit within token limit."""
        # Initial token estimate
        total_tokens = self._estimate_token_count(raw_sections)
        
        if total_tokens <= max_tokens:
            # Already within limit
            return raw_sections
        
        logger.info(
            "Context compression required",
            agent_name=agent_name,
            initial_tokens=total_tokens,
            max_tokens=max_tokens,
            compression_level=compression_level
        )
        
        self.generation_metrics["compression_applied"] += 1
        
        # Apply compression
        compressed_sections = {}
        available_tokens = max_tokens
        
        # Sort sections by priority (highest first)
        section_priority = [
            (section, content, self.section_weights.get(section, 0.5))
            for section, content in raw_sections.items()
        ]
        section_priority.sort(key=lambda x: x[2], reverse=True)
        
        for section, content, weight in section_priority:
            # Estimate tokens for this section
            section_tokens = self._estimate_token_count({section: content})
            
            if section_tokens <= available_tokens:
                # Include full section
                compressed_sections[section] = content
                available_tokens -= section_tokens
            else:
                # Compress section to fit
                if available_tokens > 100:  # Minimum viable section size
                    compressed_content = await self._compress_section_content(
                        content=content,
                        target_tokens=available_tokens,
                        compression_level=compression_level,
                        section_type=section
                    )
                    
                    if compressed_content:
                        compressed_sections[section] = compressed_content
                        available_tokens -= self._estimate_token_count({section: compressed_content})
                
                # No more space for additional sections
                if available_tokens < 100:
                    break
        
        final_tokens = self._estimate_token_count(compressed_sections)
        
        logger.info(
            "Context compression completed",
            agent_name=agent_name,
            original_tokens=total_tokens,
            compressed_tokens=final_tokens,
            compression_ratio=final_tokens / total_tokens if total_tokens > 0 else 0,
            sections_included=len(compressed_sections)
        )
        
        return compressed_sections
    
    def _estimate_token_count(self, content: Any) -> int:
        """Estimate token count for content."""
        if isinstance(content, dict):
            content_str = json.dumps(content, indent=2)
        elif isinstance(content, list):
            content_str = "\n".join(str(item) for item in content)
        else:
            content_str = str(content)
        
        # Rough token estimation: ~4 characters per token
        return max(1, int(len(content_str) / self.char_to_token_ratio))
    
    async def _compress_section_content(
        self,
        content: Any,
        target_tokens: int,
        compression_level: CompressionLevel,
        section_type: str
    ) -> Any:
        """Compress section content to fit target token count."""
        compression_ratio = self.compression_ratios[compression_level]
        
        if isinstance(content, dict):
            return await self._compress_dict_content(content, target_tokens, compression_ratio)
        elif isinstance(content, list):
            return await self._compress_list_content(content, target_tokens, compression_ratio)
        elif isinstance(content, str):
            return await self._compress_string_content(content, target_tokens, compression_ratio)
        else:
            # For other types, just truncate string representation
            content_str = str(content)
            target_chars = int(target_tokens * self.char_to_token_ratio * compression_ratio)
            return content_str[:target_chars] + "..." if len(content_str) > target_chars else content_str
    
    async def _compress_dict_content(
        self,
        content: Dict[str, Any],
        target_tokens: int,
        compression_ratio: float
    ) -> Dict[str, Any]:
        """Compress dictionary content."""
        compressed = {}
        available_tokens = int(target_tokens * compression_ratio)
        
        # Sort by key importance (heuristic)
        important_keys = ["description", "requirements", "criteria", "context", "data"]
        
        for key, value in content.items():
            value_tokens = self._estimate_token_count(value)
            
            if value_tokens <= available_tokens:
                compressed[key] = value
                available_tokens -= value_tokens
            elif available_tokens > 50 and key.lower() in important_keys:
                # Compress important values
                compressed_value = await self._compress_section_content(
                    value, available_tokens, CompressionLevel.MODERATE, key
                )
                if compressed_value:
                    compressed[key] = compressed_value
                    available_tokens -= self._estimate_token_count(compressed_value)
        
        return compressed
    
    async def _compress_list_content(
        self,
        content: List[Any],
        target_tokens: int,
        compression_ratio: float
    ) -> List[Any]:
        """Compress list content."""
        compressed = []
        available_tokens = int(target_tokens * compression_ratio)
        
        for item in content:
            item_tokens = self._estimate_token_count(item)
            
            if item_tokens <= available_tokens:
                compressed.append(item)
                available_tokens -= item_tokens
            else:
                break
        
        return compressed
    
    async def _compress_string_content(
        self,
        content: str,
        target_tokens: int,
        compression_ratio: float
    ) -> str:
        """Compress string content using intelligent truncation."""
        target_chars = int(target_tokens * self.char_to_token_ratio * compression_ratio)
        
        if len(content) <= target_chars:
            return content
        
        # Try to truncate at sentence boundaries
        sentences = content.split('. ')
        compressed = ""
        
        for sentence in sentences:
            if len(compressed + sentence) <= target_chars - 3:  # Reserve space for "..."
                compressed += sentence + ". "
            else:
                break
        
        if compressed:
            return compressed.rstrip() + "..."
        else:
            # Fallback to character truncation
            return content[:target_chars] + "..."
    
    # Context section builders (simplified implementations)
    
    async def _build_task_description(self, agent_name: str, workflow_id: str, task_context: Dict[str, Any]) -> str:
        """Build task description section."""
        agent_caps = AGENT_CAPABILITIES.get(agent_name, {})
        capabilities = agent_caps.get("capabilities", [])
        
        description = f"Agent {agent_name} assigned to workflow {workflow_id}.\n"
        description += f"Agent capabilities: {', '.join(capabilities)}\n"
        description += f"Task context: {json.dumps(task_context, indent=2)}"
        
        return description
    
    async def _build_success_criteria(self, agent_name: str, workflow_id: str, task_context: Dict[str, Any]) -> Dict[str, Any]:
        """Build success criteria section."""
        return {
            "completion_required": True,
            "quality_threshold": 0.85,
            "output_format": "structured_result",
            "validation_required": task_context.get("validate_results", True)
        }
    
    async def _build_dependencies(self, agent_name: str, workflow_id: str, task_context: Dict[str, Any]) -> List[str]:
        """Build dependencies section."""
        agent_caps = AGENT_CAPABILITIES.get(agent_name, {})
        return agent_caps.get("dependencies", [])
    
    async def _build_relevant_context(self, agent_name: str, workflow_id: str, task_context: Dict[str, Any], prioritize_recent: bool) -> Dict[str, Any]:
        """Build relevant context section."""
        return {
            "workflow_context": task_context,
            "prioritize_recent": prioritize_recent,
            "context_timestamp": time.time()
        }
    
    async def _build_agent_specific_context(self, agent_name: str, workflow_id: str, task_context: Dict[str, Any]) -> Dict[str, Any]:
        """Build agent-specific context section."""
        agent_caps = AGENT_CAPABILITIES.get(agent_name, {})
        
        return {
            "agent_category": agent_caps.get("category", "general"),
            "resource_requirements": agent_caps.get("resource_requirements", {}),
            "max_concurrent": agent_caps.get("max_concurrent", 1),
            "typical_duration": agent_caps.get("typical_duration", 300)
        }
    
    async def _build_code_context(self, agent_name: str, workflow_id: str, task_context: Dict[str, Any]) -> Dict[str, Any]:
        """Build code context section."""
        return {
            "target_files": task_context.get("target_files", []),
            "code_patterns": task_context.get("code_patterns", []),
            "language_context": task_context.get("language", "python")
        }
    
    async def _build_related_tasks(self, agent_name: str, workflow_id: str, task_context: Dict[str, Any]) -> List[str]:
        """Build related tasks section."""
        # This would query for related tasks in real implementation
        return []
    
    async def _build_historical_data(self, agent_name: str, workflow_id: str, task_context: Dict[str, Any], prioritize_recent: bool) -> Dict[str, Any]:
        """Build historical data section."""
        return {
            "previous_executions": 0,
            "success_rate": 1.0,
            "avg_execution_time": 300,
            "common_issues": []
        }
    
    async def _build_performance_hints(self, agent_name: str, workflow_id: str, task_context: Dict[str, Any]) -> List[str]:
        """Build performance hints section."""
        agent_caps = AGENT_CAPABILITIES.get(agent_name, {})
        
        hints = []
        if agent_caps.get("resource_requirements", {}).get("cpu", 1) > 1:
            hints.append("CPU-intensive agent - consider parallel processing")
        
        if agent_caps.get("typical_duration", 300) > 600:
            hints.append("Long-running agent - implement progress tracking")
        
        return hints
    
    async def _build_workflow_metadata(self, agent_name: str, workflow_id: str, task_context: Dict[str, Any]) -> Dict[str, Any]:
        """Build workflow metadata section."""
        return {
            "workflow_id": workflow_id,
            "agent_name": agent_name,
            "generated_at": time.time(),
            "version": "1.0.0"
        }