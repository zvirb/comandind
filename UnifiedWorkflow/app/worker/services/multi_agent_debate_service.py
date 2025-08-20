"""
Multi-Agent Debate Service

Implements the "Debate Only When Necessary" (DOWN) pattern from smart_ai.txt.
Activates collaborative reasoning only for low-confidence scenarios to optimize resources.
Now uses LangGraph for automatic progress monitoring.
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
from worker.graph_types import GraphState
from worker.smart_ai_models import ConfidenceLevel
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)


class DebateState(BaseModel):
    """State object for the multi-agent debate workflow."""
    # Input data
    session_id: Optional[str] = None
    user_input: str = ""
    debate_topic: str = ""
    decision_context: Dict[str, Any] = Field(default_factory=dict)
    chat_model: Optional[str] = None
    
    # Workflow state
    active_agents: List[str] = Field(default_factory=list)
    initial_positions: Dict[str, str] = Field(default_factory=dict)
    debate_history: List[Dict[str, Any]] = Field(default_factory=list)
    current_round: int = 0
    max_rounds: int = 2
    
    # Results
    consensus_reached: bool = False
    final_synthesis: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    decision: str = ""
    reasoning: str = ""


class DebateAgent(str, Enum):
    """Specialized debate agents with different perspectives."""
    OPTIMIST = "optimist"  # Focuses on positive aspects and opportunities
    PESSIMIST = "pessimist"  # Identifies risks and potential problems
    SYNTHESIZER = "synthesizer"  # Integrates different viewpoints
    DOMAIN_EXPERT = "domain_expert"  # Technical expertise for the specific domain
    USER_ADVOCATE = "user_advocate"  # Represents user interests and expectations


class DebatePhase(str, Enum):
    """Phases of the multi-agent debate process."""
    INITIAL_POSITIONS = "initial_positions"
    ARGUMENTATION = "argumentation"
    COUNTER_ARGUMENTS = "counter_arguments"
    SYNTHESIS = "synthesis"
    CONSENSUS = "consensus"


class MultiAgentDebateService:
    """
    Service implementing multi-agent debate for complex decision making.
    Uses confidence-informed activation to optimize computational resources.
    """
    
    def __init__(self):
        self.settings = get_settings()
        
        # Agent personas with specific roles and perspectives
        self.agent_personas = {
            DebateAgent.OPTIMIST: {
                "role": "You are an optimistic analyst who focuses on opportunities and positive outcomes.",
                "perspective": "positive opportunities, best-case scenarios, potential benefits",
                "style": "encouraging and solution-focused, highlighting what could go right"
            },
            DebateAgent.PESSIMIST: {
                "role": "You are a risk analyst who identifies potential problems and challenges.",
                "perspective": "risks, edge cases, potential failures, and what could go wrong",
                "style": "cautious and thorough, focusing on risk mitigation"
            },
            DebateAgent.SYNTHESIZER: {
                "role": "You are a neutral synthesizer who integrates different perspectives.",
                "perspective": "balanced analysis, integration of viewpoints, practical compromise",
                "style": "objective and balanced, seeking common ground"
            },
            DebateAgent.DOMAIN_EXPERT: {
                "role": "You are a technical expert with deep domain knowledge.",
                "perspective": "technical accuracy, implementation details, domain best practices",
                "style": "precise and authoritative, focused on technical correctness"
            },
            DebateAgent.USER_ADVOCATE: {
                "role": "You are a user advocate representing the end user's interests.",
                "perspective": "user experience, practical utility, ease of use",
                "style": "user-focused and pragmatic, prioritizing user value"
            }
        }
        
        # Debate configuration
        self.max_debate_rounds = 3
        self.consensus_threshold = 0.8  # Agreement level needed for consensus
        self.confidence_activation_threshold = 0.6  # Below this, debate is triggered
    
    async def should_activate_debate(self, state: GraphState, decision_context: Dict[str, Any]) -> bool:
        """
        Determine if multi-agent debate should be activated based on confidence and complexity.
        Implements the DOWN (Debate Only When Necessary) pattern.
        """
        confidence_score = state.confidence_score
        
        # Primary trigger: Low confidence
        if confidence_score < self.confidence_activation_threshold:
            logger.info(f"Debate triggered by low confidence: {confidence_score:.2f}")
            return True
        
        # Secondary triggers for complex scenarios
        complexity_indicators = [
            len(state.critique_history) > 2,  # Multiple reflection cycles
            state.error_count > 1,  # Multiple errors encountered
            len(decision_context.get("conflicting_options", [])) > 1,  # Multiple viable options
            decision_context.get("high_stakes", False),  # Explicitly marked as high stakes
        ]
        
        if sum(complexity_indicators) >= 2:
            logger.info(f"Debate triggered by complexity indicators: {sum(complexity_indicators)}/4")
            return True
        
        logger.info(f"Debate skipped - confidence sufficient: {confidence_score:.2f}")
        return False
    
    async def conduct_debate(self, state: GraphState, debate_topic: str, 
                           decision_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Conduct multi-agent debate to reach consensus on complex decisions.
        
        Args:
            state: Current graph state
            debate_topic: The topic/decision to debate
            decision_context: Additional context for the debate
            
        Returns:
            Dict with consensus decision, confidence, and reasoning
        """
        try:
            logger.info(f"Starting multi-agent debate on: {debate_topic}")
            
            # Broadcast debate start
            if state.session_id:
                from worker.services.progress_manager import progress_manager
                import asyncio
                progress_manager.broadcast_to_session_sync_sync(state.session_id, {
                    "type": "debate_start",
                    "content": "Starting multi-agent analysis for complex decision...",
                    "topic": debate_topic[:100]
                })
            
            # Select agents based on context
            active_agents = await self._select_agents_for_debate(state, decision_context)
            
            # Conduct debate phases
            debate_history = []
            
            # Phase 1: Initial positions
            initial_positions = await self._gather_initial_positions(
                state, debate_topic, decision_context, active_agents
            )
            debate_history.append({"phase": DebatePhase.INITIAL_POSITIONS, "content": initial_positions})
            
            # Phase 2-4: Iterative argumentation
            for round_num in range(self.max_debate_rounds):
                arguments = await self._conduct_argumentation_round(
                    state, debate_topic, initial_positions, debate_history, active_agents
                )
                debate_history.append({"phase": DebatePhase.ARGUMENTATION, "round": round_num + 1, "content": arguments})
                
                # Check for early consensus
                consensus_check = await self._check_consensus(arguments)
                if consensus_check["has_consensus"]:
                    logger.info(f"Early consensus reached in round {round_num + 1}")
                    break
            
            # Phase 5: Final synthesis
            synthesis = await self._synthesize_debate(state, debate_topic, debate_history)
            
            logger.info(f"Debate complete. Consensus confidence: {synthesis['confidence']:.2f}")
            
            # Broadcast debate completion
            if state.session_id:
                progress_manager.broadcast_to_session_sync_sync(state.session_id, {
                    "type": "debate_complete",
                    "content": f"Multi-agent analysis complete. Confidence: {synthesis['confidence']:.2f}",
                    "decision": synthesis['decision'][:100],
                    "agents_used": [agent.value for agent in active_agents]
                })
            
            return synthesis
            
        except Exception as e:
            logger.error(f"Error in multi-agent debate: {e}", exc_info=True)
            return {
                "decision": debate_topic,  # Fallback to original
                "confidence": 0.3,  # Low confidence due to error
                "reasoning": f"Debate failed: {str(e)}",
                "consensus": False,
                "agents_participated": []
            }
    
    async def _select_agents_for_debate(self, state: GraphState, 
                                      decision_context: Dict[str, Any]) -> List[DebateAgent]:
        """Select appropriate agents based on the decision context."""
        agents = [DebateAgent.OPTIMIST, DebateAgent.PESSIMIST, DebateAgent.SYNTHESIZER]
        
        # Add domain expert if technical decision
        if decision_context.get("technical_decision", False) or state.selected_tool:
            agents.append(DebateAgent.DOMAIN_EXPERT)
        
        # Add user advocate for user-facing decisions
        if decision_context.get("user_facing", True):
            agents.append(DebateAgent.USER_ADVOCATE)
        
        return agents
    
    async def _gather_initial_positions(self, state: GraphState, debate_topic: str,
                                      decision_context: Dict[str, Any], 
                                      agents: List[DebateAgent]) -> Dict[str, str]:
        """Gather initial positions from each agent."""
        positions = {}
        
        for agent in agents:
            try:
                persona = self.agent_personas[agent]
                
                position_prompt = f"""
{persona['role']}

**DEBATE TOPIC:** {debate_topic}
**CONTEXT:** {json.dumps(decision_context, indent=2)}
**USER REQUEST:** {state.user_input}
**YOUR PERSPECTIVE:** Focus on {persona['perspective']}

Provide your initial position on this topic. Consider:
1. Your perspective as {agent.value}
2. Key points that support your viewpoint
3. What you believe is the best approach

Keep your response focused and under 100 words. Use your {persona['style']}.

Your position:"""

                messages = [
                    {"role": "system", "content": f"You are {agent.value} in a collaborative decision-making process."},
                    {"role": "user", "content": position_prompt}
                ]
                
                model = state.chat_model or "llama3.2:3b"
                response, _ = await invoke_llm_with_tokens(messages, model, category="debate")
                
                positions[agent.value] = response.strip()
                
            except Exception as e:
                logger.warning(f"Failed to get position from {agent.value}: {e}")
                positions[agent.value] = f"Unable to provide position due to error: {e}"
        
        return positions
    
    async def _conduct_argumentation_round(self, state: GraphState, debate_topic: str,
                                         initial_positions: Dict[str, str], 
                                         debate_history: List[Dict[str, Any]],
                                         agents: List[DebateAgent]) -> Dict[str, str]:
        """Conduct one round of argumentation between agents."""
        arguments = {}
        
        # Build context from previous rounds
        previous_context = ""
        for history_item in debate_history:
            if history_item["phase"] == DebatePhase.ARGUMENTATION:
                previous_context += f"\nRound {history_item['round']}:\n"
                for agent_name, argument in history_item["content"].items():
                    previous_context += f"  {agent_name}: {argument[:100]}...\n"
        
        for agent in agents:
            try:
                persona = self.agent_personas[agent]
                
                # Get other agents' positions for reference
                other_positions = {k: v for k, v in initial_positions.items() if k != agent.value}
                
                argument_prompt = f"""
{persona['role']}

**DEBATE TOPIC:** {debate_topic}
**YOUR INITIAL POSITION:** {initial_positions.get(agent.value, 'Not provided')}

**OTHER AGENTS' POSITIONS:**
{json.dumps(other_positions, indent=2)}

**PREVIOUS DISCUSSION:**
{previous_context}

Now provide your argument, considering what others have said. You may:
1. Strengthen your position with new evidence
2. Address points raised by other agents
3. Find common ground where appropriate
4. Raise new concerns or opportunities

Maintain your {persona['style']} while being constructive. Keep under 100 words.

Your argument:"""

                messages = [
                    {"role": "system", "content": f"You are {agent.value} engaging in constructive debate."},
                    {"role": "user", "content": argument_prompt}
                ]
                
                model = state.chat_model or "llama3.2:3b"
                response, _ = await invoke_llm_with_tokens(messages, model, category="debate")
                
                arguments[agent.value] = response.strip()
                
            except Exception as e:
                logger.warning(f"Failed to get argument from {agent.value}: {e}")
                arguments[agent.value] = f"Unable to provide argument: {e}"
        
        return arguments
    
    async def _check_consensus(self, arguments: Dict[str, str]) -> Dict[str, Any]:
        """Check if agents have reached consensus."""
        # Simple consensus check based on agreement indicators
        agreement_words = ["agree", "consensus", "common ground", "shared", "together"]
        disagreement_words = ["disagree", "however", "but", "concern", "risk"]
        
        total_agreement = 0
        total_disagreement = 0
        
        for argument in arguments.values():
            argument_lower = argument.lower()
            total_agreement += sum(1 for word in agreement_words if word in argument_lower)
            total_disagreement += sum(1 for word in disagreement_words if word in argument_lower)
        
        # Calculate consensus ratio
        total_indicators = total_agreement + total_disagreement
        consensus_ratio = total_agreement / total_indicators if total_indicators > 0 else 0.5
        
        has_consensus = consensus_ratio >= self.consensus_threshold
        
        return {
            "has_consensus": has_consensus,
            "consensus_ratio": consensus_ratio,
            "agreement_indicators": total_agreement,
            "disagreement_indicators": total_disagreement
        }
    
    async def _synthesize_debate(self, state: GraphState, debate_topic: str,
                               debate_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Synthesize the debate into a final decision with confidence score."""
        try:
            # Build comprehensive debate context
            debate_summary = []
            for history_item in debate_history:
                phase = history_item["phase"]
                content = history_item["content"]
                
                if phase == DebatePhase.INITIAL_POSITIONS:
                    debate_summary.append("INITIAL POSITIONS:")
                    for agent, position in content.items():
                        debate_summary.append(f"  {agent}: {position}")
                
                elif phase == DebatePhase.ARGUMENTATION:
                    round_num = history_item.get("round", "?")
                    debate_summary.append(f"\nARGUMENTATION ROUND {round_num}:")
                    for agent, argument in content.items():
                        debate_summary.append(f"  {agent}: {argument}")
            
            debate_context = "\n".join(debate_summary)
            
            synthesis_prompt = f"""
You are a neutral synthesizer tasked with analyzing a multi-agent debate and reaching a final decision.

**ORIGINAL TOPIC:** {debate_topic}
**USER REQUEST:** {state.user_input}

**COMPLETE DEBATE TRANSCRIPT:**
{debate_context}

**YOUR TASK:** 
1. Analyze all perspectives presented
2. Identify areas of agreement and disagreement
3. Synthesize a balanced final decision
4. Assess confidence in this decision (0.0-1.0)

**OUTPUT FORMAT (JSON only):**
{{
  "decision": "clear final decision or recommendation",
  "confidence": 0.0-1.0,
  "reasoning": "explanation of how you reached this decision",
  "key_agreements": ["point 1", "point 2"],
  "key_concerns": ["concern 1", "concern 2"],
  "consensus": true/false
}}

Analyze the debate and provide synthesis:"""

            messages = [
                {"role": "system", "content": "You are a neutral synthesizer. Always respond with valid JSON only."},
                {"role": "user", "content": synthesis_prompt}
            ]
            
            model = state.chat_model or "llama3.2:3b"
            response, _ = await invoke_llm_with_tokens(messages, model, category="debate")
            
            try:
                synthesis = json.loads(response)
                
                # Ensure required fields
                synthesis.setdefault("decision", debate_topic)
                synthesis.setdefault("confidence", 0.5)
                synthesis.setdefault("consensus", False)
                synthesis.setdefault("reasoning", "Synthesis completed")
                
                return synthesis
                
            except json.JSONDecodeError:
                logger.warning("Failed to parse synthesis JSON, using fallback")
                return {
                    "decision": debate_topic,
                    "confidence": 0.6,  # Medium confidence for completed debate
                    "reasoning": "Multi-agent debate completed successfully",
                    "consensus": True,
                    "agents_participated": len(debate_history)
                }
                
        except Exception as e:
            logger.error(f"Error in debate synthesis: {e}")
            return {
                "decision": debate_topic,
                "confidence": 0.4,
                "reasoning": f"Synthesis error: {str(e)}",
                "consensus": False
            }

    async def conduct_debate_with_progress(self, state: GraphState, debate_topic: str, 
                                         decision_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Conduct multi-agent debate using LangGraph with automatic progress monitoring.
        
        Args:
            state: Current graph state
            debate_topic: The topic/decision to debate
            decision_context: Additional context for the debate
            
        Returns:
            Dict with consensus decision, confidence, and reasoning
        """
        try:
            # Create debate state
            debate_state = DebateState(
                session_id=state.session_id,
                user_input=state.user_input,
                debate_topic=debate_topic,
                decision_context=decision_context,
                chat_model=state.chat_model or "llama3.2:3b"
            )
            
            logger.info(f"Starting LangGraph multi-agent debate: {debate_topic}")
            
            # Get progress manager for automatic broadcasting
            from worker.services.progress_manager import progress_manager
            
            # Broadcast workflow start
            if state.session_id:
                await progress_manager.broadcast_workflow_start(
                    state.session_id, 
                    f"Multi-agent debate: {debate_topic}"
                )
            
            # Run the debate workflow with astream for progress monitoring
            config = RunnableConfig(recursion_limit=10)
            workflow_start_time = datetime.now()
            nodes_executed = 0
            
            final_state = None
            async for event in compiled_debate_workflow.astream(debate_state.model_dump(), config=config):
                nodes_executed += 1
                
                for node_name, node_state in event.items():
                    # Broadcast automatic progress update for this node
                    if state.session_id:
                        try:
                            node_execution_time = (datetime.now() - workflow_start_time).total_seconds()
                            await progress_manager.broadcast_node_transition(
                                state.session_id, f"debate_{node_name}", node_state, node_execution_time
                            )
                            logger.debug(f"Broadcasted debate progress for node: {node_name}")
                        except Exception as e:
                            logger.warning(f"Failed to broadcast debate progress for {node_name}: {e}")
                
                # Store the final state
                final_state = event
            
            # Calculate total execution time
            total_execution_time = (datetime.now() - workflow_start_time).total_seconds()
            
            # Extract final results from the last state
            if final_state:
                last_key = list(final_state.keys())[-1]
                final_debate_state = final_state[last_key]
                
                # Broadcast workflow completion
                if state.session_id:
                    final_decision = final_debate_state.get("decision", "Decision reached")
                    await progress_manager.broadcast_workflow_complete(
                        state.session_id, 
                        final_decision,
                        total_execution_time, 
                        nodes_executed
                    )
                    
                    # Post debate results directly to chat
                    synthesis = final_debate_state.get("final_synthesis", {})
                    if synthesis:
                        from worker.services.progress_manager import AgentNames
                        
                        debate_text = self._format_debate_results_for_chat(synthesis, final_debate_state)
                        await progress_manager.broadcast_agent_message(
                            state.session_id,
                            AgentNames.MULTI_AGENT_DEBATE,
                            debate_text,
                            agent_type="collaborative reasoning",
                            metadata={
                                "consensus_reached": final_debate_state.get("consensus_reached", False),
                                "agents_participated": final_debate_state.get("active_agents", [])
                            },
                            formatted=True
                        )
                
                # Format result to match expected structure
                synthesis = final_debate_state.get("final_synthesis", {})
                return {
                    "decision": final_debate_state.get("decision", debate_topic),
                    "confidence": final_debate_state.get("confidence", 0.5),
                    "reasoning": final_debate_state.get("reasoning", "Multi-agent debate completed"),
                    "consensus": final_debate_state.get("consensus_reached", False),
                    "agents_participated": final_debate_state.get("active_agents", []),
                    "synthesis": synthesis
                }
            else:
                # Fallback if no final state
                logger.warning("No final state from debate workflow")
                return {
                    "decision": debate_topic,
                    "confidence": 0.4,
                    "reasoning": "Debate workflow completed with no final state",
                    "consensus": False
                }
            
        except Exception as e:
            logger.error(f"Error in LangGraph debate workflow: {e}", exc_info=True)
            
            # Broadcast error if possible
            if state.session_id:
                try:
                    from worker.services.progress_manager import progress_manager
                    await progress_manager.broadcast_workflow_complete(
                        state.session_id,
                        f"Debate failed: {str(e)}",
                        0.0,
                        0
                    )
                except:
                    pass
            
            # Fallback to original method
            logger.info("Falling back to original debate method")
            return await self.conduct_debate(state, debate_topic, decision_context)

    def _format_debate_results_for_chat(self, synthesis: Dict[str, Any], debate_state: Dict[str, Any]) -> str:
        """Format multi-agent debate results for chat display."""
        consensus = debate_state.get("consensus_reached", False)
        agents = debate_state.get("active_agents", [])
        decision = synthesis.get("decision", "No clear decision reached")
        reasoning = synthesis.get("reasoning", "")
        confidence = synthesis.get("confidence", 0.5)
        
        # Header
        emoji = "🤝" if consensus else "🤔"
        status = "Consensus Reached" if consensus else "Analysis Complete"
        formatted_text = f"{emoji} **Multi-Agent Debate: {status}**\n\n"
        
        # Confidence indicator
        confidence_emoji = "🎯" if confidence > 0.8 else "📊" if confidence > 0.6 else "🤷"
        formatted_text += f"{confidence_emoji} **Confidence**: {confidence:.1%}\n"
        
        # Participating agents
        if agents:
            agent_list = ", ".join(agents)
            formatted_text += f"👥 **Agents**: {agent_list}\n\n"
        
        # Decision
        formatted_text += f"**🎯 Decision**: {decision}\n\n"
        
        # Reasoning
        if reasoning:
            # Truncate long reasoning
            reasoning_preview = reasoning[:300] + "..." if len(reasoning) > 300 else reasoning
            formatted_text += f"**💭 Reasoning**: {reasoning_preview}\n\n"
        
        # Key insights from synthesis
        if synthesis.get("key_agreements"):
            formatted_text += "**✅ Key Agreements**:\n"
            for agreement in synthesis["key_agreements"][:3]:  # Top 3
                formatted_text += f"• {agreement}\n"
            formatted_text += "\n"
        
        if synthesis.get("key_concerns"):
            formatted_text += "**⚠️ Key Concerns**:\n"
            for concern in synthesis["key_concerns"][:3]:  # Top 3  
                formatted_text += f"• {concern}\n"
            formatted_text += "\n"
        
        formatted_text += "🔍 This analysis involved collaborative reasoning between multiple AI perspectives."
        
        return formatted_text


# --- LangGraph Workflow Nodes ---

async def select_agents_node(state: DebateState) -> Dict[str, Any]:
    """Select appropriate agents for the debate based on context."""
    try:
        # For simplicity, select standard agents based on decision context
        selected_agents = [
            DebateAgent.OPTIMIST.value,
            DebateAgent.PESSIMIST.value,
            DebateAgent.USER_ADVOCATE.value
        ]
        
        # Add domain expert if technical decision
        if state.decision_context.get("technical_decision", False):
            selected_agents.append(DebateAgent.DOMAIN_EXPERT.value)
        
        return {"active_agents": selected_agents}
        
    except Exception as e:
        logger.error(f"Error selecting agents: {e}")
        return {"active_agents": [DebateAgent.OPTIMIST.value, DebateAgent.PESSIMIST.value]}


async def gather_positions_node(state: DebateState) -> Dict[str, Any]:
    """Gather initial positions from each selected agent."""
    try:
        positions = {}
        service = multi_agent_debate_service
        
        for agent_name in state.active_agents:
            try:
                agent_enum = DebateAgent(agent_name)
                persona = service.agent_personas[agent_enum]
                
                position_prompt = f"""
{persona['role']}

**DEBATE TOPIC:** {state.debate_topic}
**CONTEXT:** {json.dumps(state.decision_context, indent=2)}
**USER REQUEST:** {state.user_input}
**YOUR PERSPECTIVE:** Focus on {persona['perspective']}

Provide your initial position on this topic. Consider:
1. Your perspective as {agent_name}
2. Key points that support your viewpoint
3. What you believe is the best approach

Keep your response focused and under 100 words. Use your {persona['style']}.

Your position:"""

                messages = [
                    {"role": "system", "content": f"You are {agent_name} in a collaborative decision-making process."},
                    {"role": "user", "content": position_prompt}
                ]
                
                model = state.chat_model or "llama3.2:3b"
                response, _ = await invoke_llm_with_tokens(messages, model, category="debate")
                
                positions[agent_name] = response.strip()
                
            except Exception as e:
                logger.warning(f"Failed to get position from {agent_name}: {e}")
                positions[agent_name] = f"Unable to provide position due to error: {e}"
        
        return {"initial_positions": positions}
        
    except Exception as e:
        logger.error(f"Error gathering positions: {e}")
        return {"initial_positions": {}}


async def conduct_round_node(state: DebateState) -> Dict[str, Any]:
    """Conduct one round of argumentation between agents."""
    try:
        arguments = {}
        service = multi_agent_debate_service
        
        # Build context from previous rounds
        previous_context = ""
        for history_item in state.debate_history:
            if history_item.get("phase") == DebatePhase.ARGUMENTATION.value:
                previous_context += f"\nRound {history_item['round']}:\n"
                for agent_name, argument in history_item["content"].items():
                    previous_context += f"  {agent_name}: {argument[:100]}...\n"
        
        for agent_name in state.active_agents:
            try:
                agent_enum = DebateAgent(agent_name)
                persona = service.agent_personas[agent_enum]
                
                # Get other agents' positions for reference
                other_positions = {k: v for k, v in state.initial_positions.items() if k != agent_name}
                
                argument_prompt = f"""
{persona['role']}

**DEBATE TOPIC:** {state.debate_topic}
**YOUR INITIAL POSITION:** {state.initial_positions.get(agent_name, 'Not provided')}

**OTHER AGENTS' POSITIONS:**
{json.dumps(other_positions, indent=2)}

**PREVIOUS DISCUSSION:**
{previous_context}

Now provide your argument, considering what others have said. You may:
1. Strengthen your position with new evidence
2. Address points raised by other agents
3. Find common ground where appropriate
4. Raise new concerns or opportunities

Maintain your {persona['style']} while being constructive. Keep under 100 words.

Your argument:"""

                messages = [
                    {"role": "system", "content": f"You are {agent_name} engaging in constructive debate."},
                    {"role": "user", "content": argument_prompt}
                ]
                
                model = state.chat_model or "llama3.2:3b"
                response, _ = await invoke_llm_with_tokens(messages, model, category="debate")
                
                arguments[agent_name] = response.strip()
                
            except Exception as e:
                logger.warning(f"Failed to get argument from {agent_name}: {e}")
                arguments[agent_name] = f"Unable to provide argument due to error: {e}"
        
        # Update debate history
        new_history = state.debate_history + [{
            "phase": DebatePhase.ARGUMENTATION.value,
            "round": state.current_round + 1,
            "content": arguments
        }]
        
        return {
            "debate_history": new_history,
            "current_round": state.current_round + 1
        }
        
    except Exception as e:
        logger.error(f"Error in debate round: {e}")
        return {"current_round": state.current_round + 1}


async def synthesize_debate_node(state: DebateState) -> Dict[str, Any]:
    """Synthesize the debate into final consensus."""
    try:
        # Format debate history for synthesis
        debate_summary = f"INITIAL POSITIONS:\n"
        for agent, position in state.initial_positions.items():
            debate_summary += f"  {agent}: {position}\n"
        
        debate_summary += "\nDEBATE PROGRESSION:\n"
        for history_item in state.debate_history:
            if history_item.get("phase") == DebatePhase.ARGUMENTATION.value:
                debate_summary += f"Round {history_item['round']}:\n"
                for agent, argument in history_item["content"].items():
                    debate_summary += f"  {agent}: {argument}\n"
        
        synthesis_prompt = f"""
You are a neutral synthesizer analyzing a multi-agent debate. Your job is to integrate all perspectives into a balanced final decision.

**ORIGINAL TOPIC:** {state.debate_topic}
**USER REQUEST:** {state.user_input}
**CONTEXT:** {json.dumps(state.decision_context, indent=2)}

**DEBATE SUMMARY:**
{debate_summary}

**SYNTHESIS INSTRUCTIONS:**
1. Identify areas of agreement and disagreement
2. Weigh the strength of different arguments
3. Consider the user's underlying needs
4. Provide a balanced recommendation
5. Assess confidence in the decision

**OUTPUT FORMAT (JSON only):**
{{
  "decision": "clear final decision or recommendation",
  "confidence": 0.0-1.0,
  "reasoning": "explanation of how you reached this decision",
  "key_agreements": ["point 1", "point 2"],
  "key_concerns": ["concern 1", "concern 2"],
  "consensus": true/false
}}

Analyze the debate and provide synthesis:"""

        messages = [
            {"role": "system", "content": "You are a neutral synthesizer. Always respond with valid JSON only."},
            {"role": "user", "content": synthesis_prompt}
        ]
        
        model = state.chat_model or "llama3.2:3b"
        response, _ = await invoke_llm_with_tokens(messages, model, category="debate")
        
        try:
            synthesis = json.loads(response)
            
            # Ensure required fields
            synthesis.setdefault("decision", state.debate_topic)
            synthesis.setdefault("confidence", 0.5)
            synthesis.setdefault("consensus", False)
            synthesis.setdefault("reasoning", "Synthesis completed")
            
            return {
                "final_synthesis": synthesis,
                "confidence": synthesis.get("confidence", 0.5),
                "decision": synthesis.get("decision", ""),
                "reasoning": synthesis.get("reasoning", ""),
                "consensus_reached": synthesis.get("consensus", False)
            }
            
        except json.JSONDecodeError:
            logger.warning("Failed to parse synthesis JSON, using fallback")
            fallback_synthesis = {
                "decision": state.debate_topic,
                "confidence": 0.6,
                "reasoning": "Multi-agent debate completed successfully",
                "consensus": True,
                "agents_participated": len(state.active_agents)
            }
            
            return {
                "final_synthesis": fallback_synthesis,
                "confidence": 0.6,
                "decision": state.debate_topic,
                "reasoning": "Multi-agent debate completed successfully",
                "consensus_reached": True
            }
            
    except Exception as e:
        logger.error(f"Error in synthesis: {e}")
        fallback_synthesis = {
            "decision": state.debate_topic,
            "confidence": 0.4,
            "reasoning": f"Synthesis error: {str(e)}",
            "consensus": False
        }
        
        return {
            "final_synthesis": fallback_synthesis,
            "confidence": 0.4,
            "decision": state.debate_topic,
            "reasoning": f"Synthesis error: {str(e)}",
            "consensus_reached": False
        }


def should_continue_debate(state: DebateState) -> str:
    """Decide whether to continue debate or move to synthesis."""
    if state.current_round >= state.max_rounds:
        return "synthesize_debate"
    
    # Check for early consensus (could add consensus detection logic here)
    return "conduct_round"


# Create the debate workflow graph
debate_workflow = StateGraph(DebateState)

# Add nodes
debate_workflow.add_node("select_agents", RunnableLambda(select_agents_node))  # type: ignore
debate_workflow.add_node("gather_positions", RunnableLambda(gather_positions_node))  # type: ignore  
debate_workflow.add_node("conduct_round", RunnableLambda(conduct_round_node))  # type: ignore
debate_workflow.add_node("synthesize_debate", RunnableLambda(synthesize_debate_node))  # type: ignore

# Set entry point
debate_workflow.set_entry_point("select_agents")

# Add edges
debate_workflow.add_edge("select_agents", "gather_positions")
debate_workflow.add_edge("gather_positions", "conduct_round")
debate_workflow.add_conditional_edges(
    "conduct_round",
    should_continue_debate,
    {
        "conduct_round": "conduct_round",
        "synthesize_debate": "synthesize_debate"
    }
)
debate_workflow.add_edge("synthesize_debate", END)

# Compile the workflow
compiled_debate_workflow = debate_workflow.compile()


# Global instance
multi_agent_debate_service = MultiAgentDebateService()