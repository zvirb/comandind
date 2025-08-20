#!/usr/bin/env python3
"""
Intelligent Compression Engine with Domain-Specific Optimization
Advanced Context Package Compression with Quality Preservation

AIWFE Context Optimization Implementation
Version: 2.0_enhanced | Date: 2025-08-14
"""

import json
import re
import math
import time
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod

@dataclass
class CompressionProfile:
    """Domain-specific compression profile"""
    domain: str
    preservation_patterns: List[str]
    compression_weights: Dict[str, float]
    quality_thresholds: Dict[str, float]
    optimization_strategies: List[str]
    fallback_ratios: List[float]

@dataclass
class CompressionResult:
    """Result of intelligent compression operation"""
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    quality_score: float
    preservation_score: float
    strategy_applied: str
    optimization_notes: List[str]
    fallback_used: bool

@dataclass
class CompressionAnalysis:
    """Analysis of content for compression optimization"""
    content_type: str
    complexity_score: float
    critical_elements: List[str]
    redundancy_score: float
    compression_potential: float
    recommended_strategy: str

class CompressionStrategy(ABC):
    """Abstract base class for compression strategies"""
    
    @abstractmethod
    def analyze_content(self, content: str, target_ratio: float) -> CompressionAnalysis:
        """Analyze content for compression potential"""
        pass
    
    @abstractmethod
    def compress(self, content: str, target_tokens: int, profile: CompressionProfile) -> CompressionResult:
        """Compress content using strategy-specific approach"""
        pass
    
    @abstractmethod
    def preserve_critical_elements(self, content: str, profile: CompressionProfile) -> List[str]:
        """Identify and preserve critical elements"""
        pass

class HierarchicalCompressionStrategy(CompressionStrategy):
    """
    Hierarchical compression with priority-based preservation
    Maintains information hierarchy while optimizing token usage
    """
    
    def analyze_content(self, content: str, target_ratio: float) -> CompressionAnalysis:
        """Analyze content structure and compression potential"""
        
        # Identify content hierarchy
        headers = re.findall(r'^#+\s+(.+)$', content, re.MULTILINE)
        code_blocks = re.findall(r'```[\s\S]*?```', content)
        lists = re.findall(r'^\s*[-*+]\s+(.+)$', content, re.MULTILINE)
        
        # Calculate complexity based on structure
        complexity_score = (
            len(headers) * 0.3 +
            len(code_blocks) * 0.5 +
            len(lists) * 0.2 +
            (len(content.split('\n')) / 100) * 0.4
        )
        
        # Identify critical elements
        critical_elements = []
        critical_elements.extend([f"Header: {h}" for h in headers[:5]])  # Top 5 headers
        critical_elements.extend([f"Code: {c[:50]}..." for c in code_blocks[:3]])  # Top 3 code blocks
        
        # Calculate redundancy
        words = content.split()
        unique_words = set(words)
        redundancy_score = 1 - (len(unique_words) / len(words)) if words else 0
        
        # Estimate compression potential
        compression_potential = min(0.8, redundancy_score + (complexity_score / 10))
        
        return CompressionAnalysis(
            content_type="hierarchical_structured",
            complexity_score=complexity_score,
            critical_elements=critical_elements,
            redundancy_score=redundancy_score,
            compression_potential=compression_potential,
            recommended_strategy="hierarchical_priority_preservation"
        )
    
    def compress(self, content: str, target_tokens: int, profile: CompressionProfile) -> CompressionResult:
        """Apply hierarchical compression with priority preservation"""
        
        original_tokens = self._estimate_tokens(content)
        target_ratio = target_tokens / original_tokens if original_tokens > 0 else 1.0
        
        if target_ratio >= 1.0:
            return CompressionResult(
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                compression_ratio=1.0,
                quality_score=1.0,
                preservation_score=1.0,
                strategy_applied="no_compression_needed",
                optimization_notes=["Content already within target token limit"],
                fallback_used=False
            )
        
        # Extract and preserve critical elements
        critical_elements = self.preserve_critical_elements(content, profile)
        
        # Split content into sections by headers
        sections = self._split_by_hierarchy(content)
        
        # Apply progressive compression to sections
        compressed_sections = []
        compression_notes = []
        
        for i, (section_header, section_content) in enumerate(sections):
            # Calculate section priority (higher priority for earlier sections)
            section_priority = max(0.3, 1.0 - (i * 0.15))
            section_target_ratio = target_ratio / section_priority
            
            # Apply section-specific compression
            if section_priority > 0.7:
                # High priority: minimal compression
                compressed_section = self._compress_section(
                    section_content, min(0.9, section_target_ratio), "minimal"
                )
                compression_notes.append(f"Section '{section_header}': minimal compression (priority: {section_priority:.2f})")
            elif section_priority > 0.4:
                # Medium priority: balanced compression
                compressed_section = self._compress_section(
                    section_content, section_target_ratio, "balanced"
                )
                compression_notes.append(f"Section '{section_header}': balanced compression (priority: {section_priority:.2f})")
            else:
                # Low priority: aggressive compression
                compressed_section = self._compress_section(
                    section_content, section_target_ratio, "aggressive"
                )
                compression_notes.append(f"Section '{section_header}': aggressive compression (priority: {section_priority:.2f})")
            
            compressed_sections.append((section_header, compressed_section))
        
        # Reassemble compressed content
        compressed_content = self._reassemble_sections(compressed_sections)
        
        # Restore critical elements
        compressed_content = self._restore_critical_elements(compressed_content, critical_elements)
        
        # Calculate final metrics
        final_tokens = self._estimate_tokens(compressed_content)
        compression_ratio = final_tokens / original_tokens if original_tokens > 0 else 1.0
        quality_score = self._calculate_quality_score(content, compressed_content)
        preservation_score = self._calculate_preservation_score(critical_elements, compressed_content)
        
        return CompressionResult(
            original_tokens=original_tokens,
            compressed_tokens=final_tokens,
            compression_ratio=compression_ratio,
            quality_score=quality_score,
            preservation_score=preservation_score,
            strategy_applied="hierarchical_priority_preservation",
            optimization_notes=compression_notes,
            fallback_used=final_tokens > target_tokens
        )
    
    def preserve_critical_elements(self, content: str, profile: CompressionProfile) -> List[str]:
        """Identify and preserve critical elements based on domain patterns"""
        critical_elements = []
        
        # Apply domain-specific preservation patterns
        for pattern in profile.preservation_patterns:
            matches = re.findall(pattern, content, re.MULTILINE | re.IGNORECASE)
            critical_elements.extend([f"[PRESERVE:{pattern}]:{match}" for match in matches[:10]])
        
        return critical_elements
    
    def _split_by_hierarchy(self, content: str) -> List[Tuple[str, str]]:
        """Split content by hierarchical structure"""
        sections = []
        lines = content.split('\n')
        current_section = []
        current_header = "Introduction"
        
        for line in lines:
            header_match = re.match(r'^(#+)\s+(.+)$', line)
            if header_match:
                # Save previous section
                if current_section:
                    sections.append((current_header, '\n'.join(current_section)))
                
                # Start new section
                current_header = header_match.group(2)
                current_section = []
            else:
                current_section.append(line)
        
        # Add final section
        if current_section:
            sections.append((current_header, '\n'.join(current_section)))
        
        return sections
    
    def _compress_section(self, content: str, target_ratio: float, intensity: str) -> str:
        """Apply section-level compression with specified intensity"""
        if intensity == "minimal":
            return self._minimal_compression(content, target_ratio)
        elif intensity == "balanced":
            return self._balanced_compression(content, target_ratio)
        elif intensity == "aggressive":
            return self._aggressive_compression(content, target_ratio)
        else:
            return content
    
    def _minimal_compression(self, content: str, target_ratio: float) -> str:
        """Apply minimal compression preserving most content"""
        lines = content.split('\n')
        target_lines = max(int(len(lines) * target_ratio), len(lines) - 5)
        
        # Remove empty lines and redundant spacing first
        non_empty_lines = [line for line in lines if line.strip()]
        if len(non_empty_lines) <= target_lines:
            return '\n'.join(non_empty_lines)
        
        # Keep most important lines (longer lines typically contain more information)
        important_lines = sorted(non_empty_lines, key=len, reverse=True)[:target_lines]
        
        # Restore original order
        result_lines = []
        for line in lines:
            if line in important_lines:
                result_lines.append(line)
                important_lines.remove(line)
        
        return '\n'.join(result_lines)
    
    def _balanced_compression(self, content: str, target_ratio: float) -> str:
        """Apply balanced compression with moderate information loss"""
        # Combine sentence-level and line-level compression
        sentences = content.split('. ')
        target_sentences = max(1, int(len(sentences) * target_ratio))
        
        # Score sentences by importance
        sentence_scores = []
        for sentence in sentences:
            score = len(sentence)  # Base score on length
            
            # Boost score for sentences with important keywords
            importance_keywords = ['implement', 'critical', 'required', 'must', 'architecture', 'security']
            for keyword in importance_keywords:
                if keyword.lower() in sentence.lower():
                    score += 50
            
            sentence_scores.append((sentence, score))
        
        # Select top sentences
        selected_sentences = sorted(sentence_scores, key=lambda x: x[1], reverse=True)[:target_sentences]
        
        # Restore original order
        selected_sentences_ordered = []
        for sentence in sentences:
            for selected_sentence, _ in selected_sentences:
                if sentence == selected_sentence:
                    selected_sentences_ordered.append(sentence)
                    break
        
        return '. '.join(selected_sentences_ordered)
    
    def _aggressive_compression(self, content: str, target_ratio: float) -> str:
        """Apply aggressive compression with significant information loss"""
        # Extract only key phrases and critical information
        lines = content.split('\n')
        
        # Keep only lines with high information density
        high_density_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Calculate information density
            density_score = 0
            
            # Code or configuration lines
            if re.match(r'^[a-zA-Z_]+\s*[:=]', line) or '```' in line:
                density_score += 20
            
            # Lines with numbers or metrics
            if re.search(r'\d+(\.\d+)?(%|ms|sec|MB|GB)', line):
                density_score += 15
            
            # Lines with important keywords
            if any(keyword in line.lower() for keyword in ['error', 'security', 'performance', 'critical']):
                density_score += 10
            
            # Header lines
            if line.startswith('#') or line.endswith(':'):
                density_score += 5
            
            if density_score > 5 or len(line) > 80:
                high_density_lines.append(line)
        
        # Select target number of lines
        target_lines = max(1, int(len(high_density_lines) * target_ratio))
        return '\n'.join(high_density_lines[:target_lines])
    
    def _reassemble_sections(self, sections: List[Tuple[str, str]]) -> str:
        """Reassemble compressed sections into coherent content"""
        result_parts = []
        for header, content in sections:
            if content.strip():
                result_parts.append(f"## {header}")
                result_parts.append(content)
                result_parts.append("")  # Add spacing between sections
        
        return '\n'.join(result_parts)
    
    def _restore_critical_elements(self, content: str, critical_elements: List[str]) -> str:
        """Restore critical elements that may have been lost during compression"""
        # For now, append critical elements that aren't already present
        missing_elements = []
        for element in critical_elements:
            if element.split(':', 2)[-1] not in content:
                missing_elements.append(element.split(':', 2)[-1])
        
        if missing_elements:
            content += "\n\n## Critical Elements\n"
            content += '\n'.join(f"- {element}" for element in missing_elements[:5])
        
        return content
    
    def _estimate_tokens(self, content: str) -> int:
        """Estimate token count from content"""
        return int(len(content.split()) * 1.3)
    
    def _calculate_quality_score(self, original: str, compressed: str) -> float:
        """Calculate quality retention score"""
        original_lines = set(original.split('\n'))
        compressed_lines = set(compressed.split('\n'))
        
        if not original_lines:
            return 1.0
        
        preserved_lines = len(original_lines.intersection(compressed_lines))
        return preserved_lines / len(original_lines)
    
    def _calculate_preservation_score(self, critical_elements: List[str], compressed_content: str) -> float:
        """Calculate critical element preservation score"""
        if not critical_elements:
            return 1.0
        
        preserved_count = 0
        for element in critical_elements:
            element_content = element.split(':', 2)[-1]
            if element_content in compressed_content:
                preserved_count += 1
        
        return preserved_count / len(critical_elements)

