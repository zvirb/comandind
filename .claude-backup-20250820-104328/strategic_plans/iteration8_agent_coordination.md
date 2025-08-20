# Iteration 8: Agent Coordination Instructions for Integration Crisis Resolution

## Strategic Context
**Focus**: Service Integration and Cross-Service Session Synchronization
**Methodology**: Integration-First Architecture (Not Component Rebuilding)
**Critical Issue**: 48.6% endpoint failure rate due to session boundary failures

---

## Phase 1: Discovery Phase Coordination (25% Checkpoint)

### Parallel Agent Execution Group 1
**Launch Time**: T+0 minutes
**Duration**: 2 hours
**Coordination**: All agents work in parallel, report to nexus-synthesis-agent

#### fullstack-communication-auditor
**Primary Mission**: Map exact service boundary failures
```
CRITICAL FOCUS AREAS:
1. Redis ↔ API Gateway communication
2. API Gateway ↔ Frontend WebSocket
3. JWT validation ↔ Service authentication
4. Documents/Calendar navigation triggers

REQUIRED EVIDENCE:
- Service communication matrix diagram
- Specific failure point logs with timestamps
- Integration gap analysis with root causes
- Network trace of failed session scenarios

TOOLS TO USE:
- Bash: Monitor service logs during navigation
- Grep: Find authentication failures in logs
- Read: Analyze service configuration files
- WebFetch: Test API endpoints directly
```

#### schema-database-expert  
**Primary Mission**: Analyze session data flow through Redis
```
CRITICAL FOCUS AREAS:
1. Redis session key structure and TTL
2. Session data persistence patterns
3. Query patterns during navigation events
4. Data consistency between sessions

REQUIRED EVIDENCE:
- Redis session schema documentation
- Query performance metrics
- Session lifecycle analysis
- Data flow diagram through services

TOOLS TO USE:
- Bash: Redis-cli commands for session inspection
- Grep: Search for session-related queries
- Read: Analyze Redis configuration
- Performance profiling tools
```

#### security-validator
**Primary Mission**: Trace authentication chain breaks
```
CRITICAL FOCUS AREAS:
1. JWT token generation and validation
2. Session token refresh mechanisms
3. Cross-service authentication propagation
4. Security boundary violations

REQUIRED EVIDENCE:
- Complete auth flow diagram
- Token validation failure logs
- Security boundary analysis
- Vulnerability assessment report

TOOLS TO USE:
- Bash: Security scanning tools
- Grep: Find auth-related errors
- WebFetch: Test auth endpoints
- Penetration testing utilities
```

#### performance-profiler
**Primary Mission**: Identify session sync latency issues
```
CRITICAL FOCUS AREAS:
1. Redis query latency measurements
2. JWT validation processing time
3. Cross-service call overhead
4. Session sync bottlenecks

REQUIRED EVIDENCE:
- Latency measurements table
- Performance bottleneck graph
- Resource utilization metrics
- Optimization recommendations

TOOLS TO USE:
- Bash: Performance monitoring commands
- Grep: Find slow query logs
- Performance analysis tools
- System resource monitors
```

---

## Phase 2: Analysis Phase Coordination (50% Checkpoint)

### Sequential Agent Execution
**Launch Time**: T+2 hours
**Duration**: 1.5 hours
**Coordination**: Sequential processing with synthesis

#### nexus-synthesis-agent (Lead)
**Primary Mission**: Synthesize findings into architectural solution
```
INPUT PROCESSING:
1. Receive all Phase 1 discovery reports
2. Identify common failure patterns
3. Design integration architecture
4. Create implementation roadmap

DELIVERABLES:
- Unified session coordination layer design
- Cross-service synchronization protocol
- State reconciliation algorithms
- Risk mitigation strategies

CRITICAL DECISIONS:
- Session event broadcasting mechanism
- JWT refresh strategy
- AuthContext sync approach
- Rollback procedures
```

