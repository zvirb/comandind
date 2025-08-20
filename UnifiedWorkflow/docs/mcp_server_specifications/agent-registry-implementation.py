#!/usr/bin/env python3
"""
Agent Registry Implementation for Claude Agent Orchestrator MCP Server
Handles loading, validation, and management of 36 specialized agents
"""

import json
import yaml
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import re
import hashlib
from datetime import datetime

class AgentCategory(Enum):
    ORCHESTRATION = "orchestration"
    DEVELOPMENT = "development" 
    FRONTEND = "frontend"
    QUALITY = "quality"
    INFRASTRUCTURE = "infrastructure"
    DOCUMENTATION = "documentation"
    INTEGRATION = "integration"
    SECURITY = "security"
    MAINTENANCE = "maintenance"
    SYNTHESIS = "synthesis"

@dataclass
class AgentCapability:
    """Represents a specific capability of an agent"""
    name: str
    description: str
    tools_required: List[str]
    success_criteria: List[str]
    evidence_types: List[str]

@dataclass
class AgentCollaboration:
    """Defines how an agent collaborates with others"""
    works_with: List[str]
    depends_on: List[str] 
    provides_to: List[str]
    coordination_points: List[str]

@dataclass
class AgentSpecification:
    """Complete agent specification"""
    name: str
    category: AgentCategory
    description: str
    purpose: str
    capabilities: List[AgentCapability]
    tools: List[str]
    returns: List[str]
    collaboration: AgentCollaboration
    restrictions: List[str]
    examples: List[Dict[str, Any]]
    resource_pool: str
    priority: str
    expected_duration: int  # seconds
    max_context_tokens: int
    version: str
    last_updated: datetime
    validation_hash: str

