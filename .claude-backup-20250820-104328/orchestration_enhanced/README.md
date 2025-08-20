# ML-Enhanced Orchestrator

A robust ML-enhanced orchestration system for Claude Code CLI with comprehensive dependency fallbacks and graceful degradation.

## Features

- **ML-powered decision engine** for intelligent orchestration
- **Graceful dependency handling** with fallback implementations
- **Environment-agnostic operation** - works with or without external dependencies
- **Comprehensive validation** and error handling
- **Stream-based execution** with parallel coordination
- **Container-aware operations** with conflict detection

## Dependencies

### Required (Built-in Python)
- `asyncio` - Asynchronous operations
- `json` - Data serialization
- `time` - Time operations
- `typing` - Type hints
- `pathlib` - Path operations
- `dataclasses` - Data structures
- `enum` - Enumerations
- `uuid` - Unique identifiers

### Optional (with fallbacks)
- `numpy` - Mathematical operations (fallback: built-in math)
- `structlog` - Enhanced logging (fallback: standard logging)

## Installation & Validation

### Quick Validation
```bash
cd .claude/orchestration_enhanced
python3 dependency_validator.py
```

### Manual Testing
```python
# Test basic functionality
from ml_enhanced_orchestrator import MLDecisionEngine, MLEnhancedOrchestrator

# Create instances
engine = MLDecisionEngine()
orchestrator = MLEnhancedOrchestrator()

# Test ML decision making
import asyncio
context = {
    'task_type': 'backend_development',
    'complexity': 0.7,
    'available_agents': [...]
}
decision = asyncio.run(engine.make_decision(MLModelType.AGENT_SELECTION, context))
```

## Graceful Degradation Features

### 1. Numpy Fallback
If numpy is not available, the system automatically uses built-in Python math:

```python
# Fallback implementations
class np:
    @staticmethod
    def mean(data):
        if not data or len(data) == 0:
            return 0.0
        return sum(data) / len(data)
    
    @staticmethod  
    def std(data):
        if not data or len(data) == 0:
            return 0.0
        if len(data) == 1:
            return 0.0
        mean_val = np.mean(data)
        variance = sum((x - mean_val) ** 2 for x in data) / len(data)
        return variance ** 0.5
```

### 2. Structlog Fallback
If structlog is not available, falls back to standard Python logging:

```python
import logging

class structlog:
    @staticmethod
    def get_logger(name):
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        # Configure handler...
        return logger
```

### 3. MCP Integration Layer Fallback
If the MCP integration layer is not available, provides minimal fallback:

```python
class MCPIntegrationLayer:
    def __init__(self):
        self.workflow_id = f"fallback-{int(time.time())}"
        # Minimal implementation...
```

## Usage Examples

### Basic ML Decision Making
```python
import asyncio
from ml_enhanced_orchestrator import MLDecisionEngine, MLModelType

async def example_agent_selection():
    engine = MLDecisionEngine()
    
    context = {
        'task_type': 'security_validation',
        'complexity': 0.8,
        'available_agents': [
            {
                'id': 'security-validator',
                'capabilities': ['security_validation', 'penetration_testing'],
                'specializations': ['jwt_security', 'authentication_flows']
            }
        ]
    }
    
    decision = await engine.make_decision(MLModelType.AGENT_SELECTION, context)
    print(f"Recommended action: {decision.recommended_action}")
    print(f"Confidence: {decision.confidence_scores}")

asyncio.run(example_agent_selection())
```

### Risk Assessment
```python
async def example_risk_assessment():
    engine = MLDecisionEngine()
    
    context = {
        'operation_type': 'deployment',
        'system_state': {
            'health_metrics': {
                'cpu_usage': 45,
                'memory_usage': 60,
                'error_rate': 0.02
            }
        },
        'recent_failures': []
    }
    
    decision = await engine.make_decision(MLModelType.RISK_ASSESSMENT, context)
    print(f"Risk level: {decision.risk_assessment}")
    print(f"Mitigation: {decision.recommended_action}")

asyncio.run(example_risk_assessment())
```

### Parallel Agent Coordination
```python
async def example_parallel_coordination():
    orchestrator = MLEnhancedOrchestrator()
    
    agent_requests = [
        {'id': 'backend-gateway-expert', 'context': {...}},
        {'id': 'security-validator', 'context': {...}},
        {'id': 'user-experience-auditor', 'context': {...}}
    ]
    
    results = await orchestrator.execute_parallel_agents(agent_requests)
    print(f"Execution results: {results}")

asyncio.run(example_parallel_coordination())
```

## ML Decision Types

The system supports several ML-enhanced decision types:

1. **AGENT_SELECTION** - Choose optimal agents for tasks
2. **PARALLEL_COORDINATION** - Coordinate parallel agent execution
3. **VALIDATION_STRATEGY** - Determine validation approach
4. **RISK_ASSESSMENT** - Assess operation risks
5. **CONTAINER_CONFLICT** - Detect container operation conflicts
6. **STREAM_PRIORITIZATION** - Prioritize execution streams

## Architecture

### Core Components

1. **MLDecisionEngine** - ML-powered decision making
2. **MLEnhancedOrchestrator** - Main orchestration controller
3. **MCPIntegrationLayer** - MCP service integration
4. **WorkflowPhase** - 10-phase orchestration workflow

### Workflow Phases

0. **Todo Context Integration** - Load persistent todos
1. **Agent Ecosystem Validation** - Validate agent availability
2. **Strategic Intelligence Planning** - Create implementation strategy
3. **Multi-Domain Research Discovery** - Comprehensive analysis
4. **Context Synthesis & Compression** - Create context packages
5. **Parallel Implementation Execution** - Execute specialists
6. **Comprehensive Evidence-Based Validation** - Validate with evidence
7. **Decision & Iteration Control** - Determine success/iteration
8. **Atomic Version Control Synchronization** - Create commits
9. **Meta-Orchestration Audit & Learning** - Analyze workflow
10. **Continuous Todo Integration & Loop Control** - Check continuation

## Error Handling

The system includes comprehensive error handling:

- **Import-time fallbacks** for missing dependencies
- **Runtime graceful degradation** for component failures
- **Detailed error reporting** with actionable messages
- **Validation checks** before execution
- **Recovery mechanisms** for common failure scenarios

## Performance Considerations

### With Full Dependencies
- Uses optimized numpy for mathematical operations
- Enhanced logging with structlog
- Full MCP integration capabilities

### With Fallbacks
- Pure Python math implementations (slightly slower)
- Standard logging (less features but functional)
- Minimal MCP integration (basic functionality)

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   python3 dependency_validator.py
   ```

2. **Missing Numpy**
   ```bash
   pip install numpy  # Optional - system has fallback
   ```

3. **Missing Structlog**
   ```bash
   pip install structlog  # Optional - system has fallback
   ```

4. **Module Path Issues**
   ```python
   import sys
   sys.path.append('.claude/orchestration_enhanced')
   ```

### Validation Commands

```bash
# Full validation
python3 dependency_validator.py

# Test specific functionality
python3 -c "from ml_enhanced_orchestrator import MLDecisionEngine; print('Success!')"

# Test with fallbacks
python3 -c "
import sys
sys.modules['numpy'] = None  # Force fallback
from ml_enhanced_orchestrator import MLDecisionEngine
print('Fallback working!')
"
```

## Development Notes

The system is designed for maximum compatibility and robustness:

- **No hard dependencies** on external libraries
- **Graceful degradation** maintains functionality
- **Comprehensive testing** ensures reliability
- **Clear error messages** aid troubleshooting
- **Modular design** allows component replacement

## License

This component is part of the AI Workflow Engine project.