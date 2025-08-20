"""
Hybrid Expert Group LangGraph Service with Orchestration/Choreography Model

Enhances the existing expert group service with:
- Event-driven blackboard communication
- Consensus-building protocols
- Argumentation-based negotiation
- Dynamic leadership election
- Market-based task allocation
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
from worker.services.blackboard_integration_service import (
    blackboard_integration_service, EventType, Performative
)
from worker.services.consensus_building_service import (
    consensus_building_service, ConsensusPhase
)
from worker.services.expert_group_specialized_methods import (
    collect_expert_input_with_tools,
    enhance_summary_with_tool_usage
)

logger = logging.getLogger(__name__)


class OrchestrationMode(str, Enum):
    """Orchestration modes for different workflow phases."""
    CHOREOGRAPHY = "choreography"  # Decentralized agent contributions
    ORCHESTRATION = "orchestration"  # Centralized PM coordination
    HYBRID = "hybrid"  # Mix of both based on context
    CONSENSUS = "consensus"  # Consensus-building mode
    DEBATE = "debate"  # Structured argumentation mode


class LeadershipRole(str, Enum):
    """Dynamic leadership roles that agents can assume."""
    PROJECT_MANAGER = "project_manager"
    DOMAIN_LEADER = "domain_leader"
    CONSENSUS_FACILITATOR = "consensus_facilitator"
    CONFLICT_MEDIATOR = "conflict_mediator"
    QUALITY_VALIDATOR = "quality_validator"


class TaskAllocationMethod(str, Enum):
    """Methods for task allocation."""
    CONTRACT_NET = "contract_net"  # Market-based bidding
    EXPERTISE_MATCH = "expertise_match"  # Match to expertise
    LOAD_BALANCE = "load_balance"  # Balance workload
    CONSENSUS_ASSIGN = "consensus_assign"  # Consensus-based assignment


class HybridExpertGroupState(BaseModel):
    """Enhanced state object for hybrid expert group workflow."""
    # Input data
    session_id: Optional[str] = None
    user_request: str = ""
    selected_agents: List[str] = Field(default_factory=list)
    
    # Orchestration control
    orchestration_mode: OrchestrationMode = OrchestrationMode.HYBRID
    current_leader: Optional[str] = None
    leadership_history: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Blackboard state
    blackboard_events: List[Dict[str, Any]] = Field(default_factory=list)
    agent_contributions: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    contribution_opportunities: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    
    # Consensus building
    active_consensus_sessions: List[str] = Field(default_factory=list)
    consensus_decisions: List[Dict[str, Any]] = Field(default_factory=list)
    argumentation_history: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Task allocation
    allocation_method: TaskAllocationMethod = TaskAllocationMethod.CONTRACT_NET
    task_bids: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    allocated_tasks: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Phase management
    pm_questions: Dict[str, str] = Field(default_factory=dict)
    expert_inputs: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    todo_list: List[Dict[str, Any]] = Field(default_factory=list)
    completed_tasks: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Tool Usage Tracking
    tool_calls_made: List[Dict[str, Any]] = Field(default_factory=list)
    search_results: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    calendar_data: Dict[str, Any] = Field(default_factory=dict)
    
    # User context for tool usage
    user_id: Optional[str] = None
    
    # Final output
    final_summary: str = ""
    tools_used: List[str] = Field(default_factory=list)
    actions_performed: List[str] = Field(default_factory=list)
    
    # Workflow control
    current_phase: str = "initialization"
    discussion_context: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Quality and validation
    quality_checkpoints: List[Dict[str, Any]] = Field(default_factory=list)
    validation_results: Dict[str, Any] = Field(default_factory=dict)
    
    # Configuration
    chat_model: str = "llama3.1:8b"


class HybridExpertGroupLangGraphService:
    """
    Enhanced expert group service implementing hybrid orchestration/choreography model
    with consensus building and argumentation-based negotiation.
    """

    def __init__(self):
        self.agent_id_to_role = {
            "project_manager": "Project Manager",
            "technical_expert": "Technical Expert",
            "business_analyst": "Business Analyst",
            "creative_director": "Creative Director",
            "research_specialist": "Research Specialist",
            "planning_expert": "Planning Expert",
            "socratic_expert": "Socratic Expert",
            "wellbeing_coach": "Wellbeing Coach",
            "personal_assistant": "Personal Assistant",
            "data_analyst": "Data Analyst",
            "output_formatter": "Output Formatter",
            "quality_assurance": "Quality Assurance"
        }
        
        self.valid_expert_names = set(self.agent_id_to_role.values())
        self.workflow_graph = self._build_workflow_graph() if LANGGRAPH_AVAILABLE else None
        
        # Agent expertise areas for contribution detection
        self.agent_expertise = {
            "technical_expert": ["programming", "architecture", "technical", "code", "development"],
            "business_analyst": ["business", "requirements", "analysis", "process", "strategy"],
            "research_specialist": ["research", "data", "investigation", "analysis", "evidence"],
            "creative_director": ["design", "creative", "user experience", "branding", "visual"],
            "planning_expert": ["planning", "project", "timeline", "scheduling", "coordination"],
            "quality_assurance": ["quality", "testing", "validation", "verification", "standards"],
            "data_analyst": ["data", "analytics", "metrics", "statistics", "reporting"],
            "personal_assistant": ["calendar", "scheduling", "organization", "productivity"]
        }

    def _build_workflow_graph(self):
        """Build enhanced LangGraph workflow with hybrid orchestration."""
        
        if not LANGGRAPH_AVAILABLE:
            logger.warning("LangGraph not available, workflow will use sequential processing")
            return None
        
        workflow = StateGraph(Dict[str, Any])
        
        # Core workflow nodes
        workflow.add_node("initialize_hybrid_workflow", self._initialize_hybrid_workflow_node)
        workflow.add_node("detect_contribution_opportunities", self._detect_contribution_opportunities_node)
        workflow.add_node("elect_dynamic_leader", self._elect_dynamic_leader_node)
        workflow.add_node("coordinate_agent_contributions", self._coordinate_agent_contributions_node)
        workflow.add_node("facilitate_consensus_building", self._facilitate_consensus_building_node)
        workflow.add_node("conduct_argumentation", self._conduct_argumentation_node)
        workflow.add_node("allocate_tasks_market_based", self._allocate_tasks_market_based_node)
        workflow.add_node("validate_and_synthesize", self._validate_and_synthesize_node)
        workflow.add_node("generate_final_output", self._generate_final_output_node)
        
        # Define workflow flow
        workflow.set_entry_point("initialize_hybrid_workflow")
        workflow.add_edge("initialize_hybrid_workflow", "detect_contribution_opportunities")
        workflow.add_edge("detect_contribution_opportunities", "elect_dynamic_leader")
        workflow.add_edge("elect_dynamic_leader", "coordinate_agent_contributions")
        workflow.add_edge("coordinate_agent_contributions", "facilitate_consensus_building")
        workflow.add_edge("facilitate_consensus_building", "conduct_argumentation")
        workflow.add_edge("conduct_argumentation", "allocate_tasks_market_based")
        workflow.add_edge("allocate_tasks_market_based", "validate_and_synthesize")
        workflow.add_edge("validate_and_synthesize", "generate_final_output")
        workflow.add_edge("generate_final_output", END)
        
        return workflow.compile()

    async def process_request(
        self, 
        user_request: str, 
        selected_agents: List[str] = None, 
        user_id: str = None,
        orchestration_mode: OrchestrationMode = OrchestrationMode.HYBRID,
        consensus_required: bool = True
    ) -> Dict[str, Any]:
        """Process expert group request using hybrid orchestration model."""
        
        if not LANGGRAPH_AVAILABLE or self.workflow_graph is None:
            logger.info("Using fallback processing (LangGraph not available)")
            return await self._fallback_process_request(user_request, selected_agents, user_id)
        
        # Initialize state
        try:
            initial_state = HybridExpertGroupState(
                session_id=str(uuid.uuid4()),
                user_request=user_request,
                selected_agents=selected_agents or [],
                user_id=user_id,
                orchestration_mode=orchestration_mode
            )
            
            state_dict = initial_state.dict()
            
        except Exception as e:
            logger.error(f"Failed to initialize hybrid workflow state: {e}")
            return await self._emergency_fallback(user_request, selected_agents, user_id)
        
        # Run the enhanced workflow
        try:
            logger.info(f"Starting hybrid expert group workflow")
            config = RunnableConfig(recursion_limit=100)
            
            final_state = await asyncio.wait_for(
                self.workflow_graph.ainvoke(state_dict, config),
                timeout=300.0  # 5 minute timeout
            )
            
            # Handle Pydantic conversion
            if hasattr(final_state, 'dict'):
                final_state = final_state.dict()
            
            # Validate and return results
            return await self._validate_hybrid_final_state(final_state)
            
        except Exception as e:
            logger.error(f"Hybrid workflow execution failed: {e}")
            return await self._emergency_fallback(user_request, selected_agents, user_id)

    async def _initialize_hybrid_workflow_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize hybrid workflow with blackboard setup and agent registration."""
        
        logger.info("Initializing hybrid expert group workflow")
        
        session_id = state["session_id"]
        user_id = int(state["user_id"]) if state["user_id"] else 1
        selected_agents = state["selected_agents"]
        
        # Post initialization event to blackboard
        await blackboard_integration_service.post_blackboard_event(
            user_id=user_id,
            session_id=session_id,
            source_agent_id="hybrid_coordinator",
            agent_role="Hybrid Coordinator",
            event_type=EventType.GOAL_ESTABLISHED,
            performative=Performative.INFORM,
            event_payload={
                "user_request": state["user_request"],
                "selected_agents": selected_agents,
                "orchestration_mode": state["orchestration_mode"],
                "workflow_type": "hybrid_expert_group"
            }
        )
        
        # Register agents with blackboard
        for agent_id in selected_agents:
            if agent_id in self.agent_id_to_role:
                agent_role = self.agent_id_to_role[agent_id]
                
                # Store agent context
                await blackboard_integration_service.store_agent_context(
                    agent_id=agent_id,
                    agent_type="expert",
                    agent_role=agent_role,
                    user_id=user_id,
                    session_id=session_id,
                    context_key="registration",
                    context_value={
                        "registered_at": datetime.now(timezone.utc).isoformat(),
                        "expertise_areas": self.agent_expertise.get(agent_id, []),
                        "availability": "available",
                        "workload": 0
                    }
                )
        
        # Initialize agent contribution tracking
        state["agent_contributions"] = {agent_id: [] for agent_id in selected_agents}
        state["contribution_opportunities"] = {}
        state["current_phase"] = "opportunity_detection"
        
        # Add to discussion context
        discussion_entry = {
            "expert": "Hybrid Coordinator",
            "response": f"Initialized hybrid expert group workflow with {len(selected_agents)} agents",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phase": "initialization",
            "confidence": 1.0
        }
        state["discussion_context"] = [discussion_entry]
        
        logger.info(f"Hybrid workflow initialized with {len(selected_agents)} agents")
        return state

    async def _detect_contribution_opportunities_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Detect opportunities for agent contributions using blackboard analysis."""
        
        logger.info("Detecting contribution opportunities for agents")
        
        session_id = state["session_id"]
        user_id = int(state["user_id"]) if state["user_id"] else 1
        selected_agents = state["selected_agents"]
        
        # Detect opportunities for each agent
        opportunities_detected = {}
        
        for agent_id in selected_agents:
            if agent_id in self.agent_id_to_role:
                agent_role = self.agent_id_to_role[agent_id]
                expertise_areas = self.agent_expertise.get(agent_id, [])
                
                # Detect contribution opportunities
                opportunities = await blackboard_integration_service.detect_contribution_opportunities(
                    agent_id=agent_id,
                    agent_role=agent_role,
                    session_id=session_id,
                    user_id=user_id,
                    expertise_areas=expertise_areas
                )
                
                opportunities_detected[agent_id] = opportunities
                
                # Post opportunity detection event
                if opportunities:
                    await blackboard_integration_service.post_blackboard_event(
                        user_id=user_id,
                        session_id=session_id,
                        source_agent_id=agent_id,
                        agent_role=agent_role,
                        event_type=EventType.AGENT_CONTRIBUTION,
                        performative=Performative.INFORM,
                        event_payload={
                            "opportunities_found": len(opportunities),
                            "opportunity_types": [opp["opportunity_type"] for opp in opportunities],
                            "readiness_to_contribute": True
                        }
                    )
        
        state["contribution_opportunities"] = opportunities_detected
        state["current_phase"] = "leadership_election"
        
        # Add to discussion context
        total_opportunities = sum(len(opps) for opps in opportunities_detected.values())
        discussion_entry = {
            "expert": "Hybrid Coordinator",
            "response": f"Detected {total_opportunities} contribution opportunities across {len(opportunities_detected)} agents",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phase": "opportunity_detection",
            "confidence": 0.9
        }
        state["discussion_context"].append(discussion_entry)
        
        logger.info(f"Detected {total_opportunities} total contribution opportunities")
        return state

    async def _elect_dynamic_leader_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Elect dynamic leader based on context and expertise requirements."""
        
        logger.info("Conducting dynamic leadership election")
        
        user_request = state["user_request"]
        selected_agents = state["selected_agents"]
        contribution_opportunities = state["contribution_opportunities"]
        
        # Analyze request to determine leadership requirements
        leadership_prompt = f"""
        Analyze this request to determine the most appropriate leadership approach: {user_request}
        
        Available agents and their contribution opportunities:
        {json.dumps(contribution_opportunities, indent=2)}
        
        Agent roles available:
        {json.dumps({agent_id: self.agent_id_to_role.get(agent_id, "Unknown") for agent_id in selected_agents}, indent=2)}
        
        Determine:
        1. PRIMARY_LEADER: Which agent should lead this effort
        2. LEADERSHIP_STYLE: orchestration, choreography, or consensus
        3. REASONING: Why this agent and style
        4. BACKUP_LEADER: Alternative leader if needed
        
        Format as:
        PRIMARY_LEADER: [agent_id]
        LEADERSHIP_STYLE: [style]
        REASONING: [explanation]
        BACKUP_LEADER: [agent_id]
        """
        
        try:
            response, _ = await invoke_llm_with_tokens(
                messages=[{"role": "user", "content": leadership_prompt}],
                model_name=state.get("chat_model", "llama3.1:8b")
            )
            
            # Parse leadership decision
            lines = response.split('\n')
            leadership_decision = {
                "primary_leader": "project_manager",  # Default
                "leadership_style": "hybrid",
                "reasoning": "Default PM leadership",
                "backup_leader": None
            }
            
            for line in lines:
                line = line.strip()
                if line.startswith("PRIMARY_LEADER:"):
                    leader = line.replace("PRIMARY_LEADER:", "").strip()
                    if leader in selected_agents:
                        leadership_decision["primary_leader"] = leader
                elif line.startswith("LEADERSHIP_STYLE:"):
                    style = line.replace("LEADERSHIP_STYLE:", "").strip().lower()
                    if style in ["orchestration", "choreography", "consensus", "hybrid"]:
                        leadership_decision["leadership_style"] = style
                elif line.startswith("REASONING:"):
                    leadership_decision["reasoning"] = line.replace("REASONING:", "").strip()
                elif line.startswith("BACKUP_LEADER:"):
                    backup = line.replace("BACKUP_LEADER:", "").strip()
                    if backup in selected_agents:
                        leadership_decision["backup_leader"] = backup
            
        except Exception as e:
            logger.error(f"Failed to elect dynamic leader: {e}")
            leadership_decision = {
                "primary_leader": "project_manager",
                "leadership_style": "hybrid",
                "reasoning": "Fallback to PM leadership due to election failure",
                "backup_leader": None
            }
        
        # Set current leader and update orchestration mode
        state["current_leader"] = leadership_decision["primary_leader"]
        
        # Map leadership style to orchestration mode
        style_mapping = {
            "orchestration": OrchestrationMode.ORCHESTRATION,
            "choreography": OrchestrationMode.CHOREOGRAPHY,
            "consensus": OrchestrationMode.CONSENSUS,
            "hybrid": OrchestrationMode.HYBRID
        }
        state["orchestration_mode"] = style_mapping.get(
            leadership_decision["leadership_style"], 
            OrchestrationMode.HYBRID
        ).value
        
        # Record leadership history
        leadership_record = {
            **leadership_decision,
            "elected_at": datetime.now(timezone.utc).isoformat(),
            "election_context": "initial_workflow_setup"
        }
        state["leadership_history"] = [leadership_record]
        
        # Post leadership election event
        session_id = state["session_id"]
        user_id = int(state["user_id"]) if state["user_id"] else 1
        
        await blackboard_integration_service.post_blackboard_event(
            user_id=user_id,
            session_id=session_id,
            source_agent_id="hybrid_coordinator",
            agent_role="Hybrid Coordinator",
            event_type=EventType.DECISION_MADE,
            performative=Performative.ASSERT,
            event_payload={
                "leadership_election": leadership_decision,
                "new_orchestration_mode": state["orchestration_mode"]
            }
        )
        
        state["current_phase"] = "agent_coordination"
        
        # Add to discussion context
        leader_role = self.agent_id_to_role.get(leadership_decision["primary_leader"], "Unknown")
        discussion_entry = {
            "expert": "Hybrid Coordinator",
            "response": f"Elected {leader_role} as primary leader using {leadership_decision['leadership_style']} approach. {leadership_decision['reasoning']}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phase": "leadership_election",
            "confidence": 0.85
        }
        state["discussion_context"].append(discussion_entry)
        
        logger.info(f"Elected {leader_role} as primary leader with {leadership_decision['leadership_style']} style")
        return state

    async def _coordinate_agent_contributions_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate agent contributions based on orchestration mode."""
        
        logger.info("Coordinating agent contributions")
        
        orchestration_mode = OrchestrationMode(state["orchestration_mode"])
        current_leader = state["current_leader"]
        selected_agents = state["selected_agents"]
        
        if orchestration_mode == OrchestrationMode.CHOREOGRAPHY:
            # Decentralized choreography - agents self-organize
            contributions = await self._execute_choreography_mode(state)
        elif orchestration_mode == OrchestrationMode.ORCHESTRATION:
            # Centralized orchestration - leader directs
            contributions = await self._execute_orchestration_mode(state)
        else:
            # Hybrid mode - mix of both
            contributions = await self._execute_hybrid_mode(state)
        
        # Store contributions
        for agent_id, contribution_list in contributions.items():
            if agent_id not in state["agent_contributions"]:
                state["agent_contributions"][agent_id] = []
            state["agent_contributions"][agent_id].extend(contribution_list)
        
        state["current_phase"] = "consensus_building"
        
        # Add to discussion context
        total_contributions = sum(len(contribs) for contribs in contributions.values())
        discussion_entry = {
            "expert": "Hybrid Coordinator",
            "response": f"Coordinated {total_contributions} agent contributions using {orchestration_mode.value} mode",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phase": "agent_coordination",
            "confidence": 0.9
        }
        state["discussion_context"].append(discussion_entry)
        
        logger.info(f"Coordinated {total_contributions} agent contributions")
        return state

    async def _execute_choreography_mode(self, state: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """Execute decentralized choreography mode."""
        
        logger.info("Executing choreography mode - decentralized contributions")
        
        contributions = {}
        selected_agents = state["selected_agents"]
        contribution_opportunities = state["contribution_opportunities"]
        
        # Agents contribute based on detected opportunities
        tasks = []
        for agent_id in selected_agents:
            opportunities = contribution_opportunities.get(agent_id, [])
            if opportunities:
                task = self._agent_contribute_choreography(state, agent_id, opportunities)
                tasks.append((agent_id, task))
        
        # Execute contributions in parallel
        try:
            results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
            
            for (agent_id, _), result in zip(tasks, results):
                if isinstance(result, Exception):
                    logger.error(f"Error in choreography contribution from {agent_id}: {result}")
                    contributions[agent_id] = []
                else:
                    contributions[agent_id] = result or []
                    
        except Exception as e:
            logger.error(f"Failed to execute choreography mode: {e}")
            contributions = {agent_id: [] for agent_id in selected_agents}
        
        return contributions

    async def _agent_contribute_choreography(
        self, 
        state: Dict[str, Any], 
        agent_id: str, 
        opportunities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate agent contribution in choreography mode."""
        
        agent_role = self.agent_id_to_role.get(agent_id, "Unknown")
        user_request = state["user_request"]
        
        # Select best opportunity
        if not opportunities:
            return []
        
        best_opportunity = max(opportunities, key=lambda x: x.get("priority", 0))
        
        contribution_prompt = f"""
        As the {agent_role}, you've identified an opportunity to contribute to: {user_request}
        
        Opportunity details:
        {json.dumps(best_opportunity, indent=2)}
        
        Provide your expert contribution addressing:
        1. Your specific insights on this request
        2. How your expertise applies to the situation
        3. Concrete recommendations or solutions
        4. Any concerns or considerations from your perspective
        
        Be specific and actionable in your contribution.
        """
        
        try:
            response, _ = await invoke_llm_with_tokens(
                messages=[{"role": "user", "content": contribution_prompt}],
                model_name=state.get("chat_model", "llama3.1:8b")
            )
            
            contribution = {
                "agent_id": agent_id,
                "agent_role": agent_role,
                "contribution_type": "choreography",
                "opportunity_addressed": best_opportunity,
                "content": response,
                "confidence": 0.8,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Post contribution to blackboard
            await blackboard_integration_service.post_blackboard_event(
                user_id=int(state["user_id"]) if state["user_id"] else 1,
                session_id=state["session_id"],
                source_agent_id=agent_id,
                agent_role=agent_role,
                event_type=EventType.AGENT_CONTRIBUTION,
                performative=Performative.INFORM,
                event_payload=contribution
            )
            
            return [contribution]
            
        except Exception as e:
            logger.error(f"Failed to generate choreography contribution from {agent_id}: {e}")
            return []

    async def _execute_orchestration_mode(self, state: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """Execute centralized orchestration mode."""
        
        logger.info("Executing orchestration mode - centralized direction")
        
        current_leader = state["current_leader"]
        leader_role = self.agent_id_to_role.get(current_leader, "Project Manager")
        selected_agents = state["selected_agents"]
        user_request = state["user_request"]
        
        # Leader creates structured plan and delegates
        orchestration_prompt = f"""
        As the {leader_role} leading this expert group effort for: {user_request}
        
        Available team members: {', '.join([self.agent_id_to_role.get(agent, agent) for agent in selected_agents])}
        
        Create a structured coordination plan:
        1. Break down the request into specific tasks
        2. Assign tasks to appropriate team members
        3. Define the coordination approach
        4. Set priorities and sequencing
        
        Format your response as:
        COORDINATION_APPROACH: [Your leadership approach]
        
        TASK_ASSIGNMENTS:
        - [Agent Role]: [Specific task description]
        - [Agent Role]: [Specific task description]
        
        PRIORITIES: [Priority order and reasoning]
        """
        
        try:
            response, _ = await invoke_llm_with_tokens(
                messages=[{"role": "user", "content": orchestration_prompt}],
                model_name=state.get("chat_model", "llama3.1:8b")
            )
            
            # Parse orchestration plan
            task_assignments = self._parse_orchestration_plan(response, selected_agents)
            
            # Execute assigned tasks
            contributions = {}
            for agent_id, task_description in task_assignments.items():
                contribution = await self._execute_assigned_task(state, agent_id, task_description)
                contributions[agent_id] = [contribution] if contribution else []
            
            return contributions
            
        except Exception as e:
            logger.error(f"Failed to execute orchestration mode: {e}")
            return {agent_id: [] for agent_id in selected_agents}

    async def _execute_hybrid_mode(self, state: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """Execute hybrid orchestration/choreography mode."""
        
        logger.info("Executing hybrid mode - adaptive coordination")
        
        # Combine orchestration for structure with choreography for innovation
        orchestration_contributions = await self._execute_orchestration_mode(state)
        choreography_contributions = await self._execute_choreography_mode(state)
        
        # Merge contributions
        hybrid_contributions = {}
        all_agents = set(orchestration_contributions.keys()) | set(choreography_contributions.keys())
        
        for agent_id in all_agents:
            hybrid_contributions[agent_id] = []
            
            # Add orchestrated contributions
            if agent_id in orchestration_contributions:
                for contrib in orchestration_contributions[agent_id]:
                    contrib["coordination_mode"] = "orchestration"
                    hybrid_contributions[agent_id].append(contrib)
            
            # Add choreographed contributions
            if agent_id in choreography_contributions:
                for contrib in choreography_contributions[agent_id]:
                    contrib["coordination_mode"] = "choreography"
                    hybrid_contributions[agent_id].append(contrib)
        
        return hybrid_contributions

    async def _facilitate_consensus_building_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Facilitate consensus building on key decisions."""
        
        logger.info("Facilitating consensus building")
        
        agent_contributions = state["agent_contributions"]
        user_request = state["user_request"]
        
        # Identify consensus topics from contributions
        consensus_topics = await self._identify_consensus_topics(agent_contributions, user_request)
        
        consensus_results = []
        
        for topic in consensus_topics:
            # Initiate consensus process
            participating_agents = [
                {"agent_id": agent_id, "agent_role": self.agent_id_to_role.get(agent_id, "Unknown")}
                for agent_id in state["selected_agents"]
                if agent_id in agent_contributions and agent_contributions[agent_id]
            ]
            
            if len(participating_agents) < 2:
                continue
            
            consensus_criteria = {
                "convergence_threshold": 0.75,
                "max_rounds": 3,
                "require_unanimous": False
            }
            
            try:
                # Start consensus process
                consensus_id = await consensus_building_service.initiate_consensus_process(
                    user_id=int(state["user_id"]) if state["user_id"] else 1,
                    session_id=state["session_id"],
                    topic=topic["topic"],
                    participating_agents=participating_agents,
                    consensus_criteria=consensus_criteria,
                    method="delphi"
                )
                
                # Collect proposals
                proposals = await consensus_building_service.collect_independent_proposals(consensus_id)
                
                # Conduct feedback rounds
                feedback_rounds = await consensus_building_service.conduct_anonymized_feedback(consensus_id)
                
                # Analyze convergence
                convergence_analysis = await consensus_building_service.analyze_convergence(consensus_id)
                
                # Finalize consensus
                final_consensus = await consensus_building_service.finalize_consensus(consensus_id)
                
                if final_consensus:
                    consensus_results.append({
                        "topic": topic["topic"],
                        "consensus_id": consensus_id,
                        "result": final_consensus,
                        "convergence_score": convergence_analysis.get("overall_convergence_score", 0.0)
                    })
                    
                state["active_consensus_sessions"].append(consensus_id)
                
            except Exception as e:
                logger.error(f"Failed to build consensus on {topic['topic']}: {e}")
        
        state["consensus_decisions"] = consensus_results
        state["current_phase"] = "argumentation"
        
        # Add to discussion context
        discussion_entry = {
            "expert": "Consensus Facilitator",
            "response": f"Completed consensus building on {len(consensus_results)} topics with average convergence of {sum(r['convergence_score'] for r in consensus_results) / max(len(consensus_results), 1):.2f}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phase": "consensus_building",
            "confidence": 0.85
        }
        state["discussion_context"].append(discussion_entry)
        
        logger.info(f"Completed consensus building on {len(consensus_results)} topics")
        return state

    async def _conduct_argumentation_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Conduct structured argumentation and conflict resolution."""
        
        logger.info("Conducting structured argumentation")
        
        agent_contributions = state["agent_contributions"]
        consensus_decisions = state["consensus_decisions"]
        
        # Detect conflicts in contributions
        conflicts = await self._detect_contribution_conflicts(agent_contributions)
        
        argumentation_results = []
        
        for conflict in conflicts:
            # Conduct structured debate for conflict resolution
            try:
                debate_result = await self._conduct_structured_debate(state, conflict)
                if debate_result:
                    argumentation_results.append(debate_result)
                    
                    # Post conflict resolution to blackboard
                    await blackboard_integration_service.post_blackboard_event(
                        user_id=int(state["user_id"]) if state["user_id"] else 1,
                        session_id=state["session_id"],
                        source_agent_id="argumentation_facilitator",
                        agent_role="Argumentation Facilitator",
                        event_type=EventType.CONFLICT_DETECTED,
                        performative=Performative.INFORM,
                        event_payload={
                            "conflict": conflict,
                            "resolution": debate_result,
                            "resolution_method": "structured_debate"
                        }
                    )
                    
            except Exception as e:
                logger.error(f"Failed to resolve conflict through argumentation: {e}")
        
        state["argumentation_history"] = argumentation_results
        state["current_phase"] = "task_allocation"
        
        # Add to discussion context
        discussion_entry = {
            "expert": "Argumentation Facilitator",
            "response": f"Resolved {len(argumentation_results)} conflicts through structured argumentation and debate",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phase": "argumentation",
            "confidence": 0.8
        }
        state["discussion_context"].append(discussion_entry)
        
        logger.info(f"Completed argumentation phase with {len(argumentation_results)} conflict resolutions")
        return state

    async def _allocate_tasks_market_based_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Allocate tasks using market-based mechanisms."""
        
        logger.info("Conducting market-based task allocation")
        
        consensus_decisions = state["consensus_decisions"]
        selected_agents = state["selected_agents"]
        
        # Extract actionable tasks from consensus decisions
        actionable_tasks = []
        for decision in consensus_decisions:
            if "implementation_steps" in decision.get("result", {}):
                for step in decision["result"]["implementation_steps"]:
                    actionable_tasks.append({
                        "task_id": str(uuid.uuid4()),
                        "description": step,
                        "source_consensus": decision["consensus_id"],
                        "priority": "medium",
                        "estimated_effort": "medium"
                    })
        
        # Conduct Contract Net Protocol bidding
        task_bids = {}
        allocated_tasks = []
        
        for task in actionable_tasks:
            # Request bids from agents
            bids = await self._request_task_bids(state, task)
            task_bids[task["task_id"]] = bids
            
            # Evaluate bids and allocate
            if bids:
                winning_bid = self._evaluate_bids(bids, task)
                if winning_bid:
                    allocated_task = {
                        **task,
                        "allocated_to": winning_bid["agent_id"],
                        "allocation_method": "contract_net",
                        "bid_score": winning_bid["score"],
                        "allocated_at": datetime.now(timezone.utc).isoformat()
                    }
                    allocated_tasks.append(allocated_task)
                    
                    # Post task allocation to blackboard
                    await blackboard_integration_service.post_blackboard_event(
                        user_id=int(state["user_id"]) if state["user_id"] else 1,
                        session_id=state["session_id"],
                        source_agent_id="task_allocator",
                        agent_role="Task Allocator",
                        event_type=EventType.TASK_DELEGATED,
                        performative=Performative.REQUEST,
                        event_payload={
                            "task": allocated_task,
                            "allocation_method": "contract_net_protocol"
                        }
                    )
        
        state["task_bids"] = task_bids
        state["allocated_tasks"] = allocated_tasks
        state["current_phase"] = "validation_synthesis"
        
        # Add to discussion context
        discussion_entry = {
            "expert": "Task Allocator",
            "response": f"Allocated {len(allocated_tasks)} tasks using Contract Net Protocol with market-based bidding",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phase": "task_allocation",
            "confidence": 0.9
        }
        state["discussion_context"].append(discussion_entry)
        
        logger.info(f"Allocated {len(allocated_tasks)} tasks via market-based mechanisms")
        return state

    async def _validate_and_synthesize_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Validate results and synthesize final recommendations."""
        
        logger.info("Validating and synthesizing results")
        
        agent_contributions = state["agent_contributions"]
        consensus_decisions = state["consensus_decisions"]
        allocated_tasks = state["allocated_tasks"]
        
        # Multi-modal validation
        validation_results = {
            "contribution_quality": await self._validate_contribution_quality(agent_contributions),
            "consensus_integrity": await self._validate_consensus_integrity(consensus_decisions),
            "task_allocation_fairness": await self._validate_task_allocation(allocated_tasks),
            "overall_coherence": 0.0
        }
        
        # Calculate overall coherence
        quality_scores = [
            validation_results["contribution_quality"],
            validation_results["consensus_integrity"],
            validation_results["task_allocation_fairness"]
        ]
        validation_results["overall_coherence"] = sum(quality_scores) / len(quality_scores)
        
        # Quality checkpoint
        quality_checkpoint = {
            "checkpoint_id": str(uuid.uuid4()),
            "validation_results": validation_results,
            "passed_validation": validation_results["overall_coherence"] >= 0.7,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        state["validation_results"] = validation_results
        state["quality_checkpoints"] = [quality_checkpoint]
        state["current_phase"] = "final_output"
        
        # Add to discussion context
        discussion_entry = {
            "expert": "Quality Validator",
            "response": f"Validation complete. Overall coherence: {validation_results['overall_coherence']:.2f}. {'Passed' if quality_checkpoint['passed_validation'] else 'Requires improvement'}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phase": "validation_synthesis",
            "confidence": 0.95
        }
        state["discussion_context"].append(discussion_entry)
        
        logger.info(f"Validation complete with coherence score: {validation_results['overall_coherence']:.2f}")
        return state

    async def _generate_final_output_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive final output with enhanced synthesis."""
        
        logger.info("Generating final output")
        
        user_request = state["user_request"]
        agent_contributions = state["agent_contributions"]
        consensus_decisions = state["consensus_decisions"]
        allocated_tasks = state["allocated_tasks"]
        validation_results = state["validation_results"]
        
        # Synthesize comprehensive final response
        synthesis_prompt = f"""
        Create a comprehensive final response for: {user_request}
        
        Expert Contributions:
        {json.dumps({agent_id: [c.get("content", "") for c in contribs] for agent_id, contribs in agent_contributions.items()}, indent=2)}
        
        Consensus Decisions:
        {json.dumps([d.get("result", {}) for d in consensus_decisions], indent=2)}
        
        Task Allocations:
        {json.dumps(allocated_tasks, indent=2)}
        
        Validation Quality Score: {validation_results.get("overall_coherence", 0.0)}
        
        Provide a synthesis that:
        1. Directly addresses the original request
        2. Integrates insights from all expert contributions
        3. Incorporates consensus decisions reached
        4. Presents clear implementation guidance
        5. Acknowledges different perspectives and trade-offs
        6. Provides next steps based on task allocations
        
        Format as a comprehensive, professional response that showcases the collaborative expertise and consensus-building process.
        """
        
        try:
            final_response, _ = await invoke_llm_with_tokens(
                messages=[{"role": "user", "content": synthesis_prompt}],
                model_name=state.get("chat_model", "llama3.1:8b")
            )
            
            # Enhance with tool usage summary
            enhanced_final_response = enhance_summary_with_tool_usage(final_response, state)
            
        except Exception as e:
            logger.error(f"Failed to generate final synthesis: {e}")
            enhanced_final_response = f"Collaborative expert analysis completed for: {user_request}. Multiple expert perspectives were gathered and synthesized through consensus-building processes."
        
        state["final_summary"] = enhanced_final_response
        state["tools_used"] = state.get("tools_used", []) + ["Hybrid Orchestration", "Consensus Building", "Market-based Allocation"]
        state["actions_performed"] = state.get("actions_performed", []) + [
            "Dynamic leadership election",
            "Blackboard-mediated coordination", 
            "Consensus building",
            "Argumentation-based negotiation",
            "Market-based task allocation"
        ]
        
        # Final blackboard event
        await blackboard_integration_service.post_blackboard_event(
            user_id=int(state["user_id"]) if state["user_id"] else 1,
            session_id=state["session_id"],
            source_agent_id="hybrid_coordinator",
            agent_role="Hybrid Coordinator",
            event_type=EventType.VALIDATION_COMPLETED,
            performative=Performative.CONFIRM,
            event_payload={
                "final_output_generated": True,
                "quality_score": validation_results.get("overall_coherence", 0.0),
                "consensus_decisions_count": len(consensus_decisions),
                "tasks_allocated_count": len(allocated_tasks),
                "workflow_completed": True
            }
        )
        
        # Add final summary to discussion context
        discussion_entry = {
            "expert": "Hybrid Coordinator",
            "response": enhanced_final_response,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phase": "final_output",
            "confidence": 0.95
        }
        state["discussion_context"].append(discussion_entry)
        
        logger.info("Final output generated successfully")
        return state

    async def _validate_hybrid_final_state(self, final_state: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and format hybrid workflow final state."""
        
        try:
            # Ensure required keys exist
            required_keys = [
                "final_summary", "discussion_context", "agent_contributions",
                "consensus_decisions", "allocated_tasks", "validation_results"
            ]
            
            for key in required_keys:
                if key not in final_state:
                    final_state[key] = [] if key.endswith(("_context", "_contributions", "_decisions", "_tasks")) else {}
            
            # Extract experts involved
            experts_involved = list(final_state.get("agent_contributions", {}).keys())
            validated_experts = [
                self.agent_id_to_role.get(agent_id, agent_id) 
                for agent_id in experts_involved 
                if agent_id in self.agent_id_to_role
            ]
            
            return {
                "response": final_state.get("final_summary", "Hybrid expert group collaboration completed."),
                "discussion_context": final_state.get("discussion_context", []),
                "experts_involved": validated_experts,
                "agent_contributions": final_state.get("agent_contributions", {}),
                "consensus_decisions": final_state.get("consensus_decisions", []),
                "allocated_tasks": final_state.get("allocated_tasks", []),
                "validation_results": final_state.get("validation_results", {}),
                "tools_used": final_state.get("tools_used", []),
                "actions_performed": final_state.get("actions_performed", []),
                "orchestration_mode": final_state.get("orchestration_mode", "hybrid"),
                "leadership_history": final_state.get("leadership_history", []),
                "quality_checkpoints": final_state.get("quality_checkpoints", []),
                "is_coordinated": True,
                "pm_managed": True,
                "workflow_type": "hybrid_expert_group",
                "consensus_enabled": True,
                "market_based_allocation": True
            }
            
        except Exception as e:
            logger.error(f"Hybrid state validation failed: {e}")
            return await self._emergency_fallback("Validation error", [], None)

    # Helper methods for parsing, validation, and processing
    
    def _parse_orchestration_plan(self, response: str, selected_agents: List[str]) -> Dict[str, str]:
        """Parse orchestration plan and extract task assignments."""
        task_assignments = {}
        
        try:
            lines = response.split('\n')
            in_assignments = False
            
            for line in lines:
                line = line.strip()
                if line.startswith("TASK_ASSIGNMENTS:"):
                    in_assignments = True
                    continue
                elif in_assignments and line.startswith("-") and ":" in line:
                    parts = line[1:].split(":", 1)
                    if len(parts) == 2:
                        role_text = parts[0].strip()
                        task_text = parts[1].strip()
                        
                        # Find matching agent
                        for agent_id in selected_agents:
                            agent_role = self.agent_id_to_role.get(agent_id, "")
                            if role_text.lower() in agent_role.lower() or agent_role.lower() in role_text.lower():
                                task_assignments[agent_id] = task_text
                                break
                elif in_assignments and line.startswith("PRIORITIES:"):
                    break
        
        except Exception as e:
            logger.error(f"Failed to parse orchestration plan: {e}")
        
        return task_assignments

    async def _execute_assigned_task(
        self, 
        state: Dict[str, Any], 
        agent_id: str, 
        task_description: str
    ) -> Optional[Dict[str, Any]]:
        """Execute a task assigned through orchestration."""
        
        agent_role = self.agent_id_to_role.get(agent_id, "Unknown")
        
        task_prompt = f"""
        As the {agent_role}, you have been assigned this specific task: {task_description}
        
        Original request context: {state['user_request']}
        
        Execute this task and provide:
        1. Your approach to completing the task
        2. Specific deliverables or outputs
        3. Any dependencies or requirements identified
        4. Recommendations for next steps
        
        Be thorough and specific in your execution.
        """
        
        try:
            response, _ = await invoke_llm_with_tokens(
                messages=[{"role": "user", "content": task_prompt}],
                model_name=state.get("chat_model", "llama3.1:8b")
            )
            
            contribution = {
                "agent_id": agent_id,
                "agent_role": agent_role,
                "contribution_type": "orchestration",
                "assigned_task": task_description,
                "content": response,
                "confidence": 0.85,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            return contribution
            
        except Exception as e:
            logger.error(f"Failed to execute assigned task for {agent_id}: {e}")
            return None

    async def _identify_consensus_topics(
        self, 
        agent_contributions: Dict[str, List[Dict[str, Any]]], 
        user_request: str
    ) -> List[Dict[str, Any]]:
        """Identify topics requiring consensus from agent contributions."""
        
        # Analyze contributions to identify decision points
        all_content = []
        for agent_id, contributions in agent_contributions.items():
            for contrib in contributions:
                all_content.append(contrib.get("content", ""))
        
        combined_content = "\n".join(all_content)
        
        if not combined_content.strip():
            return []
        
        analysis_prompt = f"""
        Analyze these expert contributions for: {user_request}
        
        Contributions:
        {combined_content[:2000]}  # Limit for prompt size
        
        Identify key topics that require group consensus or decision-making.
        Focus on:
        1. Conflicting recommendations
        2. Major strategic decisions
        3. Resource allocation choices
        4. Implementation approaches
        
        List 2-3 most important consensus topics:
        TOPIC 1: [Description]
        TOPIC 2: [Description]
        TOPIC 3: [Description]
        """
        
        try:
            response, _ = await invoke_llm_with_tokens(
                messages=[{"role": "user", "content": analysis_prompt}],
                model_name="llama3.1:8b"
            )
            
            # Parse consensus topics
            topics = []
            lines = response.split('\n')
            
            for line in lines:
                line = line.strip()
                if line.startswith("TOPIC") and ":" in line:
                    topic_text = line.split(":", 1)[1].strip()
                    if topic_text:
                        topics.append({
                            "topic": topic_text,
                            "priority": "high",
                            "source": "contribution_analysis"
                        })
            
            return topics[:3]  # Limit to top 3 topics
            
        except Exception as e:
            logger.error(f"Failed to identify consensus topics: {e}")
            return []

    async def _detect_contribution_conflicts(
        self, 
        agent_contributions: Dict[str, List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Detect conflicts between agent contributions."""
        
        conflicts = []
        
        # Compare contributions pairwise for conflicts
        agent_list = list(agent_contributions.keys())
        
        for i, agent1 in enumerate(agent_list):
            for j, agent2 in enumerate(agent_list[i+1:], i+1):
                contrib1_content = " ".join([
                    c.get("content", "") for c in agent_contributions[agent1]
                ])
                contrib2_content = " ".join([
                    c.get("content", "") for c in agent_contributions[agent2]
                ])
                
                if contrib1_content and contrib2_content:
                    conflict = await self._analyze_contribution_conflict(
                        agent1, contrib1_content, agent2, contrib2_content
                    )
                    if conflict:
                        conflicts.append(conflict)
        
        return conflicts

    async def _analyze_contribution_conflict(
        self, 
        agent1: str, 
        content1: str, 
        agent2: str, 
        content2: str
    ) -> Optional[Dict[str, Any]]:
        """Analyze potential conflict between two contributions."""
        
        conflict_prompt = f"""
        Analyze these two expert contributions for potential conflicts:
        
        {self.agent_id_to_role.get(agent1, agent1)}:
        {content1[:500]}
        
        {self.agent_id_to_role.get(agent2, agent2)}:
        {content2[:500]}
        
        Determine if there is a significant conflict in:
        1. Recommendations
        2. Approaches
        3. Priorities
        4. Implementation strategies
        
        If conflict exists, respond:
        CONFLICT: Yes
        TYPE: [recommendation/approach/priority/implementation]
        DESCRIPTION: [Brief description of the conflict]
        SEVERITY: [low/medium/high]
        
        If no significant conflict:
        CONFLICT: No
        """
        
        try:
            response, _ = await invoke_llm_with_tokens(
                messages=[{"role": "user", "content": conflict_prompt}],
                model_name="llama3.1:8b"
            )
            
            # Parse conflict analysis
            lines = response.split('\n')
            conflict_data = {}
            
            for line in lines:
                line = line.strip()
                if ":" in line:
                    key, value = line.split(":", 1)
                    conflict_data[key.strip().lower()] = value.strip()
            
            if conflict_data.get("conflict", "").lower() == "yes":
                return {
                    "agents": [agent1, agent2],
                    "agent_roles": [
                        self.agent_id_to_role.get(agent1, agent1),
                        self.agent_id_to_role.get(agent2, agent2)
                    ],
                    "conflict_type": conflict_data.get("type", "unknown"),
                    "description": conflict_data.get("description", ""),
                    "severity": conflict_data.get("severity", "medium"),
                    "detected_at": datetime.now(timezone.utc).isoformat()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to analyze contribution conflict: {e}")
            return None

    async def _conduct_structured_debate(
        self, 
        state: Dict[str, Any], 
        conflict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Conduct structured debate to resolve conflict."""
        
        agents = conflict["agents"]
        conflict_description = conflict["description"]
        
        # Simplified debate resolution
        debate_prompt = f"""
        Facilitate a structured debate resolution for this conflict:
        
        Conflict: {conflict_description}
        Participants: {', '.join([self.agent_id_to_role.get(a, a) for a in agents])}
        
        Provide a mediated resolution that:
        1. Acknowledges both perspectives
        2. Identifies common ground
        3. Proposes a compromise or synthesis
        4. Explains the reasoning
        
        RESOLUTION: [Mediated solution]
        REASONING: [Explanation of the resolution approach]
        COMPROMISE_ELEMENTS: [What each side contributes]
        """
        
        try:
            response, _ = await invoke_llm_with_tokens(
                messages=[{"role": "user", "content": debate_prompt}],
                model_name="llama3.1:8b"
            )
            
            return {
                "conflict": conflict,
                "resolution_method": "structured_debate",
                "resolution_content": response,
                "resolved_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to conduct structured debate: {e}")
            return None

    async def _request_task_bids(
        self, 
        state: Dict[str, Any], 
        task: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Request bids from agents for task allocation."""
        
        bids = []
        selected_agents = state["selected_agents"]
        
        for agent_id in selected_agents:
            agent_role = self.agent_id_to_role.get(agent_id, "Unknown")
            
            # Request bid from agent
            bid_prompt = f"""
            As the {agent_role}, evaluate this task for potential allocation:
            
            Task: {task['description']}
            Priority: {task['priority']}
            Estimated Effort: {task['estimated_effort']}
            
            Provide your bid assessment:
            INTEREST_LEVEL: [1-5 scale, 5=very interested]
            CAPABILITY_MATCH: [1-5 scale, 5=perfect match]
            AVAILABILITY: [1-5 scale, 5=fully available]
            APPROACH: [Brief description of your approach]
            
            If not interested or capable, respond with INTEREST_LEVEL: 0
            """
            
            try:
                response, _ = await invoke_llm_with_tokens(
                    messages=[{"role": "user", "content": bid_prompt}],
                    model_name=state.get("chat_model", "llama3.1:8b")
                )
                
                # Parse bid response
                bid_data = self._parse_bid_response(response)
                if bid_data and bid_data.get("interest_level", 0) > 0:
                    bid_data.update({
                        "agent_id": agent_id,
                        "agent_role": agent_role,
                        "task_id": task["task_id"],
                        "submitted_at": datetime.now(timezone.utc).isoformat()
                    })
                    bids.append(bid_data)
                    
            except Exception as e:
                logger.error(f"Failed to collect bid from {agent_id}: {e}")
        
        return bids

    def _parse_bid_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse agent bid response."""
        
        try:
            lines = response.split('\n')
            bid_data = {}
            
            for line in lines:
                line = line.strip()
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip().lower().replace(" ", "_")
                    value = value.strip()
                    
                    if key in ["interest_level", "capability_match", "availability"]:
                        try:
                            bid_data[key] = int(value)
                        except ValueError:
                            bid_data[key] = 0
                    elif key == "approach":
                        bid_data[key] = value
            
            return bid_data
            
        except Exception as e:
            logger.error(f"Failed to parse bid response: {e}")
            return None

    def _evaluate_bids(
        self, 
        bids: List[Dict[str, Any]], 
        task: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Evaluate bids and select winner using weighted scoring."""
        
        if not bids:
            return None
        
        # Calculate composite scores
        for bid in bids:
            interest = bid.get("interest_level", 0)
            capability = bid.get("capability_match", 0)
            availability = bid.get("availability", 0)
            
            # Weighted score calculation
            bid["score"] = (
                interest * 0.3 +
                capability * 0.5 +
                availability * 0.2
            )
        
        # Select highest scoring bid
        winning_bid = max(bids, key=lambda x: x["score"])
        
        return winning_bid if winning_bid["score"] > 2.0 else None

    async def _validate_contribution_quality(
        self, 
        agent_contributions: Dict[str, List[Dict[str, Any]]]
    ) -> float:
        """Validate quality of agent contributions."""
        
        if not agent_contributions:
            return 0.0
        
        total_score = 0.0
        contribution_count = 0
        
        for agent_id, contributions in agent_contributions.items():
            for contrib in contributions:
                # Simple quality metrics
                content = contrib.get("content", "")
                confidence = contrib.get("confidence", 0.5)
                
                # Quality factors
                length_score = min(1.0, len(content) / 200)  # Favor substantial content
                confidence_score = confidence
                
                quality_score = (length_score + confidence_score) / 2
                total_score += quality_score
                contribution_count += 1
        
        return total_score / max(contribution_count, 1)

    async def _validate_consensus_integrity(self, consensus_decisions: List[Dict[str, Any]]) -> float:
        """Validate integrity of consensus decisions."""
        
        if not consensus_decisions:
            return 0.5  # Neutral score if no consensus attempted
        
        total_score = 0.0
        
        for decision in consensus_decisions:
            convergence_score = decision.get("convergence_score", 0.5)
            total_score += convergence_score
        
        return total_score / len(consensus_decisions)

    async def _validate_task_allocation(self, allocated_tasks: List[Dict[str, Any]]) -> float:
        """Validate fairness and appropriateness of task allocation."""
        
        if not allocated_tasks:
            return 0.5  # Neutral if no tasks allocated
        
        # Check distribution fairness
        agent_task_counts = {}
        total_score = 0.0
        
        for task in allocated_tasks:
            agent = task.get("allocated_to", "unknown")
            agent_task_counts[agent] = agent_task_counts.get(agent, 0) + 1
            
            # Score based on bid quality
            bid_score = task.get("bid_score", 2.5)
            normalized_score = bid_score / 5.0  # Normalize to 0-1
            total_score += normalized_score
        
        # Calculate fairness (lower variance = higher fairness)
        if len(agent_task_counts) > 1:
            counts = list(agent_task_counts.values())
            mean_count = sum(counts) / len(counts)
            variance = sum((c - mean_count) ** 2 for c in counts) / len(counts)
            fairness_score = max(0.0, 1.0 - (variance / max(counts)))
        else:
            fairness_score = 1.0
        
        quality_score = total_score / len(allocated_tasks)
        
        return (quality_score + fairness_score) / 2

    async def _emergency_fallback(
        self, 
        user_request: str, 
        selected_agents: List[str], 
        user_id: str = None
    ) -> Dict[str, Any]:
        """Emergency fallback when hybrid workflow fails."""
        
        logger.error("Using emergency fallback for hybrid expert group workflow")
        
        return {
            "response": f"I understand you need help with: {user_request}\n\nI'm experiencing technical difficulties with the full hybrid expert group workflow, but here's my analysis:\n\n• The request requires collaborative expert input\n• Multiple perspectives would benefit the solution\n• I recommend breaking this into specific expert domains\n• Consider iterative refinement and consensus building\n\nPlease try your request again or break it into smaller components.",
            "discussion_context": [],
            "experts_involved": [],
            "agent_contributions": {},
            "consensus_decisions": [],
            "allocated_tasks": [],
            "validation_results": {},
            "tools_used": ["Emergency analysis"],
            "actions_performed": ["Fallback processing"],
            "orchestration_mode": "emergency",
            "is_coordinated": False,
            "pm_managed": False,
            "workflow_type": "emergency_fallback",
            "consensus_enabled": False,
            "market_based_allocation": False
        }

    async def _fallback_process_request(
        self, 
        user_request: str, 
        selected_agents: List[str] = None, 
        user_id: str = None
    ) -> Dict[str, Any]:
        """Fallback when LangGraph is not available."""
        
        logger.info("Running simplified hybrid processing without LangGraph")
        
        # Use existing expert group service as fallback
        from worker.services.expert_group_langgraph_service import expert_group_langgraph_service
        
        try:
            result = await expert_group_langgraph_service.process_request(
                user_request, selected_agents, user_id
            )
            
            # Enhance with hybrid indicators
            result.update({
                "workflow_type": "hybrid_fallback",
                "orchestration_mode": "sequential",
                "consensus_enabled": False,
                "market_based_allocation": False
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Fallback processing failed: {e}")
            return await self._emergency_fallback(user_request, selected_agents, user_id)


# Global service instance
hybrid_expert_group_langgraph_service = HybridExpertGroupLangGraphService()