# AIWFE Agent Coordination Strategy

## Strategic Coordination Framework

### Agent Hierarchy & Boundaries

```yaml
Orchestration Layer:
  Primary: project-orchestrator
  Intelligence: enhanced-nexus-synthesis-agent
  Validation: orchestration-auditor-v2
  Context: document-compression-agent
  Version Control: atomic-git-synchronizer

Specialist Layers:
  Backend Domain:
    - backend-gateway-expert (lead)
    - schema-database-expert
    - python-refactoring-architect
    - performance-profiler
  
  Frontend Domain:
    - webui-architect (lead)
    - frictionless-ux-architect
    - whimsy-ui-creator
    - ui-regression-debugger
  
  Infrastructure Domain:
    - k8s-architecture-specialist (lead)
    - deployment-orchestrator
    - monitoring-analyst
    - dependency-analyzer
  
  Quality Domain:
    - security-validator (lead)
    - test-automation-engineer
    - fullstack-communication-auditor
    - user-experience-auditor
```

---

## Phase-Specific Agent Coordination

### Phase 1: Critical Blocker Resolution (Weeks 1-4)

```yaml
Authentication Fix Team:
  Lead: security-validator
  Support: 
    - backend-gateway-expert (service integration)
    - production-endpoint-validator (validation)
  Tasks:
    - Deploy Keycloak in K8s namespace
    - Implement OAuth2/OIDC flows
    - Validate with 1000 concurrent users
  Evidence:
    - Authentication logs showing 99.9% success
    - Token validation <100ms response times
    - Penetration test passing report

WebSocket Resolution Team:
  Lead: fullstack-communication-auditor
  Support:
    - backend-gateway-expert (Redis implementation)
    - performance-profiler (load testing)
  Tasks:
    - Implement Redis session store
    - Fix null session ID issues
    - Add connection pooling
  Evidence:
    - 1000+ concurrent WebSocket connections
    - Zero null session errors in 24 hours
    - Load test showing <50ms latency

Service Mesh Team:
  Lead: k8s-architecture-specialist
  Support:
    - monitoring-analyst (observability)
    - production-endpoint-validator (health checks)
  Tasks:
    - Deploy Istio service mesh
    - Replace Helios with Envoy proxies
    - Configure circuit breakers
  Evidence:
    - Service mesh dashboard operational
    - 99.95% uptime over 7 days
    - Distributed tracing functional
```

### Phase 2: Foundation & Architecture (Weeks 5-12)

```yaml
Infrastructure Team:
  Lead: k8s-architecture-specialist
  Parallel Agents:
    - deployment-orchestrator (GitOps setup)
    - monitoring-analyst (Prometheus/Grafana)
    - security-validator (RBAC/policies)
  Coordination:
    Week 5-6: Cluster provisioning (EKS/GKE)
    Week 7-8: GitOps with ArgoCD
    Week 9-10: Monitoring stack deployment
    Week 11-12: Security hardening
  Context Package: 
    - Cluster specifications
    - Network topology
    - Security requirements
    - Monitoring targets

Architecture Team:
  Lead: backend-gateway-expert
  Parallel Agents:
    - schema-database-expert (data design)
    - performance-profiler (optimization)
    - documentation-specialist (blueprints)
  Coordination:
    Week 5-8: Service mapping and analysis
    Week 9-10: Consolidation design
    Week 11-12: Migration planning
  Context Package:
    - Current service inventory
    - Dependency matrix
    - Performance baselines
    - Target architecture
```

### Phase 3: Service Consolidation (Weeks 13-24)

```yaml
Backend Consolidation Stream:
  Week 13-16: Gateway & Auth Services
    Agents:
      - backend-gateway-expert (Kong/Traefik setup)
      - security-validator (auth service migration)
      - test-automation-engineer (test migration)
    Deliverables:
      - 8 proxy services → 1 API Gateway
      - 4 auth services → 1 Keycloak
  
  Week 17-20: Business Logic Services
    Agents:
      - python-refactoring-architect (code consolidation)
      - schema-database-expert (data migration)
      - performance-profiler (optimization)
    Deliverables:
      - 12 microservices → 2 core services
      - Shared libraries created
      - Performance benchmarks met
  
  Week 21-24: Support Services
    Agents:
      - backend-gateway-expert (service merge)
      - monitoring-analyst (observability)
      - dependency-analyzer (package consolidation)
    Deliverables:
      - 6 data services → 2 services
      - Monitoring unified
      - Dependencies optimized

Quality Assurance Stream (Continuous):
  Agents:
    - test-automation-engineer (test coverage)
    - security-validator (vulnerability scanning)
    - fullstack-communication-auditor (integration testing)
    - user-experience-auditor (user validation)
  Validation Frequency:
    - Daily: Automated test execution
    - Weekly: Security scanning
    - Bi-weekly: User journey testing
    - Per deployment: Full validation suite
```

