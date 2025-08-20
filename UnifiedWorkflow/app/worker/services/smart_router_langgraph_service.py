"""
Smart Router LangGraph Service with Todo Management
Implements structured task planning and execution workflow similar to expert group.
"""

import json
import logging
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from enum import Enum

from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableLambda
from langchain_core.runnables.config import RunnableConfig
from pydantic import BaseModel, Field

from worker.services.ollama_service import invoke_llm_with_tokens
from worker.services.centralized_resource_service import centralized_resource_service, ComplexityLevel

logger = logging.getLogger(__name__)


class RouterState(BaseModel):
    """State object for the smart router workflow."""
    # Input data
    session_id: Optional[str] = None
    user_request: str = ""
    
    # Phase 1: Analysis
    routing_decision: str = ""
    complexity_analysis: Dict[str, Any] = Field(default_factory=dict)
    
    # Phase 2: Planning
    todo_list: List[Dict[str, Any]] = Field(default_factory=list)
    approach_strategy: str = ""
    
    # Phase 3: Task Execution
    completed_tasks: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Phase 4: Final Summary
    final_response: str = ""
    tools_used: List[str] = Field(default_factory=list)
    actions_performed: List[str] = Field(default_factory=list)
    
    # Workflow control
    current_phase: str = "analysis"
    discussion_context: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Configuration
    chat_model: str = "llama3.1:8b"


class TaskCategory(str, Enum):
    """Categories for different types of tasks."""
    RESEARCH = "Research"
    ANALYSIS = "Analysis"
    PLANNING = "Planning"
    CREATION = "Creation"
    PROBLEM_SOLVING = "Problem Solving"
    COMMUNICATION = "Communication"
    ORGANIZATION = "Organization"


