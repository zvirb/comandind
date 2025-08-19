# 🤖 Claude Code AI Workflow Engine Instructions

## 🚨 CRITICAL: 12-Step Agentic Orchestration Flow

### ⚡ MANDATORY WORKFLOW SEQUENCE ⚡

**Configuration**: Uses `.claude/unified-orchestration-config.yaml`

```yaml
Step 0: Todo Context Integration
  - orchestration-todo-manager: Cross-session todo management from .claude/orchestration_todos.json

Step 1: Agent Ecosystem Validation  
  - agent-integration-orchestrator: Agent discovery and integration

Step 2: Strategic Intelligence Planning
  - project-orchestrator: Strategic planning and coordination
  - enhanced-nexus-synthesis: Historical pattern analysis

Step 3: Multi-Domain Research Discovery
  - PARALLEL: codebase-research-analyst, schema-database-expert, security-validator, performance-profiler

Step 4: Context Synthesis & Compression
  - nexus-synthesis: Cross-domain integration
  - context-compression: Token management (max 4000 tokens per package)

Step 5: Parallel Implementation Execution
  - MULTI-STREAM: Backend, Frontend, Quality, Infrastructure, Documentation streams
  - MANDATORY project-janitor inclusion for file organization

Step 6: Evidence-Based Validation
  - production-endpoint-validator, user-experience-auditor, ui-regression-debugger
  - REQUIREMENT: Concrete evidence (screenshots, logs, curl outputs)

Step 7: Decision & Iteration Control
  - orchestration-auditor-v2: Evidence analysis (max 3 iterations)

Step 8: Atomic Version Control Synchronization
  - atomic-git-synchronizer: Atomic commits and remote sync

Step 9: Meta-Orchestration Audit & Learning (ALWAYS EXECUTES)
  - orchestration-auditor: Workflow analysis and improvement

Step 10: Production Deployment & Release
  - deployment-orchestrator: Blue-green deployment with rollback

Step 11: Production Validation & Health Monitoring  
  - IF validation fails: Return to Step 0 with production failure context
  - IF validation succeeds: Continue to Step 12

Step 12: Todo Loop Control (ALWAYS EXECUTES)
  - IF high-priority todos remain: Return to Step 0 with updated context
  - IF no todos remain: Complete workflow
```

---

## 🌊 MULTI-STREAM PARALLEL ARCHITECTURE

### ⚡ DOMAIN STREAM CLASSIFICATION ⚡

**Principle**: Independent domain progression with coordinated integration

```yaml
Domain Streams:
  Backend: backend-gateway-expert, schema-database-expert, performance-profiler
  Frontend: ui-architect, ux-architect, ui-debugger  
  Security: security-validator, fullstack-communication-auditor
  Infrastructure: monitoring-analyst, container-architecture-specialist, deployment-orchestrator
  Quality: test-automation-engineer, user-experience-auditor, code-quality-guardian
  Documentation: documentation-specialist, project-structure-mapper

Stream Progression: Planning → Research → Implementation → Validation → Production
Coordination: nexus-synthesis for integration, Redis scratch pad for communication
```

### **Stream Coordination Rules:**

```yaml
Independence: Streams progress independently unless explicit dependencies exist
Coordination: Redis scratch pad system for cross-domain communication  
Failure Handling:
  - Single stream failures don't block other streams
  - Cross-domain failures trigger coordinated recovery
  - Critical failures return all streams to planning phase
Synchronization Points:
  - Planning completion: Negotiate cross-domain dependencies
  - Implementation milestones: Integration testing across domains
  - Pre-production: Comprehensive validation and rollback alignment
```

### **🤖 ML-Enhanced Orchestration**

```yaml
ML Capabilities:
  Performance Analysis: ml-enhanced-orchestrator, predictive-coordination-ai
  Workflow Optimization: adaptive-workflow-optimizer, intelligent-context-synthesizer  
  Quality Assessment: predictive-quality-assessor, adaptive-research-coordinator
  Validation: smart-integration-validator, intelligent-failure-predictor
  
Features:
  - Real-time stream performance analysis and optimization
  - Cross-domain dependency prediction and resource allocation
  - Predictive failure analysis and conflict detection
  - Context compression with semantic preservation
  - Adaptive memory management and knowledge graph construction
```

---

## 🔄 LOOP CONTROL & CONTINUITY

### **Loop Decision Points:**