### Phase 4: WebUI Transformation (Weeks 25-36)

```yaml
Frontend Development Stream:
  Week 25-28: Foundation
    Lead: webui-architect
    Team:
      - frictionless-ux-architect (UX patterns)
      - whimsy-ui-creator (design system)
    Tasks:
      - Next.js 14 with App Router setup
      - Cosmos.so design implementation
      - Component library creation
  
  Week 29-32: Core Features
    Lead: frictionless-ux-architect  
    Team:
      - webui-architect (architecture)
      - ui-regression-debugger (testing)
    Tasks:
      - Dashboard implementation
      - Agent orchestration UI
      - Real-time monitoring views
  
  Week 33-36: Advanced Features
    Lead: whimsy-ui-creator
    Team:
      - fullstack-communication-auditor (API integration)
      - user-experience-auditor (E2E testing)
    Tasks:
      - AI opportunity management UI
      - Pieces OS integration frontend
      - Analytics dashboards

Validation Stream:
  Continuous Agents:
    - ui-regression-debugger (visual testing)
    - performance-profiler (frontend performance)
    - user-experience-auditor (user testing)
  Metrics:
    - Lighthouse scores >90
    - Core Web Vitals passing
    - User task completion >95%
```

### Phase 5: Integration & Optimization (Weeks 37-44)

```yaml
Integration Coordination:
  External Services Team:
    - google-services-integrator (Google APIs)
    - langgraph-ollama-analyst (LLM integration)
    - backend-gateway-expert (orchestration)
  
  Optimization Team:
    - performance-profiler (bottleneck analysis)
    - schema-database-expert (query optimization)
    - monitoring-analyst (resource tuning)
  
  Parallel Execution:
    Week 37-40: External integrations
    Week 41-44: Performance optimization
```

### Phase 6: Production Deployment (Weeks 45-52)

```yaml
Deployment Coordination:
  Lead: deployment-orchestrator
  Support Team:
    - production-endpoint-validator (validation)
    - monitoring-analyst (observability)
    - security-validator (security checks)
    - user-experience-auditor (user validation)
  
  Staged Rollout:
    Week 45-46: Staging validation
    Week 47-48: Canary deployment (5%)
    Week 49-50: Progressive rollout
    Week 51-52: Full production
```

---

## Parallel Execution Patterns

### Resource-Aware Scheduling

```yaml
CPU Intensive (Max 2 concurrent):
  - performance-profiler
  - codebase-research-analyst
  - test-automation-engineer
  - python-refactoring-architect

I/O Intensive (Max 3 concurrent):
  - schema-database-expert
  - documentation-specialist
  - dependency-analyzer
  - project-structure-mapper

Network Intensive (Max 2 concurrent):
  - security-validator
  - production-endpoint-validator
  - google-services-integrator
  - fullstack-communication-auditor

Memory Intensive (Max 2 concurrent):
  - enhanced-nexus-synthesis-agent
  - langgraph-ollama-analyst
  - ui-regression-debugger
  - user-experience-auditor

Context Optimized (Max 5 concurrent):
  - monitoring-analyst
  - deployment-orchestrator
  - backend-gateway-expert
  - webui-architect
  - frictionless-ux-architect
```

### Coordination Protocols

```yaml
Communication Patterns:
  Broadcast:
    - Status updates every 6 hours
    - Blocker notifications immediate
    - Success milestones within 1 hour
  
  Point-to-Point:
    - Context packages via Main Claude
    - Evidence submission to validators
    - Error reports to lead agents
  
  Synchronization:
    - Daily standup at phase boundaries
    - Weekly retrospective per stream
    - Phase gates require all streams ready
```

### Context Package Management

```yaml
Package Size Limits:
  Strategic: 3000 tokens
  Technical: 4000 tokens
  Validation: 2000 tokens
  Error: 1000 tokens

Distribution Rules:
  - Agents receive ONLY their package
  - No cross-domain package sharing
  - Compressed if >limit
  - Validated before distribution

Package Templates:
  Backend Package:
    - Service specifications
    - API contracts
    - Database schemas
    - Performance requirements
  
  Frontend Package:
    - UI requirements
    - Component specifications
    - Design tokens
    - User flows
  
  Infrastructure Package:
    - K8s manifests
    - Network policies
    - Resource limits
    - Monitoring rules
```

