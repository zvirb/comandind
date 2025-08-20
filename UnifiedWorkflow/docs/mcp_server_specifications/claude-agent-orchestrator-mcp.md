# Claude Agent Orchestrator MCP Server Specification
**Version:** 1.0  
**Date:** 2025-08-08  
**Purpose:** Complete MCP server implementation for 36-agent orchestration system

---

## 🎯 **Overview**

The Claude Agent Orchestrator MCP Server enables the complete 6-phase orchestration workflow with 36 specialized agents, advanced orchestration tools, and context management capabilities. This server bridges the gap between Claude Code's Task tool limitations and the comprehensive agent ecosystem defined in CLAUDE.md.

### **Core Capabilities**
- **36 Specialized Agents** accessible via MCP tools
- **11 Orchestration Tools** for advanced workflow management
- **Context Package Management** with intelligent compression
- **Phase-Based Workflow Coordination** with checkpoints and rollback
- **Knowledge Graph Integration** for historical pattern matching
- **Evidence-Based Validation** with audit trails

---

## 🏗️ **MCP Server Architecture**

### **Server Information**
```json
{
  "name": "claude-agent-orchestrator",
  "version": "1.0.0",
  "description": "Comprehensive agent orchestration system for Claude Code",
  "author": "AI Workflow Engine Team",
  "license": "MIT"
}
```

### **Core Components**
```yaml
components:
  agent_registry:
    purpose: Load and manage 36 specialized agents
    data_source: .claude/agents/*.md files
    validation: Agent specification compliance
    
  orchestration_engine:
    purpose: Phase-based workflow coordination
    phases: [0, 1, 2, 2.5, 3, 4, 5, 6]
    checkpoint_management: Auto-save and rollback
    
  context_manager:
    purpose: Context package creation and compression
    max_package_size: 4000_tokens
    compression_algorithm: intelligent_semantic_compression
    
  knowledge_graph:
    purpose: Historical pattern storage and retrieval
    storage: Neo4j or JSON files
    query_engine: Pattern matching and failure analysis
    
  evidence_system:
    purpose: Validation tracking and audit trails
    validation_types: [agent_claims, actual_outcomes, evidence_quality]
    audit_framework: MAST failure taxonomy integration
```

---

## 🔧 **MCP Tool Specifications**

### **1. Agent Execution Tools**

#### **call_agent**
```json
{
  "name": "call_agent",
  "description": "Execute a specialized agent with context package and coordination metadata",
  "inputSchema": {
    "type": "object",
    "properties": {
      "agent_name": {
        "type": "string",
        "enum": [
          "agent-integration-orchestrator", "project-orchestrator", "enhanced-nexus-synthesis-agent",
          "backend-gateway-expert", "schema-database-expert", "python-refactoring-architect", "codebase-research-analyst",
          "frictionless-ux-architect", "webui-architect", "whimsy-ui-creator", "ui-regression-debugger",
          "fullstack-communication-auditor", "security-validator", "test-automation-engineer", "production-endpoint-validator", "evidence-auditor",
          "performance-profiler", "deployment-orchestrator", "monitoring-analyst", "dependency-analyzer", "infrastructure-orchestrator",
          "documentation-specialist", "document-compression-agent", "nexus-synthesis-agent",
          "google-services-integrator", "langgraph-ollama-analyst",
          "security-orchestrator", "security-vulnerability-scanner", "code-quality-guardian",
          "project-janitor", "data-orchestrator", "meta-orchestrator",
          "orchestration-auditor", "orchestration-auditor-v2", "orchestration-phase0"
        ],
        "description": "Name of the specialized agent to execute"
      },
      "task_description": {
        "type": "string",
        "description": "Detailed task description for the agent"
      },
      "context_package": {
        "type": "object",
        "properties": {
          "technical_context": {"type": "string"},
          "coordination_metadata": {"type": "object"},
          "constraints": {"type": "object"},
          "success_criteria": {"type": "array"}
        },
        "description": "Compressed context package (max 4000 tokens)"
      },
      "phase": {
        "type": "string",
        "enum": ["0", "1", "2", "2.5", "3", "4", "5", "6"],
        "description": "Current orchestration phase"
      },
      "parallel_execution": {
        "type": "boolean",
        "default": false,
        "description": "Whether this agent is part of parallel execution group"
      },
      "evidence_requirements": {
        "type": "object",
        "properties": {
          "validation_type": {"type": "string"},
          "evidence_format": {"type": "string"},
          "success_metrics": {"type": "array"}
        }
      }
    },
    "required": ["agent_name", "task_description", "context_package", "phase"]
  }
}
```

