#!/usr/bin/env python3
"""
Dynamic Token Allocation System for Context Optimization
Intelligence-Enhanced Context Package Generation with Automated Sizing

AIWFE Context Optimization Implementation
Version: 2.0_enhanced | Date: 2025-08-14
"""

import json
import re
import math
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import time

@dataclass
class TokenAllocationProfile:
    """Dynamic token allocation profile for specialist contexts"""
    agent_type: str
    base_allocation: int
    complexity_multiplier: float
    domain_priority: str
    optimization_weight: float
    compression_threshold: float

@dataclass
class ContextPackageMetrics:
    """Context package generation and compression metrics"""
    package_id: str
    source_tokens: int
    target_tokens: int
    actual_tokens: int
    compression_ratio: float
    efficiency_score: float
    specialist_satisfaction: float
    generation_time: float

@dataclass
class DynamicAllocationResult:
    """Result of dynamic token allocation algorithm"""
    allocated_tokens: int
    complexity_score: float
    optimization_strategy: str
    estimated_efficiency: float
    compression_required: bool
    fallback_options: List[str]

class DynamicTokenAllocator:
    """
    Intelligent token allocation system with complexity-based sizing
    Implements predictive algorithms for optimal context package generation
    """
    
    def __init__(self):
        self.allocation_profiles = self._initialize_allocation_profiles()
        self.historical_metrics = {}
        self.optimization_cache = {}
        
    def _initialize_allocation_profiles(self) -> Dict[str, TokenAllocationProfile]:
        """Initialize specialist-specific allocation profiles"""
        return {
            # Backend Specialists
            "backend-gateway-expert": TokenAllocationProfile(
                agent_type="backend",
                base_allocation=3500,
                complexity_multiplier=1.2,
                domain_priority="technical_depth",
                optimization_weight=0.9,
                compression_threshold=0.75
            ),
            "schema-database-expert": TokenAllocationProfile(
                agent_type="database",
                base_allocation=3200,
                complexity_multiplier=1.1,
                domain_priority="structured_data",
                optimization_weight=0.85,
                compression_threshold=0.70
            ),
            
            # Frontend Specialists  
            "webui-architect": TokenAllocationProfile(
                agent_type="frontend",
                base_allocation=2800,
                complexity_multiplier=1.0,
                domain_priority="component_patterns",
                optimization_weight=0.8,
                compression_threshold=0.65
            ),
            "frictionless-ux-architect": TokenAllocationProfile(
                agent_type="ux",
                base_allocation=2500,
                complexity_multiplier=0.9,
                domain_priority="user_psychology",
                optimization_weight=0.75,
                compression_threshold=0.60
            ),
            
            # Quality Assurance
            "security-validator": TokenAllocationProfile(
                agent_type="security",
                base_allocation=3000,
                complexity_multiplier=1.3,
                domain_priority="risk_assessment",
                optimization_weight=0.95,
                compression_threshold=0.80
            ),
            "performance-profiler": TokenAllocationProfile(
                agent_type="performance",
                base_allocation=3200,
                complexity_multiplier=1.1,
                domain_priority="quantitative_metrics",
                optimization_weight=0.9,
                compression_threshold=0.75
            ),
            
            # Infrastructure
            "k8s-architecture-specialist": TokenAllocationProfile(
                agent_type="infrastructure",
                base_allocation=3500,
                complexity_multiplier=1.2,
                domain_priority="distributed_systems",
                optimization_weight=0.9,
                compression_threshold=0.75
            ),
            "deployment-orchestrator": TokenAllocationProfile(
                agent_type="devops",
                base_allocation=3000,
                complexity_multiplier=1.0,
                domain_priority="automation_patterns",
                optimization_weight=0.85,
                compression_threshold=0.70
            )
        }
    
    def calculate_complexity_score(self, context_data: Dict[str, Any], task_requirements: List[str]) -> float:
        """
        Calculate complexity score based on context data and task requirements
        Uses multiple factors: data volume, interdependencies, technical depth
        """
        base_complexity = 1.0
        
        # Factor 1: Data volume complexity
        if 'file_count' in context_data:
            file_complexity = min(context_data['file_count'] / 50.0, 2.0)
            base_complexity += file_complexity * 0.3
            
        # Factor 2: Technical depth complexity
        if 'technical_patterns' in context_data:
            pattern_complexity = len(context_data['technical_patterns']) / 10.0
            base_complexity += pattern_complexity * 0.4
            
        # Factor 3: Interdependency complexity
        if 'dependencies' in context_data:
            dependency_complexity = len(context_data['dependencies']) / 20.0
            base_complexity += dependency_complexity * 0.3
            
        # Factor 4: Task requirement complexity
        requirement_complexity = 0.0
        complexity_keywords = ['refactor', 'architecture', 'security', 'performance', 'integration']
        for requirement in task_requirements:
            for keyword in complexity_keywords:
                if keyword in requirement.lower():
                    requirement_complexity += 0.2
                    
        base_complexity += requirement_complexity
        
        # Cap complexity score at 3.0
        return min(base_complexity, 3.0)
    
    def allocate_dynamic_tokens(self, agent_name: str, context_data: Dict[str, Any], 
                              task_requirements: List[str]) -> DynamicAllocationResult:
        """
        Dynamically allocate tokens based on agent profile, complexity, and task requirements
        Implements predictive sizing with fallback strategies
        """
        if agent_name not in self.allocation_profiles:
            # Default allocation for unknown agents
            return DynamicAllocationResult(
                allocated_tokens=3000,
                complexity_score=1.0,
                optimization_strategy="default",
                estimated_efficiency=0.7,
                compression_required=False,
                fallback_options=["standard_compression"]
            )
        
        profile = self.allocation_profiles[agent_name]
        complexity_score = self.calculate_complexity_score(context_data, task_requirements)
        
        # Dynamic token allocation calculation
        base_tokens = profile.base_allocation
        complexity_adjustment = base_tokens * (complexity_score - 1.0) * profile.complexity_multiplier * 0.2
        allocated_tokens = int(base_tokens + complexity_adjustment)
        
        # Apply optimization weight
        optimized_allocation = int(allocated_tokens * profile.optimization_weight)
        
        # Determine optimization strategy
        strategy = self._determine_optimization_strategy(profile, complexity_score, optimized_allocation)
        
        # Calculate estimated efficiency
        efficiency = self._calculate_estimated_efficiency(profile, complexity_score, optimized_allocation)
        
        # Determine if compression is required
        compression_required = optimized_allocation > 4000 or efficiency < profile.compression_threshold
        
        # Generate fallback options
        fallback_options = self._generate_fallback_options(profile, complexity_score, optimized_allocation)
        
        return DynamicAllocationResult(
            allocated_tokens=min(optimized_allocation, 4000),  # Enforce 4K token limit
            complexity_score=complexity_score,
            optimization_strategy=strategy,
            estimated_efficiency=efficiency,
            compression_required=compression_required,
            fallback_options=fallback_options
        )
    
    def _determine_optimization_strategy(self, profile: TokenAllocationProfile, 
                                       complexity_score: float, allocated_tokens: int) -> str:
        """Determine the optimal compression and optimization strategy"""
        if complexity_score > 2.0:
            return "hierarchical_compression_with_priority_preservation"
        elif allocated_tokens > 3500:
            return "intelligent_summarization_with_technical_depth"
        elif profile.domain_priority == "quantitative_metrics":
            return "metrics_focused_compression"
        elif profile.domain_priority == "technical_depth":
            return "depth_preserving_optimization"
        elif profile.domain_priority == "user_psychology":
            return "behavioral_pattern_preservation"
        else:
            return "balanced_compression_optimization"
    
    def _calculate_estimated_efficiency(self, profile: TokenAllocationProfile, 
                                      complexity_score: float, allocated_tokens: int) -> float:
        """Calculate estimated token utilization efficiency"""
        base_efficiency = profile.optimization_weight
        
        # Complexity adjustment
        complexity_adjustment = min((complexity_score - 1.0) * 0.1, 0.3)
        
        # Token utilization adjustment
        utilization_ratio = allocated_tokens / 4000.0
        utilization_adjustment = 0.1 if utilization_ratio > 0.8 else -0.1
        
        estimated_efficiency = base_efficiency + complexity_adjustment + utilization_adjustment
        return max(0.5, min(estimated_efficiency, 1.0))
    
    def _generate_fallback_options(self, profile: TokenAllocationProfile, 
                                 complexity_score: float, allocated_tokens: int) -> List[str]:
        """Generate fallback compression and optimization options"""
        fallbacks = []
        
        if allocated_tokens > 3800:
            fallbacks.append("aggressive_compression_with_key_preservation")
        if complexity_score > 2.5:
            fallbacks.append("multi_level_hierarchical_compression")
        if profile.domain_priority == "technical_depth":
            fallbacks.append("code_pattern_abstraction")
        if profile.domain_priority == "quantitative_metrics":
            fallbacks.append("metrics_table_optimization")
            
        fallbacks.append("standard_intelligent_compression")
        return fallbacks
    
    def update_historical_metrics(self, package_metrics: ContextPackageMetrics):
        """Update historical performance metrics for continuous learning"""
        agent_type = package_metrics.package_id.split('_')[0]
        
        if agent_type not in self.historical_metrics:
            self.historical_metrics[agent_type] = []
            
        self.historical_metrics[agent_type].append(package_metrics)
        
        # Keep only last 100 metrics per agent type
        if len(self.historical_metrics[agent_type]) > 100:
            self.historical_metrics[agent_type] = self.historical_metrics[agent_type][-100:]
    
    def optimize_allocation_profiles(self):
        """Optimize allocation profiles based on historical performance"""
        for agent_type, metrics_list in self.historical_metrics.items():
            if len(metrics_list) < 10:  # Need sufficient data for optimization
                continue
                
            # Calculate average efficiency
            avg_efficiency = sum(m.efficiency_score for m in metrics_list) / len(metrics_list)
            avg_satisfaction = sum(m.specialist_satisfaction for m in metrics_list) / len(metrics_list)
            
            # Update profiles for agents with low performance
            for agent_name, profile in self.allocation_profiles.items():
                if profile.agent_type == agent_type:
                    if avg_efficiency < 0.7:
                        profile.base_allocation = int(profile.base_allocation * 1.1)
                    if avg_satisfaction < 0.8:
                        profile.optimization_weight = min(profile.optimization_weight + 0.05, 1.0)

