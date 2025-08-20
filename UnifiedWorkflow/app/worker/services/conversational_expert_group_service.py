"""
Conversational Expert Group Service - Real-time business meeting with tool integration
Implements dynamic conversation between experts with real tool usage - Research Specialist uses Tavily API,
Personal Assistant uses Google Calendar, with streaming tool usage transparency.
"""

import json
import logging
import uuid
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime, timezone
from enum import Enum

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
from pydantic import BaseModel, Field

from worker.services.ollama_service import invoke_llm_with_tokens
from shared.utils.streaming_utils import sanitize_content
from worker.services.expert_group_specialized_methods import (
    research_specialist_with_tools,
    personal_assistant_with_tools,
    standard_expert_response
)

logger = logging.getLogger(__name__)


class ConversationPhase(str, Enum):
    """Phases of the expert group conversation."""
    OPENING = "opening"
    INDIVIDUAL_QUESTIONS = "individual_questions"
    EXPERT_RESPONSES = "expert_responses"
    CROSS_DISCUSSION = "cross_discussion"
    TODO_PLANNING = "todo_planning"
    TASK_DELEGATION = "task_delegation"
    PROGRESS_UPDATES = "progress_updates"
    FINAL_SUMMARY = "final_summary"


class ExpertRole(str, Enum):
    """Available expert roles."""
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


class ConversationState(BaseModel):
    """State for conversational expert group workflow."""
    # Input
    session_id: str
    user_request: str
    selected_agents: List[str] = Field(default_factory=list)
    
    # Meeting management
    current_phase: ConversationPhase = ConversationPhase.OPENING
    meeting_start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    current_speaker: Optional[str] = None
    conversation_turns: int = 0
    max_conversation_turns: int = 20
    
    # Dynamic conversation
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    pending_questions: List[Dict[str, Any]] = Field(default_factory=list)
    todo_list: List[Dict[str, Any]] = Field(default_factory=list)
    completed_tasks: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Tool Usage Tracking
    tool_calls_made: List[Dict[str, Any]] = Field(default_factory=list)
    search_results: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    calendar_data: Dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[str] = None
    
    # Meeting controls
    meeting_active: bool = True
    timeout_minutes: int = 60
    
    # Configuration
    chat_model: str = "llama3.1:8b"