class TechnicalDepthCompressionStrategy(CompressionStrategy):
    """
    Technical depth compression preserving implementation details
    Optimized for backend and infrastructure content
    """
    
    def analyze_content(self, content: str, target_ratio: float) -> CompressionAnalysis:
        """Analyze technical content for compression potential"""
        
        # Identify technical patterns
        code_blocks = re.findall(r'```[\s\S]*?```', content)
        function_calls = re.findall(r'\w+\([^)]*\)', content)
        config_patterns = re.findall(r'\w+\s*[:=]\s*\w+', content)
        technical_terms = re.findall(r'\b[A-Z][a-z]*[A-Z][A-Za-z]*\b', content)
        
        # Calculate technical complexity
        complexity_score = (
            len(code_blocks) * 2.0 +
            len(function_calls) * 0.5 +
            len(config_patterns) * 0.3 +
            len(technical_terms) * 0.1
        )
        
        critical_elements = []
        critical_elements.extend([f"Code: {c[:100]}..." for c in code_blocks])
        critical_elements.extend([f"Function: {f}" for f in function_calls[:10]])
        critical_elements.extend([f"Config: {c}" for c in config_patterns[:10]])
        
        return CompressionAnalysis(
            content_type="technical_implementation",
            complexity_score=complexity_score,
            critical_elements=critical_elements,
            redundancy_score=0.3,  # Technical content typically has low redundancy
            compression_potential=0.6,  # Moderate compression potential
            recommended_strategy="technical_depth_preservation"
        )
    
    def compress(self, content: str, target_tokens: int, profile: CompressionProfile) -> CompressionResult:
        """Apply technical depth compression"""
        
        original_tokens = self._estimate_tokens(content)
        target_ratio = target_tokens / original_tokens if original_tokens > 0 else 1.0
        
        if target_ratio >= 1.0:
            return CompressionResult(
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                compression_ratio=1.0,
                quality_score=1.0,
                preservation_score=1.0,
                strategy_applied="no_compression_needed",
                optimization_notes=["Content already within target token limit"],
                fallback_used=False
            )
        
        # Preserve technical elements
        critical_elements = self.preserve_critical_elements(content, profile)
        
        # Separate technical from descriptive content
        technical_content, descriptive_content = self._separate_technical_content(content)
        
        # Apply different compression ratios
        technical_ratio = max(0.8, target_ratio + 0.2)  # Less compression for technical
        descriptive_ratio = max(0.4, target_ratio - 0.2)  # More compression for descriptive
        
        compressed_technical = self._compress_technical_content(technical_content, technical_ratio)
        compressed_descriptive = self._compress_descriptive_content(descriptive_content, descriptive_ratio)
        
        # Recombine content
        compressed_content = self._recombine_content(compressed_technical, compressed_descriptive)
        
        final_tokens = self._estimate_tokens(compressed_content)
        compression_ratio = final_tokens / original_tokens if original_tokens > 0 else 1.0
        quality_score = self._calculate_technical_quality_score(content, compressed_content)
        preservation_score = self._calculate_preservation_score(critical_elements, compressed_content)
        
        return CompressionResult(
            original_tokens=original_tokens,
            compressed_tokens=final_tokens,
            compression_ratio=compression_ratio,
            quality_score=quality_score,
            preservation_score=preservation_score,
            strategy_applied="technical_depth_preservation",
            optimization_notes=["Preserved technical implementation details", "Compressed descriptive content"],
            fallback_used=final_tokens > target_tokens
        )
    
    def preserve_critical_elements(self, content: str, profile: CompressionProfile) -> List[str]:
        """Preserve critical technical elements"""
        critical_elements = []
        
        # Code blocks (highest priority)
        code_blocks = re.findall(r'```[\s\S]*?```', content)
        critical_elements.extend([f"[CODE]:{block}" for block in code_blocks])
        
        # Function definitions and calls
        function_patterns = [
            r'def\s+\w+\([^)]*\):',
            r'class\s+\w+\([^)]*\):',
            r'@\w+\([^)]*\)',
            r'\w+\([^)]*\)\s*->'
        ]
        
        for pattern in function_patterns:
            matches = re.findall(pattern, content)
            critical_elements.extend([f"[FUNC]:{match}" for match in matches])
        
        # Configuration and constants
        config_patterns = [
            r'\w+\s*=\s*["\'].*?["\']',
            r'\w+\s*:\s*\d+',
            r'[A-Z_]+\s*=\s*.*'
        ]
        
        for pattern in config_patterns:
            matches = re.findall(pattern, content)
            critical_elements.extend([f"[CONFIG]:{match}" for match in matches[:5]])
        
        return critical_elements
    
    def _separate_technical_content(self, content: str) -> Tuple[str, str]:
        """Separate technical implementation from descriptive content"""
        lines = content.split('\n')
        technical_lines = []
        descriptive_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            
            # Technical indicators
            is_technical = (
                line_stripped.startswith(('def ', 'class ', 'import ', 'from ')) or
                '```' in line or
                re.match(r'^\s*\w+\s*[:=]', line) or
                re.search(r'\w+\([^)]*\)', line) or
                line_stripped.startswith(('#', '*', '-', '+')) or
                any(keyword in line_stripped.lower() for keyword in ['config', 'setup', 'install'])
            )
            
            if is_technical:
                technical_lines.append(line)
            else:
                descriptive_lines.append(line)
        
        return '\n'.join(technical_lines), '\n'.join(descriptive_lines)
    
    def _compress_technical_content(self, content: str, target_ratio: float) -> str:
        """Compress technical content with minimal information loss"""
        if not content.strip():
            return content
        
        lines = content.split('\n')
        target_lines = max(1, int(len(lines) * target_ratio))
        
        # Prioritize code blocks and function definitions
        priority_lines = []
        regular_lines = []
        
        for line in lines:
            if any(pattern in line for pattern in ['def ', 'class ', '```', 'import ']):
                priority_lines.append(line)
            else:
                regular_lines.append(line)
        
        # Keep all priority lines if possible, compress regular lines
        if len(priority_lines) <= target_lines:
            remaining_slots = target_lines - len(priority_lines)
            selected_regular = regular_lines[:remaining_slots]
            return '\n'.join(priority_lines + selected_regular)
        else:
            return '\n'.join(priority_lines[:target_lines])
    
    def _compress_descriptive_content(self, content: str, target_ratio: float) -> str:
        """Compress descriptive content more aggressively"""
        if not content.strip():
            return content
        
        sentences = content.split('. ')
        target_sentences = max(1, int(len(sentences) * target_ratio))
        
        # Score sentences by technical relevance
        sentence_scores = []
        for sentence in sentences:
            score = len(sentence.split())
            
            # Boost technical sentences
            if any(keyword in sentence.lower() for keyword in 
                   ['implement', 'configure', 'optimize', 'performance', 'security']):
                score *= 2
            
            sentence_scores.append((sentence, score))
        
        # Select highest scoring sentences
        selected = sorted(sentence_scores, key=lambda x: x[1], reverse=True)[:target_sentences]
        return '. '.join([s[0] for s in selected])
    
    def _recombine_content(self, technical: str, descriptive: str) -> str:
        """Recombine technical and descriptive content"""
        parts = []
        
        if technical.strip():
            parts.append("## Technical Implementation")
            parts.append(technical)
            parts.append("")
        
        if descriptive.strip():
            parts.append("## Description")
            parts.append(descriptive)
        
        return '\n'.join(parts)
    
    def _calculate_technical_quality_score(self, original: str, compressed: str) -> float:
        """Calculate quality score with emphasis on technical elements"""
        
        # Count preserved technical patterns
        technical_patterns = [
            r'```[\s\S]*?```',
            r'def\s+\w+\([^)]*\):',
            r'class\s+\w+\([^)]*\):',
            r'\w+\([^)]*\)',
            r'\w+\s*[:=]\s*\w+'
        ]
        
        original_technical = 0
        compressed_technical = 0
        
        for pattern in technical_patterns:
            original_matches = len(re.findall(pattern, original))
            compressed_matches = len(re.findall(pattern, compressed))
            
            original_technical += original_matches
            compressed_technical += compressed_matches
        
        if original_technical == 0:
            return 1.0
        
        return min(1.0, compressed_technical / original_technical)
    
    def _estimate_tokens(self, content: str) -> int:
        """Estimate token count from content"""
        return int(len(content.split()) * 1.3)
    
    def _calculate_preservation_score(self, critical_elements: List[str], compressed_content: str) -> float:
        """Calculate critical element preservation score"""
        if not critical_elements:
            return 1.0
        
        preserved_count = 0
        for element in critical_elements:
            element_content = element.split(':', 1)[-1]
            if element_content in compressed_content:
                preserved_count += 1
        
        return preserved_count / len(critical_elements)