class AutomatedPackageGenerator:
    """
    Automated context package generation from research findings
    Implements intelligent package assembly with domain-specific optimization
    """
    
    def __init__(self, allocator: DynamicTokenAllocator):
        self.allocator = allocator
        self.package_templates = self._load_package_templates()
        self.compression_engines = self._initialize_compression_engines()
    
    def _load_package_templates(self) -> Dict[str, Dict]:
        """Load domain-specific package templates"""
        return {
            "backend": {
                "required_sections": ["architecture_patterns", "api_specifications", "database_integration"],
                "optional_sections": ["performance_considerations", "security_patterns", "monitoring_setup"],
                "metadata_fields": ["service_dependencies", "resource_requirements", "scaling_parameters"]
            },
            "frontend": {
                "required_sections": ["component_architecture", "styling_approach", "state_management"],
                "optional_sections": ["accessibility_patterns", "performance_optimization", "testing_strategy"],
                "metadata_fields": ["browser_compatibility", "responsive_breakpoints", "asset_optimization"]
            },
            "security": {
                "required_sections": ["threat_assessment", "authentication_patterns", "authorization_models"],
                "optional_sections": ["encryption_standards", "audit_requirements", "compliance_frameworks"],
                "metadata_fields": ["risk_levels", "mitigation_strategies", "monitoring_requirements"]
            },
            "performance": {
                "required_sections": ["bottleneck_analysis", "optimization_targets", "monitoring_metrics"],
                "optional_sections": ["caching_strategies", "load_balancing", "resource_scaling"],
                "metadata_fields": ["performance_baselines", "optimization_priorities", "measurement_tools"]
            },
            "infrastructure": {
                "required_sections": ["deployment_architecture", "resource_allocation", "monitoring_setup"],
                "optional_sections": ["disaster_recovery", "scaling_policies", "cost_optimization"],
                "metadata_fields": ["service_dependencies", "resource_limits", "health_check_endpoints"]
            }
        }
    
    def _initialize_compression_engines(self) -> Dict[str, Any]:
        """Initialize domain-specific compression engines"""
        return {
            "hierarchical": self._hierarchical_compression,
            "intelligent_summarization": self._intelligent_summarization,
            "metrics_focused": self._metrics_focused_compression,
            "depth_preserving": self._depth_preserving_compression,
            "behavioral_pattern": self._behavioral_pattern_compression,
            "balanced": self._balanced_compression
        }
    
    def generate_package_from_research(self, agent_name: str, research_data: Dict[str, Any], 
                                     task_requirements: List[str]) -> Dict[str, Any]:
        """
        Generate optimized context package from research findings
        Implements automated package assembly with intelligent compression
        """
        start_time = time.time()
        
        # Get dynamic token allocation
        allocation_result = self.allocator.allocate_dynamic_tokens(
            agent_name, research_data, task_requirements
        )
        
        # Determine agent domain for template selection
        agent_domain = self._determine_agent_domain(agent_name)
        template = self.package_templates.get(agent_domain, self.package_templates["backend"])
        
        # Assemble raw package content
        raw_content = self._assemble_package_content(research_data, template, task_requirements)
        
        # Calculate raw token count
        raw_tokens = self._estimate_token_count(raw_content)
        
        # Apply compression if needed
        if allocation_result.compression_required or raw_tokens > allocation_result.allocated_tokens:
            compressed_content = self._apply_intelligent_compression(
                raw_content, allocation_result, agent_domain
            )
            final_tokens = self._estimate_token_count(compressed_content)
        else:
            compressed_content = raw_content
            final_tokens = raw_tokens
        
        # Generate enhanced coordination metadata
        coordination_metadata = self._generate_coordination_metadata(
            agent_name, allocation_result, final_tokens
        )
        
        # Build final package
        package = {
            "package_metadata": {
                "package_id": f"{agent_name}_context_{int(time.time())}",
                "agent_target": agent_name,
                "domain": agent_domain,
                "token_allocation": allocation_result.allocated_tokens,
                "actual_tokens": final_tokens,
                "compression_ratio": (raw_tokens - final_tokens) / raw_tokens if raw_tokens > 0 else 0,
                "efficiency_score": allocation_result.estimated_efficiency,
                "optimization_strategy": allocation_result.optimization_strategy,
                "generation_timestamp": time.time(),
                "generation_time": time.time() - start_time
            },
            "context_content": compressed_content,
            "coordination_metadata": coordination_metadata,
            "task_requirements": task_requirements,
            "fallback_strategies": allocation_result.fallback_options
        }
        
        return package
    
    def _determine_agent_domain(self, agent_name: str) -> str:
        """Determine agent domain from agent name"""
        domain_mappings = {
            "backend": ["backend-gateway-expert", "schema-database-expert", "python-refactoring-architect"],
            "frontend": ["webui-architect", "frictionless-ux-architect", "whimsy-ui-creator"],
            "security": ["security-validator", "security-orchestrator", "security-vulnerability-scanner"],
            "performance": ["performance-profiler", "monitoring-analyst"],
            "infrastructure": ["k8s-architecture-specialist", "deployment-orchestrator", "infrastructure-orchestrator"]
        }
        
        for domain, agents in domain_mappings.items():
            if agent_name in agents:
                return domain
        
        return "backend"  # Default domain
    
    def _assemble_package_content(self, research_data: Dict[str, Any], 
                                template: Dict[str, Any], task_requirements: List[str]) -> str:
        """Assemble package content from research data using domain template"""
        content_sections = []
        
        # Add required sections
        for section in template["required_sections"]:
            if section in research_data:
                content_sections.append(f"## {section.replace('_', ' ').title()}")
                content_sections.append(str(research_data[section]))
                content_sections.append("")
        
        # Add relevant optional sections
        for section in template["optional_sections"]:
            if section in research_data and self._is_section_relevant(section, task_requirements):
                content_sections.append(f"## {section.replace('_', ' ').title()}")
                content_sections.append(str(research_data[section]))
                content_sections.append("")
        
        # Add metadata
        if "metadata" in research_data:
            content_sections.append("## Metadata")
            for field in template["metadata_fields"]:
                if field in research_data["metadata"]:
                    content_sections.append(f"- {field}: {research_data['metadata'][field]}")
            content_sections.append("")
        
        return "\n".join(content_sections)
    
    def _is_section_relevant(self, section: str, task_requirements: List[str]) -> bool:
        """Determine if optional section is relevant to task requirements"""
        relevance_keywords = {
            "performance_considerations": ["optimize", "performance", "speed", "latency"],
            "security_patterns": ["security", "auth", "encrypt", "secure"],
            "accessibility_patterns": ["accessibility", "a11y", "wcag", "screen reader"],
            "testing_strategy": ["test", "validate", "qa", "quality"],
            "disaster_recovery": ["backup", "recovery", "resilience", "failover"],
            "cost_optimization": ["cost", "budget", "optimize", "efficiency"]
        }
        
        keywords = relevance_keywords.get(section, [])
        return any(keyword in req.lower() for req in task_requirements for keyword in keywords)
    
    def _estimate_token_count(self, content: str) -> int:
        """Estimate token count using word-based approximation"""
        words = len(content.split())
        return int(words * 1.3)  # Approximate 1.3 tokens per word
    
    def _apply_intelligent_compression(self, content: str, allocation_result: DynamicAllocationResult, 
                                     domain: str) -> str:
        """Apply intelligent compression based on optimization strategy"""
        strategy = allocation_result.optimization_strategy
        
        if strategy in self.compression_engines:
            return self.compression_engines[strategy](content, allocation_result.allocated_tokens)
        else:
            return self.compression_engines["balanced"](content, allocation_result.allocated_tokens)
    
    def _hierarchical_compression(self, content: str, target_tokens: int) -> str:
        """Hierarchical compression with priority preservation"""
        sections = content.split('\n## ')
        compressed_sections = []
        
        # Priority order: metadata, architecture, implementation, optional
        priority_keywords = ["metadata", "architecture", "specification", "pattern"]
        
        for section in sections:
            section_priority = 1.0
            for keyword in priority_keywords:
                if keyword.lower() in section.lower():
                    section_priority = 0.8
                    break
            
            if section_priority < 1.0:
                # Preserve high-priority sections with minimal compression
                compressed_sections.append(self._compress_section(section, 0.9))
            else:
                # Apply more aggressive compression to lower-priority sections
                compressed_sections.append(self._compress_section(section, 0.7))
        
        return '\n## '.join(compressed_sections)
    
    def _intelligent_summarization(self, content: str, target_tokens: int) -> str:
        """Intelligent summarization with technical depth preservation"""
        # Split into code blocks and text blocks
        code_pattern = r'```[\s\S]*?```'
        code_blocks = re.findall(code_pattern, content)
        text_content = re.sub(code_pattern, '[CODE_BLOCK]', content)
        
        # Compress text while preserving code blocks
        compressed_text = self._compress_text_content(text_content, 0.6)
        
        # Reinsert code blocks
        for code_block in code_blocks:
            compressed_text = compressed_text.replace('[CODE_BLOCK]', code_block, 1)
        
        return compressed_text
    
    def _metrics_focused_compression(self, content: str, target_tokens: int) -> str:
        """Metrics-focused compression preserving quantitative data"""
        # Preserve numbers, percentages, and measurement units
        metric_patterns = [
            r'\d+\.\d+%',  # Percentages
            r'\d+\.\d+\s*(ms|sec|min|MB|GB|KB)',  # Measurements
            r'\d+\s*(requests|queries|users)/\w+',  # Rates
            r'>\s*\d+',  # Thresholds
        ]
        
        protected_content = content
        for pattern in metric_patterns:
            # Mark metrics for protection during compression
            protected_content = re.sub(pattern, r'[METRIC:\g<0>]', protected_content)
        
        # Apply general compression
        compressed = self._compress_section(protected_content, 0.7)
        
        # Restore protected metrics
        compressed = re.sub(r'\[METRIC:(.*?)\]', r'\1', compressed)
        
        return compressed
    
    def _depth_preserving_compression(self, content: str, target_tokens: int) -> str:
        """Depth-preserving compression maintaining technical detail"""
        # Preserve technical terms and implementation details
        technical_patterns = [
            r'```[\s\S]*?```',  # Code blocks
            r'`[^`]+`',  # Inline code
            r'\b[A-Z][a-z]+[A-Z][A-Za-z]*\b',  # CamelCase (class/method names)
            r'\b\w+\(\)',  # Function calls
            r'https?://[^\s]+',  # URLs
        ]
        
        protected_content = content
        for i, pattern in enumerate(technical_patterns):
            protected_content = re.sub(pattern, f'[TECH_{i}:\\g<0>]', protected_content)
        
        # Apply compression to remaining content
        compressed = self._compress_section(protected_content, 0.8)
        
        # Restore technical elements
        for i in range(len(technical_patterns)):
            compressed = re.sub(f'\\[TECH_{i}:(.*?)\\]', r'\1', compressed)
        
        return compressed
    
    def _behavioral_pattern_compression(self, content: str, target_tokens: int) -> str:
        """Behavioral pattern compression for UX and user psychology content"""
        # Preserve user journey descriptions and interaction patterns
        ux_patterns = [
            r'user\s+\w+s?',  # User actions
            r'click\s+\w+',  # Click interactions
            r'navigation\s+\w+',  # Navigation patterns
            r'accessibility\s+\w+',  # Accessibility features
        ]
        
        protected_content = content
        for i, pattern in enumerate(ux_patterns):
            protected_content = re.sub(pattern, f'[UX_{i}:\\g<0>]', protected_content, flags=re.IGNORECASE)
        
        compressed = self._compress_section(protected_content, 0.75)
        
        # Restore UX patterns
        for i in range(len(ux_patterns)):
            compressed = re.sub(f'\\[UX_{i}:(.*?)\\]', r'\1', compressed)
        
        return compressed
    
    def _balanced_compression(self, content: str, target_tokens: int) -> str:
        """Balanced compression for general optimization"""
        return self._compress_section(content, 0.75)
    
    def _compress_section(self, section: str, compression_ratio: float) -> str:
        """Apply section-level compression"""
        lines = section.split('\n')
        target_lines = int(len(lines) * compression_ratio)
        
        if target_lines >= len(lines):
            return section
        
        # Keep first few lines (headers/key info) and compress the rest
        header_lines = min(3, len(lines))
        remaining_lines = lines[header_lines:]
        
        # Select most important remaining lines based on length and keywords
        important_lines = sorted(remaining_lines, 
                               key=lambda x: len(x) + (10 if any(kw in x.lower() 
                                                               for kw in ['important', 'critical', 'required']) else 0),
                               reverse=True)
        
        selected_lines = important_lines[:max(1, target_lines - header_lines)]
        
        return '\n'.join(lines[:header_lines] + selected_lines)
    
    def _compress_text_content(self, text: str, compression_ratio: float) -> str:
        """Compress text content while preserving meaning"""
        sentences = text.split('. ')
        target_sentences = int(len(sentences) * compression_ratio)
        
        if target_sentences >= len(sentences):
            return text
        
        # Prioritize sentences with key information
        sentence_scores = []
        for sentence in sentences:
            score = len(sentence)  # Base score on length
            if any(keyword in sentence.lower() for keyword in ['implement', 'critical', 'required', 'must']):
                score += 50
            sentence_scores.append((sentence, score))
        
        # Select top sentences
        selected_sentences = sorted(sentence_scores, key=lambda x: x[1], reverse=True)[:target_sentences]
        selected_sentences.sort(key=lambda x: sentences.index(x[0]))  # Restore original order
        
        return '. '.join([s[0] for s in selected_sentences])
    
    def _generate_coordination_metadata(self, agent_name: str, allocation_result: DynamicAllocationResult, 
                                      final_tokens: int) -> Dict[str, Any]:
        """Generate enhanced coordination metadata for package"""
        return {
            "allocation_metadata": {
                "dynamic_allocation": allocation_result.allocated_tokens,
                "complexity_score": allocation_result.complexity_score,
                "optimization_strategy": allocation_result.optimization_strategy,
                "estimated_efficiency": allocation_result.estimated_efficiency,
                "actual_tokens": final_tokens,
                "compression_applied": allocation_result.compression_required,
                "fallback_options": allocation_result.fallback_options
            },
            "coordination_protocols": {
                "parallel_execution_support": True,
                "cross_stream_coordination": True,
                "resource_optimization": True,
                "intelligent_compression": True
            },
            "validation_requirements": {
                "efficiency_threshold": 0.7,
                "satisfaction_threshold": 0.8,
                "token_compliance": final_tokens <= 4000,
                "compression_quality": "preserved_critical_information"
            },
            "performance_metrics": {
                "generation_efficiency": allocation_result.estimated_efficiency,
                "token_utilization": final_tokens / 4000.0,
                "compression_effectiveness": allocation_result.compression_required,
                "specialist_readiness": "optimized"
            }
        }

