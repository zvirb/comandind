#!/usr/bin/env python3
"""
Context Package Management System for Claude Agent Orchestrator MCP Server
Handles intelligent context compression, package creation, and agent-specific context distribution
"""

import json
import tiktoken
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import re
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class PackageType(Enum):
    STRATEGIC = "strategic"
    TECHNICAL = "technical" 
    FRONTEND = "frontend"
    SECURITY = "security"
    PERFORMANCE = "performance"
    DATABASE = "database"
    INTEGRATION = "integration"
    DOCUMENTATION = "documentation"

class CompressionStrategy(Enum):
    SEMANTIC_PRESERVE = "semantic_preserve"
    HIERARCHICAL_SUMMARY = "hierarchical_summary"
    CRITICAL_INFO_ONLY = "critical_info_only"
    AGENT_SPECIFIC = "agent_specific"

@dataclass
class ContextMetadata:
    """Metadata for context packages"""
    package_id: str
    target_agent: str
    package_type: PackageType
    compression_strategy: CompressionStrategy
    original_tokens: int
    final_tokens: int
    compression_ratio: float
    parallel_agents: List[str]
    synchronization_points: List[str]
    handoff_requirements: Dict[str, Any]
    priority: str
    created_at: datetime
    expires_at: Optional[datetime]

@dataclass
class ContextPackage:
    """Complete context package for an agent"""
    metadata: ContextMetadata
    content: str
    coordination_instructions: str
    success_criteria: List[str]
    evidence_requirements: Dict[str, Any]
    validation_hash: str