class IntelligentCompressionEngine:
    """
    Main compression engine coordinating multiple strategies
    Implements domain-specific compression with quality preservation
    """
    
    def __init__(self):
        self.compression_profiles = self._initialize_compression_profiles()
        self.compression_strategies = self._initialize_compression_strategies()
        self.performance_metrics = {}
        
    def _initialize_compression_profiles(self) -> Dict[str, CompressionProfile]:
        """Initialize domain-specific compression profiles"""
        return {
            "backend": CompressionProfile(
                domain="backend",
                preservation_patterns=[
                    r'```[\s\S]*?```',  # Code blocks
                    r'def\s+\w+\([^)]*\):',  # Function definitions
                    r'class\s+\w+\([^)]*\):',  # Class definitions
                    r'@\w+\([^)]*\)',  # Decorators
                    r'/api/v\d+/\w+',  # API endpoints
                    r'\w+\s*=\s*["\'].*?["\']'  # Configuration
                ],
                compression_weights={
                    "code_blocks": 0.9,
                    "api_specs": 0.8,
                    "configuration": 0.7,
                    "documentation": 0.5,
                    "examples": 0.6
                },
                quality_thresholds={
                    "technical_preservation": 0.8,
                    "implementation_detail": 0.7,
                    "overall_coherence": 0.6
                },
                optimization_strategies=["technical_depth_preservation", "hierarchical_priority"],
                fallback_ratios=[0.8, 0.6, 0.4]
            ),
            "frontend": CompressionProfile(
                domain="frontend",
                preservation_patterns=[
                    r'```[\s\S]*?```',  # Code blocks
                    r'import\s+.*?from\s+["\'].*?["\']',  # Imports
                    r'export\s+(default\s+)?.*',  # Exports
                    r'function\s+\w+\([^)]*\)',  # Function definitions
                    r'const\s+\w+\s*=',  # Constants
                    r'@media\s*\([^)]*\)'  # CSS media queries
                ],
                compression_weights={
                    "component_structure": 0.9,
                    "styling_patterns": 0.7,
                    "interaction_logic": 0.8,
                    "documentation": 0.5,
                    "examples": 0.6
                },
                quality_thresholds={
                    "component_preservation": 0.8,
                    "interaction_detail": 0.7,
                    "visual_coherence": 0.6
                },
                optimization_strategies=["component_focused", "hierarchical_priority"],
                fallback_ratios=[0.75, 0.55, 0.35]
            ),
            "security": CompressionProfile(
                domain="security",
                preservation_patterns=[
                    r'```[\s\S]*?```',  # Code blocks
                    r'@require_auth\b',  # Auth decorators
                    r'verify_\w+\(',  # Verification functions
                    r'hash_\w+\(',  # Hashing functions
                    r'encrypt\w*\(',  # Encryption functions
                    r'OAuth2\w*',  # OAuth patterns
                    r'JWT\w*',  # JWT patterns
                    r'SSL|TLS|HTTPS'  # Security protocols
                ],
                compression_weights={
                    "auth_patterns": 0.95,
                    "encryption_details": 0.9,
                    "threat_analysis": 0.8,
                    "compliance_info": 0.7,
                    "examples": 0.6
                },
                quality_thresholds={
                    "security_preservation": 0.9,
                    "implementation_detail": 0.8,
                    "compliance_coverage": 0.7
                },
                optimization_strategies=["security_critical_preservation", "threat_focused"],
                fallback_ratios=[0.85, 0.65, 0.45]
            ),
            "performance": CompressionProfile(
                domain="performance",
                preservation_patterns=[
                    r'\d+\.\d+\s*(ms|sec|min)',  # Time measurements
                    r'\d+\.\d+%',  # Percentages
                    r'\d+\s*(MB|GB|KB)',  # Memory measurements
                    r'>\s*\d+',  # Thresholds
                    r'\d+\s*(requests|queries)/\w+',  # Rates
                    r'benchmark\w*',  # Benchmarking
                    r'profile\w*',  # Profiling
                    r'optimize\w*'  # Optimization
                ],
                compression_weights={
                    "metrics_data": 0.95,
                    "optimization_strategies": 0.85,
                    "bottleneck_analysis": 0.8,
                    "monitoring_setup": 0.7,
                    "examples": 0.6
                },
                quality_thresholds={
                    "metrics_preservation": 0.9,
                    "optimization_detail": 0.8,
                    "analysis_coherence": 0.7
                },
                optimization_strategies=["metrics_preservation", "data_focused"],
                fallback_ratios=[0.8, 0.6, 0.4]
            ),
            "infrastructure": CompressionProfile(
                domain="infrastructure",
                preservation_patterns=[
                    r'apiVersion:\s*\S+',  # K8s API versions
                    r'kind:\s*\w+',  # K8s resource kinds
                    r'image:\s*\S+',  # Container images
                    r'port:\s*\d+',  # Port configurations
                    r'replicas:\s*\d+',  # Replica counts
                    r'resources:\s*',  # Resource specifications
                    r'FROM\s+\w+',  # Dockerfile FROM
                    r'EXPOSE\s+\d+'  # Dockerfile EXPOSE
                ],
                compression_weights={
                    "deployment_config": 0.9,
                    "resource_specs": 0.85,
                    "monitoring_setup": 0.8,
                    "scaling_config": 0.75,
                    "examples": 0.6
                },
                quality_thresholds={
                    "config_preservation": 0.85,
                    "deployment_detail": 0.8,
                    "operational_coherence": 0.7
                },
                optimization_strategies=["config_preservation", "deployment_focused"],
                fallback_ratios=[0.8, 0.6, 0.4]
            )
        }
    
    def _initialize_compression_strategies(self) -> Dict[str, CompressionStrategy]:
        """Initialize compression strategy implementations"""
        return {
            "hierarchical_priority": HierarchicalCompressionStrategy(),
            "technical_depth_preservation": TechnicalDepthCompressionStrategy(),
            "component_focused": HierarchicalCompressionStrategy(),  # Could be specialized further
            "security_critical_preservation": TechnicalDepthCompressionStrategy(),  # Could be specialized
            "metrics_preservation": TechnicalDepthCompressionStrategy(),  # Could be specialized
            "config_preservation": TechnicalDepthCompressionStrategy()  # Could be specialized
        }
    
    def compress_content(self, content: str, target_tokens: int, domain: str, 
                        strategy_preference: Optional[str] = None) -> CompressionResult:
        """
        Compress content using intelligent domain-specific optimization
        """
        
        # Get domain profile
        profile = self.compression_profiles.get(domain, self.compression_profiles["backend"])
        
        # Determine optimal strategy
        if strategy_preference and strategy_preference in self.compression_strategies:
            strategy_name = strategy_preference
        else:
            strategy_name = self._select_optimal_strategy(content, target_tokens, profile)
        
        strategy = self.compression_strategies[strategy_name]
        
        # Analyze content first
        analysis = strategy.analyze_content(content, target_tokens / self._estimate_tokens(content))
        
        # Apply compression
        result = strategy.compress(content, target_tokens, profile)
        
        # Apply fallbacks if necessary
        if result.fallback_used and result.compressed_tokens > target_tokens:
            result = self._apply_fallback_compression(content, target_tokens, profile, strategy)
        
        # Update performance metrics
        self._update_performance_metrics(domain, strategy_name, result)
        
        return result
    
    def _select_optimal_strategy(self, content: str, target_tokens: int, profile: CompressionProfile) -> str:
        """Select optimal compression strategy based on content analysis"""
        
        # Analyze content characteristics
        code_density = len(re.findall(r'```[\s\S]*?```', content)) / max(1, len(content.split('\n')))
        technical_density = len(re.findall(r'\w+\([^)]*\)', content)) / max(1, len(content.split()))
        structure_density = len(re.findall(r'^#+\s', content, re.MULTILINE)) / max(1, len(content.split('\n')))
        
        # Strategy selection logic
        if code_density > 0.3 or technical_density > 0.1:
            return "technical_depth_preservation"
        elif structure_density > 0.1:
            return "hierarchical_priority"
        else:
            # Use first strategy from profile
            return profile.optimization_strategies[0] if profile.optimization_strategies else "hierarchical_priority"
    
    def _apply_fallback_compression(self, content: str, target_tokens: int, 
                                  profile: CompressionProfile, original_strategy: CompressionStrategy) -> CompressionResult:
        """Apply fallback compression ratios when primary strategy fails to meet target"""
        
        best_result = None
        
        for fallback_ratio in profile.fallback_ratios:
            adjusted_target = int(target_tokens * fallback_ratio)
            
            # Try compression with adjusted target
            result = original_strategy.compress(content, adjusted_target, profile)
            
            if result.compressed_tokens <= target_tokens:
                result.fallback_used = True
                result.optimization_notes.append(f"Applied fallback compression ratio: {fallback_ratio}")
                return result
            
            if best_result is None or result.compressed_tokens < best_result.compressed_tokens:
                best_result = result
        
        # Return best result even if it doesn't meet target
        if best_result:
            best_result.fallback_used = True
            best_result.optimization_notes.append("Applied maximum fallback compression")
            return best_result
        
        # Should not reach here, but return minimal result
        return CompressionResult(
            original_tokens=self._estimate_tokens(content),
            compressed_tokens=target_tokens,
            compression_ratio=target_tokens / self._estimate_tokens(content),
            quality_score=0.5,
            preservation_score=0.3,
            strategy_applied="emergency_fallback",
            optimization_notes=["Emergency fallback compression applied"],
            fallback_used=True
        )
    
    def _update_performance_metrics(self, domain: str, strategy: str, result: CompressionResult):
        """Update performance metrics for continuous improvement"""
        
        if domain not in self.performance_metrics:
            self.performance_metrics[domain] = {}
        
        if strategy not in self.performance_metrics[domain]:
            self.performance_metrics[domain][strategy] = {
                "usage_count": 0,
                "avg_compression_ratio": 0.0,
                "avg_quality_score": 0.0,
                "avg_preservation_score": 0.0,
                "success_rate": 0.0
            }
        
        metrics = self.performance_metrics[domain][strategy]
        metrics["usage_count"] += 1
        
        # Update running averages
        n = metrics["usage_count"]
        metrics["avg_compression_ratio"] = ((n-1) * metrics["avg_compression_ratio"] + result.compression_ratio) / n
        metrics["avg_quality_score"] = ((n-1) * metrics["avg_quality_score"] + result.quality_score) / n
        metrics["avg_preservation_score"] = ((n-1) * metrics["avg_preservation_score"] + result.preservation_score) / n
        
        # Success rate (quality > 0.6 and preservation > 0.5)
        success = 1.0 if result.quality_score > 0.6 and result.preservation_score > 0.5 else 0.0
        metrics["success_rate"] = ((n-1) * metrics["success_rate"] + success) / n
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate performance report for compression strategies"""
        return {
            "compression_performance": self.performance_metrics,
            "strategy_recommendations": self._generate_strategy_recommendations(),
            "optimization_opportunities": self._identify_optimization_opportunities()
        }
    
    def _generate_strategy_recommendations(self) -> Dict[str, str]:
        """Generate strategy recommendations based on performance metrics"""
        recommendations = {}
        
        for domain, strategies in self.performance_metrics.items():
            best_strategy = None
            best_score = 0.0
            
            for strategy, metrics in strategies.items():
                # Combined score: quality + preservation + success rate
                combined_score = (
                    metrics["avg_quality_score"] * 0.4 +
                    metrics["avg_preservation_score"] * 0.3 +
                    metrics["success_rate"] * 0.3
                )
                
                if combined_score > best_score:
                    best_score = combined_score
                    best_strategy = strategy
            
            if best_strategy:
                recommendations[domain] = best_strategy
        
        return recommendations
    
    def _identify_optimization_opportunities(self) -> List[str]:
        """Identify opportunities for compression optimization"""
        opportunities = []
        
        for domain, strategies in self.performance_metrics.items():
            for strategy, metrics in strategies.items():
                if metrics["avg_quality_score"] < 0.6:
                    opportunities.append(f"Improve quality for {domain}:{strategy}")
                
                if metrics["avg_preservation_score"] < 0.5:
                    opportunities.append(f"Improve preservation for {domain}:{strategy}")
                
                if metrics["success_rate"] < 0.7:
                    opportunities.append(f"Optimize success rate for {domain}:{strategy}")
        
        return opportunities
    
    def _estimate_tokens(self, content: str) -> int:
        """Estimate token count from content"""
        return int(len(content.split()) * 1.3)

def main():
    """Test the intelligent compression engine"""
    
    # Initialize compression engine
    engine = IntelligentCompressionEngine()
    
    # Test content
    test_content = """