#### **call_agents_parallel**
```json
{
  "name": "call_agents_parallel",
  "description": "Execute multiple agents simultaneously with coordinated context packages",
  "inputSchema": {
    "type": "object",
    "properties": {
      "agent_calls": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "agent_name": {"type": "string"},
            "task_description": {"type": "string"},
            "context_package": {"type": "object"},
            "priority": {"type": "string", "enum": ["critical", "high", "medium", "low"]}
          }
        }
      },
      "phase": {"type": "string"},
      "coordination_strategy": {
        "type": "object",
        "properties": {
          "synchronization_points": {"type": "array"},
          "failure_handling": {"type": "string"},
          "resource_allocation": {"type": "object"}
        }
      },
      "max_parallel": {
        "type": "number",
        "default": 5,
        "description": "Maximum agents to run simultaneously"
      }
    },
    "required": ["agent_calls", "phase"]
  }
}
```

### **2. Orchestration Tools**

#### **query_orchestration_knowledge**
```json
{
  "name": "query_orchestration_knowledge",
  "description": "Query orchestration knowledge graph for historical patterns and solutions",
  "inputSchema": {
    "type": "object",
    "properties": {
      "entity": {"type": "string", "description": "Error pattern, agent name, or solution type to query"},
      "query_type": {
        "type": "string",
        "enum": ["error_pattern", "successful_solution", "agent_performance", "failure_cascade"]
      },
      "context": {"type": "object", "description": "Additional context for pattern matching"},
      "time_range": {"type": "string", "description": "Time range for historical data (e.g., 'last_30_days')"}
    },
    "required": ["entity", "query_type"]
  }
}
```

#### **create_orchestration_checkpoint**
```json
{
  "name": "create_orchestration_checkpoint",
  "description": "Create recovery checkpoint before critical operations",
  "inputSchema": {
    "type": "object",
    "properties": {
      "phase": {"type": "string", "description": "Current orchestration phase"},
      "state": {
        "type": "object",
        "properties": {
          "agent_states": {"type": "object"},
          "context_packages": {"type": "object"},
          "execution_metadata": {"type": "object"},
          "validation_status": {"type": "object"}
        }
      },
      "checkpoint_type": {
        "type": "string", 
        "enum": ["phase_start", "critical_operation", "validation_point", "failure_recovery"]
      },
      "description": {"type": "string"}
    },
    "required": ["phase", "state", "checkpoint_type"]
  }
}
```

#### **load_orchestration_checkpoint**
```json
{
  "name": "load_orchestration_checkpoint",
  "description": "Load previous checkpoint for rollback recovery",
  "inputSchema": {
    "type": "object",
    "properties": {
      "checkpoint_id": {"type": "string", "description": "Unique checkpoint identifier"},
      "recovery_mode": {
        "type": "string",
        "enum": ["full_rollback", "partial_recovery", "state_merge"],
        "default": "full_rollback"
      },
      "selective_recovery": {
        "type": "object",
        "properties": {
          "agents_to_recover": {"type": "array"},
          "contexts_to_restore": {"type": "array"},
          "validation_to_reset": {"type": "array"}
        }
      }
    },
    "required": ["checkpoint_id"]
  }
}
```

#### **compress_orchestration_document**
```json
{
  "name": "compress_orchestration_document",
  "description": "Intelligent compression of large documents preventing token overflow",
  "inputSchema": {
    "type": "object",
    "properties": {
      "content": {"type": "string", "description": "Content to compress"},
      "target_tokens": {
        "type": "number", 
        "default": 4000,
        "description": "Target token count after compression"
      },
      "compression_strategy": {
        "type": "string",
        "enum": ["semantic_preserve", "hierarchical_summary", "critical_info_only"],
        "default": "semantic_preserve"
      },
      "preserve_sections": {
        "type": "array",
        "description": "Section types to preserve during compression"
      },
      "agent_context": {
        "type": "string",
        "description": "Target agent name for context-specific compression"
      }
    },
    "required": ["content", "target_tokens"]
  }
}
```

#### **extract_orchestration_entities**
```json
{
  "name": "extract_orchestration_entities",
  "description": "Extract key entities from logs, errors, and reports",
  "inputSchema": {
    "type": "object",
    "properties": {
      "text": {"type": "string", "description": "Text to analyze"},
      "entity_types": {
        "type": "array",
        "items": {
          "type": "string",
          "enum": ["error_patterns", "agent_names", "failure_modes", "success_indicators", "performance_metrics"]
        },
        "default": ["error_patterns", "agent_names", "failure_modes"]
      },
      "extraction_depth": {
        "type": "string",
        "enum": ["surface", "detailed", "comprehensive"],
        "default": "detailed"
      }
    },
    "required": ["text"]
  }
}
```

#### **search_knowledge_graph_for_patterns**
```json
{
  "name": "search_knowledge_graph_for_patterns",
  "description": "Query knowledge graph for historically successful solutions to similar error patterns",
  "inputSchema": {
    "type": "object",
    "properties": {
      "error_name": {"type": "string", "description": "Specific error or failure pattern name"},
      "error_context": {
        "type": "object",
        "properties": {
          "error_type": {"type": "string"},
          "affected_systems": {"type": "array"},
          "severity": {"type": "string"},
          "frequency": {"type": "string"}
        }
      },
      "solution_criteria": {
        "type": "object",
        "properties": {
          "min_success_rate": {"type": "number", "default": 0.8},
          "recency_weight": {"type": "number", "default": 0.3},
          "similarity_threshold": {"type": "number", "default": 0.7}
        }
      }
    },
    "required": ["error_name"]
  }
}
```

#### **check_memory_for_past_failures**
```json
{
  "name": "check_memory_for_past_failures",
  "description": "Validate patterns haven't failed recently using mem0 integration",
  "inputSchema": {
    "type": "object",
    "properties": {
      "pattern_description": {"type": "string", "description": "Description of the pattern or solution to validate"},
      "lookback_period": {
        "type": "string",
        "default": "30_days",
        "description": "How far back to check for failures"
      },
      "failure_threshold": {
        "type": "number",
        "default": 0.2,
        "description": "Failure rate threshold to consider pattern risky"
      },
      "context_similarity": {
        "type": "number",
        "default": 0.8,
        "description": "Minimum context similarity for failure comparison"
      }
    },
    "required": ["pattern_description"]
  }
}
```

#### **record_orchestration_outcome**
```json
{
  "name": "record_orchestration_outcome",
  "description": "Record workflow outcomes for continuous learning",
  "inputSchema": {
    "type": "object",
    "properties": {
      "pattern": {"type": "string", "description": "Pattern or solution that was attempted"},
      "success": {"type": "boolean", "description": "Whether the pattern was successful"},
      "details": {
        "type": "object",
        "properties": {
          "execution_time": {"type": "number"},
          "agents_involved": {"type": "array"},
          "evidence_quality": {"type": "number"},
          "failure_modes": {"type": "array"},
          "success_factors": {"type": "array"}
        }
      },
      "context": {
        "type": "object",
        "description": "Context information for future pattern matching"
      },
      "lessons_learned": {"type": "array", "description": "Key insights for future improvements"}
    },
    "required": ["pattern", "success", "details"]
  }
}
```

#### **get_agent_coordination_strategy**
```json
{
  "name": "get_agent_coordination_strategy",
  "description": "Generate optimal coordination strategy based on current agent states and error context",
  "inputSchema": {
    "type": "object",
    "properties": {
      "agents_status": {
        "type": "object",
        "description": "Current status of all agents"
      },
      "error_context": {
        "type": "object",
        "properties": {
          "error_type": {"type": "string"},
          "affected_systems": {"type": "array"},
          "urgency": {"type": "string"},
          "complexity": {"type": "string"}
        }
      },
      "resource_constraints": {
        "type": "object",
        "properties": {
          "max_parallel_agents": {"type": "number"},
          "time_constraints": {"type": "string"},
          "resource_availability": {"type": "object"}
        }
      },
      "success_criteria": {"type": "array"}
    },
    "required": ["agents_status", "error_context"]
  }
}
```

