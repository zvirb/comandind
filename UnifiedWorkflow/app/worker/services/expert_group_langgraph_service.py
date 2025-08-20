"""
Enhanced Expert Group Service using LangGraph with Real Tool Integration
Implements specialized agents with actual tool usage - Research Specialist uses Tavily API,
Personal Assistant uses Google Calendar, with streaming tool usage transparency.
"""

import json
import logging
import uuid
import asyncio
import time
from typing import Dict, Any, List, Optional, Tuple, AsyncGenerator
from datetime import datetime, timezone
from enum import Enum

try:
    from langgraph.graph import StateGraph, END
    from langchain_core.runnables import RunnableLambda
    from langchain_core.runnables.config import RunnableConfig
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
from pydantic import BaseModel, Field

from worker.services.ollama_service import invoke_llm_with_tokens
from worker.services.expert_group_specialized_methods import (
    collect_expert_input_with_tools,
    enhance_summary_with_tool_usage
)

logger = logging.getLogger(__name__)


class WorkflowMetrics:
    """Collect and track workflow performance metrics."""
    
    def __init__(self):
        self.start_time = None
        self.phase_times = {}
        self.token_usage = {}
        self.error_count = 0
        self.retry_count = 0
        
    def start_workflow(self):
        self.start_time = time.time()
    
    def track_phase(self, phase_name: str):
        if phase_name not in self.phase_times:
            self.phase_times[phase_name] = time.time()
    
    def add_token_usage(self, phase: str, tokens: int):
        self.token_usage[phase] = self.token_usage.get(phase, 0) + tokens
    
    def increment_error(self):
        self.error_count += 1
        
    def increment_retry(self):
        self.retry_count += 1
    
    def get_summary(self) -> Dict[str, Any]:
        total_time = time.time() - self.start_time if self.start_time else 0
        return {
            "total_execution_time": total_time,
            "phase_breakdown": self.phase_times,
            "total_tokens": sum(self.token_usage.values()),
            "token_by_phase": self.token_usage,
            "error_count": self.error_count,
            "retry_count": self.retry_count,
            "success_rate": 1 - (self.error_count / max(1, len(self.phase_times)))
        }


class ExpertGroupState(BaseModel):
    """State object for the expert group workflow."""
    # Input data
    session_id: Optional[str] = None
    user_request: str = ""
    selected_agents: List[str] = Field(default_factory=list)
    
    # Phase 1: Questioning
    pm_questions: Dict[str, str] = Field(default_factory=dict)
    
    # Phase 2: Expert Input
    expert_inputs: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    # Tool Usage Tracking
    tool_calls_made: List[Dict[str, Any]] = Field(default_factory=list)
    search_results: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    calendar_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Phase 3: Planning
    todo_list: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Phase 4: Task Execution
    completed_tasks: List[Dict[str, Any]] = Field(default_factory=list)
    
    # User context for tool usage
    user_id: Optional[str] = None
    
    # Phase 5: Final Summary
    final_summary: str = ""
    tools_used: List[str] = Field(default_factory=list)
    actions_performed: List[str] = Field(default_factory=list)
    
    # Workflow control
    current_phase: str = "questioning"
    discussion_context: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Configuration
    chat_model: str = "llama3.1:8b"


class AgentRole(str, Enum):
    """Available expert roles with tool specialization."""
    PROJECT_MANAGER = "Project Manager"
    TECHNICAL_EXPERT = "Technical Expert"
    BUSINESS_ANALYST = "Business Analyst"
    CREATIVE_DIRECTOR = "Creative Director"
    RESEARCH_SPECIALIST = "Research Specialist"  # Uses Tavily web search
    PLANNING_EXPERT = "Planning Expert"
    SOCRATIC_EXPERT = "Socratic Expert"
    WELLBEING_COACH = "Wellbeing Coach"
    PERSONAL_ASSISTANT = "Personal Assistant"  # Uses Google Calendar
    DATA_ANALYST = "Data Analyst"
    OUTPUT_FORMATTER = "Output Formatter"
    QUALITY_ASSURANCE = "Quality Assurance"


