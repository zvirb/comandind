"""
Helios PM Orchestration Engine - Project Manager-led multi-agent orchestration
Implements true task delegation with @mention system and concurrent expert processing
"""

import json
import logging
import uuid
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator, Tuple
from datetime import datetime, timezone
from enum import Enum
import re

from pydantic import BaseModel, Field

from worker.services.agent_llm_manager import AgentLLMManager
from worker.services.agent_api_abstraction import AgentAPIAbstraction
from shared.services.agent_configuration_service import AgentConfigurationService
# TEMPORARILY DISABLED: Tables don't exist yet due to incomplete migration
# from shared.database.models.helios_multi_agent_models import TaskStatus, AgentStatus

# Temporary local enums to replace the database model imports
class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

class AgentStatus(str, Enum):
    ONLINE = "online"
    WORKING = "working"
    IDLE = "idle"
    OFFLINE = "offline"
    ERROR = "error"
    OVERLOADED = "overloaded"

from shared.utils.streaming_utils import sanitize_content
from worker.services.ollama_service import invoke_llm_with_tokens

logger = logging.getLogger(__name__)


class OrchestrationType(str, Enum):
    """Types of PM orchestration actions."""
    TASK_ANALYSIS = "task_analysis"
    TASK_DELEGATION = "task_delegation"
    PROGRESS_CHECK = "progress_check"
    SYNTHESIS_REQUEST = "synthesis_request"
    QUALITY_CHECK = "quality_check"


class HeliosAgentRole(str, Enum):
    """Available expert agents in Helios framework."""
    PROJECT_MANAGER = "Project Manager"
    TECHNICAL_EXPERT = "Technical Expert"
    BUSINESS_ANALYST = "Business Analyst"
    CREATIVE_DIRECTOR = "Creative Director"
    RESEARCH_SPECIALIST = "Research Specialist"
    PLANNING_EXPERT = "Planning Expert"
    SOCRATIC_EXPERT = "Socratic Expert"
    WELLBEING_COACH = "Wellbeing Coach"
    PERSONAL_ASSISTANT = "Personal Assistant"
    DATA_ANALYST = "Data Analyst"
    OUTPUT_FORMATTER = "Output Formatter"
    QUALITY_ASSURANCE = "Quality Assurance"


class TaskDelegation(BaseModel):
    """Model for PM task delegation."""
    task_id: str
    target_agent: str
    directive: str
    priority: int = 1
    dependencies: List[str] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    response: Optional[str] = None
    
    
class ExpertResponse(BaseModel):
    """Model for expert agent response."""
    expert_id: str
    task_id: str
    response_content: str
    confidence_score: float = 0.0
    tool_calls_made: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HeliosOrchestrationState(BaseModel):
    """State for Helios PM orchestration workflow."""
    # Session info
    session_id: str
    user_request: str
    user_id: Optional[str] = None
    
    # Orchestration state
    orchestration_type: OrchestrationType = OrchestrationType.TASK_ANALYSIS
    pm_analysis: Optional[str] = None
    task_delegations: List[TaskDelegation] = Field(default_factory=list)
    expert_responses: List[ExpertResponse] = Field(default_factory=list)
    
    # Agent management
    available_agents: List[str] = Field(default_factory=list)
    agent_status: Dict[str, AgentStatus] = Field(default_factory=dict)
    
    # Synthesis and output
    synthesis_content: Optional[str] = None
    qa_review: Optional[str] = None
    final_output: Optional[str] = None
    
    # Workflow control
    orchestration_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    chat_model: str = "llama3.1:8b"