#### **validate_specialist_scope**
```json
{
  "name": "validate_specialist_scope",
  "description": "Prevent scope explosion by validating specialist actions don't exceed boundaries",
  "inputSchema": {
    "type": "object",
    "properties": {
      "agent_name": {"type": "string", "description": "Name of the agent to validate"},
      "proposed_actions": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "action_type": {"type": "string"},
            "scope": {"type": "string"},
            "resources_required": {"type": "array"},
            "dependencies": {"type": "array"}
          }
        }
      },
      "agent_boundaries": {
        "type": "object",
        "description": "Defined boundaries for the specific agent"
      },
      "context_package_limits": {
        "type": "object",
        "description": "Constraints from the agent's context package"
      }
    },
    "required": ["agent_name", "proposed_actions"]
  }
}
```

### **3. Context Management Tools**

#### **create_context_package**
```json
{
  "name": "create_context_package",
  "description": "Create compressed context package for specific agent",
  "inputSchema": {
    "type": "object",
    "properties": {
      "target_agent": {"type": "string"},
      "full_context": {"type": "string", "description": "Complete context information"},
      "package_type": {
        "type": "string",
        "enum": ["strategic", "technical", "frontend", "security", "performance", "database"]
      },
      "coordination_metadata": {
        "type": "object",
        "properties": {
          "parallel_agents": {"type": "array"},
          "synchronization_points": {"type": "array"},
          "handoff_requirements": {"type": "object"}
        }
      },
      "max_tokens": {"type": "number", "default": 4000}
    },
    "required": ["target_agent", "full_context", "package_type"]
  }
}
```

### **4. Validation and Evidence Tools**

#### **collect_evidence**
```json
{
  "name": "collect_evidence",
  "description": "Collect and validate evidence for agent success claims",
  "inputSchema": {
    "type": "object",
    "properties": {
      "agent_name": {"type": "string"},
      "success_claims": {"type": "array"},
      "evidence_types": {
        "type": "array",
        "items": {
          "type": "string",
          "enum": ["bash_output", "test_results", "screenshots", "performance_metrics", "security_scan", "user_validation"]
        }
      },
      "validation_criteria": {"type": "object"}
    },
    "required": ["agent_name", "success_claims", "evidence_types"]
  }
}
```

### **5. Agent Registry Tools**

#### **list_available_agents**
```json
{
  "name": "list_available_agents",
  "description": "Get list of all available agents with their capabilities",
  "inputSchema": {
    "type": "object",
    "properties": {
      "category_filter": {
        "type": "array",
        "items": {
          "type": "string",
          "enum": ["orchestration", "development", "frontend", "quality", "infrastructure", "documentation", "integration", "security", "maintenance"]
        }
      },
      "capability_filter": {"type": "array"},
      "availability_status": {"type": "boolean", "default": true}
    }
  }
}
```

#### **get_agent_specification**
```json
{
  "name": "get_agent_specification",
  "description": "Get detailed specification for a specific agent",
  "inputSchema": {
    "type": "object",
    "properties": {
      "agent_name": {"type": "string"},
      "include_examples": {"type": "boolean", "default": true},
      "include_collaboration_patterns": {"type": "boolean", "default": true}
    },
    "required": ["agent_name"]
  }
}
```

---

## 📦 **Installation and Deployment**

### **Prerequisites**
```yaml
requirements:
  python: ">=3.9"
  dependencies:
    - mcp>=0.9.0
    - pydantic>=2.0.0
    - neo4j>=5.0.0  # Optional for knowledge graph
    - redis>=4.0.0  # Optional for context caching
    - tiktoken>=0.5.0  # For token counting
```

### **Installation Steps**

1. **Create MCP Server Package**
```bash
mkdir -p ~/.claude-code/mcp-servers/claude-agent-orchestrator
cd ~/.claude-code/mcp-servers/claude-agent-orchestrator
```

2. **Install Dependencies**
```bash
pip install mcp pydantic tiktoken neo4j redis
```

3. **Create Server Configuration**
```json
{
  "mcpServers": {
    "claude-agent-orchestrator": {
      "command": "python",
      "args": [
        "-m", "claude_agent_orchestrator"
      ],
      "env": {
        "AGENT_REGISTRY_PATH": "~/.claude-code/agents",
        "KNOWLEDGE_GRAPH_URL": "bolt://localhost:7687",
        "CONTEXT_CACHE_URL": "redis://localhost:6379"
      }
    }
  }
}
```