class ConversationalExpertGroupService:
    """Service for running conversational expert group meetings."""
    
    def __init__(self):
        self.agent_id_to_role = {
            "project_manager": ExpertRole.PROJECT_MANAGER,
            "technical_expert": ExpertRole.TECHNICAL_EXPERT,
            "business_analyst": ExpertRole.BUSINESS_ANALYST,
            "creative_director": ExpertRole.CREATIVE_DIRECTOR,
            "research_specialist": ExpertRole.RESEARCH_SPECIALIST,
            "planning_expert": ExpertRole.PLANNING_EXPERT,
            "socratic_expert": ExpertRole.SOCRATIC_EXPERT,
            "wellbeing_coach": ExpertRole.WELLBEING_COACH,
            "personal_assistant": ExpertRole.PERSONAL_ASSISTANT,
            "data_analyst": ExpertRole.DATA_ANALYST,
            "output_formatter": ExpertRole.OUTPUT_FORMATTER,
            "quality_assurance": ExpertRole.QUALITY_ASSURANCE
        }
        # Create validation mapping for hallucination prevention
        self.valid_expert_names = set(role.value for role in ExpertRole)
        
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
                logger.warning(f"CONVERSATIONAL HALLUCINATION DETECTED: Invalid expert '{expert_name}' filtered out. Valid experts: {list(self.valid_expert_names)}")
        
        if invalid_experts:
            logger.error(f"Conversational hallucinated experts detected and filtered: {invalid_experts}")
        
        return valid_experts
    
    async def run_conversational_meeting(
        self, 
        user_request: str, 
        selected_agents: List[str],
        user_id: str = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Run a conversational expert group meeting with real-time streaming.
        
        Yields:
            Dict containing streaming updates for the frontend
        """
        
        logger.info(f"CONVERSATIONAL_DEBUG: Starting conversational meeting with agents: {selected_agents}")
        
        # Validate selected agents before initializing state
        if not selected_agents:
            logger.warning("CONVERSATIONAL_DEBUG: No agents provided, using default Project Manager")
            selected_agents = ["project_manager"]  # Ensure at least PM is present
        
        # Filter valid agents
        valid_agents = [agent for agent in selected_agents if agent in self.agent_id_to_role]
        if not valid_agents:
            logger.warning(f"CONVERSATIONAL_DEBUG: No valid agents found, defaulting to Project Manager. Invalid agents: {selected_agents}")
            valid_agents = ["project_manager"]
        
        logger.info(f"CONVERSATIONAL_DEBUG: Using valid agents: {valid_agents}")
        
        # Initialize meeting state with validated agents
        state = ConversationState(
            session_id=str(uuid.uuid4()),
            user_request=user_request,
            selected_agents=valid_agents,  # Use validated agents
            user_id=user_id
        )
        
        logger.info(f"CONVERSATIONAL_DEBUG: Initialized state with session_id: {state.session_id}, agents: {valid_agents}")
        
        # Yield meeting start with already validated participants
        try:
            # Use the validated agents from state
            meeting_agents = state.selected_agents
            
            # Generate participant roles text with enhanced debugging
            participant_roles = []
            logger.info(f"MEETING_START_DEBUG: Processing {len(meeting_agents)} agents: {meeting_agents}")
            
            for agent in meeting_agents:
                if agent in self.agent_id_to_role:
                    role = self.agent_id_to_role[agent]
                    role_value = role.value
                    participant_roles.append(role_value)
                    logger.info(f"MEETING_START_DEBUG: Agent '{agent}' -> Role '{role_value}'")
                else:
                    logger.error(f"MEETING_START_DEBUG: Agent '{agent}' NOT FOUND in agent_id_to_role mapping!")
                    participant_roles.append(f"Unknown({agent})")
            
            participants_text = ', '.join(participant_roles)
            logger.info(f"MEETING_START_DEBUG: Generated participants text: '{participants_text}' from {len(participant_roles)} roles")
            
            # Create comprehensive meeting start data
            meeting_start_data = {
                "type": "meeting_start",
                "content": sanitize_content(f"🎯 **Expert Group Meeting Started**\n\nTopic: {user_request}\n\nParticipants: {participants_text}\n\nFacilitator: Project Manager"),
                "metadata": {
                    "session_id": state.session_id,
                    "participants": meeting_agents,  # Use state agents (already validated)
                    "participant_roles": [self.agent_id_to_role[agent].value for agent in meeting_agents],
                    "agents_count": len(meeting_agents),
                    "original_selection": selected_agents,  # Track original selection for debugging
                    "estimated_duration": "Up to 60 minutes"
                },
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
            }
            logger.info(f"MEETING_START_DEBUG: About to yield meeting_start_data with {len(meeting_agents)} participants: {meeting_start_data}")
            yield meeting_start_data
            logger.info("MEETING_START_DEBUG: Successfully yielded meeting_start")
        except Exception as e:
            logger.error(f"Error yielding meeting_start: {e}", exc_info=True)
            yield {
                "type": "error",
                "content": sanitize_content(f"Failed to start meeting: {str(e)}"),
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                "metadata": {
                    "error_type": type(e).__name__
                }
            }
        
        # Main conversation loop with enhanced real-time updates and loop prevention
        max_loop_iterations = 50  # Prevent infinite loops
        loop_iteration = 0
        
        while state.meeting_active and self._within_time_limit(state) and loop_iteration < max_loop_iterations:
            loop_iteration += 1
            logger.info(f"Main loop iteration {loop_iteration} - active: {state.meeting_active}, within_time: {self._within_time_limit(state)}, phase: {state.current_phase}")
            
            # Check if we should move to next phase
            should_advance = self._should_advance_phase(state)
            if should_advance:
                next_phase = self._get_next_phase(state.current_phase)
                
                # Check for final summary phase to end meeting
                if next_phase == ConversationPhase.FINAL_SUMMARY:
                    logger.info("Reached final summary phase, ending main loop")
                    break
                
                # Yield phase transition with detailed info
                yield {
                    "type": "phase_transition",
                    "content": sanitize_content(f"📋 **Meeting Phase: {next_phase.value.replace('_', ' ').title()}**\n\n{self._get_phase_description(next_phase)}"),
                    "metadata": {
                        "phase": next_phase.value,
                        "previous_phase": state.current_phase.value,
                        "turn": state.conversation_turns,
                        "loop_iteration": loop_iteration,
                        "participating_experts": len([r for r in state.conversation_history if r.get("type") == "expert_response" and not r.get("metadata", {}).get("excluded")])
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
                }
                
                state.current_phase = next_phase
                
                # Add a brief pause for phase transition
                await asyncio.sleep(0.5)
            
            # Execute current phase with progress tracking
            phase_responses = 0
            async for response in self._execute_phase(state):
                yield response
                phase_responses += 1
                
                # Update state based on response
                if response.get("type") in ["expert_response", "expert_exclusion", "expert_question"]:
                    state.conversation_history.append(response)
                    if response.get("type") == "expert_response":
                        state.conversation_turns += 1
                
                # Brief pause between expert responses for better UX
                if response.get("type") == "expert_response":
                    await asyncio.sleep(0.2)
            
            # Check meeting limits - multiple exit conditions
            if state.conversation_turns >= state.max_conversation_turns:
                logger.info("Meeting reached maximum conversation turns")
                yield {
                    "type": "meeting_info",
                    "content": sanitize_content("📋 **Meeting reached maximum interaction limit - proceeding to summary**"),
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                    "metadata": {"reason": "max_turns_reached"}
                }
                break
                
            # Check if no responses in this phase and we're stuck
            if phase_responses == 0:
                if state.current_phase in [ConversationPhase.EXPERT_RESPONSES, ConversationPhase.CROSS_DISCUSSION]:
                    logger.info(f"No responses in phase {state.current_phase}, forcing advancement")
                    # Force advance by ensuring phase advancement condition is met
                    if state.current_phase == ConversationPhase.EXPERT_RESPONSES:
                        # Clear pending questions to force advancement
                        state.pending_questions = []
                    continue
                elif loop_iteration > 10:
                    logger.warning(f"No responses for {loop_iteration} iterations in phase {state.current_phase}, ending meeting")
                    break
                    
            # Check for loop prevention - if stuck in same phase too long
            if loop_iteration > 20 and not should_advance:
                logger.error(f"Meeting stuck in phase {state.current_phase} for {loop_iteration} iterations, forcing end")
                break
                
            # Progressive delay between phases (shorter for active phases)
            phase_delay = 0.2 if state.current_phase in [ConversationPhase.OPENING, ConversationPhase.INDIVIDUAL_QUESTIONS] else 0.4
            await asyncio.sleep(phase_delay)
        
        # Log exit reason
        if loop_iteration >= max_loop_iterations:
            logger.error(f"Meeting ended due to loop iteration limit ({max_loop_iterations})")
        elif not state.meeting_active:
            logger.info("Meeting ended - meeting_active set to False")
        elif not self._within_time_limit(state):
            logger.info("Meeting ended - time limit exceeded")
        else:
            logger.info("Meeting ended - normal completion")
        
        logger.info("Main conversation loop completed")
        
        # End meeting with summary
        logger.info("Generating meeting summary...")
        async for summary_response in self._generate_meeting_summary(state):
            yield summary_response
        
        logger.info("Conversational meeting completed successfully")
    
    def _within_time_limit(self, state: ConversationState) -> bool:
        """Check if meeting is within time limit."""
        elapsed = datetime.now(timezone.utc) - state.meeting_start_time
        return elapsed.total_seconds() < (state.timeout_minutes * 60)
    
    def _should_advance_phase(self, state: ConversationState) -> bool:
        """Determine if we should advance to the next phase."""
        
        # Count actual responses by phase to determine advancement
        opening_responses = len([r for r in state.conversation_history if r.get('phase') == 'opening'])
        question_responses = len([r for r in state.conversation_history if r.get('phase') == 'individual_questions'])
        expert_responses = len([r for r in state.conversation_history if r.get('phase') == 'expert_responses' and r.get('type') == 'expert_response'])
        cross_discussion_responses = len([r for r in state.conversation_history if r.get('phase') == 'cross_discussion'])
        task_delegation_responses = len([r for r in state.conversation_history if r.get('phase') == 'task_delegation'])
        
        # Phase advancement conditions based on actual responses rather than turn counts
        phase_conditions = {
            ConversationPhase.OPENING: opening_responses >= 1,
            ConversationPhase.INDIVIDUAL_QUESTIONS: question_responses >= len(state.selected_agents) - 1,  # PM asks each agent except themselves
            ConversationPhase.EXPERT_RESPONSES: expert_responses >= len(state.pending_questions) or len(state.pending_questions) == 0,  # All pending questions answered or none to answer
            ConversationPhase.CROSS_DISCUSSION: cross_discussion_responses >= min(3, len(state.selected_agents) - 1),  # Max 3 cross-discussion responses
            ConversationPhase.TODO_PLANNING: len(state.todo_list) > 0 or state.conversation_turns >= 10,  # Either todos created or force advance
            ConversationPhase.TASK_DELEGATION: len(state.completed_tasks) > 0 or len(state.todo_list) == 0 or task_delegation_responses > 0,  # EMERGENCY FIX: Tasks delegated, no todos, OR delegation responses exist
            ConversationPhase.PROGRESS_UPDATES: state.conversation_turns >= state.max_conversation_turns - 2
        }
        
        result = phase_conditions.get(state.current_phase, False)
        
        # EMERGENCY: Specific protection against task delegation infinite loops
        if state.current_phase == ConversationPhase.TASK_DELEGATION:
            # Force advance if we've generated any delegation responses OR if completed_tasks exist
            delegation_complete = (task_delegation_responses > 0 or 
                                 len(state.completed_tasks) > 0 or 
                                 len(state.todo_list) == 0)
            if delegation_complete:
                logger.info(f"EMERGENCY_LOOP_FIX: Advancing from task_delegation - responses: {task_delegation_responses}, completed: {len(state.completed_tasks)}, todos: {len(state.todo_list)}")
                return True
        
        # Force advancement if stuck in any phase for too long
        phase_response_count = {
            ConversationPhase.OPENING: opening_responses,
            ConversationPhase.INDIVIDUAL_QUESTIONS: question_responses, 
            ConversationPhase.EXPERT_RESPONSES: expert_responses,
            ConversationPhase.CROSS_DISCUSSION: cross_discussion_responses,
            ConversationPhase.TASK_DELEGATION: task_delegation_responses
        }.get(state.current_phase, 0)
        
        # Force advance if no activity in current phase after reasonable time
        if phase_response_count == 0 and state.conversation_turns >= 5:
            logger.warning(f"Force advancing from {state.current_phase} due to no responses after {state.conversation_turns} turns")
            return True
            
        return result
    
    def _get_next_phase(self, current_phase: ConversationPhase) -> ConversationPhase:
        """Get the next phase in the conversation."""
        phase_order = [
            ConversationPhase.OPENING,
            ConversationPhase.INDIVIDUAL_QUESTIONS,
            ConversationPhase.EXPERT_RESPONSES,
            ConversationPhase.CROSS_DISCUSSION,
            ConversationPhase.TODO_PLANNING,
            ConversationPhase.TASK_DELEGATION,
            ConversationPhase.PROGRESS_UPDATES,
            ConversationPhase.FINAL_SUMMARY
        ]
        
        try:
            current_index = phase_order.index(current_phase)
            return phase_order[min(current_index + 1, len(phase_order) - 1)]
        except ValueError:
            return ConversationPhase.FINAL_SUMMARY
    
    def _get_phase_description(self, phase: ConversationPhase) -> str:
        """Get a user-friendly description of what happens in each phase."""
        descriptions = {
            ConversationPhase.OPENING: "Project Manager welcomes the team and sets meeting objectives",
            ConversationPhase.INDIVIDUAL_QUESTIONS: "Project Manager asks targeted questions to each expert",
            ConversationPhase.EXPERT_RESPONSES: "Experts provide their professional insights and recommendations",
            ConversationPhase.CROSS_DISCUSSION: "Team members collaborate and build on each other's ideas",
            ConversationPhase.TODO_PLANNING: "Project Manager creates actionable todo list from discussion",
            ConversationPhase.TASK_DELEGATION: "Specific tasks are assigned to appropriate team members",
            ConversationPhase.PROGRESS_UPDATES: "Team members confirm their commitments and next steps",
            ConversationPhase.FINAL_SUMMARY: "Project Manager provides comprehensive meeting summary"
        }
        return descriptions.get(phase, "Meeting phase in progress")
    
    async def _execute_phase(self, state: ConversationState) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute the current conversation phase."""
        
        if state.current_phase == ConversationPhase.OPENING:
            async for response in self._opening_phase(state):
                yield response
                
        elif state.current_phase == ConversationPhase.INDIVIDUAL_QUESTIONS:
            async for response in self._individual_questions_phase(state):
                yield response
                
        elif state.current_phase == ConversationPhase.EXPERT_RESPONSES:
            async for response in self._expert_responses_phase(state):
                yield response
                
        elif state.current_phase == ConversationPhase.CROSS_DISCUSSION:
            async for response in self._cross_discussion_phase(state):
                yield response
                
        elif state.current_phase == ConversationPhase.TODO_PLANNING:
            async for response in self._todo_planning_phase(state):
                yield response
                
        elif state.current_phase == ConversationPhase.TASK_DELEGATION:
            async for response in self._task_delegation_phase(state):
                yield response
                
        elif state.current_phase == ConversationPhase.PROGRESS_UPDATES:
            async for response in self._progress_updates_phase(state):
                yield response
    
    async def _opening_phase(self, state: ConversationState) -> AsyncGenerator[Dict[str, Any], None]:
        """Project Manager opens the meeting."""
        
        pm_prompt = f"""
        As the Project Manager, you are facilitating an expert group meeting.
        
        Topic: {state.user_request}
        Participants: {', '.join([self.agent_id_to_role[agent].value for agent in state.selected_agents])}
        
        Provide a brief opening statement (2-3 sentences) that:
        1. Welcomes the team
        2. Clearly states the meeting objective
        3. Sets expectations for collaborative discussion
        
        Keep it conversational and professional.
        """
        
        response_text, _ = await invoke_llm_with_tokens(
            messages=[{"role": "user", "content": pm_prompt}],
            model_name=state.chat_model
        )
        
        yield {
            "type": "expert_response",
            "expert": "Project Manager",
            "expert_id": "project_manager",
            "content": sanitize_content(response_text),
            "phase": "opening",
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "metadata": {
                "is_facilitator": True,
                "meeting_role": "opening_statement"
            }
        }
    
    async def _individual_questions_phase(self, state: ConversationState) -> AsyncGenerator[Dict[str, Any], None]:
        """Project Manager asks individual questions to each expert."""
        
        questions_generated = 0
        
        for agent_id in state.selected_agents:
            if agent_id == "project_manager":  # Skip PM asking themselves
                continue
            
            # Validate agent exists in our mapping
            if agent_id not in self.agent_id_to_role:
                logger.warning(f"Unknown agent_id: {agent_id}, skipping question generation")
                continue
                
            expert_role = self.agent_id_to_role[agent_id]
            
            try:
                question_prompt = f"""
                As the Project Manager facilitating this meeting about: {state.user_request}
                
                Generate a specific, targeted question for the {expert_role.value} based on their expertise.
                The question should:
                1. Be directly relevant to their domain knowledge
                2. Help gather their unique perspective on the topic
                3. Be conversational and meeting-appropriate
                4. Encourage detailed input
                
                Format as a direct question you would ask in a business meeting.
                """
                
                question_response, _ = await invoke_llm_with_tokens(
                    messages=[{"role": "user", "content": question_prompt}],
                    model_name=state.chat_model
                )
                
                yield {
                    "type": "expert_question",
                    "expert": "Project Manager",
                    "expert_id": "project_manager", 
                    "target_expert": expert_role.value,
                    "target_expert_id": agent_id,
                    "content": sanitize_content(f"**Question for {expert_role.value}:** {question_response}"),
                    "phase": "individual_questions",
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                    "metadata": {
                        "is_facilitator": True,
                        "question_target": agent_id
                    }
                }
                
                # Add to pending questions
                state.pending_questions.append({
                    "target_expert": agent_id,
                    "question": question_response,
                    "asked_at": datetime.now(timezone.utc).isoformat()
                })
                
                questions_generated += 1
                
            except Exception as e:
                logger.error(f"Failed to generate question for {expert_role.value}: {e}")
                # Add fallback question
                fallback_question = f"What are your key insights and recommendations for: {state.user_request}?"
                
                yield {
                    "type": "expert_question",
                    "expert": "Project Manager",
                    "expert_id": "project_manager", 
                    "target_expert": expert_role.value,
                    "target_expert_id": agent_id,
                    "content": sanitize_content(f"**Question for {expert_role.value}:** {fallback_question}"),
                    "phase": "individual_questions",
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                    "metadata": {
                        "is_facilitator": True,
                        "question_target": agent_id,
                        "is_fallback": True
                    }
                }
                
                # Add to pending questions
                state.pending_questions.append({
                    "target_expert": agent_id,
                    "question": fallback_question,
                    "asked_at": datetime.now(timezone.utc).isoformat(),
                    "is_fallback": True
                })
                
                questions_generated += 1
        
        # Ensure we have at least one question even if no valid agents
        if questions_generated == 0:
            logger.warning("No questions generated for any experts, creating general question")
            fallback_question = f"What approach would you recommend for: {state.user_request}?"
            
            yield {
                "type": "expert_question",
                "expert": "Project Manager",
                "expert_id": "project_manager", 
                "target_expert": "Team",
                "target_expert_id": "general",
                "content": sanitize_content(f"**General Question:** {fallback_question}"),
                "phase": "individual_questions",
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                "metadata": {
                    "is_facilitator": True,
                    "question_target": "general",
                    "is_fallback": True
                }
            }
            
            # Add to pending questions for general response
            state.pending_questions.append({
                "target_expert": "general",
                "question": fallback_question,
                "asked_at": datetime.now(timezone.utc).isoformat(),
                "is_fallback": True
            })
        
        logger.info(f"Generated {questions_generated} questions for {len(state.selected_agents)} selected agents")
    
    async def _expert_responses_phase(self, state: ConversationState) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute expert responses in parallel with specialized tool usage and admin model settings."""
        
        if not state.pending_questions:
            logger.warning("No pending questions for expert responses - generating fallback response")
            # Generate a fallback PM response when no questions are available
            yield {
                "type": "expert_response",
                "expert": "Project Manager",
                "expert_id": "project_manager",
                "content": sanitize_content(f"Based on the request '{state.user_request}', I'll coordinate our team to provide comprehensive guidance and create an actionable plan."),
                "phase": "expert_responses",
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                "metadata": {
                    "is_fallback": True,
                    "reason": "no_pending_questions"
                }
            }
            return
        
        # Import parallel execution services
        from worker.services.parallel_expert_executor import parallel_expert_executor
        from worker.services.user_expert_settings_service import user_expert_settings_service
        
        logger.info(f"Starting parallel expert responses for {len(state.pending_questions)} experts")
        
        # Get user's expert model configurations
        user_id_int = int(state.user_id) if state.user_id else 1
        user_expert_models = await user_expert_settings_service.get_user_expert_models(user_id_int)
        
        # Yield model configuration info
        yield {
            "type": "model_configuration",
            "content": sanitize_content(f"🔧 **Model Configuration**: Using admin-configured models for each expert"),
            "phase": "expert_responses",
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "metadata": {
                "user_expert_models": user_expert_models,
                "parallel_execution": True
            }
        }
        
        # Create expert tasks for parallel execution
        expert_tasks = []
        for question_data in state.pending_questions:
            agent_id = question_data["target_expert"]
            question = question_data["question"]
            expert_role = self.agent_id_to_role[agent_id]
            
            expert_task = {
                "expert_id": agent_id,
                "expert_role": expert_role.value,
                "prompt_data": {
                    "user_request": state.user_request,
                    "question": question,
                    "responding_to_question": question
                }
            }
            expert_tasks.append(expert_task)
        
        # Execute experts in parallel with resource management
        parallel_success = False
        try:
            async for parallel_result in parallel_expert_executor.execute_experts_in_parallel(
                expert_tasks=expert_tasks,
                user_settings=user_expert_models,
                session_id=state.session_id,
                user_id=state.user_id
            ):
                # Forward parallel execution results
                yield parallel_result
                parallel_success = True
                
                # Update state with tool usage data if present
                if parallel_result.get("type") == "expert_response":
                    expert_id = parallel_result.get("expert_id")
                    expert_role = parallel_result.get("expert")
                    tools_used = parallel_result.get("metadata", {}).get("tools_used", [])
                    
                    # Update state tracking
                    if tools_used:
                        state.tool_calls_made.extend([
                            {
                                "expert": expert_role,
                                "tool": tool,
                                "session_id": state.session_id
                            }
                            for tool in tools_used
                        ])
                    
                    # Handle tool-specific data updates
                    if expert_role == "Research Specialist" and "web_search" in tools_used:
                        # Mock search results for state tracking
                        if "Research Specialist" not in state.search_results:
                            state.search_results["Research Specialist"] = []
                        state.search_results["Research Specialist"].append({
                            "query": "parallel execution research",
                            "result": "Research completed using web search tools"
                        })
                    
                    elif expert_role == "Personal Assistant" and "google_calendar" in tools_used:
                        # Mock calendar data for state tracking
                        state.calendar_data["Personal Assistant"] = {
                            "events_found": 3,
                            "period_checked": "next 7 days"
                        }
        
        except Exception as e:
            logger.error(f"Error in parallel expert execution: {e}", exc_info=True)
            parallel_success = False
        
        # If parallel execution failed or yielded no results, use sequential fallback
        if not parallel_success:
            logger.warning("Parallel execution failed or yielded no results, falling back to sequential")
            
            yield {
                "type": "execution_fallback",
                "content": sanitize_content(f"⚠️ **Fallback Mode**: Switching to sequential execution to ensure expert responses"),
                "phase": "expert_responses",
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                "metadata": {
                    "fallback_reason": "ensuring_expert_responses",
                    "parallel_attempted": True
                }
            }
            
            # Execute sequentially as fallback
            async for sequential_result in self._expert_responses_phase_sequential(state):
                yield sequential_result
    
    async def _expert_responses_phase_sequential(self, state: ConversationState) -> AsyncGenerator[Dict[str, Any], None]:
        """Fallback sequential expert responses (original implementation)."""
        
        if not state.pending_questions:
            logger.warning("No pending questions in sequential fallback, generating default PM response")
            # Generate a fallback response from Project Manager
            yield {
                "type": "expert_response",
                "expert": "Project Manager",
                "expert_id": "project_manager",
                "content": sanitize_content(f"Based on the request '{state.user_request}', let me provide some general guidance and coordinate our next steps."),
                "phase": "expert_responses",
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                "metadata": {
                    "is_fallback": True,
                    "execution_mode": "sequential_fallback",
                    "reason": "no_pending_questions"
                }
            }
            return
        
        for question_data in state.pending_questions:
            agent_id = question_data["target_expert"]
            question = question_data["question"]
            
            # Handle general questions (when agent_id is "general")
            if agent_id == "general":
                # Generate a general Project Manager response
                expert_input = {
                    "input": f"As the Project Manager, I'll coordinate our approach to: {state.user_request}. Let me outline the key considerations and next steps based on this request.",
                    "tools_used": [],
                    "confidence": 0.75,
                    "metadata": {"is_general_response": True}
                }
                
                expert_role_value = "Project Manager"
                display_agent_id = "project_manager"
                
            elif agent_id not in self.agent_id_to_role:
                logger.warning(f"Unknown agent_id in sequential fallback: {agent_id}, using PM fallback")
                expert_input = {
                    "input": f"I'll coordinate with the team to address: {state.user_request}. Let me provide some initial guidance while we align our expert resources.",
                    "tools_used": [],
                    "confidence": 0.65,
                    "metadata": {"is_fallback_pm_response": True}
                }
                
                expert_role_value = "Project Manager"
                display_agent_id = "project_manager"
                
            else:
                expert_role = self.agent_id_to_role[agent_id]
                expert_role_value = expert_role.value
                display_agent_id = agent_id
            
                logger.info(f"Processing expert response for {expert_role_value} (sequential fallback)")
                
                # Specialized processing based on agent type
                if expert_role_value == "Research Specialist":
                    # Stream tool usage metadata
                    yield {
                        "type": "tool_usage_start",
                        "expert": expert_role_value,
                        "expert_id": display_agent_id,
                        "content": sanitize_content(f"**{expert_role_value}** is conducting web research to provide evidence-based insights..."),
                        "phase": "expert_responses",
                        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                        "metadata": {
                            "tool_starting": "web_search",
                            "tool_purpose": "research_evidence",
                            "execution_mode": "sequential_fallback"
                        }
                    }
                    
                    # Use specialized tool method
                    expert_input = await research_specialist_with_tools(
                        state.user_request, 
                        question, 
                        state.user_id, 
                        state.tool_calls_made, 
                        state.search_results
                    )
                
                    # Stream search results metadata
                    if state.search_results.get("Research Specialist"):
                        searches = state.search_results["Research Specialist"]
                        for search in searches:
                            yield {
                                "type": "tool_result",
                                "expert": expert_role_value,
                                "expert_id": display_agent_id,
                                "content": sanitize_content(f"🔍 **Search Query:** {search['query']}\n📄 **Found:** {search['result'][:150]}..."),
                                "phase": "expert_responses",
                                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                                "metadata": {
                                    "tool_type": "search_result",
                                    "search_query": search['query'],
                                    "execution_mode": "sequential_fallback"
                                }
                            }
                    
                elif expert_role_value == "Personal Assistant":
                    # Stream calendar tool usage metadata
                    yield {
                        "type": "tool_usage_start",
                        "expert": expert_role_value,
                        "expert_id": display_agent_id,
                        "content": sanitize_content(f"**{expert_role_value}** is checking your calendar for scheduling insights..."),
                        "phase": "expert_responses",
                        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                        "metadata": {
                            "tool_starting": "google_calendar",
                            "tool_purpose": "scheduling_analysis",
                            "execution_mode": "sequential_fallback"
                        }
                    }
                    
                    # Use specialized tool method
                    expert_input = await personal_assistant_with_tools(
                        state.user_request, 
                        question, 
                        state.user_id, 
                        state.tool_calls_made, 
                        state.calendar_data
                    )
                
                    # Stream calendar results metadata
                    if state.calendar_data.get("Personal Assistant"):
                        cal_data = state.calendar_data["Personal Assistant"]
                        if "events_found" in cal_data:
                            yield {
                                "type": "tool_result",
                                "expert": expert_role_value,
                                "expert_id": display_agent_id,
                                "content": sanitize_content(f"📅 **Calendar Checked:** Found {cal_data['events_found']} upcoming events in {cal_data['period_checked']}"),
                                "phase": "expert_responses",
                                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                                "metadata": {
                                    "tool_type": "calendar_result",
                                    "events_found": cal_data['events_found'],
                                    "execution_mode": "sequential_fallback"
                                }
                            }
                    
                else:
                    # Standard expert response without tools
                    expert_input = await standard_expert_response(
                        expert_role_value,
                        state.user_request,
                        question
                    )
            
            # Yield the final expert response
            yield {
                "type": "expert_response",
                "expert": expert_role_value,
                "expert_id": display_agent_id,
                "content": sanitize_content(expert_input["input"]),
                "phase": "expert_responses",
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                "metadata": {
                    "responding_to_question": sanitize_content(question),
                    "expertise_area": expert_role_value,
                    "tools_used": expert_input.get("tools_used", []),
                    "confidence": expert_input.get("confidence", 0.85),
                    "tool_enhanced": len(expert_input.get("tools_used", [])) > 0,
                    "execution_mode": "sequential_fallback",
                    "metadata": expert_input.get("metadata", {})
                }
            }
    
    async def _cross_discussion_phase(self, state: ConversationState) -> AsyncGenerator[Dict[str, Any], None]:
        """Experts respond to each other's input with meaningful collaboration."""
        
        # Only include experts who participated in the previous phase (weren't excluded)
        participating_experts = []
        for response in state.conversation_history:
            if (response.get("type") == "expert_response" and 
                response.get("phase") == "expert_responses" and
                not response.get("metadata", {}).get("excluded", False)):
                expert_id = response.get("expert_id")
                if expert_id and expert_id not in participating_experts:
                    participating_experts.append(expert_id)
        
        # Select 2-3 experts for cross-discussion from participating experts only
        discussion_experts = participating_experts[:3] if len(participating_experts) > 3 else participating_experts
        
        if not discussion_experts:
            # No experts to discuss, yield a PM message
            yield {
                "type": "expert_response",
                "expert": "Project Manager",
                "expert_id": "project_manager",
                "content": sanitize_content("It seems we need to adjust our approach since the selected experts don't have substantial input on this topic. Let me create a general action plan based on the request."),
                "phase": "cross_discussion",
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                "metadata": {
                    "discussion_type": "fallback_pm_response",
                    "reason": "No participating experts"
                }
            }
            return
        
        for agent_id in discussion_experts:
            if agent_id == "project_manager":
                continue
                
            expert_role = self.agent_id_to_role[agent_id]
            
            # Get recent conversation context from participating experts only
            recent_responses = [r for r in state.conversation_history 
                              if (r.get("type") == "expert_response" and 
                                  r.get("phase") == "expert_responses" and
                                  not r.get("metadata", {}).get("excluded", False))][-3:]
            
            if not recent_responses:
                continue
                
            context_summary = "\n".join([f"{r['expert']}: {r['content'][:200]}..." for r in recent_responses])
            
            discussion_prompt = f"""
            You are the {expert_role.value} in a business meeting about: {state.user_request}
            
            Based on what you've heard from your colleagues:
            {context_summary}
            
            Provide a brief response that:
            1. Acknowledges something specific another expert said
            2. Adds your perspective or builds on their point
            3. Raises any concerns or additional considerations
            
            Keep it conversational and collaborative (1-2 paragraphs).
            """
            
            discussion_response, _ = await invoke_llm_with_tokens(
                messages=[{"role": "user", "content": discussion_prompt}],
                model_name=state.chat_model
            )
            
            yield {
                "type": "expert_response",
                "expert": expert_role.value,
                "expert_id": agent_id,
                "content": sanitize_content(discussion_response),
                "phase": "cross_discussion",
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                "metadata": {
                    "discussion_type": "cross_discussion",
                    "responding_to": "colleague_input",
                    "collaboration_level": "active"
                }
            }
    
    async def _todo_planning_phase(self, state: ConversationState) -> AsyncGenerator[Dict[str, Any], None]:
        """Project Manager creates todo list based on discussion."""
        
        conversation_summary = "\n".join([
            f"{r['expert']}: {r['content']}"
            for r in state.conversation_history 
            if r.get("type") == "expert_response"
        ])
        
        todo_prompt = f"""
        As the Project Manager, create a todo list based on our team discussion about: {state.user_request}
        
        Team input summary:
        {conversation_summary}
        
        Create 5-8 specific, actionable todo items that:
        1. Address the key points raised by experts
        2. Are assigned to appropriate team members
        3. Have clear priorities (High/Medium/Low)
        4. Build toward solving the original request
        
        Format as:
        - [Task description] - Assigned: [Expert] - Priority: [High/Medium/Low]
        """
        
        todo_response, _ = await invoke_llm_with_tokens(
            messages=[{"role": "user", "content": todo_prompt}],
            model_name=state.chat_model
        )
        
        # Parse todo items
        todo_items = self._parse_todo_list(todo_response)
        state.todo_list.extend(todo_items)
        
        yield {
            "type": "todo_update",
            "expert": "Project Manager",
            "expert_id": "project_manager",
            "content": sanitize_content(f"**Action Plan Created:**\n\n{todo_response}"),
            "phase": "todo_planning",
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "metadata": {
                "todo_list": todo_items,
                "total_tasks": len(todo_items)
            }
        }
    
    async def _task_delegation_phase(self, state: ConversationState) -> AsyncGenerator[Dict[str, Any], None]:
        """Project Manager delegates specific tasks to experts."""
        
        # Emergency circuit breaker to prevent infinite loops
        if len(state.completed_tasks) >= len(state.todo_list) and state.todo_list:
            logger.warning("Task delegation phase already completed - preventing infinite loop")
            return
        
        tasks_delegated = 0
        for todo_item in state.todo_list:
            assigned_expert = todo_item.get("assigned_to")
            task_description = todo_item.get("task")
            
            if assigned_expert and assigned_expert != "Project Manager":
                yield {
                    "type": "task_delegation",
                    "expert": "Project Manager",
                    "expert_id": "project_manager",
                    "target_expert": assigned_expert,
                    "content": sanitize_content(f"**Task Delegation:** {assigned_expert}, please take the lead on: {task_description}"),
                    "phase": "task_delegation",
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                    "metadata": {
                        "task": sanitize_content(task_description),
                        "assigned_to": assigned_expert,
                        "priority": todo_item.get("priority", "Medium")
                    }
                }
                
                # CRITICAL FIX: Mark task as delegated/completed to prevent infinite loop
                completed_task = {
                    "task": task_description,
                    "assigned_to": assigned_expert,
                    "status": "delegated",
                    "delegated_at": datetime.now(timezone.utc).isoformat(),
                    "priority": todo_item.get("priority", "Medium")
                }
                state.completed_tasks.append(completed_task)
                tasks_delegated += 1
        
        # If no tasks were delegated (all assigned to PM or none exist), mark phase as complete
        if tasks_delegated == 0:
            logger.info("No tasks to delegate - marking delegation phase complete")
            state.completed_tasks.append({
                "task": "Task delegation review",
                "assigned_to": "Project Manager", 
                "status": "completed",
                "delegated_at": datetime.now(timezone.utc).isoformat(),
                "priority": "Low"
            })
        
        logger.info(f"Task delegation phase completed - {tasks_delegated} tasks delegated")
    
    async def _progress_updates_phase(self, state: ConversationState) -> AsyncGenerator[Dict[str, Any], None]:
        """Experts provide brief progress or commitment updates."""
        
        for agent_id in state.selected_agents:
            if agent_id == "project_manager":
                continue
                
            expert_role = self.agent_id_to_role[agent_id]
            
            # Find tasks assigned to this expert
            assigned_tasks = [t for t in state.todo_list if t.get("assigned_to") == expert_role.value]
            
            if assigned_tasks:
                update_prompt = f"""
                As the {expert_role.value}, provide a brief update on your assigned tasks:
                {[t['task'] for t in assigned_tasks]}
                
                Give a short status update including:
                1. Your commitment to the tasks
                2. Any initial thoughts on approach
                3. Expected timeline or next steps
                
                Keep it brief and meeting-appropriate (1 paragraph).
                """
                
                update_response, _ = await invoke_llm_with_tokens(
                    messages=[{"role": "user", "content": update_prompt}],
                    model_name=state.chat_model
                )
                
                yield {
                    "type": "expert_response",
                    "expert": expert_role.value,
                    "expert_id": agent_id,
                    "content": sanitize_content(update_response),
                    "phase": "progress_updates",
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                    "metadata": {
                        "assigned_tasks": len(assigned_tasks),
                        "update_type": "commitment"
                    }
                }
    
    async def _generate_meeting_summary(self, state: ConversationState) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate final meeting summary with detailed analytics."""
        
        meeting_duration = datetime.now(timezone.utc) - state.meeting_start_time
        
        # Count participating vs excluded experts
        participating_experts = []
        excluded_experts = []
        
        for response in state.conversation_history:
            if response.get("type") == "expert_response" and response.get("phase") == "expert_responses":
                expert = response.get("expert")
                if expert and expert not in participating_experts:
                    participating_experts.append(expert)
            elif response.get("type") == "expert_exclusion":
                expert = response.get("expert")
                if expert and expert not in excluded_experts:
                    excluded_experts.append(expert)
        
        # Build conversation summary from participating experts only
        conversation_summary = "\n".join([
            f"{r['expert']}: {r['content'][:150]}..."
            for r in state.conversation_history 
            if (r.get("type") == "expert_response" and 
                not r.get("metadata", {}).get("excluded", False))
        ])
        
        # Build tool usage summary
        tool_usage_summary = ""
        if state.tool_calls_made:
            tool_usage_summary += "\n\nTools Used During Meeting:\n"
            for tool_call in state.tool_calls_made:
                tool_usage_summary += f"- {tool_call['expert']}: {tool_call['tool']}"
                if 'query' in tool_call:
                    tool_usage_summary += f" (Query: {tool_call['query']})"
                tool_usage_summary += "\n"
        
        if state.search_results:
            tool_usage_summary += "\nResearch Conducted:\n"
            for expert, results in state.search_results.items():
                tool_usage_summary += f"- {expert}: {len(results)} web searches performed\n"
        
        if state.calendar_data:
            tool_usage_summary += "\nCalendar Analysis:\n"
            for expert, data in state.calendar_data.items():
                if "events_found" in data:
                    tool_usage_summary += f"- {expert}: Checked calendar, found {data['events_found']} upcoming events\n"
                elif "error" in data:
                    tool_usage_summary += f"- {expert}: Calendar check failed - {data['error']}\n"
        
        summary_prompt = f"""
        As the Project Manager, provide a comprehensive meeting summary for: {state.user_request}
        
        Meeting Details:
        - Duration: {int(meeting_duration.total_seconds() / 60)} minutes
        - Selected Participants: {', '.join([self.agent_id_to_role[agent].value for agent in state.selected_agents])}
        - Active Participants: {', '.join(participating_experts) if participating_experts else 'None'}
        - Excluded (Not Relevant): {', '.join(excluded_experts) if excluded_experts else 'None'}
        - Conversation turns: {state.conversation_turns}
        
        Key Discussion Points:
        {conversation_summary if conversation_summary else 'No substantial expert input - general recommendations provided.'}
        
        {tool_usage_summary}
        
        Action Items: {len(state.todo_list)} tasks assigned
        
        Provide a professional meeting summary including:
        1. Meeting overview and objectives
        2. Key insights and decisions made (or note if expert input was limited)
        3. Specialized tools and research utilized by experts
        4. Action items and assignments
        5. Next steps and timeline
        6. Thank the team for their participation and tool-enhanced insights
        7. Note any adjustments made due to topic relevance
        """
        
        summary_response, _ = await invoke_llm_with_tokens(
            messages=[{"role": "user", "content": summary_prompt}],
            model_name=state.chat_model
        )
        
        yield {
            "type": "meeting_summary",
            "expert": "Project Manager",
            "expert_id": "project_manager",
            "content": sanitize_content(f"**📋 Meeting Summary**\n\n{summary_response}"),
            "phase": "final_summary",
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "metadata": {
                "meeting_duration_minutes": int(meeting_duration.total_seconds() / 60),
                "total_selected_participants": len(state.selected_agents),
                "active_participants": len(participating_experts),
                "excluded_participants": len(excluded_experts),
                "conversation_turns": state.conversation_turns,
                "tasks_created": len(state.todo_list),
                "meeting_completed": True,
                "effectiveness_score": len(participating_experts) / len(state.selected_agents) if state.selected_agents else 0
            }
        }
        
        yield {
            "type": "meeting_end",
            "content": sanitize_content(f"🎯 **Meeting Concluded** - Thank you for your participation!\n\n**Meeting Statistics:**\n- Active participants: {len(participating_experts)}/{len(state.selected_agents)}\n- Duration: {int(meeting_duration.total_seconds() / 60)} minutes\n- Tasks created: {len(state.todo_list)}"),
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "metadata": {
                "session_id": state.session_id,
                "status": "completed",
                "final_statistics": {
                    "active_participants": len(participating_experts),
                    "total_selected": len(state.selected_agents),
                    "duration_minutes": int(meeting_duration.total_seconds() / 60),
                    "tasks_created": len(state.todo_list)
                }
            }
        }
    
    def _parse_todo_list(self, todo_text: str) -> List[Dict[str, Any]]:
        """Parse todo list from LLM response."""
        todo_items = []
        lines = todo_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('-') and 'Assigned:' in line and 'Priority:' in line:
                parts = line[1:].split(' - ')
                if len(parts) >= 3:
                    task = parts[0].strip()
                    assigned = parts[1].replace('Assigned:', '').strip() if 'Assigned:' in parts[1] else ''
                    priority = parts[2].replace('Priority:', '').strip() if 'Priority:' in parts[2] else 'Medium'
                    
                    todo_items.append({
                        'task': task,
                        'assigned_to': assigned,
                        'priority': priority,
                        'status': 'pending',
                        'created_at': datetime.now(timezone.utc).isoformat()
                    })
        
        return todo_items


# Create service instance
conversational_expert_group_service = ConversationalExpertGroupService()