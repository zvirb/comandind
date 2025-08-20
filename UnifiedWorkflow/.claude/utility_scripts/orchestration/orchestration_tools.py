# orchestration_tools.py
"""
Enhanced orchestration tools integrated with existing workflow
Provides knowledge graph client, checkpoint system, and document compression
"""

import subprocess
import json
import atexit
import re
import os
from datetime import datetime
from pathlib import Path
import hashlib

class OrchestrationKnowledgeClient:
    """
    Manages and communicates with the orchestration knowledge graph server subprocess.
    Integrates with existing enhanced orchestration workflow.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(OrchestrationKnowledgeClient, cls).__new__(cls)
        return cls._instance

    def __init__(self, server_script_path: str = './orchestration_knowledge_server.py'):
        if not hasattr(self, 'process'):
            print("Starting Orchestration Knowledge Graph MCP Server subprocess...")
            self.process = subprocess.Popen(
                [server_script_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            atexit.register(self.terminate)

    def query_knowledge(self, entity: str) -> dict:
        """Query the orchestration knowledge graph for context and solutions."""
        if self.process.poll() is not None:
            error_output = self.process.stderr.read()
            raise RuntimeError(f"The orchestration KG server process has terminated. Stderr: {error_output}")
        
        try:
            self.process.stdin.write(entity + '\n')
            self.process.stdin.flush()
            response_line = self.process.stdout.readline()
            return json.loads(response_line)
        except (BrokenPipeError, json.JSONDecodeError) as e:
            raise RuntimeError(f"Failed to communicate with the orchestration KG server: {e}")

    def query_checkpoint(self, checkpoint_id: str) -> dict:
        """Query for checkpoint data."""
        try:
            self.process.stdin.write(f"CHECKPOINT:{checkpoint_id}\n")
            self.process.stdin.flush()
            response_line = self.process.stdout.readline()
            return json.loads(response_line)
        except (BrokenPipeError, json.JSONDecodeError) as e:
            raise RuntimeError(f"Failed to retrieve checkpoint: {e}")

    def terminate(self):
        """Terminate the server subprocess."""
        if hasattr(self, 'process') and self.process.poll() is None:
            print("Terminating Orchestration Knowledge Graph MCP Server subprocess...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()

class OrchestrationCheckpointManager:
    """
    Checkpoint system for orchestration workflows to enable recovery and prevent recursive errors.
    """
    def __init__(self, checkpoint_dir: str = "/home/marku/ai_workflow_engine/orchestration_checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)
        self.current_workflow_id = None
        
    def create_checkpoint(self, phase: str, state: dict, workflow_id: str = None) -> str:
        """Create a checkpoint for the current orchestration state."""
        if workflow_id:
            self.current_workflow_id = workflow_id
        elif not self.current_workflow_id:
            self.current_workflow_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            
        checkpoint_id = f"{self.current_workflow_id}_{phase}"
        checkpoint_data = {
            "checkpoint_id": checkpoint_id,
            "workflow_id": self.current_workflow_id,
            "phase": phase,
            "timestamp": datetime.now().isoformat(),
            "state": state,
            "state_hash": hashlib.md5(json.dumps(state, sort_keys=True).encode()).hexdigest()
        }
        
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
            
        return checkpoint_id
    
    def load_checkpoint(self, checkpoint_id: str) -> dict:
        """Load a checkpoint by ID."""
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
        if checkpoint_file.exists():
            with open(checkpoint_file, 'r') as f:
                return json.load(f)
        return None
    
    def list_checkpoints(self, workflow_id: str = None) -> list:
        """List all checkpoints for a workflow or all workflows."""
        checkpoints = []
        pattern = f"{workflow_id}_*.json" if workflow_id else "*.json"
        
        for checkpoint_file in self.checkpoint_dir.glob(pattern):
            try:
                with open(checkpoint_file, 'r') as f:
                    checkpoint_data = json.load(f)
                checkpoints.append(checkpoint_data)
            except Exception as e:
                print(f"Error loading checkpoint {checkpoint_file}: {e}")
                
        return sorted(checkpoints, key=lambda x: x['timestamp'])
    
    def get_rollback_checkpoint(self, current_phase: str) -> dict:
        """Get the most appropriate checkpoint for rollback."""
        checkpoints = self.list_checkpoints(self.current_workflow_id)
        
        # Find the last successful checkpoint before current phase
        phase_order = ["phase_0", "phase_1", "phase_2", "phase_2_5", "phase_3", "phase_4", "phase_5", "phase_6"]
        current_index = phase_order.index(current_phase) if current_phase in phase_order else -1
        
        for checkpoint in reversed(checkpoints):
            checkpoint_phase_index = phase_order.index(checkpoint['phase']) if checkpoint['phase'] in phase_order else -1
            if checkpoint_phase_index < current_index:
                return checkpoint
                
        return None

class DocumentCompressionAgent:
    """
    Intelligent document compression agent for managing large context files
    Prevents context overflow while preserving essential information
    """
    
    def __init__(self, max_tokens: int = 8000):
        self.max_tokens = max_tokens
        self.compression_strategies = {
            "summarize_sections": self._summarize_sections,
            "extract_key_points": self._extract_key_points,
            "hierarchical_compress": self._hierarchical_compress,
            "technical_compress": self._technical_compress
        }
    
    def compress_document(self, content: str, target_tokens: int = None, strategy: str = "technical_compress") -> dict:
        """
        Compress a document using the specified strategy while preserving critical information.
        """
        if target_tokens is None:
            target_tokens = self.max_tokens
            
        current_tokens = self._estimate_tokens(content)
        
        if current_tokens <= target_tokens:
            return {
                "status": "no_compression_needed",
                "original_tokens": current_tokens,
                "compressed_content": content,
                "compression_ratio": 1.0
            }
        
        compression_func = self.compression_strategies.get(strategy, self._technical_compress)
        compressed_content = compression_func(content, target_tokens)
        compressed_tokens = self._estimate_tokens(compressed_content)
        
        return {
            "status": "compressed",
            "original_tokens": current_tokens,
            "compressed_tokens": compressed_tokens,
            "compression_ratio": compressed_tokens / current_tokens,
            "compressed_content": compressed_content,
            "strategy_used": strategy
        }
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (1 token ≈ 4 characters)."""
        return len(text) // 4
    
    def _technical_compress(self, content: str, target_tokens: int) -> str:
        """Technical document compression preserving code, errors, and solutions."""
        lines = content.split('\n')
        
        # Priority preservation patterns
        high_priority_patterns = [
            r'```.*?```',  # Code blocks
            r'ERROR:.*',   # Error messages
            r'CRITICAL:.*', # Critical messages
            r'✅.*',       # Success markers
            r'❌.*',       # Failure markers
            r'Phase \d+:', # Phase markers
            r'##\s.*',     # Headers
            r'\*\*.*?\*\*' # Bold text
        ]
        
        # Extract high priority content
        priority_content = []
        remaining_content = []
        
        for line in lines:
            is_priority = any(re.search(pattern, line, re.DOTALL) for pattern in high_priority_patterns)
            if is_priority:
                priority_content.append(line)
            else:
                remaining_content.append(line)
        
        # Build compressed version
        compressed_lines = priority_content.copy()
        
        # Add remaining content until target is reached
        remaining_tokens = target_tokens - self._estimate_tokens('\n'.join(compressed_lines))
        
        for line in remaining_content:
            line_tokens = self._estimate_tokens(line)
            if remaining_tokens >= line_tokens:
                compressed_lines.append(line)
                remaining_tokens -= line_tokens
            else:
                # Add truncated line if space allows
                if remaining_tokens > 20:
                    truncated = line[:remaining_tokens * 4 - 3] + "..."
                    compressed_lines.append(truncated)
                break
        
        return '\n'.join(compressed_lines)
    
    def _summarize_sections(self, content: str, target_tokens: int) -> str:
        """Summarize sections while preserving structure."""
        sections = re.split(r'\n#{1,3}\s', content)
        compressed_sections = []
        
        available_tokens = target_tokens
        
        for section in sections:
            section_tokens = self._estimate_tokens(section)
            if section_tokens <= available_tokens:
                compressed_sections.append(section)
                available_tokens -= section_tokens
            else:
                # Summarize section
                lines = section.split('\n')
                summary_lines = lines[:min(3, len(lines))]  # Keep first 3 lines
                summary_lines.append(f"[... {len(lines) - 3} more lines compressed ...]")
                compressed_section = '\n'.join(summary_lines)
                compressed_sections.append(compressed_section)
                available_tokens -= self._estimate_tokens(compressed_section)
                
            if available_tokens <= 0:
                break
                
        return '\n# '.join(compressed_sections)
    
    def _extract_key_points(self, content: str, target_tokens: int) -> str:
        """Extract key points and critical information."""
        # Extract lines with key indicators
        key_patterns = [
            r'.*(?:CRITICAL|ERROR|FAILED|SUCCESS|✅|❌).*',
            r'.*(?:Root Cause|Solution|Fix|Implementation).*',
            r'.*(?:Phase \d+|Step \d+).*',
            r'.*\*\*.*?\*\*.*',  # Bold text
            r'```.*?```'  # Code blocks
        ]
        
        lines = content.split('\n')
        key_lines = []
        
        for line in lines:
            if any(re.search(pattern, line, re.IGNORECASE | re.DOTALL) for pattern in key_patterns):
                key_lines.append(line)
        
        # Truncate to target tokens
        result_lines = []
        current_tokens = 0
        
        for line in key_lines:
            line_tokens = self._estimate_tokens(line)
            if current_tokens + line_tokens <= target_tokens:
                result_lines.append(line)
                current_tokens += line_tokens
            else:
                break
                
        return '\n'.join(result_lines)
    
    def _hierarchical_compress(self, content: str, target_tokens: int) -> str:
        """Hierarchical compression maintaining document structure."""
        # Split by headers
        sections = re.split(r'\n(#{1,6}\s.*)', content)
        
        compressed_parts = []
        available_tokens = target_tokens
        
        i = 0
        while i < len(sections) and available_tokens > 0:
            section = sections[i]
            section_tokens = self._estimate_tokens(section)
            
            if section_tokens <= available_tokens:
                compressed_parts.append(section)
                available_tokens -= section_tokens
            else:
                # Compress this section
                if section.startswith('#'):
                    # Keep header
                    compressed_parts.append(section)
                    available_tokens -= self._estimate_tokens(section)
                else:
                    # Compress content
                    lines = section.split('\n')
                    key_lines = [line for line in lines if 
                                any(keyword in line.lower() for keyword in 
                                    ['error', 'critical', 'solution', 'fix', 'implementation', 'phase'])]
                    
                    compressed_content = '\n'.join(key_lines[:10])  # Top 10 key lines
                    if self._estimate_tokens(compressed_content) <= available_tokens:
                        compressed_parts.append(compressed_content)
                        available_tokens -= self._estimate_tokens(compressed_content)
            
            i += 1
            
        return ''.join(compressed_parts)

