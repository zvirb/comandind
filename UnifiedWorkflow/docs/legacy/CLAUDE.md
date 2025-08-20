# ⛔⛔⛔ STOP! MANDATORY AGENT HIERARCHY PROTOCOL ⛔⛔⛔

## 🚨🚨🚨 CRITICAL: RECURSION PREVENTION SYSTEM ACTIVE 🚨🚨🚨

### ⚡ AGENT HIERARCHY - STRICT ENFORCEMENT ⚡

**MANDATORY CALL HIERARCHY TO PREVENT INFINITE LOOPS:**

```
1. User → project-orchestrator (ONLY user can call orchestrator)
2. project-orchestrator → Main Claude (orchestrator DELEGATES to you)
3. Main Claude → Specialist Agents (you EXECUTE the plan)
4. Specialist Agents → NEVER call orchestrators (FORBIDDEN - causes recursion!)
```

### 🛑 RECURSION PREVENTION RULES:
- **RULE 1**: Only the USER can call project-orchestrator
- **RULE 2**: project-orchestrator NEVER calls other orchestrators
- **RULE 3**: Specialist agents NEVER call ANY orchestrator
- **RULE 4**: No agent can call itself (direct recursion forbidden)
- **RULE 5**: Main Claude executes plans, doesn't create new orchestration loops

### 🛑 STOP AND CHECK BEFORE ANY ACTION:
- [ ] Am I about to call project-orchestrator FIRST? (If NO → STOP!)
- [ ] Am I thinking of calling a specialist agent directly? (If YES → STOP!)
- [ ] Have I verified project-orchestrator is my FIRST action? (If NO → STOP!)

### ⚠️ RECURSION DETECTION SYSTEM ⚠️
**Active Monitoring with `.claude/agent_logger.py`**

If recursion is detected:
1. **IMMEDIATE HALT**: Execution stops with RecursionError
2. **LOGGED**: Full call stack saved to `.claude/logs/`
3. **PREVENTED**: Call rejected before execution
4. **REPORTED**: Recursion chain shown in error message

**Common Recursion Patterns (FORBIDDEN):**
- Specialist → project-orchestrator → Specialist (LOOP!)
- orchestrator → orchestrator → orchestrator (INFINITE!)
- Agent A → Agent B → Agent A (CIRCULAR!)
- Any agent calling project-orchestrator except USER

---

# Claude AI Development Instructions

## 🚨 CRITICAL: ALWAYS READ AIASSIST.md FIRST

**MANDATORY FIRST STEP**: Before beginning ANY development work or answering questions about this codebase, you MUST read the **[AIASSIST.md](./AIASSIST.md)** file to understand the system architecture and development patterns.

## 📋 Required Reading

**AIASSIST.md** contains essential information including:
- System architecture overview
- Multi-container service interactions
- **CRITICAL**: Python import patterns (`from shared.` prefix requirement)
- Database migration guidelines
- Development best practices
- Security model
- Container-specific configurations

## ⚠️ Development Rules

1. **READ AIASSIST.md FIRST** - This is not optional
2. Follow the `from shared.` import pattern for all Python code
3. Never make direct database schema changes - use Alembic migrations
4. Understand the service communication flow: webui → caddy → api → worker/postgres/redis
5. Respect the security model and container boundaries

## 🚨🚨🚨 REMINDER: PROJECT-ORCHESTRATOR IS MANDATORY 🚨🚨🚨

**⛔ STOP! Before proceeding, confirm you're using project-orchestrator FIRST! ⛔**

## 🤖 Agent Instructions - MANDATORY PROJECT-ORCHESTRATOR USAGE

**🚨 CRITICAL: EVERY user interaction MUST use the project-orchestrator agent**

### ⚡ ENFORCEMENT CHECKPOINT ⚡
**BEFORE READING FURTHER, VERIFY:**
- [ ] I understand project-orchestrator is MANDATORY for ALL requests
- [ ] I will NEVER call specialist agents directly
- [ ] I will ALWAYS use project-orchestrator as my FIRST action
- [ ] I understand violations are UNACCEPTABLE

### Absolute Requirements:
1. **NEVER** call specialist agents directly
2. **ALWAYS** use `project-orchestrator` as the first and primary agent for ALL user requests
3. **NO EXCEPTIONS** - Even simple requests must go through project-orchestrator
4. **RESEARCH-FIRST MANDATE**: Project-orchestrator MUST always start with codebase-research-analyst
5. **NO IMPLEMENTATION BY ORCHESTRATOR**: Project-orchestrator NEVER implements fixes itself