```yaml
Phase 11 Loop Control:
  - IF production validation fails: Return to Step 0 with production failure context
  - IF production validation succeeds: Continue to Step 12 (todo check)

Phase 12 Loop Control:
  - IF high-priority todos remain: Return to Step 0 with updated context  
  - IF no todos remain: Complete workflow

Context Continuity:
  - Maintain session memory across iterations
  - Preserve learning from previous cycles
  - Build upon completed work without duplication
  - Progressive continuation toward project goals
```

---

## 🏗️ CONTAINER ARCHITECTURE PRINCIPLES

### ⚡ MANDATORY ISOLATION RULES ⚡

**Principle**: Each new functionality = separate container/service

```yaml
Container Requirements:
  ✅ CORRECT:
    - New Service = New Container
    - Independent API endpoints (/health, /api/v1/...)
    - Graceful degradation ("Service offline" messages)
    - No cascading failures

  ❌ FORBIDDEN:
    - Modifying existing working containers
    - Integrating new features into existing services
    - Creating tight coupling between components

Integration Patterns:
  New Functionality:
    1. Create dedicated container
    2. Expose standardized APIs
    3. Register with API gateway
    4. Add frontend error handling
    5. Test graceful degradation

  Technology Upgrades (Blue-Green):
    1. Keep existing container as fallback
    2. Build new container with upgraded tech
    3. Test extensively in isolation
    4. Route to new container as primary
    5. Retire old container only after stability proven

Exception Protocol (ONLY when deep integration required):
  1. Backup current container
  2. Create container copy (api-v1 → api-v2)
  3. Implement changes in NEW copy
  4. Use new as primary, old as fallback
  5. Monitor stability before retirement
```

---

## 🗄️ MEMORY MCP STORAGE & FILE ORGANIZATION

### **🚨 MANDATORY STORAGE RULES 🚨**

```yaml
File Creation Rules:
  FORBIDDEN:
    - .md files in project root
    - Report files outside designated directories
  REQUIRED:  
    - ALL agent outputs in memory MCP
    - Structured entity naming: "{agent-name}-{output-type}-{YYYYMMDD-HHMMSS}"

Memory MCP Usage:
  # Store agent output
  mcp__memory__create_entities(entities=[{
      "name": "{agent-name}-{output-type}-{timestamp}",
      "entityType": "agent-output",
      "observations": ["findings and results"]
  }])

  # Query outputs
  mcp__memory__search_nodes(query="agent output type domain")

File Organization:
  - project-janitor: ALWAYS included in Phase 5 execution
  - Root directory: Maximum 15 files
  - Reports: docs/reports/ (if file creation absolutely necessary)
  - Evidence: docs/evidence/ (if file creation absolutely necessary)
```

---

## 🛑 RECURSION PREVENTION & AGENT HIERARCHY

### **Strict Agent Hierarchy:**
```
1. User → orchestration-todo-manager (Phase 0)
2. project-orchestrator → Main Claude (strategic delegation)  
3. Main Claude → Specialist Agents (execution)
4. Specialist Agents → NEVER call orchestrators (FORBIDDEN!)
```

### **🚀 Orchestration Triggers:**
- "start flow", "orchestration", "agentic flow", "start agent(s)"

### **Agent Behavior Rules:**

```yaml
✅ CORRECT Specialist Behavior:
  - RECEIVE context package only
  - PERFORM domain-specific expertise
  - USE ALL AVAILABLE TOOLS
  - RETURN results to Main Claude
  - NEVER start new orchestration

❌ FORBIDDEN Behaviors:
  - Calling orchestrators (project-orchestrator, nexus-synthesis, etc.)
  - Starting new Task flows
  - Exceeding context boundaries
  - Calling other specialists directly

Recursion Prevention:
  - Only USER initiates orchestration
  - Orchestrators NEVER call other orchestrators
  - Specialists NEVER call orchestrators
  - No self-calling agents
  - Main Claude executes, doesn't create loops
```

---

## 📋 ORCHESTRATION AGENTS & CONTEXT SYSTEM

### **Orchestration Agent Hierarchy:**
```yaml
Phase 0: orchestration-todo-manager (Todo Coordinator)
Phase 1: agent-integration-orchestrator (Ecosystem Manager)
Phase 2: project-orchestrator (Strategic Coordinator)
Phase 4: enhanced-nexus-synthesis (Strategic Intelligence), document-compression (Content Optimizer)
Phase 8: atomic-git-synchronizer (Version Control Manager)
Phase 9: orchestration-auditor (Meta-Analyst)
Phase 10: deployment-orchestrator (Release Manager)
Phase 12: orchestration-todo-manager (Todo Loop Controller)
```