# Instantiate the global components
kg_client = OrchestrationKnowledgeClient()
checkpoint_manager = OrchestrationCheckpointManager()
doc_compressor = DocumentCompressionAgent()

# Tool functions for enhanced orchestration workflow
def query_orchestration_knowledge(entity: str) -> str:
    """
    Query the orchestration knowledge graph for contextual information about errors,
    patterns, and solutions. Enhanced with orchestration-specific context.
    """
    print(f"--- TOOL: Querying Orchestration KG for entity: '{entity}' ---")
    response = kg_client.query_knowledge(entity)
    return json.dumps(response)

def create_orchestration_checkpoint(phase: str, state: dict, workflow_id: str = None) -> str:
    """
    Create a checkpoint in the orchestration workflow for recovery and rollback capabilities.
    """
    print(f"--- TOOL: Creating orchestration checkpoint for phase: '{phase}' ---")
    checkpoint_id = checkpoint_manager.create_checkpoint(phase, state, workflow_id)
    return f"Checkpoint created: {checkpoint_id}"

def load_orchestration_checkpoint(checkpoint_id: str) -> str:
    """
    Load a previously created orchestration checkpoint for recovery.
    """
    print(f"--- TOOL: Loading orchestration checkpoint: '{checkpoint_id}' ---")
    checkpoint_data = checkpoint_manager.load_checkpoint(checkpoint_id)
    return json.dumps(checkpoint_data)