---

## Agent Collaboration Matrix

### Direct Collaboration Allowed

| Agent 1 | Agent 2 | Purpose |
|---------|---------|---------|
| backend-gateway-expert | schema-database-expert | API-DB integration |
| webui-architect | frictionless-ux-architect | UI/UX alignment |
| k8s-architecture-specialist | deployment-orchestrator | Infrastructure deployment |
| security-validator | production-endpoint-validator | Security validation |
| test-automation-engineer | ui-regression-debugger | Test coordination |

### Forbidden Interactions

| Agent Type | Cannot Call | Reason |
|------------|------------|---------|
| Specialists | Orchestrators | Prevents recursion |
| Specialists | Other specialists (different domain) | Maintains boundaries |
| Orchestrators | Other orchestrators | Avoids loops |
| All agents | Themselves | Prevents infinite recursion |

---

## Evidence Collection Requirements

### Per-Agent Evidence Types

```yaml
backend-gateway-expert:
  - API response times
  - Service health checks
  - Traffic routing logs
  - Error rates

schema-database-expert:
  - Query execution plans
  - Migration success logs
  - Performance metrics
  - Data integrity checks

security-validator:
  - Penetration test reports
  - Vulnerability scan results
  - Authentication logs
  - Compliance certificates

ui-regression-debugger:
  - Screenshot comparisons
  - Lighthouse reports
  - Browser test results
  - Performance traces

production-endpoint-validator:
  - Endpoint availability
  - SSL certificate status
  - Response time graphs
  - Cross-region validation

user-experience-auditor:
  - User journey recordings
  - Task completion rates
  - Error screenshots
  - Interaction heatmaps
```

### Evidence Storage Protocol

```yaml
Storage Structure:
  /evidence/
    /phase-1/
      /auth-validation/
      /websocket-tests/
      /service-mesh/
    /phase-2/
      /infrastructure/
      /architecture/
    ...

Retention Policy:
  - Critical evidence: Permanent
  - Test results: 90 days
  - Performance data: 180 days
  - Screenshots: 30 days

Access Control:
  - Write: Agent that generated
  - Read: All agents in same phase
  - Audit: Orchestration agents only
```

---

## Scope Boundary Enforcement

### Agent Scope Limits

```yaml
Backend Agents:
  Allowed:
    - Server-side code changes
    - API modifications
    - Database operations
    - Service configuration
  Forbidden:
    - Frontend code changes
    - UI modifications
    - Client-side logic
    - Style changes

Frontend Agents:
  Allowed:
    - React/Next.js code
    - CSS/styling
    - Client-side state
    - UI components
  Forbidden:
    - Server code changes
    - Database queries
    - API implementations
    - Infrastructure configs

Infrastructure Agents:
  Allowed:
    - K8s manifests
    - Network policies
    - Resource definitions
    - Monitoring configs
  Forbidden:
    - Application code
    - Business logic
    - UI changes
    - Database schemas
```

### Scope Validation Process

```yaml
Pre-Execution:
  1. Agent proposes actions
  2. Main Claude validates scope
  3. Approval/rejection decision
  4. Execution or re-planning

Violations:
  - Warning on first violation
  - Task reassignment on second
  - Agent suspension on third
  
Recovery:
  - Identify correct agent
  - Transfer context package
  - Resume execution
```

---

## Continuous Improvement Loop

### Feedback Collection

```yaml
Per-Phase Metrics:
  - Agent efficiency scores
  - Parallel execution success
  - Context package effectiveness
  - Evidence quality ratings
  - Scope violation frequency

Weekly Analysis:
  - Bottleneck identification
  - Coordination improvements
  - Package optimization
  - Evidence standardization
```

### Optimization Actions

```yaml
Agent Performance:
  - Retrain underperforming agents
  - Adjust parallelization limits
  - Optimize context packages
  - Improve evidence templates

Coordination Efficiency:
  - Streamline communication
  - Reduce synchronization points
  - Enhance parallel patterns
  - Automate evidence collection
```

---

## Implementation Checklist

### Pre-Coordination
- [ ] Agent availability verified
- [ ] Context packages prepared
- [ ] Scope boundaries defined
- [ ] Evidence requirements clear
- [ ] Parallel streams planned

### During Coordination
- [ ] Agents receiving correct packages
- [ ] Parallel execution monitored
- [ ] Scope boundaries enforced
- [ ] Evidence being collected
- [ ] Communication flowing

### Post-Coordination
- [ ] All evidence collected
- [ ] Results validated
- [ ] Lessons documented
- [ ] Improvements identified
- [ ] Next phase prepared