# Claude Agent Orchestrator MCP Server - Complete Deployment Guide
**Version:** 1.0  
**Date:** 2025-08-08  
**Scope:** Global Claude Code integration for all projects

---

## 🚀 **Quick Start Summary**

The Claude Agent Orchestrator MCP Server enables **36 specialized agents** and **11 orchestration tools** globally across all your Claude Code projects. This guide provides step-by-step installation and configuration.

### **What You Get:**
- ✅ **36 Specialized Agents** available via MCP tools
- ✅ **11 Orchestration Tools** for advanced workflow management  
- ✅ **6-Phase Orchestration Workflow** with automatic checkpoints
- ✅ **Context Package Management** with intelligent compression
- ✅ **Evidence-Based Validation** with comprehensive audit trails
- ✅ **Global Availability** across all Claude Code projects

---

## 📋 **Prerequisites**

### **System Requirements**
```yaml
operating_systems:
  - macOS (10.15+)
  - Linux (Ubuntu 18.04+, CentOS 7+)
  - Windows (WSL2 recommended)

python_requirements:
  - Python 3.9 or higher
  - pip package manager
  - Virtual environment support

optional_services:
  - Redis (for caching and performance)
  - Neo4j (for advanced knowledge graph features)
  - SQLite (included by default)

claude_code_requirements:
  - Claude Code CLI installed and configured
  - MCP server support enabled
  - User settings.json write access
```

### **Pre-Installation Checklist**
- [ ] Python 3.9+ installed (`python3 --version`)
- [ ] Claude Code CLI working (`claude-code --version`)
- [ ] Git access for repository cloning
- [ ] Write permissions to Claude Code settings
- [ ] Network access for package installation

---

## 🛠️ **Installation Methods**

### **Method 1: Automated Installation (Recommended)**

#### **Step 1: Download Installation Script**
```bash
# Download the automated installer
curl -fsSL https://raw.githubusercontent.com/your-repo/claude-agent-orchestrator/main/install.sh -o install-orchestrator.sh

# Make executable
chmod +x install-orchestrator.sh

# Run installation
./install-orchestrator.sh
```

#### **Step 2: Verify Installation**
```bash
# Check MCP server status
claude-code mcp status

# Test agent availability
claude-code mcp test claude-agent-orchestrator list_available_agents
```

### **Method 2: Manual Installation**

#### **Step 1: Create Installation Directory**
```bash
# Create MCP servers directory in Claude Code config
mkdir -p ~/.claude-code/mcp-servers
cd ~/.claude-code/mcp-servers

# Clone the orchestrator server
git clone https://github.com/your-repo/claude-agent-orchestrator.git
cd claude-agent-orchestrator
```

#### **Step 2: Set Up Python Environment**
```bash
# Create virtual environment
python3 -m venv orchestrator-env

# Activate environment (Linux/macOS)
source orchestrator-env/bin/activate

# Activate environment (Windows)
# orchestrator-env\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### **Step 3: Install Package**
```bash
# Install in development mode
pip install -e .

# Or install from package
pip install claude-agent-orchestrator
```

#### **Step 4: Configure Claude Code Settings**
```bash
# Open Claude Code settings
code ~/.claude-code/settings.json