#### enhanced-nexus-synthesis-agent (Support)
**Primary Mission**: Apply historical patterns and learning
```
HISTORICAL ANALYSIS:
1. Query knowledge graph for similar integration issues
2. Apply successful patterns from past fixes
3. Identify potential failure modes
4. Recommend proven solutions

PATTERN MATCHING:
- Previous session management fixes
- Successful service integration patterns
- Known pitfalls to avoid
- Performance optimization techniques
```

---

## Phase 3: Implementation Phase Coordination (75% Checkpoint)

### Parallel Stream Execution
**Launch Time**: T+3.5 hours
**Duration**: 3 hours
**Coordination**: 4 parallel streams with synchronization points

#### Stream 1: Backend Integration (backend-gateway-expert)
```
IMPLEMENTATION TASKS:
1. Session Synchronization Middleware
   - Redis session event broadcasting
   - JWT token refresh mechanism
   - Session validation middleware
   - Cross-service auth propagation

2. API Gateway Updates
   - Unified authentication middleware
   - Session state preservation
   - Error recovery mechanisms
   - Logging enhancements

VALIDATION CHECKPOINTS:
- 25%: Middleware compiles and deploys
- 50%: Session events broadcasting
- 75%: Cross-service auth working

TOOLS: Edit, MultiEdit, Bash for testing
```

#### Stream 2: Frontend Integration (webui-architect)
```
IMPLEMENTATION TASKS:
1. AuthContext State Management
   - Session persistence hooks
   - Navigation state preservation
   - Real-time sync handlers
   - Recovery mechanisms

2. Component Updates
   - Protected route enhancements
   - Navigation event handlers
   - Session timeout management
   - Error boundary improvements

VALIDATION CHECKPOINTS:
- 25%: Hooks implemented
- 50%: State persistence working
- 75%: Navigation maintains session

TOOLS: Edit, MultiEdit, Bash for build
```

#### Stream 3: Database Optimization (schema-database-expert)
```
IMPLEMENTATION TASKS:
1. Redis Session Optimization
   - Session schema updates
   - Index optimization
   - Event trigger implementation
   - Consistency check procedures

2. Performance Tuning
   - Query optimization
   - Cache configuration
   - TTL adjustments
   - Monitoring setup

VALIDATION CHECKPOINTS:
- 25%: Schema updated
- 50%: Indexes operational
- 75%: Events triggering

TOOLS: Bash for Redis commands, Edit for configs
```

#### Stream 4: Infrastructure Updates (deployment-orchestrator)
```
IMPLEMENTATION TASKS:
1. Service Configuration
   - Environment variable updates
   - Session timeout policies
   - Health check adjustments
   - Service dependencies

2. Deployment Pipeline
   - Integration component deployment
   - Configuration synchronization
   - Monitoring setup
   - Rollback preparation

VALIDATION CHECKPOINTS:
- 25%: Configs updated
- 50%: Services restarted
- 75%: Health checks passing

TOOLS: Edit for configs, Bash for deployment
```

---

## Phase 4: Validation Phase Coordination (100% Checkpoint)

### Comprehensive Parallel Validation
**Launch Time**: T+6.5 hours
**Duration**: 2 hours
**Coordination**: All validation agents parallel with evidence collection

#### user-experience-auditor (Critical Path)
```
END-TO-END USER JOURNEY TESTS:
1. Complete Authentication Flow
   - Login with valid credentials
   - Navigate to Documents
   - Navigate to Calendar
   - Verify session maintained
   - Logout successfully

2. Session Persistence Tests
   - 30-minute idle test
   - Browser refresh recovery
   - Multi-tab synchronization
   - Network interruption recovery

EVIDENCE REQUIREMENTS:
- Playwright screenshots at each step
- Session token verification
- Console log capture
- Performance metrics

SUCCESS CRITERIA:
- Zero logouts during navigation
- Session maintained across all tests
- Recovery mechanisms functional
```

