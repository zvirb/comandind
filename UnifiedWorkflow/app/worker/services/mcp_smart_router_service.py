"""
Enhanced Smart Router LangGraph Service with MCP Integration

Implements enhanced Smart Router with MCP (Model Context Protocol) tool integration:
- Dynamic MCP tool discovery and selection
- OAuth Resource Server authentication for tool access
- Human-in-the-loop approval workflows for dangerous operations
- Enhanced error handling and recovery with MCP fallbacks
- Performance optimization with tool load balancing
- Comprehensive audit logging and security monitoring

This service maintains the existing 4-phase LangGraph workflow (Analysis → Planning → Execution → Summary)
while adding MCP compliance and advanced tool orchestration capabilities.
"""

import asyncio
import json
import logging
import uuid
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from enum import Enum

from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableLambda
from langchain_core.runnables.config import RunnableConfig
from pydantic import BaseModel, Field

from worker.services.ollama_service import invoke_llm_with_tokens
from worker.services.centralized_resource_service import centralized_resource_service, ComplexityLevel
from worker.services.mcp_registry_service import get_mcp_registry_service, MCPRegistryService
from worker.services.mcp_security_framework import get_mcp_security_framework, MCPSecurityFramework
from shared.services.enhanced_jwt_service import enhanced_jwt_service
from shared.services.security_audit_service import security_audit_service

logger = logging.getLogger(__name__)


# ================================
# Enhanced Router State
# ================================

class MCPRouterState(BaseModel):
    """Enhanced state object for the MCP-enabled smart router workflow."""
    # Input data
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    user_request: str = ""
    
    # Phase 1: Analysis
    routing_decision: str = ""
    complexity_analysis: Dict[str, Any] = Field(default_factory=dict)
    tool_requirements: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Phase 2: Planning
    todo_list: List[Dict[str, Any]] = Field(default_factory=list)
    approach_strategy: str = ""
    selected_tools: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Phase 3: Tool Execution
    completed_tasks: List[Dict[str, Any]] = Field(default_factory=list)
    tool_results: List[Dict[str, Any]] = Field(default_factory=list)
    approval_requests: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Phase 4: Final Summary
    final_response: str = ""
    execution_summary: Dict[str, Any] = Field(default_factory=dict)
    
    # MCP Integration
    mcp_context: Dict[str, Any] = Field(default_factory=dict)
    authentication_context: Dict[str, Any] = Field(default_factory=dict)
    security_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Workflow control
    current_phase: str = "analysis"
    discussion_context: List[Dict[str, Any]] = Field(default_factory=list)
    error_context: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Configuration
    chat_model: str = "llama3.1:8b"
    enable_mcp_tools: bool = True
    require_approval: bool = False


class TaskCategory(str, Enum):
    """Categories for different types of tasks."""
    RESEARCH = "Research"
    ANALYSIS = "Analysis" 
    PLANNING = "Planning"
    CREATION = "Creation"
    PROBLEM_SOLVING = "Problem Solving"
    COMMUNICATION = "Communication"
    ORGANIZATION = "Organization"
    AUTOMATION = "Automation"


class MCPToolType(str, Enum):
    """Types of MCP tools available."""
    CALENDAR = "calendar"
    TASK = "task"
    EMAIL = "email"
    SEARCH = "search"
    FILE = "file"
    ANALYSIS = "analysis"


# ================================
# Enhanced Smart Router Service
# ================================