class HeliosPMOrchestrationEngine:
    """Project Manager orchestration engine for Helios multi-agent framework."""
    
    def __init__(self):
        self.agent_manager = AgentLLMManager()
        self.api_abstraction = AgentAPIAbstraction()
        self.config_service = AgentConfigurationService()
        
        # Agent role mapping
        self.agent_id_to_role = {
            "project_manager": HeliosAgentRole.PROJECT_MANAGER,
            "technical_expert": HeliosAgentRole.TECHNICAL_EXPERT,
            "business_analyst": HeliosAgentRole.BUSINESS_ANALYST,
            "creative_director": HeliosAgentRole.CREATIVE_DIRECTOR,
            "research_specialist": HeliosAgentRole.RESEARCH_SPECIALIST,
            "planning_expert": HeliosAgentRole.PLANNING_EXPERT,
            "socratic_expert": HeliosAgentRole.SOCRATIC_EXPERT,
            "wellbeing_coach": HeliosAgentRole.WELLBEING_COACH,
            "personal_assistant": HeliosAgentRole.PERSONAL_ASSISTANT,
            "data_analyst": HeliosAgentRole.DATA_ANALYST,
            "output_formatter": HeliosAgentRole.OUTPUT_FORMATTER,
            "quality_assurance": HeliosAgentRole.QUALITY_ASSURANCE
        }
        
        # Reverse mapping for quick lookups
        self.role_to_agent_id = {v: k for k, v in self.agent_id_to_role.items()}
        
    async def initialize_orchestration(self, user_request: str, user_id: Optional[str] = None) -> HeliosOrchestrationState:
        """Initialize PM orchestration state."""
        # Get available agents with configured LLMs
        available_agents = await self._get_available_agents(user_id)
        
        # Initialize agent status
        agent_status = {agent: AgentStatus.IDLE for agent in available_agents}
        agent_status["project_manager"] = AgentStatus.ONLINE
        
        return HeliosOrchestrationState(
            session_id=str(uuid.uuid4()),
            user_request=user_request,
            user_id=user_id,
            available_agents=available_agents,
            agent_status=agent_status
        )
        
    async def _get_available_agents(self, user_id: Optional[str] = None) -> List[str]:
        """Get list of available agents with configured LLMs."""
        # Get all agent configurations
        configs = await self.config_service.get_all_agent_configurations(user_id)
        
        # Filter agents that have LLM assignments
        available = []
        for config in configs:
            if config.assigned_llm:
                available.append(config.agent_id)
                
        # Always include PM if not already present
        if "project_manager" not in available:
            available.insert(0, "project_manager")
            
        return available
        
    def _parse_at_mentions(self, text: str) -> List[Tuple[str, str]]:
        """Parse @mentions from PM directives."""
        # Pattern to match @[Agent Name] directive text
        pattern = r'@\[([^\]]+)\]\s*([^@]+)'
        matches = re.findall(pattern, text)
        
        delegations = []
        for agent_name, directive in matches:
            # Map agent name to agent_id
            for agent_id, role in self.agent_id_to_role.items():
                if role.value == agent_name or agent_name.lower() in agent_id:
                    delegations.append((agent_id, directive.strip()))
                    break
                    
        return delegations
        
    async def run_pm_orchestration(self, state: HeliosOrchestrationState, 
                                   stream_callback: Optional[Any] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """Run PM orchestration workflow with streaming support."""
        try:
            # Phase 1: PM Task Analysis
            logger.info(f"Starting PM orchestration for session {state.session_id}")
            yield self._create_phase_update("pm_analysis", "Project Manager analyzing request...")
            
            state.orchestration_type = OrchestrationType.TASK_ANALYSIS
            analysis_result = await self._pm_task_analysis(state)
            state.pm_analysis = analysis_result
            
            yield self._create_content_update("pm_analysis", analysis_result, "project_manager")
            
            # Phase 2: Task Delegation
            yield self._create_phase_update("task_delegation", "Delegating tasks to expert agents...")
            
            state.orchestration_type = OrchestrationType.TASK_DELEGATION
            delegations = await self._pm_task_delegation(state)
            state.task_delegations = delegations
            
            for delegation in delegations:
                yield self._create_delegation_update(delegation)
                
            # Phase 3: Concurrent Expert Processing
            yield self._create_phase_update("expert_processing", "Experts working on assigned tasks...")
            
            # Process experts concurrently
            expert_tasks = []
            for delegation in state.task_delegations:
                if delegation.target_agent in state.available_agents:
                    state.agent_status[delegation.target_agent] = AgentStatus.WORKING
                    expert_tasks.append(self._process_expert_task(state, delegation))
                    
            # Gather all expert responses
            responses = await asyncio.gather(*expert_tasks, return_exceptions=True)
            
            for response in responses:
                if isinstance(response, ExpertResponse):
                    state.expert_responses.append(response)
                    state.agent_status[response.expert_id] = AgentStatus.IDLE
                    yield self._create_expert_response_update(response)
                    
            # Phase 4: Synthesis
            yield self._create_phase_update("synthesis", "Synthesizing expert responses...")
            
            state.orchestration_type = OrchestrationType.SYNTHESIS_REQUEST
            synthesis = await self._synthesize_responses(state)
            state.synthesis_content = synthesis
            
            yield self._create_content_update("synthesis", synthesis, "output_formatter")
            
            # Phase 5: Quality Assurance
            yield self._create_phase_update("quality_assurance", "Performing final quality review...")
            
            state.orchestration_type = OrchestrationType.QUALITY_CHECK
            qa_review = await self._quality_assurance_review(state)
            state.qa_review = qa_review
            state.final_output = qa_review  # QA provides the final polished output
            
            yield self._create_content_update("final_output", state.final_output, "quality_assurance")
            
            # Complete
            yield self._create_phase_update("complete", "Expert group collaboration complete!")
            
        except Exception as e:
            logger.error(f"Error in PM orchestration: {str(e)}", exc_info=True)
            yield self._create_error_update(str(e))
            
    async def _pm_task_analysis(self, state: HeliosOrchestrationState) -> str:
        """PM analyzes user request and plans approach."""
        prompt = f"""You are the Project Manager leading a team of expert agents. 
Analyze this user request and determine which experts should be involved and what specific tasks to delegate.

User Request: {state.user_request}

Available Experts:
{self._format_available_experts(state.available_agents)}

Provide a clear analysis of:
1. What the user is asking for
2. Which experts should be involved
3. What specific sub-tasks need to be delegated
4. The logical order of operations

Your analysis will guide the task delegation phase."""

        try:
            # Use PM's configured LLM
            response = await self.agent_manager.get_agent_response(
                agent_type="project_manager",
                prompt=prompt,
                temperature=0.7
            )
            return response
        except Exception as e:
            logger.error(f"Error in PM task analysis: {str(e)}")
            return f"I'll analyze this request and coordinate our expert team to provide a comprehensive response."
            
    async def _pm_task_delegation(self, state: HeliosOrchestrationState) -> List[TaskDelegation]:
        """PM creates specific task delegations with @mentions."""
        prompt = f"""Based on your analysis, create specific task delegations for the expert team.
Use @mentions to assign tasks to specific experts.

Your Analysis:
{state.pm_analysis}

Format your delegations as:
@[Expert Name] Specific task or question for this expert

For example:
@[Technical Expert] Assess the technical feasibility of implementing a real-time chat system
@[Business Analyst] Analyze the cost implications and ROI of the proposed solution

Create clear, specific delegations for each expert that should be involved."""

        try:
            response = await self.agent_manager.get_agent_response(
                agent_type="project_manager",
                prompt=prompt,
                temperature=0.7
            )
            
            # Parse @mentions from response
            delegations = self._parse_at_mentions(response)
            
            # Create TaskDelegation objects
            task_delegations = []
            for i, (agent_id, directive) in enumerate(delegations):
                task_delegations.append(TaskDelegation(
                    task_id=f"task_{i+1}",
                    target_agent=agent_id,
                    directive=directive,
                    priority=i+1
                ))
                
            return task_delegations
            
        except Exception as e:
            logger.error(f"Error in PM task delegation: {str(e)}")
            # Fallback delegations
            return [TaskDelegation(
                task_id="task_1",
                target_agent="research_specialist",
                directive="Please provide relevant information about the user's request"
            )]
            
    async def _process_expert_task(self, state: HeliosOrchestrationState, 
                                    delegation: TaskDelegation) -> ExpertResponse:
        """Process individual expert task using their configured LLM."""
        try:
            # Build expert prompt
            expert_role = self.agent_id_to_role.get(delegation.target_agent, "Expert")
            
            prompt = f"""You are the {expert_role.value} on an expert team.
The Project Manager has assigned you this task:

{delegation.directive}

Context from user request: {state.user_request}

Provide your expert response focusing on your area of specialization."""

            # Get response using agent's configured LLM
            response = await self.agent_manager.get_agent_response(
                agent_type=delegation.target_agent,
                prompt=prompt,
                temperature=0.7
            )
            
            # Mark task as completed
            delegation.status = TaskStatus.COMPLETED
            delegation.response = response
            
            return ExpertResponse(
                expert_id=delegation.target_agent,
                task_id=delegation.task_id,
                response_content=response,
                confidence_score=0.9
            )
            
        except Exception as e:
            logger.error(f"Error processing expert task for {delegation.target_agent}: {str(e)}")
            return ExpertResponse(
                expert_id=delegation.target_agent,
                task_id=delegation.task_id,
                response_content=f"I encountered an issue processing this task: {str(e)}",
                confidence_score=0.3
            )
            
    async def _synthesize_responses(self, state: HeliosOrchestrationState) -> str:
        """Output Formatter synthesizes all expert responses."""
        # Prepare expert responses summary
        responses_text = ""
        for response in state.expert_responses:
            expert_role = self.agent_id_to_role.get(response.expert_id, "Expert")
            responses_text += f"\n\n{expert_role.value}:\n{response.response_content}"
            
        prompt = f"""You are the Output Formatter responsible for synthesizing expert responses.
Create a comprehensive, well-structured response that integrates all expert inputs.

User Request: {state.user_request}

Expert Responses:{responses_text}

Synthesize these expert inputs into a cohesive, well-organized response that:
1. Addresses the user's request completely
2. Integrates insights from all experts
3. Presents information in a clear, logical structure
4. Highlights key recommendations and action items"""

        try:
            response = await self.agent_manager.get_agent_response(
                agent_type="output_formatter",
                prompt=prompt,
                temperature=0.7
            )
            return response
        except Exception as e:
            logger.error(f"Error in synthesis: {str(e)}")
            return "Here is a summary of the expert team's findings..."
            
    async def _quality_assurance_review(self, state: HeliosOrchestrationState) -> str:
        """Quality Assurance performs final review and polish."""
        prompt = f"""You are the Quality Assurance specialist performing the final review.
Review the synthesized response and ensure it meets quality standards.

User Request: {state.user_request}

Synthesized Response:
{state.synthesis_content}

Perform a quality review checking for:
1. Completeness - Does it fully address the user's request?
2. Accuracy - Is the information correct and well-supported?
3. Clarity - Is it easy to understand and well-organized?
4. Professionalism - Is the tone appropriate and polished?

Provide the final, polished response ready for the user."""

        try:
            response = await self.agent_manager.get_agent_response(
                agent_type="quality_assurance",
                prompt=prompt,
                temperature=0.5
            )
            return response
        except Exception as e:
            logger.error(f"Error in QA review: {str(e)}")
            return state.synthesis_content or "The expert team has completed their analysis."
            
    def _format_available_experts(self, agents: List[str]) -> str:
        """Format available experts list."""
        experts = []
        for agent_id in agents:
            if agent_id in self.agent_id_to_role:
                role = self.agent_id_to_role[agent_id]
                experts.append(f"- {role.value} (@{agent_id})")
        return "\n".join(experts)
        
    def _create_phase_update(self, phase: str, message: str) -> Dict[str, Any]:
        """Create phase update message."""
        return {
            "type": "phase_update",
            "phase": phase,
            "content": message,
            "metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        
    def _create_content_update(self, update_type: str, content: str, agent: str) -> Dict[str, Any]:
        """Create content update message."""
        return {
            "type": update_type,
            "content": sanitize_content(content),
            "metadata": {
                "agent": agent,
                "agent_role": self.agent_id_to_role.get(agent, "Expert").value,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        
    def _create_delegation_update(self, delegation: TaskDelegation) -> Dict[str, Any]:
        """Create task delegation update."""
        agent_role = self.agent_id_to_role.get(delegation.target_agent, "Expert")
        return {
            "type": "task_delegation",
            "content": f"Task assigned to {agent_role.value}: {delegation.directive}",
            "metadata": {
                "task_id": delegation.task_id,
                "target_agent": delegation.target_agent,
                "agent_role": agent_role.value,
                "priority": delegation.priority
            }
        }
        
    def _create_expert_response_update(self, response: ExpertResponse) -> Dict[str, Any]:
        """Create expert response update."""
        agent_role = self.agent_id_to_role.get(response.expert_id, "Expert")
        return {
            "type": "expert_response",
            "content": response.response_content,
            "metadata": {
                "expert_id": response.expert_id,
                "expert_role": agent_role.value,
                "task_id": response.task_id,
                "confidence": response.confidence_score,
                "timestamp": response.created_at.isoformat()
            }
        }
        
    def _create_error_update(self, error: str) -> Dict[str, Any]:
        """Create error update message."""
        return {
            "type": "error",
            "content": f"An error occurred during orchestration: {error}",
            "metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }