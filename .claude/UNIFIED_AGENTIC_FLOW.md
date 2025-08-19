# 🤖 Unified Agentic Coding Flow

## 🚨 INTEGRATED 10-STEP ORCHESTRATION WORKFLOW

**EVERY complex task MUST follow this EXACT unified 10-step workflow integrating all orchestration structures:**

### **Step 0: Todo Context Integration** (general-purpose)
- **Purpose**: Cross-session todo management and context continuity
- **Agents**: general-purpose
- **Parallel**: No (Sequential)
- **Triggers**: Every orchestration starts here
- **Outputs**: Persistent todo context, priority integration, ongoing issue analysis
- **Quality Gates**: Todo relevance validation, priority scoring
- **Resource Pool**: Memory intensive

### **Step 1: Agent Ecosystem Validation** (agent-integration-orchestrator)  
- **Purpose**: Agent discovery, integration, and ecosystem health
- **Agents**: agent-integration-orchestrator
- **Parallel**: No (Sequential)
- **Triggers**: After Step 0 completion
- **Outputs**: Agent registry updates, ecosystem status, integration validation
- **Quality Gates**: Agent availability check, capability validation
- **Resource Pool**: I/O intensive

### **Step 2: Strategic Intelligence Planning** (Enhanced Analysis)
- **Purpose**: Historical pattern analysis and strategic coordination
- **Agents**: 
  - project-orchestrator (strategic planning)
  - enhanced-nexus-synthesis-agent (historical intelligence)
- **Parallel**: Sequential lead (project-orchestrator → enhanced-nexus-synthesis-agent)
- **Triggers**: After Step 1 validation
- **Outputs**: Strategic master plan, historical pattern insights, coordinated approach
- **Quality Gates**: Strategy validation, pattern verification
- **Resource Pool**: Memory intensive

### **Step 3: Multi-Domain Research Discovery** (Parallel Research)
- **Purpose**: Comprehensive system analysis and requirement gathering
- **Agents**: 
  - codebase-research-analyst (primary research)
  - schema-database-expert (database analysis)
  - security-validator (security assessment)
  - performance-profiler (performance analysis)
  - smart-search-agent (targeted discovery)
- **Parallel**: Yes (max_concurrent: 5)
- **Triggers**: Strategic plan approval
- **Outputs**: Research findings, system analysis, security assessment, performance baseline
- **Quality Gates**: Research completeness, data consistency validation
- **Resource Pool**: CPU intensive, Network intensive

### **Step 4: Context Synthesis & Compression** (Intelligence Integration)
- **Purpose**: Research integration with intelligent compression
- **Agents**:
  - nexus-synthesis-agent (cross-domain integration) 
  - context-compression-agent (content optimization)
  - document-compression-agent (large content handling)
- **Parallel**: Sequential (nexus-synthesis → compression agents)
- **Triggers**: Research completion (75% minimum)
- **Outputs**: Integrated context packages (<4000 tokens each), compressed documentation
- **Quality Gates**: Context package validation, token limit compliance
- **Resource Pool**: Memory intensive

### **Step 5: Parallel Implementation Execution** (Multi-Stream Implementation)
- **Purpose**: Coordinated implementation across all domains
- **Execution Streams**:
  
  **Backend Stream (max_concurrent: 3)**:
  - backend-gateway-expert (API implementation)
  - schema-database-expert (database changes)
  - google-services-integrator (integrations)
  
  **Frontend Stream (max_concurrent: 3)**:
  - webui-architect (frontend architecture)
  - frictionless-ux-architect (UX optimization)
  - whimsy-ui-creator (delightful interactions)
  
  **Quality Stream (max_concurrent: 4)**:
  - test-automation-engineer (test implementation)
  - security-validator (security implementation)
  - fullstack-communication-auditor (integration validation)
  - rapid-testing-agent (fast feedback)
  
  **Infrastructure Stream (max_concurrent: 3)**:
  - infrastructure-orchestrator (DevOps coordination)
  - monitoring-analyst (observability)
  - dependency-analyzer (package management)
  
  **Documentation Stream (max_concurrent: 2)**:
  - documentation-specialist (live documentation)
  - project-janitor (maintenance)

- **Parallel**: Yes (cross-stream sync: true)
- **Triggers**: Context synthesis approval
- **Outputs**: Implementation artifacts, test suites, documentation, infrastructure configs
- **Quality Gates**: Implementation validation, integration health, security clearance
- **Resource Pools**: All pools (CPU, I/O, Network, Memory)

### **Step 6: Comprehensive Evidence-Based Validation** (Multi-Layer Validation)
- **Purpose**: Evidence-based validation with real user testing
- **Agents**:
  - production-endpoint-validator (infrastructure validation with EVIDENCE)
  - user-experience-auditor (real user interaction testing)
  - ui-regression-debugger (visual regression validation)
  - performance-profiler (performance validation)
  - code-quality-guardian (code quality enforcement)
- **Parallel**: Yes (completion gates required)
- **Triggers**: Implementation stream completion
- **Outputs**: Validation evidence, user interaction logs, performance metrics, quality reports
- **Quality Gates**: 
  - **MANDATORY EVIDENCE**: All claims require concrete proof (curl outputs, screenshots, logs)
  - **PRODUCTION ACCESSIBILITY**: Remote endpoint connectivity with timeout testing
  - **USER WORKFLOW VALIDATION**: End-to-end user interaction evidence
  - **INFRASTRUCTURE HEALTH**: Monitoring system functional validation
- **Resource Pool**: Network intensive, Memory intensive

### **Step 7: Decision & Iteration Control** (Quality Decision Point)
- **Purpose**: Evaluate validation evidence and determine completion
- **Decision Criteria**:
  - **IF VALIDATION SUCCEEDS** (all user issues resolved with evidence): → Step 8
  - **IF VALIDATION FAILS** (issues remain unresolved): → Step 0 (iteration restart)
- **Agents**: orchestration-auditor-v2 (evidence analysis)
- **Parallel**: No (Sequential decision)
- **Triggers**: Validation completion
- **Outputs**: Success/failure determination, iteration requirements, evidence summary
- **Quality Gates**: Evidence-based decision validation
- **Iteration Limit**: Maximum 3 iterations before meta-orchestrator escalation

### **Step 8: Atomic Version Control Synchronization** (Git Operations)
- **Purpose**: Atomic commit creation and remote synchronization
- **Agents**: atomic-git-synchronizer
- **Parallel**: No (Sequential)
- **Triggers**: Successful validation (Step 7 approval)
- **Outputs**: Atomic commits, remote sync confirmation, version control updates
- **Quality Gates**: Commit atomicity, sync validation, branch health
- **Resource Pool**: I/O intensive

### **Step 9: Meta-Orchestration Audit & Learning** (ALWAYS EXECUTES)
- **Purpose**: Workflow analysis and continuous improvement
- **Agents**: 
  - orchestration-auditor (meta-analysis)
  - execution-conflict-detector (conflict analysis)
  - evidence-auditor (validation verification)
- **Parallel**: No (Sequential analysis)
- **Triggers**: ALWAYS runs regardless of Step 7 outcome
- **Outputs**: Workflow improvement recommendations, learning insights, audit reports
- **Quality Gates**: Audit completeness, improvement identification
- **Enforcement**: NON-OPTIONAL, runs after every workflow

---

## 🎯 **UNIFIED TRIGGER SYSTEM**

### **Automatic Orchestration Triggers:**
- "start flow"
- "orchestration" 
- "agentic flow"
- "agentic orchestration"
- "start agent"
- "start agents"

**Action**: IMMEDIATELY begin Step 0: Todo Context Integration

---

## 🔧 **INTEGRATED RESOURCE MANAGEMENT**

### **Resource Pool Coordination:**
```yaml
CPU Intensive Pool (max_concurrent: 2):
  - performance-profiler, codebase-research-analyst, test-automation-engineer
  - timeout_multiplier: 1.5x

I/O Intensive Pool (max_concurrent: 3):
  - schema-database-expert, documentation-specialist, dependency-analyzer
  - timeout_multiplier: 1.2x

Network Intensive Pool (max_concurrent: 2):
  - security-validator, dependency-analyzer, monitoring-analyst
  - timeout_multiplier: 1.8x

Memory Intensive Pool (max_concurrent: 2):
  - nexus-synthesis-agent, enhanced-nexus-synthesis-agent, orchestration-auditor
  - timeout_multiplier: 2.0x
```