def main():
    """Main function for testing the dynamic token allocation system"""
    allocator = DynamicTokenAllocator()
    generator = AutomatedPackageGenerator(allocator)
    
    # Test dynamic allocation
    test_context = {
        'file_count': 25,
        'technical_patterns': ['microservices', 'event-driven', 'CQRS', 'docker'],
        'dependencies': ['fastapi', 'redis', 'postgres', 'kubernetes']
    }
    
    test_requirements = ['Implement microservices architecture', 'Optimize database performance', 'Add security validation']
    
    # Test allocation for different agents
    test_agents = ['backend-gateway-expert', 'security-validator', 'performance-profiler']
    
    for agent in test_agents:
        result = allocator.allocate_dynamic_tokens(agent, test_context, test_requirements)
        print(f"\n=== {agent} ===")
        print(f"Allocated Tokens: {result.allocated_tokens}")
        print(f"Complexity Score: {result.complexity_score:.2f}")
        print(f"Strategy: {result.optimization_strategy}")
        print(f"Efficiency: {result.estimated_efficiency:.2f}")
        print(f"Compression Required: {result.compression_required}")
        print(f"Fallbacks: {result.fallback_options}")
    
    print("\n=== Dynamic Token Allocation System Implementation Complete ===")

if __name__ == "__main__":
    main()