4. **Register with Claude Code**
```bash
# Add to Claude Code settings.json
{
  "mcpServers": {
    "claude-agent-orchestrator": {
      "command": "python",
      "args": ["-m", "claude_agent_orchestrator"],
      "env": {
        "AGENT_REGISTRY_PATH": "/path/to/agents",
        "KNOWLEDGE_GRAPH_URL": "bolt://localhost:7687"
      }
    }
  }
}
```

---

## 🔄 **Usage Examples**

### **Example 1: Single Agent Call**
```python
# Call specialized agent
result = await call_agent(
    agent_name="backend-gateway-expert",
    task_description="Debug API 500 errors on /api/v1/settings endpoint",
    context_package={
        "technical_context": "Server returning 500 Internal Server Error...",
        "coordination_metadata": {"phase": "3", "parallel_group": "backend_stream"},
        "constraints": {"max_execution_time": "300s"},
        "success_criteria": ["API returns 200", "Error logs show resolution"]
    },
    phase="3",
    evidence_requirements={
        "validation_type": "api_testing",
        "evidence_format": "bash_output",
        "success_metrics": ["http_status_200", "error_logs_cleared"]
    }
)
```

### **Example 2: Parallel Agent Execution**
```python
# Execute multiple agents simultaneously
results = await call_agents_parallel(
    agent_calls=[
        {
            "agent_name": "production-endpoint-validator",
            "task_description": "Test https://aiwfe.com endpoint functionality",
            "context_package": {"technical_context": "Production SSL validation..."},
            "priority": "critical"
        },
        {
            "agent_name": "security-validator", 
            "task_description": "Validate authentication security",
            "context_package": {"technical_context": "JWT token validation..."},
            "priority": "high"
        },
        {
            "agent_name": "monitoring-analyst",
            "task_description": "Analyze system performance metrics",
            "context_package": {"technical_context": "Performance monitoring..."},
            "priority": "medium"
        }
    ],
    phase="4",
    coordination_strategy={
        "synchronization_points": ["initial_validation", "cross_validation"],
        "failure_handling": "continue_others_on_failure",
        "resource_allocation": {"max_concurrent": 3}
    }
)
```

### **Example 3: Orchestration Tools Usage**
```python
# Query historical patterns
patterns = await search_knowledge_graph_for_patterns(
    error_name="API_500_Internal_Server_Error",
    error_context={
        "error_type": "server_error",
        "affected_systems": ["api_gateway", "authentication"],
        "severity": "high"
    },
    solution_criteria={
        "min_success_rate": 0.9,
        "recency_weight": 0.4
    }
)

# Create checkpoint before critical operation
checkpoint_id = await create_orchestration_checkpoint(
    phase="3",
    state={
        "agent_states": current_agent_states,
        "context_packages": active_context_packages,
        "execution_metadata": execution_metadata
    },
    checkpoint_type="critical_operation",
    description="Before parallel agent execution for API error resolution"
)

# Validate specialist scope
validation = await validate_specialist_scope(
    agent_name="backend-gateway-expert",
    proposed_actions=[
        {
            "action_type": "api_debugging",
            "scope": "server_logs_analysis",
            "resources_required": ["file_read", "bash_execution"],
            "dependencies": ["log_file_access"]
        }
    ]
)
```

---

## 🎯 **Benefits of MCP Server Implementation**

### **Immediate Benefits**
- ✅ **36 Specialized Agents** available in Claude Code
- ✅ **11 Orchestration Tools** for advanced workflow management
- ✅ **Phase-Based Orchestration** with automatic checkpoint management
- ✅ **Context Package Management** preventing token overflow
- ✅ **Evidence-Based Validation** with comprehensive audit trails

### **Advanced Capabilities**
- 🧠 **Historical Pattern Learning** via knowledge graph integration
- 🔄 **Automatic Failure Recovery** with intelligent checkpoint system
- 📊 **Real-Time Performance Monitoring** with resource optimization
- 🎯 **Intelligent Agent Coordination** with parallel execution
- 📈 **Continuous Improvement** through outcome tracking

### **Integration Benefits**
- 🔗 **Universal Availability** across all Claude Code projects
- 🎚️ **Configurable Deployment** with environment-specific settings
- 📱 **Cross-Platform Compatibility** with standard MCP protocol
- 🔐 **Security-First Design** with scope validation and audit trails

This MCP server specification provides the complete infrastructure needed to implement the full 36-agent orchestration system with all advanced orchestration capabilities as a standard MCP server that can be deployed globally in your Claude Code environment.