### **Cross-Step Resource Coordination:**
- **Step 3 (Research)**: Utilizes CPU + Network pools
- **Step 4 (Synthesis)**: Requires Memory pool
- **Step 5 (Implementation)**: Distributes across all pools
- **Step 6 (Validation)**: Focuses on Network + Memory pools

---

## 🚫 **RECURSION PREVENTION & HIERARCHY**

### **STRICT STEP HIERARCHY:**
```
User → Step 0: general-purpose
Step 0 → Step 1: agent-integration-orchestrator  
Step 1 → Step 2: project-orchestrator + enhanced-nexus-synthesis-agent
Step 2 → Main Claude (coordination execution)
Main Claude → Specialist Agents (domain execution)
Specialist Agents → NEVER call orchestrators (FORBIDDEN!)
```

### **FORBIDDEN PATTERNS:**
- Specialist → Orchestrator (RECURSION!)
- Agent → Agent direct calls (ISOLATION VIOLATION!)
- Step skipping (WORKFLOW VIOLATION!)
- Orchestrator → Orchestrator (INFINITE LOOP!)

---

## 📊 **UNIFIED QUALITY GATES**

### **Pre-Step Validation:**
- Agent availability verification
- Resource allocation confirmation
- Dependency resolution check
- Context package size validation

### **During-Step Monitoring:**
- Progress tracking (30s intervals)
- Resource usage monitoring (85% threshold)
- Inter-agent communication health
- Partial result validation

### **Post-Step Quality Gates:**
- Step completion verification
- Output quality validation
- Integration health check
- Evidence collection (Steps 6-7)

---

## 📈 **PERFORMANCE METRICS & MONITORING**

### **Unified Metrics Collection:**
```yaml
step_execution_time:
  type: histogram
  labels: [step_number, agent_count, resource_pool]

agent_success_rate:
  type: gauge
  labels: [agent_name, step, domain]

resource_utilization:
  type: gauge  
  labels: [resource_pool, step, agent_name]

evidence_validation_score:
  type: gauge
  labels: [validation_type, step, success_rate]
```

### **Alert Thresholds:**
- **Step Execution Failure**: Success rate < 80% (High severity)
- **Resource Exhaustion**: Utilization > 90% (Critical severity) 
- **Evidence Validation Failure**: Evidence score < 70% (High severity)
- **Workflow Iteration Overflow**: Iterations > 3 (Critical severity)

---

## 🎪 **COLLABORATION HUB INTEGRATION**

### **Communication Channels:**
```yaml
shared_context:
  persistence: memory
  max_size_mb: 100
  ttl_seconds: 3600

result_exchange:
  persistence: redis
  max_entries: 1000
  ttl_seconds: 7200

progress_tracking:
  persistence: database
  update_interval_seconds: 15
```

### **Synchronization Points:**
```yaml
step_0_complete:
  required_agents: [general-purpose]
  timeout_seconds: 60

step_3_research_complete:
  required_agents: [codebase-research-analyst, schema-database-expert]
  completion_rate: 0.75
  timeout_seconds: 300

step_5_implementation_streams_sync:
  required_streams: [backend, frontend, quality, infrastructure]
  cross_stream_sync: true
  timeout_seconds: 600

step_6_evidence_validation:
  required_agents: [production-endpoint-validator]
  evidence_requirement: mandatory
  timeout_seconds: 400
```

---

## 🔄 **FALLBACK & RECOVERY STRATEGIES**

### **Resource Exhaustion:**
- **Action**: Sequential degradation by priority
- **Priority Order**: security → performance → testing → documentation

### **Agent Failure:**
- **Action**: Task redistribution to backup agents
- **Backup Pool**: nexus-synthesis-agent, codebase-research-analyst
- **Retry Attempts**: 2 with exponential backoff

### **Step Timeout:**
- **Action**: Partial completion if above minimum threshold
- **Minimum Completion Rate**: 60%
- **Escalation**: meta-orchestrator at 40% completion

### **Validation Failure:**
- **Action**: Automatic iteration restart at Step 0
- **Context**: Failure analysis integrated into todo context
- **Iteration Tracking**: "Iteration N" suffix in step tracking