# Or use nano/vim
nano ~/.claude-code/settings.json
```

Add the following configuration:
```json
{
  "mcpServers": {
    "claude-agent-orchestrator": {
      "command": "python",
      "args": [
        "-m", "claude_agent_orchestrator.server"
      ],
      "env": {
        "AGENT_REGISTRY_PATH": "~/.claude-code/agents",
        "ORCHESTRATION_DB_PATH": "~/.claude-code/orchestration.db",
        "CONTEXT_CACHE_DIR": "~/.claude-code/context-cache",
        "KNOWLEDGE_GRAPH_URL": "sqlite:///~/.claude-code/knowledge.db",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

#### **Step 5: Copy Agent Specifications**
```bash
# Create agent registry directory
mkdir -p ~/.claude-code/agents

# Copy agent specifications
cp -r agents/* ~/.claude-code/agents/

# Set permissions
chmod -R 644 ~/.claude-code/agents/*.md
```

#### **Step 6: Initialize System**
```bash
# Initialize orchestration database
python -m claude_agent_orchestrator.init_db

# Test installation
python -m claude_agent_orchestrator.test_installation
```

---

## ⚙️ **Configuration Options**

### **Environment Variables**
```bash
# Core Configuration
export AGENT_REGISTRY_PATH="~/.claude-code/agents"
export ORCHESTRATION_DB_PATH="~/.claude-code/orchestration.db"
export CONTEXT_CACHE_DIR="~/.claude-code/context-cache"

# Optional Services
export REDIS_URL="redis://localhost:6379"
export NEO4J_URL="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="password"

# Performance Settings
export MAX_PARALLEL_AGENTS="5"
export MAX_CONTEXT_TOKENS="4000"
export CHECKPOINT_RETENTION_DAYS="30"

# Logging and Monitoring
export LOG_LEVEL="INFO"
export ENABLE_METRICS="true"
export METRICS_PORT="8080"
```

### **Advanced Configuration File**
Create `~/.claude-code/orchestrator-config.yaml`:
```yaml
orchestrator:
  version: "1.0"
  
agent_registry:
  path: "~/.claude-code/agents"
  auto_reload: true
  validation_strict: true
  
orchestration:
  max_parallel_agents: 5
  default_timeout: 300
  checkpoint_interval: 60
  
context_management:
  max_tokens_per_package: 4000
  compression_strategy: "semantic_preserve"
  cache_ttl: 3600
  
knowledge_graph:
  enabled: true
  backend: "sqlite"  # or "neo4j"
  retention_days: 90
  
validation:
  evidence_required: true
  audit_framework: "mast"
  validation_timeout: 120
  
performance:
  enable_redis_cache: true
  enable_metrics: true
  resource_monitoring: true
```

---

## 🔧 **Agent Registry Setup**

### **Automatic Agent Detection**
The system automatically loads agent specifications from:
```bash
~/.claude-code/agents/
├── agent-integration-orchestrator.md
├── backend-gateway-expert.md
├── enhanced-nexus-synthesis-agent.md
├── production-endpoint-validator.md
├── security-validator.md
└── ... (all 36 agents)
```

### **Agent Validation**
```bash
# Validate all agent specifications
python -m claude_agent_orchestrator.validate_agents

# Check specific agent
python -m claude_agent_orchestrator.validate_agents --agent backend-gateway-expert

# List all available agents
python -m claude_agent_orchestrator.list_agents
```

### **Custom Agent Registration**
To add custom agents:
```bash
# Create new agent specification
cp ~/.claude-code/agents/template.md ~/.claude-code/agents/my-custom-agent.md

# Edit specification
nano ~/.claude-code/agents/my-custom-agent.md

# Reload agent registry
python -m claude_agent_orchestrator.reload_registry
```

---

## 🧪 **Testing and Validation**

### **Basic Functionality Tests**
```bash
# Test MCP server connection
claude-code mcp ping claude-agent-orchestrator

# Test agent listing
claude-code mcp call claude-agent-orchestrator list_available_agents

# Test single agent call
claude-code mcp call claude-agent-orchestrator call_agent \
  --agent_name "backend-gateway-expert" \
  --task_description "Test API connectivity" \
  --context_package '{"technical_context": "API testing required"}' \
  --phase "3"
```

### **Orchestration Workflow Tests**
```bash
# Test orchestration tools
claude-code mcp call claude-agent-orchestrator create_orchestration_checkpoint \
  --phase "1" \
  --state '{"test": "data"}' \
  --checkpoint_type "test" \
  --description "Testing checkpoint creation"

# Test context package creation
claude-code mcp call claude-agent-orchestrator create_context_package \
  --target_agent "security-validator" \
  --full_context "Security testing context..." \
  --package_type "security"
```

### **Performance Validation**
```bash
# Run performance benchmark
python -m claude_agent_orchestrator.benchmark

# Test parallel execution
python -m claude_agent_orchestrator.test_parallel

# Memory usage test
python -m claude_agent_orchestrator.test_memory
```

---

## 🚀 **Usage Examples**

### **Example 1: Single Agent Execution**
```python
# In Claude Code conversation
result = await call_agent(
    agent_name="backend-gateway-expert",
    task_description="Debug API 500 errors on /api/v1/settings",
    context_package={
        "technical_context": "Production API returning 500 Internal Server Error...",
        "coordination_metadata": {"phase": "3"},
        "constraints": {"max_execution_time": "300s"},
        "success_criteria": ["API returns 200", "Logs show resolution"]
    },
    phase="3",
    evidence_requirements={
        "validation_type": "api_testing", 
        "evidence_format": "bash_output",
        "success_metrics": ["http_status_200", "error_logs_cleared"]
    }
)
```

### **Example 2: Parallel Agent Orchestration**
```python
# Execute multiple agents simultaneously
parallel_result = await call_agents_parallel(
    agent_calls=[
        {
            "agent_name": "production-endpoint-validator",
            "task_description": "Validate https://aiwfe.com endpoints",
            "context_package": {"technical_context": "Production validation..."},
            "priority": "critical"
        },
        {
            "agent_name": "security-validator", 
            "task_description": "Security audit of authentication",
            "context_package": {"technical_context": "Auth security check..."},
            "priority": "high"
        },
        {
            "agent_name": "monitoring-analyst",
            "task_description": "Performance metrics analysis", 
            "context_package": {"technical_context": "System monitoring..."},
            "priority": "medium"
        }
    ],
    phase="4",
    max_parallel=3
)
```

### **Example 3: Full 6-Phase Orchestration**
```python
# Phase 0: Agent Integration Check
await call_agent(
    agent_name="agent-integration-orchestrator",
    task_description="Detect and integrate available agents",
    phase="0"
)

# Phase 1: Strategic Planning  
await call_agent(
    agent_name="project-orchestrator",
    task_description="Analyze API errors and create coordination strategy",
    phase="1"
)

# Phase 2: Research
research_agents = ["codebase-research-analyst", "backend-gateway-expert", "security-validator"]
await call_agents_parallel(
    agent_calls=[{
        "agent_name": agent,
        "task_description": f"Research API errors from {agent} perspective"
    } for agent in research_agents],
    phase="2"
)

# Phase 2.5: Context Synthesis
synthesis_result = await call_agent(
    agent_name="enhanced-nexus-synthesis-agent",
    task_description="Synthesize research into coordinated execution plan",
    phase="2.5"
)

# Phase 3: Execute specialists with context packages
# Phase 4: Validate with evidence-based testing
# Phase 5: Iterate or complete based on validation
# Phase 6: Audit and improve workflow
```

---

## 🔍 **Troubleshooting**

### **Common Issues and Solutions**

#### **Issue: MCP Server Not Starting**
```bash
# Check Python environment
which python3
python3 --version

# Check dependencies
pip list | grep claude-agent

# Check configuration
cat ~/.claude-code/settings.json | grep -A 10 claude-agent-orchestrator

# Check logs
tail -f ~/.claude-code/logs/mcp-claude-agent-orchestrator.log
```

#### **Issue: Agents Not Loading**
```bash
# Validate agent registry
python -m claude_agent_orchestrator.validate_agents

# Check agent directory
ls -la ~/.claude-code/agents/

# Check permissions
chmod -R 644 ~/.claude-code/agents/*.md

# Reload registry
python -m claude_agent_orchestrator.reload_registry
```

#### **Issue: Context Package Errors**
```bash
# Check tokenizer installation
pip show tiktoken

# Test compression
python -m claude_agent_orchestrator.test_compression

# Check cache directory
ls -la ~/.claude-code/context-cache/
```

#### **Issue: Performance Problems**
```bash
# Enable Redis (if available)
redis-server --daemonize yes

# Check memory usage
python -m claude_agent_orchestrator.memory_usage

# Optimize configuration
# Reduce MAX_PARALLEL_AGENTS
# Increase MAX_CONTEXT_TOKENS if needed
```

### **Debug Mode**
```bash
# Enable debug logging
export LOG_LEVEL="DEBUG"

# Run with verbose output
python -m claude_agent_orchestrator.server --verbose

# Test with debug agent
claude-code mcp call claude-agent-orchestrator debug_info
```

---

## 📈 **Monitoring and Maintenance**

### **Health Monitoring**
```bash
# Check MCP server health
claude-code mcp health claude-agent-orchestrator

# Monitor resource usage
python -m claude_agent_orchestrator.monitor

# Check agent performance
python -m claude_agent_orchestrator.agent_stats
```

### **Log Management**
```bash
# View orchestration logs
tail -f ~/.claude-code/logs/orchestration.log

# View agent execution logs
tail -f ~/.claude-code/logs/agent-execution.log

# Rotate logs
python -m claude_agent_orchestrator.rotate_logs
```

### **Database Maintenance**
```bash
# Backup orchestration database
cp ~/.claude-code/orchestration.db ~/.claude-code/backups/orchestration-$(date +%Y%m%d).db

# Clean old checkpoints
python -m claude_agent_orchestrator.cleanup_checkpoints --days 30

# Optimize knowledge graph
python -m claude_agent_orchestrator.optimize_knowledge_graph
```

### **Updates and Upgrades**
```bash
# Update orchestrator server
pip install --upgrade claude-agent-orchestrator

# Update agent specifications
cd ~/.claude-code/mcp-servers/claude-agent-orchestrator
git pull origin main
cp -r agents/* ~/.claude-code/agents/

# Restart MCP server
claude-code mcp restart claude-agent-orchestrator
```

---

## 🔒 **Security Considerations**

### **Access Control**
```bash
# Secure agent directory
chmod 755 ~/.claude-code/agents/
chmod 644 ~/.claude-code/agents/*.md

# Secure database files
chmod 600 ~/.claude-code/orchestration.db
chmod 600 ~/.claude-code/knowledge.db
```

### **Network Security**
- Ensure Redis is not exposed to external networks
- Use authentication for Neo4j if enabled
- Monitor MCP server logs for unusual activity

### **Data Privacy**
- Context packages may contain sensitive information
- Enable encryption for database storage in production
- Implement retention policies for orchestration data

---

## 📊 **Performance Optimization**

### **Resource Tuning**
```yaml
# Optimize for different environments

# Development Environment
max_parallel_agents: 3
max_context_tokens: 3000
enable_redis_cache: false

# Production Environment  
max_parallel_agents: 8
max_context_tokens: 6000
enable_redis_cache: true
enable_metrics: true

# Resource Constrained
max_parallel_agents: 2
max_context_tokens: 2000
checkpoint_retention_days: 7
```

### **Monitoring Metrics**
- Agent execution times
- Context package compression ratios
- Orchestration success rates
- Resource utilization
- Error patterns and frequencies

---

## 🎯 **Success Validation**

### **Installation Success Criteria**
- [ ] All 36 agents loaded successfully
- [ ] 11 orchestration tools available
- [ ] MCP server responding to health checks
- [ ] Context package creation working
- [ ] Knowledge graph initialized
- [ ] Test agent execution successful

### **Performance Benchmarks**
- Agent loading time: < 5 seconds
- Context package creation: < 2 seconds
- Parallel agent execution: 3-5 agents simultaneously
- Memory usage: < 500MB baseline
- Response time: < 1 second for most operations

---

## 🆘 **Support and Resources**

### **Documentation**
- **Architecture Guide**: `/docs/architecture/`
- **Agent Specifications**: `/.claude/agents/`
- **API Reference**: `/docs/api/`
- **Examples**: `/examples/`

### **Community Resources**
- **Issues**: https://github.com/your-repo/claude-agent-orchestrator/issues
- **Discussions**: https://github.com/your-repo/claude-agent-orchestrator/discussions
- **Wiki**: https://github.com/your-repo/claude-agent-orchestrator/wiki

### **Professional Support**
For enterprise deployments and custom configurations:
- Email: support@orchestrator.ai
- Discord: #claude-orchestrator
- Documentation: https://docs.orchestrator.ai

---

## 🎉 **Deployment Complete!**

Congratulations! You now have the complete Claude Agent Orchestrator MCP Server deployed globally across all your Claude Code projects. You can now:

✅ **Access 36 specialized agents** in any Claude Code conversation  
✅ **Use 11 orchestration tools** for advanced workflow management  
✅ **Execute 6-phase orchestration workflows** with automatic checkpoints  
✅ **Create context packages** with intelligent compression  
✅ **Validate with evidence-based testing** and comprehensive audit trails  

### **Next Steps:**
1. **Test basic functionality** with simple agent calls
2. **Try parallel execution** with multiple agents
3. **Explore orchestration workflows** for complex tasks
4. **Configure monitoring** for production use
5. **Customize agents** for your specific needs

**Welcome to the future of AI-powered development workflows!**