### Project-Orchestrator Authority:
- **Research Coordination**: ALWAYS begins with codebase-research-analyst for technical tasks
- **Strategic Planning**: Creates implementation plans based on research findings
- **MULTI-AGENT COORDINATION**: Orchestrates multiple specialist agents working in parallel
- **NO DIRECT IMPLEMENTATION**: Never performs technical work - only coordinates and instructs
- **MAIN CLAUDE EXECUTION**: After orchestration, main Claude executes the coordinated plan using multiple agents

### Workflow Pattern (WITH RECURSION PREVENTION):
```
✅ CORRECT FLOW:
User Request 
  → project-orchestrator (creates plan, NO IMPLEMENTATION)
    → Returns plan to Main Claude
      → Main Claude executes with specialist agents
        → Specialists complete tasks (NO ORCHESTRATOR CALLS)
          → Results returned to user

❌ FORBIDDEN FLOWS (CAUSE RECURSION):
- Specialist → project-orchestrator → ... (RECURSION!)
- orchestrator → orchestrator → ... (INFINITE LOOP!)
- Main Claude → project-orchestrator → ... (CIRCULAR!)
```

### Multi-Agent Orchestration Protocol (RECURSION-SAFE):
```
1. USER calls project-orchestrator with request
2. project-orchestrator analyzes and creates plan (NO AGENT CALLS)
3. project-orchestrator RETURNS plan to Main Claude
4. Main Claude RECEIVES plan and executes it:
   - Calls codebase-research-analyst for context
   - Calls backend-gateway-expert for API/server issues
   - Calls ui-regression-debugger for frontend testing
   - Calls other specialists as needed
5. Each specialist:
   - Completes their task
   - Returns results to Main Claude
   - NEVER calls any orchestrator
6. Main Claude aggregates results
7. Returns final result to user

⚠️ CRITICAL: Steps 4-6 are YOUR responsibility as Main Claude!
```

### Tool Discovery:
- **Agent Registry**: Consult **[.claude/AGENT_REGISTRY.md](./.claude/AGENT_REGISTRY.md)** for all available specialist agents
- **Automatic Delegation**: Project-orchestrator determines optimal agent combinations
- **No Manual Intervention**: Standard development tasks execute autonomously

## 🔄 When Starting New Conversations

If you are Claude starting a new conversation about this codebase:
1. **IMMEDIATELY** read AIASSIST.md before doing anything else
2. Understand the architecture before making changes
3. Follow established patterns and practices

## 📁 Project Structure

- **`.claude/`** - Claude AI configuration and agent definitions
- **`app/`** - Main application code (API, WebUI, Worker, Shared modules)
- **`docker/`** - Container configurations and scripts
- **`scripts/`** - Automation and deployment scripts
- **`docs/`** - Comprehensive project documentation
- **`config/`** - Service configurations (Caddy, PostgreSQL, Redis, etc.)

## 🔧 Development Workflow - RECURSION-SAFE OPERATIONS

1. **USER initiates with project-orchestrator** - Only user can call orchestrator
2. **ORCHESTRATOR PLANS ONLY** - Returns plan without calling agents
3. **MAIN CLAUDE EXECUTES** - You receive plan and call specialists
4. **RESEARCH-FIRST EXECUTION** - You call codebase-research-analyst first
3. **MULTI-AGENT ORCHESTRATION** - Project-orchestrator coordinates multiple agents, main Claude executes
4. **ITERATIVE DEBUG-FIX LOOPS** - Continue testing and fixing until complete success
5. **PLAYWRIGHT MANDATE** - UI testing MUST use playwright tools via ui-regression-debugger
6. **PARALLEL AGENT EXECUTION** - Launch multiple agents simultaneously for complex issues
7. **Automatic Progress Tracking** - Use TodoWrite tool for transparency
8. **Security-Integrated Planning** - Security considerations built into agent workflows

### 🎯 Critical Testing Requirements:
- **Frontend Issues**: MUST use ui-regression-debugger with playwright tools
- **Login Testing**: MUST attempt actual login flows through browser automation
- **API Testing**: Use backend-gateway-expert for endpoint validation
- **Integration Testing**: Use fullstack-communication-auditor for frontend-backend issues
- **Iterative Process**: Continue debug-fix cycles until user objectives are completely met