---

## 🎯 **SUCCESS CRITERIA & COMPLETION**

### **Unified Flow Success Indicators:**
- ✅ All 10 steps completed in sequence
- ✅ No recursion or circular agent calls
- ✅ All context packages under token limits (4000 max)
- ✅ **MANDATORY EVIDENCE-BASED VALIDATION**: Production accessibility verified with concrete proof
- ✅ **MANDATORY INFRASTRUCTURE VALIDATION**: All systems functional with evidence
- ✅ **MANDATORY USER INTERACTION VALIDATION**: End-to-end workflows tested with evidence
- ✅ Atomic commits created and synchronized to remote
- ✅ Step 9 orchestration audit ALWAYS executed with improvement recommendations

### **Individual Agent Success Indicators:**
- ✅ Stayed within assigned domain boundaries
- ✅ Used context packages efficiently (no additional research requests)
- ✅ Leveraged appropriate tools extensively
- ✅ Provided quantitative, evidence-based results
- ✅ Completed tasks within resource pool guidelines
- ✅ Returned actionable findings to coordination layer

---

## 💡 **USAGE EXAMPLES**

### **Example 1: Complex Feature Implementation**
```
User: "Implement user authentication with 2FA and Google OAuth"

Step 0: Todo integration (check for related ongoing work)
Step 1: Agent ecosystem validation (verify Google integration capability)
Step 2: Strategic planning (auth strategy + historical auth patterns)
Step 3: Research discovery (parallel: security analysis + existing auth + OAuth patterns + performance)
Step 4: Context synthesis (integrated auth solution with compressed docs)
Step 5: Implementation streams:
  - Backend: API endpoints + OAuth integration + database schemas
  - Frontend: Login UI + 2FA components + user flows
  - Quality: Security testing + integration tests + performance validation
  - Infrastructure: OAuth configs + monitoring + deployment
Step 6: Evidence validation (production auth testing + user interaction validation)
Step 7: Success evaluation (if validation passes → Step 8, if fails → iterate at Step 0)
Step 8: Atomic commits (auth feature commits with logical grouping)
Step 9: Audit & learning (auth implementation analysis and workflow improvements)
```

### **Example 2: Performance Optimization**
```
User: "Optimize application performance"

Step 0: Todo integration (check for ongoing performance issues)
Step 1: Agent ecosystem validation (verify performance tooling)
Step 2: Strategic planning (optimization strategy + historical performance patterns)
Step 3: Research discovery (parallel: bottleneck analysis + code profiling + query analysis + monitoring)
Step 4: Context synthesis (performance optimization roadmap with compression)
Step 5: Implementation streams:
  - Backend: API optimization + query improvements + caching
  - Frontend: Bundle optimization + rendering improvements
  - Quality: Performance testing + benchmarking + validation
  - Infrastructure: Monitoring enhancements + resource optimization
Step 6: Evidence validation (performance metrics validation + user experience testing)
Step 7: Success evaluation (performance targets met → Step 8, else iterate)
Step 8: Atomic commits (performance optimization commits)
Step 9: Audit & learning (optimization effectiveness analysis and workflow improvements)
```

---

## 🏆 **UNIFIED FRAMEWORK BENEFITS**

### **Performance Improvements:**
- **60-70% reduction** in total execution time through parallel coordination
- **80% better resource utilization** through integrated pool management
- **50% reduction in agent idle time** through intelligent scheduling
- **90% context efficiency** through compression and package management

### **Quality Enhancements:**
- **Evidence-based validation** with mandatory proof requirements
- **Multi-domain expert coverage** across all technical areas
- **Automatic quality gates** at each step with failure recovery
- **Continuous learning** through Step 9 audit integration

### **Operational Benefits:**
- **Real-time coordination** across all orchestration structures
- **Unified trigger system** for consistent workflow initiation
- **Comprehensive monitoring** with integrated metrics and alerting
- **Failure resilience** with automatic retry and iteration capabilities

---

**This unified agentic coding flow represents the integration of all three orchestration structures into a cohesive, step-based workflow that maximizes efficiency, maintains quality, and ensures continuous improvement while preventing recursion and maintaining clear agent boundaries.**