class SmartRouterLangGraphService:
    """Enhanced smart router service using LangGraph for structured task management."""

    def __init__(self):
        self.workflow_graph = self._build_workflow_graph()

    def _build_workflow_graph(self) -> StateGraph:
        """Build the LangGraph workflow for smart router processing with Helios delegation."""
        
        workflow = StateGraph(RouterState)
        
        # Add nodes for each phase
        workflow.add_node("analyze_request", self._analyze_request_node)
        workflow.add_node("create_todo_plan", self._create_todo_plan_node)
        workflow.add_node("execute_tasks", self._execute_tasks_node)
        workflow.add_node("delegate_to_helios", self._delegate_to_helios_node)
        workflow.add_node("generate_final_response", self._generate_final_response_node)
        
        # Define the workflow flow with conditional routing
        workflow.set_entry_point("analyze_request")
        
        # Conditional routing based on complexity analysis
        workflow.add_conditional_edges(
            "analyze_request",
            self._route_decision,
            {
                "delegate": "delegate_to_helios",
                "plan": "create_todo_plan",
                "direct": "execute_tasks"
            }
        )
        
        workflow.add_edge("create_todo_plan", "execute_tasks")
        workflow.add_edge("execute_tasks", "generate_final_response")
        workflow.add_edge("delegate_to_helios", "generate_final_response")
        workflow.add_edge("generate_final_response", END)
        
        return workflow.compile()

    async def process_request(self, user_request: str, session_id: str = None) -> Dict[str, Any]:
        """Process smart router request using LangGraph workflow with todo management."""
        
        # Initialize state
        initial_state = RouterState(
            session_id=session_id or str(uuid.uuid4()),
            user_request=user_request
        )
        
        # Run the workflow
        config = RunnableConfig(recursion_limit=100)
        final_state = await self.workflow_graph.ainvoke(initial_state.dict(), config)
        
        return {
            "response": final_state["final_response"],
            "discussion_context": final_state["discussion_context"],
            "routing_decision": final_state["routing_decision"],
            "todo_list": final_state["todo_list"],
            "completed_tasks": final_state["completed_tasks"],
            "tools_used": final_state["tools_used"],
            "actions_performed": final_state["actions_performed"],
            "complexity_analysis": final_state["complexity_analysis"],
            "approach_strategy": final_state["approach_strategy"],
            "workflow_type": "langgraph_smart_router",
            "confidence_score": final_state["complexity_analysis"].get("confidence", 0.85)
        }

    async def _analyze_request_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 1: Analyze the request and determine routing approach."""
        
        user_request = state["user_request"]
        
        analysis_prompt = f"""
        As an intelligent routing system with access to expert teams, analyze this user request: {user_request}

        Provide a comprehensive analysis including:

        1. ROUTING DECISION: Choose the best approach:
           - DIRECT: Simple, straightforward response (factual questions, basic tasks)
           - PLANNING: Complex task requiring structured breakdown (projects, multi-step processes)
           - DELEGATE: Multi-domain expertise needed, strategic analysis, or collaborative problem-solving

        2. COMPLEXITY ANALYSIS:
           - Complexity Level: [Simple/Moderate/Complex/Strategic]
           - Task Category: [Research/Analysis/Planning/Creation/Problem Solving/Communication/Organization]
           - Domains Involved: [List of expertise domains needed]
           - Collaboration Benefits: [Why expert team would add value]
           - Tool Limitations: [What individual tools might miss]
           - Estimated Steps: [Number of steps needed]
           - Resources Required: [What resources/tools might be needed]
           - Time Scope: [Quick/Medium/Extended]

        3. DELEGATION INDICATORS:
           - Multi-domain expertise required?
           - Strategic or comprehensive analysis needed?
           - Would benefit from multiple expert perspectives?
           - Complex problem-solving requiring collaboration?

        4. KEY CONSIDERATIONS:
           - What are the main challenges or requirements?
           - What domain knowledge is needed?
           - Are there dependencies or prerequisites?

        Format your response as:
        ROUTING DECISION: [DIRECT, PLANNING, or DELEGATE]
        
        COMPLEXITY ANALYSIS:
        - Complexity Level: [level]
        - Task Category: [category]
        - Domains Involved: [domains]
        - Estimated Steps: [number]
        - Resources Required: [list]
        - Time Scope: [scope]
        
        KEY CONSIDERATIONS:
        [Your analysis of challenges and requirements]
        """
        
        # Use centralized resource management for request analysis
        session_id = state.get("session_id", "smart_router_session")
        user_id = state.get("user_id", "system")
        
        result = await centralized_resource_service.allocate_and_invoke(
            prompt=analysis_prompt,
            user_id=str(user_id),
            service_name="smart_router",
            session_id=session_id,
            complexity=ComplexityLevel.COMPLEX,  # Analysis requires complex reasoning
            fallback_allowed=True
        )
        
        response = result["response"]
        
        # Parse the analysis response
        lines = response.split('\n')
        routing_decision = ""
        complexity_analysis = {}
        considerations = ""
        
        current_section = None
        for line in lines:
            line = line.strip()
            if line.startswith("ROUTING DECISION:"):
                routing_decision = line.replace("ROUTING DECISION:", "").strip()
            elif line.startswith("COMPLEXITY ANALYSIS:"):
                current_section = "complexity"
            elif line.startswith("KEY CONSIDERATIONS:"):
                current_section = "considerations"
            elif current_section == "complexity" and ":" in line and line.startswith("-"):
                parts = line[1:].split(":", 1)
                if len(parts) == 2:
                    key = parts[0].strip().replace(" ", "_").lower()
                    value = parts[1].strip()
                    complexity_analysis[key] = value
            elif current_section == "considerations" and line:
                considerations += line + " "
        
        # Set confidence based on routing decision
        if routing_decision == "DIRECT":
            confidence = 0.95
        elif routing_decision == "DELEGATE":
            confidence = 0.90  # High confidence in expert team
        else:  # PLANNING
            confidence = 0.85
        complexity_analysis["confidence"] = confidence
        complexity_analysis["considerations"] = considerations.strip()
        
        # Add to discussion context
        discussion_entry = {
            "expert": "Smart Router",
            "response": f"Analysis complete. Routing decision: {routing_decision}. {considerations[:100]}...",
            "timestamp": datetime.now().isoformat(),
            "phase": "analysis",
            "confidence": confidence
        }
        
        state["routing_decision"] = routing_decision
        state["complexity_analysis"] = complexity_analysis
        state["current_phase"] = "planning"
        state["discussion_context"] = [discussion_entry]
        
        return state

    def _route_decision(self, state: Dict[str, Any]) -> str:
        """Determine routing based on analysis results."""
        routing_decision = state.get("routing_decision", "DIRECT").upper()
        
        if routing_decision == "DELEGATE":
            return "delegate"
        elif routing_decision == "PLANNING":
            return "plan"
        else:
            return "direct"

    async def _delegate_to_helios_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate complex tasks to the Helios expert team."""
        
        user_request = state["user_request"]
        session_id = state.get("session_id", "smart_router_session")
        complexity_analysis = state.get("complexity_analysis", {})
        
        try:
            # Import and use the existing Helios delegation handler
            from worker.tool_handlers import handle_helios_delegation
            
            # Collect all delegation output
            delegation_response_parts = []
            
            # Call the Helios delegation handler and collect streaming responses
            async for chunk in handle_helios_delegation(
                user_input=user_request,
                user_id=1,  # Default user ID for system requests
                session_id=session_id
            ):
                delegation_response_parts.append(chunk)
            
            # Combine all response parts
            full_delegation_response = "".join(delegation_response_parts)
            
            # Update state with delegation results
            state["final_response"] = full_delegation_response
            state["current_phase"] = "completed"
            state["tools_used"] = ["delegate_to_helios_team"]
            state["actions_performed"] = ["Delegated to Helios expert team for collaborative analysis"]
            
            # Add delegation summary to discussion context
            delegation_entry = {
                "expert": "Helios Delegation System",
                "response": "Task successfully delegated to expert team for comprehensive analysis",
                "timestamp": datetime.now().isoformat(),
                "phase": "delegation",
                "confidence": 0.95
            }
            
            discussion_context = state.get("discussion_context", [])
            discussion_context.append(delegation_entry)
            state["discussion_context"] = discussion_context
            
        except Exception as e:
            logger.error(f"Error in Helios delegation: {e}", exc_info=True)
            
            # Fallback response
            fallback_response = f"""I attempted to delegate your request to our expert team for comprehensive analysis, but encountered a technical issue.

**Your Request**: {user_request}

**Analysis**: Based on the complexity analysis, this request would benefit from collaborative expert input involving multiple domains: {complexity_analysis.get('domains_involved', 'multiple areas')}.

**Alternative Approach**: I can provide a structured analysis using available tools, though it may not have the full depth that our expert team collaboration would provide.

Would you like me to proceed with a direct analysis, or would you prefer to try the expert team delegation again?"""

            state["final_response"] = fallback_response
            state["current_phase"] = "completed"
            state["tools_used"] = ["delegation_fallback"]
            state["actions_performed"] = ["Attempted Helios delegation with fallback response"]
        
        return state

    async def _create_todo_plan_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 2: Create structured todo plan based on analysis."""
        
        user_request = state["user_request"]
        routing_decision = state["routing_decision"]
        complexity_analysis = state["complexity_analysis"]
        
        if routing_decision == "DIRECT":
            # For direct routing, create a simple single-task plan
            todo_list = [{
                "task": f"Provide direct response to: {user_request}",
                "category": complexity_analysis.get("task_category", "Communication"),
                "priority": "High",
                "status": "pending",
                "estimated_time": "Quick"
            }]
            approach_strategy = "Direct response approach - provide immediate, comprehensive answer."
        elif routing_decision == "DELEGATE":
            # This shouldn't happen with proper routing, but provide fallback
            todo_list = [{
                "task": f"Delegate to expert team: {user_request}",
                "category": "Collaboration",
                "priority": "High",
                "status": "pending",
                "estimated_time": "Extended"
            }]
            approach_strategy = "Expert team delegation - comprehensive collaborative analysis."
        else:
            # For planning routing, create detailed todo breakdown
            planning_prompt = f"""
            Based on this request: {user_request}
            
            Analysis shows:
            - Complexity: {complexity_analysis.get('complexity_level', 'Moderate')}
            - Category: {complexity_analysis.get('task_category', 'Planning')}
            - Estimated Steps: {complexity_analysis.get('estimated_steps', '3-5')}
            - Resources: {complexity_analysis.get('resources_required', 'Standard')}
            
            Create a detailed todo list that breaks down this request into actionable tasks.
            
            Format your response as:
            
            APPROACH STRATEGY:
            [Explain the overall approach and methodology]
            
            TODO LIST:
            1. [Task description] - Category: [Research/Analysis/Planning/Creation/Problem Solving/Communication/Organization] - Priority: [High/Medium/Low] - Time: [Quick/Medium/Extended]
            2. [Task description] - Category: [category] - Priority: [priority] - Time: [time]
            [Continue...]
            
            Ensure tasks are:
            - Specific and actionable
            - Properly sequenced (dependencies considered)
            - Categorized appropriately
            - Realistic in scope and time estimation
            """
            
            # Use centralized resource management for planning
            session_id = state.get("session_id", "smart_router_session")
            user_id = state.get("user_id", "system")
            
            result = await centralized_resource_service.allocate_and_invoke(
                prompt=planning_prompt,
                user_id=str(user_id),
                service_name="smart_router",
                session_id=session_id,
                complexity=ComplexityLevel.COMPLEX,  # Planning requires complex reasoning
                fallback_allowed=True
            )
            
            response = result["response"]
            
            # Parse todo list
            lines = response.split('\n')
            todo_list = []
            approach_strategy = ""
            
            current_section = None
            for line in lines:
                line = line.strip()
                if line.startswith("APPROACH STRATEGY:"):
                    current_section = "strategy"
                elif line.startswith("TODO LIST:"):
                    current_section = "todos"
                elif current_section == "strategy" and line:
                    approach_strategy += line + " "
                elif current_section == "todos" and line and (line[0].isdigit() or line.startswith("-")):
                    # Parse todo item
                    if " - Category:" in line and " - Priority:" in line and " - Time:" in line:
                        parts = line.split(" - Category:")
                        task_part = parts[0].strip()
                        if task_part.startswith(tuple('123456789')):
                            task_part = task_part[2:].strip()  # Remove numbering
                        
                        remaining = parts[1].split(" - Priority:")
                        category = remaining[0].strip()
                        
                        priority_time = remaining[1].split(" - Time:")
                        priority = priority_time[0].strip()
                        estimated_time = priority_time[1].strip() if len(priority_time) > 1 else "Medium"
                        
                        todo_list.append({
                            "task": task_part,
                            "category": category,
                            "priority": priority,
                            "estimated_time": estimated_time,
                            "status": "pending"
                        })
        
        # Add to discussion context
        planning_message = f"Created {len(todo_list)}-item action plan using {routing_decision.lower()} approach. {approach_strategy[:100]}..."
        discussion_entry = {
            "expert": "Smart Router",
            "response": planning_message,
            "timestamp": datetime.now().isoformat(),
            "phase": "planning",
            "confidence": 0.90
        }
        
        state["todo_list"] = todo_list
        state["approach_strategy"] = approach_strategy.strip()
        state["current_phase"] = "execution"
        state["discussion_context"].append(discussion_entry)
        
        return state

    async def _execute_tasks_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 3: Execute todo list tasks."""
        
        todo_list = state["todo_list"]
        user_request = state["user_request"]
        completed_tasks = []
        tools_used = []
        actions_performed = []
        
        for todo_item in todo_list:
            task = todo_item["task"]
            category = todo_item["category"]
            
            # Execute task based on category
            task_prompt = f"""
            Execute this {category} task: {task}
            
            Original request context: {user_request}
            
            Provide:
            1. TASK EXECUTION: Your detailed work on completing this task
            2. TOOLS USED: Any methods, frameworks, or approaches you applied
            3. ACTIONS PERFORMED: Specific actions you took to complete the task
            4. KEY OUTPUTS: Main results, findings, or deliverables from this task
            
            Be thorough and specific in your execution.
            
            Format your response as:
            TASK EXECUTION: [Your detailed work and process]
            TOOLS USED: [List methods, frameworks, approaches]
            ACTIONS PERFORMED: [Specific actions taken]
            KEY OUTPUTS: [Results and deliverables]
            """
            
            # Use centralized resource management for task execution
            session_id = state.get("session_id", "smart_router_session")
            user_id = state.get("user_id", "system")
            
            result = await centralized_resource_service.allocate_and_invoke(
                prompt=task_prompt,
                user_id=str(user_id),
                service_name="smart_router",
                session_id=session_id,
                complexity=ComplexityLevel.COMPLEX,  # Task execution requires complex reasoning
                fallback_allowed=True
            )
            
            response = result["response"]
            
            # Parse response
            lines = response.split('\n')
            task_execution = ""
            task_tools = []
            task_actions = []
            key_outputs = ""
            
            current_section = None
            for line in lines:
                line = line.strip()
                if line.startswith("TASK EXECUTION:"):
                    current_section = "execution"
                    task_execution = line.replace("TASK EXECUTION:", "").strip()
                elif line.startswith("TOOLS USED:"):
                    current_section = "tools"
                elif line.startswith("ACTIONS PERFORMED:"):
                    current_section = "actions"
                elif line.startswith("KEY OUTPUTS:"):
                    current_section = "outputs"
                elif current_section == "execution" and line:
                    task_execution += " " + line
                elif current_section == "tools" and line:
                    task_tools.append(line.lstrip("- "))
                elif current_section == "actions" and line:
                    task_actions.append(line.lstrip("- "))
                elif current_section == "outputs" and line:
                    key_outputs += " " + line
            
            completed_task = {
                "task": task,
                "category": category,
                "execution": task_execution,
                "key_outputs": key_outputs.strip(),
                "status": "completed",
                "tools_used": task_tools,
                "actions_performed": task_actions,
                "priority": todo_item["priority"]
            }
            
            completed_tasks.append(completed_task)
            tools_used.extend(task_tools)
            actions_performed.extend(task_actions)
            
            # Add to discussion context
            discussion_entry = {
                "expert": "Smart Router",
                "response": f"✅ {task} - {key_outputs[:100]}..." if key_outputs else f"✅ {task}",
                "timestamp": datetime.now().isoformat(),
                "phase": "task_execution",
                "task": task,
                "confidence": 0.85
            }
            state["discussion_context"].append(discussion_entry)
        
        state["completed_tasks"] = completed_tasks
        state["tools_used"] = list(set(tools_used))  # Remove duplicates
        state["actions_performed"] = list(set(actions_performed))
        state["current_phase"] = "summary"
        
        return state

    async def _generate_final_response_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 4: Generate comprehensive final response."""
        
        user_request = state["user_request"]
        completed_tasks = state["completed_tasks"]
        routing_decision = state["routing_decision"]
        approach_strategy = state["approach_strategy"]
        tools_used = state["tools_used"]
        actions_performed = state["actions_performed"]
        
        # Create task summary
        task_summary = ""
        key_outputs_combined = ""
        
        for i, task in enumerate(completed_tasks, 1):
            task_summary += f"\n{i}. ✅ {task['task']}\n   Result: {task['execution'][:150]}...\n"
            if task.get('key_outputs'):
                key_outputs_combined += f"{task['key_outputs']} "
        
        summary_prompt = f"""
        Generate a comprehensive final response for this request: {user_request}
        
        Routing approach used: {routing_decision}
        Strategy: {approach_strategy}
        
        Completed tasks:
        {task_summary}
        
        Tools used: {', '.join(tools_used) if tools_used else 'Standard analysis methods'}
        Actions performed: {', '.join(actions_performed) if actions_performed else 'Systematic approach'}
        
        Combined outputs: {key_outputs_combined}
        
        Create a final response that:
        1. Directly addresses the original request
        2. Synthesizes insights from all completed tasks
        3. Provides actionable recommendations or clear answers
        4. Shows the systematic approach taken
        5. Offers next steps if appropriate
        
        Make the response comprehensive yet accessible, highlighting the structured approach used.
        """
        
        # Use centralized resource management for final summary
        session_id = state.get("session_id", "smart_router_session")
        user_id = state.get("user_id", "system")
        
        result = await centralized_resource_service.allocate_and_invoke(
            prompt=summary_prompt,
            user_id=str(user_id),
            service_name="smart_router",
            session_id=session_id,
            complexity=ComplexityLevel.COMPLEX,  # Summary generation requires complex reasoning
            fallback_allowed=True
        )
        
        final_response = result["response"]
        
        # Add to discussion context
        discussion_entry = {
            "expert": "Smart Router",
            "response": final_response,
            "timestamp": datetime.now().isoformat(),
            "phase": "final_summary",
            "confidence": 0.95
        }
        
        state["final_response"] = final_response
        state["discussion_context"].append(discussion_entry)
        
        return state


# Create service instance
smart_router_langgraph_service = SmartRouterLangGraphService()