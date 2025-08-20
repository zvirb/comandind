# AI Workflow Engine: Ollama & LLM Integration Architecture

**Last Updated: August 2, 2025**

This document provides a comprehensive overview of the AI Workflow Engine's Ollama integration, LangGraph workflows, and LLM-powered service architecture. It serves as the definitive guide for understanding AI capabilities, performance optimization, and development patterns.

## 1. Core AI Architecture Overview

### 1.1 AI Service Integration Pattern

The AI Workflow Engine follows a **distributed AI processing architecture** where the `worker` service handles all AI-intensive operations while the `api` service orchestrates user interactions and streaming responses.

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   WebUI     │ -> │    API      │ -> │   Worker    │ -> │   Ollama    │
│ (Frontend)  │    │ (FastAPI)   │    │ (Celery)    │    │ (LLM Host)  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       ^                   ^                   |               |
       |                   |                   v               v
       |                   |            ┌─────────────┐ ┌─────────────┐
       |                   |            │   Qdrant    │ │    GPU      │
       +-------------------+            │ (Vector DB) │ │ Resources   │
              Streaming                  └─────────────┘ └─────────────┘
```

### 1.2 Key Components

- **Ollama Service**: Local LLM hosting with GPU acceleration
- **LangGraph Workflows**: Self-correcting AI agent orchestration
- **Qdrant Vector Database**: Semantic memory and RAG capabilities
- **Model Lifecycle Manager**: GPU resource optimization
- **Expert Group Systems**: Multi-agent collaboration frameworks

## 2. Ollama Service Integration

### 2.1 Core Service Architecture

The `OllamaService` class (`app/worker/services/ollama_service.py`) provides the foundation for all LLM interactions:

```python
class OllamaService:
    """Service class for interacting with Ollama LLM API."""
    
    async def invoke_llm(self, prompt: str, model_name: str = None) -> str
    async def invoke_llm_with_tokens(self, messages: List[Dict], model_name: str) -> Tuple[str, TokenMetrics]
    async def invoke_llm_stream(self, messages: List[Dict], model_name: str) -> AsyncGenerator[str, None]
    async def generate_embeddings(self, texts: List[str], model_name: str) -> List[List[float]]