#### fullstack-communication-auditor (API Validation)
```
API INTEGRATION TESTS:
1. Endpoint Recovery Validation
   - Test all 48.6% failing endpoints
   - Verify success rate >90%
   - Check response times
   - Validate error handling

2. Cross-Service Communication
   - Service-to-service auth
   - Data consistency checks
   - Transaction integrity
   - Error propagation

EVIDENCE REQUIREMENTS:
- API response logs
- Success rate statistics
- Latency measurements
- Error analysis report
```

#### security-validator (Security Verification)
```
SECURITY VALIDATION TESTS:
1. Session Security
   - Session hijacking attempts
   - Token refresh security
   - Cross-site isolation
   - Auth chain integrity

2. Vulnerability Assessment
   - OWASP compliance
   - Penetration testing
   - Security headers
   - Encryption validation

EVIDENCE REQUIREMENTS:
- Security scan results
- Penetration test report
- Compliance checklist
- Vulnerability assessment
```

#### performance-profiler (Performance Metrics)
```
PERFORMANCE VALIDATION:
1. Latency Measurements
   - Session sync <100ms
   - JWT validation <50ms
   - Redis operations <20ms
   - API responses <200ms

2. Resource Utilization
   - Memory usage stable
   - CPU usage optimal
   - Network bandwidth
   - Database connections

EVIDENCE REQUIREMENTS:
- Performance graphs
- Resource metrics
- Optimization report
- Bottleneck analysis
```

---

## Critical Success Metrics

### Primary Metrics (MUST ACHIEVE)
1. **Documents/Calendar Navigation**: Zero logouts (Binary Pass/Fail)
2. **Endpoint Failure Rate**: <10% (from current 48.6%)
3. **User Journey Completion**: >90% success rate

### Secondary Metrics (SHOULD ACHIEVE)
1. **Session Sync Latency**: <100ms average
2. **Redis Hit Rate**: >95%
3. **JWT Validation Success**: >99%
4. **AuthContext Consistency**: 100%

---

## Checkpoint Decision Gates

### 25% Gate (Discovery Complete)
**Pass Criteria**: All integration failures mapped with evidence
**Fail Action**: Extended discovery with additional agents

### 50% Gate (Architecture Designed)
**Pass Criteria**: Complete solution architecture validated
**Fail Action**: Architecture revision with risk reassessment

### 75% Gate (Implementation Complete)
**Pass Criteria**: All components deployed and initially tested
**Fail Action**: Targeted fixes with focused agent deployment

### 100% Gate (Validation Complete)
**Pass Criteria**: All primary metrics achieved with evidence
**Fail Action**: Return to Phase 2 for architecture revision

---

## Emergency Procedures

### If Session Crisis Worsens
1. Implement emergency session bypass
2. Deploy temporary stateless mode
3. Enable verbose logging
4. Escalate to meta-orchestrator

### If Integration Fails
1. Rollback to checkpoint
2. Isolate problematic service
3. Implement service bypass
4. Document failure patterns

### If Performance Degrades
1. Enable circuit breakers
2. Reduce sync frequency
3. Implement caching layer
4. Scale Redis cluster

---

## Communication Protocol

### Status Updates
- Every 30 minutes during implementation
- Immediately on critical issues
- At each checkpoint gate
- On completion of each phase

### Evidence Collection
- Store in `.claude/validation_evidence/iteration8/`
- Include timestamps on all evidence
- Maintain chain of custody
- Create summary reports

### Coordination Sync Points
- After each phase completion
- At 25%, 50%, 75% checkpoints
- On any blocking issues
- Before major decisions

---

## Expected Timeline

**Total Duration**: 8.5 hours
- Phase 1 (Discovery): 2 hours
- Phase 2 (Analysis): 1.5 hours
- Phase 3 (Implementation): 3 hours
- Phase 4 (Validation): 2 hours

**Buffer Time**: +1.5 hours for iterations
**Total Estimate**: 10 hours

---

## Success Declaration

Upon achieving all primary metrics with evidence:
1. Generate success report with all evidence
2. Update orchestration knowledge graph
3. Document lessons learned
4. Celebrate integration crisis resolution

This coordination plan ensures systematic resolution of the session management crisis through focused integration work rather than component rebuilding.