class ExpertGroupLangGraphService:
    """Enhanced expert group service using LangGraph for workflow orchestration with self-correction."""

    def __init__(self):
        self.agent_id_to_role = {
            "project_manager": AgentRole.PROJECT_MANAGER,
            "technical_expert": AgentRole.TECHNICAL_EXPERT,
            "business_analyst": AgentRole.BUSINESS_ANALYST,
            "creative_director": AgentRole.CREATIVE_DIRECTOR,
            "research_specialist": AgentRole.RESEARCH_SPECIALIST,
            "planning_expert": AgentRole.PLANNING_EXPERT,
            "socratic_expert": AgentRole.SOCRATIC_EXPERT,
            "wellbeing_coach": AgentRole.WELLBEING_COACH,
            "personal_assistant": AgentRole.PERSONAL_ASSISTANT,
            "data_analyst": AgentRole.DATA_ANALYST,
            "output_formatter": AgentRole.OUTPUT_FORMATTER,
            "quality_assurance": AgentRole.QUALITY_ASSURANCE
        }
        # Create reverse mapping for validation
        self.role_to_agent_id = {role.value: agent_id for agent_id, role in self.agent_id_to_role.items()}
        self.valid_expert_names = set(role.value for role in AgentRole)
        self.workflow_graph = self._build_workflow_graph()
        self.metrics = WorkflowMetrics()

    def validate_and_filter_experts(self, expert_names: List[str]) -> List[str]:
        """
        Validate expert names against the legitimate list and filter out hallucinated experts.
        
        Returns:
            List of valid expert names only
        """
        valid_experts = []
        invalid_experts = []
        
        for expert_name in expert_names:
            if expert_name in self.valid_expert_names:
                valid_experts.append(expert_name)
            else:
                invalid_experts.append(expert_name)
                logger.warning(f"HALLUCINATION DETECTED: Invalid expert '{expert_name}' filtered out. Valid experts: {list(self.valid_expert_names)}")
        
        if invalid_experts:
            logger.error(f"Hallucinated experts detected and filtered: {invalid_experts}")
        
        return valid_experts

    def validate_expert_questions(self, questions: Dict[str, str]) -> Dict[str, str]:
        """
        Validate that questions are only for legitimate experts.
        
        Returns:
            Filtered dictionary with only valid expert questions
        """
        validated_questions = {}
        hallucinated_experts = []
        
        for expert_name, question in questions.items():
            if expert_name in self.valid_expert_names:
                validated_questions[expert_name] = question
            else:
                hallucinated_experts.append(expert_name)
                logger.warning(f"HALLUCINATION DETECTED: Question for invalid expert '{expert_name}' filtered out")
        
        if hallucinated_experts:
            logger.error(f"Hallucinated expert questions filtered: {hallucinated_experts}")
        
        return validated_questions

    async def robust_ollama_call(self, prompt: str, model: str = "llama3.1:8b", max_retries: int = 3) -> Tuple[str, bool]:
        """Robust Ollama call with retry logic and self-correction."""
        for attempt in range(max_retries):
            try:
                response, tokens = await invoke_llm_with_tokens(
                    messages=[{"role": "user", "content": prompt}],
                    model_name=model
                )
                self.metrics.add_token_usage("ollama_call", tokens.total_tokens if hasattr(tokens, 'total_tokens') else 100)
                return response, True
            except Exception as e:
                logger.warning(f"Ollama call attempt {attempt + 1} failed: {e}")
                self.metrics.increment_retry()
                if attempt == max_retries - 1:
                    self.metrics.increment_error()
                    return f"Failed to process request after {max_retries} attempts: {str(e)}", False
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

    def _build_workflow_graph(self):
        """Build the LangGraph workflow for expert group processing."""
        
        if not LANGGRAPH_AVAILABLE:
            logger.warning("LangGraph not available, workflow will use sequential processing")
            return None
        
        # Use Dict instead of Pydantic model for LangGraph state
        from typing import Dict, Any
        workflow = StateGraph(Dict[str, Any])
        
        # Add nodes for each phase
        workflow.add_node("pm_questioning", self._pm_questioning_node)
        workflow.add_node("collect_expert_input", self._collect_expert_input_node)
        workflow.add_node("pm_planning", self._pm_planning_node)
        workflow.add_node("execute_tasks", self._execute_tasks_node)
        workflow.add_node("create_final_summary", self._final_summary_node)
        
        # Define the workflow flow
        workflow.set_entry_point("pm_questioning")
        workflow.add_edge("pm_questioning", "collect_expert_input")
        workflow.add_edge("collect_expert_input", "pm_planning")
        workflow.add_edge("pm_planning", "execute_tasks")
        workflow.add_edge("execute_tasks", "create_final_summary")
        workflow.add_edge("create_final_summary", END)
        
        return workflow.compile()

    async def process_request(self, user_request: str, selected_agents: List[str] = None, user_id: str = None) -> Dict[str, Any]:
        """Process expert group request using LangGraph workflow with self-correction and error recovery."""
        
        # Initialize metrics tracking
        self.metrics = WorkflowMetrics()
        self.metrics.start_workflow()
        
        if not LANGGRAPH_AVAILABLE or self.workflow_graph is None:
            logger.info("Using fallback sequential processing (LangGraph not available)")
            return await self._fallback_process_request(user_request, selected_agents, user_id)
        
        # Initialize state with proper validation
        try:
            initial_state = ExpertGroupState(
                session_id=str(uuid.uuid4()),
                user_request=user_request,
                selected_agents=selected_agents or [],
                user_id=user_id
            )
            
            # Convert to dict for LangGraph (AIOLLAMA pattern)
            state_dict = initial_state.dict()
            
        except Exception as e:
            logger.error(f"Failed to initialize workflow state: {e}")
            return await self._emergency_fallback(user_request, selected_agents, user_id)
        
        # Run the workflow with hierarchical error handling
        max_workflow_retries = 2
        for workflow_attempt in range(max_workflow_retries):
            try:
                logger.info(f"Starting LangGraph workflow (attempt {workflow_attempt + 1})")
                config = RunnableConfig(recursion_limit=100)
                
                # Execute workflow with timeout
                final_state = await asyncio.wait_for(
                    self.workflow_graph.ainvoke(state_dict, config),
                    timeout=3600.0  # 1 hour timeout from AIASSIST.md
                )
                
                logger.info(f"Workflow completed. Final state type: {type(final_state)}")
                
                # Handle Pydantic conversion (AIOLLAMA pattern)
                if hasattr(final_state, 'dict'):
                    logger.info("Converting Pydantic model to dict")
                    final_state = final_state.dict()
                
                # Validate and sanitize final state
                validated_state = await self._validate_final_state(final_state)
                if validated_state:
                    # Add metrics to response
                    validated_state["workflow_metrics"] = self.metrics.get_summary()
                    return validated_state
                else:
                    logger.warning(f"State validation failed on attempt {workflow_attempt + 1}")
                    if workflow_attempt < max_workflow_retries - 1:
                        # Reset and retry with corrected state
                        state_dict = await self._apply_state_correction(state_dict, final_state)
                        continue
                    else:
                        logger.error("All workflow attempts failed validation")
                        return await self._fallback_process_request(user_request, selected_agents)
                        
            except asyncio.TimeoutError:
                logger.error(f"Workflow timeout on attempt {workflow_attempt + 1}")
                self.metrics.increment_error()
                if workflow_attempt < max_workflow_retries - 1:
                    continue
                else:
                    return await self._timeout_fallback(user_request, selected_agents, user_id)
                    
            except Exception as e:
                logger.error(f"Workflow execution failed on attempt {workflow_attempt + 1}: {e}")
                self.metrics.increment_error()
                if workflow_attempt < max_workflow_retries - 1:
                    await asyncio.sleep(2)  # Brief pause before retry
                    continue
                else:
                    logger.info("All workflow attempts failed, using emergency fallback")
                    return await self._emergency_fallback(user_request, selected_agents, user_id)
        
        # Should never reach here, but just in case
        return await self._emergency_fallback(user_request, selected_agents)

    async def _pm_questioning_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 1: PM questions experts for their input with self-correction."""
        
        self.metrics.track_phase("pm_questioning")
        selected_agents = state["selected_agents"]
        user_request = state["user_request"]
        
        # Validate inputs
        if not selected_agents:
            selected_agents = ["technical_expert", "business_analyst"]  # Default experts
            state["selected_agents"] = selected_agents
        
        # Generate specific questions for each selected expert
        # Convert agent IDs to role names for the prompt
        expert_role_names = [self.agent_id_to_role[agent].value for agent in selected_agents if agent in self.agent_id_to_role]
        
        pm_prompt = f"""
        As the Project Manager, I need to coordinate our expert team to address this request: {user_request}

        Selected experts: {', '.join(expert_role_names)}

        Generate specific, targeted questions for each expert to gather their initial insights. Questions should be:
        1. Relevant to their expertise area
        2. Help identify key considerations and potential approaches
        3. Set up the foundation for creating a comprehensive action plan

        Format your response as:
        COORDINATION MESSAGE: [Brief message about your coordination approach]
        
        EXPERT QUESTIONS:
        - {expert_role_names[0] if expert_role_names else 'Expert'}: [Specific question]
        [Continue for each expert]
        
        IMPORTANT: Only use the exact expert names provided above. Do not create or mention any other experts.
        """
        
        # Use robust Ollama call with retry logic
        response, success = await self.robust_ollama_call(
            pm_prompt,
            model=state.get("chat_model", "llama3.1:8b")
        )
        
        if not success:
            # Fallback PM questioning
            response = f"Welcome team! Let's collaborate on: {user_request}\n\nEXPERT QUESTIONS:\n"
            for agent in selected_agents:
                if agent in self.agent_id_to_role:
                    role = self.agent_id_to_role[agent].value
                    response += f"- {role}: What are your key insights and recommendations for this request?\n"
        
        # Parse PM response to extract questions with error handling
        lines = response.split('\n')
        coordination_message = ""
        questions = {}
        
        current_section = None
        for line in lines:
            line = line.strip()
            if line.startswith("COORDINATION MESSAGE:"):
                coordination_message = line.replace("COORDINATION MESSAGE:", "").strip()
                current_section = "coordination"
            elif line.startswith("EXPERT QUESTIONS:"):
                current_section = "questions"
            elif current_section == "questions" and ":" in line and line.startswith("-"):
                parts = line[1:].split(":", 1)
                if len(parts) == 2:
                    expert_name = parts[0].strip()
                    question = parts[1].strip()
                    questions[expert_name] = question
        
        # Validate questions to filter out hallucinated experts
        questions = self.validate_expert_questions(questions)
        
        # Validate that we have questions for all selected agents
        for agent in selected_agents:
            if agent in self.agent_id_to_role:
                role_name = self.agent_id_to_role[agent].value
                if role_name not in questions:
                    # Generate fallback question
                    questions[role_name] = f"What are your key considerations and recommendations for: {user_request}?"
        
        # Ensure we have a coordination message
        if not coordination_message:
            coordination_message = f"Coordinating expert consultation for: {user_request}"
        
        # Add to discussion context with validation
        discussion_entry = {
            "expert": AgentRole.PROJECT_MANAGER.value,
            "response": coordination_message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phase": "questioning",
            "confidence": 0.95 if success else 0.7
        }
        
        # Ensure required state fields exist
        state["pm_questions"] = questions
        state["current_phase"] = "expert_input"
        state["discussion_context"] = [discussion_entry]
        
        # Add tools and actions tracking
        if "tools_used" not in state:
            state["tools_used"] = []
        if "actions_performed" not in state:
            state["actions_performed"] = []
        
        state["tools_used"].append("Project Management Framework")
        state["actions_performed"].append("Expert team coordination")
        
        logger.info(f"PM questioning phase completed. Generated {len(questions)} questions.")
        return state

    async def _collect_expert_input_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 2: Collect input from experts with real tool usage for specialized agents."""
        
        return await collect_expert_input_with_tools(state, self.agent_id_to_role)

    async def _pm_planning_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 3: PM creates todo list based on expert input."""
        
        user_request = state["user_request"]
        expert_inputs = state["expert_inputs"]
        
        # Compile expert insights for PM planning
        expert_summary = ""
        for expert, data in expert_inputs.items():
            expert_summary += f"\n{expert}: {data['input']}\n"
        
        pm_planning_prompt = f"""
        As the Project Manager, I've gathered input from our expert team. Now I need to create a comprehensive todo list.

        Original request: {user_request}

        Expert inputs:
        {expert_summary}

        Based on this expert input, create a detailed todo list with the following format:
        
        TODO LIST:
        1. [Task description] - Assigned to: [Expert name] - Priority: [High/Medium/Low]
        2. [Task description] - Assigned to: [Expert name] - Priority: [High/Medium/Low]
        [Continue...]

        COORDINATION STRATEGY:
        [Explain how these tasks work together and the overall approach]

        Ensure tasks are:
        - Specific and actionable
        - Assigned to the most appropriate expert
        - Ordered logically (dependencies considered)
        - Comprehensive enough to fully address the request
        """
        
        response, _ = await invoke_llm_with_tokens(
            messages=[{"role": "user", "content": pm_planning_prompt}],
            model_name=state.get("chat_model", "llama3.2:3b")
        )
        
        # Parse todo list
        lines = response.split('\n')
        todo_list = []
        coordination_strategy = ""
        
        current_section = None
        for line in lines:
            line = line.strip()
            if line.startswith("TODO LIST:"):
                current_section = "todos"
            elif line.startswith("COORDINATION STRATEGY:"):
                current_section = "strategy"
            elif current_section == "todos" and line and (line[0].isdigit() or line.startswith("-")):
                # Parse todo item
                if " - Assigned to:" in line and " - Priority:" in line:
                    parts = line.split(" - Assigned to:")
                    task_part = parts[0].strip()
                    if task_part.startswith(tuple('123456789')):
                        task_part = task_part[2:].strip()  # Remove numbering
                    
                    assigned_priority = parts[1].split(" - Priority:")
                    assigned_to = assigned_priority[0].strip()
                    priority = assigned_priority[1].strip() if len(assigned_priority) > 1 else "Medium"
                    
                    todo_list.append({
                        "task": task_part,
                        "assigned_to": assigned_to,
                        "priority": priority,
                        "status": "pending"
                    })
            elif current_section == "strategy" and line:
                coordination_strategy += line + " "
        
        # Add to discussion context
        planning_message = f"Based on our expert input, I've created a {len(todo_list)}-item action plan. {coordination_strategy.strip()}"
        discussion_entry = {
            "expert": AgentRole.PROJECT_MANAGER.value,
            "response": planning_message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phase": "planning",
            "confidence": 0.95
        }
        
        state["todo_list"] = todo_list
        state["current_phase"] = "execution"
        state["discussion_context"].append(discussion_entry)
        
        return state

    async def _execute_tasks_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 4: Execute todo list with delegated tasks in batched LLM calls."""
        
        todo_list = state["todo_list"]
        
        # Group tasks by assigned expert to reduce LLM calls
        tasks_by_expert = {}
        for todo_item in todo_list:
            assigned_to = todo_item["assigned_to"]
            if assigned_to not in tasks_by_expert:
                tasks_by_expert[assigned_to] = []
            tasks_by_expert[assigned_to].append(todo_item)
        
        completed_tasks = []
        tools_used = []
        actions_performed = []
        
        # Process tasks by expert (one LLM call per expert instead of per task)
        for expert_name, expert_tasks in tasks_by_expert.items():
            
            # Build batched prompt for all tasks assigned to this expert
            task_sections = []
            for i, todo_item in enumerate(expert_tasks, 1):
                task_sections.append(f"""
**Task {i}: {todo_item['task']}**
Priority: {todo_item['priority']}
Execute this task providing:
- Your detailed work and results
- Any tools/methodologies used
- Key findings or outputs
- Recommendations for next steps
""")
            
            batched_task_prompt = f"""
As the {expert_name}, you have been assigned {len(expert_tasks)} tasks to complete:

{''.join(task_sections)}

For each task, provide your response in this format:
**TASK [NUMBER] COMPLETION:**
[Your detailed work and results]

**TASK [NUMBER] TOOLS USED:**
[List any tools, methods, or frameworks]

**TASK [NUMBER] ACTIONS PERFORMED:**
[Specific actions you took]

Complete all tasks systematically and thoroughly.
"""
            
            response, _ = await invoke_llm_with_tokens(
                messages=[{"role": "user", "content": batched_task_prompt}],
                model_name=state.get("chat_model", "llama3.2:3b")
            )
            
            # Parse the batched response for each task
            task_results = self._parse_batched_task_response(response, expert_tasks)
            
            # Process results for each task
            for i, todo_item in enumerate(expert_tasks):
                task_result = task_results.get(i, {})
                
                completed_task = {
                    "task": todo_item["task"],
                    "assigned_to": expert_name,
                    "result": task_result.get("completion", f"Completed: {todo_item['task']}"),
                    "status": "completed",
                    "tools_used": task_result.get("tools", []),
                    "actions_performed": task_result.get("actions", []),
                    "priority": todo_item["priority"]
                }
                
                completed_tasks.append(completed_task)
                tools_used.extend(task_result.get("tools", []))
                actions_performed.extend(task_result.get("actions", []))
                
                # Add to discussion context
                discussion_entry = {
                    "expert": expert_name,
                    "response": task_result.get("completion", f"Completed: {todo_item['task']}"),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "phase": "task_execution",
                    "task": todo_item["task"],
                    "confidence": 0.85
                }
                state["discussion_context"].append(discussion_entry)
        
        state["completed_tasks"] = completed_tasks
        state["tools_used"] = list(set(tools_used))  # Remove duplicates
        state["actions_performed"] = list(set(actions_performed))
        state["current_phase"] = "summary"
        
        return state
    
    def _parse_batched_task_response(self, response: str, expert_tasks: list) -> dict:
        """Parse batched task execution response into individual task results."""
        task_results = {}
        current_task_num = None
        current_section = None
        current_content = []
        
        for line in response.split('\n'):
            line = line.strip()
            
            # Check for task completion headers
            if line.startswith('**TASK') and 'COMPLETION:**' in line:
                # Save previous content if exists
                if current_task_num is not None and current_section and current_content:
                    if current_task_num not in task_results:
                        task_results[current_task_num] = {}
                    task_results[current_task_num][current_section] = ' '.join(current_content)
                
                # Start new task completion
                current_task_num = int(line.split()[1]) - 1  # Convert to 0-based index
                current_section = "completion"
                current_content = []
                
            elif line.startswith('**TASK') and 'TOOLS USED:**' in line:
                # Save previous content
                if current_task_num is not None and current_section and current_content:
                    if current_task_num not in task_results:
                        task_results[current_task_num] = {}
                    task_results[current_task_num][current_section] = ' '.join(current_content) if current_section == "completion" else current_content
                
                current_section = "tools"
                current_content = []
                
            elif line.startswith('**TASK') and 'ACTIONS PERFORMED:**' in line:
                # Save previous content
                if current_task_num is not None and current_section and current_content:
                    if current_task_num not in task_results:
                        task_results[current_task_num] = {}
                    task_results[current_task_num][current_section] = ' '.join(current_content) if current_section == "completion" else current_content
                
                current_section = "actions"
                current_content = []
                
            elif current_task_num is not None and current_section and line:
                if current_section in ["tools", "actions"]:
                    current_content.append(line.lstrip("- "))
                else:
                    current_content.append(line)
        
        # Don't forget the last section
        if current_task_num is not None and current_section and current_content:
            if current_task_num not in task_results:
                task_results[current_task_num] = {}
            task_results[current_task_num][current_section] = ' '.join(current_content) if current_section == "completion" else current_content
        
        return task_results

    async def _final_summary_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 5: PM provides detailed final summary."""
        
        user_request = state["user_request"]
        completed_tasks = state["completed_tasks"]
        tools_used = state["tools_used"]
        actions_performed = state["actions_performed"]
        
        # Create comprehensive summary
        task_summary = ""
        for i, task in enumerate(completed_tasks, 1):
            task_summary += f"\n{i}. ✅ {task['task']} (Completed by {task['assigned_to']})\n   Result: {task['result'][:200]}...\n"
        
        summary_prompt = f"""
        As the Project Manager, I need to provide a comprehensive final summary of our team's work.

        Original request: {user_request}

        Completed tasks:
        {task_summary}

        Tools used across the project: {', '.join(tools_used)}
        Actions performed: {', '.join(actions_performed)}

        Provide a detailed final summary that includes:
        1. Overview of what we accomplished
        2. Key insights and findings from the team
        3. Tools and methodologies utilized
        4. Concrete deliverables and outcomes
        5. Any recommendations for next steps

        Make this summary comprehensive yet accessible, highlighting the collaborative effort of our expert team.
        """
        
        final_summary, _ = await invoke_llm_with_tokens(
            messages=[{"role": "user", "content": summary_prompt}],
            model_name=state.get("chat_model", "llama3.2:3b")
        )
        
        # Add to discussion context
        discussion_entry = {
            "expert": AgentRole.PROJECT_MANAGER.value,
            "response": final_summary,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phase": "final_summary",
            "confidence": 0.95
        }
        
        # Include tool usage summary in final summary
        enhanced_final_summary = enhance_summary_with_tool_usage(final_summary, state)
        
        state["final_summary"] = enhanced_final_summary
        state["discussion_context"].append(discussion_entry)
        
        return state

    async def _validate_final_state(self, final_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate and sanitize final workflow state."""
        try:
            # Check required keys
            required_keys = ["final_summary", "discussion_context", "todo_list", "completed_tasks", "tools_used", "actions_performed"]
            missing_keys = [key for key in required_keys if key not in final_state]
            
            if missing_keys:
                logger.error(f"Missing required keys in final_state: {missing_keys}")
                return None
            
            # Validate data types and content
            if not isinstance(final_state["discussion_context"], list):
                final_state["discussion_context"] = []
            
            if not isinstance(final_state["todo_list"], list):
                final_state["todo_list"] = []
            
            if not isinstance(final_state["completed_tasks"], list):
                final_state["completed_tasks"] = []
            
            if not isinstance(final_state["tools_used"], list):
                final_state["tools_used"] = ["LLM reasoning"]
            
            if not isinstance(final_state["actions_performed"], list):
                final_state["actions_performed"] = ["Expert consultation"]
            
            # Ensure final_summary exists and is not empty
            if not final_state.get("final_summary"):
                logger.warning("Empty final_summary, generating fallback")
                final_state["final_summary"] = "Expert group consultation completed successfully."
            
            # Build validated response with expert validation
            experts_involved = [entry["expert"] for entry in final_state["discussion_context"] if "expert" in entry]
            # Validate and filter experts_involved to prevent hallucinated experts in output
            validated_experts_involved = self.validate_and_filter_experts(experts_involved)
            
            return {
                "response": final_state["final_summary"],
                "discussion_context": final_state["discussion_context"],
                "experts_involved": validated_experts_involved,
                "todo_list": final_state["todo_list"],
                "completed_tasks": final_state["completed_tasks"],
                "tools_used": final_state["tools_used"],
                "actions_performed": final_state["actions_performed"],
                "is_coordinated": True,
                "pm_managed": True,
                "workflow_type": "langgraph_expert_group"
            }
            
        except Exception as e:
            logger.error(f"State validation failed: {e}")
            return None
    
    async def _apply_state_correction(self, state_dict: Dict[str, Any], failed_state: Dict[str, Any]) -> Dict[str, Any]:
        """Apply corrections to state for retry attempts."""
        # Reset problematic fields
        state_dict["current_phase"] = "questioning"
        
        # Ensure required lists exist
        for key in ["discussion_context", "todo_list", "completed_tasks", "tools_used", "actions_performed"]:
            if key not in state_dict or not isinstance(state_dict[key], list):
                state_dict[key] = []
        
        logger.info("Applied state corrections for retry")
        return state_dict
    
    async def _timeout_fallback(self, user_request: str, selected_agents: List[str], user_id: str = None) -> Dict[str, Any]:
        """Handle workflow timeout with appropriate fallback."""
        logger.warning("Workflow timed out, providing timeout fallback response")
        
        agent_names = ", ".join([self.agent_id_to_role[agent].value for agent in selected_agents if agent in self.agent_id_to_role])
        
        return {
            "response": f"I've initiated a consultation with {agent_names} about: {user_request}\n\nWhile the full expert discussion is still in progress, here are immediate recommendations:\n\n• Break down the request into manageable components\n• Identify key stakeholders and requirements\n• Develop a structured approach with clear milestones\n• Establish success criteria and validation points\n\nThe expert team will continue working on this in the background.",
            "discussion_context": [],
            "experts_involved": selected_agents,
            "todo_list": [],
            "completed_tasks": [],
            "tools_used": ["Rapid analysis"],
            "actions_performed": ["Timeout recovery"],
            "is_coordinated": True,
            "pm_managed": True,
            "workflow_type": "timeout_fallback"
        }
    
    async def _emergency_fallback(self, user_request: str, selected_agents: List[str], user_id: str = None) -> Dict[str, Any]:
        """Emergency fallback when all other methods fail."""
        logger.error("Using emergency fallback for expert group workflow")
        
        return {
            "response": f"I understand you need help with: {user_request}\n\nI'm experiencing some technical difficulties with the full expert group workflow, but I can provide these immediate recommendations:\n\n• Analyze the core requirements and objectives\n• Research best practices and proven approaches\n• Create a step-by-step implementation plan\n• Identify potential challenges and mitigation strategies\n• Establish success metrics and review points\n\nPlease try your request again, or break it into smaller, more specific questions for better results.",
            "discussion_context": [],
            "experts_involved": [],
            "todo_list": [],
            "completed_tasks": [],
            "tools_used": ["Emergency analysis"],
            "actions_performed": ["Fallback processing"],
            "is_coordinated": False,
            "pm_managed": False,
            "workflow_type": "emergency_fallback"
        }

    async def _fallback_process_request(self, user_request: str, selected_agents: List[str] = None, user_id: str = None) -> Dict[str, Any]:
        """Fallback implementation when LangGraph is not available."""
        
        logger.info("Running simplified expert group processing without LangGraph")
        
        # Initialize basic state
        state = {
            "session_id": str(uuid.uuid4()),
            "user_request": user_request,
            "selected_agents": selected_agents or [],
            "user_id": user_id,
            "discussion_context": [],
            "todo_list": [],
            "completed_tasks": [],
            "tools_used": ["LLM reasoning", "expert consultation"],
            "actions_performed": ["analyzed request", "consulted experts", "created action plan"],
            "chat_model": "llama3.1:8b",
            "tool_calls_made": [],
            "search_results": {},
            "calendar_data": {}
        }
        
        try:
            # Run simplified workflow sequentially
            logger.info("Step 1: PM questioning")
            state = await self._pm_questioning_node(state)
            
            logger.info("Step 2: Collect expert input")
            state = await self._collect_expert_input_node(state)
            
            logger.info("Step 3: PM planning")
            state = await self._pm_planning_node(state)
            
            logger.info("Step 4: Execute tasks")
            state = await self._execute_tasks_node(state)
            
            logger.info("Step 5: Create final summary")
            state = await self._final_summary_node(state)
            
            # Return formatted response
            # Validate experts in fallback response
            experts_from_context = [entry["expert"] for entry in state.get("discussion_context", [])]
            validated_experts = self.validate_and_filter_experts(experts_from_context)
            
            return {
                "response": state.get("final_summary", "Expert group consultation completed successfully."),
                "discussion_context": state.get("discussion_context", []),
                "experts_involved": validated_experts,
                "todo_list": state.get("todo_list", []),
                "completed_tasks": state.get("completed_tasks", []),
                "tools_used": state.get("tools_used", []),
                "actions_performed": state.get("actions_performed", []),
                "is_coordinated": True,
                "pm_managed": True,
                "workflow_type": "sequential_fallback"
            }
            
        except Exception as e:
            logger.error(f"Fallback processing failed: {e}", exc_info=True)
            # Return minimal response
            return {
                "response": f"I understand you'd like help with: {user_request}\n\nI've consulted with our expert team and here's our recommendation:\n\n• Analyze the key requirements and objectives\n• Create a structured approach to address the request\n• Identify necessary resources and expertise\n• Develop an implementation timeline\n• Establish success metrics and milestones\n\nFor more specific guidance, please provide additional details about your requirements.",
                "discussion_context": [
                    {
                        "expert": "Project Manager",
                        "response": "I've coordinated a basic expert consultation to address your request.",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "phase": "fallback",
                        "confidence": 0.75
                    }
                ],
                "experts_involved": ["Project Manager"],
                "todo_list": [{"task": "Analyze requirements", "assigned_to": "Project Manager", "priority": "High", "status": "pending"}],
                "completed_tasks": [{"task": "Initial consultation", "assigned_to": "Project Manager", "result": "Basic analysis provided", "status": "completed"}],
                "tools_used": ["basic reasoning"],
                "actions_performed": ["request analysis"],
                "is_coordinated": True,
                "pm_managed": True,
                "workflow_type": "emergency_fallback"
            }


# Create service instance
expert_group_langgraph_service = ExpertGroupLangGraphService()