class AgentRegistry:
    """Registry for managing all specialized agents"""
    
    def __init__(self, registry_path: str = None):
        self.registry_path = registry_path or os.path.expanduser("~/.claude-code/agents")
        self.agents: Dict[str, AgentSpecification] = {}
        self.categories: Dict[AgentCategory, List[str]] = {}
        self.loaded = False
        self.validation_errors: List[str] = []
        
    def load_agents(self) -> bool:
        """Load all agents from registry path"""
        try:
            registry_path = Path(self.registry_path)
            if not registry_path.exists():
                self.validation_errors.append(f"Registry path does not exist: {registry_path}")
                return False
                
            agent_files = list(registry_path.glob("*.md"))
            if not agent_files:
                self.validation_errors.append(f"No agent files found in {registry_path}")
                return False
                
            loaded_count = 0
            for agent_file in agent_files:
                try:
                    agent_spec = self._parse_agent_file(agent_file)
                    if agent_spec:
                        self.agents[agent_spec.name] = agent_spec
                        self._categorize_agent(agent_spec)
                        loaded_count += 1
                except Exception as e:
                    self.validation_errors.append(f"Error loading {agent_file}: {str(e)}")
                    
            self.loaded = loaded_count > 0
            return self.loaded
            
        except Exception as e:
            self.validation_errors.append(f"Failed to load agent registry: {str(e)}")
            return False
    
    def _parse_agent_file(self, file_path: Path) -> Optional[AgentSpecification]:
        """Parse individual agent markdown file"""
        try:
            content = file_path.read_text()
            
            # Extract YAML frontmatter
            frontmatter_match = re.match(r'^---\n(.*?)\n---\n(.*)$', content, re.DOTALL)
            if not frontmatter_match:
                raise ValueError("No YAML frontmatter found")
                
            frontmatter = yaml.safe_load(frontmatter_match.group(1))
            markdown_content = frontmatter_match.group(2)
            
            # Parse markdown content for detailed specifications
            parsed_content = self._parse_markdown_content(markdown_content)
            
            # Build agent specification
            agent_spec = AgentSpecification(
                name=frontmatter.get('name', file_path.stem),
                category=AgentCategory(self._determine_category(frontmatter.get('name', ''), parsed_content)),
                description=frontmatter.get('description', ''),
                purpose=parsed_content.get('purpose', ''),
                capabilities=self._extract_capabilities(parsed_content),
                tools=parsed_content.get('tools', []),
                returns=parsed_content.get('returns', []),
                collaboration=self._extract_collaboration(parsed_content),
                restrictions=parsed_content.get('restrictions', []),
                examples=parsed_content.get('examples', []),
                resource_pool=self._determine_resource_pool(frontmatter.get('name', '')),
                priority=self._determine_priority(frontmatter.get('name', '')),
                expected_duration=self._estimate_duration(frontmatter.get('name', '')),
                max_context_tokens=4000,  # Default
                version="1.0",
                last_updated=datetime.now(),
                validation_hash=self._generate_hash(content)
            )
            
            # Validate specification
            if self._validate_agent_spec(agent_spec):
                return agent_spec
            else:
                return None
                
        except Exception as e:
            raise ValueError(f"Failed to parse agent file {file_path}: {str(e)}")
    
    def _parse_markdown_content(self, content: str) -> Dict[str, Any]:
        """Parse markdown content for agent details"""
        parsed = {}
        
        # Extract purpose
        purpose_match = re.search(r'\*\*Purpose\*\*:?\s*(.+?)(?=\n\*\*|\n###|\n##|$)', content, re.DOTALL)
        if purpose_match:
            parsed['purpose'] = purpose_match.group(1).strip()
            
        # Extract tools
        tools_match = re.search(r'\*\*Tools\*\*:?\s*(.+?)(?=\n\*\*|\n###|\n##|$)', content, re.DOTALL)
        if tools_match:
            tools_text = tools_match.group(1)
            parsed['tools'] = [tool.strip() for tool in re.split(r'[,\n-]', tools_text) if tool.strip()]
            
        # Extract returns
        returns_match = re.search(r'\*\*Returns\*\*:?\s*(.+?)(?=\n\*\*|\n###|\n##|$)', content, re.DOTALL)
        if returns_match:
            returns_text = returns_match.group(1)
            parsed['returns'] = [ret.strip() for ret in re.split(r'[,\n-]', returns_text) if ret.strip()]
            
        # Extract restrictions
        restrictions_match = re.search(r'\*\*RESTRICTION\*\*:?\s*(.+?)(?=\n\*\*|\n###|\n##|$)', content, re.DOTALL)
        if restrictions_match:
            parsed['restrictions'] = [restrictions_match.group(1).strip()]
            
        # Extract collaboration info
        collaboration_match = re.search(r'\*\*Collaboration\*\*:?\s*(.+?)(?=\n\*\*|\n###|\n##|$)', content, re.DOTALL)
        if collaboration_match:
            parsed['collaboration_text'] = collaboration_match.group(1).strip()
            
        return parsed
    
    def _extract_capabilities(self, parsed_content: Dict) -> List[AgentCapability]:
        """Extract capabilities from parsed content"""
        capabilities = []
        
        # Extract from tools and returns as basic capabilities
        tools = parsed_content.get('tools', [])
        returns = parsed_content.get('returns', [])
        
        for i, tool in enumerate(tools[:3]):  # Limit to first 3 for brevity
            capability = AgentCapability(
                name=f"capability_{i+1}",
                description=f"Use {tool} for specialized tasks",
                tools_required=[tool],
                success_criteria=returns[:2] if returns else ["successful_execution"],
                evidence_types=["execution_output", "validation_results"]
            )
            capabilities.append(capability)
            
        return capabilities
    
    def _extract_collaboration(self, parsed_content: Dict) -> AgentCollaboration:
        """Extract collaboration patterns"""
        collab_text = parsed_content.get('collaboration_text', '')
        
        # Simple pattern extraction - in real implementation, would be more sophisticated
        works_with = re.findall(r'works with ([a-z-]+)', collab_text, re.IGNORECASE)
        depends_on = re.findall(r'depends on ([a-z-]+)', collab_text, re.IGNORECASE)
        provides_to = re.findall(r'provides to ([a-z-]+)', collab_text, re.IGNORECASE)
        
        return AgentCollaboration(
            works_with=works_with,
            depends_on=depends_on,
            provides_to=provides_to,
            coordination_points=["initialization", "validation", "completion"]
        )
    
    def _determine_category(self, agent_name: str, parsed_content: Dict) -> str:
        """Determine agent category from name and content"""
        name_lower = agent_name.lower()
        
        if any(keyword in name_lower for keyword in ['orchestrator', 'orchestrat']):
            return AgentCategory.ORCHESTRATION.value
        elif any(keyword in name_lower for keyword in ['backend', 'database', 'python', 'codebase']):
            return AgentCategory.DEVELOPMENT.value
        elif any(keyword in name_lower for keyword in ['ui', 'ux', 'frontend', 'webui', 'whimsy']):
            return AgentCategory.FRONTEND.value
        elif any(keyword in name_lower for keyword in ['test', 'security', 'validator', 'audit']):
            return AgentCategory.QUALITY.value
        elif any(keyword in name_lower for keyword in ['performance', 'deployment', 'monitoring', 'dependency', 'infrastructure']):
            return AgentCategory.INFRASTRUCTURE.value
        elif any(keyword in name_lower for keyword in ['documentation', 'document']):
            return AgentCategory.DOCUMENTATION.value
        elif any(keyword in name_lower for keyword in ['google', 'langgraph', 'ollama']):
            return AgentCategory.INTEGRATION.value
        elif any(keyword in name_lower for keyword in ['security', 'vulnerability', 'quality']):
            return AgentCategory.SECURITY.value
        elif any(keyword in name_lower for keyword in ['janitor', 'data']):
            return AgentCategory.MAINTENANCE.value
        elif any(keyword in name_lower for keyword in ['nexus', 'synthesis']):
            return AgentCategory.SYNTHESIS.value
        else:
            return AgentCategory.DEVELOPMENT.value  # Default
    
    def _determine_resource_pool(self, agent_name: str) -> str:
        """Determine resource pool based on agent type"""
        name_lower = agent_name.lower()
        
        if any(keyword in name_lower for keyword in ['performance', 'codebase', 'test']):
            return "cpu_intensive"
        elif any(keyword in name_lower for keyword in ['database', 'documentation', 'dependency']):
            return "io_intensive"
        elif any(keyword in name_lower for keyword in ['security', 'monitoring', 'validator']):
            return "network_intensive"
        elif any(keyword in name_lower for keyword in ['nexus', 'synthesis', 'orchestrator']):
            return "memory_intensive"
        else:
            return "general"
    
    def _determine_priority(self, agent_name: str) -> str:
        """Determine agent priority"""
        name_lower = agent_name.lower()
        
        if any(keyword in name_lower for keyword in ['security', 'orchestrator']):
            return "critical"
        elif any(keyword in name_lower for keyword in ['backend', 'database', 'performance']):
            return "high"
        else:
            return "medium"
    
    def _estimate_duration(self, agent_name: str) -> int:
        """Estimate execution duration in seconds"""
        name_lower = agent_name.lower()
        
        if any(keyword in name_lower for keyword in ['orchestrator', 'synthesis']):
            return 300  # 5 minutes
        elif any(keyword in name_lower for keyword in ['security', 'performance', 'test']):
            return 240  # 4 minutes
        elif any(keyword in name_lower for keyword in ['backend', 'database']):
            return 180  # 3 minutes
        else:
            return 120  # 2 minutes
    
    def _generate_hash(self, content: str) -> str:
        """Generate validation hash for content"""
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _validate_agent_spec(self, spec: AgentSpecification) -> bool:
        """Validate agent specification"""
        if not spec.name or not spec.description:
            self.validation_errors.append(f"Agent {spec.name} missing required fields")
            return False
        
        if not spec.capabilities:
            self.validation_errors.append(f"Agent {spec.name} has no capabilities defined")
            return False
            
        return True
    
    def _categorize_agent(self, agent: AgentSpecification):
        """Add agent to category index"""
        if agent.category not in self.categories:
            self.categories[agent.category] = []
        self.categories[agent.category].append(agent.name)
    
    # Public API methods
    
    def get_agent(self, name: str) -> Optional[AgentSpecification]:
        """Get agent specification by name"""
        return self.agents.get(name)
    
    def list_agents(self, category: Optional[AgentCategory] = None, 
                   capability_filter: Optional[List[str]] = None) -> List[str]:
        """List agents with optional filtering"""
        if category:
            return self.categories.get(category, [])
        
        if capability_filter:
            filtered_agents = []
            for agent_name, agent in self.agents.items():
                agent_tools = [cap.name for cap in agent.capabilities]
                if any(cap in agent_tools for cap in capability_filter):
                    filtered_agents.append(agent_name)
            return filtered_agents
        
        return list(self.agents.keys())
    
    def get_agent_capabilities(self, name: str) -> List[AgentCapability]:
        """Get agent capabilities"""
        agent = self.get_agent(name)
        return agent.capabilities if agent else []
    
    def get_collaboration_graph(self) -> Dict[str, Dict[str, List[str]]]:
        """Get complete collaboration graph"""
        graph = {}
        for name, agent in self.agents.items():
            graph[name] = {
                'works_with': agent.collaboration.works_with,
                'depends_on': agent.collaboration.depends_on,
                'provides_to': agent.collaboration.provides_to
            }
        return graph
    
    def validate_parallel_execution(self, agent_names: List[str]) -> Tuple[bool, List[str]]:
        """Validate if agents can execute in parallel"""
        issues = []
        
        # Check resource pool conflicts
        resource_pools = {}
        for name in agent_names:
            agent = self.get_agent(name)
            if not agent:
                issues.append(f"Agent {name} not found")
                continue
                
            pool = agent.resource_pool
            if pool not in resource_pools:
                resource_pools[pool] = []
            resource_pools[pool].append(name)
        
        # Check resource limits (simplified)
        for pool, agents in resource_pools.items():
            if pool == "cpu_intensive" and len(agents) > 2:
                issues.append(f"Too many CPU intensive agents: {agents}")
            elif pool == "memory_intensive" and len(agents) > 2:
                issues.append(f"Too many memory intensive agents: {agents}")
        
        # Check for circular dependencies
        for name in agent_names:
            agent = self.get_agent(name)
            if not agent:
                continue
            for dep in agent.collaboration.depends_on:
                if dep in agent_names:
                    dep_agent = self.get_agent(dep)
                    if dep_agent and name in dep_agent.collaboration.depends_on:
                        issues.append(f"Circular dependency: {name} <-> {dep}")
        
        return len(issues) == 0, issues
    
    def get_optimal_execution_order(self, agent_names: List[str]) -> List[List[str]]:
        """Get optimal execution order considering dependencies"""
        # Simplified topological sort
        remaining = set(agent_names)
        execution_waves = []
        
        while remaining:
            wave = []
            for name in list(remaining):
                agent = self.get_agent(name)
                if not agent:
                    wave.append(name)
                    continue
                    
                # Check if dependencies are satisfied
                deps_satisfied = all(
                    dep not in remaining for dep in agent.collaboration.depends_on
                    if dep in agent_names
                )
                
                if deps_satisfied:
                    wave.append(name)
            
            if not wave:  # Circular dependency detected
                wave = list(remaining)  # Add all remaining
            
            execution_waves.append(wave)
            remaining.difference_update(wave)
            
        return execution_waves
    
    def export_registry_summary(self) -> Dict[str, Any]:
        """Export registry summary for debugging"""
        return {
            "total_agents": len(self.agents),
            "categories": {cat.value: len(agents) for cat, agents in self.categories.items()},
            "validation_errors": self.validation_errors,
            "resource_pools": {
                pool: [name for name, agent in self.agents.items() if agent.resource_pool == pool]
                for pool in set(agent.resource_pool for agent in self.agents.values())
            },
            "loaded": self.loaded,
            "registry_path": self.registry_path
        }

# Registry instance for MCP server
registry = AgentRegistry()

# Load agents on import
if not registry.load_agents():
    print(f"Warning: Failed to load agent registry: {registry.validation_errors}")

def get_registry() -> AgentRegistry:
    """Get the global registry instance"""
    return registry