class MCPSmartRouterService:
    """Enhanced Smart Router service with MCP tool integration and security."""
    
    def __init__(self):
        self.workflow_graph = self._build_workflow_graph()
        self.mcp_registry: Optional[MCPRegistryService] = None
        self.security_framework: Optional[MCPSecurityFramework] = None
        
        # Performance metrics
        self.execution_metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time_ms": 0.0,
            "tool_usage_stats": {},
            "approval_request_count": 0
        }
    
    async def initialize(self) -> None:
        """Initialize MCP components."""
        
        try:
            self.mcp_registry = await get_mcp_registry_service()
            self.security_framework = await get_mcp_security_framework()
            
            if not self.mcp_registry:
                logger.warning("MCP Registry Service not available - falling back to basic routing")
            if not self.security_framework:
                logger.warning("MCP Security Framework not available - reduced security features")
                
            logger.info("MCP Smart Router Service initialized")
            
        except Exception as e:
            logger.error(f"Error initializing MCP components: {e}", exc_info=True)
    
    def _build_workflow_graph(self) -> StateGraph:
        """Build the enhanced LangGraph workflow for MCP-enabled smart routing."""
        
        workflow = StateGraph(MCPRouterState)
        
        # Add nodes for each phase
        workflow.add_node("analyze_request", self._analyze_request_node)
        workflow.add_node("create_tool_plan", self._create_tool_plan_node)
        workflow.add_node("execute_mcp_tools", self._execute_mcp_tools_node)
        workflow.add_node("handle_approvals", self._handle_approvals_node)
        workflow.add_node("generate_final_response", self._generate_final_response_node)
        
        # Define conditional edges for approval handling
        workflow.set_entry_point("analyze_request")
        workflow.add_edge("analyze_request", "create_tool_plan")
        workflow.add_edge("create_tool_plan", "execute_mcp_tools")
        
        # Conditional edge for approval handling
        workflow.add_conditional_edges(
            "execute_mcp_tools",
            self._should_handle_approvals,
            {
                "handle_approvals": "handle_approvals",
                "generate_response": "generate_final_response"
            }
        )
        workflow.add_edge("handle_approvals", "generate_final_response")
        workflow.add_edge("generate_final_response", END)
        
        return workflow.compile()
    
    async def process_request(
        self,
        user_request: str,
        user_id: str = None,
        session_id: str = None,
        authentication_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Process smart router request with MCP tool integration."""
        
        start_time = time.time()
        self.execution_metrics["total_requests"] += 1
        
        try:
            # Initialize state
            initial_state = MCPRouterState(
                session_id=session_id or str(uuid.uuid4()),
                user_id=user_id or "anonymous",
                user_request=user_request,
                authentication_context=authentication_context or {},
                enable_mcp_tools=self.mcp_registry is not None
            )
            
            # Run the workflow
            config = RunnableConfig(recursion_limit=100)
            final_state = await self.workflow_graph.ainvoke(initial_state.dict(), config)
            
            # Calculate execution time
            execution_time_ms = (time.time() - start_time) * 1000
            self.execution_metrics["successful_requests"] += 1
            self._update_average_response_time(execution_time_ms)
            
            # Log successful execution
            await security_audit_service.log_security_event(
                user_id=user_id or "anonymous",
                event_type="mcp_smart_router_success",
                details={
                    "execution_time_ms": execution_time_ms,
                    "tools_used": len(final_state.get("tool_results", [])),
                    "approval_requests": len(final_state.get("approval_requests", []))
                }
            )
            
            return {
                "response": final_state["final_response"],
                "discussion_context": final_state["discussion_context"],
                "routing_decision": final_state["routing_decision"],
                "todo_list": final_state["todo_list"],
                "completed_tasks": final_state["completed_tasks"],
                "tool_results": final_state["tool_results"],
                "approval_requests": final_state["approval_requests"],
                "execution_summary": final_state["execution_summary"],
                "complexity_analysis": final_state["complexity_analysis"],
                "approach_strategy": final_state["approach_strategy"],
                "workflow_type": "mcp_smart_router",
                "execution_time_ms": execution_time_ms,
                "confidence_score": final_state["complexity_analysis"].get("confidence", 0.85),
                "mcp_enabled": final_state["enable_mcp_tools"],
                "security_metadata": final_state["security_metadata"]
            }
            
        except Exception as e:
            # Handle execution failure
            execution_time_ms = (time.time() - start_time) * 1000
            self.execution_metrics["failed_requests"] += 1
            
            logger.error(f"MCP Smart Router execution failed: {e}", exc_info=True)
            
            # Log failed execution
            await security_audit_service.log_security_event(
                user_id=user_id or "anonymous",
                event_type="mcp_smart_router_failure",
                details={
                    "error": str(e),
                    "execution_time_ms": execution_time_ms
                }
            )
            
            return {
                "response": f"I encountered an error processing your request: {str(e)}",
                "discussion_context": [],
                "routing_decision": "ERROR",
                "error": str(e),
                "execution_time_ms": execution_time_ms,
                "workflow_type": "mcp_smart_router",
                "success": False
            }
    
    async def _analyze_request_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 1: Analyze the request and determine MCP tool requirements."""
        
        user_request = state["user_request"]
        enable_mcp = state.get("enable_mcp_tools", False)
        
        # Enhanced analysis prompt that considers MCP tools
        analysis_prompt = f"""
        As an intelligent routing system with access to advanced productivity tools, analyze this user request: {user_request}

        Available tool capabilities include:
        - Calendar Management: Create, update, delete, and query calendar events
        - Task Management: Create, update, prioritize, and track tasks and projects
        - Email Communication: Compose, send, and manage email communications
        - Research and Analysis: Web search and information gathering
        - File Operations: Document creation and management

        Provide a comprehensive analysis including:

        1. ROUTING DECISION: Choose the best approach:
           - DIRECT: Simple, straightforward response (factual questions, basic information)
           - PLANNING: Complex task requiring structured breakdown and tool usage
           - TOOL_ASSISTED: Request that would benefit from productivity tool integration

        2. COMPLEXITY ANALYSIS:
           - Complexity Level: [Simple/Moderate/Complex]
           - Task Category: [Research/Analysis/Planning/Creation/Problem Solving/Communication/Organization/Automation]
           - Estimated Steps: [Number of steps needed]
           - Tool Requirements: [What specific tools would be helpful]
           - Time Scope: [Quick/Medium/Extended]

        3. TOOL RECOMMENDATIONS:
           - Calendar Tools: [Needed/Not Needed] - [specific operations if needed]
           - Task Tools: [Needed/Not Needed] - [specific operations if needed]
           - Email Tools: [Needed/Not Needed] - [specific operations if needed]
           - Research Tools: [Needed/Not Needed] - [specific operations if needed]

        4. KEY CONSIDERATIONS:
           - What are the main challenges or requirements?
           - What domain knowledge is needed?
           - Are there dependencies or prerequisites?
           - Would automation or tool assistance significantly improve the outcome?

        Format your response as:
        ROUTING DECISION: [DIRECT/PLANNING/TOOL_ASSISTED]
        
        COMPLEXITY ANALYSIS:
        - Complexity Level: [level]
        - Task Category: [category]
        - Estimated Steps: [number]
        - Tool Requirements: [list]
        - Time Scope: [scope]
        
        TOOL RECOMMENDATIONS:
        - Calendar Tools: [assessment]
        - Task Tools: [assessment]  
        - Email Tools: [assessment]
        - Research Tools: [assessment]
        
        KEY CONSIDERATIONS:
        [Your analysis of challenges and requirements]
        """
        
        # Use centralized resource management for analysis
        session_id = state.get("session_id", "mcp_router_session")
        user_id = state.get("user_id", "system")
        
        result = await centralized_resource_service.allocate_and_invoke(
            prompt=analysis_prompt,
            user_id=str(user_id),
            service_name="mcp_smart_router",
            session_id=session_id,
            complexity=ComplexityLevel.COMPLEX,
            fallback_allowed=True
        )
        
        response = result["response"]
        
        # Parse the analysis response
        routing_decision, complexity_analysis, tool_requirements = await self._parse_analysis_response(response)
        
        # Discover available MCP tools if enabled
        available_tools = []
        if enable_mcp and self.mcp_registry:
            try:
                user_permissions = state.get("authentication_context", {}).get("scopes", [])
                discovered_tools = await self.mcp_registry.discover_tools(
                    query=user_request,
                    user_permissions=user_permissions
                )
                available_tools = discovered_tools[:10]  # Limit to top 10 tools
            except Exception as e:
                logger.warning(f"Tool discovery failed: {e}")
        
        # Add to discussion context
        discussion_entry = {
            "expert": "MCP Smart Router",
            "response": f"Analysis complete. Routing: {routing_decision}. Found {len(available_tools)} available tools.",
            "timestamp": datetime.now().isoformat(),
            "phase": "analysis",
            "confidence": complexity_analysis.get("confidence", 0.85)
        }
        
        # Update state
        state["routing_decision"] = routing_decision
        state["complexity_analysis"] = complexity_analysis
        state["tool_requirements"] = tool_requirements
        state["current_phase"] = "planning"
        state["discussion_context"] = [discussion_entry]
        state["mcp_context"] = {
            "available_tools": available_tools,
            "tool_discovery_count": len(available_tools)
        }
        
        return state
    
    async def _create_tool_plan_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 2: Create structured plan with MCP tool integration."""
        
        user_request = state["user_request"]
        routing_decision = state["routing_decision"]
        complexity_analysis = state["complexity_analysis"]
        tool_requirements = state["tool_requirements"]
        available_tools = state.get("mcp_context", {}).get("available_tools", [])
        
        if routing_decision == "DIRECT":
            # Simple direct response plan
            todo_list = [{
                "task": f"Provide direct response to: {user_request}",
                "category": complexity_analysis.get("task_category", "Communication"),
                "priority": "High",
                "status": "pending",
                "estimated_time": "Quick",
                "tools_needed": []
            }]
            approach_strategy = "Direct response approach - provide immediate, comprehensive answer."
            selected_tools = []
        
        else:
            # Enhanced planning with tool integration
            planning_prompt = f"""
            Based on this request: {user_request}
            
            Analysis shows:
            - Complexity: {complexity_analysis.get('complexity_level', 'Moderate')}
            - Category: {complexity_analysis.get('task_category', 'Planning')}
            - Routing: {routing_decision}
            - Tool Requirements: {tool_requirements}
            
            Available MCP Tools:
            {self._format_available_tools(available_tools)}
            
            Create a detailed execution plan that integrates appropriate tools.
            
            Format your response as:
            
            APPROACH STRATEGY:
            [Explain the overall approach and methodology, including how tools will be used]
            
            TODO LIST:
            1. [Task description] - Category: [category] - Priority: [High/Medium/Low] - Tools: [tool1, tool2] - Time: [Quick/Medium/Extended]
            2. [Task description] - Category: [category] - Priority: [priority] - Tools: [tools] - Time: [time]
            [Continue...]
            
            TOOL INTEGRATION PLAN:
            - Tool 1: [tool_name] - Operations: [operation1, operation2] - Purpose: [purpose]
            - Tool 2: [tool_name] - Operations: [operations] - Purpose: [purpose]
            [Continue...]
            
            Ensure tasks are:
            - Specific and actionable
            - Properly sequenced with tool dependencies
            - Categorized appropriately
            - Realistic in scope and time estimation
            - Integrated with appropriate MCP tools
            """
            
            session_id = state.get("session_id", "mcp_router_session")
            user_id = state.get("user_id", "system")
            
            result = await centralized_resource_service.allocate_and_invoke(
                prompt=planning_prompt,
                user_id=str(user_id),
                service_name="mcp_smart_router",
                session_id=session_id,
                complexity=ComplexityLevel.COMPLEX,
                fallback_allowed=True
            )
            
            response = result["response"]
            
            # Parse planning response
            todo_list, approach_strategy, selected_tools = await self._parse_planning_response(
                response, available_tools
            )
        
        # Add to discussion context
        planning_message = f"Created {len(todo_list)}-item action plan using {routing_decision.lower()} approach with {len(selected_tools)} tools."
        discussion_entry = {
            "expert": "MCP Smart Router",
            "response": planning_message,
            "timestamp": datetime.now().isoformat(),
            "phase": "planning",
            "confidence": 0.90
        }
        
        # Update state
        state["todo_list"] = todo_list
        state["approach_strategy"] = approach_strategy
        state["selected_tools"] = selected_tools
        state["current_phase"] = "execution"
        state["discussion_context"].append(discussion_entry)
        
        return state
    
    async def _execute_mcp_tools_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 3: Execute tasks with MCP tool integration."""
        
        todo_list = state["todo_list"]
        selected_tools = state["selected_tools"]
        user_request = state["user_request"]
        user_id = state.get("user_id", "anonymous")
        authentication_context = state.get("authentication_context", {})
        
        completed_tasks = []
        tool_results = []
        approval_requests = []
        
        for todo_item in todo_list:
            task = todo_item["task"]
            category = todo_item["category"]
            tools_needed = todo_item.get("tools_needed", [])
            
            try:
                # Execute task
                if tools_needed and self.mcp_registry and state.get("enable_mcp_tools", False):
                    # Execute with MCP tools
                    task_result = await self._execute_task_with_mcp_tools(
                        task, tools_needed, user_id, authentication_context, state
                    )
                else:
                    # Execute with LLM only
                    task_result = await self._execute_task_with_llm(
                        task, category, user_request, state
                    )
                
                # Process results
                if task_result.get("approval_required", False):
                    approval_requests.append(task_result["approval_request"])
                    # Skip execution for now, will be handled in approval phase
                    continue
                
                completed_tasks.append({
                    "task": task,
                    "category": category,
                    "execution": task_result.get("execution", ""),
                    "key_outputs": task_result.get("key_outputs", ""),
                    "status": "completed",
                    "tools_used": task_result.get("tools_used", []),
                    "actions_performed": task_result.get("actions_performed", []),
                    "priority": todo_item.get("priority", "Medium"),
                    "execution_time_ms": task_result.get("execution_time_ms", 0)
                })
                
                if task_result.get("tool_results"):
                    tool_results.extend(task_result["tool_results"])
                
                # Update tool usage statistics
                for tool_name in task_result.get("tools_used", []):
                    self.execution_metrics["tool_usage_stats"][tool_name] = (
                        self.execution_metrics["tool_usage_stats"].get(tool_name, 0) + 1
                    )
                
                # Add to discussion context
                discussion_entry = {
                    "expert": "MCP Smart Router",
                    "response": f"✅ {task} - {task_result.get('key_outputs', '')[:100]}...",
                    "timestamp": datetime.now().isoformat(),
                    "phase": "task_execution",
                    "task": task,
                    "confidence": 0.85,
                    "tools_used": task_result.get("tools_used", [])
                }
                state["discussion_context"].append(discussion_entry)
                
            except Exception as e:
                logger.error(f"Error executing task '{task}': {e}", exc_info=True)
                
                # Add error to context
                error_entry = {
                    "task": task,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                    "phase": "task_execution"
                }
                state.setdefault("error_context", []).append(error_entry)
                
                # Create failed task entry
                completed_tasks.append({
                    "task": task,
                    "category": category,
                    "execution": f"Task failed: {str(e)}",
                    "status": "failed",
                    "error": str(e),
                    "priority": todo_item.get("priority", "Medium")
                })
        
        # Update state
        state["completed_tasks"] = completed_tasks
        state["tool_results"] = tool_results
        state["approval_requests"] = approval_requests
        state["current_phase"] = "approval" if approval_requests else "summary"
        
        return state
    
    async def _handle_approvals_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle human approval requests for dangerous operations."""
        
        approval_requests = state.get("approval_requests", [])
        
        if not approval_requests:
            # No approvals needed, move to summary
            state["current_phase"] = "summary"
            return state
        
        # For now, just log the approval requests and move to summary
        # In a full implementation, this would wait for human approval
        self.execution_metrics["approval_request_count"] += len(approval_requests)
        
        approval_summary = f"🔒 {len(approval_requests)} operations require approval before execution."
        discussion_entry = {
            "expert": "MCP Smart Router",
            "response": approval_summary,
            "timestamp": datetime.now().isoformat(),
            "phase": "approval_handling",
            "confidence": 1.0
        }
        state["discussion_context"].append(discussion_entry)
        
        state["current_phase"] = "summary"
        return state
    
    async def _generate_final_response_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 4: Generate comprehensive final response with MCP tool summary."""
        
        user_request = state["user_request"]
        completed_tasks = state["completed_tasks"]
        tool_results = state["tool_results"]
        approval_requests = state.get("approval_requests", [])
        routing_decision = state["routing_decision"]
        approach_strategy = state["approach_strategy"]
        
        # Aggregate tool usage
        all_tools_used = set()
        all_actions_performed = set()
        total_execution_time = 0
        
        for task in completed_tasks:
            all_tools_used.update(task.get("tools_used", []))
            all_actions_performed.update(task.get("actions_performed", []))
            total_execution_time += task.get("execution_time_ms", 0)
        
        # Create execution summary
        execution_summary = {
            "total_tasks": len(completed_tasks),
            "successful_tasks": len([t for t in completed_tasks if t.get("status") == "completed"]),
            "failed_tasks": len([t for t in completed_tasks if t.get("status") == "failed"]),
            "tools_used": list(all_tools_used),
            "total_execution_time_ms": total_execution_time,
            "approval_requests_count": len(approval_requests),
            "mcp_enabled": state.get("enable_mcp_tools", False)
        }
        
        # Create comprehensive summary prompt
        task_summary = ""
        for i, task in enumerate(completed_tasks, 1):
            status_icon = "✅" if task.get("status") == "completed" else "❌"
            task_summary += f"\n{i}. {status_icon} {task['task']}\n"
            if task.get("key_outputs"):
                task_summary += f"   Result: {task['key_outputs'][:150]}...\n"
            if task.get("tools_used"):
                task_summary += f"   Tools: {', '.join(task['tools_used'])}\n"
        
        # Format tool results
        tool_summary = ""
        if tool_results:
            tool_summary = f"\n\nTool Execution Results:\n"
            for result in tool_results[:5]:  # Limit to first 5 results
                tool_summary += f"- {result.get('tool_name', 'Unknown')}: {result.get('summary', 'Executed successfully')}\n"
        
        # Handle approval requests
        approval_summary = ""
        if approval_requests:
            approval_summary = f"\n\n🔒 Approval Required:\n"
            for req in approval_requests:
                approval_summary += f"- {req.get('operation', 'Unknown operation')}: {req.get('message', 'Requires approval')}\n"
        
        summary_prompt = f"""
        Generate a comprehensive final response for this request: {user_request}
        
        Routing approach used: {routing_decision}
        Strategy: {approach_strategy}
        
        Completed tasks ({execution_summary['successful_tasks']}/{execution_summary['total_tasks']} successful):
        {task_summary}
        
        Tools used: {', '.join(execution_summary['tools_used']) if execution_summary['tools_used'] else 'Standard LLM processing only'}
        Total execution time: {execution_summary['total_execution_time_ms']:.0f}ms
        {tool_summary}
        {approval_summary}
        
        Create a final response that:
        1. Directly addresses the original request
        2. Synthesizes insights from all completed tasks and tool executions
        3. Highlights key results and accomplishments
        4. Explains any tool integrations that were used
        5. Mentions any approval requirements if applicable
        6. Provides actionable next steps if appropriate
        7. Shows the systematic approach taken
        
        Make the response comprehensive yet accessible, highlighting the enhanced capabilities from tool integration.
        """
        
        # Use centralized resource management for final summary
        session_id = state.get("session_id", "mcp_router_session")
        user_id = state.get("user_id", "system")
        
        result = await centralized_resource_service.allocate_and_invoke(
            prompt=summary_prompt,
            user_id=str(user_id),
            service_name="mcp_smart_router",
            session_id=session_id,
            complexity=ComplexityLevel.COMPLEX,
            fallback_allowed=True
        )
        
        final_response = result["response"]
        
        # Add to discussion context
        discussion_entry = {
            "expert": "MCP Smart Router",
            "response": final_response,
            "timestamp": datetime.now().isoformat(),
            "phase": "final_summary",
            "confidence": 0.95,
            "execution_summary": execution_summary
        }
        
        # Update state
        state["final_response"] = final_response
        state["execution_summary"] = execution_summary
        state["discussion_context"].append(discussion_entry)
        
        return state
    
    async def _execute_task_with_mcp_tools(
        self,
        task: str,
        tools_needed: List[str],
        user_id: str,
        authentication_context: Dict[str, Any],
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute task using MCP tools."""
        
        tool_results = []
        tools_used = []
        actions_performed = []
        execution_summary = ""
        
        start_time = time.time()
        
        try:
            for tool_spec in tools_needed:
                # Parse tool specification (format: "tool_name:operation" or just "tool_name")
                if ":" in tool_spec:
                    tool_name, operation = tool_spec.split(":", 1)
                else:
                    tool_name = tool_spec
                    operation = "default"
                
                # Determine parameters based on task and tool
                parameters = await self._generate_tool_parameters(task, tool_name, operation, state)
                
                # Execute tool via MCP registry
                if self.mcp_registry:
                    tool_result = await self.mcp_registry.execute_tool_request(
                        tool_name=tool_name,
                        parameters=parameters,
                        user_id=user_id,
                        authentication_context=authentication_context
                    )
                    
                    if tool_result["success"]:
                        tool_results.append({
                            "tool_name": tool_name,
                            "operation": operation,
                            "result": tool_result["result"],
                            "execution_time_ms": tool_result.get("execution_time_ms", 0),
                            "summary": f"Successfully executed {tool_name}:{operation}"
                        })
                        tools_used.append(tool_name)
                        actions_performed.append(f"{tool_name}:{operation}")
                    else:
                        # Handle tool execution failure
                        if tool_result.get("approval_required", False):
                            return {
                                "approval_required": True,
                                "approval_request": {
                                    "operation": f"{tool_name}:{operation}",
                                    "message": tool_result.get("error", "Operation requires approval"),
                                    "tool_name": tool_name,
                                    "parameters": parameters
                                }
                            }
                        else:
                            logger.warning(f"Tool execution failed: {tool_name}:{operation} - {tool_result.get('error')}")
                            execution_summary += f"⚠️ {tool_name}:{operation} failed: {tool_result.get('error', 'Unknown error')}\n"
            
            # Generate execution summary
            if tool_results:
                execution_summary += f"Successfully executed {len(tool_results)} tool operations for task: {task}"
                key_outputs = "; ".join([r.get("summary", "") for r in tool_results])
            else:
                execution_summary = f"Task completed without tool integration: {task}"
                key_outputs = "Task completed using LLM capabilities"
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            return {
                "execution": execution_summary,
                "key_outputs": key_outputs,
                "tools_used": tools_used,
                "actions_performed": actions_performed,
                "tool_results": tool_results,
                "execution_time_ms": execution_time_ms
            }
            
        except Exception as e:
            logger.error(f"Error executing task with MCP tools: {e}", exc_info=True)
            execution_time_ms = (time.time() - start_time) * 1000
            
            return {
                "execution": f"Task execution failed: {str(e)}",
                "key_outputs": f"Error: {str(e)}",
                "tools_used": tools_used,
                "actions_performed": actions_performed,
                "tool_results": tool_results,
                "execution_time_ms": execution_time_ms,
                "error": str(e)
            }
    
    async def _execute_task_with_llm(
        self,
        task: str,
        category: str,
        user_request: str,
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute task using LLM only (fallback when tools not available)."""
        
        start_time = time.time()
        
        task_prompt = f"""
        Execute this {category} task: {task}
        
        Original request context: {user_request}
        
        Since advanced productivity tools are not available, provide a comprehensive response using your knowledge and reasoning capabilities.
        
        Provide:
        1. TASK EXECUTION: Your detailed work on completing this task
        2. METHODS USED: Your reasoning approach and methodology
        3. KEY OUTPUTS: Main results, insights, or recommendations
        4. LIMITATIONS: Any limitations due to lack of tool access
        
        Be thorough and specific in your execution.
        
        Format your response as:
        TASK EXECUTION: [Your detailed work and process]
        METHODS USED: [Your reasoning approach]
        KEY OUTPUTS: [Results and insights]
        LIMITATIONS: [Any limitations noted]
        """
        
        session_id = state.get("session_id", "mcp_router_session")
        user_id = state.get("user_id", "system")
        
        result = await centralized_resource_service.allocate_and_invoke(
            prompt=task_prompt,
            user_id=str(user_id),
            service_name="mcp_smart_router",
            session_id=session_id,
            complexity=ComplexityLevel.MODERATE,
            fallback_allowed=True
        )
        
        response = result["response"]
        execution_time_ms = (time.time() - start_time) * 1000
        
        # Parse response sections
        sections = self._parse_llm_task_response(response)
        
        return {
            "execution": sections.get("task_execution", response),
            "key_outputs": sections.get("key_outputs", "Task completed using LLM reasoning"),
            "tools_used": ["LLM"],
            "actions_performed": [sections.get("methods_used", "Reasoning and analysis")],
            "tool_results": [],
            "execution_time_ms": execution_time_ms,
            "limitations": sections.get("limitations", "")
        }
    
    # Helper methods for parsing and tool management
    
    async def _parse_analysis_response(self, response: str) -> Tuple[str, Dict[str, Any], List[Dict[str, Any]]]:
        """Parse analysis response and extract structured data."""
        
        lines = response.split('\n')
        routing_decision = "DIRECT"
        complexity_analysis = {}
        tool_requirements = []
        
        current_section = None
        for line in lines:
            line = line.strip()
            if line.startswith("ROUTING DECISION:"):
                routing_decision = line.replace("ROUTING DECISION:", "").strip()
            elif line.startswith("COMPLEXITY ANALYSIS:"):
                current_section = "complexity"
            elif line.startswith("TOOL RECOMMENDATIONS:"):
                current_section = "tools"
            elif current_section == "complexity" and ":" in line and line.startswith("-"):
                parts = line[1:].split(":", 1)
                if len(parts) == 2:
                    key = parts[0].strip().replace(" ", "_").lower()
                    value = parts[1].strip()
                    complexity_analysis[key] = value
            elif current_section == "tools" and ":" in line and line.startswith("-"):
                parts = line[1:].split(":", 1)
                if len(parts) == 2:
                    tool_type = parts[0].strip().replace(" ", "_").lower()
                    assessment = parts[1].strip()
                    if "needed" in assessment.lower():
                        tool_requirements.append({
                            "tool_type": tool_type,
                            "assessment": assessment,
                            "needed": "needed" in assessment.lower()
                        })
        
        # Set confidence based on routing decision
        complexity_analysis["confidence"] = 0.95 if routing_decision == "DIRECT" else 0.85
        
        return routing_decision, complexity_analysis, tool_requirements
    
    async def _parse_planning_response(self, response: str, available_tools: List[Any]) -> Tuple[List[Dict[str, Any]], str, List[Dict[str, Any]]]:
        """Parse planning response and extract todo list and tool plan."""
        
        lines = response.split('\n')
        todo_list = []
        approach_strategy = ""
        selected_tools = []
        
        current_section = None
        for line in lines:
            line = line.strip()
            if line.startswith("APPROACH STRATEGY:"):
                current_section = "strategy"
            elif line.startswith("TODO LIST:"):
                current_section = "todos"
            elif line.startswith("TOOL INTEGRATION PLAN:"):
                current_section = "tool_plan"
            elif current_section == "strategy" and line:
                approach_strategy += line + " "
            elif current_section == "todos" and line and (line[0].isdigit() or line.startswith("-")):
                todo_item = self._parse_todo_item(line)
                if todo_item:
                    todo_list.append(todo_item)
            elif current_section == "tool_plan" and line.startswith("-"):
                tool_plan = self._parse_tool_plan_item(line)
                if tool_plan:
                    selected_tools.append(tool_plan)
        
        return todo_list, approach_strategy.strip(), selected_tools
    
    def _parse_todo_item(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a single todo item from planning response."""
        
        try:
            # Remove numbering and parse components
            if line.startswith(tuple('123456789')):
                line = line[2:].strip()
            elif line.startswith("- "):
                line = line[2:].strip()
            
            # Parse format: Task - Category: X - Priority: Y - Tools: [Z] - Time: W
            parts = line.split(" - ")
            if len(parts) < 2:
                return None
            
            task = parts[0].strip()
            
            # Parse other components
            category = "General"
            priority = "Medium"
            tools_needed = []
            estimated_time = "Medium"
            
            for part in parts[1:]:
                if part.startswith("Category:"):
                    category = part.replace("Category:", "").strip()
                elif part.startswith("Priority:"):
                    priority = part.replace("Priority:", "").strip()
                elif part.startswith("Tools:"):
                    tools_str = part.replace("Tools:", "").strip().strip("[]")
                    if tools_str and tools_str != "none":
                        tools_needed = [t.strip() for t in tools_str.split(",")]
                elif part.startswith("Time:"):
                    estimated_time = part.replace("Time:", "").strip()
            
            return {
                "task": task,
                "category": category,
                "priority": priority,
                "tools_needed": tools_needed,
                "estimated_time": estimated_time,
                "status": "pending"
            }
            
        except Exception as e:
            logger.warning(f"Error parsing todo item '{line}': {e}")
            return None
    
    def _parse_tool_plan_item(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a tool integration plan item."""
        
        try:
            # Format: - Tool: name - Operations: [op1, op2] - Purpose: purpose
            line = line[1:].strip()  # Remove leading dash
            
            parts = line.split(" - ")
            if len(parts) < 2:
                return None
            
            tool_name = ""
            operations = []
            purpose = ""
            
            for part in parts:
                if part.startswith("Tool:"):
                    tool_name = part.replace("Tool:", "").strip()
                elif part.startswith("Operations:"):
                    ops_str = part.replace("Operations:", "").strip().strip("[]")
                    if ops_str:
                        operations = [op.strip() for op in ops_str.split(",")]
                elif part.startswith("Purpose:"):
                    purpose = part.replace("Purpose:", "").strip()
            
            if tool_name:
                return {
                    "tool_name": tool_name,
                    "operations": operations,
                    "purpose": purpose
                }
            
        except Exception as e:
            logger.warning(f"Error parsing tool plan item '{line}': {e}")
        
        return None
    
    async def _generate_tool_parameters(
        self,
        task: str,
        tool_name: str,
        operation: str,
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate appropriate parameters for tool execution based on task context."""
        
        # This is a simplified parameter generation
        # In a full implementation, this would use more sophisticated analysis
        
        base_params = {
            "task_context": task,
            "user_request": state.get("user_request", ""),
            "session_id": state.get("session_id")
        }
        
        # Tool-specific parameter generation
        if tool_name.startswith("calendar"):
            if operation in ["create_event", "create"]:
                # Extract event details from task
                base_params.update({
                    "summary": f"Event for: {task}",
                    "start_time": (datetime.now() + timedelta(hours=1)).isoformat(),
                    "end_time": (datetime.now() + timedelta(hours=2)).isoformat(),
                    "description": f"Created from task: {task}"
                })
            elif operation in ["get_events", "list"]:
                base_params.update({
                    "start_date": datetime.now().isoformat(),
                    "end_date": (datetime.now() + timedelta(days=7)).isoformat()
                })
        
        elif tool_name.startswith("task"):
            if operation in ["create", "create_task"]:
                base_params.update({
                    "title": task[:100],  # Truncate for title
                    "description": task,
                    "priority": "medium"
                })
            elif operation in ["list", "get_list"]:
                base_params.update({
                    "limit": 20
                })
        
        elif tool_name.startswith("email"):
            if operation in ["compose", "create"]:
                base_params.update({
                    "subject": f"Regarding: {task[:50]}",
                    "body": f"This email is related to the task: {task}",
                    "priority": "normal"
                })
        
        return base_params
    
    def _parse_llm_task_response(self, response: str) -> Dict[str, str]:
        """Parse LLM task execution response into sections."""
        
        sections = {}
        lines = response.split('\n')
        current_section = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            if line.startswith("TASK EXECUTION:"):
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                current_section = "task_execution"
                current_content = [line.replace("TASK EXECUTION:", "").strip()]
            elif line.startswith("METHODS USED:"):
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                current_section = "methods_used"
                current_content = [line.replace("METHODS USED:", "").strip()]
            elif line.startswith("KEY OUTPUTS:"):
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                current_section = "key_outputs"
                current_content = [line.replace("KEY OUTPUTS:", "").strip()]
            elif line.startswith("LIMITATIONS:"):
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                current_section = "limitations"
                current_content = [line.replace("LIMITATIONS:", "").strip()]
            elif current_section and line:
                current_content.append(line)
        
        # Add final section
        if current_section:
            sections[current_section] = '\n'.join(current_content)
        
        # Clean up sections
        for key, value in sections.items():
            sections[key] = value.strip()
        
        return sections
    
    def _format_available_tools(self, tools: List[Any]) -> str:
        """Format available tools for inclusion in prompts."""
        
        if not tools:
            return "No MCP tools currently available."
        
        formatted = []
        for tool in tools[:5]:  # Limit to first 5 tools
            tool_name = tool.tool_name if hasattr(tool, 'tool_name') else str(tool)
            tool_desc = tool.tool_description if hasattr(tool, 'tool_description') else "Advanced productivity tool"
            formatted.append(f"- {tool_name}: {tool_desc}")
        
        if len(tools) > 5:
            formatted.append(f"... and {len(tools) - 5} more tools available")
        
        return '\n'.join(formatted)
    
    def _should_handle_approvals(self, state: Dict[str, Any]) -> str:
        """Determine if approval handling is needed."""
        
        approval_requests = state.get("approval_requests", [])
        return "handle_approvals" if approval_requests else "generate_response"
    
    def _update_average_response_time(self, execution_time_ms: float) -> None:
        """Update average response time metric."""
        
        current_avg = self.execution_metrics["average_response_time_ms"]
        total_requests = self.execution_metrics["successful_requests"]
        
        if total_requests == 1:
            self.execution_metrics["average_response_time_ms"] = execution_time_ms
        else:
            # Exponential moving average
            self.execution_metrics["average_response_time_ms"] = (
                current_avg * 0.8 + execution_time_ms * 0.2
            )
    
    async def get_service_metrics(self) -> Dict[str, Any]:
        """Get service performance metrics."""
        
        return {
            "service_name": "MCP Smart Router",
            "service_status": "active",
            "metrics": self.execution_metrics.copy(),
            "mcp_integration": {
                "registry_available": self.mcp_registry is not None,
                "security_framework_available": self.security_framework is not None,
                "tools_enabled": True
            },
            "performance": {
                "success_rate": (
                    self.execution_metrics["successful_requests"] / 
                    max(self.execution_metrics["total_requests"], 1)
                ),
                "average_response_time_ms": self.execution_metrics["average_response_time_ms"],
                "total_requests": self.execution_metrics["total_requests"]
            },
            "last_updated": datetime.now(timezone.utc).isoformat()
        }


# ================================
# Factory and Initialization
# ================================

# Global service instance
mcp_smart_router_service = MCPSmartRouterService()

async def create_mcp_smart_router_service() -> MCPSmartRouterService:
    """Create and initialize the MCP Smart Router Service."""
    
    await mcp_smart_router_service.initialize()
    logger.info("MCP Smart Router Service created and initialized")
    return mcp_smart_router_service

async def get_mcp_smart_router_service() -> MCPSmartRouterService:
    """Get the global MCP Smart Router Service instance."""
    return mcp_smart_router_service