### 🚨 VERIFICATION MANDATE - NO FALSE SUCCESS CLAIMS:
- **NEVER CLAIM SUCCESS WITHOUT PROOF**: All agents must provide actual browser evidence
- **REAL CREDENTIAL TESTING**: Must attempt login with actual test credentials through Playwright
- **SCREENSHOT EVIDENCE**: Must provide visual proof of success/failure states
- **CONSOLE LOG VERIFICATION**: Must capture and analyze actual JavaScript errors
- **NETWORK REQUEST MONITORING**: Must verify API calls succeed with real responses
- **USER JOURNEY COMPLETION**: Must demonstrate complete login-to-dashboard flow works
- **ITERATIVE DEBUGGING**: Continue testing and fixing until user can personally verify success

### Agentic Workflow Enablers:
- ✅ **No Manual Approvals Required** for standard development tasks
- ✅ **Autonomous Agent Coordination** across multiple specialists  
- ✅ **End-to-End Task Completion** without human intervention
- ✅ **Intelligent Error Recovery** and workflow adaptation
- ✅ **Seamless Multi-Agent Collaboration** for complex projects

### Removed Blockers:
- ❌ Manual approval requirements for agent calls
- ❌ Step-by-step confirmation requests
- ❌ Artificial delays in agent coordination
- ❌ Restrictions on agent-to-agent communication

## ⛔ ANOTHER REMINDER: USE PROJECT-ORCHESTRATOR! ⛔

**If you've read this far without using project-orchestrator, you're already in violation!**

## 🔄 MANDATORY ITERATIVE TESTING WORKFLOW

### ⚡ TOP-LEVEL PATTERN FOR ALL USER REQUESTS ⚡

**EVERY user request MUST follow this iterative structure:**

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. EXECUTE: Execute user prompt using project-orchestrator      │
│    → Research → Specialists → Implement fixes                   │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. VALIDATE: Test from user perspective to confirm resolution   │
│    → Recreate original user experience                          │
│    → Verify NO errors persist                                   │
│    → Collect evidence (screenshots, logs, test results)         │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. ITERATE OR COMPLETE:                                         │
│    → IF errors found: Return to step 1 with new error context  │  
│    → IF no errors: Produce comprehensive success report         │
└─────────────────────────────────────────────────────────────────┘
```

### 🧪 CRITICAL VALIDATION REQUIREMENTS

**STEP 2 MUST ALWAYS INCLUDE:**
- **User Perspective Recreation**: Test exactly as the user would experience it
- **Original Issue Verification**: Confirm the reported problem is completely resolved  
- **End-to-End Testing**: Test complete workflows, not isolated components
- **Evidence Collection**: Screenshots, logs, API responses, error messages
- **New Issue Detection**: Check if fixes introduced any new problems

## 🎯 Implementation Examples

### ✅ CORRECT: Complete Iterative Workflow
```
User: "Fix the login system at aiwfe.com"

ITERATION 1:
• Execute: project-orchestrator → backend-gateway-expert → API fixes
• Validate: ui-regression-debugger tests login → Still 500 errors  
• Result: ERRORS FOUND → Continue to iteration 2

ITERATION 2: 
• Execute: project-orchestrator → schema-database-expert → DB connection fixes
• Validate: ui-regression-debugger tests login → Login works, but session lost on refresh
• Result: ERRORS FOUND → Continue to iteration 3

ITERATION 3:
• Execute: project-orchestrator → session management fixes
• Validate: ui-regression-debugger tests complete login flow → ✅ ALL working
• Result: NO ERRORS → Generate success report