# Backend API Implementation

## Core Architecture
The backend follows a microservices architecture with FastAPI as the main framework.

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class UserModel(BaseModel):
    id: int
    name: str
    email: str

@app.get("/api/v1/users/{user_id}")
async def get_user(user_id: int):
    # Implementation details
    user = await fetch_user_from_database(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

## Database Integration
The system uses PostgreSQL with SQLAlchemy ORM for data persistence.

Configuration settings:
- DATABASE_URL = "postgresql://user:pass@localhost:5432/db"
- CONNECTION_POOL_SIZE = 20
- MAX_OVERFLOW = 30

## Security Patterns
Authentication is handled through JWT tokens with refresh token rotation.

```python
from jose import jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

## Performance Considerations
The API handles approximately 10,000 requests per minute with average response time of 150ms.

Key metrics:
- Average response time: 150ms
- 95th percentile response time: 300ms
- Memory usage: 2.5GB
- CPU utilization: 65%

Optimization strategies include connection pooling, query optimization, and Redis caching for frequently accessed data.
"""
    
    # Test compression for different domains and targets
    test_cases = [
        ("backend", 2000, None),
        ("backend", 1500, "technical_depth_preservation"),
        ("security", 1000, None),
        ("performance", 800, "metrics_preservation")
    ]
    
    print("=== Intelligent Compression Engine Test ===\n")
    
    for domain, target_tokens, strategy in test_cases:
        print(f"Testing {domain} compression (target: {target_tokens} tokens, strategy: {strategy or 'auto'})")
        
        result = engine.compress_content(test_content, target_tokens, domain, strategy)
        
        print(f"  Original tokens: {result.original_tokens}")
        print(f"  Compressed tokens: {result.compressed_tokens}")
        print(f"  Compression ratio: {result.compression_ratio:.2f}")
        print(f"  Quality score: {result.quality_score:.2f}")
        print(f"  Preservation score: {result.preservation_score:.2f}")
        print(f"  Strategy applied: {result.strategy_applied}")
        print(f"  Fallback used: {result.fallback_used}")
        print(f"  Optimization notes: {result.optimization_notes}")
        print()
    
    # Performance report
    print("=== Performance Report ===")
    performance_report = engine.get_performance_report()
    print(json.dumps(performance_report, indent=2))
    
    print("\n=== Intelligent Compression Engine Implementation Complete ===")

if __name__ == "__main__":
    main()