def compress_orchestration_document(content: str, target_tokens: int = 8000, strategy: str = "technical_compress") -> str:
    """
    Compress large documents while preserving critical orchestration information.
    Strategies: summarize_sections, extract_key_points, hierarchical_compress, technical_compress
    """
    print(f"--- TOOL: Compressing document with strategy: '{strategy}' ---")
    result = doc_compressor.compress_document(content, target_tokens, strategy)
    return json.dumps(result)

def extract_orchestration_entities(text: str) -> str:
    """
    Extract key orchestration entities such as error patterns, phase indicators,
    agent names, and technical components from orchestration logs or reports.
    """
    print(f"--- TOOL: Extracting orchestration entities from text ---")
    
    # Enhanced patterns for orchestration context
    patterns = {
        "errors": r"(?i)(error|exception|fail|critical)[\w\s]*(?:\w+error|\w+exception)",
        "phases": r"Phase\s+\d+(?:\.\d+)?:?\s*[\w\s]+",
        "agents": r"(?i)(agent|specialist|orchestrator)[\w\s-]*(?:agent|specialist|orchestrator)",
        "http_codes": r"\b[45]\d{2}\b",
        "technical_terms": r"\b[A-Z][a-z]+[A-Z][A-Za-z]*\b",
        "file_paths": r"[/\\][\w/\\.-]+\.[a-zA-Z]{2,4}",
        "functions": r"\b\w+\([^)]*\)",
        "success_markers": r"[✅❌]\s*[\w\s]+",
        "database_terms": r"(?i)(database|sql|postgresql|async|sync|session|connection)",
        "auth_terms": r"(?i)(auth|csrf|jwt|token|login|permission)"
    }
    
    entities = {}
    for category, pattern in patterns.items():
        matches = re.findall(pattern, text)
        if matches:
            entities[category] = list(set(matches))
    
    # Flatten and deduplicate
    all_entities = []
    for category_entities in entities.values():
        all_entities.extend(category_entities)
    
    unique_entities = list(set(all_entities))
    
    return json.dumps({
        "categorized_entities": entities,
        "all_entities": unique_entities,
        "total_count": len(unique_entities)
    })

def get_rollback_checkpoint(current_phase: str) -> str:
    """
    Get the most appropriate checkpoint for rolling back from current phase.
    """
    print(f"--- TOOL: Finding rollback checkpoint for phase: '{current_phase}' ---")
    checkpoint = checkpoint_manager.get_rollback_checkpoint(current_phase)
    return json.dumps(checkpoint)

# List of all enhanced orchestration tools
available_orchestration_tools = [
    query_orchestration_knowledge,
    create_orchestration_checkpoint,
    load_orchestration_checkpoint,
    compress_orchestration_document,
    extract_orchestration_entities,
    get_rollback_checkpoint
]