```

### 2.2 Model Communication Patterns

#### HTTP Client Configuration
- **Timeout**: 3600 seconds (1 hour) for long-running workflows
- **Connection Pooling**: AsyncClient with automatic connection management
- **Error Handling**: Exponential backoff with self-correction

#### API Endpoints Used
- `/api/chat`: Conversational interactions with context
- `/api/embeddings`: Vector generation for semantic search
- `/api/generate`: Direct text completion (legacy)

### 2.3 Context Injection

All LLM calls automatically inject current date/time context:

```python
def _inject_datetime_context(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    current_time = now_utc.strftime("%A, %B %d, %Y at %I:%M %p UTC")
    datetime_context = {
        "role": "system", 
        "content": f"Current date and time: {current_time}. Use this information when responding to time-sensitive questions."
    }
```

## 3. LangGraph Workflow Implementations

### 3.1 Expert Group LangGraph Service

**File**: `app/worker/services/expert_group_langgraph_service.py`

#### Workflow Architecture
```python
workflow = StateGraph(Dict[str, Any])  # Uses dict for LangGraph compatibility

# Workflow Nodes:
1. pm_questioning_node    -> Generate expert questions
2. collect_expert_input   -> Gather specialized input with tools
3. pm_planning_node       -> Create structured todo list
4. execute_tasks_node     -> Parallel task execution
5. final_summary_node     -> Comprehensive result synthesis
```

#### State Management Pattern (CRITICAL)
```python
# CORRECT: Pydantic for validation, dict for LangGraph
initial_state = ExpertGroupState(...)
state_dict = initial_state.dict()
final_state = await workflow.ainvoke(state_dict, config)

# Handle Pydantic conversion on return
if hasattr(final_state, 'dict'):
    final_state = final_state.dict()
```

#### Self-Correction Mechanisms
- **Hierarchical Fallback**: 3-tier error recovery system
- **Retry Logic**: Exponential backoff with max 3 attempts
- **State Validation**: Comprehensive output validation
- **Emergency Fallback**: Minimal response when all methods fail

### 3.2 Smart Router LangGraph Service

**File**: `app/worker/services/smart_router_langgraph_service.py`

#### Workflow Phases
```python
1. analyze_request        -> Complexity analysis and routing decision
2. create_todo_plan      -> Structured task breakdown
3. execute_tasks         -> Sequential task execution
4. generate_final_response -> Result synthesis
```

#### Routing Decision Logic
- **DIRECT**: Simple, straightforward responses (factual questions)
- **PLANNING**: Complex tasks requiring structured breakdown

#### Task Categorization
```python
class TaskCategory(str, Enum):
    RESEARCH = "Research"
    ANALYSIS = "Analysis" 
    PLANNING = "Planning"
    CREATION = "Creation"
    PROBLEM_SOLVING = "Problem Solving"
    COMMUNICATION = "Communication"
    ORGANIZATION = "Organization"
```

## 4. Model Management & Resource Optimization

### 4.1 Model Lifecycle Manager

**File**: `app/worker/services/model_lifecycle_manager.py`

#### Key Features
- **Preloading Strategy**: Common models kept in memory
- **Automatic Unloading**: LRU eviction after 10 minutes inactivity
- **GPU Memory Monitoring**: nvidia-smi integration
- **Background Cleanup**: 5-minute cleanup intervals

#### Preloaded Models
```python
preload_models = {
    "llama3.2:1b",    # Fast small model
    "llama3.2:3b",    # Medium model  
    "llama3.1:8b"     # Large model for complex tasks
}
```

### 4.2 Model Resource Manager

**File**: `app/worker/services/model_resource_manager.py`

#### Parameter-Based Categorization
```python
class ModelCategory(str, Enum):
    SMALL_1B = "1b"        # ~1 billion parameters
    MEDIUM_4B = "4b"       # ~4 billion parameters
    LARGE_8B = "8b"        # ~8 billion parameters 
    XLARGE_10B = "10b+"    # 10+ billion parameters
```

#### Parallel Execution Limits
```python
ParallelExecutionLimits:
    small_1b_limit: 5     # 5 concurrent 1B models
    medium_4b_limit: 4    # 4 concurrent 4B models
    large_8b_limit: 3     # 3 concurrent 8B models
    xlarge_10b_limit: 1   # 1 concurrent 10B+ model
```

#### GPU Resource Management
- **Memory Estimation**: Parameter count to memory mapping
- **Execution Slots**: Category-based concurrent limits
- **Queue Management**: Pending request processing
- **Resource Monitoring**: Real-time GPU utilization tracking

## 5. Vector Database Integration (Qdrant)

### 5.1 QdrantService Architecture

**File**: `app/worker/services/qdrant_service.py`

#### Core Capabilities
```python
class QdrantService:
    async def store_chat_message(self, message_id: str, content: str, user_id: int, 
                                 session_id: str, message_type: str, message_order: int)
    async def search_points(self, query_text: str, limit: int = 5, user_id: int = None)
    async def upsert_points(self, points: List[models.PointStruct])
    async def search(self, vector: List[float], user_id: int, limit: int = 5)
```

#### Embedding Generation
- **Model**: `mxbai-embed-large` (default)
- **Concurrency**: Async batch processing
- **Timeout**: 3600 seconds for large batches
- **Error Handling**: Partial success with fallback

### 5.2 RAG Implementation Patterns

#### Chat Message Storage
```python
payload = {
    "message_id": message_id,
    "user_id": user_id, 
    "session_id": session_id,
    "text": content,
    "message_type": message_type,
    "source": "chat_message",
    "conversation_domain": domain,
    "tool_used": tool_name,
    "content_type": "chat"
}
```

#### Semantic Search Features
- **User Isolation**: Per-user vector spaces
- **Session Filtering**: Conversation-specific search
- **Content Type Filtering**: Document vs chat vs system
- **Temporal Relevance**: Timestamp-based ranking

## 6. Multi-Agent & Expert Systems

### 6.1 Expert Role Definitions

```python
class AgentRole(str, Enum):
    PROJECT_MANAGER = "Project Manager"
    TECHNICAL_EXPERT = "Technical Expert" 
    BUSINESS_ANALYST = "Business Analyst"
    CREATIVE_DIRECTOR = "Creative Director"
    RESEARCH_SPECIALIST = "Research Specialist"  # Uses Tavily API
    PLANNING_EXPERT = "Planning Expert"
    SOCRATIC_EXPERT = "Socratic Expert"
    WELLBEING_COACH = "Wellbeing Coach"
    PERSONAL_ASSISTANT = "Personal Assistant"    # Uses Google Calendar
    DATA_ANALYST = "Data Analyst"
    OUTPUT_FORMATTER = "Output Formatter"
    QUALITY_ASSURANCE = "Quality Assurance"
```

### 6.2 Tool Integration Patterns

#### Real Tool Usage
- **Research Specialist**: Tavily web search API
- **Personal Assistant**: Google Calendar integration
- **Technical Expert**: Code analysis and validation
- **Business Analyst**: Data processing and metrics

#### Tool Call Transparency
```python
tool_calls_made = [
    {
        "tool_name": "tavily_search",
        "parameters": {"query": "latest AI research"},
        "result": "Found 15 recent papers...",
        "timestamp": "2025-08-02T10:30:00Z"
    }
]
```

## 7. Performance Optimization Strategies

### 7.1 Batched Processing

#### Expert Input Collection
Instead of individual LLM calls per expert, the system uses batched prompts:

```python
batched_prompt = f"""
Multi-expert consultation for: {user_request}

Provide responses from each expert perspective:
## Technical Expert
Question: {technical_question}
[Response expected]

## Business Analyst  
Question: {business_question}
[Response expected]

Format: **Expert Name:** [Response]
"""
```

#### Task Execution Optimization
Tasks assigned to the same expert are batched into single LLM calls:

```python
batched_task_prompt = f"""
As the {expert_name}, you have been assigned {len(expert_tasks)} tasks:

**Task 1:** {task_1_description}
**Task 2:** {task_2_description}

For each task, provide:
**TASK [NUMBER] COMPLETION:** [detailed work]
**TASK [NUMBER] TOOLS USED:** [methods used]
**TASK [NUMBER] ACTIONS PERFORMED:** [specific actions]
"""
```

### 7.2 Model Selection Strategy

#### Performance Tiers
```python
# Fast models for simple operations
FAST_MODELS = ["llama3.2:1b", "llama3.2:3b"]

# Standard models for complex reasoning  
STANDARD_MODELS = ["llama3.1:8b-instruct", "llama3.2:8b"]

# Large models for complex multi-step workflows
LARGE_MODELS = ["llama3.1:70b", "llama3.2:90b"]
```

#### Dynamic Model Selection
```python
def select_optimal_model(complexity: str, operation_type: str) -> str:
    if operation_type in ["questioning", "simple_response"]:
        return FAST_MODELS[0]
    elif complexity == "complex" or operation_type == "planning":
        return LARGE_MODELS[0] if available else STANDARD_MODELS[0]
    else:
        return STANDARD_MODELS[0]
```

### 7.3 Caching & Memory Management

#### Model Caching
- **Preloaded Models**: Core models kept in GPU memory
- **LRU Eviction**: Automatic unloading of unused models
- **Memory Thresholds**: 80% GPU usage triggers aggressive cleanup

#### Response Caching
- **Session Context**: Previous responses cached for context
- **Embedding Cache**: Vector embeddings cached for reuse
- **Template Cache**: Common prompt templates pre-compiled

## 8. Streaming & Real-Time Features

### 8.1 Streaming Response Pattern

#### Server-Sent Events (SSE)
```python
async def streaming_workflow_wrapper(
    workflow_func: Callable,
    user_request: str,
    selected_agents: List[str]
) -> AsyncGenerator[Dict[str, Any], None]:
    
    yield {"type": "workflow_start", "content": "Initializing..."}
    
    # Stream intermediate results
    for entry in result.get("discussion_context", []):
        yield {
            "type": "expert_response",
            "expert": entry["expert"],
            "content": entry["response"],
            "phase": entry["phase"]
        }
        await asyncio.sleep(0.1)  # Prevent client overwhelm
    
    yield {"type": "workflow_complete", "content": final_result}
```

#### Chat Mode Integration
**File**: `app/api/routers/chat_modes_router.py`

```python
# Chat modes available:
1. Simple Chat      -> Direct LLM interaction
2. Expert Group     -> Multi-expert LangGraph workflow
3. Smart Router     -> Intelligent task routing
4. Socratic Interview -> Assessment-focused interaction
```

### 8.2 Progress Tracking

#### Workflow Metrics
```python
class WorkflowMetrics:
    def __init__(self):
        self.start_time = None
        self.phase_times = {}
        self.token_usage = {}
        self.error_count = 0
        self.retry_count = 0
    
    def get_summary(self) -> Dict[str, Any]:
        return {
            "total_execution_time": total_time,
            "phase_breakdown": self.phase_times,
            "total_tokens": sum(self.token_usage.values()),
            "error_count": self.error_count,
            "success_rate": 1 - (self.error_count / max(1, len(self.phase_times)))
        }
```

## 9. Error Handling & Reliability

### 9.1 Hierarchical Fallback System

#### Level 1: Retry Current Operation
```python
async def robust_ollama_call(self, prompt: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            response, tokens = await invoke_llm_with_tokens(messages, model_name)
            return response, True
        except Exception as e:
            if attempt == max_retries - 1:
                return f"Failed after {max_retries} attempts: {str(e)}", False
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

#### Level 2: Simplified Workflow
```python
async def simplified_workflow(self, request: str, partial_state: Dict):
    simple_prompt = f"""
    Provide a comprehensive response to: {request}
    
    Structure your response with:
    1. Analysis of the request
    2. Key recommendations  
    3. Action steps
    4. Resources needed
    """
    response, _ = await robust_ollama_call(simple_prompt)
    return {"response": response, "workflow_type": "simplified_fallback"}
```

#### Level 3: Emergency Fallback
```python
async def emergency_fallback(self, user_request: str) -> Dict[str, Any]:
    return {
        "response": f"I understand you need help with: {user_request}...",
        "workflow_type": "emergency_fallback",
        "is_coordinated": False
    }
```

### 9.2 Timeout Management

#### Configuration (from AIASSIST.md)
- **Standard Timeout**: 300 seconds (5 minutes) for AI operations
- **Long Workflow Timeout**: 3600 seconds (1 hour) for multi-agent
- **Streaming Timeout**: No timeout (client-handled)

#### Timeout Handling
```python
try:
    final_state = await asyncio.wait_for(
        self.workflow_graph.ainvoke(state_dict, config),
        timeout=3600.0  # 1 hour timeout
    )
except asyncio.TimeoutError:
    return await self._timeout_fallback(user_request, selected_agents)
```

## 10. Development Guidelines & Best Practices

### 10.1 LangGraph Development Patterns

#### State Management Rules
```python
# ✅ CORRECT: Use dict for LangGraph state
workflow = StateGraph(Dict[str, Any])

# ❌ INCORRECT: Pydantic models cause serialization issues
workflow = StateGraph(MyPydanticModel)

# ✅ CORRECT: Pydantic for validation, dict for workflow
initial_state = MyStateModel(...)
final_state = await workflow.ainvoke(initial_state.dict(), config)
```

#### Node Function Pattern
```python
async def workflow_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Always return dict, never Pydantic model instances."""
    try:
        # Main processing logic
        result = await process_node_logic(state)
        return result  # Must be dict
    except Exception as e:
        logger.error(f"Node execution failed: {e}")
        return await emergency_fallback(state)
```

### 10.2 Error Boundary Implementation

```python
async def workflow_node_with_boundaries(state: Dict[str, Any]) -> Dict[str, Any]:
    try:
        result = await process_logic(state)
        return result
    except SpecificExpectedException as e:
        logger.info(f"Handling expected error: {e}")
        return await handle_expected_error(state, e)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return await emergency_fallback(state)
```

### 10.3 Performance Testing Framework

```python
async def test_workflow_robustness(
    workflow_func: Callable,
    test_cases: List[Dict[str, Any]]
) -> Dict[str, Any]:
    
    results = {"passed": 0, "failed": 0, "errors": []}
    
    for test_case in test_cases:
        try:
            result = await workflow_func(test_case["input"])
            
            # Validate result structure
            required_keys = ["response", "discussion_context", "completed_tasks"]
            if all(key in result for key in required_keys):
                results["passed"] += 1
            else:
                results["failed"] += 1
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"Test failed: {str(e)}")
    
    return results
```

## 11. Monitoring & Observability

### 11.1 Metrics Collection

#### Token Usage Tracking
```python
class TokenMetrics:
    def add_tokens(self, input_tokens: int, output_tokens: int, category: str):
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.by_category[category] = self.by_category.get(category, 0) + input_tokens + output_tokens
```

#### GPU Resource Monitoring
```python
async def _get_gpu_memory_info(self) -> Optional[Dict[str, float]]:
    result = subprocess.run([
        'nvidia-smi', '--query-gpu=memory.used,memory.total,memory.free',
        '--format=csv,noheader,nounits'
    ], capture_output=True, text=True, timeout=5)
    
    if result.returncode == 0:
        memory_used, memory_total, memory_free = result.stdout.strip().split('\n')[0].split(', ')
        return {
            'memory_used': float(memory_used),
            'memory_total': float(memory_total), 
            'memory_free': float(memory_free)
        }
```

### 11.2 Performance Metrics

#### Workflow Performance
- **Execution Time**: Per-phase timing breakdown
- **Token Consumption**: Input/output token tracking by category
- **Error Rates**: Success/failure ratios with error categorization
- **Resource Utilization**: GPU memory and model loading metrics

#### Model Performance
- **Loading Times**: Model initialization duration
- **Inference Speed**: Tokens per second generation
- **Memory Efficiency**: GPU memory usage per model
- **Concurrent Capacity**: Parallel execution limits

## 12. Deployment & Production Considerations

### 12.1 Resource Requirements

#### Minimum System Requirements
- **GPU Memory**: 16GB VRAM for standard operation
- **System RAM**: 32GB for concurrent model loading
- **Storage**: 500GB SSD for model storage
- **Network**: Stable connection for external tool APIs

#### Recommended Configuration
- **GPU**: NVIDIA RTX 4090 or A100 (24GB+ VRAM)
- **CPU**: 16+ cores for concurrent processing
- **RAM**: 64GB for optimal performance
- **Storage**: 1TB NVMe SSD

### 12.2 Production Monitoring

#### Health Checks
```python
async def get_ai_system_health() -> Dict[str, Any]:
    return {
        "ollama_status": await check_ollama_connection(),
        "gpu_memory": await get_gpu_memory_info(),
        "loaded_models": len(model_lifecycle_manager.loaded_models),
        "qdrant_status": await qdrant_service.list_collections(),
        "workflow_metrics": workflow_metrics.get_summary()
    }
```

#### Performance Alerts
- **GPU Memory > 90%**: Trigger model cleanup
- **Workflow Timeout > 80%**: Scale resources or optimize
- **Error Rate > 5%**: Investigate fallback patterns
- **Token Usage Spikes**: Monitor cost implications

### 12.3 Scaling Strategies

#### Horizontal Scaling
- **Multiple Worker Instances**: Distribute AI workload
- **Load Balancing**: Round-robin or capability-based routing
- **Model Sharding**: Different workers host different models

#### Vertical Scaling  
- **Multi-GPU Support**: Model distribution across GPUs
- **Memory Optimization**: Advanced caching strategies
- **Batch Size Tuning**: Optimize throughput vs latency

## 13. Security & Privacy

### 13.1 Data Protection

#### Vector Database Security
- **User Isolation**: Strict per-user vector spaces
- **Data Encryption**: TLS for all Qdrant communications
- **Access Control**: API key and certificate-based auth

#### LLM Interaction Security
- **Local Processing**: All LLM inference stays on-premises
- **Input Sanitization**: Prompt injection prevention
- **Output Filtering**: Sensitive data detection and removal

### 13.2 Privacy-First Architecture

#### No External Dependencies
- **Local Ollama**: No data sent to external LLM providers
- **On-Premises Qdrant**: Vector storage remains local
- **Optional External Tools**: Tavily/Google APIs only when explicitly used

#### Data Retention Policies
- **Chat History**: User-controlled retention periods
- **Vector Embeddings**: Automatic cleanup of old embeddings
- **Model Caches**: Temporary storage with automatic expiration

---

This documentation provides a comprehensive foundation for understanding and developing with the AI Workflow Engine's Ollama and LLM integration capabilities. All patterns have been validated in production environments and provide robust error handling, performance optimization, and monitoring capabilities.

For specific implementation details, refer to the source files mentioned throughout this document. For troubleshooting and advanced configuration, consult the AIASSIST.md file for additional context.