class ContextPackageManager:
    """Manages context package creation, compression, and distribution"""
    
    def __init__(self, 
                 cache_dir: str = "context_cache",
                 max_package_tokens: int = 4000,
                 default_compression_ratio: float = 0.6):
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        self.max_package_tokens = max_package_tokens
        self.default_compression_ratio = default_compression_ratio
        
        # Initialize tokenizer
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except:
            self.tokenizer = None
            logger.warning("Tokenizer not available, using character-based estimation")
        
        # Agent-specific compression templates
        self.agent_templates = self._init_agent_templates()
        
        # Context package cache
        self.package_cache: Dict[str, ContextPackage] = {}
    
    def _init_agent_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize agent-specific context templates"""
        return {
            # Orchestration Agents
            "project-orchestrator": {
                "focus_areas": ["requirements", "strategy", "coordination", "risks"],
                "exclude_sections": ["implementation_details", "code_snippets"],
                "priority_keywords": ["objective", "scope", "timeline", "dependencies"],
                "max_tokens": 3000
            },
            "enhanced-nexus-synthesis-agent": {
                "focus_areas": ["patterns", "integration", "synthesis", "coordination"],
                "exclude_sections": ["low_level_details", "specific_implementations"],
                "priority_keywords": ["synthesis", "integration", "coordination", "strategy"],
                "max_tokens": 4000
            },
            
            # Development Agents
            "backend-gateway-expert": {
                "focus_areas": ["api_errors", "server_logs", "database_issues", "authentication"],
                "exclude_sections": ["frontend_details", "ui_specifications"],
                "priority_keywords": ["api", "server", "error", "500", "database", "auth"],
                "max_tokens": 4000
            },
            "schema-database-expert": {
                "focus_areas": ["database", "schema", "queries", "performance", "relationships"],
                "exclude_sections": ["frontend_logic", "ui_components"],
                "priority_keywords": ["database", "schema", "query", "table", "index", "migration"],
                "max_tokens": 3500
            },
            
            # Frontend Agents  
            "webui-architect": {
                "focus_areas": ["ui_components", "frontend_errors", "user_interface", "styling"],
                "exclude_sections": ["backend_implementation", "database_details"],
                "priority_keywords": ["ui", "component", "frontend", "react", "css", "javascript"],
                "max_tokens": 3000
            },
            "frictionless-ux-architect": {
                "focus_areas": ["user_experience", "usability", "user_flows", "accessibility"],
                "exclude_sections": ["technical_implementation", "server_details"],
                "priority_keywords": ["ux", "user", "flow", "experience", "accessibility", "usability"],
                "max_tokens": 3000
            },
            
            # Quality Assurance Agents
            "security-validator": {
                "focus_areas": ["security_vulnerabilities", "authentication", "authorization", "ssl"],
                "exclude_sections": ["ui_styling", "performance_optimization"],
                "priority_keywords": ["security", "auth", "ssl", "vulnerability", "csrf", "jwt"],
                "max_tokens": 4000
            },
            "production-endpoint-validator": {
                "focus_areas": ["endpoint_testing", "ssl_validation", "production_health"],
                "exclude_sections": ["development_setup", "local_environment"],
                "priority_keywords": ["endpoint", "production", "ssl", "https", "validation", "health"],
                "max_tokens": 3500
            },
            
            # Infrastructure Agents
            "performance-profiler": {
                "focus_areas": ["performance_metrics", "bottlenecks", "optimization", "monitoring"],
                "exclude_sections": ["ui_design", "user_flows"],
                "priority_keywords": ["performance", "optimization", "metrics", "bottleneck", "latency"],
                "max_tokens": 3500
            },
            "monitoring-analyst": {
                "focus_areas": ["system_monitoring", "alerts", "metrics", "logs"],
                "exclude_sections": ["design_specifications", "user_stories"],
                "priority_keywords": ["monitoring", "metrics", "alerts", "logs", "observability"],
                "max_tokens": 3000
            }
        }
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # Rough estimation: 1 token ≈ 4 characters
            return len(text) // 4
    
    def _generate_package_id(self, target_agent: str, package_type: str) -> str:
        """Generate unique package ID"""
        timestamp = str(int(datetime.now().timestamp() * 1000))
        content_hash = hashlib.md5(f"{target_agent}{package_type}{timestamp}".encode()).hexdigest()[:8]
        return f"pkg_{target_agent}_{package_type}_{timestamp}_{content_hash}"
    
    async def create_context_package(self,
                                   target_agent: str,
                                   full_context: str,
                                   package_type: str,
                                   coordination_metadata: Optional[Dict] = None,
                                   max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """Create compressed context package for specific agent"""
        
        try:
            # Validate inputs
            if target_agent not in self.agent_templates:
                logger.warning(f"No template found for agent {target_agent}, using default")
                agent_template = {"max_tokens": max_tokens or self.max_package_tokens}
            else:
                agent_template = self.agent_templates[target_agent]
            
            # Determine compression strategy
            package_type_enum = PackageType(package_type)
            compression_strategy = self._determine_compression_strategy(target_agent, package_type_enum)
            
            # Set token limits
            target_tokens = max_tokens or agent_template.get("max_tokens", self.max_package_tokens)
            original_tokens = self._count_tokens(full_context)
            
            # Apply agent-specific compression
            compressed_content = await self._compress_for_agent(
                full_context, target_agent, target_tokens, agent_template
            )
            
            final_tokens = self._count_tokens(compressed_content)
            compression_ratio = final_tokens / original_tokens if original_tokens > 0 else 1.0
            
            # Create coordination instructions
            coordination_instructions = self._create_coordination_instructions(
                target_agent, coordination_metadata or {}
            )
            
            # Generate success criteria
            success_criteria = self._generate_success_criteria(target_agent, package_type)
            
            # Create evidence requirements
            evidence_requirements = self._create_evidence_requirements(target_agent)
            
            # Generate package ID and metadata
            package_id = self._generate_package_id(target_agent, package_type)
            
            metadata = ContextMetadata(
                package_id=package_id,
                target_agent=target_agent,
                package_type=package_type_enum,
                compression_strategy=compression_strategy,
                original_tokens=original_tokens,
                final_tokens=final_tokens,
                compression_ratio=compression_ratio,
                parallel_agents=coordination_metadata.get("parallel_agents", []) if coordination_metadata else [],
                synchronization_points=coordination_metadata.get("synchronization_points", []) if coordination_metadata else [],
                handoff_requirements=coordination_metadata.get("handoff_requirements", {}) if coordination_metadata else {},
                priority=self._determine_priority(target_agent),
                created_at=datetime.now(),
                expires_at=None
            )
            
            # Create complete package
            context_package = ContextPackage(
                metadata=metadata,
                content=compressed_content,
                coordination_instructions=coordination_instructions,
                success_criteria=success_criteria,
                evidence_requirements=evidence_requirements,
                validation_hash=hashlib.sha256(compressed_content.encode()).hexdigest()[:16]
            )
            
            # Cache the package
            self.package_cache[package_id] = context_package
            
            # Save to disk
            await self._save_package_to_disk(context_package)
            
            return {
                "success": True,
                "package_id": package_id,
                "target_agent": target_agent,
                "package_type": package_type,
                "original_tokens": original_tokens,
                "final_tokens": final_tokens,
                "compression_ratio": compression_ratio,
                "compression_strategy": compression_strategy.value,
                "coordination_instructions": coordination_instructions,
                "success_criteria": success_criteria,
                "evidence_requirements": evidence_requirements,
                "package_content": compressed_content
            }
            
        except Exception as e:
            logger.error(f"Error creating context package: {str(e)}")
            return {"error": f"Failed to create context package: {str(e)}"}
    
    def _determine_compression_strategy(self, target_agent: str, package_type: PackageType) -> CompressionStrategy:
        """Determine optimal compression strategy"""
        
        # Agent-specific strategies
        if target_agent in ["enhanced-nexus-synthesis-agent", "nexus-synthesis-agent"]:
            return CompressionStrategy.HIERARCHICAL_SUMMARY
        elif target_agent in ["security-validator", "production-endpoint-validator"]:
            return CompressionStrategy.CRITICAL_INFO_ONLY
        elif package_type == PackageType.STRATEGIC:
            return CompressionStrategy.SEMANTIC_PRESERVE
        else:
            return CompressionStrategy.AGENT_SPECIFIC
    
    async def _compress_for_agent(self, content: str, target_agent: str, 
                                target_tokens: int, agent_template: Dict) -> str:
        """Apply agent-specific compression"""
        
        if self._count_tokens(content) <= target_tokens:
            return content
        
        # Get agent template preferences
        focus_areas = agent_template.get("focus_areas", [])
        exclude_sections = agent_template.get("exclude_sections", [])
        priority_keywords = agent_template.get("priority_keywords", [])
        
        # Split content into sections
        sections = self._split_content_into_sections(content)
        
        # Score sections based on relevance to agent
        scored_sections = self._score_sections_for_agent(
            sections, focus_areas, exclude_sections, priority_keywords
        )
        
        # Select and compress sections to fit token limit
        compressed_content = self._select_and_compress_sections(
            scored_sections, target_tokens, target_agent
        )
        
        return compressed_content
    
    def _split_content_into_sections(self, content: str) -> List[Dict[str, Any]]:
        """Split content into logical sections"""
        
        # Split by common section markers
        section_markers = [
            r'#{1,3}\s+(.+)',  # Markdown headers
            r'\*\*([^*]+)\*\*',  # Bold text (often section titles)
            r'## (.+)',  # Specific level 2 headers
            r'### (.+)',  # Specific level 3 headers
        ]
        
        sections = []
        current_section = {"title": "Introduction", "content": "", "score": 0.0}
        
        lines = content.split('\n')
        
        for line in lines:
            # Check if line is a section marker
            is_section_marker = False
            for marker in section_markers:
                match = re.match(marker, line.strip())
                if match:
                    # Save current section if it has content
                    if current_section["content"].strip():
                        sections.append(current_section)
                    
                    # Start new section
                    current_section = {
                        "title": match.group(1) if match.groups() else line.strip(),
                        "content": "",
                        "score": 0.0
                    }
                    is_section_marker = True
                    break
            
            # Add line to current section
            if not is_section_marker:
                current_section["content"] += line + "\n"
        
        # Add final section
        if current_section["content"].strip():
            sections.append(current_section)
        
        return sections
    
    def _score_sections_for_agent(self, sections: List[Dict], focus_areas: List[str], 
                                exclude_sections: List[str], priority_keywords: List[str]) -> List[Dict]:
        """Score sections based on relevance to target agent"""
        
        for section in sections:
            score = 0.0
            title_lower = section["title"].lower()
            content_lower = section["content"].lower()
            combined = f"{title_lower} {content_lower}"
            
            # Boost score for focus areas
            for focus_area in focus_areas:
                if focus_area.lower() in combined:
                    score += 2.0
            
            # Boost score for priority keywords
            for keyword in priority_keywords:
                keyword_count = combined.count(keyword.lower())
                score += keyword_count * 1.5
            
            # Penalize excluded sections
            for exclude_pattern in exclude_sections:
                if exclude_pattern.lower() in combined:
                    score -= 3.0
            
            # Base relevance scoring
            if any(word in combined for word in ["error", "failed", "issue", "problem"]):
                score += 1.0
            
            if any(word in combined for word in ["success", "completed", "working", "fixed"]):
                score += 0.5
            
            # Length penalty for very long sections
            section_tokens = self._count_tokens(section["content"])
            if section_tokens > 1000:
                score -= 0.5
            
            section["score"] = max(0.0, score)  # Ensure non-negative
        
        # Sort by score (highest first)
        return sorted(sections, key=lambda x: x["score"], reverse=True)
    
    def _select_and_compress_sections(self, scored_sections: List[Dict], 
                                    target_tokens: int, target_agent: str) -> str:
        """Select and compress sections to fit token limit"""
        
        selected_content = []
        current_tokens = 0
        
        # Always include high-scoring sections first
        for section in scored_sections:
            section_content = f"## {section['title']}\n{section['content']}\n"
            section_tokens = self._count_tokens(section_content)
            
            if current_tokens + section_tokens <= target_tokens:
                selected_content.append(section_content)
                current_tokens += section_tokens
            else:
                # Try to compress the section
                available_tokens = target_tokens - current_tokens
                if available_tokens > 100:  # Minimum viable section size
                    compressed_section = self._compress_section(
                        section, available_tokens, target_agent
                    )
                    if compressed_section:
                        selected_content.append(compressed_section)
                        current_tokens += self._count_tokens(compressed_section)
                break
        
        return "\n".join(selected_content)
    
    def _compress_section(self, section: Dict, available_tokens: int, target_agent: str) -> str:
        """Compress individual section to fit available tokens"""
        
        title = section["title"]
        content = section["content"]
        
        # Try different compression strategies
        lines = content.split('\n')
        
        # Strategy 1: Keep first and last few lines, summarize middle
        if len(lines) > 10:
            header_lines = lines[:3]
            footer_lines = lines[-2:]
            middle_count = len(lines) - 5
            
            compressed = f"## {title}\n"
            compressed += "\n".join(header_lines) + "\n"
            compressed += f"\n[... {middle_count} lines of {target_agent} relevant details ...]\n"
            compressed += "\n".join(footer_lines) + "\n"
            
            if self._count_tokens(compressed) <= available_tokens:
                return compressed
        
        # Strategy 2: Extract key sentences
        sentences = content.split('.')
        key_sentences = [s.strip() for s in sentences[:available_tokens // 50] if s.strip()]
        
        if key_sentences:
            compressed = f"## {title}\n" + ". ".join(key_sentences) + ".\n"
            if self._count_tokens(compressed) <= available_tokens:
                return compressed
        
        # Strategy 3: Truncate with ellipsis
        max_chars = available_tokens * 4  # Rough character estimate
        if len(content) > max_chars:
            truncated = content[:max_chars] + "..."
            compressed = f"## {title}\n{truncated}\n"
            return compressed
        
        return None
    
    def _create_coordination_instructions(self, target_agent: str, 
                                        coordination_metadata: Dict) -> str:
        """Create coordination instructions for the agent"""
        
        instructions = f"## Coordination Instructions for {target_agent}\n\n"
        
        # Parallel execution instructions
        if coordination_metadata.get("parallel_agents"):
            instructions += "### Parallel Execution Context\n"
            instructions += f"- Executing in parallel with: {', '.join(coordination_metadata['parallel_agents'])}\n"
            instructions += "- Coordinate results through Main Claude\n"
            instructions += "- Do not call other agents directly\n\n"
        
        # Synchronization points
        if coordination_metadata.get("synchronization_points"):
            instructions += "### Synchronization Points\n"
            for point in coordination_metadata["synchronization_points"]:
                instructions += f"- {point}\n"
            instructions += "\n"
        
        # Handoff requirements
        if coordination_metadata.get("handoff_requirements"):
            instructions += "### Handoff Requirements\n"
            for requirement, details in coordination_metadata["handoff_requirements"].items():
                instructions += f"- {requirement}: {details}\n"
            instructions += "\n"
        
        # Agent-specific coordination rules
        agent_rules = {
            "backend-gateway-expert": [
                "Focus on server-side API issues and database connectivity",
                "Provide bash command outputs as evidence",
                "Test API endpoints and document response codes"
            ],
            "security-validator": [
                "Validate all security claims with evidence",
                "Test authentication flows end-to-end",
                "Document security findings with severity levels"
            ],
            "production-endpoint-validator": [
                "Test both HTTP and HTTPS endpoints",
                "Validate SSL certificates and security headers",
                "Provide cross-environment comparison data"
            ]
        }
        
        if target_agent in agent_rules:
            instructions += f"### {target_agent} Specific Rules\n"
            for rule in agent_rules[target_agent]:
                instructions += f"- {rule}\n"
            instructions += "\n"
        
        instructions += "### General Coordination Rules\n"
        instructions += "- Return results to Main Claude for coordination\n"
        instructions += "- Use available tools extensively for your specialization\n"
        instructions += "- Provide evidence for all success claims\n"
        instructions += "- Stay within your defined agent boundaries\n"
        
        return instructions
    
    def _generate_success_criteria(self, target_agent: str, package_type: str) -> List[str]:
        """Generate success criteria for the agent"""
        
        base_criteria = [
            "Complete assigned tasks within context package scope",
            "Provide evidence for all success claims",
            "Return actionable findings to Main Claude"
        ]
        
        agent_specific_criteria = {
            "backend-gateway-expert": [
                "API endpoints return expected status codes",
                "Server logs show error resolution",
                "Database connectivity verified"
            ],
            "security-validator": [
                "Security vulnerabilities identified and documented",
                "Authentication flows tested successfully",
                "Security recommendations provided"
            ],
            "production-endpoint-validator": [
                "Production endpoints tested successfully",
                "SSL certificates validated",
                "Cross-environment comparison completed"
            ],
            "performance-profiler": [
                "Performance bottlenecks identified",
                "Optimization recommendations provided",
                "Performance metrics documented"
            ]
        }
        
        criteria = base_criteria.copy()
        if target_agent in agent_specific_criteria:
            criteria.extend(agent_specific_criteria[target_agent])
        
        return criteria
    
    def _create_evidence_requirements(self, target_agent: str) -> Dict[str, Any]:
        """Create evidence requirements for the agent"""
        
        base_requirements = {
            "validation_type": "execution_evidence",
            "evidence_format": "structured_output",
            "success_metrics": ["task_completion", "evidence_quality"]
        }
        
        agent_requirements = {
            "backend-gateway-expert": {
                "validation_type": "api_testing",
                "evidence_format": "bash_output",
                "success_metrics": ["http_status_codes", "server_logs", "database_connectivity"]
            },
            "security-validator": {
                "validation_type": "security_testing",
                "evidence_format": "security_scan_results",
                "success_metrics": ["vulnerability_assessment", "auth_validation", "compliance_check"]
            },
            "production-endpoint-validator": {
                "validation_type": "endpoint_testing",
                "evidence_format": "test_results",
                "success_metrics": ["endpoint_availability", "ssl_validation", "performance_metrics"]
            }
        }
        
        return agent_requirements.get(target_agent, base_requirements)
    
    def _determine_priority(self, target_agent: str) -> str:
        """Determine priority level for the agent"""
        
        critical_agents = [
            "security-validator", "production-endpoint-validator", "backend-gateway-expert"
        ]
        
        high_priority_agents = [
            "enhanced-nexus-synthesis-agent", "performance-profiler", "monitoring-analyst"
        ]
        
        if target_agent in critical_agents:
            return "critical"
        elif target_agent in high_priority_agents:
            return "high"
        else:
            return "medium"
    
    async def _save_package_to_disk(self, package: ContextPackage) -> bool:
        """Save context package to disk for persistence"""
        
        try:
            package_file = self.cache_dir / f"{package.metadata.package_id}.json"
            
            package_data = {
                "metadata": asdict(package.metadata),
                "content": package.content,
                "coordination_instructions": package.coordination_instructions,
                "success_criteria": package.success_criteria,
                "evidence_requirements": package.evidence_requirements,
                "validation_hash": package.validation_hash
            }
            
            with open(package_file, 'w') as f:
                json.dump(package_data, f, indent=2, default=str)
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving package to disk: {str(e)}")
            return False
    
    async def get_context_package(self, package_id: str) -> Optional[ContextPackage]:
        """Retrieve context package by ID"""
        
        # Check cache first
        if package_id in self.package_cache:
            return self.package_cache[package_id]
        
        # Load from disk
        try:
            package_file = self.cache_dir / f"{package_id}.json"
            if package_file.exists():
                with open(package_file, 'r') as f:
                    package_data = json.load(f)
                
                # Reconstruct package
                metadata = ContextMetadata(**package_data['metadata'])
                package = ContextPackage(
                    metadata=metadata,
                    content=package_data['content'],
                    coordination_instructions=package_data['coordination_instructions'],
                    success_criteria=package_data['success_criteria'],
                    evidence_requirements=package_data['evidence_requirements'],
                    validation_hash=package_data['validation_hash']
                )
                
                # Cache for future use
                self.package_cache[package_id] = package
                return package
        
        except Exception as e:
            logger.error(f"Error loading package from disk: {str(e)}")
        
        return None
    
    async def create_parallel_packages(self, agents_context_map: Dict[str, Dict]) -> Dict[str, Any]:
        """Create context packages for parallel agent execution"""
        
        try:
            packages = {}
            coordination_metadata_base = {
                "parallel_agents": list(agents_context_map.keys()),
                "synchronization_points": ["initialization", "execution", "validation", "completion"]
            }
            
            for agent_name, context_info in agents_context_map.items():
                # Create agent-specific coordination metadata
                coordination_metadata = coordination_metadata_base.copy()
                coordination_metadata.update(context_info.get("coordination", {}))
                
                # Create package for this agent
                package_result = await self.create_context_package(
                    target_agent=agent_name,
                    full_context=context_info["content"],
                    package_type=context_info.get("package_type", "technical"),
                    coordination_metadata=coordination_metadata,
                    max_tokens=context_info.get("max_tokens")
                )
                
                if package_result.get("success"):
                    packages[agent_name] = package_result
                else:
                    logger.error(f"Failed to create package for {agent_name}: {package_result.get('error')}")
            
            return {
                "success": True,
                "packages_created": len(packages),
                "packages": packages,
                "parallel_agents": list(agents_context_map.keys()),
                "created_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error creating parallel packages: {str(e)}")
            return {"error": f"Failed to create parallel packages: {str(e)}"}

# Global instance for MCP server
context_manager = ContextPackageManager()

def get_context_manager() -> ContextPackageManager:
    """Get the global context package manager instance"""
    return context_manager