### **Context Package System:**
```yaml
Size Limits (STRICTLY ENFORCED):
  - Memory MCP entities: Max 8000 tokens
  - Context packages: Max 4000 tokens
  - Strategic packages: Max 3000 tokens

Package Types:
  - Strategic Context: High-level architecture (3000 tokens max)
  - Technical Context: Implementation details (4000 tokens max)
  - Frontend Context: UI patterns and components (3000 tokens max)
  - Security Context: Auth patterns and vulnerabilities (3000 tokens max)
  - Performance Context: Bottlenecks and optimization (3000 tokens max)
  - Database Context: Schema and query patterns (3500 tokens max)

Documentation Access:
  Query memory MCP for: "System Architecture Documentation", "API Documentation", 
  "Security Implementation Guide", "Project Overview Documentation"
```

---

## 📝 TODO MANAGEMENT SYSTEM

### **Two-Tier Todo System:**

```yaml
Storage: .claude/orchestration_todos.json

1. Session Todos (TodoWrite tool):
   - Temporary, current session tracking
   - Active orchestration phase management

2. Orchestration Todos (Persistent file):
   - Cross-session items managed by orchestration-todo-manager
   - Context continuity across Claude sessions

Phase 0 Integration:
  1. Read persistent todos from .claude/orchestration_todos.json
  2. Analyze relevance to current context
  3. Prioritize based on urgency and impact
  4. Integrate high-priority items into current iteration
  5. Update status based on progress

Todo Structure:
  {
    "id": "unique-identifier",
    "content": "Clear, actionable description", 
    "priority": "critical|high|medium|low|backlog",
    "status": "pending|in_progress|completed|blocked",
    "context_tags": ["relevant", "areas"],
    "urgency_score": 85,
    "impact_score": 90
  }
```

---

## 🔧 TOOL USAGE GUIDE

### **Core Tools by Category:**

```yaml
File Operations: Read, Write, Edit, MultiEdit, Glob, LS
Search & Analysis: Grep, Task, WebFetch, WebSearch  
Development: Bash, NotebookEdit, execution tools
Context & Memory: TodoWrite, MCP tools

Orchestration Tools:
  - query_orchestration_knowledge(): Knowledge graph queries
  - create/load_orchestration_checkpoint(): Recovery checkpoints
  - compress_orchestration_document(): Token overflow prevention

Collaborative Tools (Redis):
  - mcp__redis__hset/hget/hgetall(): Shared workspace
  - mcp__redis__sadd/smembers(): Agent notifications
  - mcp__redis__zadd/zrange(): Collaboration timeline

Sequential Thinking Tools:
  - mcp__sequential_thinking(): Step-by-step problem decomposition
  - Thought revision and branching capabilities
  - Dynamic thought count adjustment
  - Solution hypothesis generation

Specialized: Browser tools, Sequential Thinking (mcp__sequential_thinking), File System tools
```

### **Agent-Specific Tool Requirements:**

```yaml
Research Agents: Read, Grep, Glob, LS extensively + Bash exploration
Implementation Agents: Read → Edit/MultiEdit → Bash validation + Redis collaboration
Quality Assurance: Bash testing + Browser tools (user-experience-auditor: Playwright)
Documentation: Read → Edit + size management
Analysis Agents: Bash analysis + Read configs + quantitative metrics

Tool Patterns:
  Discovery: LS → Glob → Grep → Read
  Implementation: Read → Edit/MultiEdit → Bash  
  Validation: Bash → Grep → Read
  Documentation: Glob → Read → Edit
  Collaboration: Redis scratch pad → coordination → validation
```


---

## 🛠️ SPECIALIST AGENT ROSTER

### **Agent Categories (35+ Agents):**

```yaml
Development: backend-gateway-expert, schema-database-expert, python-refactoring-architect, codebase-research-analyst

Frontend/UX: ux-architect, ui-architect, ui-designer, ui-debugger

Quality Assurance: fullstack-communication-auditor, security-validator, test-automation-engineer, user-experience-auditor

Infrastructure/DevOps: performance-profiler, deployment-orchestrator, monitoring-analyst, dependency-analyzer, atomic-git-synchronizer, container-architecture-specialist

Documentation/Knowledge: documentation-specialist, project-structure-mapper, project-janitor

Context/Execution: context-compression, execution-conflict-detector, execution-simulator

Integration: external-services-integrator, graph-framework-analyst

Intelligence: enhanced-nexus-synthesis

ML/AI Orchestration: ml-enhanced-orchestrator, predictive-coordination-ai, adaptive-workflow-optimizer, intelligent-context-synthesizer, predictive-quality-assessor, adaptive-research-coordinator, smart-integration-validator, intelligent-failure-predictor

Collaboration: collaborative-scratch-pad
```

---

## 🔧 SYSTEM FEATURES

```yaml
Advanced Orchestration:
  - Workflow checkpointing and rollback
  - Priority queue system and intelligent cache
  - Evidence validation and predictive validation
  - Context package templates and workflow enforcement

Self-Improving System:
  - Phase 9 feeds learnings back into system
  - Phase 1 ensures new agent integration
  - Continuous evolution based on execution patterns
  - Knowledge graph integration for historical learning

Quality Assurance:
  - Mandatory Phase 6 validation with user perspective testing
  - Iterative refinement until validation succeeds
  - Evidence-based success claims with audit verification
```

---

## 📚 DOCUMENTATION ACCESS

### **Memory MCP Priority:**

```yaml
Query Memory MCP First: mcp__memory__search_nodes(query="term")

Categories:
  - Architecture: System design, data flows, container architecture
  - API: REST endpoints, authentication, WebSocket protocols  
  - Security: Implementation guides, security protocols, audit procedures
  - Development: Code patterns, workflows, agent specifications
  - Infrastructure: Deployment, monitoring, troubleshooting

Best Practices:
  1. Query before acting
  2. Use specific entity names
  3. Store new docs in memory MCP
  4. Update existing rather than duplicate
  5. Categorize properly ("documentation", "agent-spec")

Legacy Files (Git Standards): README.md, CONTRIBUTING.md
```

---

## ⚠️ WORKFLOW ENFORCEMENT

### **Role-Specific Checklists:**

```yaml
Main Claude (Orchestration Executor):
  - Complex multi-domain task requiring orchestration?
  - Started with orchestration-todo-manager (Phase 0)?
  - Following exact 12-phase sequence?
  - Calling specialists with context packages only?
  - Using TodoWrite for tracking?

Specialist Agents (During Orchestration):
  - Working ONLY within assigned domain?
  - Using context package, NOT requesting full research?
  - Leveraging ALL appropriate tools?
  - Returning results to Main Claude?
  - Providing evidence-based results?

Validation Requirements:
  - Context packages under size limits (4000 tokens max)
  - Evidence collection specified
  - User perspective testing planned
  - Measurable, verifiable results provided
```

---

## 🤝 COORDINATION & VALIDATION

### **Information Flow & Communication:**

```yaml
Phase Flow: Phase 0 (todos) → Phase 1 (ecosystem) → ... → Phase 11 (production validation) → Phase 12 (todo check)  
Loop Control: Phase 11/12 decision points for continuation or completion

Communication Rules:
  ✅ Specialists → Main Claude (results)
  ✅ Main Claude → Specialists (context packages)
  ✅ Orchestration agents → Main Claude (strategic outputs)
  ❌ Specialists → Orchestration agents (FORBIDDEN - recursion)
  ❌ Cross-specialist calls (FORBIDDEN - bypass coordination)

Evidence Requirements:
  - Implementation: Bash command results
  - Testing: Execution logs and screenshots  
  - Analysis: Quantitative metrics
  - Validation: User perspective evidence (Playwright for user-experience-auditor)
  
Compliance:
  - Use TodoWrite for complex tasks
  - Leverage appropriate tools
  - Provide evidence through tool usage
  - Stay within context limits
```

---

## 🎯 SUCCESS METRICS

### **Orchestration Success:**

```yaml
Flow Completion:
  ✅ All 12 phases completed (including production deployment/validation)
  ✅ No recursion or circular calls
  ✅ Context packages under size limits
  ✅ Appropriate tool usage

Validation Requirements:
  ✅ MANDATORY: Production accessibility verified (curl/ping evidence)
  ✅ MANDATORY: Infrastructure validation (monitoring, metrics, database)
  ✅ MANDATORY: Concrete evidence (curl outputs, health checks)
  ✅ User perspective validation with evidence
  ✅ Atomic commits and remote synchronization
  ✅ Phase 9 audit ALWAYS executed

Agent Success:
  ✅ Domain boundary compliance
  ✅ Efficient context package usage
  ✅ Multiple tool leverage
  ✅ Quantitative, evidence-based results
  ✅ Actionable findings returned
```

---

**This orchestration system creates a self-improving, scalable AI workflow engine that prevents context overload, eliminates recursion risks, and ensures comprehensive task continuation.**