FINAL REPORT: 
"✅ Authentication system fully resolved:
- Fixed API 500 errors (database connection issue)
- Fixed session persistence (cookie configuration)  
- Verified complete login flow works end-to-end
- Evidence: [screenshots, logs, test results]"
```

### ❌ INCORRECT: Fix Without Validation
```
User: "Fix the login system"
Claude: project-orchestrator → backend fixes → "Authentication fixed!"
(No validation testing - user still experiences login failures)
```

### 🚨 MANDATORY CHECK BEFORE EXAMPLES 🚨
**STOP! Are you following the iterative testing pattern? If not, go back and start over!**

## 🚨 ENFORCEMENT NOTICE

**Any Claude instance that does NOT use project-orchestrator as the primary agent is operating outside established protocols and must immediately correct this behavior.**

### ⚠️ VIOLATION CONSEQUENCES ⚠️
**If you violate the project-orchestrator protocol:**
1. **IMMEDIATE HALT**: Stop all actions immediately
2. **ACKNOWLEDGE ERROR**: Admit the protocol violation to the user
3. **RESTART CORRECTLY**: Begin again with project-orchestrator
4. **NO EXCUSES**: "I forgot" or "It seemed simpler" are NOT acceptable

### 🛑 FINAL COMPLIANCE CHECKPOINT 🛑
**BEFORE TAKING ANY ACTION:**
- [ ] I am calling project-orchestrator FIRST (not any other agent)
- [ ] I understand direct specialist calls are FORBIDDEN
- [ ] I will let project-orchestrator coordinate ALL work
- [ ] I acknowledge violations are UNACCEPTABLE
- [ ] I will STOP if I'm about to violate this protocol

### ⚡ REMEMBER: YOUR FIRST ACTION MUST BE PROJECT-ORCHESTRATOR ⚡

**THE ONLY ACCEPTABLE FIRST RESPONSE TO ANY USER REQUEST:**
```
"I'll use the project-orchestrator to coordinate this request..."
[Calls project-orchestrator agent]
```

### 🚨🚨🚨 ABSOLUTE FINAL WARNING 🚨🚨🚨
**IF YOU'RE ABOUT TO CALL ANY AGENT OTHER THAN PROJECT-ORCHESTRATOR FIRST:**
# STOP! YOU ARE IN VIOLATION!

---

*This file establishes Claude AI development guidelines and MANDATES the use of the project-orchestrator agent for ALL user interactions. No exceptions. Any violation of this protocol is a critical error that must be immediately corrected.*

## ⛔ ONE MORE TIME: USE PROJECT-ORCHESTRATOR FOR EVERYTHING! ⛔

## 📊 COMPREHENSIVE LOGGING AND MONITORING

### 🚨 MANDATORY EXECUTION LOGGING

**ALL agents MUST use the logging system to track every action:**

```python
# Import the logger
from .claude.agent_logger import log_action, log_verification

# Log every agent action BEFORE execution
log_action("agent-name", "action-description", 
          tools_used=["tool1", "tool2"], 
          result="action result")

# Log verification attempts
log_verification("agent-name", "verification-type", 
                result=True/False, evidence="proof")
```

### 📁 LOG FILE LOCATIONS:
- **`.claude/logs/execution.log`** - All agent actions
- **`.claude/logs/agents/[agent]-[timestamp].log`** - Individual agent logs
- **`.claude/logs/orchestration.log`** - Project-orchestrator plans
- **`.claude/logs/validation.log`** - Verification attempts
- **`.claude/logs/RECURSION_ERRORS.log`** - Blocked recursion attempts
- **`.claude/logs/screenshots/`** - UI testing evidence

### ⚠️ LOGGING REQUIREMENTS BY AGENT:

#### ui-regression-debugger:
```python
# MUST log every Playwright action
log_action("ui-regression-debugger", "navigate to login page", 
          tools_used=["playwright-navigate"], result="page loaded")

# MUST save screenshots as evidence
await page.screenshot({path: '.claude/logs/screenshots/login-attempt.png'})
log_verification("ui-regression-debugger", "login-visual-check", 
                result=True, evidence="screenshot: login-attempt.png")
```

#### backend-gateway-expert:
```python
# MUST log all API calls
log_action("backend-gateway-expert", "test authentication endpoint", 
          tools_used=["curl", "docker-logs"], result="200 OK response")

# MUST log service health checks
log_verification("backend-gateway-expert", "service-health", 
                result=True, evidence="container running, logs clean")
```

#### codebase-research-analyst:
```python
# MUST log all code searches
log_action("codebase-research-analyst", "search for authentication code", 
          tools_used=["grep", "find"], result="found 15 auth-related files")
```

### 🔍 EXECUTION MONITORING:

After EVERY user request, generate execution trace:
```bash
# Check execution trace
python .claude/visualize_execution.py

# Check for recursion violations
if [ -f .claude/logs/RECURSION_ERRORS.log ]; then
    echo "⚠️ RECURSION DETECTED!"
    cat .claude/logs/RECURSION_ERRORS.log
fi

# Show execution summary
python .claude/agent_logger.py
```

### 🛡️ RECURSION PREVENTION ACTIVE:

**The logging system includes AUTOMATIC recursion detection:**
- Any agent attempting to call project-orchestrator will FAIL immediately
- All violations logged to `.claude/logs/RECURSION_ERRORS.log`
- System prevents infinite loops BEFORE they start

### 📈 SUCCESS VERIFICATION:

**NEVER claim success without logged evidence:**
1. **Screenshot proof** for UI changes
2. **API response logs** for backend fixes  
3. **Test execution logs** for functionality verification
4. **Error resolution logs** showing before/after states